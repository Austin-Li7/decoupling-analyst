import logging
import re

from mgt470_analyst.renderers.markdown import render_report
from mgt470_analyst.renderers.markdown_zh import render_report_zh


class FakeTranslationClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def structured(self, **kwargs):
        if self.fail:
            raise RuntimeError("translation unavailable")
        schema = kwargs["schema"]
        if schema.__name__ == "MermaidLabelTranslation":
            return schema(labels=["步骤一", "步骤二"])
        raise AssertionError(f"Unexpected schema: {schema.__name__}")

    def text(self, **kwargs):
        if self.fail:
            raise RuntimeError("translation unavailable")
        markdown = kwargs["user"].split("MARKDOWN:\n", maxsplit=1)[-1]
        return (
            markdown.replace("## TL;DR", "## 要点摘要")
            .replace("## Key Diagram", "## 关键图示")
            .replace("## The Wedge", "## 切入楔子")
            .replace("## Confidence & Open Questions", "## 信心与开放问题")
            .replace("### Lens Fit", "### 透镜契合")
            .replace("### Weak Link", "### 薄弱环节")
            .replace("English paragraph", "中文段落")
        )


def _heading_count(markdown: str, marker: str) -> int:
    return len(re.findall(rf"^{re.escape(marker)}\s", markdown, flags=re.MULTILINE))


def _minimal_context() -> dict:
    return {
        "company_name": "Duolingo",
        "final_judgment": {
            "judgment": "study_more",
            "one_sentence_thesis": "Duolingo should study the onboarding wedge.",
            "why_now": "The market is moving now.",
            "strongest_argument": "The activity has obvious effort friction.",
            "biggest_risk": "Evidence is thin.",
            "staged_actions": ["LIGHT: test onboarding helper"],
            "do_not_do": ["Do not overbuild."],
            "next_research_steps": ["Verify retention data."],
            "evidence_ids": ["E1"],
        },
        "lens_fit": {
            "primary_type": "tech_substitution",
            "confidence": "medium",
            "decoupling_fit_score": 0.72,
            "recommended_report_mode": "strategic_memo",
            "reasoning": "Technology changes the job.",
        },
        "case_perspective": {
            "perspective": "disruptor",
            "confidence": "medium",
            "primary_question": "Where should the entrant attack?",
            "reasoning": "The case is from a challenger seat.",
        },
        "company_profile": {
            "company": {"name": "Duolingo", "industry": "education technology"},
            "business_model": {"revenue_model": "subscription", "pricing_model": "freemium"},
        },
        "critic_review": {
            "overall_score": 3.5,
            "discipline_scores": [],
            "citation_issues": [],
        },
        "evidence_store": {"E1": {"claim": "Evidence."}},
        "weak_link": "Evaluate options scored 216.0: effort is high.",
        "weak_links": {
            "ranked_weak_links": [{"activity_id": "A2", "rationale": "Effort is high."}]
        },
        "decoupling": "Focused product.",
        "decoupling_strategy": {
            "primary_decoupling": {
                "activity_to_decouple": "Evaluate options",
                "why_customer_switches": "It is faster.",
            }
        },
        "business_model": "Subscription monetization.",
        "competitive_response": "Incumbents may copy.",
        "competitive": {"likely_responses": []},
        "recoupling": {},
        "cvc": [
            {"id": "A1", "step": 1, "activity": "Discover", "current_provider": "search"},
            {"id": "A2", "step": 2, "activity": "Evaluate", "current_provider": "apps"},
        ],
        "values": [{"activity_id": "A2", "value_type": "erode"}],
        "research": {"research_summary": "English paragraph.", "sources": []},
    }


def test_zh_report_has_same_section_count_as_en() -> None:
    english = render_report(_minimal_context())

    chinese = render_report_zh(english, client=FakeTranslationClient())

    assert _heading_count(chinese, "##") == _heading_count(english, "##")
    assert _heading_count(chinese, "###") == _heading_count(english, "###")
    assert "## 要点摘要" in chinese


def test_zh_report_preserves_mermaid_syntax() -> None:
    english = """---
company: Acme
workflow: mgt470_analyst
---

# Acme Report

## Key Diagram

```mermaid
flowchart LR
    A1["<b>Step 1</b><br/>Discover options"]
    A2["<b>Step 2</b><br/>Evaluate options"]
    A1 --> A2
    style A1 fill:#d1f7c4,stroke:#1f8a3a,color:#0b3d18
```
"""

    chinese = render_report_zh(english, client=FakeTranslationClient())

    assert "flowchart LR" in chinese
    assert "style A1 fill:#d1f7c4,stroke:#1f8a3a,color:#0b3d18" in chinese
    assert 'A1["步骤一"]' in chinese
    assert 'A2["步骤二"]' in chinese


def test_zh_falls_back_to_english_on_llm_failure(caplog) -> None:
    caplog.set_level(logging.WARNING)
    english = "# Acme\n\n## TL;DR\n\nEnglish content."

    chinese = render_report_zh(english, client=FakeTranslationClient(fail=True))

    assert "⚠️ 自动翻译失败，以下为英文原文" in chinese
    assert "English content." in chinese
    assert "translation unavailable" in caplog.text


def test_zh_preserves_evidence_ids_and_urls() -> None:
    english = (
        "# Acme\n\n## TL;DR\n\n"
        "Evidence (E12, E13) comes from https://example.com/path and S1."
    )

    chinese = render_report_zh(english, client=FakeTranslationClient())

    assert "E12" in chinese
    assert "E13" in chinese
    assert "S1" in chinese
    assert "https://example.com/path" in chinese


def test_zh_does_not_truncate_with_ellipsis() -> None:
    long_paragraph = " ".join(["English paragraph"] * 100)
    english = f"# Acme\n\n## TL;DR\n\n{long_paragraph}"

    chinese = render_report_zh(english, client=FakeTranslationClient())

    assert "…" not in chinese


def test_zh_renderer_uses_text_translation_method() -> None:
    class TextOnlyClient:
        def __init__(self) -> None:
            self.called = False

        def text(self, **kwargs):
            self.called = True
            return "# 中文标题\n\n## 要点摘要\n\n完整翻译。"

        def structured(self, **kwargs):
            raise AssertionError("Mermaid labels are absent; structured should not be used")

    client = TextOnlyClient()

    chinese = render_report_zh(
        "# English title\n\n## TL;DR\n\nComplete translation.",
        client=client,
    )

    assert client.called
    assert "# 中文标题" in chinese
