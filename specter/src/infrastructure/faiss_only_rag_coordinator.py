"""
FAISS-Only RAG Coordinator

High-performance RAG coordinator using only FAISS for vector operations.
Replaces LangChain with optimized direct implementations for better performance
and conversation isolation.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer, QMutex, QMutexLocker

from ..infrastructure.storage.settings_manager import settings
from ..infrastructure.conversation_management.services.conversation_service import ConversationService
from .rag_pipeline.vector_store.optimized_faiss_client import OptimizedFaissClient, OptimizedSearchResult
from .rag_pipeline.config.rag_config import get_config, RAGPipelineConfig
from .rag_pipeline.services.embedding_service import EmbeddingService
from .rag_pipeline.document_loaders.loader_factory import load_document
from .rag_pipeline.text_processing.text_splitter import TextSplitterFactory

logger = logging.getLogger("specter.faiss_only_rag_coordinator")


@dataclass
class DocumentProcessingJob:
    """Document processing job for async handling."""
    job_id: str
    file_path: str
    conversation_id: str
    callback: Optional[Callable] = None
    progress_callback: Optional[Callable] = None


@dataclass
class QueryJob:
    """Query processing job for async handling."""
    job_id: str
    query_text: str
    conversation_id: str
    callback: Optional[Callable] = None
    top_k: int = 5


class DocumentProcessor(QThread):
    """Background thread for processing documents without blocking UI."""
    
    # Signals
    processing_started = pyqtSignal(str)  # job_id
    processing_progress = pyqtSignal(str, int, str)  # job_id, progress_percent, status
    processing_completed = pyqtSignal(str, bool, str)  # job_id, success, result_or_error
    
    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator
        self.job_queue = []
        self.current_job = None
        self.should_stop = False
        self.mutex = QMutex()
    
    def add_job(self, job: DocumentProcessingJob):
        """Add document processing job to queue."""
        with QMutexLocker(self.mutex):
            self.job_queue.append(job)
        
        if not self.isRunning():
            self.start()
    
    def run(self):
        """Process document jobs in background."""
        while not self.should_stop:
            job = None
            
            with QMutexLocker(self.mutex):
                if self.job_queue:
                    job = self.job_queue.pop(0)
            
            if job:
                self.current_job = job
                self._process_document_job(job)
                self.current_job = None
            else:
                self.msleep(100)  # Wait for jobs
    
    def _process_document_job(self, job: DocumentProcessingJob):
        """Process a single document job."""
        try:
            self.processing_started.emit(job.job_id)
            
            # Load document
            self.processing_progress.emit(job.job_id, 10, "Loading document...")
            document = self.coordinator._load_document_sync(job.file_path)
            
            if not document:
                self.processing_completed.emit(job.job_id, False, "Failed to load document")
                return
            
            # Split into chunks
            self.processing_progress.emit(job.job_id, 30, "Splitting document...")
            chunks = self.coordinator._split_document_sync(document)
            
            if not chunks:
                self.processing_completed.emit(job.job_id, False, "Failed to create chunks")
                return
            
            # Generate embeddings
            self.processing_progress.emit(job.job_id, 50, "Generating embeddings...")
            embeddings = self.coordinator._generate_embeddings_sync(chunks)
            
            if not embeddings:
                self.processing_completed.emit(job.job_id, False, "Failed to generate embeddings")
                return
            
            # Index in FAISS
            self.processing_progress.emit(job.job_id, 80, "Indexing in FAISS...")
            chunk_ids = self.coordinator._index_document_sync(
                document, chunks, embeddings, job.conversation_id
            )
            
            if chunk_ids:
                self.processing_progress.emit(job.job_id, 100, "Complete")
                self.processing_completed.emit(job.job_id, True, f"Indexed {len(chunk_ids)} chunks")
            else:
                self.processing_completed.emit(job.job_id, False, "Failed to index document")
                
        except Exception as e:
            logger.error(f"Document processing job {job.job_id} failed: {e}")
            self.processing_completed.emit(job.job_id, False, str(e))
    
    def stop_processing(self):
        """Stop the processing thread."""
        self.should_stop = True
        self.wait()


class FAISSONlyRAGCoordinator(QObject):
    """
    FAISS-Only RAG Coordinator for high-performance document processing and querying.
    
    Key Features:
    - Direct FAISS integration (no LangChain overhead)
    - Conversation-specific document isolation
    - PyQt6 signal integration for UI responsiveness
    - Background document processing
    - Thread-safe operations
    - Memory-efficient design
    """
    
    # PyQt6 Signals
    document_uploaded = pyqtSignal(str, str, int)  # conversation_id, document_id, chunk_count
    query_completed = pyqtSignal(str, str, int)  # conversation_id, query, result_count
    error_occurred = pyqtSignal(str)  # error_message
    status_changed = pyqtSignal(str)  # status_message
    
    def __init__(self, conversation_service: ConversationService):
        super().__init__()
        
        self.conversation_service = conversation_service
        self.config: Optional[RAGPipelineConfig] = None
        self.faiss_client: Optional[OptimizedFaissClient] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.text_splitter = None
        
        # Background processing
        self.document_processor = DocumentProcessor(self)
        self.query_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="QueryFAISS")
        
        # State management
        self._is_ready = False
        self._initialization_error = None
        
        # Statistics
        self._stats = {
            'documents_processed': 0,
            'queries_executed': 0,
            'total_processing_time': 0.0,
            'total_query_time': 0.0,
            'conversations_active': 0
        }
        
        # Connect signals
        self._connect_signals()
        
        # Initialize
        self._initialize()
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.document_processor.processing_completed.connect(self._on_document_processed)
        
        if self.faiss_client:
            self.faiss_client.document_indexed.connect(self._on_document_indexed)
            self.faiss_client.search_completed.connect(self._on_search_completed)
            self.faiss_client.error_occurred.connect(self._on_faiss_error)
    
    def _initialize(self):
        """Initialize FAISS-only RAG system."""
        try:
            self.status_changed.emit("Initializing FAISS-only RAG system...")
            
            # Check API key
            api_key = settings.get("ai_model.api_key")
            if not api_key:
                self._initialization_error = "No OpenAI API key found"
                self.error_occurred.emit(self._initialization_error)
                return
            
            # Get configuration
            self.config = get_config()
            
            # Initialize FAISS client
            self.faiss_client = OptimizedFaissClient(self.config.vector_store)
            
            # Initialize embedding service
            self.embedding_service = EmbeddingService(
                api_endpoint=self.config.embedding.api_endpoint,
                api_key=api_key,
                model=self.config.embedding.model,
                max_retries=self.config.embedding.max_retries,
                timeout=self.config.embedding.timeout,
                rate_limit_delay=self.config.embedding.rate_limit_delay,
                cache_size=self.config.embedding.cache_size,
                cache_ttl=self.config.embedding.cache_ttl_hours * 3600
            )
            
            # Initialize text splitter
            self.text_splitter = TextSplitterFactory.create_splitter(
                self.config.text_processing
            )
            
            # Connect FAISS signals
            self._connect_signals()
            
            self._is_ready = True
            self.status_changed.emit("FAISS-only RAG system ready")
            
            logger.info("✅ FAISS-only RAG coordinator initialized successfully")
            
        except Exception as e:
            self._initialization_error = f"Failed to initialize FAISS-only RAG: {e}"
            self.error_occurred.emit(self._initialization_error)
            logger.error(self._initialization_error)
    
    def is_ready(self) -> bool:
        """Check if RAG system is ready."""
        return self._is_ready and self.faiss_client and self.faiss_client.is_ready()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        status = {
            'ready': self.is_ready(),
            'initialization_error': self._initialization_error,
            'faiss_available': self.faiss_client is not None,
            'embedding_service_ready': self.embedding_service is not None,
            'api_key_configured': bool(settings.get("ai_model.api_key")),
        }
        
        if self.faiss_client:
            status.update(self.faiss_client.get_optimized_stats())
        
        status.update(self._stats)
        return status
    
    def upload_document_async(
        self, 
        file_path: str, 
        conversation_id: str,
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ) -> str:
        """
        Upload document asynchronously without blocking UI.
        
        Returns job_id for tracking progress.
        """
        if not self.is_ready():
            error_msg = f"RAG system not ready: {self._initialization_error}"
            self.error_occurred.emit(error_msg)
            return ""
        
        job_id = f"upload_{int(time.time() * 1000)}"
        job = DocumentProcessingJob(
            job_id=job_id,
            file_path=file_path,
            conversation_id=conversation_id,
            callback=completion_callback,
            progress_callback=progress_callback
        )
        
        self.document_processor.add_job(job)
        return job_id
    
    def query_conversation_sync(
        self,
        query_text: str,
        conversation_id: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Synchronous conversation-specific query for immediate results.
        
        Optimized for PyQt6 main thread usage.
        """
        if not self.is_ready():
            return {
                'answer': f"RAG system not ready: {self._initialization_error}",
                'sources': [],
                'error': self._initialization_error
            }
        
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.create_embedding(query_text)
            if query_embedding is None:
                return {
                    'answer': 'Failed to generate query embedding',
                    'sources': [],
                    'error': 'Embedding generation failed'
                }
            
            # Search FAISS by conversation
            results = self.faiss_client.search_by_conversation_sync(
                query_embedding=query_embedding,
                conversation_id=conversation_id,
                top_k=top_k
            )
            
            # Process results
            sources = []
            context_parts = []
            
            for i, result in enumerate(results):
                source_info = {
                    'content': result.content,
                    'metadata': result.metadata,
                    'score': result.score,
                    'chunk_id': result.chunk_id,
                    'document_id': result.document_id
                }
                sources.append(source_info)
                context_parts.append(f"Source {i+1}:\n{result.content}")
            
            # Generate answer using context
            context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
            answer = self._generate_contextual_answer(query_text, context)
            
            # Update statistics
            query_time = time.time() - start_time
            self._stats['queries_executed'] += 1
            self._stats['total_query_time'] += query_time
            
            # Emit signal
            self.query_completed.emit(conversation_id, query_text, len(results))
            
            return {
                'answer': answer,
                'sources': sources,
                'context': context,
                'query_time': query_time,
                'conversation_id': conversation_id
            }
            
        except Exception as e:
            error_msg = f"Query failed: {str(e)}"
            self.error_occurred.emit(error_msg)
            logger.error(f"Query error: {e}")
            
            return {
                'answer': f"I encountered an error processing your query: {error_msg}",
                'sources': [],
                'error': error_msg
            }
    
    def _generate_contextual_answer(self, query: str, context: str) -> str:
        """Generate answer using context (simplified version without LangChain)."""
        if not context or context == "No relevant context found.":
            return "I don't have relevant information in the uploaded documents to answer your question."
        
        # For now, return a simple context-based response
        # In production, you'd use your AI service here
        return f"Based on the uploaded documents:\n\n{context[:500]}..."
    
    def get_conversation_documents(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a conversation."""
        if not self.is_ready():
            return []
        
        return self.faiss_client.get_conversation_documents(conversation_id)
    
    def remove_conversation_documents(self, conversation_id: str) -> int:
        """Remove all documents for a conversation."""
        if not self.is_ready():
            return 0
        
        try:
            count = self.faiss_client.remove_conversation_documents(conversation_id)
            if count > 0:
                self.status_changed.emit(f"Removed {count} documents from conversation {conversation_id}")
            return count
        except Exception as e:
            self.error_occurred.emit(f"Failed to remove documents: {str(e)}")
            return 0
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        stats = self._stats.copy()
        
        if self.faiss_client:
            faiss_stats = self.faiss_client.get_optimized_stats()
            stats.update(faiss_stats)
        
        # Calculate averages
        if stats['queries_executed'] > 0:
            stats['avg_query_time'] = stats['total_query_time'] / stats['queries_executed']
        else:
            stats['avg_query_time'] = 0.0
        
        if stats['documents_processed'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['documents_processed']
        else:
            stats['avg_processing_time'] = 0.0
        
        return stats
    
    # Synchronous helper methods for document processing
    
    def _load_document_sync(self, file_path: str):
        """Load document synchronously."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(load_document(file_path))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Failed to load document {file_path}: {e}")
            return None
    
    def _split_document_sync(self, document):
        """Split document into chunks synchronously."""
        try:
            return self.text_splitter.split_text(document.content)
        except Exception as e:
            logger.error(f"Failed to split document: {e}")
            return []
    
    def _generate_embeddings_sync(self, chunks):
        """Generate embeddings for chunks synchronously."""
        try:
            texts = [chunk.content for chunk in chunks]
            return self.embedding_service.create_batch_embeddings(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []
    
    def _index_document_sync(self, document, chunks, embeddings, conversation_id):
        """Index document in FAISS synchronously."""
        try:
            return self.faiss_client.index_document_sync(
                document, chunks, embeddings, conversation_id
            )
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return []
    
    # Signal handlers
    
    def _on_document_processed(self, job_id: str, success: bool, result: str):
        """Handle document processing completion."""
        if success:
            self._stats['documents_processed'] += 1
            logger.info(f"Document processing job {job_id} completed: {result}")
        else:
            logger.error(f"Document processing job {job_id} failed: {result}")
    
    def _on_document_indexed(self, document_id: str, chunk_count: int):
        """Handle document indexing completion."""
        self.document_uploaded.emit("", document_id, chunk_count)
    
    def _on_search_completed(self, query: str, result_count: int):
        """Handle search completion."""
        logger.debug(f"Search completed: {result_count} results for query: {query[:50]}...")
    
    def _on_faiss_error(self, error_message: str):
        """Handle FAISS errors."""
        self.error_occurred.emit(f"FAISS error: {error_message}")
    
    def cleanup(self):
        """Clean shutdown of RAG coordinator."""
        logger.info("Cleaning up FAISS-only RAG coordinator...")
        
        try:
            # Stop document processor
            self.document_processor.stop_processing()
            
            # Shutdown query executor
            self.query_executor.shutdown(wait=True)
            
            # Close FAISS client
            if self.faiss_client:
                self.faiss_client.close()
            
            self._is_ready = False
            self.status_changed.emit("FAISS-only RAG system shutdown")
            
        except Exception as e:
            logger.error(f"Error during RAG coordinator cleanup: {e}")


# Factory function
def create_faiss_only_rag_coordinator(conversation_service: ConversationService) -> FAISSONlyRAGCoordinator:
    """Create optimized FAISS-only RAG coordinator."""
    return FAISSONlyRAGCoordinator(conversation_service)