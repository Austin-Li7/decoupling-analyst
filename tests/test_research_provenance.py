import json
import logging
from pathlib import Path

import pytest

from mgt470_analyst.adapters.research.gpt_researcher_adapter import (
    GPTResearcherAdapter,
    RetrievalAllDeadError,
    _build_research_provenance,
    _URLLivenessResult,
)
from mgt470_analyst.schemas.raw_input import RawInput


def test_provenance_classifies_report_only_urls() -> None:
    research_sources_urls = [
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
        searched_urls=[],
        research_sources_urls=research_sources_urls,
        visited_urls_from_retriever=research_sources_urls,
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
    assert provenance["research_sources_urls"] == research_sources_urls
    assert provenance["visited_urls_from_retriever"] == research_sources_urls
    assert provenance["prefetched_url_count"] == 0


def test_provenance_writes_by_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    artifact_path = tmp_path / "research_provenance.json"

    GPTResearcherAdapter()._normalize(
        report="Report cites https://example.com/a",
        sources=["https://example.com/a"],
        raw_input=RawInput(company_name="Acme"),
        run_id="acme-20260509-120000",
        provenance_path=artifact_path,
        research_sources_urls=["https://example.com/a"],
        visited_urls_from_retriever=[],
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["research_sources_urls"] == ["https://example.com/a"]
    assert artifact["visited_urls_from_retriever"] == []
    assert artifact["prefetched_url_count"] == 1
    assert artifact["report_only_url_ratio"] == 0.0


def test_provenance_writes_artifact_schema(monkeypatch, tmp_path: Path, caplog) -> None:
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
        research_sources_urls=["https://example.com/a"],
        visited_urls_from_retriever=["https://example.com/a"],
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["company_name"] == "Acme"
    assert artifact["run_id"] == "acme-20260509-120000"
    assert artifact["searched_urls_count"] == 1
    assert artifact["research_sources_urls"] == ["https://example.com/a"]
    assert artifact["visited_urls_from_retriever"] == ["https://example.com/a"]
    assert artifact["prefetched_url_count"] == 0
    assert artifact["report_cited_urls_count"] == 2
    assert artifact["union_pre_liveness_count"] == 1
    assert artifact["report_urls_in_search_results"] == 1
    assert artifact["report_urls_only_in_report"] == 1
    assert artifact["report_only_url_ratio"] == 0.5
    assert artifact["post_liveness_kept_urls"] == ["https://example.com/a"]
    assert artifact["post_liveness_dropped_urls"] == []
    assert "Research provenance dump written:" in caplog.text


def test_normalize_uses_research_sources_urls_only(monkeypatch) -> None:
    research_sources_urls = [
        "https://example.com/retrieved-1",
        "https://example.com/retrieved-2",
    ]
    report = (
        "Report cites https://example.com/retrieved-1 and "
        "https://example.com/fabricated"
    )
    monkeypatch.setattr(
        "mgt470_analyst.adapters.research.gpt_researcher_adapter._filter_live_urls_with_results",
        lambda urls: (urls, []),
    )

    brief = GPTResearcherAdapter()._normalize(
        report=report,
        sources=["https://example.com/ignored-source-url"],
        raw_input=RawInput(company_name="Acme"),
        research_sources_urls=research_sources_urls,
        visited_urls_from_retriever=[],
    )

    assert [source.url_or_path for source in brief.sources] == research_sources_urls
    assert "https://example.com/fabricated" not in [
        source.url_or_path for source in brief.sources
    ]


def test_retrieval_all_dead_raises(monkeypatch) -> None:
    retrieved = ["https://example.com/dead-1", "https://example.com/dead-2"]
    monkeypatch.setattr(
        "mgt470_analyst.adapters.research.gpt_researcher_adapter._filter_live_urls_with_results",
        lambda urls: ([], [_URLLivenessResult(url=url, live=False, status="404") for url in urls]),
    )

    with pytest.raises(RetrievalAllDeadError):
        GPTResearcherAdapter()._normalize(
            report="Report cites https://example.com/fabricated",
            sources=[],
            raw_input=RawInput(company_name="Acme"),
            research_sources_urls=retrieved,
            visited_urls_from_retriever=[],
        )


def test_provenance_records_prefetch_discrepancy(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    artifact_path = tmp_path / "research_provenance.json"
    research_sources_urls = ["https://example.com/a", "https://example.com/b"]

    GPTResearcherAdapter()._normalize(
        report="Report cites https://example.com/a",
        sources=["https://example.com/a"],
        raw_input=RawInput(company_name="Acme"),
        run_id="acme-20260509-120000",
        provenance_path=artifact_path,
        research_sources_urls=research_sources_urls,
        visited_urls_from_retriever=[],
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["prefetched_url_count"] == 2
    assert artifact["visited_urls_from_retriever"] == []
    assert artifact["research_sources_urls"] == research_sources_urls
