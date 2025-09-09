"""
Thread-Safe RAG Session

Provides a thread-safe interface to the FAISS-based RAG pipeline.
This replaces ChromaDB-based solutions to prevent segfaults in Qt applications.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from ..config.rag_config import get_config, RAGPipelineConfig
from ..pipeline.safe_rag_pipeline import SafeRAGPipeline

logger = logging.getLogger("ghostman.safe_rag_session")


class SafeRAGSession:
    """
    Thread-safe RAG session using FAISS vector store.
    
    This class provides a safe interface to the RAG pipeline without
    the threading issues that occurred with ChromaDB.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize safe RAG session.
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config or get_config()
        self.logger = logging.getLogger("ghostman.safe_rag_session.SafeRAGSession")
        
        # Initialize FAISS-based pipeline
        self._pipeline: Optional[SafeRAGPipeline] = None
        
        # Session state
        self._session_id = f"rag_session_{int(time.time())}"
        self._is_ready = False
        
        # Initialize session
        self._initialize()
    
    def _initialize(self):
        """Initialize the RAG session."""
        try:
            self.logger.info(f"Initializing safe RAG session: {self._session_id}")
            
            # Create FAISS-based pipeline
            self._pipeline = SafeRAGPipeline(self.config)
            
            if self._pipeline.is_ready():
                self._is_ready = True
                self.logger.info("✅ Safe RAG session ready")
            else:
                self.logger.error("❌ FAISS pipeline not ready")
                self._is_ready = False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize RAG session: {e}")
            self._is_ready = False
    
    @property
    def is_ready(self) -> bool:
        """Check if the RAG session is ready."""
        return self._is_ready and self._pipeline is not None
    
    def ingest_document(self, file_path: Union[str, Path], 
                       metadata_override: Optional[Dict[str, Any]] = None,
                       timeout: float = 120.0) -> Optional[str]:
        """
        Ingest a document (thread-safe).
        
        Args:
            file_path: Path to document file
            metadata_override: Optional metadata overrides
            timeout: Operation timeout in seconds (unused with FAISS)
            
        Returns:
            Document ID if successful, None if failed
        """
        if not self.is_ready:
            self.logger.error("RAG session not ready")
            return None
        
        try:
            self.logger.info(f"🔄 Ingesting document (thread-safe): {file_path}")
            start_time = time.time()
            
            # Process document through FAISS pipeline
            document_id = self._pipeline.ingest_document(
                file_path=file_path,
                metadata_override=metadata_override
            )
            
            processing_time = time.time() - start_time
            
            if document_id:
                if document_id.startswith("skipped_"):
                    self.logger.warning(f"⚠️ Document processing skipped: {document_id}")
                else:
                    self.logger.info(f"✅ Document ingested successfully: {document_id} ({processing_time:.2f}s)")
            else:
                self.logger.error("❌ Document ingestion failed")
            
            return document_id
            
        except Exception as e:
            self.logger.error(f"❌ Document ingestion error: {e}")
            return None
    
    def query(self, query_text: str, top_k: int = 5, 
              filters: Optional[Dict[str, Any]] = None,
              timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Query the RAG pipeline (thread-safe).
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            filters: Optional metadata filters (unused with current FAISS impl)
            timeout: Operation timeout in seconds (unused with FAISS)
            
        Returns:
            Query response if successful, None if failed
        """
        if not self.is_ready:
            self.logger.error("RAG session not ready")
            return None
        
        try:
            self.logger.info(f"🔍 Querying RAG pipeline (thread-safe): {query_text[:50]}...")
            start_time = time.time()
            
            # Query through FAISS pipeline
            result = self._pipeline.query(
                query_text=query_text,
                top_k=top_k
            )
            
            processing_time = time.time() - start_time
            
            if result:
                sources_count = len(result.get('sources', []))
                self.logger.info(f"✅ Query completed: {sources_count} sources found ({processing_time:.2f}s)")
            else:
                self.logger.warning("⚠️ Query returned no results")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Query error: {e}")
            return None
    
    def get_stats(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Get RAG pipeline statistics (thread-safe).
        
        Args:
            timeout: Operation timeout in seconds (unused with FAISS)
            
        Returns:
            Statistics if successful, None if failed
        """
        if not self.is_ready:
            return {
                'session_ready': False,
                'error': 'RAG session not ready'
            }
        
        try:
            # Get stats from pipeline
            stats = self._pipeline.get_stats() if self._pipeline else {}
            
            # Add session info
            stats['session'] = {
                'session_id': self._session_id,
                'ready': self._is_ready,
                'vector_store': 'faiss',
                'config': {
                    'embedding_model': self.config.embedding.model,
                    'llm_model': self.config.llm.model,
                    'collection_name': self.config.vector_store.collection_name
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Get stats error: {e}")
            return {
                'session_ready': self._is_ready,
                'error': str(e)
            }
    
    def health_check(self, timeout: float = 5.0) -> bool:
        """
        Check if the RAG session is healthy.
        
        Args:
            timeout: Check timeout in seconds (unused with FAISS)
            
        Returns:
            True if healthy, False otherwise
        """
        return self.is_ready and self._pipeline.is_ready() if self._pipeline else False
    
    def close(self):
        """Close the RAG session (cleanup)."""
        try:
            self.logger.info(f"Closing safe RAG session: {self._session_id}")
            if self._pipeline:
                self._pipeline.cleanup()
            self._is_ready = False
            
        except Exception as e:
            self.logger.error(f"Error closing RAG session: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._is_ready:
            self.close()


def create_safe_rag_session(config: Optional[RAGPipelineConfig] = None) -> SafeRAGSession:
    """
    Create a new thread-safe RAG session.
    
    Args:
        config: RAG pipeline configuration
        
    Returns:
        SafeRAGSession instance
    """
    return SafeRAGSession(config)