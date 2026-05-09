import logging

from mgt470_analyst.renderers.markdown_zh import render_report_zh


class FailingClient:
    def structured(self, **kwargs):
        raise RuntimeError("translation unavailable")


def _minimal_context() -> dict:
    return {
        "company_name": "Duolingo",
        "final_judgment": {
            "judgment": "study_more",
            "one_sentence_thesis": "Duolingo should study the onboarding wedge.",
            "biggest_risk": "Thin evidence.",
            "staged_actions": ["LIGHT: test helper"],
        },
        "lens_fit": {
            "primary_type": "tech_substitution",
            "confidence": "medium",
            "decoupling_fit_score": 0.7,
        },
        "case_perspective": {"perspective": "disruptor", "confidence": "medium"},
        "decoupling_strategy": {
            "primary_decoupling": {
                "activity_to_decouple": "Evaluate options",
                "why_customer_switches": "It is faster.",
            }
        },
        "weak_links": {
            "ranked_weak_links": [
                {"activity_id": "A2", "rationale": "Evaluation is hard."}
            ]
        },
        "critic_review": {
            "citation_issues": [
                {"severity": "high", "issue": "Needs stronger evidence."}
            ]
        },
        "cvc": [
            {"id": "A1", "step": 1, "activity": "Discover options"},
            {"id": "A2", "step": 2, "activity": "Evaluate options"},
        ],
        "values": [{"activity_id": "A2", "value_type": "erode"}],
    }


def test_zh_digest_uses_dict_for_short_fields(caplog) -> None:
    caplog.set_level(logging.WARNING)

    digest = render_report_zh(_minimal_context(), client=FailingClient())

    assert "技术替代" in digest
    assert "颠覆者" in digest


def test_zh_digest_falls_back_gracefully_on_llm_failure(caplog) -> None:
    caplog.set_level(logging.WARNING)
    context = _minimal_context()

    digest = render_report_zh(context, client=FailingClient())

    assert "Duolingo should study the onboarding wedge." in digest
    assert "translation unavailable" in caplog.text
    assert "# Duolingo 数字解构分析摘要" in digest
