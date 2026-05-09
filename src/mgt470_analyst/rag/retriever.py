from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mgt470_analyst.rag.chunker import Chunk
from mgt470_analyst.rag.indexer import (
    AUSTIN_COLLECTION_NAME,
    EMBEDDING_MODEL,
    PRIMARY_COLLECTION_NAME,
    default_persist_dir,
)

# Per-module query framing. The retriever combines this with the company
# name and case perspective to surface chunks relevant to the LLM call we're
# about to make. Stays simple intentionally — keyword soup matches the
# semantics of an embedding-similarity search well enough.
_MODULE_FRAMING: dict[str, str] = {
    "cvc": "customer value chain activities decoupling Teixeira",
    "weak_links": "weak link decoupling opportunity pain frequency switching",
    "decoupling": "decoupling strategy primary new offering layered evolution",
    "business_model": "business model unit economics CAC CLV value capture",
    "competitive_response": "incumbent recoupling response platform defense",
    "final_judgment": "investment judgment recommendation staged actions don't-do",
}

PRIMARY_DISTANCE_MULTIPLIER = 2 / 3


@dataclass(frozen=True)
class RankedChunk:
    chunk: Chunk
    distance: float


class MethodologyRetriever:
    """Queries the local notes index for chunks relevant to a module call.

    Returns ``[]`` (never raises) when:
    - the index dir does not exist (`mgt470 reindex` was never run)
    - ``OPENAI_API_KEY`` is not set (no way to embed the query)
    - any underlying chromadb error occurs

    This silent-fallback contract is what lets the orchestrator pass the
    retriever output straight to the prompt renderer without branching.
    """

    def __init__(
        self,
        *,
        persist_dir: Path | str | None = None,
        top_k: int = 5,
    ) -> None:
        self._persist_dir = Path(persist_dir) if persist_dir else default_persist_dir()
        self._top_k = top_k
        self._collections: dict[str, object] = {}
        self._initialized = False

    def _collections_or_none(self) -> dict[str, object]:
        if self._initialized:
            return self._collections
        self._initialized = True

        if not self._persist_dir.exists():
            return {}
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {}

        try:
            import chromadb
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

            client = chromadb.PersistentClient(path=str(self._persist_dir))
            embed_fn = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBEDDING_MODEL)
            for corpus, collection_name in (
                ("austin", AUSTIN_COLLECTION_NAME),
                ("primary", PRIMARY_COLLECTION_NAME),
            ):
                try:
                    self._collections[corpus] = client.get_collection(
                        name=collection_name, embedding_function=embed_fn
                    )
                except Exception:
                    continue
        except Exception:
            self._collections = {}
        return self._collections

    def retrieve_for_module(
        self,
        module_name: str,
        company_name: str,
        perspective: str | None = None,
        top_k: int | None = None,
    ) -> list[Chunk]:
        collections = self._collections_or_none()
        if not collections:
            return []

        k = top_k or self._top_k
        query = _build_query(module_name, company_name, perspective)

        ranked: list[RankedChunk] = []
        for corpus, collection in collections.items():
            n_results = min(k, 3) if len(collections) > 1 else k * 2
            try:
                result = collection.query(query_texts=[query], n_results=n_results)
            except Exception:
                continue
            ranked.extend(_ranked_chunks_from_result(result, corpus=corpus))

        if not ranked:
            return []

        return merge_ranked_chunks(ranked, top_k=k, company_name=company_name)


def _ranked_chunks_from_result(result: dict, *, corpus: str) -> list[RankedChunk]:
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    ranked: list[RankedChunk] = []
    for index, (cid, doc, meta) in enumerate(zip(ids, docs, metas, strict=False)):
        meta = meta or {}
        trail_str = meta.get("heading_trail") or ""
        heading_trail = tuple(h for h in trail_str.split(" > ") if h)
        chunk_corpus = str(meta.get("corpus") or corpus)
        try:
            distance = float(distances[index])
        except (IndexError, TypeError, ValueError):
            distance = float(index + 1)
        ranked.append(
            RankedChunk(
                chunk=Chunk(
                    text=doc or "",
                    source_path=str(meta.get("source_path") or cid),
                    heading_trail=heading_trail,
                    chunk_index=int(meta.get("chunk_index") or 0),
                    corpus=chunk_corpus,
                ),
                distance=distance,
            )
        )
    return ranked


def merge_ranked_chunks(
    ranked_chunks: list[RankedChunk],
    *,
    top_k: int,
    company_name: str = "",
) -> list[Chunk]:
    """Merge Chroma results, boosting Teixeira primary-source chunks.

    Chroma distances are lower-is-better, so a 1.5x primary weight is applied
    by multiplying primary distances by 2/3.
    """
    company_lc = (company_name or "").strip().lower()

    def sort_key(item: RankedChunk) -> tuple[int, float]:
        company_miss = 0
        if company_lc:
            company_miss = 0 if _mentions(item.chunk, company_lc) else 1
        distance = item.distance
        if item.chunk.corpus == "primary":
            distance *= PRIMARY_DISTANCE_MULTIPLIER
        return (company_miss, distance)

    return [item.chunk for item in sorted(ranked_chunks, key=sort_key)[:top_k]]


def _build_query(module_name: str, company_name: str, perspective: str | None) -> str:
    framing = _MODULE_FRAMING.get(module_name, module_name.replace("_", " "))
    bits = [framing]
    if company_name:
        bits.append(company_name)
    if perspective:
        bits.append(f"{perspective} perspective")
    return " ".join(bits)


def _mentions(chunk: Chunk, needle_lc: str) -> bool:
    if needle_lc in chunk.source_path.lower():
        return True
    return any(needle_lc in h.lower() for h in chunk.heading_trail)
