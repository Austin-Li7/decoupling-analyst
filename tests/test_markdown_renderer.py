from mgt470_analyst.renderers.markdown import render_report
from mgt470_analyst.schemas.final_judgment import FinalJudgment


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
            "company": {
                "name": "Duolingo",
                "website": "https://www.duolingo.com",
                "ticker": "DUOL",
                "public_or_private": "public",
                "industry": "education technology",
                "geography": ["US"],
                "stage": "public",
                "description": "Language-learning app.",
            },
            "business_model": {
                "revenue_model": "subscription plus ads",
                "pricing_model": "freemium",
                "distribution_channels": ["app stores"],
            },
        },
        "critic_review": {
            "overall_score": 3.5,
            "weakest_aspect": "Evidence depth",
            "discipline_scores": [],
            "citation_issues": [
                {
                    "severity": "high",
                    "issue": "Retention claim needs stronger evidence.",
                    "cited_evidence_ids": ["E1"],
                    "location": "final_judgment",
                }
            ],
            "revision_suggestions": [],
            "would_disagree_with_thesis": False,
            "disagreement_summary": "Defensible but incomplete.",
        },
        "evidence_store": {"E1": {"claim": "User supplied target company."}},
        "weak_link": "Evaluate options scored 216.0: effort is high.",
        "weak_links": {
            "ranked_weak_links": [
                {
                    "activity_id": "A2",
                    "score": 216.0,
                    "rationale": "Effort is high.",
                    "evidence_ids": ["E1"],
                }
            ]
        },
        "decoupling": "Focused product that makes this activity easier.",
        "decoupling_strategy": {
            "primary_decoupling": {
                "activity_to_decouple": "Evaluate options",
                "from_incumbent_bundle": "full course bundle",
                "customer_pain": "high effort",
                "new_offering": "A focused helper for evaluating options.",
                "why_customer_switches": "It is faster.",
                "cheaper_faster_easier": ["faster"],
                "evidence_ids": ["E1"],
            },
            "do_not_decouple": [],
        },
        "business_model": "Subscription monetization.",
        "competitive_response": "Incumbents may copy.",
        "competitive": {"likely_responses": []},
        "recoupling": {
            "vulnerability": "medium",
            "incumbent_capability_to_recouple": "medium",
            "incumbent_incentive_to_recouple": "medium",
            "rationale": "Incumbents can copy some pieces.",
            "defenses": ["speed"],
        },
        "cvc": [
            {
                "id": "A1",
                "step": 1,
                "activity": "Discover options",
                "current_provider": "search",
                "evidence_ids": ["E1"],
            },
            {
                "id": "A2",
                "step": 2,
                "activity": "Evaluate options",
                "current_provider": "apps",
                "evidence_ids": ["E1"],
            },
        ],
        "values": [
            {"activity_id": "A1", "value_type": "create", "reasoning": "Creates value."},
            {"activity_id": "A2", "value_type": "erode", "reasoning": "Erodes value."},
        ],
        "research": {
            "research_summary": "Clean summary.",
            "sources": [],
            "open_questions": ["What is retention by cohort?"],
        },
    }


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


def test_renderer_pyramid_structure() -> None:
    report = render_report(_minimal_context())

    assert report.index("## TL;DR") < report.index("## Key Diagram")
    assert report.index("## Key Diagram") < report.index("## The Wedge")
    assert report.index("## The Wedge") < report.index("## Confidence & Open Questions")
    assert "<details>" in report
    assert "📚 Appendix: full module outputs (click to expand)" in report


def test_renderer_strips_inline_md_headings() -> None:
    context = _minimal_context()
    context["research"]["research_summary"] = (
        "## Introduction\nThis raw GPT Researcher text should not become an outer heading."
    )

    report = render_report(context)

    assert "\n## Introduction" not in report
    assert "Raw GPT Researcher narrative (unparsed)" in report
    assert "    ## Introduction" in report


def test_renderer_isolates_report_only_references() -> None:
    context = _minimal_context()
    context["company_profile"]["company"]["website"] = "https://retrieved.example.com"
    context["final_judgment"]["one_sentence_thesis"] = (
        "Use validated evidence E1 and https://retrieved.example.com, but inspect "
        "unsupported claim E99 from https://unretrieved.example.com."
    )
    context["evidence_store"] = {
        "E1": {
            "claim": "Retrieved source supports the claim.",
            "source_id": "S1",
            "locator": "website: https://retrieved.example.com",
            "confidence": "high",
            "used_by_modules": ["final_judgment"],
        }
    }
    context["research"]["sources"] = [
        {
            "id": "S1",
            "title": "Retrieved source",
            "url_or_path": "https://retrieved.example.com",
            "source_type": "website",
            "retrieved_at": "2026-05-21",
            "reliability": "high",
            "key_claims": ["Retrieved source supports the claim."],
        }
    ]

    report = render_report(context)

    assert "## Unverified References" in report
    unverified = report.split("## Unverified References", maxsplit=1)[1]
    assert "E99" in unverified
    assert "https://unretrieved.example.com" in unverified
    assert "E1" not in unverified
    assert "https://retrieved.example.com" not in unverified


def test_renderer_omits_unverified_section_when_references_are_grounded() -> None:
    context = _minimal_context()
    context["company_profile"]["company"]["website"] = "https://retrieved.example.com"
    context["final_judgment"]["one_sentence_thesis"] = (
        "Use validated evidence E1 from https://retrieved.example.com."
    )
    context["evidence_store"] = {
        "E1": {
            "claim": "Retrieved source supports the claim.",
            "source_id": "S1",
            "locator": "website: https://retrieved.example.com",
            "confidence": "high",
            "used_by_modules": ["final_judgment"],
        }
    }
    context["research"]["sources"] = [
        {
            "id": "S1",
            "title": "Retrieved source",
            "url_or_path": "https://retrieved.example.com",
            "source_type": "website",
            "retrieved_at": "2026-05-21",
            "reliability": "high",
            "key_claims": ["Retrieved source supports the claim."],
        }
    ]

    report = render_report(context)

    assert "## Unverified References" not in report
