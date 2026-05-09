"""GPT Researcher-backed live web research adapter."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse

import httpx

from mgt470_analyst.adapters.research.base import ResearchAdapter
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief, ResearchSource

DEFAULT_MAX_ITERATIONS = 2
DEFAULT_MAX_SUBTOPICS = 3
URL_LIVENESS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
URL_LIVENESS_TIMEOUT_SECONDS = 10.0
URL_LIVENESS_MAX_WORKERS = 8
_HEAD_FALLBACK_STATUS_CODES = {405, 501}
_HEAD_FALLBACK_STATUS_LABELS = {str(status) for status in _HEAD_FALLBACK_STATUS_CODES}
_HEAD_FALLBACK_ERROR_LABELS = {
    "timeout",
    "connection error",
    "ssl error",
    "request error",
}
_URL_RE = re.compile(r"https?://[^\s\])>\"']+")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _URLLivenessResult:
    url: str
    live: bool
    status: str


class GPTResearcherAdapter(ResearchAdapter):
    """Wrap Austin's gpt-researcher fork behind the sync ResearchAdapter API."""

    def __init__(
        self,
        *,
        report_type: str = "research_report",
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_subtopics: int = DEFAULT_MAX_SUBTOPICS,
    ) -> None:
        self.report_type = report_type
        self.max_iterations = max_iterations
        self.max_subtopics = max_subtopics

    def research(self, raw_input: RawInput) -> ResearchBrief:
        return asyncio.run(self._research_async(raw_input))

    async def _research_async(self, raw_input: RawInput) -> ResearchBrief:
        gpt_researcher = _load_gpt_researcher()
        query = self._build_query(raw_input)
        self._apply_cost_guardrails()
        researcher = gpt_researcher(
            query=query,
            report_type=self.report_type,
            config_path=None,
            max_subtopics=self.max_subtopics,
        )

        await _maybe_await(researcher.conduct_research())
        report = await _maybe_await(researcher.write_report())
        source_urls = await _maybe_await(researcher.get_source_urls())
        return self._normalize(str(report), source_urls, raw_input)

    def _build_query(self, raw_input: RawInput) -> str:
        ticker = f" Ticker: {raw_input.ticker}." if raw_input.ticker else ""
        website = f" Website: {raw_input.website}." if raw_input.website else ""
        return (
            f"Research {raw_input.company_name} for a Teixeira-style MGT470 digital "
            f"disruption analysis.{ticker}{website} Use broad public web sources: "
            "official company pages, pricing pages, docs or API pages, credible news, "
            "reviews, customer discussions, and competitor comparisons. Do not add site: "
            "restrictions or narrow boolean operators; DuckDuckGo should be able to find "
            "ordinary public pages. Gather cited facts about the customer value chain "
            "(customer, job-to-be-done, friction), monetization and unit economics if "
            "disclosed, competitors and bundles, signs of decoupling, reported customer "
            "pain points, and recent strategic moves. Return real URLs for every source."
        )

    def _normalize(
        self,
        report: str,
        sources: Any,
        raw_input: RawInput,
    ) -> ResearchBrief:
        urls = _extract_source_urls(report)
        if len(urls) < 10:
            for source_url in _extract_source_urls(sources):
                if source_url not in urls:
                    urls.append(source_url)
        urls = _filter_live_urls(urls)

        sentences = _extract_sentences(report)
        key_claims = sentences[: max(len(urls), 1)]
        if not key_claims:
            key_claims = [
                f"GPT Researcher returned a cited research report for {raw_input.company_name}."
            ]

        research_sources = [
            ResearchSource(
                id=f"S{index}",
                title=_title_from_url(url),
                url_or_path=url,
                source_type=_source_type_from_url(url),
                retrieved_at=date.today().isoformat(),
                reliability="medium",
                key_claims=[key_claims[(index - 1) % len(key_claims)]],
            )
            for index, url in enumerate(urls, start=1)
        ]

        return ResearchBrief(
            company_name=raw_input.company_name,
            research_summary=_summary_from_report(report, raw_input.company_name),
            sources=research_sources,
            open_questions=[
                "Validate the most strategically important claims against primary sources.",
                "Check whether recent customer pain points reflect durable behavior change.",
            ],
            conflicts=[],
        )

    def _apply_cost_guardrails(self) -> None:
        # Keep live research bounded near Austin's Phase 2 target of <= $1 per
        # research phase. GPT Researcher reads these env vars in current forks.
        if not os.getenv("TAVILY_API_KEY"):
            os.environ.setdefault("RETRIEVER", "duckduckgo")
        os.environ.setdefault("MAX_ITERATIONS", str(self.max_iterations))
        os.environ.setdefault("MAX_SUBTOPICS", str(self.max_subtopics))
        os.environ.setdefault("MAX_SEARCH_RESULTS_PER_QUERY", "5")


def _load_gpt_researcher() -> Any:
    try:
        from gpt_researcher import GPTResearcher
    except ImportError as exc:
        raise RuntimeError(
            "gpt-researcher is not installed. Install with: "
            "pip install 'gpt-researcher @ "
            "git+https://github.com/Austin-Li7/gpt-researcher.git'"
        ) from exc
    return GPTResearcher


def _filter_live_urls(urls: list[str]) -> list[str]:
    if not urls:
        return []
    if os.getenv("MGT470_URL_LIVENESS", "1") == "0":
        LOGGER.info("URL liveness gate disabled by MGT470_URL_LIVENESS=0")
        return urls

    worker_count = min(URL_LIVENESS_MAX_WORKERS, len(urls))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(_check_url_liveness, urls))

    kept = [result.url for result in results if result.live]
    dropped = [result for result in results if not result.live]
    dropped_summary = ", ".join(
        f"{result.url} -> {result.status}" for result in dropped[:5]
    )
    if len(dropped) > 5:
        dropped_summary = f"{dropped_summary}, ... (+{len(dropped) - 5} more)"
    LOGGER.info(
        "URL liveness gate: kept %s/%s (dropped: %s)",
        len(kept),
        len(urls),
        dropped_summary or "none",
    )
    if len(kept) < 3:
        LOGGER.warning(
            "URL liveness gate: fewer than 3 live source URLs survived (%s/%s). "
            "Letting thin brief through.",
            len(kept),
            len(urls),
        )
    return kept


def _check_url_liveness(url: str) -> _URLLivenessResult:
    headers = {
        "User-Agent": URL_LIVENESS_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=URL_LIVENESS_TIMEOUT_SECONDS,
            headers=headers,
        ) as client:
            head_status = _try_head(client, url)
            fallback_labels = _HEAD_FALLBACK_STATUS_LABELS | _HEAD_FALLBACK_ERROR_LABELS
            if head_status.live or head_status.status not in fallback_labels:
                return head_status
            return _try_get_without_body(client, url)
    except httpx.TimeoutException:
        return _URLLivenessResult(url=url, live=False, status="timeout")
    except httpx.ConnectError:
        return _URLLivenessResult(url=url, live=False, status="connection error")
    except httpx.TransportError as exc:
        status = "ssl error" if "ssl" in str(exc).lower() else "request error"
        return _URLLivenessResult(url=url, live=False, status=status)
    except httpx.HTTPError:
        return _URLLivenessResult(url=url, live=False, status="request error")


def _try_head(client: httpx.Client, url: str) -> _URLLivenessResult:
    try:
        response = client.head(url)
        response.close()
    except httpx.TimeoutException:
        return _URLLivenessResult(url=url, live=False, status="timeout")
    except httpx.ConnectError:
        return _URLLivenessResult(url=url, live=False, status="connection error")
    except httpx.TransportError as exc:
        status = "ssl error" if "ssl" in str(exc).lower() else "request error"
        return _URLLivenessResult(url=url, live=False, status=status)
    except httpx.HTTPError:
        return _URLLivenessResult(url=url, live=False, status="request error")
    return _result_from_status(url, response.status_code)


def _try_get_without_body(client: httpx.Client, url: str) -> _URLLivenessResult:
    try:
        with client.stream("GET", url, headers={"Range": "bytes=0-0"}) as response:
            return _result_from_status(url, response.status_code)
    except httpx.TimeoutException:
        return _URLLivenessResult(url=url, live=False, status="timeout")
    except httpx.ConnectError:
        return _URLLivenessResult(url=url, live=False, status="connection error")
    except httpx.TransportError as exc:
        status = "ssl error" if "ssl" in str(exc).lower() else "request error"
        return _URLLivenessResult(url=url, live=False, status=status)
    except httpx.HTTPError:
        return _URLLivenessResult(url=url, live=False, status="request error")


def _result_from_status(url: str, status_code: int) -> _URLLivenessResult:
    return _URLLivenessResult(
        url=url,
        live=200 <= status_code < 300,
        status=str(status_code),
    )


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _extract_source_urls(sources: Any) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for candidate in _iter_source_candidates(sources):
        for match in _URL_RE.findall(str(candidate)):
            url = match.rstrip(".,;")
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def _iter_source_candidates(sources: Any) -> Iterable[Any]:
    if sources is None:
        return []
    if isinstance(sources, str):
        return [sources]
    if isinstance(sources, dict):
        values: list[Any] = []
        for key in ("url", "href", "link", "source", "sources"):
            value = sources.get(key)
            if isinstance(value, list):
                values.extend(value)
            elif value:
                values.append(value)
        return values or list(sources.values())
    if isinstance(sources, Iterable):
        return sources
    return [sources]


def _extract_sentences(report: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", report).strip()
    sentences = [
        sentence.strip(" -")
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
        if len(sentence.strip()) >= 40
    ]
    return sentences[:20]


def _summary_from_report(report: str, company_name: str) -> str:
    sentences = _extract_sentences(report)
    if sentences:
        return " ".join(sentences[:4])
    return f"GPT Researcher produced a live web research report for {company_name}."


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path:
        return f"{parsed.netloc} / {path.split('/')[-1][:80]}"
    return parsed.netloc or url


def _source_type_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if "sec.gov" in host or "investor" in host or "annual" in path:
        return "filing"
    if path.endswith((".pdf", ".ppt", ".pptx")):
        return "deck"
    return "article"
