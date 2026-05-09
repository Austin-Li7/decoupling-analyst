from __future__ import annotations

import json
import os
from pathlib import Path

from mgt470_analyst.rag.chunker import chunk_markdown

AUSTIN_COLLECTION_NAME = "austin_notes"
PRIMARY_COLLECTION_NAME = "primary_teixeira"
COLLECTION_NAME = AUSTIN_COLLECTION_NAME
EMBEDDING_MODEL = "text-embedding-3-small"


def default_persist_dir() -> Path:
    return Path.home() / ".cache" / "mgt470-analyst" / "notes_index"


def default_notes_dir() -> Path:
    """Resolve the notes corpus directory.

    Order: ``MGT470_NOTES_DIR`` env var, then ``./MGT470`` relative to the
    current working directory. The corpus itself is gitignored — Austin
    keeps it locally; the env var is the supported override for sessions
    that run from a worktree where the notes aren't present.
    """
    env = os.environ.get("MGT470_NOTES_DIR")
    if env:
        return Path(env).expanduser()
    return Path.cwd() / "MGT470"


def default_primary_corpus_dir() -> Path:
    return Path.cwd() / "data" / "teixeira_corpus"


def build_index(
    notes_dir: Path | str | None = None,
    *,
    primary_dir: Path | str | None = None,
    persist_dir: Path | str | None = None,
) -> dict:
    """Idempotent re-index of Austin notes and optional primary corpus.

    Skips files whose mtime hasn't changed since the last run. Primary
    Teixeira markdown is indexed into a separate ChromaDB collection when
    ``data/teixeira_corpus`` exists.
    """
    notes_path = Path(notes_dir) if notes_dir else default_notes_dir()
    primary_path = Path(primary_dir) if primary_dir else default_primary_corpus_dir()
    persist_path = Path(persist_dir) if persist_dir else default_persist_dir()
    if not notes_path.is_dir():
        raise FileNotFoundError(
            f"Notes directory not found: {notes_path}. "
            "Set MGT470_NOTES_DIR to the absolute path of your MGT470/ folder."
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to embed notes. "
            "Put it in .env at the project root or export it before running."
        )

    persist_path.mkdir(parents=True, exist_ok=True)

    import chromadb
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    client = chromadb.PersistentClient(path=str(persist_path))
    embed_fn = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBEDDING_MODEL)

    austin_summary = _index_markdown_dir(
        client=client,
        embed_fn=embed_fn,
        source_dir=notes_path,
        collection_name=AUSTIN_COLLECTION_NAME,
        corpus="austin",
        state_path=persist_path / "index_state.json",
    )
    primary_summary = {
        "files_indexed": 0,
        "chunks_added": 0,
        "stale_removed": 0,
        "source_dir": str(primary_path),
        "collection": PRIMARY_COLLECTION_NAME,
    }
    if primary_path.is_dir():
        primary_summary = _index_markdown_dir(
            client=client,
            embed_fn=embed_fn,
            source_dir=primary_path,
            collection_name=PRIMARY_COLLECTION_NAME,
            corpus="primary",
            state_path=persist_path / "primary_index_state.json",
        )

    return {
        "files_indexed": austin_summary["files_indexed"],
        "chunks_added": austin_summary["chunks_added"],
        "persist_dir": str(persist_path),
        "notes_dir": str(notes_path),
        "stale_removed": austin_summary["stale_removed"],
        "primary_files_indexed": primary_summary["files_indexed"],
        "primary_chunks_added": primary_summary["chunks_added"],
        "primary_stale_removed": primary_summary["stale_removed"],
        "primary_dir": str(primary_path),
    }


def _index_markdown_dir(
    *,
    client,
    embed_fn,
    source_dir: Path,
    collection_name: str,
    corpus: str,
    state_path: Path,
) -> dict:
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
    )

    state: dict[str, float] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}

    files_indexed = 0
    chunks_added = 0
    seen_files: set[str] = set()

    for md_path in sorted(source_dir.rglob("*.md")):
        rel = str(md_path.relative_to(source_dir))
        seen_files.add(rel)
        mtime = md_path.stat().st_mtime
        if state.get(rel) == mtime:
            continue

        existing = collection.get(where={"source_path": rel})
        existing_ids = existing.get("ids") or []
        if existing_ids:
            collection.delete(ids=existing_ids)

        text = md_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, rel)
        if chunks:
            ids = [f"{corpus}::{rel}::{c.chunk_index}" for c in chunks]
            documents = [c.text for c in chunks]
            metadatas = [
                {
                    "source_path": c.source_path,
                    "heading_trail": " > ".join(c.heading_trail),
                    "chunk_index": c.chunk_index,
                    "corpus": corpus,
                }
                for c in chunks
            ]
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            chunks_added += len(chunks)

        state[rel] = mtime
        files_indexed += 1

    stale = [rel for rel in state if rel not in seen_files]
    for rel in stale:
        existing = collection.get(where={"source_path": rel})
        existing_ids = existing.get("ids") or []
        if existing_ids:
            collection.delete(ids=existing_ids)
        state.pop(rel, None)

    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return {
        "files_indexed": files_indexed,
        "chunks_added": chunks_added,
        "stale_removed": len(stale),
        "source_dir": str(source_dir),
        "collection": collection_name,
    }
