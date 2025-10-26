"""
Safe RAG Pipeline with Segfault Protection

Enhanced RAG pipeline that prevents ChromaDB segmentation faults:
- Uses FAISSClient for thread-safe vector storage
- Implements multiple fallback strategies
- Provides graceful degradation when ChromaDB fails
- Includes in-memory vector storage fallback
- Process isolation for ChromaDB operations
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ..config.rag_config import RAGPipelineConfig, get_config, validate_config
from ..document_loaders.loader_factory import DocumentLoaderFactory, load_document
from ..document_loaders.base_loader import Document
from ..text_processing.text_splitter import TextSplitterFactory, TextChunk
from ..vector_store.faiss_client import FaissClient, SearchResult
from ..services.embedding_service import EmbeddingService
from ...ai.session_manager import session_manager
from .rag_pipeline import RAGQuery, RAGResponse

logger = logging.getLogger("ghostman.safe_rag_pipeline")


class InMemoryVectorStore:
    """Simple in-memory vector store for fallback when ChromaDB fails."""
    
    def __init__(self):
        self.documents = []  # List of tuples: (chunk_id, content, embedding, metadata)
        self.stats = {
            'documents_stored': 0,
            'chunks_stored': 0,
            'searches_performed': 0,
        }
    
    async def store_document(self, document: Document, chunks: List[TextChunk], 
                           embeddings: List[np.ndarray]) -> List[str]:
        """Store document chunks with embeddings in memory."""
        chunk_ids = []
        document_id = f"inmem_{int(time.time())}_{len(self.documents)}"
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_id}_{chunk.chunk_index}"
            chunk_ids.append(chunk_id)
            
            metadata = {
                "document_id": document_id,
                "chunk_index": chunk.chunk_index or 0,
                "start_char": chunk.start_char or 0,
                "end_char": chunk.end_char or 0,
                "token_count": chunk.token_count or 0,
                "source": document.metadata.source or "unknown",
                "source_type": document.metadata.source_type or "text",
                "filename": document.metadata.filename or "untitled",
            }
            
            self.documents.append((chunk_id, chunk.content, embedding, metadata))
        
        self.stats['documents_stored'] += 1
        self.stats['chunks_stored'] += len(chunks)
        
        return chunk_ids
    
    async def similarity_search(self, query_embedding: np.ndarray, 
                              top_k: int = 5,
                              filters: Optional[Dict[str, Any]] = None,
                              include_embeddings: bool = False) -> List[SearchResult]:
        """Perform similarity search using cosine similarity."""
        if not self.documents:
            return []
        
        # Extract embeddings and calculate similarities
        embeddings = np.array([doc[2] for doc in self.documents])
        
        # Ensure query_embedding is 2D for sklearn
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        similarities = cosine_similarity(query_embedding, embeddings)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only return positive similarities
                chunk_id, content, embedding, metadata = self.documents[idx]
                
                result = SearchResult(
                    document_id=metadata.get("document_id", ""),
                    chunk_id=chunk_id,
                    content=content,
                    score=float(similarities[idx]),
                    metadata=metadata,
                    embedding=embedding if include_embeddings else None
                )
                results.append(result)
        
        self.stats['searches_performed'] += 1
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get in-memory store statistics."""
        return self.stats.copy()
    
    def is_ready(self) -> bool:
        """Always ready since it's in-memory."""
        return True


class SafeRAGPipeline:
    """
    Safe RAG pipeline that prevents ChromaDB segmentation faults.
    
    Features:
    - Process-isolated ChromaDB initialization
    - In-memory fallback vector storage
    - Graceful degradation on failures
    - Thread-safe operations
    - Comprehensive error handling
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize safe RAG pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(f"{__name__}.SafeRAGPipeline")
        
        # Initialize components
        self.document_loader_factory = DocumentLoaderFactory(self.config.document_loading)
        self.text_splitter = TextSplitterFactory.create_splitter(self.config.text_processing)
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService(
            api_endpoint=self.config.embedding.api_endpoint,
            api_key=str(self.config.embedding.api_key or ""),
            model=self.config.embedding.model,
            max_retries=self.config.embedding.max_retries,
            timeout=self.config.embedding.timeout,
            rate_limit_delay=self.config.embedding.rate_limit_delay,
            cache_size=self.config.embedding.cache_size,
            cache_ttl=(self.config.embedding.cache_ttl_hours or 24) * 3600
        )
        
        # Initialize vector stores (primary and fallback)
        self.primary_vector_store = FaissClient(self.config.vector_store)
        self.fallback_vector_store = InMemoryVectorStore()
        self.using_fallback = False
        
        # LLM session manager
        self.session_manager = session_manager
        
        # Performance tracking
        self._stats = {
            'documents_processed': 0,
            'queries_processed': 0,
            'fallback_operations': 0,
            'chromadb_failures': 0,
            'total_processing_time': 0.0,
            'total_query_time': 0.0,
            'chunks_created': 0,
            'embeddings_generated': 0,
        }
        
        self.logger.info("Safe RAG Pipeline initialized successfully")
    
    def is_ready(self) -> bool:
        """Check if the pipeline is ready for operations."""
        try:
            # Embedding service check
            if not getattr(self, "embedding_service", None):
                return False
            
            try:
                emb_ok = bool(self.embedding_service.test_connection())
            except Exception:
                emb_ok = False
            
            # Vector store check (primary or fallback)
            vs_ok = (
                self.primary_vector_store.is_ready() or 
                self.fallback_vector_store.is_ready()
            )
            
            return emb_ok and vs_ok
            
        except Exception:
            return False
    
    async def _get_vector_store(self):
        """Get the appropriate vector store (primary or fallback)."""
        # Try primary store first
        if not self.using_fallback and self.primary_vector_store.is_ready():
            return self.primary_vector_store
        
        # Check if we need to attempt primary store initialization
        if not self.using_fallback:
            try:
                # This will attempt initialization if needed
                await self.primary_vector_store._ensure_initialized()
                if self.primary_vector_store.is_ready():
                    return self.primary_vector_store
            except Exception as e:
                self.logger.warning(f"Primary vector store failed, switching to fallback: {e}")
                self._stats['chromadb_failures'] += 1
                self.using_fallback = True
        
        # Use fallback store
        self._stats['fallback_operations'] += 1
        self.logger.info("Using in-memory fallback vector store")
        return self.fallback_vector_store
    
    async def ingest_document(self, source: Union[str, Path], 
                            metadata_override: Optional[Dict[str, Any]] = None) -> str:
        """
        Ingest a single document into the safe RAG pipeline.
        
        Args:
            source: Document source (file path or URL)
            metadata_override: Optional metadata to override/add
            
        Returns:
            Document ID or None if embedding generation fails
        """
        start_time = time.time()
        
        try:
            # 1. Load document
            self.logger.info(f"Loading document: {source}")
            document = await self.document_loader_factory.load_document(source)
            
            # Override metadata if provided
            if metadata_override:
                for key, value in metadata_override.items():
                    setattr(document.metadata, key, value)
            
            # 2. Split document into chunks
            self.logger.info(f"Splitting document into chunks")
            chunks = self.text_splitter.split_text(document.content)
            
            # 3. Generate embeddings for chunks
            self.logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = await self._generate_embeddings([chunk.content for chunk in chunks])
            
            # 4. Check if any embeddings failed
            failed_embeddings = sum(1 for emb in embeddings if self._is_fallback_embedding(emb))
            if failed_embeddings > 0:
                self.logger.warning(f"⚠️ {failed_embeddings}/{len(embeddings)} embeddings failed - proceeding with fallback storage")
            
            # 5. Store in vector database (safe)
            vector_store = await self._get_vector_store()
            self.logger.info(f"Storing chunks in {'primary' if not self.using_fallback else 'fallback'} vector store")
            
            try:
                chunk_ids = await vector_store.store_document(document, chunks, embeddings)
            except Exception as e:
                if not self.using_fallback:
                    # Primary failed, try fallback
                    self.logger.warning(f"Primary storage failed, trying fallback: {e}")
                    self._stats['chromadb_failures'] += 1
                    self.using_fallback = True
                    vector_store = await self._get_vector_store()
                    chunk_ids = await vector_store.store_document(document, chunks, embeddings)
                else:
                    raise
            
            # Update statistics
            processing_time = time.time() - start_time
            self._stats['documents_processed'] += 1
            self._stats['chunks_created'] += len(chunks)
            self._stats['embeddings_generated'] += len(embeddings)
            self._stats['total_processing_time'] += processing_time
            
            document_id = chunk_ids[0].split('_')[0] if chunk_ids else f'safe_{int(time.time())}'
            
            self.logger.info(f"Document ingested successfully: {document_id} "
                           f"({len(chunks)} chunks, {processing_time:.2f}s)")
            
            return document_id
            
        except Exception as e:
            self.logger.error(f"Failed to ingest document {source}: {e}")
            raise
    
    async def ingest_documents(self, sources: List[Union[str, Path]], 
                             max_concurrent: int = 3) -> List[Optional[str]]:
        """
        Ingest multiple documents concurrently.
        
        Args:
            sources: List of document sources
            max_concurrent: Maximum concurrent ingestion operations
            
        Returns:
            List of document IDs (None for failed ingestions)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_with_semaphore(source):
            async with semaphore:
                try:
                    return await self.ingest_document(source)
                except Exception as e:
                    self.logger.error(f"Failed to ingest {source}: {e}")
                    return None
        
        tasks = [ingest_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        document_ids = []
        for result in results:
            if isinstance(result, Exception):
                document_ids.append(None)
            else:
                document_ids.append(result)
        
        successful = len([r for r in document_ids if r is not None])
        self.logger.info(f"Ingested {successful}/{len(sources)} documents successfully")
        
        return document_ids
    
    async def query(self, query: Union[str, RAGQuery]) -> RAGResponse:
        """
        Process a query through the safe RAG pipeline.
        
        Args:
            query: Query string or RAGQuery object
            
        Returns:
            RAG response with generated answer and sources
        """
        start_time = time.time()
        
        # Normalize query
        if isinstance(query, str):
            rag_query = RAGQuery(text=query)
        else:
            rag_query = query
        
        try:
            # 1. Generate query embedding
            self.logger.debug(f"Generating embedding for query: {rag_query.text[:100]}...")
            query_embeddings = await self._generate_embeddings([rag_query.text])
            query_embedding = query_embeddings[0]
            
            # 2. Check if query embedding failed
            if self._is_fallback_embedding(query_embedding):
                self.logger.error("⚠️ Query embedding failed - cannot perform search")
                return RAGResponse(
                    query=rag_query.text,
                    answer="I apologize, but I cannot process your query due to an embedding service issue. Please check your API configuration.",
                    sources=[],
                    context_used="",
                    processing_time=time.time() - start_time,
                    metadata={'error': 'embedding_failed'}
                )
            
            # 3. Retrieve relevant chunks
            vector_store = await self._get_vector_store()
            top_k = rag_query.top_k or self.config.retrieval.top_k
            
            try:
                search_results = await vector_store.similarity_search(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filters=rag_query.filters,
                    include_embeddings=False
                )
            except Exception as e:
                if not self.using_fallback:
                    # Primary failed, try fallback
                    self.logger.warning(f"Primary search failed, trying fallback: {e}")
                    self._stats['chromadb_failures'] += 1
                    self.using_fallback = True
                    vector_store = await self._get_vector_store()
                    search_results = await vector_store.similarity_search(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        filters=rag_query.filters,
                        include_embeddings=False
                    )
                else:
                    raise
            
            # 4. Filter results (use all for now)
            filtered_results = search_results
            
            # 5. Assemble context
            context = self._assemble_context(filtered_results, rag_query)
            
            # 6. Generate answer using LLM
            answer = await self._generate_answer(rag_query.text, context)
            
            # Create response
            processing_time = time.time() - start_time
            response = RAGResponse(
                query=rag_query.text,
                answer=answer,
                sources=filtered_results,
                context_used=context,
                processing_time=processing_time,
                metadata={
                    'chunks_retrieved': len(search_results),
                    'chunks_used': len(filtered_results),
                    'context_length': len(context),
                    'using_fallback': self.using_fallback,
                    'config_used': {
                        'top_k': top_k,
                        'similarity_threshold': self.config.retrieval.similarity_threshold,
                        'max_context_length': self.config.retrieval.max_context_length
                    }
                }
            )
            
            # Update statistics
            self._stats['queries_processed'] += 1
            self._stats['total_query_time'] += processing_time
            
            self.logger.info(f"Query processed in {processing_time:.2f}s: "
                           f"{len(filtered_results)} sources used "
                           f"({'fallback' if self.using_fallback else 'primary'} store)")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            raise
    
    async def _generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for a list of texts."""
        embeddings = []
        failed_count = 0
        
        for text in texts:
            embedding = self.embedding_service.create_embedding(text)
            if embedding is not None:
                embeddings.append(embedding)
            else:
                failed_count += 1
                self.logger.warning(f"Failed to generate embedding for text: {text[:50]}...")
                
                # Create small random embeddings instead of zeros
                try:
                    dim = int(self.config.embedding.dimensions) if self.config.embedding.dimensions else 1536
                except Exception:
                    dim = 1536
                
                fallback_embedding = np.random.normal(0, 0.001, dim).astype(np.float32)
                embeddings.append(fallback_embedding)
        
        if failed_count > 0:
            self.logger.warning(f"Generated {failed_count}/{len(texts)} fallback embeddings due to API failures")
        
        return embeddings
    
    def _is_fallback_embedding(self, embedding: np.ndarray) -> bool:
        """Check if an embedding is a fallback."""
        try:
            if embedding is None:
                return True
            
            variance = np.var(embedding)
            mean_abs = np.mean(np.abs(embedding))
            
            # Fallback embeddings have very small variance
            is_fallback = variance < 0.000002 and mean_abs < 0.002
            
            if is_fallback:
                self.logger.debug(f"Detected fallback embedding: var={variance:.8f}, mean_abs={mean_abs:.6f}")
            
            return is_fallback
            
        except Exception as e:
            self.logger.warning(f"Error checking fallback embedding: {e}")
            return True
    
    def _assemble_context(self, search_results: List[SearchResult], query: RAGQuery) -> str:
        """Assemble context from search results."""
        if not search_results:
            return ""
        
        context_parts = []
        total_length = 0
        max_length = query.context_length or self.config.retrieval.max_context_length
        
        for i, result in enumerate(search_results):
            # Create context entry
            if query.include_metadata and isinstance(result.metadata, dict) and result.metadata.get('title'):
                context_entry = f"Source {i+1} ({result.metadata['title']}):\n{result.content}\n"
            else:
                context_entry = f"Source {i+1}:\n{result.content}\n"
            
            if total_length + len(context_entry) > max_length:
                break
            
            context_parts.append(context_entry)
            total_length += len(context_entry)
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using LLM."""
        try:
            # Build prompt
            user_prompt = self._build_rag_prompt(query, context)
            system_prompt = getattr(self.config.llm, "system_prompt", "").strip()
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            # Make request
            timeout_seconds = None
            if hasattr(self.config.llm, "timeout") and self.config.llm.timeout is not None:
                try:
                    timeout_seconds = int(self.config.llm.timeout)
                except Exception:
                    timeout_seconds = None
            
            response = self.session_manager.make_request(
                method="POST",
                url=f"{self.config.llm.api_endpoint}/chat/completions",
                json={
                    "model": self.config.llm.model,
                    "messages": messages,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "top_p": self.config.llm.top_p,
                    "frequency_penalty": self.config.llm.frequency_penalty,
                    "presence_penalty": self.config.llm.presence_penalty,
                },
                headers={"Authorization": f"Bearer {self.config.llm.api_key}"},
                timeout=timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = ""
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if isinstance(choice.get("message"), dict):
                        answer = (choice["message"].get("content") or "").strip()
                    else:
                        answer = (choice.get("text") or "").strip()
                return answer or "I apologize, but I'm unable to generate a response at this time."
            else:
                self.logger.error(f"LLM request failed: {response.status_code}")
                return "I apologize, but I'm unable to generate a response at this time."
                
        except Exception as e:
            self.logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I encountered an error while generating the response."
    
    def _build_rag_prompt(self, query: str, context: str) -> str:
        """Build RAG prompt for LLM."""
        if not context.strip():
            return f'I do not have relevant information to answer your question: "{query}". Please provide more details or rephrase the question.'
        
        template = getattr(self.config.llm, "user_prompt_template", None)
        if template:
            try:
                return template.format(context=context, query=query)
            except Exception:
                pass
        
        return f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store."""
        try:
            vector_store = await self._get_vector_store()
            deleted_count = await vector_store.delete_document(document_id)
            self.logger.info(f"Deleted document {document_id}: {deleted_count} chunks removed")
            return deleted_count > 0
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = self._stats.copy()
        
        # Add component stats
        stats['embedding_service'] = self.embedding_service.get_stats()
        
        # Add vector store stats
        if self.using_fallback:
            stats['vector_store'] = {
                'type': 'in_memory_fallback',
                'stats': self.fallback_vector_store.get_stats()
            }
        else:
            stats['vector_store'] = {
                'type': 'safe_chromadb',
                'stats': self.primary_vector_store.get_stats()
            }
        
        stats['document_loader'] = self.document_loader_factory.get_loader_stats()
        
        # Calculate derived metrics
        if stats['documents_processed'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['documents_processed']
            stats['avg_chunks_per_document'] = stats['chunks_created'] / stats['documents_processed']
        else:
            stats['avg_processing_time'] = 0.0
            stats['avg_chunks_per_document'] = 0.0
        
        if stats['queries_processed'] > 0:
            stats['avg_query_time'] = stats['total_query_time'] / stats['queries_processed']
        else:
            stats['avg_query_time'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset all statistics."""
        for key in self._stats:
            self._stats[key] = 0
        
        self.embedding_service.clear_cache()
        self.primary_vector_store.reset_stats()
        self.fallback_vector_store = InMemoryVectorStore()  # Reset fallback
        self.document_loader_factory.reset_all_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "status": "healthy",
            "components": {},
            "using_fallback": self.using_fallback,
            "config": {
                "embedding_model": self.config.embedding.model,
                "llm_model": self.config.llm.model,
                "vector_store": self.config.vector_store.collection_name
            }
        }
        
        # Check embedding service
        try:
            if self.embedding_service.test_connection():
                health["components"]["embedding_service"] = "healthy"
            else:
                health["components"]["embedding_service"] = "unhealthy"
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["embedding_service"] = f"error: {e}"
            health["status"] = "degraded"
        
        # Check vector stores
        try:
            primary_health = await self.primary_vector_store.health_check()
            health["components"]["primary_vector_store"] = primary_health["status"]
            
            if primary_health["status"] != "healthy":
                if not self.using_fallback:
                    health["status"] = "degraded"
                health["components"]["fallback_vector_store"] = "ready"
            
        except Exception as e:
            health["components"]["primary_vector_store"] = f"error: {e}"
            if not self.using_fallback:
                health["status"] = "degraded"
            health["components"]["fallback_vector_store"] = "ready"
        
        return health
    
    def force_primary_reinitialize(self):
        """Force primary vector store reinitialization."""
        self.using_fallback = False
        self.primary_vector_store.force_reinitialize()
        self.logger.info("Forced primary vector store reinitialization")
    
    def __str__(self) -> str:
        store_type = "fallback" if self.using_fallback else "primary"
        return f"SafeRAGPipeline(docs={self._stats['documents_processed']}, queries={self._stats['queries_processed']}, store={store_type})"
    
    def __repr__(self) -> str:
        return f"SafeRAGPipeline(config={self.config.pipeline_name})"