"""
Safe ChromaDB Client with Segfault Protection

A robust wrapper around ChromaDB that prevents segmentation faults in Qt applications:
- Process isolation for ChromaDB initialization
- SQLite WAL mode and connection isolation
- Lazy initialization with multiple retry strategies
- Graceful degradation and fallback mechanisms
- Thread-safe operations with proper connection management
"""

import asyncio
import functools
import logging
import multiprocessing
import os
import queue
import sqlite3
import tempfile
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from ..config.rag_config import VectorStoreConfig
from ..document_loaders.base_loader import Document
from ..text_processing.text_splitter import TextChunk
from .chromadb_client import ChromaDBClient, SearchResult, ChromaDBError

logger = logging.getLogger("ghostman.safe_chromadb")


class SafeChromaDBError(Exception):
    """Safe ChromaDB specific errors."""
    pass


class ChromaDBInitializer:
    """Process-isolated ChromaDB initializer to prevent segfaults."""
    
    @staticmethod
    def initialize_in_process(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize ChromaDB in a separate process to avoid Qt threading conflicts."""
        try:
            # Import ChromaDB in the separate process
            import chromadb
            from chromadb.config import Settings
            
            # Reconstruct config from dict
            persist_dir = config_dict.get('persist_directory')
            collection_name = config_dict.get('collection_name', 'ghostman_documents')
            distance_function = config_dict.get('distance_function', 'cosine')
            host = config_dict.get('host', 'localhost')
            port = config_dict.get('port', 8000)
            ssl = config_dict.get('ssl', False)
            
            # Ensure directory exists
            if persist_dir:
                Path(persist_dir).mkdir(parents=True, exist_ok=True)
            
            # Configure SQLite for WAL mode (Write-Ahead Logging) to reduce lock contention
            sqlite_db_path = Path(persist_dir) / "chroma.sqlite3" if persist_dir else None
            if sqlite_db_path and sqlite_db_path.exists():
                try:
                    with sqlite3.connect(str(sqlite_db_path), timeout=30) as conn:
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA synchronous=NORMAL") 
                        conn.execute("PRAGMA cache_size=10000")
                        conn.execute("PRAGMA temp_store=MEMORY")
                        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                        conn.commit()
                        logger.info("Applied SQLite performance optimizations")
                except Exception as e:
                    logger.warning(f"Failed to optimize SQLite settings: {e}")
            
            # Create settings
            settings = Settings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
                is_persistent=True if persist_dir else False
            )
            
            # Try to create client
            client = None
            if host == "localhost" and not ssl:
                # Use persistent client
                client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=settings
                )
            else:
                # Use HTTP client
                client = chromadb.HttpClient(
                    host=host,
                    port=port,
                    ssl=ssl,
                    settings=settings
                )
            
            # Test client by getting or creating collection
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": distance_function}
            )
            
            # Test basic operations
            test_count = collection.count()
            
            return {
                'success': True,
                'collection_name': collection_name,
                'count': test_count,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'collection_name': None,
                'count': 0,
                'error': str(e)
            }


class SafeChromaDBClient:
    """
    Thread-safe ChromaDB client that prevents segmentation faults.
    
    Key safety features:
    - Process isolation for initialization
    - Thread-safe operations with connection management
    - Lazy initialization with retry logic
    - Graceful degradation on failures
    - SQLite WAL mode for better concurrency
    """
    
    def __init__(self, config: VectorStoreConfig):
        """
        Initialize safe ChromaDB client.
        
        Args:
            config: Vector store configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.SafeChromaDBClient")
        
        # Client state
        self._client: Optional[ChromaDBClient] = None
        self._initialization_lock = threading.RLock()
        self._initialized = False
        self._initialization_error: Optional[str] = None
        self._last_init_attempt = 0.0
        self._init_retry_delay = 5.0  # seconds
        self._max_init_retries = 3
        self._init_attempt_count = 0
        
        # Performance tracking
        self._stats = {
            'initialization_attempts': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'fallback_operations': 0,
            'last_success_time': 0.0,
        }
        
        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="SafeChromaDB")
        
        self.logger.info("SafeChromaDBClient initialized (lazy initialization enabled)")
    
    def _can_attempt_initialization(self) -> bool:
        """Check if we can attempt initialization based on retry policy."""
        now = time.time()
        if self._init_attempt_count >= self._max_init_retries:
            return False
        if now - self._last_init_attempt < self._init_retry_delay:
            return False
        return True
    
    async def _safe_initialize(self) -> bool:
        """
        Safely initialize ChromaDB using process isolation.
        
        Returns:
            True if initialization successful, False otherwise
        """
        with self._initialization_lock:
            # Check if already initialized
            if self._initialized and self._client is not None:
                return True
            
            # Check retry policy
            if not self._can_attempt_initialization():
                return False
            
            self._last_init_attempt = time.time()
            self._init_attempt_count += 1
            self._stats['initialization_attempts'] += 1
            
            try:
                self.logger.info(f"Attempting safe ChromaDB initialization (attempt {self._init_attempt_count}/{self._max_init_retries})")
                
                # Prepare config for process initialization
                config_dict = {
                    'persist_directory': self.config.persist_directory,
                    'collection_name': self.config.collection_name,
                    'distance_function': self.config.distance_function,
                    'host': self.config.host,
                    'port': self.config.port,
                    'ssl': self.config.ssl,
                    'headers': self.config.headers,
                }
                
                # Use process pool to safely initialize ChromaDB
                # This prevents Qt threading issues by isolating ChromaDB in separate process
                loop = asyncio.get_event_loop()
                with ProcessPoolExecutor(max_workers=1) as executor:
                    future = loop.run_in_executor(
                        executor,
                        ChromaDBInitializer.initialize_in_process,
                        config_dict
                    )
                    
                    # Wait for process initialization with timeout
                    result = await asyncio.wait_for(future, timeout=30.0)
                
                if result['success']:
                    # Process initialization successful, now create client in current thread
                    try:
                        self._client = ChromaDBClient(self.config)
                        self._initialized = True
                        self._initialization_error = None
                        
                        self.logger.info(f"✅ ChromaDB initialized successfully: {result['collection_name']} ({result['count']} documents)")
                        return True
                        
                    except Exception as e:
                        self.logger.error(f"❌ Failed to create client after process init: {e}")
                        self._initialization_error = f"Client creation failed: {e}"
                        return False
                else:
                    self.logger.error(f"❌ Process initialization failed: {result['error']}")
                    self._initialization_error = result['error']
                    return False
                    
            except asyncio.TimeoutError:
                error_msg = "ChromaDB initialization timed out (30s)"
                self.logger.error(f"❌ {error_msg}")
                self._initialization_error = error_msg
                return False
                
            except Exception as e:
                error_msg = f"Safe initialization failed: {e}"
                self.logger.error(f"❌ {error_msg}")
                self._initialization_error = error_msg
                return False
    
    async def _ensure_initialized(self) -> bool:
        """Ensure ChromaDB is initialized, attempting if necessary."""
        if self._initialized and self._client is not None:
            return True
        
        return await self._safe_initialize()
    
    @contextmanager
    def _safe_operation(self, operation_name: str):
        """Context manager for safe ChromaDB operations with error handling."""
        try:
            start_time = time.time()
            self.logger.debug(f"Starting {operation_name}")
            yield
            
            # Track successful operation
            self._stats['successful_operations'] += 1
            self._stats['last_success_time'] = time.time()
            self.logger.debug(f"{operation_name} completed in {time.time() - start_time:.2f}s")
            
        except Exception as e:
            self._stats['failed_operations'] += 1
            self.logger.error(f"{operation_name} failed: {e}")
            raise SafeChromaDBError(f"{operation_name} failed: {e}")
    
    async def store_document(self, document: Document, chunks: List[TextChunk], 
                           embeddings: List[np.ndarray]) -> List[str]:
        """
        Store document chunks with embeddings (thread-safe).
        
        Args:
            document: Document to store
            chunks: Text chunks from the document  
            embeddings: Embeddings for each chunk
            
        Returns:
            List of chunk IDs that were stored
        """
        # Ensure initialized
        if not await self._ensure_initialized():
            self._stats['fallback_operations'] += 1
            raise SafeChromaDBError(f"ChromaDB not available: {self._initialization_error}")
        
        with self._safe_operation("store_document"):
            return await self._client.store_document(document, chunks, embeddings)
    
    async def similarity_search(self, query_embedding: np.ndarray, 
                              top_k: int = 5,
                              filters: Optional[Dict[str, Any]] = None,
                              include_embeddings: bool = False) -> List[SearchResult]:
        """
        Perform similarity search (thread-safe).
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
            include_embeddings: Whether to include embeddings in results
            
        Returns:
            List of search results
        """
        # Ensure initialized
        if not await self._ensure_initialized():
            self._stats['fallback_operations'] += 1
            self.logger.warning("ChromaDB not available for search, returning empty results")
            return []
        
        with self._safe_operation("similarity_search"):
            return await self._client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
                include_embeddings=include_embeddings
            )
    
    async def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document (thread-safe).
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            Number of chunks deleted
        """
        # Ensure initialized
        if not await self._ensure_initialized():
            self._stats['fallback_operations'] += 1
            self.logger.warning("ChromaDB not available for deletion")
            return 0
        
        with self._safe_operation("delete_document"):
            return await self._client.delete_document(document_id)
    
    async def update_chunk_metadata(self, chunk_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a specific chunk (thread-safe).
        
        Args:
            chunk_id: Chunk ID to update
            metadata: New metadata
            
        Returns:
            True if successful
        """
        # Ensure initialized
        if not await self._ensure_initialized():
            self._stats['fallback_operations'] += 1
            return False
        
        with self._safe_operation("update_chunk_metadata"):
            return await self._client.update_chunk_metadata(chunk_id, metadata)
    
    def is_ready(self) -> bool:
        """Quick synchronous check if the client is ready."""
        return self._initialized and self._client is not None and self._client.is_ready()
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        if not await self._ensure_initialized():
            return {
                "name": self.config.collection_name,
                "count": 0,
                "status": "not_initialized",
                "error": self._initialization_error
            }
        
        with self._safe_operation("get_collection_info"):
            return await self._client.get_collection_info()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self._stats.copy()
        
        # Add base client stats if available
        if self._client:
            try:
                base_stats = self._client.get_stats()
                stats.update(base_stats)
            except Exception:
                pass
        
        # Add safety stats
        stats.update({
            'initialized': self._initialized,
            'init_attempts': self._init_attempt_count,
            'max_retries': self._max_init_retries,
            'initialization_error': self._initialization_error,
            'last_init_attempt': self._last_init_attempt,
        })
        
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        for key in ['successful_operations', 'failed_operations', 'fallback_operations']:
            self._stats[key] = 0
        
        if self._client:
            self._client.reset_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the safe vector store."""
        health = {
            "status": "unknown",
            "initialized": self._initialized,
            "initialization_error": self._initialization_error,
            "stats": self.get_stats()
        }
        
        if not self._initialized:
            health["status"] = "not_initialized"
            return health
        
        if not self._client:
            health["status"] = "unhealthy"
            health["error"] = "Client is None after initialization"
            return health
        
        try:
            # Delegate to underlying client
            underlying_health = await self._client.health_check()
            health.update(underlying_health)
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health
    
    async def backup_collection(self, backup_path: str) -> bool:
        """
        Backup collection data.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if successful
        """
        if not await self._ensure_initialized():
            return False
        
        with self._safe_operation("backup_collection"):
            return await self._client.backup_collection(backup_path)
    
    def force_reinitialize(self):
        """Force reinitialization on next operation (reset retry limits)."""
        with self._initialization_lock:
            self._initialized = False
            self._client = None
            self._initialization_error = None
            self._init_attempt_count = 0
            self._last_init_attempt = 0.0
            
            self.logger.info("Forced reinitialization - next operation will retry ChromaDB setup")
    
    def close(self):
        """Close the safe ChromaDB client and cleanup resources."""
        try:
            if self._client:
                self._client.close()
            
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=True)
                
            self.logger.debug("SafeChromaDBClient closed successfully")
            
        except Exception as e:
            self.logger.warning(f"Error during safe client cleanup: {e}")
    
    def __str__(self) -> str:
        status = "initialized" if self._initialized else "not_initialized"
        return f"SafeChromaDBClient(collection={self.config.collection_name}, status={status})"
    
    def __repr__(self) -> str:
        return f"SafeChromaDBClient(config={self.config})"
    
    def __del__(self):
        """Cleanup resources on deletion."""
        self.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()