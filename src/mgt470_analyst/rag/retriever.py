from __future__ import annotations

import os
from pathlib import Path

from mgt470_analyst.rag.chunker import Chunk
from mgt470_analyst.rag.indexer import COLLECTION_NAME, EMBEDDING_MODEL, default_persist_dir

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
        self._collection = None
        self._initialized = False

    def _collection_or_none(self):
        if self._initialized:
            return self._collection
        self._initialized = True

        if not self._persist_dir.exists():
            return None
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            import chromadb
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

            client = chromadb.PersistentClient(path=str(self._persist_dir))
            embed_fn = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBEDDING_MODEL)
            self._collection = client.get_collection(
                name=COLLECTION_NAME, embedding_function=embed_fn
            )
        except Exception:
            self._collection = None
        return self._collection

    def retrieve_for_module(
        self,
        module_name: str,
        company_name: str,
        perspective: str | None = None,
        top_k: int | None = None,
    ) -> list[Chunk]:
        collection = self._collection_or_none()
        if collection is None:
            return []

        k = top_k or self._top_k
        query = self._build_query(module_name, company_name, perspective)

        try:
            result = collection.query(query_texts=[query], n_results=k * 2)
        except Exception:
            return []

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]

        chunks: list[Chunk] = []
        for cid, doc, meta in zip(ids, docs, metas, strict=False):
            meta = meta or {}
            trail_str = meta.get("heading_trail") or ""
            heading_trail = tuple(h for h in trail_str.split(" > ") if h)
            chunks.append(
                Chunk(
                    text=doc or "",
                    source_path=str(meta.get("source_path") or cid),
                    heading_trail=heading_trail,
                    chunk_index=int(meta.get("chunk_index") or 0),
                )
            )

        # Lexical re-rank: chunks whose source path or heading trail mentions
        # the company surface first. Useful because the case-specific note
        # for a company is the highest-signal context we have.
        company_lc = (company_name or "").strip().lower()
        if company_lc:
            chunks.sort(key=lambda c: 0 if _mentions(c, company_lc) else 1)

        return chunks[:k]

    @staticmethod
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
