"""
RAG Worker Thread

Thread-safe worker that handles all RAG operations (FAISS/ChromaDB) in isolation to prevent segfaults.
Uses a dedicated thread with a request/response queue system for safe GUI integration.
Supports both FAISS and ChromaDB vector stores with automatic fallback.
"""

import asyncio
import logging
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..pipeline.rag_pipeline import RAGPipeline
from ..config.rag_config import get_config, RAGPipelineConfig

logger = logging.getLogger("ghostman.rag_worker")


class RequestType(Enum):
    """Types of requests the worker can handle."""
    INGEST_DOCUMENT = "ingest_document"
    QUERY = "query"
    GET_STATS = "get_stats"
    HEALTH_CHECK = "health_check"
    SHUTDOWN = "shutdown"


@dataclass
class WorkerRequest:
    """Request to the ChromaDB worker thread."""
    request_id: str
    request_type: RequestType
    data: Dict[str, Any]
    timestamp: float


@dataclass
class WorkerResponse:
    """Response from the ChromaDB worker thread."""
    request_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: float = 0.0


class RAGWorker:
    """
    Thread-safe RAG worker that handles all vector store operations in isolation.
    
    This worker runs in a dedicated thread with its own event loop, preventing
    Qt threading issues and vector store segfaults (especially ChromaDB).
    Supports both FAISS and ChromaDB backends with automatic fallback.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize the RAG worker.
        
        Args:
            config: RAG pipeline configuration (uses default if None)
        """
        self.config = config or get_config()
        self.logger = logging.getLogger("ghostman.rag_worker.RAGWorker")
        
        # Threading components
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._ready_event = threading.Event()
        
        # Worker state
        self._rag_pipeline: Optional[RAGPipeline] = None
        self._is_running = False
        self._pending_requests: Dict[str, float] = {}  # request_id -> timestamp
        
        # Performance tracking
        self._stats = {
            'requests_processed': 0,
            'requests_failed': 0,
            'total_processing_time': 0.0,
            'worker_uptime': 0.0,
            'start_time': time.time()
        }
    
    def start(self) -> bool:
        """
        Start the worker thread.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._is_running:
            self.logger.warning("Worker already running")
            return True
        
        try:
            vector_store_type = self.config.vector_store.type.value if hasattr(self.config.vector_store.type, 'value') else str(self.config.vector_store.type)
            self.logger.info(f"Starting RAG worker thread with {vector_store_type} vector store...")
            self._shutdown_event.clear()
            self._ready_event.clear()
            
            self.worker_thread = threading.Thread(
                target=self._worker_main,
                name="RAGWorker",
                daemon=True
            )
            self.worker_thread.start()
            
            # Wait for worker to be ready (max 10 seconds)
            if self._ready_event.wait(timeout=10.0):
                self._is_running = True
                self.logger.info(f"✅ RAG worker started successfully with {vector_store_type} backend")
                return True
            else:
                self.logger.error("❌ RAG worker failed to start within timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to start RAG worker: {e}")
            return False
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the worker thread gracefully.
        
        Args:
            timeout: Maximum time to wait for shutdown
            
        Returns:
            True if stopped successfully, False if timeout
        """
        if not self._is_running:
            self.logger.info("Worker not running")
            return True
        
        try:
            self.logger.info("Stopping RAG worker thread...")
            
            # Send shutdown request
            shutdown_request = WorkerRequest(
                request_id=f"shutdown_{uuid.uuid4().hex[:8]}",
                request_type=RequestType.SHUTDOWN,
                data={},
                timestamp=time.time()
            )
            self.request_queue.put(shutdown_request)
            self._shutdown_event.set()
            
            # Wait for worker to finish
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=timeout)
                
                if self.worker_thread.is_alive():
                    self.logger.warning("⚠️ Worker thread did not stop within timeout")
                    return False
            
            self._is_running = False
            self.logger.info("✅ RAG worker stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping RAG worker: {e}")
            return False
    
    def ingest_document(self, file_path: Union[str, Path], 
                       metadata_override: Optional[Dict[str, Any]] = None,
                       timeout: float = 60.0) -> Optional[str]:
        """
        Ingest a document (thread-safe).
        
        Args:
            file_path: Path to document file
            metadata_override: Optional metadata overrides
            timeout: Request timeout in seconds
            
        Returns:
            Document ID if successful, None if failed
        """
        request = WorkerRequest(
            request_id=f"ingest_{uuid.uuid4().hex[:8]}",
            request_type=RequestType.INGEST_DOCUMENT,
            data={
                'file_path': str(file_path),
                'metadata_override': metadata_override
            },
            timestamp=time.time()
        )
        
        response = self._send_request(request, timeout)
        
        if response and response.success:
            return response.data
        elif response:
            self.logger.error(f"Document ingestion failed: {response.error}")
            return None
        else:
            self.logger.error("Document ingestion timed out")
            return None
    
    def query(self, query_text: str, top_k: int = 5, 
              filters: Optional[Dict[str, Any]] = None,
              timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Query the RAG pipeline (thread-safe).
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            filters: Optional metadata filters
            timeout: Request timeout in seconds
            
        Returns:
            Query response if successful, None if failed
        """
        request = WorkerRequest(
            request_id=f"query_{uuid.uuid4().hex[:8]}",
            request_type=RequestType.QUERY,
            data={
                'query_text': query_text,
                'top_k': top_k,
                'filters': filters
            },
            timestamp=time.time()
        )
        
        response = self._send_request(request, timeout)
        
        if response and response.success:
            return response.data
        elif response:
            self.logger.error(f"Query failed: {response.error}")
            return None
        else:
            self.logger.error("Query timed out")
            return None
    
    def get_stats(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Get RAG pipeline statistics (thread-safe).
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Stats dictionary if successful, None if failed
        """
        request = WorkerRequest(
            request_id=f"stats_{uuid.uuid4().hex[:8]}",
            request_type=RequestType.GET_STATS,
            data={},
            timestamp=time.time()
        )
        
        response = self._send_request(request, timeout)
        
        if response and response.success:
            # Add worker stats
            worker_stats = self._stats.copy()
            worker_stats['worker_uptime'] = time.time() - worker_stats['start_time']
            
            return {
                'rag_pipeline': response.data,
                'worker': worker_stats
            }
        elif response:
            self.logger.error(f"Get stats failed: {response.error}")
            return None
        else:
            self.logger.error("Get stats timed out")
            return None
    
    def health_check(self, timeout: float = 5.0) -> bool:
        """
        Check if the worker and RAG pipeline are healthy (thread-safe).
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            True if healthy, False otherwise
        """
        if not self._is_running:
            return False
        
        request = WorkerRequest(
            request_id=f"health_{uuid.uuid4().hex[:8]}",
            request_type=RequestType.HEALTH_CHECK,
            data={},
            timestamp=time.time()
        )
        
        response = self._send_request(request, timeout)
        return response is not None and response.success
    
    def _send_request(self, request: WorkerRequest, timeout: float) -> Optional[WorkerResponse]:
        """Send a request and wait for response."""
        if not self._is_running:
            self.logger.error("Worker not running")
            return None
        
        try:
            # Add to pending requests
            self._pending_requests[request.request_id] = request.timestamp
            
            # Send request
            self.request_queue.put(request)
            
            # Wait for response
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    response = self.response_queue.get(timeout=0.1)
                    if response.request_id == request.request_id:
                        # Remove from pending
                        self._pending_requests.pop(request.request_id, None)
                        return response
                    else:
                        # Put back wrong response
                        self.response_queue.put(response)
                except queue.Empty:
                    continue
            
            # Timeout occurred
            self._pending_requests.pop(request.request_id, None)
            self.logger.warning(f"Request {request.request_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            self._pending_requests.pop(request.request_id, None)
            return None
    
    def _worker_main(self):
        """Main worker thread function."""
        try:
            vector_store_type = self.config.vector_store.type.value if hasattr(self.config.vector_store.type, 'value') else str(self.config.vector_store.type)
            self.logger.info(f"RAG worker thread started with {vector_store_type} backend")
            
            # Initialize RAG pipeline in worker thread
            self.logger.info("Initializing RAG pipeline in worker thread...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self._rag_pipeline = RAGPipeline(self.config)
                self.logger.info(f"✅ RAG pipeline initialized successfully with {vector_store_type} vector store")
                
                # Signal that worker is ready
                self._ready_event.set()
                
                # Process requests
                self._process_requests(loop)
                
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"❌ Worker thread crashed: {e}")
            self.logger.error(traceback.format_exc())
            
            # Signal ready even if failed (to prevent deadlock)
            self._ready_event.set()
    
    def _process_requests(self, loop: asyncio.AbstractEventLoop):
        """Process requests in the worker thread."""
        while not self._shutdown_event.is_set():
            try:
                # Get request with timeout
                try:
                    request = self.request_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process request
                start_time = time.time()
                response = self._handle_request(request, loop)
                processing_time = time.time() - start_time
                
                # Update stats
                if response.success:
                    self._stats['requests_processed'] += 1
                else:
                    self._stats['requests_failed'] += 1
                self._stats['total_processing_time'] += processing_time
                
                # Send response
                self.response_queue.put(response)
                
                # Check for shutdown
                if request.request_type == RequestType.SHUTDOWN:
                    self.logger.info("Shutdown request received, stopping worker")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error processing request: {e}")
                self.logger.error(traceback.format_exc())
        
        self.logger.info("Worker thread finished processing requests")
    
    def _handle_request(self, request: WorkerRequest, 
                       loop: asyncio.AbstractEventLoop) -> WorkerResponse:
        """Handle a specific request."""
        try:
            if request.request_type == RequestType.INGEST_DOCUMENT:
                result = loop.run_until_complete(
                    self._rag_pipeline.ingest_document(
                        request.data['file_path'],
                        request.data.get('metadata_override')
                    )
                )
                return WorkerResponse(
                    request_id=request.request_id,
                    success=True,
                    data=result,
                    timestamp=time.time()
                )
                
            elif request.request_type == RequestType.QUERY:
                from ..pipeline.rag_pipeline import RAGQuery
                
                rag_query = RAGQuery(
                    text=request.data['query_text'],
                    top_k=request.data.get('top_k', 5),
                    filters=request.data.get('filters')
                )
                
                result = loop.run_until_complete(self._rag_pipeline.query(rag_query))
                
                # Convert to serializable format
                response_data = {
                    'query': result.query,
                    'answer': result.answer,
                    'sources': [
                        {
                            'content': source.content,
                            'metadata': source.metadata,
                            'score': source.score
                        }
                        for source in result.sources
                    ],
                    'context_used': result.context_used,
                    'processing_time': result.processing_time,
                    'metadata': result.metadata
                }
                
                return WorkerResponse(
                    request_id=request.request_id,
                    success=True,
                    data=response_data,
                    timestamp=time.time()
                )
                
            elif request.request_type == RequestType.GET_STATS:
                stats = self._rag_pipeline.get_stats()
                return WorkerResponse(
                    request_id=request.request_id,
                    success=True,
                    data=stats,
                    timestamp=time.time()
                )
                
            elif request.request_type == RequestType.HEALTH_CHECK:
                is_healthy = True  # Default healthy if no health_check method
                if hasattr(self._rag_pipeline, 'health_check'):
                    try:
                        if hasattr(self._rag_pipeline.health_check, '__call__'):
                            health_result = self._rag_pipeline.health_check()
                            # If it's a coroutine, await it; otherwise use directly
                            if hasattr(health_result, '__await__'):
                                is_healthy = loop.run_until_complete(health_result)
                            else:
                                is_healthy = health_result
                    except Exception as e:
                        self.logger.warning(f"Health check failed: {e}")
                        is_healthy = False
                
                return WorkerResponse(
                    request_id=request.request_id,
                    success=True,
                    data={'healthy': is_healthy},
                    timestamp=time.time()
                )
                
            elif request.request_type == RequestType.SHUTDOWN:
                return WorkerResponse(
                    request_id=request.request_id,
                    success=True,
                    data={'message': 'Shutdown initiated'},
                    timestamp=time.time()
                )
                
            else:
                return WorkerResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"Unknown request type: {request.request_type}",
                    timestamp=time.time()
                )
                
        except Exception as e:
            error_msg = f"Request processing failed: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            return WorkerResponse(
                request_id=request.request_id,
                success=False,
                error=error_msg,
                timestamp=time.time()
            )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._is_running:
            self.stop()


# Global worker instance for singleton usage
_global_worker: Optional[RAGWorker] = None
_worker_lock = threading.Lock()


def get_rag_worker(config: Optional[RAGPipelineConfig] = None) -> RAGWorker:
    """
    Get the global RAG worker instance (singleton).
    
    Args:
        config: RAG configuration (only used on first call)
        
    Returns:
        RAG worker instance
    """
    global _global_worker
    
    with _worker_lock:
        if _global_worker is None:
            _global_worker = RAGWorker(config)
            _global_worker.start()
        
        return _global_worker


def shutdown_rag_worker():
    """Shutdown the global RAG worker."""
    global _global_worker
    
    with _worker_lock:
        if _global_worker is not None:
            _global_worker.stop()
            _global_worker = None


# Legacy aliases for backward compatibility
ChromaDBWorker = RAGWorker
get_chromadb_worker = get_rag_worker
shutdown_chromadb_worker = shutdown_rag_worker