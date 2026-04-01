"""
Archival Memory Service for the MemGPT-style memory system.

Provides long-term semantic storage using a simple JSON + embedding
approach. Each memory is stored with its text and embedding vector
for similarity search.

Storage: ``%APPDATA%/Specter/memory/archival.json``
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("specter.memory.archival")

_PAGE_SIZE = 5


class ArchivalMemoryService:
    """
    Long-term semantic memory with embedding-based search.

    Uses the existing EmbeddingService for vectorization and stores
    entries in a simple JSON file with numpy arrays serialized as lists.
    This avoids dependency on the full RAG FAISS pipeline.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            appdata = os.environ.get("APPDATA", "")
            storage_path = Path(appdata) / "Specter" / "memory" / "archival.json"
        self._storage_path = storage_path
        self._entries: List[Dict[str, Any]] = []
        self._embedding_service = None
        self._load()

    def _ensure_embedding_service(self) -> bool:
        """Lazy-initialize the embedding service."""
        if self._embedding_service is not None:
            return True
        try:
            from ..rag_pipeline.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
            return True
        except Exception as e:
            logger.warning(f"Embedding service not available: {e}")
            return False

    async def insert(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Embed and store a memory passage.

        Returns a confirmation string.
        """
        if not self._ensure_embedding_service():
            return "Error: Embedding service not available"

        try:
            embedding = await self._embedding_service.get_embedding(content)
            if embedding is None:
                return "Error: Failed to generate embedding"

            entry = {
                "content": content,
                "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding),
                "metadata": metadata or {},
            }
            self._entries.append(entry)
            self._save()

            logger.info(f"Stored archival memory ({len(self._entries)} total)")
            return f"Stored in archival memory. Total entries: {len(self._entries)}"

        except Exception as e:
            logger.error(f"Failed to insert archival memory: {e}")
            return f"Error storing in archival memory: {e}"

    async def search(self, query: str, top_k: int = _PAGE_SIZE) -> List[Dict]:
        """
        Semantic search over archival memory via cosine similarity.
        """
        if not self._entries:
            return []
        if not self._ensure_embedding_service():
            return []

        try:
            query_embedding = await self._embedding_service.get_embedding(query)
            if query_embedding is None:
                return []

            query_vec = np.array(query_embedding, dtype=np.float32)
            norm_q = np.linalg.norm(query_vec)
            if norm_q > 0:
                query_vec = query_vec / norm_q

            # Compute cosine similarity against all entries
            scored = []
            for entry in self._entries:
                vec = np.array(entry["embedding"], dtype=np.float32)
                norm_v = np.linalg.norm(vec)
                if norm_v > 0:
                    vec = vec / norm_v
                score = float(np.dot(query_vec, vec))
                scored.append((score, entry))

            scored.sort(key=lambda x: x[0], reverse=True)

            results = []
            for score, entry in scored[:top_k]:
                results.append({
                    "content": entry["content"],
                    "score": score,
                    "metadata": entry.get("metadata", {}),
                })

            return results

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
        return len(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data.get("entries", [])
                logger.info(f"Loaded {len(self._entries)} archival memory entries")
            except Exception as e:
                logger.warning(f"Failed to load archival memory: {e}")
                self._entries = []
        else:
            self._entries = []

    def _save(self) -> None:
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"entries": self._entries}
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save archival memory: {e}")
