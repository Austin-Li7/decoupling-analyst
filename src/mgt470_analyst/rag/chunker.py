from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Chunk:
    """A retrievable unit of a Markdown note.

    ``heading_trail`` is the path of headings leading to this chunk
    (e.g. ``("MGT470 全课知识串联", "1. 最核心框架", "1.1 什么是 CVC")``),
    used both for source attribution in prompts and for lexical re-ranking
    on company-name match.
    """

    text: str
    source_path: str
    heading_trail: tuple[str, ...]
    chunk_index: int
    corpus: str = "austin"


def chunk_markdown(
    text: str,
    source_path: str,
    *,
    max_chars: int = 3200,
    min_chars: int = 400,
) -> list[Chunk]:
    """Split a Markdown document into heading-bounded chunks.

    Boundaries: each H1/H2/H3 starts a new chunk if the running buffer is
    already ``>= min_chars``. Code fences are respected (no false-positive
    headings inside ```...```). YAML frontmatter is stripped. Sections
    longer than ``max_chars`` are split at paragraph (\\n\\n) boundaries.
    """
    text = _FRONTMATTER_RE.sub("", text, count=1)

    chunks: list[Chunk] = []
    current: list[str] = []
    trail: list[tuple[int, str]] = []
    in_code = False

    def buffer_text() -> str:
        return "\n".join(current).strip()

    def emit() -> None:
        body = buffer_text()
        if not body:
            return
        for piece in _split_oversize(body, max_chars):
            chunks.append(
                Chunk(
                    text=piece,
                    source_path=source_path,
                    heading_trail=tuple(h for _, h in trail),
                    chunk_index=len(chunks),
                )
            )

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            current.append(line)
            continue

        match = None if in_code else _HEADING_RE.match(line)
        if match and len(match.group(1)) <= 3:
            level = len(match.group(1))
            heading = match.group(2).strip()
            if len(buffer_text()) >= min_chars:
                emit()
                current = []
            trail = [(lv, h) for (lv, h) in trail if lv < level]
            trail.append((level, heading))
            current.append(line)
        else:
            current.append(line)

    emit()
    return chunks


def _split_oversize(body: str, max_chars: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    pieces: list[str] = []
    buf: list[str] = []
    size = 0
    for para in _split_paragraph_or_lines(body, max_chars):
        para_size = len(para) + 2
        if size + para_size > max_chars and buf:
            pieces.append("\n\n".join(buf).strip())
            buf = [para]
            size = para_size
        else:
            buf.append(para)
            size += para_size
    if buf:
        pieces.append("\n\n".join(buf).strip())
    return [p for p in pieces if p]


def _split_paragraph_or_lines(body: str, max_chars: int) -> list[str]:
    units: list[str] = []
    for para in body.split("\n\n"):
        if len(para) <= max_chars:
            units.append(para)
            continue
        line_buf: list[str] = []
        line_size = 0
        for line in para.splitlines():
            line_len = len(line) + 1
            if line_size + line_len > max_chars and line_buf:
                units.append("\n".join(line_buf))
                line_buf = [line]
                line_size = line_len
            else:
                line_buf.append(line)
                line_size += line_len
        if line_buf:
            units.append("\n".join(line_buf))
    return units
