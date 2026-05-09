from mgt470_analyst import orchestrator
from mgt470_analyst.adapters.research.gpt_researcher_adapter import GPTResearcherAdapter
from mgt470_analyst.adapters.research.openai_research import OpenAIResearchAdapter
from mgt470_analyst.llm.client import LLMClient
from mgt470_analyst.llm.config import LLMConfig
from mgt470_analyst.orchestrator import _select_research_adapter
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


def test_select_research_adapter_uses_stub_when_offline(monkeypatch) -> None:
    monkeypatch.setenv("MGT470_OFFLINE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MGT470_RESEARCH_BACKEND", "gpt_researcher")

    adapter = _select_research_adapter(client=_fake_client())

    assert isinstance(adapter, OpenAIResearchAdapter)


def test_select_research_adapter_uses_gpt_researcher_when_key_is_set(monkeypatch) -> None:
    monkeypatch.setenv("MGT470_OFFLINE", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MGT470_RESEARCH_BACKEND", "gpt_researcher")

    adapter = _select_research_adapter(client=_fake_client())

    assert isinstance(adapter, GPTResearcherAdapter)


def test_gpt_researcher_query_under_tavily_limit() -> None:
    query = GPTResearcherAdapter()._build_query(RawInput(company_name="Notion"))

    assert len(query) < 380
    assert "Notion" in query
    assert "digital disruption" in query or "decoupling" in query


def test_gpt_researcher_query_includes_ticker_and_website_when_present() -> None:
    query = GPTResearcherAdapter()._build_query(
        RawInput(
            company_name="Nubank",
            ticker="NU",
            website="https://nubank.com.br",
        )
    )

    assert len(query) < 380
    assert "NU" in query
    assert "https://nubank.com.br" in query


def test_gpt_researcher_query_handles_long_company_name() -> None:
    company_name = "A" * 100

    query = GPTResearcherAdapter()._build_query(RawInput(company_name=company_name))

    assert len(query) < 380
    assert company_name in query


def test_gpt_researcher_normalize_uses_retrieved_urls(monkeypatch) -> None:
    from mgt470_analyst.schemas.raw_input import RawInput

    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    report = (
        "Finding one. References: "
        "https://www.notion.so/pricing "
        "https://developers.notion.com/ "
        "https://www.pcmag.com/reviews/notion"
    )
    brief = GPTResearcherAdapter()._normalize(
        report=report,
        sources=["https://translate.yandex.com/"],
        raw_input=RawInput(company_name="Notion"),
        research_sources_urls=["https://www.notion.so/pricing"],
    )

    assert [source.url_or_path for source in brief.sources] == [
        "https://www.notion.so/pricing"
    ]


def test_gpt_researcher_normalize_ignores_report_urls_when_retrieved_url_present(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    report = " ".join(f"https://example.com/source-{index}" for index in range(10))
    brief = GPTResearcherAdapter()._normalize(
        report=report,
        sources=["https://translate.yandex.com/"],
        raw_input=RawInput(company_name="Notion"),
        research_sources_urls=["https://translate.yandex.com/"],
    )

    assert len(brief.sources) == 1
    assert "https://translate.yandex.com/" in [source.url_or_path for source in brief.sources]


def test_live_research_failure_falls_back_to_stub(monkeypatch, caplog) -> None:
    class FailingGPTResearcherAdapter:
        def research(self, raw_input: RawInput):
            raise RuntimeError("simulated live failure")

    monkeypatch.setenv("MGT470_OFFLINE", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MGT470_RESEARCH_BACKEND", "gpt_researcher")
    monkeypatch.setattr(orchestrator, "GPTResearcherAdapter", FailingGPTResearcherAdapter)
    caplog.set_level("WARNING", logger="mgt470_analyst.orchestrator")

    brief = orchestrator._run_research_with_fallback(
        RawInput(company_name="Notion"),
        client=_fake_client(),
    )

    assert brief.company_name == "Notion"
    assert brief.sources
    assert "gpt_researcher" in caplog.text
    assert "falling back to stub" in caplog.text
    assert "simulated live failure" in caplog.text
