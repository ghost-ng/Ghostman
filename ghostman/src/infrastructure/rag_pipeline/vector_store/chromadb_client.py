"""
ChromaDB Vector Store Client

Comprehensive ChromaDB integration for the RAG pipeline:
- Document storage and retrieval with embeddings
- Metadata filtering and search capabilities
- Collection management and persistence
- Batch operations for performance
- Integration with existing embedding service
"""

import asyncio
import functools
import logging
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

import numpy as np

from ..config.rag_config import VectorStoreConfig
from ..document_loaders.base_loader import Document, DocumentMetadata
from ..text_processing.text_splitter import TextChunk

logger = logging.getLogger("ghostman.chromadb_client")


@dataclass
class SearchResult:
    """Result from vector search."""
    document_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


class ChromaDBError(Exception):
    """ChromaDB specific errors."""
    pass


class ChromaDBClient:
    """
    Thread-safe ChromaDB client for vector storage and retrieval.
    
    Features:
    - Document and chunk storage with embeddings
    - Similarity search with metadata filtering
    - Collection management and persistence
    - Batch operations for performance
    - Integration with embedding services
    - Thread-safe operations to prevent segfaults
    """
    
    def __init__(self, config: VectorStoreConfig, embedding_function=None):
        """
        Initialize ChromaDB client.
        
        Args:
            config: Vector store configuration
            embedding_function: Optional custom embedding function
        """
        if not CHROMADB_AVAILABLE:
            raise ChromaDBError("ChromaDB not available - install chromadb package")
        
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ChromaDBClient")
        
        # Initialize ChromaDB client
        self._client = None
        self._collection = None
        self._embedding_function = embedding_function
        
        # Thread safety components
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ChromaDB")
        self._chromadb_thread_id = None
        
        # Performance tracking
        self._stats = {
            'documents_stored': 0,
            'chunks_stored': 0,
            'searches_performed': 0,
            'total_search_time': 0.0,
            'total_storage_time': 0.0,
        }
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Create ChromaDB settings
            settings = Settings(
                persist_directory=self.config.persist_directory,
                anonymized_telemetry=False
            )
            
            # Initialize client
            if self.config.host == "localhost" and not self.config.ssl:
                # Use persistent client for local storage
                self._client = chromadb.PersistentClient(
                    path=self.config.persist_directory,
                    settings=settings
                )
            else:
                # Use HTTP client for remote ChromaDB
                self._client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port,
                    ssl=self.config.ssl,
                    headers=self.config.headers,
                    settings=settings
                )
            
            # IMPORTANT: Do NOT set embedding function when we're providing embeddings manually
            # Setting an embedding function AND providing embeddings causes crashes/conflicts
            # Since the RAG pipeline generates embeddings itself, we don't need ChromaDB to do it
            if self._embedding_function is None:
                # Keep embedding_function as None - we'll provide embeddings manually
                self.logger.info("ChromaDB configured for manual embedding provision (no embedding function)")
                pass  # Explicitly do nothing - no embedding function needed
            
            # Get or create collection
            self._get_or_create_collection()
            
            self.logger.info(f"ChromaDB client initialized: {self.config.collection_name}")
            
        except Exception as e:
            raise ChromaDBError(f"Failed to initialize ChromaDB client: {e}")
    
    def _get_or_create_collection(self):
        """Get or create the document collection."""
        try:
            # Try to get existing collection
            self._collection = self._client.get_collection(
                name=self.config.collection_name,
                embedding_function=self._embedding_function
            )
            self.logger.info(f"Using existing collection: {self.config.collection_name}")
            
        except Exception:
            # Create new collection
            metadata = {
                "hnsw:space": self.config.distance_function,
                "created_at": datetime.now().isoformat(),
                "ghostman_version": "1.0"
            }
            
            self._collection = self._client.create_collection(
                name=self.config.collection_name,
                embedding_function=self._embedding_function,
                metadata=metadata
            )
            self.logger.info(f"Created new collection: {self.config.collection_name}")
    
    async def store_document(self, document: Document, chunks: List[TextChunk], 
                           embeddings: List[np.ndarray]) -> List[str]:
        """
        Store document chunks with embeddings.
        
        Args:
            document: Document to store
            chunks: Text chunks from the document
            embeddings: Embeddings for each chunk
            
        Returns:
            List of chunk IDs that were stored
        """
        start_time = time.time()
        
        if len(chunks) != len(embeddings):
            raise ChromaDBError("Number of chunks must match number of embeddings")
        
        try:
            # Prepare data for ChromaDB
            chunk_ids = []
            chunk_contents = []
            chunk_embeddings = []
            chunk_metadatas = []
            
            document_id = str(uuid.uuid4())
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{document_id}_{chunk.chunk_index}"
                chunk_ids.append(chunk_id)
                chunk_contents.append(chunk.content)
                chunk_embeddings.append(embedding.tolist() if isinstance(embedding, np.ndarray) else embedding)
                
                # Combine document and chunk metadata (filter out None values)
                combined_metadata = {
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index if chunk.chunk_index is not None else 0,
                    "start_char": chunk.start_char if chunk.start_char is not None else 0,
                    "end_char": chunk.end_char if chunk.end_char is not None else 0,
                    "token_count": chunk.token_count if chunk.token_count is not None else 0,
                    "source": document.metadata.source or "unknown",
                    "source_type": document.metadata.source_type or "text",
                    "filename": document.metadata.filename or "untitled",
                    "file_extension": document.metadata.file_extension or ".txt",
                    "created_at": datetime.now().isoformat(),
                }
                
                # Add document metadata
                if document.metadata.title:
                    combined_metadata["title"] = document.metadata.title
                if document.metadata.author:
                    combined_metadata["author"] = document.metadata.author
                if document.metadata.language:
                    combined_metadata["language"] = document.metadata.language
                if document.metadata.created_at:
                    combined_metadata["document_created_at"] = document.metadata.created_at.isoformat()
                
                # Add custom metadata
                if document.metadata.custom:
                    for key, value in document.metadata.custom.items():
                        if isinstance(value, (str, int, float, bool)):
                            combined_metadata[f"custom_{key}"] = value
                
                # Add chunk metadata
                if chunk.metadata:
                    for key, value in chunk.metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            combined_metadata[f"chunk_{key}"] = value
                
                chunk_metadatas.append(combined_metadata)
            
            # Store in ChromaDB in batches
            await self._store_batch(chunk_ids, chunk_contents, chunk_embeddings, chunk_metadatas)
            
            # Update statistics
            storage_time = time.time() - start_time
            self._stats['documents_stored'] += 1
            self._stats['chunks_stored'] += len(chunks)
            self._stats['total_storage_time'] += storage_time
            
            self.logger.info(f"Stored document with {len(chunks)} chunks in {storage_time:.2f}s")
            return chunk_ids
            
        except Exception as e:
            raise ChromaDBError(f"Failed to store document: {e}")
    
    async def _store_batch(self, ids: List[str], documents: List[str], 
                          embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Store documents in batches for performance using thread-safe operations."""
        batch_size = self.config.max_batch_size
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            # CRITICAL FIX: Use dedicated single-threaded executor for ChromaDB operations
            # This prevents SQLite connection corruption across threads
            def _safe_add_batch():
                """Thread-safe batch addition function."""
                with self._lock:
                    # Ensure ChromaDB operations run in the same thread consistently
                    current_thread = threading.current_thread().ident
                    if self._chromadb_thread_id is None:
                        self._chromadb_thread_id = current_thread
                        self.logger.debug(f"ChromaDB operations bound to thread {current_thread}")
                    elif self._chromadb_thread_id != current_thread:
                        raise RuntimeError(f"ChromaDB thread safety violation: expected {self._chromadb_thread_id}, got {current_thread}")
                    
                    return self._collection.add(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        metadatas=batch_metadatas,
                        documents=batch_docs
                    )
            
            # Execute in dedicated single-threaded executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _safe_add_batch)
    
    async def similarity_search(self, query_embedding: np.ndarray, 
                              top_k: int = 5,
                              filters: Optional[Dict[str, Any]] = None,
                              include_embeddings: bool = False) -> List[SearchResult]:
        """
        Perform similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
            include_embeddings: Whether to include embeddings in results
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        try:
            # Prepare query
            query_embeddings = [query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding]
            
            # Prepare include list
            include_list = ["documents", "metadatas", "distances"]
            if include_embeddings:
                include_list.append("embeddings")
            
            # Execute search using thread-safe operations
            def _safe_query():
                """Thread-safe query function."""
                with self._lock:
                    return self._collection.query(
                        query_embeddings=query_embeddings,
                        n_results=top_k,
                        where=filters,
                        include=include_list
                    )
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(self._executor, _safe_query)
            
            # Convert to SearchResult objects
            search_results = []
            
            if results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                documents = results["documents"][0] if results["documents"] else [None] * len(ids)
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
                distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
                embeddings = results.get("embeddings", [[None] * len(ids)])[0] if include_embeddings else [None] * len(ids)
                
                for i, chunk_id in enumerate(ids):
                    metadata = metadatas[i] or {}
                    
                    # Normalize distance to similarity score in [0,1]
                    similarity = 1.0 / (1.0 + distances[i])
                    result = SearchResult(
                        document_id=metadata.get("document_id", ""),
                        chunk_id=chunk_id,
                        content=documents[i] or "",
                        score=similarity,
                        metadata=metadata,
                        embedding=np.array(embeddings[i]) if embeddings[i] else None
                    )
                    search_results.append(result)
            
            # Update statistics
            search_time = time.time() - start_time
            self._stats['searches_performed'] += 1
            self._stats['total_search_time'] += search_time
            
            self.logger.debug(f"Search completed: {len(search_results)} results in {search_time:.2f}s")
            return search_results
            
        except Exception as e:
            raise ChromaDBError(f"Search failed: {e}")
    
    async def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            # Find all chunks for this document
            results = await self.similarity_search(
                query_embedding=np.zeros(1536),  # Dummy embedding
                top_k=10000,  # Large number to get all
                filters={"document_id": document_id}
            )
            
            if not results:
                return 0
            
            chunk_ids = [result.chunk_id for result in results]
            
            # Delete chunks using thread-safe operations
            def _safe_delete():
                """Thread-safe delete function."""
                with self._lock:
                    return self._collection.delete(ids=chunk_ids)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _safe_delete)
            
            self.logger.info(f"Deleted {len(chunk_ids)} chunks for document {document_id}")
            return len(chunk_ids)
            
        except Exception as e:
            raise ChromaDBError(f"Failed to delete document: {e}")
    
    async def update_chunk_metadata(self, chunk_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a specific chunk.
        
        Args:
            chunk_id: Chunk ID to update
            metadata: New metadata
            
        Returns:
            True if successful
        """
        try:
            def _safe_update():
                """Thread-safe update function."""
                with self._lock:
                    return self._collection.update(
                        ids=[chunk_id],
                        embeddings=None,
                        metadatas=[metadata],
                        documents=None
                    )
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _safe_update)
            
            self.logger.debug(f"Updated metadata for chunk {chunk_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update chunk metadata: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Quick synchronous check if the collection is ready."""
        try:
            return self._collection is not None and self._client is not None
        except Exception:
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            def _safe_get_info():
                """Thread-safe collection info retrieval."""
                with self._lock:
                    count = self._collection.count()
                    metadata = getattr(self._collection, 'metadata', {}) or {}
                    return count, metadata
            
            loop = asyncio.get_event_loop()
            count, metadata = await loop.run_in_executor(self._executor, _safe_get_info)
            
            return {
                "name": self.config.collection_name,
                "count": count,
                "metadata": metadata,
                "distance_function": self.config.distance_function,
                "persist_directory": self.config.persist_directory
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self._stats.copy()
        
        # Calculate derived metrics
        if stats['searches_performed'] > 0:
            stats['avg_search_time'] = stats['total_search_time'] / stats['searches_performed']
        else:
            stats['avg_search_time'] = 0.0
        
        if stats['documents_stored'] > 0:
            stats['avg_storage_time'] = stats['total_storage_time'] / stats['documents_stored']
            stats['avg_chunks_per_document'] = stats['chunks_stored'] / stats['documents_stored']
        else:
            stats['avg_storage_time'] = 0.0
            stats['avg_chunks_per_document'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        for key in self._stats:
            self._stats[key] = 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the vector store."""
        try:
            # Check if client is connected
            collection_info = await self.get_collection_info()
            
            # Perform a simple query to test functionality
            dummy_embedding = np.random.rand(1536).tolist()
            start_time = time.time()
            
            test_results = await self.similarity_search(
                query_embedding=dummy_embedding,
                top_k=1
            )
            
            query_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "collection_count": collection_info.get("count", 0),
                "collection_name": collection_info.get("name"),
                "query_response_time": query_time,
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def backup_collection(self, backup_path: str) -> bool:
        """
        Backup collection data.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if successful
        """
        try:
            # This is a simplified backup - in production you might want
            # to export all data and metadata
            import json
            
            collection_info = await self.get_collection_info()
            stats = self.get_stats()
            
            backup_data = {
                "collection_info": collection_info,
                "stats": stats,
                "backup_time": datetime.now().isoformat(),
                "config": {
                    "collection_name": self.config.collection_name,
                    "distance_function": self.config.distance_function,
                    "persist_directory": self.config.persist_directory
                }
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self.logger.info(f"Collection backup saved to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
    
    def __str__(self) -> str:
        return f"ChromaDBClient(collection={self.config.collection_name}, count={self._collection.count() if self._collection else 0})"
    
    def __repr__(self) -> str:
        return f"ChromaDBClient(config={self.config})"
    
    def __del__(self):
        """Cleanup resources on deletion."""
        self.close()
    
    def close(self):
        """Close the ChromaDB client and cleanup resources."""
        try:
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=True)
                self.logger.debug("ChromaDB executor shutdown successfully")
        except Exception as e:
            self.logger.warning(f"Error during ChromaDB cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()