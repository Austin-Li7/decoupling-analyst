import pytest

from mgt470_analyst import orchestrator
from mgt470_analyst.adapters.research import gpt_researcher_adapter
from mgt470_analyst.adapters.research.gpt_researcher_adapter import (
    GPTResearcherAdapter,
    RetrievalAllDeadError,
    RetrievalEmptyError,
)
from mgt470_analyst.llm.client import LLMClient
from mgt470_analyst.llm.config import LLMConfig
from mgt470_analyst.schemas.raw_input import RawInput


def _fake_client() -> LLMClient:
    return LLMClient(
        LLMConfig(
            fast="fake",
            smart="fake",
            research="fake",
            fast_effort="low",
            smart_effort="medium",
            research_effort="medium",
            offline=True,
        )
    )


class _EmptyRetrievalResearcher:
    visited_urls: list[str] = []
    write_report_called = False

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def conduct_research(self) -> None:
        self.visited_urls = []

    def get_research_sources(self) -> list[dict[str, str]]:
        return []

    async def write_report(self) -> str:
        self.write_report_called = True
        return "This should not be written."

    async def get_source_urls(self) -> list[str]:
        return []


class _PrefetchedResearcher:
    visited_urls: set[str] = set()
    research_sources = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
    ]

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def conduct_research(self) -> None:
        self.visited_urls = set()

    def get_research_sources(self) -> list[dict[str, str]]:
        return self.research_sources

    async def write_report(self) -> str:
        return "Report cites https://example.com/a"

    async def get_source_urls(self) -> list[str]:
        return ["https://example.com/a"]


def test_empty_research_sources_raises_retrieval_empty_error(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    monkeypatch.setattr(
        gpt_researcher_adapter,
        "_load_gpt_researcher",
        lambda: _EmptyRetrievalResearcher,
    )

    with pytest.raises(RetrievalEmptyError):
        GPTResearcherAdapter().research(RawInput(company_name="Notion"))


def test_grounding_uses_research_sources_when_visited_urls_empty(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    monkeypatch.setattr(
        gpt_researcher_adapter,
        "_load_gpt_researcher",
        lambda: _PrefetchedResearcher,
    )

    brief = GPTResearcherAdapter().research(RawInput(company_name="Notion"))

    assert [source.url_or_path for source in brief.sources] == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_orchestrator_falls_back_on_retrieval_empty(monkeypatch, caplog) -> None:
    monkeypatch.setenv("MGT470_OFFLINE", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MGT470_RESEARCH_BACKEND", "gpt_researcher")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    monkeypatch.setattr(
        gpt_researcher_adapter,
        "_load_gpt_researcher",
        lambda: _EmptyRetrievalResearcher,
    )
    caplog.set_level("WARNING", logger="mgt470_analyst.orchestrator")

    brief = orchestrator._run_research_with_fallback(
        RawInput(company_name="Notion"),
        client=_fake_client(),
    )

    assert brief.company_name == "Notion"
    assert brief.sources
    assert brief.sources[0].source_type == "stub"
    assert "RetrievalEmptyError" in caplog.text
    assert "falling back to stub" in caplog.text


def test_orchestrator_falls_back_on_retrieval_all_dead(monkeypatch, caplog) -> None:
    class AllDeadGPTResearcherAdapter:
        def research(self, raw_input: RawInput):
            raise RetrievalAllDeadError("all retrieved URLs failed liveness")

    monkeypatch.setenv("MGT470_OFFLINE", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MGT470_RESEARCH_BACKEND", "gpt_researcher")
    monkeypatch.setattr(orchestrator, "GPTResearcherAdapter", AllDeadGPTResearcherAdapter)
    caplog.set_level("WARNING", logger="mgt470_analyst.orchestrator")

    brief = orchestrator._run_research_with_fallback(
        RawInput(company_name="Notion"),
        client=_fake_client(),
    )

    assert brief.company_name == "Notion"
    assert brief.sources
    assert "RetrievalAllDeadError" in caplog.text
    assert "falling back to stub" in caplog.text


def test_no_tavily_key_no_escape_hatch_raises_at_guardrail_time(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("MGT470_ALLOW_UNGROUNDED_RESEARCH", raising=False)
    monkeypatch.delenv("RETRIEVER", raising=False)

    with pytest.raises(RuntimeError, match="No TAVILY_API_KEY set"):
        GPTResearcherAdapter()._apply_cost_guardrails()


def test_no_tavily_key_with_escape_hatch_warns_and_uses_ddg(
    monkeypatch, caplog
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("RETRIEVER", raising=False)
    monkeypatch.setenv("MGT470_ALLOW_UNGROUNDED_RESEARCH", "1")
    caplog.set_level("WARNING", logger=gpt_researcher_adapter.__name__)

    GPTResearcherAdapter()._apply_cost_guardrails()

    assert "DuckDuckGo retriever is known to return 0 results" in caplog.text
    assert "TAVILY_API_KEY" in caplog.text
    assert gpt_researcher_adapter.os.environ["RETRIEVER"] == "duckduckgo"


def test_max_search_results_per_query_not_set(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.delenv("MAX_SEARCH_RESULTS_PER_QUERY", raising=False)

    GPTResearcherAdapter()._apply_cost_guardrails()

    assert "MAX_SEARCH_RESULTS_PER_QUERY" not in gpt_researcher_adapter.os.environ
