from mgt470_analyst.adapters.research.gpt_researcher_adapter import GPTResearcherAdapter
from mgt470_analyst.adapters.research.openai_research import OpenAIResearchAdapter
from mgt470_analyst.llm.client import LLMClient
from mgt470_analyst.llm.config import LLMConfig
from mgt470_analyst.orchestrator import _select_research_adapter


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


def test_gpt_researcher_query_asks_for_broad_public_sources() -> None:
    from mgt470_analyst.schemas.raw_input import RawInput

    query = GPTResearcherAdapter()._build_query(RawInput(company_name="Notion"))

    assert "Use broad public web sources" in query
    assert "Do not add site: restrictions" in query


def test_gpt_researcher_normalize_prefers_report_reference_urls() -> None:
    from mgt470_analyst.schemas.raw_input import RawInput

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
    )

    assert [source.url_or_path for source in brief.sources[:3]] == [
        "https://www.notion.so/pricing",
        "https://developers.notion.com/",
        "https://www.pcmag.com/reviews/notion",
    ]


def test_gpt_researcher_normalize_ignores_sparse_scrape_urls_when_report_has_enough() -> None:
    from mgt470_analyst.schemas.raw_input import RawInput

    report = " ".join(f"https://example.com/source-{index}" for index in range(10))
    brief = GPTResearcherAdapter()._normalize(
        report=report,
        sources=["https://translate.yandex.com/"],
        raw_input=RawInput(company_name="Notion"),
    )

    assert len(brief.sources) == 10
    assert "https://translate.yandex.com/" not in [source.url_or_path for source in brief.sources]
