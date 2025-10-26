"""
Thread-Safe RAG Session

Provides a stable interface to FAISS-based RAG operations.
This replaces the ChromaDB-based solution that was causing segmentation faults.
"""

import logging
from typing import Dict, Any, Optional

from ..config.rag_config import RAGPipelineConfig
from .simple_faiss_session import create_simple_faiss_session, SimpleFAISSSession

logger = logging.getLogger("ghostman.safe_rag_session")


class SafeRAGSession:
    """
    Safe RAG session using simple FAISS backend.
    
    This provides the same interface as before but uses a stable
    FAISS implementation instead of the problematic ChromaDB.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """Initialize safe RAG session."""
        self.simple_session = create_simple_faiss_session(config)
        
    @property
    def is_ready(self) -> bool:
        """Check if session is ready."""
        return self.simple_session.is_ready
    
    def ingest_document(self, file_path, metadata_override=None, timeout=120.0):
        """Ingest document - delegate to simple session."""
        return self.simple_session.ingest_document(file_path, metadata_override, timeout)
    
    def query(self, query_text, top_k=5, filters=None, timeout=30.0, conversation_id=None):
        """Query - delegate to simple session."""
        return self.simple_session.query(query_text, top_k, filters, timeout, conversation_id)
    
    def get_stats(self, timeout=5.0):
        """Get stats - delegate to simple session."""
        return self.simple_session.get_stats(timeout)
    
    def health_check(self, timeout=5.0):
        """Health check - delegate to simple session."""
        return self.simple_session.health_check(timeout)
    
    def close(self):
        """Close session - delegate to simple session."""
        return self.simple_session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_safe_rag_session(config: Optional[RAGPipelineConfig] = None) -> SafeRAGSession:
    """Create a new safe RAG session."""
    return SafeRAGSession(config)