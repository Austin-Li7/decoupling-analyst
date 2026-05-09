import pytest

from mgt470_analyst import orchestrator
from mgt470_analyst.adapters.research import gpt_researcher_adapter
from mgt470_analyst.adapters.research.gpt_researcher_adapter import (
    GPTResearcherAdapter,
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

    async def write_report(self) -> str:
        self.write_report_called = True
        return "This should not be written."

    async def get_source_urls(self) -> list[str]:
        return []


def test_empty_visited_urls_raises_retrieval_empty_error(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    monkeypatch.setattr(
        gpt_researcher_adapter,
        "_load_gpt_researcher",
        lambda: _EmptyRetrievalResearcher,
    )

    with pytest.raises(RetrievalEmptyError):
        GPTResearcherAdapter().research(RawInput(company_name="Notion"))


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
