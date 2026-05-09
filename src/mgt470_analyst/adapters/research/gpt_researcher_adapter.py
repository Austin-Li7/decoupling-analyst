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
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from mgt470_analyst.adapters.research.base import ResearchAdapter
from mgt470_analyst.io.json_artifacts import write_json_artifact
from mgt470_analyst.llm.client import record_external_llm_cost
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


class RetrievalEmptyError(RuntimeError):
    """Raised when GPT Researcher completes without retrieving any source URLs."""


class RetrievalAllDeadError(RuntimeError):
    """Raised when retrieved URLs all fail the URL liveness gate."""


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

    def research_for_run(
        self,
        raw_input: RawInput,
        *,
        run_id: str,
        run_dir: Path,
    ) -> ResearchBrief:
        return asyncio.run(
            self._research_async(raw_input, run_id=run_id, run_dir=run_dir)
        )

    async def _research_async(
        self,
        raw_input: RawInput,
        *,
        run_id: str = "",
        run_dir: Path | None = None,
    ) -> ResearchBrief:
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
        visited_urls = [str(url) for url in list(getattr(researcher, "visited_urls", []) or [])]
        # Grounding uses research_sources, not visited_urls. In Austin's fork,
        # Tavily prefetched content is recorded in research_sources at
        # gpt_researcher/skills/researcher.py:779-789 but does not update
        # visited_urls, while scrape-path sources do. This fork-side bookkeeping
        # discrepancy could be upstreamed as a small PR.
        research_sources = await _get_research_sources(researcher)
        research_sources_urls = _extract_research_source_urls(research_sources)
        if not research_sources_urls:
            raise RetrievalEmptyError(
                "GPT Researcher completed conduct_research() with 0 research_sources URLs; "
                "refusing to write an ungrounded report."
            )
        report = await _maybe_await(researcher.write_report())
        record_external_llm_cost(
            "gpt_researcher_internal",
            cost_usd=float(getattr(researcher, "research_costs", 0.0) or 0.0),
            model="gpt-researcher",
            note=(
                "GPT Researcher's own LLM calls (sub-query gen, scrape "
                "summarization, report writing)"
            ),
        )
        source_urls = await _maybe_await(researcher.get_source_urls())
        provenance_path = run_dir / "research_provenance.json" if run_dir else None
        return self._normalize(
            str(report),
            source_urls,
            raw_input,
            run_id=run_id,
            provenance_path=provenance_path,
            research_sources_urls=research_sources_urls,
            visited_urls_from_retriever=visited_urls,
        )

    def _build_query(self, raw_input: RawInput) -> str:
        ticker = f" ({raw_input.ticker})" if raw_input.ticker else ""
        website = f" {raw_input.website}" if raw_input.website else ""
        query = (
            "Teixeira-style digital disruption analysis of "
            f"{raw_input.company_name}{ticker}{website}: customer value chain, "
            "decoupling, weak links, monetization, competitors, customer pain "
            "points, recent strategic moves."
        )
        if len(query) >= 380:
            raise ValueError(f"Query exceeds Tavily limit: {len(query)} chars")
        return query

    def _normalize(
        self,
        report: str,
        sources: Any,
        raw_input: RawInput,
        *,
        run_id: str = "",
        provenance_path: Path | None = None,
        research_sources_urls: list[str] | None = None,
        visited_urls_from_retriever: list[str] | None = None,
    ) -> ResearchBrief:
        research_sources_urls = research_sources_urls or []
        visited_urls_from_retriever = visited_urls_from_retriever or []
        report_cited_urls = _extract_source_urls(report)
        searched_urls = _extract_source_urls(sources)
        union_pre_liveness = _dedupe_urls(research_sources_urls)
        urls, dropped = _filter_live_urls_with_results(union_pre_liveness)
        if research_sources_urls and not urls:
            raise RetrievalAllDeadError(
                "GPT Researcher retrieved URLs, but every URL failed the liveness gate."
            )
        _write_research_provenance_if_enabled(
            path=provenance_path,
            company_name=raw_input.company_name,
            run_id=run_id,
            searched_urls=searched_urls,
            research_sources_urls=research_sources_urls,
            visited_urls_from_retriever=visited_urls_from_retriever,
            report_cited_urls=report_cited_urls,
            union_pre_liveness=union_pre_liveness,
            post_liveness_kept_urls=urls,
            post_liveness_dropped=dropped,
        )

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
        if os.getenv("TAVILY_API_KEY"):
            os.environ["RETRIEVER"] = "tavily"
        elif os.getenv("MGT470_ALLOW_UNGROUNDED_RESEARCH") == "1":
            os.environ["RETRIEVER"] = "duckduckgo"
            LOGGER.warning(
                "DuckDuckGo retriever is known to return 0 results in many "
                "environments; runs may produce ungrounded briefs. Set TAVILY_API_KEY "
                "for grounded research."
            )
        else:
            raise RuntimeError(
                "No TAVILY_API_KEY set; live research will not be grounded. Set "
                "TAVILY_API_KEY or MGT470_ALLOW_UNGROUNDED_RESEARCH=1 to override."
            )
        os.environ.setdefault("MAX_ITERATIONS", str(self.max_iterations))
        os.environ.setdefault("MAX_SUBTOPICS", str(self.max_subtopics))
        # Do not set MAX_SEARCH_RESULTS_PER_QUERY here. Tavily's defaults are
        # tuned by tier; the old DDG-era clamp made grounded runs too shallow
        # and contributed to one-URL retrieval.


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


async def _get_research_sources(researcher: Any) -> list[Any]:
    get_research_sources = getattr(researcher, "get_research_sources", None)
    if callable(get_research_sources):
        return list(await _maybe_await(get_research_sources()) or [])
    return list(getattr(researcher, "research_sources", []) or [])


def _extract_research_source_urls(research_sources: list[Any]) -> list[str]:
    urls: list[str] = []
    for source in research_sources:
        if isinstance(source, dict) and source.get("url"):
            urls.append(str(source["url"]))
    return _dedupe_urls(urls)


def _filter_live_urls(urls: list[str]) -> list[str]:
    kept, _dropped = _filter_live_urls_with_results(urls)
    return kept


def _filter_live_urls_with_results(
    urls: list[str],
) -> tuple[list[str], list[_URLLivenessResult]]:
    if not urls:
        return [], []
    if os.getenv("MGT470_URL_LIVENESS", "1") == "0":
        LOGGER.info("URL liveness gate disabled by MGT470_URL_LIVENESS=0")
        return urls, []

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
    return kept, dropped


def _union_pre_liveness_urls(
    report_cited_urls: list[str],
    searched_urls: list[str],
) -> list[str]:
    urls = report_cited_urls.copy()
    if len(urls) < 10:
        for source_url in searched_urls:
            if source_url not in urls:
                urls.append(source_url)
    return urls


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _write_research_provenance_if_enabled(
    *,
    path: Path | None,
    company_name: str,
    run_id: str,
    searched_urls: list[str],
    research_sources_urls: list[str],
    visited_urls_from_retriever: list[str],
    report_cited_urls: list[str],
    union_pre_liveness: list[str],
    post_liveness_kept_urls: list[str],
    post_liveness_dropped: list[_URLLivenessResult],
) -> None:
    if path is None:
        return
    artifact = _build_research_provenance(
        company_name=company_name,
        run_id=run_id,
        searched_urls=searched_urls,
        research_sources_urls=research_sources_urls,
        visited_urls_from_retriever=visited_urls_from_retriever,
        report_cited_urls=report_cited_urls,
        union_pre_liveness=union_pre_liveness,
        post_liveness_kept_urls=post_liveness_kept_urls,
        post_liveness_dropped=post_liveness_dropped,
    )
    write_json_artifact(path, artifact)
    LOGGER.info(
        "Research provenance dump written: %s (report_only_ratio=%.2f)",
        path,
        artifact["report_only_url_ratio"],
    )


def _build_research_provenance(
    *,
    company_name: str,
    run_id: str,
    searched_urls: list[str],
    research_sources_urls: list[str],
    visited_urls_from_retriever: list[str],
    report_cited_urls: list[str],
    union_pre_liveness: list[str],
    post_liveness_kept_urls: list[str],
    post_liveness_dropped: list[_URLLivenessResult],
) -> dict[str, Any]:
    research_sources_set = set(research_sources_urls)
    visited_set = set(visited_urls_from_retriever)
    report_urls = [
        {
            "url": url,
            "provenance": "in_search_results"
            if url in research_sources_set
            else "only_in_report",
        }
        for url in report_cited_urls
    ]
    report_urls_in_search_results = sum(
        1 for item in report_urls if item["provenance"] == "in_search_results"
    )
    report_urls_only_in_report = len(report_urls) - report_urls_in_search_results
    return {
        "company_name": company_name,
        "run_id": run_id,
        "searched_urls_count": len(searched_urls),
        "report_cited_urls_count": len(report_cited_urls),
        "union_pre_liveness_count": len(union_pre_liveness),
        "report_urls_in_search_results": report_urls_in_search_results,
        "report_urls_only_in_report": report_urls_only_in_report,
        "report_only_url_ratio": round(
            report_urls_only_in_report / len(report_urls), 3
        )
        if report_urls
        else 0.0,
        "searched_urls": searched_urls,
        "research_sources_urls": research_sources_urls,
        "visited_urls_from_retriever": visited_urls_from_retriever,
        "prefetched_url_count": len(
            [url for url in research_sources_urls if url not in visited_set]
        ),
        "report_cited_urls": report_urls,
        "post_liveness_kept_urls": post_liveness_kept_urls,
        "post_liveness_dropped_urls": [
            {
                "url": result.url,
                "status": result.status,
                "was_in_search_results": result.url in research_sources_set,
            }
            for result in post_liveness_dropped
        ],
    }


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
