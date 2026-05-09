import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_rerender_script_regenerates_both_reports(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_json(
        run_dir / "run.json",
        {"run_id": "duolingo-20260509", "input": {"company_name": "Duolingo"}},
    )
    _write_json(
        run_dir / "research_brief.json",
        {"company_name": "Duolingo", "research_summary": "## Introduction\nRaw.", "sources": []},
    )
    _write_json(
        run_dir / "company_profile.json",
        {
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
    )
    _write_json(
        run_dir / "lens_fit.json",
        {
            "primary_type": "tech_substitution",
            "confidence": "medium",
            "decoupling_fit_score": 0.7,
            "recommended_report_mode": "strategic_memo",
            "reasoning": "Technology changes the job.",
        },
    )
    _write_json(
        run_dir / "case_perspective.json",
        {
            "perspective": "disruptor",
            "confidence": "medium",
            "primary_question": "Where should the entrant attack?",
            "reasoning": "Challenger seat.",
        },
    )
    _write_json(
        run_dir / "cvc.json",
        {
            "activities": [
                {"id": "A1", "step": 1, "activity": "Discover", "current_provider": "search"},
                {"id": "A2", "step": 2, "activity": "Evaluate", "current_provider": "apps"},
            ]
        },
    )
    _write_json(
        run_dir / "value_type_diagnosis.json",
        {"activities": [{"activity_id": "A2", "value_type": "erode", "reasoning": "Hard."}]},
    )
    _write_json(
        run_dir / "weak_link_analysis.json",
        {
            "ranked_weak_links": [
                {"activity_id": "A2", "score": 216.0, "rationale": "Evaluation is hard."}
            ]
        },
    )
    _write_json(
        run_dir / "decoupling_strategy.json",
        {
            "primary_decoupling": {
                "activity_to_decouple": "Evaluate",
                "from_incumbent_bundle": "course bundle",
                "customer_pain": "high effort",
                "new_offering": "Focused helper.",
                "why_customer_switches": "Faster.",
                "cheaper_faster_easier": ["faster"],
                "evidence_ids": ["E1"],
            },
            "do_not_decouple": [],
        },
    )
    _write_json(run_dir / "business_model_analysis.json", {"value_creation": "Creates value."})
    _write_json(
        run_dir / "competitive_response.json",
        {
            "likely_responses": [{"description": "Copy.", "response_type": "copy"}],
            "recoupling_vulnerability": {
                "vulnerability": "medium",
                "incumbent_capability_to_recouple": "medium",
                "incumbent_incentive_to_recouple": "medium",
                "rationale": "Can copy.",
                "defenses": ["speed"],
            },
        },
    )
    _write_json(
        run_dir / "final_judgment.json",
        {
            "judgment": "study_more",
            "one_sentence_thesis": "Duolingo should study the onboarding wedge.",
            "why_now": "The market is moving.",
            "strongest_argument": "Lower effort.",
            "biggest_risk": "Thin evidence.",
            "staged_actions": ["LIGHT: test helper"],
            "do_not_do": ["Do not overbuild."],
            "next_research_steps": ["Verify retention."],
            "evidence_ids": ["E1"],
        },
    )
    _write_json(
        run_dir / "critic_review.json",
        {
            "overall_score": 3,
            "weakest_aspect": "Evidence",
            "discipline_scores": [],
            "citation_issues": [
                {
                    "severity": "high",
                    "issue": "Needs better evidence.",
                    "cited_evidence_ids": ["E1"],
                    "location": "final",
                }
            ],
            "revision_suggestions": [],
            "would_disagree_with_thesis": False,
            "disagreement_summary": "Defensible.",
        },
    )
    _write_json(run_dir / "evidence_store.json", {"E1": {"claim": "Evidence."}})
    _write_json(
        run_dir / "cost_summary.json",
        {
            "run_id": "duolingo-20260509",
            "company_name": "Duolingo",
            "total_input_tokens": 10,
            "total_output_tokens": 5,
            "total_cost_usd": 0.001,
            "by_module": {
                "company_profile": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "cost_usd": 0.001,
                    "model": "gpt-5.2",
                }
            },
            "notes": [],
        },
    )

    completed = subprocess.run(
        [sys.executable, "scripts/rerender_report.py", str(run_dir)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (run_dir / "final_report.md").exists()
    assert (run_dir / "final_report_zh.md").exists()
    assert "## TL;DR" in (run_dir / "final_report.md").read_text(encoding="utf-8")
    cost_summary = json.loads((run_dir / "cost_summary.json").read_text(encoding="utf-8"))
    assert "final_report_zh" in cost_summary["by_module"]
