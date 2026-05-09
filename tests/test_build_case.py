import importlib.util
import json
from pathlib import Path


def _load_build_case_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "build_case.py"
    spec = importlib.util.spec_from_file_location("build_case", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_build_case_creates_archive_layout_and_metrics(tmp_path: Path) -> None:
    module = _load_build_case_module()
    run_dir = tmp_path / "runs" / "acme-20260509-101112"
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": "acme-20260509-101112",
            "created_at": "2026-05-09T10:11:12-07:00",
            "input": {"company_name": "Acme"},
            "modules": [
                {"module": "research", "status": "ok"},
                {"module": "critic", "status": "ok"},
            ],
        },
    )
    _write_json(
        run_dir / "research_brief.json",
        {
            "company_name": "Acme",
            "sources": [
                {"url_or_path": "https://example.com/a"},
                {"url_or_path": "https://example.com/b"},
            ],
        },
    )
    _write_json(run_dir / "evidence_store.json", {"E1": {}, "E2": {}, "E3": {}})
    _write_json(
        run_dir / "research_provenance.json",
        {
            "research_sources_urls": [
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
                "https://example.com/d",
                "https://example.com/e",
                "https://example.com/f",
            ],
            "post_liveness_kept_urls": [
                "https://example.com/a",
                "https://example.com/b",
            ],
        },
    )
    _write_json(
        run_dir / "cost_summary.json",
        {
            "run_id": "acme-20260509-101112",
            "company_name": "Acme",
            "total_cost_usd": 0.123,
            "by_module": {},
            "notes": [],
        },
    )
    _write_json(
        run_dir / "critic_review.json",
        {
            "citation_issues": [
                {"severity": "high"},
                {"severity": "medium"},
                {"severity": "medium"},
            ]
        },
    )
    _write_json(run_dir / "lens_fit.json", {"conflicts": ["one"]})
    (run_dir / "final_report.md").write_text("# Acme\n", encoding="utf-8")
    (run_dir / "run.log").write_text(
        "URL liveness gate: kept 2/5 (dropped: https://bad.example -> 404)\n",
        encoding="utf-8",
    )
    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    (cases_root / "TEMPLATE_review.md").write_text(
        "# Case Review: <Company>\n\n"
        "**Run ID:** \n"
        "**Run date:** \n"
        "**Reviewer:** \n"
        "**Time spent reviewing (minutes):** \n\n"
        "## 1. Strongest claims (top 3)\n"
        "For each: template guidance.\n\n"
        "## 2. Weakest claims (top 3)  \n"
        "For each: template guidance.\n",
        encoding="utf-8",
    )

    case_dir = module.build_case(
        run_dir=run_dir,
        slug="acme",
        cases_root=cases_root,
    )

    assert case_dir == cases_root / "_archive" / "acme-20260509"
    assert (case_dir / "run" / "run.json").exists()
    assert (case_dir / "run" / "final_report.md").read_text(encoding="utf-8") == "# Acme\n"
    assert json.loads((case_dir / "cost_summary.json").read_text(encoding="utf-8"))[
        "total_cost_usd"
    ] == 0.123
    assert json.loads((case_dir / "research_provenance.json").read_text(encoding="utf-8"))[
        "research_sources_urls"
    ] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/d",
        "https://example.com/e",
        "https://example.com/f",
    ]
    review = (case_dir / "review.md").read_text(encoding="utf-8")
    assert "**Run ID:** acme-20260509-101112" in review
    assert "**Run date:** 2026-05-09" in review
    assert "**Reviewer:** " in review
    assert "For each: template guidance." not in review

    metrics = json.loads((case_dir / "baseline_metrics.json").read_text(encoding="utf-8"))
    assert metrics == {
        "company_name": "Acme",
        "run_id": "acme-20260509-101112",
        "run_date": "2026-05-09",
        "sources_total": 6,
        "sources_kept_after_liveness": 2,
        "liveness_pass_rate": 0.333,
        "evidence_store_entries": 3,
        "modules_completed": 2,
        "modules_with_conflicts_flagged": 1,
        "critic_review_severity_counts": {"high": 1, "medium": 2, "low": 0},
        "research_backend": "gpt_researcher",
        "rag_enabled": True,
        "wall_clock_seconds": 0,
    }
