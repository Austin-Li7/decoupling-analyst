from __future__ import annotations

import json
import os
from pathlib import Path

from mgt470_analyst.rag.chunker import chunk_markdown

COLLECTION_NAME = "austin_notes"
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


def build_index(
    notes_dir: Path | str | None = None,
    *,
    persist_dir: Path | str | None = None,
) -> dict:
    """Idempotent re-index of the MGT470 notes directory.

    Skips files whose mtime hasn't changed since the last run. Returns a
    summary dict (files_indexed, chunks_added, persist_dir).
    """
    notes_path = Path(notes_dir) if notes_dir else default_notes_dir()
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
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )

    state_path = persist_path / "index_state.json"
    state: dict[str, float] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}

    files_indexed = 0
    chunks_added = 0
    seen_files: set[str] = set()

    for md_path in sorted(notes_path.rglob("*.md")):
        rel = str(md_path.relative_to(notes_path))
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
            ids = [f"{rel}::{c.chunk_index}" for c in chunks]
            documents = [c.text for c in chunks]
            metadatas = [
                {
                    "source_path": c.source_path,
                    "heading_trail": " > ".join(c.heading_trail),
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ]
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            chunks_added += len(chunks)

        state[rel] = mtime
        files_indexed += 1

    # Drop entries for files that no longer exist on disk.
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
        "persist_dir": str(persist_path),
        "notes_dir": str(notes_path),
        "stale_removed": len(stale),
    }
