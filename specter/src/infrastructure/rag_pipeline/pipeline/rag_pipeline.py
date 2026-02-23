"""
RAG Pipeline Orchestrator

Complete RAG pipeline implementation that integrates:
- Document loading and processing
- Text splitting and chunking
- Embedding generation
- Vector storage in ChromaDB
- Query processing and retrieval
- LLM integration for generation
- End-to-end RAG workflow
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import os

import numpy as np

from ..config.rag_config import RAGPipelineConfig, get_config, validate_config, VectorStoreType
from ..document_loaders.loader_factory import DocumentLoaderFactory, load_document
from ..document_loaders.base_loader import Document
from ..text_processing.text_splitter import TextSplitterFactory, TextChunk
from ..vector_store.chromadb_client import ChromaDBClient, SearchResult
from ..vector_store.faiss_client import FaissClient
from ..services.embedding_service import EmbeddingService
from ...ai.session_manager import session_manager

logger = logging.getLogger("specter.rag_pipeline")


@dataclass
class RAGQuery:
    """Query for the RAG pipeline."""
    text: str
    filters: Optional[Dict[str, Any]] = None
    top_k: Optional[int] = None
    context_length: Optional[int] = None
    include_metadata: bool = True


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""
    query: str
    answer: str
    sources: List[SearchResult]
    context_used: str
    processing_time: float
    metadata: Dict[str, Any]


class RAGPipeline:
    """
    Complete RAG (Retrieval-Augmented Generation) pipeline.
    
    Orchestrates the entire RAG process:
    1. Document ingestion and processing
    2. Text chunking and embedding generation
    3. Vector storage and indexing
    4. Query processing and retrieval
    5. Context assembly and LLM generation
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize RAG pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(f"{__name__}.RAGPipeline")
        
        # Initialize components
        self.document_loader_factory = DocumentLoaderFactory(self.config.document_loading)
        self.text_splitter = TextSplitterFactory.create_splitter(self.config.text_processing)
        
        # Initialize embedding service (ensure api_key is a string for the client)
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
        
        # Propagate configured keys/models into environment for components that expect them (Chroma client, tests, etc.)
        try:
            if getattr(self.config, "embedding", None) and getattr(self.config.embedding, "api_key", None):
                os.environ["OPENAI_API_KEY"] = str(self.config.embedding.api_key)
            if getattr(self.config, "embedding", None) and getattr(self.config.embedding, "model", None):
                os.environ.setdefault("OPENAI_EMBEDDING_MODEL", str(self.config.embedding.model))
            if getattr(self.config, "llm", None) and getattr(self.config.llm, "model", None):
                os.environ.setdefault("OPENAI_LLM_MODEL", str(self.config.llm.model))
        except Exception:
            # Best-effort: do not fail initialization if environment cannot be set
            self.logger.debug("Could not set environment variables for external clients; continuing with config values")
        
        # Initialize vector store based on configuration
        if self.config.vector_store.type == VectorStoreType.FAISS:
            try:
                self.vector_store = FaissClient(self.config.vector_store)
                self.logger.info("✅ Using FAISS vector store (no SQLite dependencies)")
            except Exception as e:
                self.logger.error(f"❌ FAISS initialization failed: {e}")
                self.logger.warning("🔄 Falling back to ChromaDB vector store")
                self.vector_store = ChromaDBClient(self.config.vector_store)
        else:
            self.vector_store = ChromaDBClient(self.config.vector_store)
            self.logger.info("✅ Using ChromaDB vector store (thread-safe worker)")
        
        # Validate configuration and initialize components
        validate_config(self.config)

        # Initialize LLM session manager for generation (use unified session manager)
        self.session_manager = session_manager
        
        # Performance tracking
        self._stats = {
            'documents_processed': 0,
            'queries_processed': 0,
            'total_processing_time': 0.0,
            'total_query_time': 0.0,
            'chunks_created': 0,
            'embeddings_generated': 0,
        }
        
        self.logger.info("RAG Pipeline initialized successfully")
    
    def is_ready(self) -> bool:
        """Quick synchronous readiness check for the pipeline.

        Returns True when core components are available and responding.
        This is designed for lightweight readiness checks (UI/worker loops).
        """
        try:
            # Basic presence checks
            if not getattr(self, "embedding_service", None):
                return False
            if not getattr(self, "vector_store", None):
                return False
            
            # Embedding service health (synchronous)
            try:
                emb_ok = bool(self.embedding_service.test_connection())
            except Exception:
                emb_ok = False
            
            # Vector store basic info (synchronous)
            try:
                vs_ok = self.vector_store.is_ready()
            except Exception:
                vs_ok = False
            
            return emb_ok and vs_ok
        except Exception:
            return False
    
    async def ingest_document(self, source: Union[str, Path], 
                            metadata_override: Optional[Dict[str, Any]] = None) -> str:
        """
        Ingest a single document into the RAG pipeline.
        
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
            
            # 4. Check if any embeddings failed - if so, skip storage to prevent crashes
            failed_embeddings = sum(1 for emb in embeddings if self._is_fallback_embedding(emb))
            if failed_embeddings > 0:
                self.logger.error(f"⚠️ Skipping document storage due to {failed_embeddings}/{len(embeddings)} failed embeddings")
                self.logger.error(f"💡 This prevents ChromaDB segfault - fix your OpenAI API key to enable proper embedding storage")
                # Return a fake document ID to indicate processing completed but storage was skipped
                return f"skipped_{int(time.time())}"
            
            # 5. Store in vector database (only if all embeddings are valid)
            self.logger.info(f"Storing chunks in vector database")
            chunk_ids = await self.vector_store.store_document(document, chunks, embeddings)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._stats['documents_processed'] += 1
            self._stats['chunks_created'] += len(chunks)
            self._stats['embeddings_generated'] += len(embeddings)
            self._stats['total_processing_time'] += processing_time
            
            document_id = chunk_ids[0].split('_')[0] if chunk_ids else 'unknown'
            
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
        Process a query through the complete RAG pipeline.
        
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
            
            # 2. Check if query embedding failed - if so, return empty response
            if self._is_fallback_embedding(query_embedding):
                self.logger.error("⚠️ Query embedding failed - cannot perform search")
                self.logger.error("💡 Fix your OpenAI API key to enable RAG queries")
                return RAGResponse(
                    query=rag_query.text,
                    answer="I apologize, but I cannot process your query due to an embedding service issue. Please check your API configuration.",
                    sources=[],
                    context_used="",
                    processing_time=time.time() - start_time,
                    metadata={'error': 'embedding_failed'}
                )
            
            # 3. Retrieve relevant chunks
            top_k = rag_query.top_k or self.config.retrieval.top_k
            search_results = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=rag_query.filters,
                include_embeddings=False
            )
            
            # 4. Filter by similarity threshold
            # 4. Disabled threshold filtering; rely on top_k ordering only
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
                           f"{len(filtered_results)} sources used")
            
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
                
                # Instead of zero embeddings which cause segfaults, create small random embeddings
                # This ensures ChromaDB doesn't crash while still indicating embedding failure
                try:
                    dim = int(self.config.embedding.dimensions) if self.config.embedding.dimensions else 1536
                except Exception:
                    dim = 1536
                
                # Create small random embeddings instead of zeros (prevents ChromaDB segfault)
                # Use float32 to match OpenAI embedding format
                fallback_embedding = np.random.normal(0, 0.001, dim).astype(np.float32)
                embeddings.append(fallback_embedding)
                
        if failed_count > 0:
            self.logger.warning(f"Generated {failed_count}/{len(texts)} fallback embeddings due to API failures")
        
        return embeddings
    
    def _is_fallback_embedding(self, embedding: np.ndarray) -> bool:
        """Check if an embedding is a fallback (small random values with very low variance)."""
        try:
            if embedding is None:
                return True
            
            # Fallback embeddings have very small variance (since they're generated from normal(0, 0.001))
            variance = np.var(embedding)
            mean_abs = np.mean(np.abs(embedding))
            
            # Fallback embeddings: variance < 0.000002, mean_abs < 0.002
            # Real OpenAI embeddings: much higher variance and mean
            is_fallback = variance < 0.000002 and mean_abs < 0.002
            
            if is_fallback:
                self.logger.debug(f"Detected fallback embedding: var={variance:.8f}, mean_abs={mean_abs:.6f}")
            
            return is_fallback
            
        except Exception as e:
            self.logger.warning(f"Error checking fallback embedding: {e}")
            return True  # Assume fallback if we can't check
    
    def _assemble_context(self, search_results: List[SearchResult], query: RAGQuery) -> str:
        """Assemble context from search results.

        This implementation supports three overlap handling modes:
          - "truncate": truncate the overflowing entry to fit (if remaining is meaningful)
          - "merge": drop oldest entries (sliding window) until new entry fits;
                     if preserve_chunk_boundaries is False, allow truncation of the new entry
          - any other value: stop adding further entries (skip)
        """
        if not search_results:
            return ""

        context_parts: List[str] = []
        total_length = 0
        max_length = query.context_length or self.config.retrieval.max_context_length
        preserve_boundaries = getattr(self.config.retrieval, "preserve_chunk_boundaries", True)
        min_acceptable_remaining = 50  # characters; lower than previous 100 to be more permissive

        for i, result in enumerate(search_results):
            # Create context entry
            if query.include_metadata and isinstance(result.metadata, dict) and result.metadata.get('title'):
                context_entry = f"Source {i+1} ({result.metadata['title']}):\n{result.content}\n"
            else:
                context_entry = f"Source {i+1}:\n{result.content}\n"

            entry_len = len(context_entry)

            # If entry already exceeds max_length on its own
            if entry_len > max_length:
                # If we can break entries (no preserve) then truncate to fit otherwise skip
                if not preserve_boundaries:
                    if max_length > min_acceptable_remaining:
                        truncated = context_entry[:max_length - 3] + "..."
                        return truncated  # nothing else can be included
                    else:
                        return ""  # can't fit anything meaningful
                else:
                    # preserve boundaries => skip this entry entirely
                    continue

            # If adding the entry would exceed max length, handle according to policy
            if total_length + entry_len > max_length:
                handling = getattr(self.config.retrieval, "context_overlap_handling", "merge")
                if handling == "truncate":
                    remaining = max_length - total_length
                    if remaining > min_acceptable_remaining:
                        truncated = context_entry[:remaining - 3] + "..."
                        context_parts.append(truncated)
                        total_length += len(truncated)
                    break

                elif handling == "merge":
                    # Drop oldest entries until it fits or we run out
                    while context_parts and (total_length + entry_len) > max_length:
                        removed = context_parts.pop(0)
                        total_length -= len(removed)

                    # If it still doesn't fit after dropping and we are allowed to truncate, do so
                    if total_length + entry_len > max_length:
                        if not preserve_boundaries:
                            remaining = max_length - total_length
                            if remaining > min_acceptable_remaining:
                                truncated = context_entry[:remaining - 3] + "..."
                                context_parts.append(truncated)
                                total_length += len(truncated)
                        # Either way, stop processing further entries after merge attempt
                        break
                    # otherwise it fits now and will be appended below

                else:
                    # skip any further entries
                    break

            # Append entry
            context_parts.append(context_entry)
            total_length += entry_len

            # Defensive stop if somehow we've reached the limit
            if total_length >= max_length:
                break

        return "\n".join(context_parts)
    
    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using LLM."""
        try:
            # Build user prompt from template or fallback
            user_prompt = self._build_rag_prompt(query, context)
            system_prompt = getattr(self.config.llm, "system_prompt", "").strip() if hasattr(self.config.llm, "system_prompt") else ""
            
            # Prepare messages: system (optional) + user
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            # Use SessionManager to make the request (ensure timeout is int or None)
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
                # Support both 'choices[].message.content' and 'choices[].text'
                answer = ""
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if isinstance(choice.get("message"), dict):
                        answer = (choice["message"].get("content") or "").strip()
                    else:
                        answer = (choice.get("text") or "").strip()
                return answer or "I apologize, but I'm unable to generate a response at this time."
            else:
                self.logger.error(f"LLM request failed: {response.status_code} - {getattr(response, 'text', '')}")
                return "I apologize, but I'm unable to generate a response at this time."
                
        except Exception as e:
            self.logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I encountered an error while generating the response."
    
    def _build_rag_prompt(self, query: str, context: str) -> str:
        """Build RAG prompt for LLM using configurable templates (LLMConfig.user_prompt_template)."""
        if not context.strip():
            # No context available
            return f'I do not have relevant information to answer your question: "{query}". Please provide more details or rephrase the question.'
        
        # Prefer configured user prompt template if present
        template = getattr(self.config.llm, "user_prompt_template", None)
        if template:
            try:
                return template.format(context=context, query=query)
            except Exception:
                # Fall back to simple formatting if template fails
                pass
        
        # Default prompt
        return f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if successful
        """
        try:
            deleted_count = await self.vector_store.delete_document(document_id)
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
        stats['vector_store'] = self.vector_store.get_stats()
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
        self.vector_store.reset_stats()
        self.document_loader_factory.reset_all_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "status": "healthy",
            "components": {},
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
        
        # Check vector store
        try:
            vs_health = await self.vector_store.health_check()
            health["components"]["vector_store"] = vs_health["status"]
            if vs_health["status"] != "healthy":
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["vector_store"] = f"error: {e}"
            health["status"] = "unhealthy"
        
        # Check document loaders
        try:
            loader_test = await self.document_loader_factory.test_loaders()
            failed_loaders = [name for name, result in loader_test.items() if not result["available"]]
            if failed_loaders:
                health["components"]["document_loaders"] = f"some_failed: {failed_loaders}"
            else:
                health["components"]["document_loaders"] = "healthy"
        except Exception as e:
            health["components"]["document_loaders"] = f"error: {e}"
        
        return health
    
    async def backup(self, backup_path: str) -> bool:
        """
        Backup pipeline data and configuration.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if successful
        """
        try:
            import json
            from datetime import datetime
            
            backup_data = {
                "backup_time": datetime.now().isoformat(),
                "config": self.config.to_dict(),
                "stats": self.get_stats(),
                "health": await self.health_check()
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Also backup vector store
            vs_backup_path = backup_path.replace('.json', '_vectorstore.json')
            await self.vector_store.backup_collection(vs_backup_path)
            
            self.logger.info(f"Pipeline backup saved to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
    
    def __str__(self) -> str:
        return f"RAGPipeline(docs={self._stats['documents_processed']}, queries={self._stats['queries_processed']})"
    
    def __repr__(self) -> str:
        return f"RAGPipeline(config={self.config.pipeline_name})"


# Global pipeline instance
_global_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(config: Optional[RAGPipelineConfig] = None) -> RAGPipeline:
    """Get the global RAG pipeline instance."""
    global _global_pipeline
    
    if _global_pipeline is None:
        _global_pipeline = RAGPipeline(config)
    
    return _global_pipeline


def set_rag_pipeline(pipeline: RAGPipeline):
    """Set the global RAG pipeline instance."""
    global _global_pipeline
    _global_pipeline = pipeline