"""
Archival Memory Service for the MemGPT-style memory system.

Provides long-term semantic storage backed by the existing FAISS vector
store and embedding service. The LLM can insert and search memories
via tool calls.

Archival entries are stored with ``memory_type: "archival"`` metadata
to keep them separate from file-context RAG documents.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("specter.memory.archival")

_ARCHIVAL_METADATA = {"memory_type": "archival", "source": "memgpt"}
_PAGE_SIZE = 5


class ArchivalMemoryService:
    """
    Long-term semantic memory backed by FAISS.

    Uses the existing RAG infrastructure (FaissClient + EmbeddingService)
    with metadata filtering to separate archival memories from file
    context documents.
    """

    def __init__(self):
        self._initialized = False
        self._faiss_client = None
        self._embedding_service = None

    def _ensure_initialized(self) -> bool:
        """Lazy-initialize FAISS and embedding service."""
        if self._initialized:
            return self._faiss_client is not None

        self._initialized = True
        try:
            from ..rag_pipeline.vector_store.faiss_client import FaissClient
            from ..rag_pipeline.services.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService()
            self._faiss_client = FaissClient()
            logger.info("Archival memory service initialized")
            return True
        except Exception as e:
            logger.warning(f"Archival memory not available: {e}")
            return False

    async def insert(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Embed and store a memory passage.

        Returns a confirmation string with the total archival count.
        """
        if not self._ensure_initialized():
            return "Error: Archival memory not available (FAISS/embeddings not configured)"

        try:
            combined_meta = dict(_ARCHIVAL_METADATA)
            if metadata:
                combined_meta.update(metadata)

            # Generate embedding
            embedding = await self._embedding_service.get_embedding(content)
            if embedding is None:
                return "Error: Failed to generate embedding for archival entry"

            # Store in FAISS
            from langchain.schema import Document
            doc = Document(page_content=content, metadata=combined_meta)
            self._faiss_client.add_documents([doc])

            count = self.get_count()
            logger.info(f"Stored archival memory ({count} total)")
            return f"Stored in archival memory. Total entries: {count}"

        except Exception as e:
            logger.error(f"Failed to insert archival memory: {e}")
            return f"Error storing in archival memory: {e}"

    async def search(self, query: str, top_k: int = _PAGE_SIZE) -> List[Dict]:
        """
        Semantic search over archival memory.

        Returns a list of matching passages with scores.
        """
        if not self._ensure_initialized():
            return []

        try:
            results = self._faiss_client.similarity_search_with_score(
                query, k=top_k * 2  # Over-fetch to filter
            )

            archival_results = []
            for doc, score in results:
                meta = doc.metadata or {}
                if meta.get("memory_type") == "archival":
                    archival_results.append({
                        "content": doc.page_content,
                        "score": float(score),
                        "metadata": meta,
                    })
                    if len(archival_results) >= top_k:
                        break

            return archival_results

        except Exception as e:
            logger.error(f"Archival memory search failed: {e}")
            return []

    def format_results(self, results: List[Dict]) -> str:
        """Format search results as a readable string for the LLM."""
        if not results:
            return "No results found in archival memory."
        lines = []
        for r in results:
            score = r.get("score", 0)
            content = r.get("content", "")[:300]
            lines.append(f"[Relevance: {score:.2f}] {content}")
        return "\n".join(lines)

    def get_count(self) -> int:
        """Return approximate count of archival entries."""
        if not self._faiss_client:
            return 0
        try:
            # Approximate — count all documents in the store
            # (no easy way to filter by metadata without searching)
            return getattr(self._faiss_client, '_document_count', 0)
        except Exception:
            return 0
