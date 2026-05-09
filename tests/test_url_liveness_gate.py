import logging
from collections.abc import Mapping

import httpx
import pytest

from mgt470_analyst.adapters.research import gpt_researcher_adapter
from mgt470_analyst.adapters.research.gpt_researcher_adapter import (
    GPTResearcherAdapter,
    RetrievalAllDeadError,
)
from mgt470_analyst.schemas.raw_input import RawInput


def _normalize_with_urls(urls: list[str]):
    return GPTResearcherAdapter()._normalize(
        report=" ".join(urls),
        sources=[],
        raw_input=RawInput(company_name="Notion"),
        visited_urls_from_retriever=urls,
    )


def _patch_http_client(
    monkeypatch: pytest.MonkeyPatch,
    routes: Mapping[tuple[str, str], int | Exception],
):
    calls: list[tuple[str, str]] = []

    class FakeStream:
        def __init__(self, response: httpx.Response) -> None:
            self.response = response

        def __enter__(self) -> httpx.Response:
            return self.response

        def __exit__(self, exc_type, exc, traceback) -> None:
            self.response.close()

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.timeout = kwargs.get("timeout")
            self.follow_redirects = kwargs.get("follow_redirects")
            self.headers = kwargs.get("headers")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            pass

        def head(self, url: str) -> httpx.Response:
            return self._response("HEAD", url)

        def stream(self, method: str, url: str, **kwargs) -> FakeStream:
            return FakeStream(self._response(method, url))

        def _response(self, method: str, url: str) -> httpx.Response:
            calls.append((method, url))
            result = routes[(method, url)]
            if isinstance(result, Exception):
                raise result
            return httpx.Response(result, request=httpx.Request(method, url))

    monkeypatch.setattr(gpt_researcher_adapter.httpx, "Client", FakeClient)
    return calls


def test_url_liveness_gate_keeps_all_healthy_urls_in_order(monkeypatch) -> None:
    monkeypatch.delenv("MGT470_URL_LIVENESS", raising=False)
    urls = [
        "https://example.com/one",
        "https://example.com/two",
        "https://example.com/three",
    ]
    _patch_http_client(monkeypatch, {("HEAD", url): 200 for url in urls})

    brief = _normalize_with_urls(urls)

    assert [source.url_or_path for source in brief.sources] == urls


def test_url_liveness_gate_drops_dead_urls_and_preserves_survivor_order(
    monkeypatch, caplog
) -> None:
    monkeypatch.delenv("MGT470_URL_LIVENESS", raising=False)
    urls = [
        "https://example.com/healthy-first",
        "https://example.com/not-found",
        "https://example.com/timeout",
        "https://example.com/healthy-second",
        "https://example.com/server-error",
    ]
    _patch_http_client(
        monkeypatch,
        {
            ("HEAD", urls[0]): 200,
            ("HEAD", urls[1]): 404,
            ("HEAD", urls[2]): httpx.TimeoutException("timed out"),
            ("GET", urls[2]): httpx.TimeoutException("timed out"),
            ("HEAD", urls[3]): 204,
            ("HEAD", urls[4]): 500,
        },
    )
    caplog.set_level(logging.INFO, logger=gpt_researcher_adapter.__name__)

    brief = _normalize_with_urls(urls)

    assert [source.url_or_path for source in brief.sources] == [urls[0], urls[3]]
    assert "URL liveness gate: kept 2/5" in caplog.text
    assert "https://example.com/not-found -> 404" in caplog.text
    assert "https://example.com/timeout -> timeout" in caplog.text


def test_url_liveness_gate_falls_back_to_get_when_head_is_not_allowed(
    monkeypatch,
) -> None:
    monkeypatch.delenv("MGT470_URL_LIVENESS", raising=False)
    urls = ["https://example.com/head-blocked"]
    calls = _patch_http_client(
        monkeypatch,
        {
            ("HEAD", urls[0]): 405,
            ("GET", urls[0]): 200,
        },
    )

    brief = _normalize_with_urls(urls)

    assert [source.url_or_path for source in brief.sources] == urls
    assert calls == [("HEAD", urls[0]), ("GET", urls[0])]


def test_url_liveness_gate_can_be_disabled_with_env_var(
    monkeypatch, caplog
) -> None:
    monkeypatch.setenv("MGT470_URL_LIVENESS", "0")
    urls = [
        "https://example.com/dead",
        "https://example.com/also-dead",
    ]
    calls = _patch_http_client(monkeypatch, {})
    caplog.set_level(logging.INFO, logger=gpt_researcher_adapter.__name__)

    brief = _normalize_with_urls(urls)

    assert [source.url_or_path for source in brief.sources] == urls
    assert calls == []
    assert "URL liveness gate disabled by MGT470_URL_LIVENESS=0" in caplog.text


def test_url_liveness_gate_all_retrieved_urls_dead_raises_and_warns(
    monkeypatch, caplog
) -> None:
    monkeypatch.delenv("MGT470_URL_LIVENESS", raising=False)
    urls = [
        "https://example.com/not-found",
        "https://example.com/server-error",
    ]
    _patch_http_client(
        monkeypatch,
        {
            ("HEAD", urls[0]): 404,
            ("HEAD", urls[1]): 500,
        },
    )
    caplog.set_level(logging.INFO, logger=gpt_researcher_adapter.__name__)

    with pytest.raises(RetrievalAllDeadError):
        _normalize_with_urls(urls)

    assert "URL liveness gate: kept 0/2" in caplog.text
    assert "fewer than 3 live source URLs survived" in caplog.text
