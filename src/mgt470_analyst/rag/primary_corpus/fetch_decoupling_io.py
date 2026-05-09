from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from mgt470_analyst.rag.primary_corpus.sources import SourceSpec, load_sources
from mgt470_analyst.rag.primary_corpus.util import slugify_text, slugify_url, write_markdown


@dataclass(frozen=True)
class HarvestResult:
    written: list[Path]
    skipped: list[str]


def harvest_text_sources(
    *,
    output_dir: Path | str,
    sources_path: Path | str | None = None,
    source_filter: str | None = None,
    timeout: float = 30.0,
) -> HarvestResult:
    """Fetch article/book source pages and save extracted text as Markdown."""
    sources = load_sources(sources_path).text_sources
    if source_filter:
        sources = [s for s in sources if s.source == source_filter]

    out_path = Path(output_dir)
    written: list[Path] = []
    skipped: list[str] = []
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        for source in sources:
            try:
                response = client.get(source.url).raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type or source.url.lower().endswith(".pdf"):
                    body = pdf_to_markdown(response.content)
                else:
                    body = html_to_markdown(response.text)
            except Exception as exc:
                skipped.append(f"{source.url}: {exc}")
                continue

            if len(body.strip()) < 200:
                skipped.append(f"{source.url}: extracted text too short")
                continue

            folder = _folder_for(source)
            slug = slugify_text(source.title) if source.title else slugify_url(source.url)
            path = out_path / folder / f"{slug}.md"
            write_markdown(
                path,
                title=source.title,
                url=source.url,
                source=source.source,
                body=body,
            )
            written.append(path)
    return HarvestResult(written=written, skipped=skipped)


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.body or soup
    lines: list[str] = []
    for node in root.find_all(["h1", "h2", "h3", "p", "li"], recursive=True):
        text = " ".join(node.get_text(" ", strip=True).split())
        if not text:
            continue
        if node.name == "h1":
            lines.append(f"# {text}")
        elif node.name == "h2":
            lines.append(f"## {text}")
        elif node.name == "h3":
            lines.append(f"### {text}")
        elif node.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()


def pdf_to_markdown(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    lines: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            lines.append(f"## Page {index}")
            lines.append("")
            lines.append(text)
            lines.append("")
    return "\n".join(lines).strip()


def _folder_for(source: SourceSpec) -> str:
    if source.kind == "book":
        return "books"
    if source.source == "decoupling-io":
        return "decoupling_io"
    return "articles"
