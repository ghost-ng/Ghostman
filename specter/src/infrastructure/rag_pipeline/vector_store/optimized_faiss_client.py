"""
Optimized FAISS Vector Store Client - FAISS-Only Architecture

High-performance FAISS implementation optimized for PyQt6 applications:
- Synchronous operations (no unnecessary async overhead)
- Conversation-aware document filtering
- Thread-safe design with minimal locking
- Memory-efficient batch processing
- Direct integration with PyQt6 event loop
"""

import logging
import pickle
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from queue import Queue
import json

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker

from ..config.rag_config import VectorStoreConfig
from ..document_loaders.base_loader import Document, DocumentMetadata
from ..text_processing.text_splitter import TextChunk

# Import FAISS with error handling
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = logging.getLogger("specter.optimized_faiss_client")


@dataclass
class ConversationMetadata:
    """Metadata for conversation-specific document filtering."""
    conversation_id: str
    document_id: str
    source_file: str
    upload_timestamp: float
    chunk_index: int
    total_chunks: int


@dataclass
class OptimizedSearchResult:
    """Optimized search result with conversation context."""
    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str
    document_id: str
    conversation_id: Optional[str] = None
    embedding: Optional[np.ndarray] = None


class FaissOperationError(Exception):
    """FAISS operation specific errors."""
    pass


class OptimizedFaissClient(QObject):
    """
    Optimized FAISS client for PyQt6 applications.
    
    Key Optimizations:
    1. Synchronous operations - no async overhead
    2. Conversation-aware filtering
    3. Batch processing for embeddings
    4. Memory-efficient vector storage
    5. PyQt6 signal integration
    """
    
    # PyQt6 Signals
    document_indexed = pyqtSignal(str, int)  # document_id, chunk_count
    search_completed = pyqtSignal(str, int)  # query, result_count
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__()
        
        if not FAISS_AVAILABLE:
            raise FaissOperationError("FAISS not available - install faiss-cpu package")
        
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.OptimizedFaissClient")
        
        # FAISS components
        self._index: Optional[faiss.IndexFlatIP] = None
        self._dimension = 1536  # OpenAI embedding dimension
        
        # Optimized storage
        self._documents: List[tuple] = []  # (chunk_id, content, conversation_metadata)
        self._id_to_index: Dict[str, int] = {}
        self._conversation_index: Dict[str, List[int]] = {}  # conversation_id -> [indices]
        
        # Persistence
        self._index_path = Path(config.persist_directory) / "optimized_faiss_index.bin"
        self._metadata_path = Path(config.persist_directory) / "optimized_metadata.pkl"
        
        # Thread safety with minimal locking
        self._mutex = QMutex()
        self._executor = ThreadPoolExecutor(
            max_workers=2, 
            thread_name_prefix="OptimizedFAISS"
        )
        
        # Performance tracking
        self._stats = {
            'documents_indexed': 0,
            'chunks_indexed': 0,
            'searches_performed': 0,
            'avg_search_time': 0.0,
            'avg_indexing_time': 0.0,
            'memory_usage_mb': 0.0,
            'conversations_tracked': 0
        }
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize optimized FAISS client."""
        try:
            # Ensure directory exists
            persist_path = Path(self.config.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)
            
            # Load existing data or create new
            self._load_from_disk()
            
            self.logger.info(f"Optimized FAISS client ready: {len(self._documents)} chunks, "
                           f"{len(self._conversation_index)} conversations")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize optimized FAISS: {e}")
            self._create_empty_index()
    
    def _create_empty_index(self):
        """Create new empty optimized index."""
        with QMutexLocker(self._mutex):
            self._index = faiss.IndexFlatIP(self._dimension)
            self._documents = []
            self._id_to_index = {}
            self._conversation_index = {}
            self.logger.info("Created new optimized FAISS index")
    
    def _load_from_disk(self):
        """Load existing optimized index."""
        try:
            with QMutexLocker(self._mutex):
                if self._index_path.exists() and self._metadata_path.exists():
                    # Load FAISS index
                    self._index = faiss.read_index(str(self._index_path))
                    self._dimension = self._index.d
                    
                    # Load metadata
                    with open(self._metadata_path, 'rb') as f:
                        data = pickle.load(f)
                        self._documents = data.get('documents', [])
                        self._id_to_index = data.get('id_to_index', {})
                        self._conversation_index = data.get('conversation_index', {})
                        self._stats.update(data.get('stats', {}))
                    
                    self.logger.info(f"Loaded optimized FAISS: {self._index.ntotal} vectors")
                else:
                    self._create_empty_index()
                    
        except Exception as e:
            self.logger.error(f"Failed to load optimized FAISS: {e}")
            self._create_empty_index()
    
    def _save_to_disk(self):
        """Save optimized index to disk."""
        try:
            with QMutexLocker(self._mutex):
                # Save FAISS index
                faiss.write_index(self._index, str(self._index_path))
                
                # Save metadata
                data = {
                    'documents': self._documents,
                    'id_to_index': self._id_to_index,
                    'conversation_index': self._conversation_index,
                    'stats': self._stats,
                    'dimension': self._dimension,
                    'last_saved': time.time()
                }
                
                with open(self._metadata_path, 'wb') as f:
                    pickle.dump(data, f)
                    
        except Exception as e:
            self.logger.error(f"Failed to save optimized FAISS: {e}")
    
    def index_document_sync(
        self, 
        document: Document, 
        chunks: List[TextChunk], 
        embeddings: List[np.ndarray],
        conversation_id: str
    ) -> List[str]:
        """
        Synchronously index document with conversation context.
        
        Optimized for PyQt6 - no async overhead.
        """
        start_time = time.time()
        
        if len(chunks) != len(embeddings):
            raise FaissOperationError("Chunks and embeddings count mismatch")
        
        try:
            with QMutexLocker(self._mutex):
                document_id = str(uuid.uuid4())
                chunk_ids = []
                
                # Prepare normalized embeddings
                normalized_vectors = []
                for embedding in embeddings:
                    vector = np.array(embedding, dtype=np.float32)
                    if vector.ndim > 1:
                        vector = vector.flatten()
                    
                    # Normalize for cosine similarity
                    norm = np.linalg.norm(vector)
                    if norm > 0:
                        vector = vector / norm
                    
                    normalized_vectors.append(vector)
                
                vectors_array = np.array(normalized_vectors)
                
                # Add to FAISS index
                start_idx = self._index.ntotal
                self._index.add(vectors_array)
                
                # Store document metadata
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_id = f"{document_id}_{chunk.chunk_index}"
                    chunk_ids.append(chunk_id)
                    
                    # Create conversation metadata
                    conv_metadata = ConversationMetadata(
                        conversation_id=conversation_id,
                        document_id=document_id,
                        source_file=document.metadata.source or "unknown",
                        upload_timestamp=time.time(),
                        chunk_index=chunk.chunk_index or i,
                        total_chunks=len(chunks)
                    )
                    
                    # Enhanced metadata
                    full_metadata = {
                        **asdict(conv_metadata),
                        'content_preview': chunk.content[:100],
                        'token_count': chunk.token_count or 0,
                        'filename': document.metadata.filename,
                        'file_extension': document.metadata.file_extension
                    }
                    
                    # Store document tuple
                    doc_tuple = (chunk_id, chunk.content, full_metadata)
                    self._documents.append(doc_tuple)
                    self._id_to_index[chunk_id] = start_idx + i
                    
                    # Update conversation index
                    if conversation_id not in self._conversation_index:
                        self._conversation_index[conversation_id] = []
                    self._conversation_index[conversation_id].append(start_idx + i)
                
                # Save to disk
                self._save_to_disk()
                
                # Update statistics
                indexing_time = time.time() - start_time
                self._stats['documents_indexed'] += 1
                self._stats['chunks_indexed'] += len(chunks)
                self._stats['avg_indexing_time'] = (
                    (self._stats['avg_indexing_time'] * (self._stats['documents_indexed'] - 1) + indexing_time) / 
                    self._stats['documents_indexed']
                )
                self._stats['conversations_tracked'] = len(self._conversation_index)
                
                # Emit signal
                self.document_indexed.emit(document_id, len(chunks))
                
                self.logger.info(f"Indexed document {document_id}: {len(chunks)} chunks in {indexing_time:.2f}s")
                return chunk_ids
                
        except Exception as e:
            self.error_occurred.emit(f"Failed to index document: {str(e)}")
            raise FaissOperationError(f"Document indexing failed: {e}")
    
    def search_by_conversation_sync(
        self,
        query_embedding: np.ndarray,
        conversation_id: str,
        top_k: int = 5
    ) -> List[OptimizedSearchResult]:
        """
        Synchronous conversation-specific search.
        
        Optimized for PyQt6 with conversation filtering.
        """
        start_time = time.time()
        
        try:
            with QMutexLocker(self._mutex):
                if self._index.ntotal == 0:
                    return []
                
                # Get conversation-specific indices
                conversation_indices = self._conversation_index.get(conversation_id, [])
                if not conversation_indices:
                    self.logger.info(f"No documents found for conversation {conversation_id}")
                    return []
                
                # Normalize query embedding
                query_vector = np.array(query_embedding, dtype=np.float32)
                if query_vector.ndim > 1:
                    query_vector = query_vector.flatten()
                
                norm = np.linalg.norm(query_vector)
                if norm > 0:
                    query_vector = query_vector / norm
                
                query_vector = query_vector.reshape(1, -1)
                
                # Search entire index first
                search_k = min(top_k * 3, self._index.ntotal)
                similarities, indices = self._index.search(query_vector, search_k)
                
                # Filter results by conversation
                results = []
                for i in range(len(indices[0])):
                    idx = int(indices[0][i])
                    if idx == -1 or idx >= len(self._documents):
                        continue
                    
                    # Check if this index belongs to the conversation
                    if idx in conversation_indices:
                        chunk_id, content, metadata = self._documents[idx]
                        score = float(similarities[0][i])
                        
                        result = OptimizedSearchResult(
                            content=content,
                            metadata=metadata,
                            score=score,
                            chunk_id=chunk_id,
                            document_id=metadata['document_id'],
                            conversation_id=conversation_id
                        )
                        results.append(result)
                        
                        if len(results) >= top_k:
                            break
                
                # Update statistics
                search_time = time.time() - start_time
                self._stats['searches_performed'] += 1
                self._stats['avg_search_time'] = (
                    (self._stats['avg_search_time'] * (self._stats['searches_performed'] - 1) + search_time) / 
                    self._stats['searches_performed']
                )
                
                # Emit signal
                self.search_completed.emit(conversation_id, len(results))
                
                self.logger.debug(f"Conversation search: {len(results)} results in {search_time:.2f}s")
                return results
                
        except Exception as e:
            self.error_occurred.emit(f"Search failed: {str(e)}")
            raise FaissOperationError(f"Conversation search failed: {e}")
    
    def get_conversation_documents(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific conversation."""
        try:
            with QMutexLocker(self._mutex):
                conversation_indices = self._conversation_index.get(conversation_id, [])
                documents = []
                
                for idx in conversation_indices:
                    if idx < len(self._documents):
                        chunk_id, content, metadata = self._documents[idx]
                        documents.append({
                            'chunk_id': chunk_id,
                            'content_preview': content[:200],
                            'metadata': metadata
                        })
                
                return documents
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation documents: {e}")
            return []
    
    def remove_conversation_documents(self, conversation_id: str) -> int:
        """Remove all documents for a conversation (requires index rebuild)."""
        try:
            with QMutexLocker(self._mutex):
                if conversation_id not in self._conversation_index:
                    return 0
                
                # Get indices to remove
                indices_to_remove = set(self._conversation_index[conversation_id])
                removed_count = len(indices_to_remove)
                
                # Rebuild documents list without removed indices
                new_documents = []
                new_id_to_index = {}
                new_conversation_index = {}
                
                new_index = 0
                for old_index, (chunk_id, content, metadata) in enumerate(self._documents):
                    if old_index not in indices_to_remove:
                        new_documents.append((chunk_id, content, metadata))
                        new_id_to_index[chunk_id] = new_index
                        
                        # Update conversation index
                        conv_id = metadata.get('conversation_id')
                        if conv_id and conv_id != conversation_id:
                            if conv_id not in new_conversation_index:
                                new_conversation_index[conv_id] = []
                            new_conversation_index[conv_id].append(new_index)
                        
                        new_index += 1
                
                # Rebuild FAISS index (expensive operation)
                self._create_empty_index()
                self._documents = new_documents
                self._id_to_index = new_id_to_index
                self._conversation_index = new_conversation_index
                
                # Note: In production, you'd want to store embeddings and rebuild index properly
                self.logger.warning(f"Removed {removed_count} chunks for conversation {conversation_id}")
                self.logger.warning("FAISS index rebuild required - embeddings lost")
                
                self._save_to_disk()
                return removed_count
                
        except Exception as e:
            self.logger.error(f"Failed to remove conversation documents: {e}")
            return 0
    
    def get_optimized_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        with QMutexLocker(self._mutex):
            stats = self._stats.copy()
            stats.update({
                'total_chunks': len(self._documents),
                'total_conversations': len(self._conversation_index),
                'index_size': self._index.ntotal if self._index else 0,
                'memory_usage_mb': self._estimate_memory_usage(),
                'is_ready': self._index is not None
            })
            return stats
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            # Rough estimation
            vector_memory = self._index.ntotal * self._dimension * 4  # float32
            metadata_memory = len(self._documents) * 1024  # rough metadata size
            total_bytes = vector_memory + metadata_memory
            return total_bytes / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def is_ready(self) -> bool:
        """Check if client is ready for operations."""
        return self._index is not None
    
    def close(self):
        """Clean shutdown."""
        try:
            self._executor.shutdown(wait=True)
            if self._index is not None:
                self._save_to_disk()
            self.logger.info("Optimized FAISS client closed")
        except Exception as e:
            self.logger.warning(f"Error during optimized FAISS cleanup: {e}")


def create_optimized_faiss_client(config: VectorStoreConfig) -> OptimizedFaissClient:
    """Factory function for optimized FAISS client."""
    return OptimizedFaissClient(config)