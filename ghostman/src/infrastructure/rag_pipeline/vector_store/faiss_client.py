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
    document_id: Optional[str] = None
    embedding: Optional[np.ndarray] = None

logger = logging.getLogger("ghostman.faiss_client")

# Debug logger specifically for array comparison issues
debug_logger = logging.getLogger("ghostman.faiss_client.array_debug")
debug_logger.setLevel(logging.DEBUG)


def safe_array_comparison(metadata_value: Any, filter_value: Any, filter_key: str) -> bool:
    """
    Safely compare values that might be numpy arrays.
    
    This function handles the "truth value of an array with more than one element is ambiguous" error
    by properly handling numpy arrays, scalars, and regular Python types.
    
    Args:
        metadata_value: Value from metadata
        filter_value: Value to compare against
        filter_key: Key name for debugging
        
    Returns:
        True if values are equal, False otherwise
    """
    try:
        # ENHANCED DEBUG LOGGING
        debug_logger.debug(f"safe_array_comparison called: key='{filter_key}', meta_type={type(metadata_value)}, filter_type={type(filter_value)}")
        debug_logger.debug(f"metadata_value={metadata_value}, filter_value={filter_value}")
        # Handle numpy scalars and arrays
        if hasattr(metadata_value, 'item'):  # numpy scalar
            metadata_value = metadata_value.item()
            
        if hasattr(filter_value, 'item'):  # numpy scalar  
            filter_value = filter_value.item()
        
        # Handle numpy arrays specifically
        if isinstance(metadata_value, np.ndarray) or isinstance(filter_value, np.ndarray):
            # Convert both to arrays for comparison
            if not isinstance(metadata_value, np.ndarray):
                metadata_value = np.array(metadata_value)
            if not isinstance(filter_value, np.ndarray):
                filter_value = np.array(filter_value)
            
            # Check shapes first
            if metadata_value.shape != filter_value.shape:
                return False
            
            # For arrays, use array_equal for element-wise comparison
            try:
                result = np.array_equal(metadata_value, filter_value)
                return bool(result)  # Ensure we return a Python bool
            except Exception:
                return False
        
        # Regular comparison for non-array types
        result = metadata_value == filter_value
        
        # Ensure we return a Python bool, not a numpy bool or array
        if hasattr(result, 'item'):  # numpy scalar bool
            return result.item()
        elif hasattr(result, 'any'):  # This shouldn't happen, but safety check
            debug_logger.warning(f"Unexpected array result in regular comparison for '{filter_key}': {type(result)}")
            return bool(result.any())
        else:
            return bool(result)  # Convert to Python bool
        
    except Exception as e:
        debug_logger.error(f"Safe array comparison failed for '{filter_key}': {e}")
        return False


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
            # Ensure persistence directory exists with robust error handling
            persist_path = Path(self.config.persist_directory)
            try:
                persist_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"FAISS persistence directory ready: {persist_path}")
            except Exception as dir_error:
                self.logger.error(f"Failed to create FAISS directory {persist_path}: {dir_error}")
                # Try to use a temporary directory as fallback
                import tempfile
                temp_dir = Path(tempfile.gettempdir()) / "ghostman_faiss_emergency"
                temp_dir.mkdir(parents=True, exist_ok=True)
                self.config.persist_directory = str(temp_dir)
                self._index_path = temp_dir / "faiss_index.bin"
                self._metadata_path = temp_dir / "metadata.json"
                self._documents_path = temp_dir / "documents.pkl"
                self.logger.warning(f"Using emergency temp directory for FAISS: {temp_dir}")
            
            # Verify we can write to the directory
            try:
                test_file = persist_path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
                self.logger.debug("FAISS directory write test passed")
            except Exception as write_error:
                self.logger.error(f"Cannot write to FAISS directory {persist_path}: {write_error}")
                raise FaissError(f"FAISS directory not writable: {persist_path}")
            
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
        self._stats['documents_stored'] = 0
        self._stats['chunks_stored'] = 0
        self.logger.info(f"Created empty FAISS index with dimension {self._dimension}")
    
    def _load_from_disk(self):
        """Load existing FAISS index and metadata from disk."""
        try:
            # Check if required files exist
            if self._index_path.exists() and self._documents_path.exists():
                try:
                    # Load FAISS index with validation
                    self._index = faiss.read_index(str(self._index_path))
                    self._dimension = self._index.d
                    self.logger.debug(f"Loaded FAISS index from {self._index_path}")
                    
                    # Validate index
                    if self._index.ntotal < 0:
                        raise ValueError("Invalid FAISS index: negative vector count")
                    
                    # Load documents and metadata with validation
                    with open(self._documents_path, 'rb') as f:
                        data = pickle.load(f)
                        self._documents = data.get('documents', [])
                        self._id_to_index = data.get('id_to_index', {})
                    
                    # Validate loaded data consistency
                    if len(self._documents) > 0 and self._index.ntotal != len(self._documents):
                        self.logger.warning(f"Inconsistent data: {self._index.ntotal} vectors but {len(self._documents)} documents")
                        # Try to fix by rebuilding document list
                        if self._index.ntotal < len(self._documents):
                            self._documents = self._documents[:self._index.ntotal]
                            self.logger.info("Truncated document list to match index size")
                    
                    self._stats['index_size'] = self._index.ntotal
                    self._stats['documents_stored'] = len(self._documents)
                    self._stats['chunks_stored'] = self._index.ntotal
                    self.logger.info(f"Loaded FAISS index: {self._index.ntotal} vectors, {len(self._documents)} documents")
                    
                except Exception as load_error:
                    self.logger.error(f"Failed to load FAISS data files: {load_error}")
                    # Try to salvage what we can
                    self._try_salvage_index()
            else:
                missing_files = []
                if not self._index_path.exists():
                    missing_files.append(str(self._index_path))
                if not self._documents_path.exists():
                    missing_files.append(str(self._documents_path))
                
                self.logger.info(f"FAISS files missing: {missing_files}. Creating new index.")
                self._create_empty_index()
                
        except Exception as e:
            self.logger.error(f"Critical error loading FAISS index: {e}")
            self._create_empty_index()
    
    def _try_salvage_index(self):
        """Try to salvage a corrupted FAISS index."""
        try:
            self.logger.info("Attempting to salvage FAISS index...")
            
            # Try to load just the index
            if self._index_path.exists():
                try:
                    self._index = faiss.read_index(str(self._index_path))
                    self._dimension = self._index.d
                    self.logger.info("Successfully loaded FAISS index, documents list will be empty")
                    
                    # Reset documents since we can't load them
                    self._documents = []
                    self._id_to_index = {}
                    self._stats['index_size'] = self._index.ntotal
                    return
                except Exception:
                    self.logger.error("FAISS index file is corrupted")
            
            # If index is corrupted, try to load just documents
            if self._documents_path.exists():
                try:
                    with open(self._documents_path, 'rb') as f:
                        data = pickle.load(f)
                        self._documents = data.get('documents', [])
                        self._id_to_index = data.get('id_to_index', {})
                    
                    self.logger.info(f"Loaded {len(self._documents)} documents, but index is corrupted - creating new index")
                    self._create_empty_index()
                    return
                except Exception:
                    self.logger.error("Documents file is also corrupted")
            
            # Everything is corrupted, start fresh
            self.logger.warning("All FAISS files corrupted, starting with empty index")
            self._create_empty_index()
            
        except Exception as e:
            self.logger.error(f"Salvage operation failed: {e}")
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
                        
                        # Combine metadata - start with chunk metadata (includes conversation_id)
                        metadata = {}
                        
                        # Add chunk metadata first (this includes conversation_id and other overrides)
                        if hasattr(chunk, 'metadata') and chunk.metadata:
                            for key, value in chunk.metadata.items():
                                if isinstance(value, (str, int, float, bool)):
                                    metadata[key] = value
                        
                        # Then add document-level metadata (may override some chunk metadata)
                        metadata.update({
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
                        })
                        
                        # Add document metadata (won't override chunk metadata due to update order)
                        if document.metadata.title:
                            metadata["title"] = document.metadata.title
                        if document.metadata.author:
                            metadata["author"] = document.metadata.author
                        if document.metadata.language:
                            metadata["language"] = document.metadata.language
                        
                        # Add custom metadata from document
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
                    
                    # Ensure query_vector is 1D
                    if query_vector.ndim > 1:
                        query_vector = query_vector.flatten()
                    
                    norm = np.linalg.norm(query_vector)
                    if norm > 0:
                        query_vector = query_vector / norm
                    
                    # Validate dimensions
                    if query_vector.shape[0] != self._dimension:
                        raise FaissError(f"Query vector dimension {query_vector.shape[0]} doesn't match index dimension {self._dimension}")
                    
                    # Reshape for FAISS
                    query_vector = query_vector.reshape(1, -1)
                    
                    # Search in FAISS - use all documents when conversation isolation is needed
                    is_conversation_filter = (filters and 
                        ('conversation_id' in filters or 
                         'pending_conversation_id' in filters or 
                         '_or_pending_conversation_id' in filters))
                    
                    if is_conversation_filter:
                        # For conversation isolation, search ALL documents to ensure we find 
                        # conversation-specific files regardless of similarity ranking
                        search_k = self._index.ntotal
                        self.logger.warning(f"🔒 CONVERSATION ISOLATION: Searching ALL {search_k} documents")
                    else:
                        # For regular similarity search, use limited search
                        search_k = min(top_k * 2, self._index.ntotal)  # Get more results for filtering
                    try:
                        self.logger.warning(f"🔍 FAISS SEARCH: total vectors={self._index.ntotal}, search_k={search_k}, top_k={top_k}")
                        if filters:
                            self.logger.warning(f"🔍 FAISS SEARCH: Will apply filters after search: {filters}")
                        similarities, indices = self._index.search(query_vector, search_k)
                        self.logger.warning(f"🔍 FAISS SEARCH: Raw results count: {len([i for i in indices[0] if i != -1])}")
                        self.logger.warning(f"🔍 FAISS SEARCH: similarities={similarities[0][:5]}, indices={indices[0][:5]}")
                    except Exception as search_error:
                        self.logger.error(f"FAISS search failed: {search_error}")
                        self.logger.error(f"Query vector shape: {query_vector.shape}, dtype: {query_vector.dtype}")
                        self.logger.error(f"Index total: {self._index.ntotal}, dimension: {self._dimension}")
                        raise FaissError(f"FAISS search failed: {search_error}")
                    
                    # Convert to SearchResult objects
                    results = []
                    self.logger.debug(f"Processing {len(indices[0])} potential results, docs available: {len(self._documents)}")
                    for i in range(len(indices[0])):
                        index_value = int(indices[0][i])
                        if index_value == -1:  # FAISS returns -1 for invalid results
                            self.logger.debug(f"Skipping invalid result at position {i}")
                            continue
                        
                        doc_idx = index_value
                        similarity_score = float(similarities[0][i])
                        self.logger.debug(f"Result {i}: doc_idx={doc_idx}, score={similarity_score}")
                        
                        # Get document info
                        if doc_idx < len(self._documents):
                            chunk_id, content, metadata = self._documents[doc_idx]
                        else:
                            # Handle mismatch between index and documents
                            self.logger.warning(f"Document index {doc_idx} out of range (have {len(self._documents)} docs)")
                            # Create placeholder document
                            chunk_id = f"orphan_{doc_idx}"
                            content = f"[Orphaned vector at index {doc_idx}]"
                            metadata = {"orphaned": True, "index": doc_idx}
                        
                        # ENHANCED FILTERING: Support OR logic for conversation isolation
                        if filters:
                            skip = False                                
                            try:
                                self.logger.warning(f"🔍 FILTER DEBUG: Applying filters {filters} to document {chunk_id}")
                                self.logger.warning(f"🔍 FILTER DEBUG: Document metadata keys: {list(metadata.keys())}")
                                
                                # FIXED: Handle single pending_conversation_id filter (Tier 2 search)
                                if 'pending_conversation_id' in filters and 'conversation_id' not in filters and '_or_pending_conversation_id' not in filters:
                                    # This is a direct pending conversation search (Tier 2 in SmartContextSelector)
                                    pending_value = filters['pending_conversation_id']
                                    
                                    # ENHANCED DEBUG LOGGING
                                    self.logger.warning(f"🔍 PENDING FILTER: Looking for pending_conversation_id = {pending_value[:8]}...")
                                    self.logger.warning(f"🔍 PENDING FILTER: Document {chunk_id} metadata keys: {list(metadata.keys())}")
                                    
                                    if 'pending_conversation_id' in metadata:
                                        doc_pending_id = metadata['pending_conversation_id']
                                        # Handle numpy arrays/scalars safely
                                        if hasattr(doc_pending_id, 'item'):
                                            doc_pending_id = doc_pending_id.item()
                                        doc_id_str = str(doc_pending_id)[:8] if doc_pending_id is not None else 'None'
                                        self.logger.warning(f"🔍 PENDING FILTER: Document has pending_conversation_id = {doc_id_str}...")
                                        
                                        try:
                                            comparison_result = safe_array_comparison(metadata['pending_conversation_id'], pending_value, 'pending_conversation_id')
                                            if comparison_result:
                                                self.logger.warning(f"✅ PENDING FILTER: Document {chunk_id} MATCHES pending filter!")
                                                # Continue processing other filters if any
                                                remaining_filters = {k: v for k, v in filters.items() if k != 'pending_conversation_id'}
                                                if remaining_filters:
                                                    for filter_key, filter_value in remaining_filters.items():
                                                        if filter_key not in metadata:
                                                            skip = True
                                                            break
                                                        if not safe_array_comparison(metadata[filter_key], filter_value, filter_key):
                                                            skip = True
                                                            break
                                                    if skip:
                                                        continue
                                                # If we get here, all filters passed - don't skip this document
                                            else:
                                                self.logger.warning(f"❌ PENDING FILTER: Document {chunk_id} filtered out - pending mismatch ({doc_id_str}... != {pending_value[:8]}...)")
                                                skip = True
                                        except Exception as pending_error:
                                            self.logger.error(f"🔥 PENDING FILTER ERROR: {pending_error}")
                                            skip = True
                                        
                                        if skip:
                                            continue
                                    else:
                                        self.logger.warning(f"❌ PENDING FILTER: Document {chunk_id} filtered out - no pending_conversation_id in metadata")
                                        continue
                                # Handle special OR filtering for conversation isolation
                                elif 'conversation_id' in filters and '_or_pending_conversation_id' in filters:
                                    # Check if document belongs to this conversation via either field
                                    conv_id_value = filters['conversation_id']
                                    pending_conv_id_value = filters['_or_pending_conversation_id']
                                    
                                    # Document matches if it has matching conversation_id OR pending_conversation_id
                                    matches_conversation = (
                                        ('conversation_id' in metadata and safe_array_comparison(metadata['conversation_id'], conv_id_value, 'conversation_id')) or
                                        ('pending_conversation_id' in metadata and safe_array_comparison(metadata['pending_conversation_id'], pending_conv_id_value, 'pending_conversation_id'))
                                    )
                                    
                                    if matches_conversation:
                                        self.logger.debug(f"Document {chunk_id} matches conversation filter (OR logic)")
                                    else:
                                        self.logger.debug(f"Document {chunk_id} filtered out - no conversation match")
                                        continue
                                        
                                    # Skip regular filter processing for these special keys
                                    remaining_filters = {k: v for k, v in filters.items() 
                                                       if k not in ['conversation_id', '_or_pending_conversation_id']}
                                    if not remaining_filters:
                                        # Only conversation filters - we already processed them
                                        pass
                                    else:
                                        # Apply remaining filters normally
                                        for filter_key, filter_value in remaining_filters.items():
                                            if filter_key not in metadata:
                                                self.logger.debug(f"Filter key '{filter_key}' not found in metadata, skipping document")
                                                skip = True
                                                break
                                            
                                            metadata_value = metadata[filter_key]
                                            if not safe_array_comparison(metadata_value, filter_value, filter_key):
                                                self.logger.debug(f"Filter mismatch: '{filter_key}' value '{metadata_value}' != '{filter_value}', skipping document")
                                                skip = True
                                                break
                                else:
                                    # Regular filtering logic for other cases
                                    for filter_key, filter_value in filters.items():
                                        if filter_key.startswith('_or_'):
                                            # Skip special OR keys when not used with conversation_id
                                            continue

                                        # Special handling for collection_tag filter (supports list of tags)
                                        if filter_key == 'collection_tag' and isinstance(filter_value, list):
                                            # Check if document's collection_tag is IN the list
                                            if 'collection_tag' not in metadata:
                                                self.logger.debug(f"Document has no collection_tag, skipping")
                                                skip = True
                                                break

                                            doc_tag = metadata['collection_tag']
                                            # Handle numpy types
                                            if hasattr(doc_tag, 'item'):
                                                doc_tag = doc_tag.item()
                                            doc_tag = str(doc_tag) if doc_tag is not None else None

                                            # Check if document tag is in the filter list
                                            if doc_tag not in filter_value:
                                                self.logger.debug(f"Document collection_tag '{doc_tag}' not in {filter_value}, skipping")
                                                skip = True
                                                break
                                            else:
                                                self.logger.info(f"✅ Document collection_tag '{doc_tag}' matches filter {filter_value}")
                                            continue  # Skip to next filter

                                        if filter_key not in metadata:
                                            self.logger.debug(f"Filter key '{filter_key}' not found in metadata, skipping document")
                                            skip = True
                                            break

                                        metadata_value = metadata[filter_key]
                                        if not safe_array_comparison(metadata_value, filter_value, filter_key):
                                            self.logger.debug(f"Filter mismatch: '{filter_key}' value '{metadata_value}' != '{filter_value}', skipping document")
                                            skip = True
                                            break
                                        else:
                                            self.logger.debug(f"Filter match: '{filter_key}' value '{metadata_value}' == '{filter_value}'")
                                
                                if skip:
                                    self.logger.debug(f"Document {chunk_id} filtered out")
                                    continue
                                    
                            except Exception as filter_error:
                                self.logger.warning(f"Error during metadata filtering: {filter_error}")
                                # Skip this result to be safe
                                continue
                        
                        # Create search result
                        result = SearchResult(
                            content=content,
                            metadata=metadata,
                            score=similarity_score,
                            chunk_id=chunk_id,
                            document_id=metadata.get("document_id", ""),
                            embedding=None  # FAISS doesn't return embeddings by default
                        )
                        results.append(result)
                        self.logger.debug(f"Added result: {chunk_id} (score: {similarity_score})")
                        
                        if len(results) >= top_k:
                            break
                    
                    # FINAL RESULT DEBUG
                    self.logger.warning(f"🔍 FAISS SEARCH COMPLETE: Returning {len(results)} results after filtering")
                    if filters and len(results) == 0:
                        self.logger.warning(f"❌ FAISS SEARCH: No results survived filtering with {filters}")
                    
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
            # Specific handling for numpy array truth value error
            error_msg = str(e)
            if "truth value of an array" in error_msg.lower():
                debug_logger.error("❌ NUMPY ARRAY TRUTH VALUE ERROR DETECTED")
                debug_logger.error(f"Error: {error_msg}")
                debug_logger.error(f"Query embedding type: {type(query_embedding)}")
                debug_logger.error(f"Query embedding shape: {getattr(query_embedding, 'shape', 'N/A')}")
                debug_logger.error(f"Filters provided: {filters}")
                debug_logger.error("This error was caught and wrapped by the error isolation system")
                
                # Return empty results instead of crashing
                self.logger.error("FAISS search failed due to numpy array comparison issue - returning empty results")
                return []
            else:
                debug_logger.error(f"General FAISS search error: {error_msg}")
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
    
    def clear_all_documents(self):
        """Clear all documents and embeddings from the FAISS index."""
        try:
            with self._lock:
                self.logger.info("Clearing all documents from FAISS index")
                
                # Create a fresh empty index
                self._create_empty_index()
                
                # Clear all data structures
                self._documents = []
                self._id_to_index = {}
                
                # Reset stats
                self.reset_stats()
                
                # Save the cleared state to disk
                self._save_to_disk()
                
                self.logger.info("Successfully cleared all documents from FAISS index")
                
        except Exception as e:
            self.logger.error(f"Failed to clear documents: {e}")
            raise
    
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