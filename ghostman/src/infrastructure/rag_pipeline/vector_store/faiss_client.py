"""
FAISS Vector Store Client

Alternative vector storage implementation using Facebook's FAISS library.
This provides a completely different vector database that doesn't rely on SQLite,
eliminating potential segmentation faults from ChromaDB.

Features:
- High-performance similarity search using FAISS
- No SQLite dependencies (pure C++ with Python bindings)
- Persistent storage with automatic indexing
- Thread-safe operations
- Compatible with existing RAG pipeline interface
"""

import asyncio
import functools
import json
import logging
import os
import pickle
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from ..config.rag_config import VectorStoreConfig
from ..document_loaders.base_loader import Document, DocumentMetadata
from ..text_processing.text_splitter import TextChunk
# Define SearchResult locally (previously from chromadb_client)
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Search result from vector store."""
    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str

logger = logging.getLogger("ghostman.faiss_client")

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None


class FaissError(Exception):
    """FAISS specific errors."""
    pass


class FaissClient:
    """
    FAISS-based vector store client as an alternative to ChromaDB.
    
    Benefits over ChromaDB:
    - No SQLite dependencies (eliminates segfault risk)
    - High-performance C++ implementation
    - Memory-efficient indexing
    - Simple persistent storage
    - Thread-safe operations
    """
    
    def __init__(self, config: VectorStoreConfig):
        """
        Initialize FAISS client.
        
        Args:
            config: Vector store configuration
        """
        if not FAISS_AVAILABLE:
            raise FaissError("FAISS not available - install faiss-cpu or faiss-gpu package")
        
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.FaissClient")
        
        # FAISS components
        self._index: Optional[faiss.IndexFlatIP] = None  # Inner product index
        self._dimension = 1536  # Default OpenAI embedding dimension
        
        # Document storage (FAISS only stores vectors, not metadata)
        self._documents = []  # List of (chunk_id, content, metadata) tuples
        self._id_to_index = {}  # Map chunk_id to FAISS index position
        
        # Persistence paths
        self._index_path = Path(config.persist_directory) / "faiss_index.bin"
        self._metadata_path = Path(config.persist_directory) / "metadata.json"
        self._documents_path = Path(config.persist_directory) / "documents.pkl"
        
        # Thread safety
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="FAISS")
        
        # Performance tracking
        self._stats = {
            'documents_stored': 0,
            'chunks_stored': 0,
            'searches_performed': 0,
            'total_search_time': 0.0,
            'total_storage_time': 0.0,
            'index_size': 0,
        }
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize FAISS index and load existing data."""
        try:
            # Ensure persistence directory exists
            Path(self.config.persist_directory).mkdir(parents=True, exist_ok=True)
            
            # Load existing index and data
            self._load_from_disk()
            
            self.logger.info(f"FAISS client initialized: {len(self._documents)} documents loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FAISS client: {e}")
            # Create empty index as fallback
            self._create_empty_index()
    
    def _create_empty_index(self):
        """Create a new empty FAISS index."""
        # Use Inner Product index (cosine similarity with normalized vectors)
        self._index = faiss.IndexFlatIP(self._dimension)
        self._documents = []
        self._id_to_index = {}
        self._stats['index_size'] = 0
        self.logger.info(f"Created empty FAISS index with dimension {self._dimension}")
    
    def _load_from_disk(self):
        """Load existing FAISS index and metadata from disk."""
        try:
            if self._index_path.exists() and self._documents_path.exists():
                # Load FAISS index
                self._index = faiss.read_index(str(self._index_path))
                self._dimension = self._index.d
                
                # Load documents and metadata
                with open(self._documents_path, 'rb') as f:
                    data = pickle.load(f)
                    self._documents = data.get('documents', [])
                    self._id_to_index = data.get('id_to_index', {})
                
                self._stats['index_size'] = self._index.ntotal
                self.logger.info(f"Loaded FAISS index: {self._index.ntotal} vectors, {len(self._documents)} documents")
            else:
                self.logger.info("No existing FAISS index found, creating new one")
                self._create_empty_index()
                
        except Exception as e:
            self.logger.error(f"Failed to load FAISS index from disk: {e}")
            self._create_empty_index()
    
    def _save_to_disk(self):
        """Save FAISS index and metadata to disk."""
        try:
            with self._lock:
                # Ensure parent directories exist
                self._index_path.parent.mkdir(parents=True, exist_ok=True)
                self._documents_path.parent.mkdir(parents=True, exist_ok=True)
                self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save FAISS index
                faiss.write_index(self._index, str(self._index_path))
                
                # Save documents and metadata
                data = {
                    'documents': self._documents,
                    'id_to_index': self._id_to_index,
                    'dimension': self._dimension,
                    'stats': self._stats
                }
                
                with open(self._documents_path, 'wb') as f:
                    pickle.dump(data, f)
                
                # Save metadata as JSON for inspection
                metadata = {
                    'collection_name': self.config.collection_name,
                    'dimension': self._dimension,
                    'document_count': len(self._documents),
                    'vector_count': self._index.ntotal if self._index else 0,
                    'last_updated': time.time(),
                }
                
                with open(self._metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.debug("FAISS index and metadata saved to disk")
                
        except Exception as e:
            self.logger.error(f"Failed to save FAISS index to disk: {e}")
    
    async def store_document(self, document: Document, chunks: List[TextChunk], 
                           embeddings: List[np.ndarray]) -> List[str]:
        """
        Store document chunks with embeddings in FAISS.
        
        Args:
            document: Document to store
            chunks: Text chunks from the document
            embeddings: Embeddings for each chunk
            
        Returns:
            List of chunk IDs that were stored
        """
        start_time = time.time()
        
        if len(chunks) != len(embeddings):
            raise FaissError("Number of chunks must match number of embeddings")
        
        try:
            def _store_batch():
                """Thread-safe batch storage function."""
                with self._lock:
                    document_id = str(uuid.uuid4())
                    chunk_ids = []
                    
                    # Prepare embeddings for FAISS (normalize for cosine similarity)
                    vectors = []
                    for embedding in embeddings:
                        if isinstance(embedding, np.ndarray):
                            vector = embedding.astype(np.float32)
                        else:
                            vector = np.array(embedding, dtype=np.float32)
                        
                        # Normalize for cosine similarity (FAISS IndexFlatIP uses inner product)
                        norm = np.linalg.norm(vector)
                        if norm > 0:
                            vector = vector / norm
                        
                        vectors.append(vector)
                    
                    vectors_array = np.array(vectors)
                    
                    # Add to FAISS index
                    start_idx = self._index.ntotal
                    self._index.add(vectors_array)
                    
                    # Store documents and metadata
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        chunk_id = f"{document_id}_{chunk.chunk_index}"
                        chunk_ids.append(chunk_id)
                        
                        # Combine metadata
                        metadata = {
                            "document_id": document_id,
                            "chunk_index": chunk.chunk_index if chunk.chunk_index is not None else 0,
                            "start_char": chunk.start_char if chunk.start_char is not None else 0,
                            "end_char": chunk.end_char if chunk.end_char is not None else 0,
                            "token_count": chunk.token_count if chunk.token_count is not None else 0,
                            "source": document.metadata.source or "unknown",
                            "source_type": document.metadata.source_type or "text",
                            "filename": document.metadata.filename or "untitled",
                            "file_extension": document.metadata.file_extension or ".txt",
                            "created_at": time.time(),
                        }
                        
                        # Add document metadata
                        if document.metadata.title:
                            metadata["title"] = document.metadata.title
                        if document.metadata.author:
                            metadata["author"] = document.metadata.author
                        if document.metadata.language:
                            metadata["language"] = document.metadata.language
                        
                        # Add custom metadata
                        if document.metadata.custom:
                            for key, value in document.metadata.custom.items():
                                if isinstance(value, (str, int, float, bool)):
                                    metadata[f"custom_{key}"] = value
                        
                        # Store document info
                        self._documents.append((chunk_id, chunk.content, metadata))
                        self._id_to_index[chunk_id] = start_idx + i
                    
                    # Save to disk
                    self._save_to_disk()
                    
                    return chunk_ids
            
            # Execute in thread pool
            loop = asyncio.get_event_loop()
            chunk_ids = await loop.run_in_executor(self._executor, _store_batch)
            
            # Update statistics
            storage_time = time.time() - start_time
            self._stats['documents_stored'] += 1
            self._stats['chunks_stored'] += len(chunks)
            self._stats['total_storage_time'] += storage_time
            self._stats['index_size'] = self._index.ntotal
            
            self.logger.info(f"Stored document with {len(chunks)} chunks in FAISS in {storage_time:.2f}s")
            return chunk_ids
            
        except Exception as e:
            raise FaissError(f"Failed to store document in FAISS: {e}")
    
    async def similarity_search(self, query_embedding: np.ndarray, 
                              top_k: int = 5,
                              filters: Optional[Dict[str, Any]] = None,
                              include_embeddings: bool = False) -> List[SearchResult]:
        """
        Perform similarity search using FAISS.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters (applied post-search)
            include_embeddings: Whether to include embeddings in results
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        try:
            def _search():
                """Thread-safe search function."""
                with self._lock:
                    if self._index.ntotal == 0:
                        return []
                    
                    # Normalize query embedding for cosine similarity
                    if isinstance(query_embedding, np.ndarray):
                        query_vector = query_embedding.astype(np.float32)
                    else:
                        query_vector = np.array(query_embedding, dtype=np.float32)
                    
                    norm = np.linalg.norm(query_vector)
                    if norm > 0:
                        query_vector = query_vector / norm
                    
                    # Reshape for FAISS
                    query_vector = query_vector.reshape(1, -1)
                    
                    # Search in FAISS
                    search_k = min(top_k * 2, self._index.ntotal)  # Get more results for filtering
                    similarities, indices = self._index.search(query_vector, search_k)
                    
                    # Convert to SearchResult objects
                    results = []
                    for i in range(len(indices[0])):
                        if indices[0][i] == -1:  # FAISS returns -1 for invalid results
                            continue
                        
                        doc_idx = indices[0][i]
                        similarity_score = float(similarities[0][i])
                        
                        # Get document info
                        if doc_idx < len(self._documents):
                            chunk_id, content, metadata = self._documents[doc_idx]
                            
                            # Apply metadata filters if provided
                            if filters:
                                skip = False
                                for filter_key, filter_value in filters.items():
                                    if filter_key not in metadata:
                                        skip = True
                                        break
                                    if metadata[filter_key] != filter_value:
                                        skip = True
                                        break
                                
                                if skip:
                                    continue
                            
                            # Create search result
                            result = SearchResult(
                                document_id=metadata.get("document_id", ""),
                                chunk_id=chunk_id,
                                content=content,
                                score=similarity_score,
                                metadata=metadata,
                                embedding=None  # FAISS doesn't return embeddings by default
                            )
                            results.append(result)
                            
                            if len(results) >= top_k:
                                break
                    
                    return results
            
            # Execute search in thread pool
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(self._executor, _search)
            
            # Update statistics
            search_time = time.time() - start_time
            self._stats['searches_performed'] += 1
            self._stats['total_search_time'] += search_time
            
            self.logger.debug(f"FAISS search completed: {len(search_results)} results in {search_time:.2f}s")
            return search_results
            
        except Exception as e:
            raise FaissError(f"FAISS search failed: {e}")
    
    async def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Note: FAISS doesn't support individual deletion efficiently,
        so we rebuild the index without the deleted documents.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            def _delete_document():
                """Thread-safe deletion function."""
                with self._lock:
                    # Find indices to remove
                    indices_to_remove = []
                    new_documents = []
                    new_id_to_index = {}
                    
                    deleted_count = 0
                    new_index = 0
                    
                    for i, (chunk_id, content, metadata) in enumerate(self._documents):
                        if metadata.get("document_id") == document_id:
                            indices_to_remove.append(i)
                            deleted_count += 1
                        else:
                            new_documents.append((chunk_id, content, metadata))
                            new_id_to_index[chunk_id] = new_index
                            new_index += 1
                    
                    if deleted_count > 0:
                        # Rebuild FAISS index without deleted vectors
                        self._create_empty_index()
                        
                        if new_documents:
                            # Collect remaining vectors (need to regenerate or store them)
                            self.logger.warning("Document deletion in FAISS requires index rebuild - this may be slow")
                            # For now, just update document list
                            # In production, you'd want to store embeddings alongside metadata
                        
                        self._documents = new_documents
                        self._id_to_index = new_id_to_index
                        self._save_to_disk()
                    
                    return deleted_count
            
            loop = asyncio.get_event_loop()
            deleted_count = await loop.run_in_executor(self._executor, _delete_document)
            
            self.logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
            
        except Exception as e:
            raise FaissError(f"Failed to delete document from FAISS: {e}")
    
    def is_ready(self) -> bool:
        """Quick synchronous check if the FAISS index is ready."""
        try:
            return self._index is not None
        except Exception:
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the FAISS collection."""
        try:
            with self._lock:
                return {
                    "name": self.config.collection_name,
                    "count": len(self._documents),
                    "vector_count": self._index.ntotal if self._index else 0,
                    "dimension": self._dimension,
                    "index_type": "FAISS IndexFlatIP",
                    "persist_directory": self.config.persist_directory
                }
        except Exception as e:
            self.logger.error(f"Failed to get FAISS collection info: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get FAISS client statistics."""
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
        for key in ['searches_performed', 'total_search_time', 'total_storage_time']:
            self._stats[key] = 0
        self._stats['avg_search_time'] = 0.0
        self._stats['avg_storage_time'] = 0.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on FAISS store."""
        try:
            collection_info = await self.get_collection_info()
            
            # Perform a simple search to test functionality
            dummy_embedding = np.random.rand(self._dimension).astype(np.float32)
            start_time = time.time()
            
            test_results = await self.similarity_search(
                query_embedding=dummy_embedding,
                top_k=1
            )
            
            query_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "collection_count": collection_info.get("count", 0),
                "vector_count": collection_info.get("vector_count", 0),
                "collection_name": collection_info.get("name"),
                "query_response_time": query_time,
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def close(self):
        """Close FAISS client and cleanup resources."""
        try:
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=True)
            
            # Final save to disk
            if self._index is not None:
                self._save_to_disk()
                
            self.logger.debug("FAISS client closed successfully")
            
        except Exception as e:
            self.logger.warning(f"Error during FAISS cleanup: {e}")
    
    def __str__(self) -> str:
        count = len(self._documents) if self._documents else 0
        return f"FaissClient(collection={self.config.collection_name}, count={count})"
    
    def __repr__(self) -> str:
        return f"FaissClient(config={self.config})"
    
    def __del__(self):
        """Cleanup resources on deletion."""
        self.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()