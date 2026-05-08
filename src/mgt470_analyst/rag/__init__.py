"""RAG layer over Austin's MGT470 course notes.

Public surface:
- ``Chunk``: the unit of retrieved text plus its source attribution.
- ``MethodologyRetriever``: queries the local ChromaDB index for chunks
  relevant to a given module + company + perspective. Returns ``[]``
  silently when the index is missing or no API key is configured, so
  modules can pass the result straight to the prompt renderer.
- ``build_index``: idempotent indexer that walks a notes directory,
  chunks each Markdown file, and persists embeddings to ChromaDB.

The whole module is gated by the orchestrator on the ``MGT470_RAG=1``
env var, so the rest of the pipeline works unchanged when RAG is off.
"""

from mgt470_analyst.rag.chunker import Chunk, chunk_markdown
from mgt470_analyst.rag.indexer import build_index, default_persist_dir
from mgt470_analyst.rag.retriever import MethodologyRetriever

__all__ = [
    "Chunk",
    "MethodologyRetriever",
    "build_index",
    "chunk_markdown",
    "default_persist_dir",
]
