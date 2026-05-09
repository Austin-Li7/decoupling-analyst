import json
import logging
from pathlib import Path

from mgt470_analyst.adapters.research.gpt_researcher_adapter import (
    GPTResearcherAdapter,
    _build_research_provenance,
    _URLLivenessResult,
)
from mgt470_analyst.schemas.raw_input import RawInput


def test_provenance_classifies_report_only_urls() -> None:
    searched_urls = [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
    report_urls = [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/fabricated",
    ]

    provenance = _build_research_provenance(
        company_name="Acme",
        run_id="acme-20260509-120000",
        searched_urls=searched_urls,
        report_cited_urls=report_urls,
        union_pre_liveness=report_urls,
        post_liveness_kept_urls=report_urls[:3],
        post_liveness_dropped=[
            _URLLivenessResult(
                url="https://example.com/fabricated",
                live=False,
                status="404",
            )
        ],
    )

    report_only = [
        item
        for item in provenance["report_cited_urls"]
        if item["provenance"] == "only_in_report"
    ]
    assert report_only == [
        {"url": "https://example.com/fabricated", "provenance": "only_in_report"}
    ]
    assert provenance["report_urls_in_search_results"] == 3
    assert provenance["report_urls_only_in_report"] == 1
    assert provenance["report_only_url_ratio"] == 0.25
    assert provenance["post_liveness_dropped_urls"] == [
        {
            "url": "https://example.com/fabricated",
            "status": "404",
            "was_in_search_results": False,
        }
    ]


def test_provenance_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MGT470_RESEARCH_PROVENANCE", raising=False)
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    artifact_path = tmp_path / "research_provenance.json"

    GPTResearcherAdapter()._normalize(
        report="Report cites https://example.com/a",
        sources=["https://example.com/a"],
        raw_input=RawInput(company_name="Acme"),
        run_id="acme-20260509-120000",
        provenance_path=artifact_path,
    )

    assert not artifact_path.exists()


def test_provenance_enabled_writes_artifact(monkeypatch, tmp_path: Path, caplog) -> None:
    monkeypatch.setenv("MGT470_RESEARCH_PROVENANCE", "1")
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    artifact_path = tmp_path / "research_provenance.json"
    caplog.set_level(logging.INFO, logger="mgt470_analyst.adapters.research.gpt_researcher_adapter")

    GPTResearcherAdapter()._normalize(
        report=(
            "Report cites https://example.com/a and "
            "https://example.com/fabricated"
        ),
        sources=["https://example.com/a"],
        raw_input=RawInput(company_name="Acme"),
        run_id="acme-20260509-120000",
        provenance_path=artifact_path,
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["company_name"] == "Acme"
    assert artifact["run_id"] == "acme-20260509-120000"
    assert artifact["searched_urls_count"] == 1
    assert artifact["report_cited_urls_count"] == 2
    assert artifact["union_pre_liveness_count"] == 2
    assert artifact["report_urls_in_search_results"] == 1
    assert artifact["report_urls_only_in_report"] == 1
    assert artifact["report_only_url_ratio"] == 0.5
    assert artifact["post_liveness_kept_urls"] == [
        "https://example.com/a",
        "https://example.com/fabricated",
    ]
    assert artifact["post_liveness_dropped_urls"] == []
    assert "Research provenance dump written:" in caplog.text
