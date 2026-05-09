"""Offline tests for the RAG layer.

These never touch ChromaDB or the OpenAI embedding API: the chunker is
pure-Python on a string, and the retriever's contract is to return ``[]``
when the index dir is missing or no API key is set — both true in tests.
"""

from __future__ import annotations

from pathlib import Path

from mgt470_analyst.llm.prompts import render_methodology_context
from mgt470_analyst.rag.chunker import Chunk, chunk_markdown
from mgt470_analyst.rag.retriever import MethodologyRetriever, RankedChunk, merge_ranked_chunks


def test_chunk_markdown_strips_frontmatter_and_splits_on_headings():
    text = """\
---
title: Sample
tag: x
---

# Top

Intro paragraph.

## Section A

Body of section A. Lorem ipsum dolor sit amet, the section is long enough
to clear the min_chars threshold so the next heading actually starts a new
chunk and the chunker doesn't merge them into one block. Adding a bit
more padding text here so we definitely cross 400 chars and the boundary
fires reliably across platforms.

## Section B

Body of section B with its own content that is also padded out past the
minimum-chars threshold so the chunker treats it as a distinct chunk and
we can assert ordering on heading_trail without flakiness.
"""
    chunks = chunk_markdown(text, "sample.md", min_chars=80)

    assert len(chunks) >= 2
    # Frontmatter is gone — no chunk should start with "---".
    for chunk in chunks:
        assert "title: Sample" not in chunk.text
    # Heading trail tracks the H2 we're inside.
    assert any("Section A" in c.heading_trail[-1] for c in chunks)
    assert any("Section B" in c.heading_trail[-1] for c in chunks)


def test_chunk_markdown_ignores_headings_inside_code_fences():
    text = """\
# Top
Body line one is short.

```python
# This is a comment, not a heading
def f():
    pass
```

## Real heading
Body two.
"""
    chunks = chunk_markdown(text, "code.md", min_chars=10)
    # The code-fence "# This is a comment" must not have started a chunk.
    all_headings = [h for c in chunks for h in c.heading_trail]
    assert all("This is a comment, not a heading" not in h for h in all_headings)


def test_chunk_markdown_splits_long_transcript_without_blank_lines():
    text = "# Talk\n\n" + "\n".join(f"caption line {i} with no blank paragraph" for i in range(50))

    chunks = chunk_markdown(text, "talk.md", max_chars=200, min_chars=20)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 220 for chunk in chunks)


def test_retriever_returns_empty_when_index_missing(tmp_path: Path):
    # Persist dir does not exist on disk → retriever returns [] silently.
    retriever = MethodologyRetriever(persist_dir=tmp_path / "nonexistent")
    chunks = retriever.retrieve_for_module("cvc", "OLX Brazil", perspective="transitioning")
    assert chunks == []


def test_render_methodology_context_empty_returns_empty_string():
    assert render_methodology_context([]) == ""


def test_render_methodology_context_formats_chunks():
    chunks = [
        Chunk(
            text="OLX should preserve free posting.",
            source_path="MGT470-chatgpt/OLX.md",
            heading_trail=("OLX", "1. Core engine"),
            chunk_index=0,
        )
    ]
    rendered = render_methodology_context(chunks)
    assert "COURSE CONTEXT" in rendered
    assert "OLX should preserve free posting." in rendered
    assert "MGT470-chatgpt/OLX.md" in rendered
    assert "1. Core engine" in rendered


def test_render_methodology_context_groups_primary_before_course():
    chunks = [
        Chunk(
            text="Austin note about preserving free posting.",
            source_path="MGT470-chatgpt/OLX.md",
            heading_trail=("OLX",),
            chunk_index=0,
            corpus="austin",
        ),
        Chunk(
            text="Teixeira calls this a value-eroding activity.",
            source_path="decoupling_io/value-eroding.md",
            heading_trail=("Value erosion",),
            chunk_index=0,
            corpus="primary",
        ),
    ]

    rendered = render_methodology_context(chunks)

    primary_pos = rendered.index("PRIMARY SOURCE")
    course_pos = rendered.index("COURSE CONTEXT")
    assert primary_pos < course_pos
    assert "Teixeira's own writing/speaking" in rendered
    assert "Austin's MGT470 notes" in rendered
    assert "attribute at least one Teixeira framework phrase" in rendered


def test_merge_ranked_chunks_boosts_primary_distances():
    austin_chunk = Chunk(
        text="Austin note",
        source_path="notes.md",
        heading_trail=(),
        chunk_index=0,
        corpus="austin",
    )
    primary_chunk = Chunk(
        text="Primary source",
        source_path="talk.md",
        heading_trail=(),
        chunk_index=0,
        corpus="primary",
    )

    merged = merge_ranked_chunks(
        [
            RankedChunk(chunk=austin_chunk, distance=0.40),
            RankedChunk(chunk=primary_chunk, distance=0.55),
        ],
        top_k=2,
    )

    assert merged == [primary_chunk, austin_chunk]
