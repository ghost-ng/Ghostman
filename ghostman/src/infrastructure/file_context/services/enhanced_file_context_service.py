"""
Enhanced File Context Service integrating RAG Pipeline.

Provides a bridge between a simple file-context interface and the RAG pipeline.
This implementation is intentionally minimal and focused on correct metadata
mapping and use of the RAG pipeline outputs.
"""

import logging
import os
from typing import Optional, Dict, Any, Union, List
from pathlib import Path
from dataclasses import dataclass

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False

from ..rag_pipeline.config.rag_config import RAGPipelineConfig, get_config
from ..rag_pipeline.pipeline.rag_pipeline import get_rag_pipeline, RAGPipeline, RAGQuery, RAGResponse
from ..rag_pipeline.text_processing.text_splitter import TextSplitterFactory

logger = logging.getLogger("ghostman.enhanced_file_context_service")


@dataclass
class EnhancedFileContextConfig:
    legacy_enabled: bool = True
    rag_enabled: bool = True
    auto_migrate: bool = False
    migration_batch_size: int = 100
    fallback_to_legacy: bool = True


# Provide a minimal signal implementation for non-Qt environments
class _SimpleSignal:
    def __init__(self):
        self._subscribers = []

    def connect(self, fn):
        if callable(fn):
            self._subscribers.append(fn)

    def emit(self, *args, **kwargs):
        for fn in list(self._subscribers):
            try:
                fn(*args, **kwargs)
            except Exception:
                logger.exception("Signal subscriber raised exception")

if PYQT_AVAILABLE:
    class EnhancedFileContextService(QObject):
        """
        Enhanced file context service (Qt-enabled) exposing pyqt signals that the UI
        can connect to. Signals:
          - file_processing_started(file_id, filename)
          - file_processing_completed(file_id, result_data)
          - file_processing_failed(file_id, error_message)
        """
        file_processing_started = pyqtSignal(str, str)
        file_processing_completed = pyqtSignal(str, dict)
        file_processing_failed = pyqtSignal(str, str)

        def __init__(
            self,
            api_key: Optional[str] = None,
            enhanced_config: Optional[EnhancedFileContextConfig] = None,
            rag_config: Optional[RAGPipelineConfig] = None
        ):
            super().__init__()
            self.enhanced_config = enhanced_config or EnhancedFileContextConfig()
            self._initialized = False
            self.legacy_service = None
            self.rag_pipeline: Optional[RAGPipeline] = None
            self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            self.rag_config = rag_config or get_config()
            logger.info("EnhancedFileContextService created (Qt signals enabled)")
else:
    class EnhancedFileContextService:
        """
        Enhanced file context service for non-Qt environments. Provides a small
        signal-like API (connect/emit) so background workers or CLI can subscribe.
        """
        def __init__(
            self,
            api_key: Optional[str] = None,
            enhanced_config: Optional[EnhancedFileContextConfig] = None,
            rag_config: Optional[RAGPipelineConfig] = None
        ):
            self.enhanced_config = enhanced_config or EnhancedFileContextConfig()
            self._initialized = False
            self.legacy_service = None
            self.rag_pipeline: Optional[RAGPipeline] = None
            self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            self.rag_config = rag_config or get_config()

            # Simple signals for non-Qt usage
            self.file_processing_started = _SimpleSignal()
            self.file_processing_completed = _SimpleSignal()
            self.file_processing_failed = _SimpleSignal()

            logger.info("EnhancedFileContextService created (simple signals)")

    async def initialize(self) -> bool:
        """Initialize the enhanced service and RAG pipeline if enabled."""
        if self._initialized:
            return True

        try:
            logger.info("Initializing EnhancedFileContextService")

            if self.enhanced_config.rag_enabled:
                # Ensure llm API key is present on the pipeline config (non-destructive)
                if not getattr(self.rag_config.llm, "api_key", None) and self.api_key:
                    self.rag_config.llm.api_key = self.api_key

                # Initialize or retrieve global pipeline with explicit config
                self.rag_pipeline = get_rag_pipeline(self.rag_config)

            self._initialized = True
            logger.info("EnhancedFileContextService initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize EnhancedFileContextService: {e}")
            return False

    async def process_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Ingest a file using the RAG pipeline and return a structured result.

        This derives chunk counts from the same splitter used by the pipeline,
        and returns realistic token counts (word-based approximation).
        """
        if not self._initialized:
            return {"success": False, "error": "Service not initialized"}

        file_path = Path(file_path)
        if not file_path.exists():
            return {"success": False, "error": "File not found"}

        if not self.rag_pipeline:
            return {"success": False, "error": "RAG pipeline not initialized"}

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Use the pipeline's splitter for accurate chunk counts
            splitter = self.rag_pipeline.text_splitter
            chunks = splitter.split_text(content)
            chunk_count = len(chunks)
            token_count = len(content.split())
 
            # Emit started signal (use filename as temporary id until document id is known)
            try:
                self.file_processing_started.emit(file_path.name, file_path.name)
            except Exception:
                # If signal is not callable or not available, ignore
                pass
 
            # Ingest to pipeline (this stores chunks and embeddings)
            document_id = await self.rag_pipeline.ingest_document(str(file_path))
 
            result = {
                "success": True,
                "document_id": document_id,
                "filename": file_path.name,
                "tokens": token_count,
                "chunks": chunk_count
            }
 
            # Emit completed signal with document id and result data
            try:
                self.file_processing_completed.emit(document_id, result)
            except Exception:
                pass
 
            logger.info(f"file_processing_completed emitted for {file_path.name}")
            return result
 
        except Exception as e:
            logger.exception(f"Error processing file with RAG pipeline: {e}")
            # Emit failed signal
            try:
                self.file_processing_failed.emit(file_path.name, str(e))
            except Exception:
                pass
            logger.error(f"file_processing_failed emitted for {file_path.name}: {e}")
            return {"success": False, "error": str(e)}

    async def get_relevant_contexts(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        max_contexts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG pipeline and convert results into a legacy-compatible format.

        Returns a dictionary containing:
          - contexts: list of context dicts (file_id, filename, content, similarity_score, tokens_used)
          - total_tokens: total tokens counted across returned contexts
          - selection_time: processing time reported by the pipeline
          - query_analysis: metadata about the query
        """
        if not self._initialized or not self.rag_pipeline:
            return {
                "contexts": [],
                "total_tokens": 0,
                "selection_time": 0.0,
                "query_analysis": {"error": "Service not initialized"}
            }

        try:
            rag_response: RAGResponse = await self.rag_pipeline.query(query)

            if not rag_response or not rag_response.sources:
                return {
                    "contexts": [],
                    "total_tokens": 0,
                    "selection_time": getattr(rag_response, "processing_time", 0.0),
                    "query_analysis": {"system": "rag", "note": "no_sources"}
                }

            contexts = []
            total_tokens = 0

            sources = rag_response.sources[:max_contexts] if max_contexts else rag_response.sources

            for src in sources:
                filename = src.metadata.get("filename", src.metadata.get("source", "unknown"))
                tokens_used = len(src.content.split())

                contexts.append({
                    "file_id": getattr(src, "document_id", "unknown"),
                    "filename": filename,
                    "content": src.content,
                    "similarity_score": float(getattr(src, "score", 0.0)),
                    "relevance_score": float(getattr(src, "score", 0.0)),
                    "tokens_used": tokens_used
                })
                total_tokens += tokens_used

            return {
                "contexts": contexts,
                "total_tokens": total_tokens,
                "selection_time": getattr(rag_response, "processing_time", 0.0),
                "query_analysis": {"system": "rag", "intent": "search"}
            }

        except Exception as e:
            logger.exception(f"RAG context selection failed: {e}")
            return {
                "contexts": [],
                "total_tokens": 0,
                "selection_time": 0.0,
                "query_analysis": {"error": str(e)}
            }

    async def shutdown(self):
        """Shutdown the enhanced service and optionally clear the global pipeline."""
        try:
            if self.rag_pipeline:
                # If the global instance is being used by other parts, avoid wiping it.
                # Optionally clear the global pipeline if this service owns it.
                from ...rag_pipeline.pipeline.rag_pipeline import set_rag_pipeline
                try:
                    set_rag_pipeline(None)
                except Exception:
                    # Best-effort cleanup; don't raise
                    pass
        except Exception as e:
            logger.debug(f"Error during enhanced service shutdown: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Return combined statistics, preferring RAG pipeline stats when available."""
        stats: Dict[str, Any] = {"system": "enhanced", "rag_enabled": self.enhanced_config.rag_enabled}
        if self.rag_pipeline:
            try:
                stats["rag"] = self.rag_pipeline.get_stats()
            except Exception:
                stats["rag"] = {"error": "failed to read rag stats"}
        return stats