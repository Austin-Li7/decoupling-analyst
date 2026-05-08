from mgt470_analyst.renderers.markdown import render_report
from mgt470_analyst.schemas.final_judgment import FinalJudgment


def test_markdown_report_contains_required_sections() -> None:
    report = render_report(
        {
            "company_name": "Duolingo",
            "final_judgment": FinalJudgment(
                judgment="study_more",
                one_sentence_thesis="The company is worth studying, but evidence is sparse.",
                why_now="A plausible weak link exists.",
                strongest_argument="Focused decoupling reduces effort.",
                biggest_risk="Stub research.",
                next_research_steps=["Run real cited research."],
                evidence_ids=["E1"],
            ),
            "evidence_store": {"E1": {"claim": "User supplied target company."}},
            "weak_link": "Compare and choose among options",
            "decoupling": "Focused product that makes this activity easier.",
        }
    )

    assert "Duolingo" in report
    assert "> [!important] Final Judgment" in report
    assert "## Evidence Base" in report
    assert "## Weak Link" in report
    assert "## Decoupling Strategy" in report
