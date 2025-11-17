"""
Simple FAISS RAG Session

A straightforward implementation using FAISS vector store directly,
without the complex async pipeline that was causing issues.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from ..config.rag_config import get_config, RAGPipelineConfig
from ..vector_store.faiss_client import FaissClient, SearchResult
from ..services.embedding_service import EmbeddingService
from ..document_loaders.loader_factory import load_document
from ..text_processing.text_splitter import TextSplitterFactory
from ..smart_context_selector import SmartContextSelector, ContextResult

logger = logging.getLogger("ghostman.simple_faiss_session")


class SimpleFAISSSession:
    """
    Simple FAISS-based RAG session that works synchronously.
    
    This is a minimal implementation that avoids the async complexity
    and directly uses FAISS for stable operation.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """Initialize simple FAISS session."""
        self.config = config or get_config()
        self.logger = logging.getLogger("ghostman.simple_faiss_session.SimpleFAISSSession")
        
        # Initialize components
        self.faiss_client: Optional[FaissClient] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.text_splitter = None
        self.context_selector: Optional[SmartContextSelector] = None
        self._is_ready = False
        
        # Session state
        self._session_id = f"simple_faiss_session_{int(time.time())}"
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the session."""
        try:
            self.logger.info(f"Initializing simple FAISS session: {self._session_id}")
            
            # Initialize FAISS client
            self.faiss_client = FaissClient(self.config.vector_store)
            
            # Initialize embedding service
            self.embedding_service = EmbeddingService(
                api_endpoint=self.config.embedding.api_endpoint,
                api_key=self.config.embedding.api_key,
                model=self.config.embedding.model,
                max_retries=self.config.embedding.max_retries,
                timeout=self.config.embedding.timeout,
                rate_limit_delay=self.config.embedding.rate_limit_delay,
                cache_size=self.config.embedding.cache_size,
                cache_ttl=self.config.embedding.cache_ttl_hours * 3600  # Convert hours to seconds
            )
            
            # Initialize text splitter
            self.text_splitter = TextSplitterFactory.create_splitter(
                self.config.text_processing
            )
            
            # Initialize smart context selector
            self.context_selector = SmartContextSelector(logger=self.logger)
            
            self._is_ready = True
            self.logger.info("✅ Simple FAISS session ready")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize simple FAISS session: {e}")
            self._is_ready = False
    
    @property
    def is_ready(self) -> bool:
        """Check if the session is ready."""
        return self._is_ready
    
    def ingest_document(self, file_path: Union[str, Path], 
                       metadata_override: Optional[Dict[str, Any]] = None,
                       timeout: float = 120.0) -> Optional[str]:
        """
        Ingest a document into FAISS.
        
        Args:
            file_path: Path to document file
            metadata_override: Optional metadata overrides
            timeout: Timeout (unused in sync version)
            
        Returns:
            Document ID if successful, None if failed
        """
        if not self.is_ready:
            self.logger.error("Session not ready")
            return None
        
        try:
            self.logger.info(f"🔄 Ingesting document: {file_path}")
            start_time = time.time()
            
            # Load document using thread-safe pattern
            import asyncio
            import threading
            import queue
            
            doc_queue = queue.Queue()
            
            def load_doc():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        doc = new_loop.run_until_complete(load_document(str(file_path)))
                        doc_queue.put(doc)
                    finally:
                        new_loop.close()
                except Exception as e:
                    self.logger.error(f"Document load error: {e}")
                    doc_queue.put(None)
            
            thread = threading.Thread(target=load_doc, daemon=True)
            thread.start()
            thread.join(timeout=30.0)
            
            if doc_queue.empty():
                self.logger.error("Document load timed out")
                document = None
            else:
                document = doc_queue.get()
                
            if not document:
                self.logger.error(f"Failed to load document: {file_path}")
                return None
            
            # Split into chunks (already returns TextChunk objects)
            chunks = self.text_splitter.split_text(document.content)
            if not chunks:
                self.logger.error(f"No chunks created from document: {file_path}")
                return None
            
            # Add metadata to chunks
            import uuid
            document_id = str(uuid.uuid4())
            for chunk in chunks:
                chunk.metadata.update({
                    'source': str(file_path),
                    'document_id': document_id,
                    **(metadata_override or {})
                })
            
            self.logger.info(f"Split document into {len(chunks)} chunks")
            
            # Generate embeddings for chunks
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.create_batch_embeddings(texts)
            
            if not embeddings or len(embeddings) != len(chunks):
                self.logger.error(f"Failed to generate embeddings for {len(chunks)} chunks")
                return None
            
            self.logger.info(f"Generated embeddings for {len(chunks)} chunks")
            
            # Store in FAISS using thread-safe pattern
            store_queue = queue.Queue()
            
            def store_doc():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        ids = new_loop.run_until_complete(
                            self.faiss_client.store_document(
                                document=document,
                                chunks=chunks,
                                embeddings=embeddings
                            )
                        )
                        store_queue.put(ids)
                    finally:
                        new_loop.close()
                except Exception as e:
                    self.logger.error(f"Document store error: {e}")
                    store_queue.put(None)
            
            thread = threading.Thread(target=store_doc, daemon=True)
            thread.start()
            thread.join(timeout=30.0)
            
            if store_queue.empty():
                self.logger.error("Document store timed out")
                chunk_ids = None
            else:
                chunk_ids = store_queue.get()
            
            if not chunk_ids:
                self.logger.error("Failed to store document in FAISS")
                return None
            
            processing_time = time.time() - start_time
            self.logger.info(f"✅ Document ingested successfully: {document_id} ({processing_time:.2f}s)")
            
            return document_id
            
        except Exception as e:
            self.logger.error(f"❌ Document ingestion error: {e}")
            return None
    
    def query(self, query_text: str, top_k: int = 5, 
              filters: Optional[Dict[str, Any]] = None,
              timeout: float = 30.0,
              conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Query the FAISS index using SmartContextSelector with progressive fallback.
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            filters: Optional metadata filters (legacy parameter, now handled by SmartContextSelector)
            timeout: Timeout (unused in sync version)
            conversation_id: Current conversation ID for context selection
            
        Returns:
            Query response if successful, None if failed
        """
        if not self.is_ready:
            self.logger.error("Session not ready")
            return None
        
        try:
            self.logger.info(f"🔍 Smart Querying FAISS: {query_text[:50]}...")
            start_time = time.time()
            
            # Use SmartContextSelector for intelligent context selection
            import asyncio
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def run_smart_search():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # FIXED: Enable strict isolation - only use files from current conversation
                        # No time-based fallback to ensure conversation isolation
                        strict_isolation = True  # STRICT ISOLATION ENFORCED
                        
                        # Log strict isolation mode
                        self.logger.info(f"🔒 STRICT ISOLATION: Only using files from conversation {conversation_id[:8] if conversation_id else 'None'}...")
                        if conversation_id:
                            self.logger.info(f"🎯 Looking ONLY for conversation {conversation_id[:8]}... files")
                        else:
                            self.logger.warning(f"⚠️ No conversation ID - no files will be found")

                        # CRITICAL DEBUG: Log additional_filters before passing
                        self.logger.warning(f"🔍 CRITICAL DEBUG: additional_filters = {filters}")
                        self.logger.warning(f"🔍 CRITICAL DEBUG: filters type = {type(filters)}")
                        self.logger.warning(f"🔍 CRITICAL DEBUG: filters is None? {filters is None}")
                        if filters:
                            self.logger.warning(f"🔍 CRITICAL DEBUG: 'collection_tag' in filters? {'collection_tag' in filters}")

                        context_results, selection_info = new_loop.run_until_complete(
                            self.context_selector.select_context(
                                faiss_client=self.faiss_client,
                                embedding_service=self.embedding_service,
                                query_text=query_text,
                                top_k=top_k,
                                conversation_id=conversation_id,
                                max_tokens=4000,
                                strict_conversation_isolation=strict_isolation,
                                additional_filters=filters  # Pass collection_tag and other custom filters
                            )
                        )
                        result_queue.put((context_results, selection_info))
                    finally:
                        new_loop.close()
                except Exception as e:
                    self.logger.error(f"Smart search thread error: {e}")
                    result_queue.put((None, {}))
            
            thread = threading.Thread(target=run_smart_search, daemon=True)
            thread.start()
            thread.join(timeout=timeout)
            
            if result_queue.empty():
                self.logger.warning("Smart search timed out")
                context_results, selection_info = None, {}
            else:
                context_results, selection_info = result_queue.get()
            
            processing_time = time.time() - start_time
            
            if context_results is not None and len(context_results) > 0:
                sources = []
                for result in context_results:
                    try:
                        # Include source type and selection information
                        source_dict = {
                            'content': result.content,
                            'metadata': dict(result.metadata),  # Ensure it's a regular dict
                            'score': result.score,
                            'source_type': result.source_type.value,
                            'selection_tier': result.selection_tier,
                            'threshold_used': result.threshold_used
                        }
                        sources.append(source_dict)
                    except Exception as result_error:
                        self.logger.warning(f"Error processing result: {result_error}")
                        continue
                
                # Build response with transparency information
                response = {
                    'sources': sources,
                    'selection_info': selection_info,
                    'context': self._build_context_from_sources(sources),
                    'success': True,
                    'processing_time': processing_time
                }
                
                self.logger.info(f"✅ Smart query completed: {len(sources)} sources found ({processing_time:.2f}s)")
                return response
            else:
                self.logger.warning("⚠️ Smart query returned no results after fallback")
                return {
                    'sources': [],
                    'selection_info': selection_info,
                    'context': '',
                    'success': True,
                    'message': 'No relevant context found despite progressive fallback',
                    'processing_time': processing_time
                }
            
        except Exception as e:
            self.logger.error(f"❌ Smart query error: {e}")
            return None
    
    def _build_context_from_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Build context string from sources with source type tagging."""
        context_parts = []
        
        for source in sources:
            try:
                content = source.get('content', '')
                metadata = source.get('metadata', {})
                source_type = source.get('source_type', 'unknown')
                score = source.get('score', 0.0)
                
                if content:
                    # Tag the source with its type and relevance
                    source_name = metadata.get('source', 'document')
                    context_part = f"[{source_type.upper()}: {source_name} (relevance: {score:.3f})]\n{content}"
                    context_parts.append(context_part)
            except Exception as e:
                self.logger.warning(f"Error building context from source: {e}")
                continue
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_stats(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Get session statistics."""
        if not self.is_ready:
            return {
                'session_ready': False,
                'error': 'Session not ready'
            }
        
        try:
            # Get stats from FAISS client with defensive programming
            faiss_stats = {}
            if hasattr(self.faiss_client, 'get_stats'):
                try:
                    client_stats = self.faiss_client.get_stats()
                    # Ensure we have a dictionary, not some other object
                    if isinstance(client_stats, dict):
                        faiss_stats = client_stats
                    else:
                        self.logger.warning(f"FAISS client get_stats returned non-dict: {type(client_stats)}")
                        faiss_stats = {}
                except Exception as stats_error:
                    self.logger.warning(f"FAISS client get_stats failed: {stats_error}")
                    faiss_stats = {}
            
            stats = {
                'session_ready': True,
                'session_id': self._session_id,
                'vector_store': 'faiss',
                'rag_pipeline': {
                    'documents_processed': faiss_stats.get('documents_stored', 0) if isinstance(faiss_stats, dict) else 0,
                    'vector_store': {
                        'chunks_stored': faiss_stats.get('chunks_stored', 0) if isinstance(faiss_stats, dict) else 0
                    }
                }
            }
            return stats
        except Exception as e:
            self.logger.error(f"❌ Get stats error: {e}")
            return {'session_ready': False, 'error': str(e)}
    
    def health_check(self, timeout: float = 5.0) -> bool:
        """Check if session is healthy."""
        return self.is_ready
    
    def close(self):
        """Close the session."""
        self.logger.info(f"Closing simple FAISS session: {self._session_id}")
        self._is_ready = False


def create_simple_faiss_session(config: Optional[RAGPipelineConfig] = None) -> SimpleFAISSSession:
    """Create a new simple FAISS session."""
    return SimpleFAISSSession(config)