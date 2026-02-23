"""
Qt-safe RAG Pipeline Bridge

This module provides a Qt-friendly interface to the RAG pipeline that prevents
segmentation faults by properly managing threading and asyncio interactions.

Key features:
- Thread-safe ChromaDB operations
- Proper Qt signal/slot integration  
- AsyncIO event loop management
- Error handling and recovery
- Resource cleanup
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional, List, Dict, Any, Union, Callable
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QApplication

from ..pipeline.rag_pipeline import RAGPipeline, RAGQuery, RAGResponse
from ..config.rag_config import RAGPipelineConfig


logger = logging.getLogger("specter.qt_rag_bridge")


class QtRagWorker(QObject):
    """Qt worker for RAG operations that run in a dedicated thread."""
    
    # Signals for communication with Qt main thread
    document_ingested = pyqtSignal(str, str, bool, dict)  # file_path, doc_id, success, metadata
    query_completed = pyqtSignal(str, str, list, bool, dict)  # query, answer, sources, success, metadata
    error_occurred = pyqtSignal(str, str)  # operation, error_message
    progress_updated = pyqtSignal(str, int, int)  # operation, current, total
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        super().__init__()
        self.config = config
        self.rag_pipeline: Optional[RAGPipeline] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = threading.Event()
        self.logger = logging.getLogger(f"{__name__}.QtRagWorker")
        
    def initialize(self):
        """Initialize RAG pipeline in worker thread."""
        try:
            # Create dedicated event loop for this worker
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            
            # Initialize RAG pipeline
            self.rag_pipeline = RAGPipeline(self.config)
            
            self.logger.info("QtRagWorker initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize QtRagWorker: {e}")
            self.error_occurred.emit("initialization", str(e))
            return False
    
    def run_async_operation(self, operation: Callable, *args, **kwargs):
        """Run async operation safely in worker thread."""
        if not self._event_loop or not self.rag_pipeline:
            self.error_occurred.emit("operation", "Worker not initialized")
            return
        
        try:
            # Schedule coroutine in worker's event loop
            if asyncio.iscoroutinefunction(operation):
                future = asyncio.run_coroutine_threadsafe(
                    operation(*args, **kwargs), 
                    self._event_loop
                )
                return future.result(timeout=300)  # 5 minute timeout
            else:
                return operation(*args, **kwargs)
                
        except Exception as e:
            self.logger.error(f"Async operation failed: {e}")
            self.error_occurred.emit("async_operation", str(e))
            raise
    
    def ingest_document_sync(self, file_path: str, metadata_override: Optional[Dict] = None):
        """Synchronously ingest a document (called from worker thread)."""
        try:
            self.logger.info(f"Starting document ingestion: {file_path}")
            
            async def _ingest():
                return await self.rag_pipeline.ingest_document(
                    source=file_path,
                    metadata_override=metadata_override
                )
            
            document_id = self.run_async_operation(_ingest)
            
            # Emit success signal
            self.document_ingested.emit(
                file_path, 
                document_id or "unknown", 
                True,
                {"processing_time": 0.0, "chunks": 0}  # Add actual stats if needed
            )
            
        except Exception as e:
            self.logger.error(f"Document ingestion failed: {e}")
            self.document_ingested.emit(file_path, "", False, {"error": str(e)})
    
    def query_sync(self, query_text: str, top_k: int = 5, filters: Optional[Dict] = None):
        """Synchronously query the RAG pipeline (called from worker thread)."""
        try:
            self.logger.info(f"Processing query: {query_text[:100]}...")
            
            async def _query():
                query = RAGQuery(text=query_text, top_k=top_k, filters=filters)
                return await self.rag_pipeline.query(query)
            
            response: RAGResponse = self.run_async_operation(_query)
            
            # Convert sources to serializable format
            sources = []
            for source in response.sources:
                sources.append({
                    "content": source.content,
                    "score": source.score,
                    "metadata": source.metadata,
                    "document_id": source.document_id,
                    "chunk_id": source.chunk_id
                })
            
            # Emit success signal
            self.query_completed.emit(
                query_text,
                response.answer,
                sources,
                True,
                {
                    "processing_time": response.processing_time,
                    "context_used": len(response.context_used),
                    "sources_count": len(response.sources)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            self.query_completed.emit(query_text, "", [], False, {"error": str(e)})
    
    def shutdown(self):
        """Shutdown worker and cleanup resources."""
        try:
            self._shutdown_event.set()
            
            if self.rag_pipeline:
                # Close ChromaDB connection
                if hasattr(self.rag_pipeline.vector_store, 'close'):
                    self.rag_pipeline.vector_store.close()
            
            if self._event_loop and not self._event_loop.is_closed():
                # Stop the event loop
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                
            self.logger.info("QtRagWorker shutdown completed")
            
        except Exception as e:
            self.logger.warning(f"Error during worker shutdown: {e}")


class QtRagBridge(QObject):
    """
    Qt-safe bridge to RAG pipeline operations.
    
    This class manages a dedicated worker thread for RAG operations,
    preventing Qt + AsyncIO + ChromaDB threading conflicts.
    """
    
    # Signals
    document_processed = pyqtSignal(str, str, bool, dict)  # file_path, doc_id, success, metadata
    query_answered = pyqtSignal(str, str, list, bool, dict)  # query, answer, sources, success, metadata
    error_occurred = pyqtSignal(str, str)  # operation, error_message
    ready_changed = pyqtSignal(bool)  # ready status
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.QtRagBridge")
        
        # Worker thread components
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[QtRagWorker] = None
        self._is_ready = False
        
        # Operation queue for thread safety
        self._operation_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="QtRagOp")
        
    def initialize(self) -> bool:
        """Initialize the RAG bridge with worker thread."""
        try:
            self.logger.info("Initializing QtRagBridge...")
            
            # Create worker thread
            self._worker_thread = QThread()
            self._worker = QtRagWorker(self.config)
            
            # Move worker to thread
            self._worker.moveToThread(self._worker_thread)
            
            # Connect signals
            self._worker.document_ingested.connect(self.document_processed)
            self._worker.query_completed.connect(self.query_answered)
            self._worker.error_occurred.connect(self.error_occurred)
            
            # Connect thread lifecycle
            self._worker_thread.started.connect(self._worker.initialize)
            self._worker_thread.finished.connect(self._worker.shutdown)
            
            # Start worker thread
            self._worker_thread.start()
            
            # Wait for initialization (with timeout)
            start_time = time.time()
            while not self._is_initialization_complete() and (time.time() - start_time) < 30:
                QApplication.processEvents()
                time.sleep(0.1)
            
            if self._is_initialization_complete():
                self._is_ready = True
                self.ready_changed.emit(True)
                self.logger.info("QtRagBridge initialized successfully")
                return True
            else:
                self.logger.error("QtRagBridge initialization timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize QtRagBridge: {e}")
            self.error_occurred.emit("initialization", str(e))
            return False
    
    def _is_initialization_complete(self) -> bool:
        """Check if worker initialization is complete."""
        return (self._worker and 
                hasattr(self._worker, 'rag_pipeline') and 
                self._worker.rag_pipeline is not None)
    
    def is_ready(self) -> bool:
        """Check if bridge is ready for operations."""
        return self._is_ready and self._worker_thread and self._worker_thread.isRunning()
    
    def ingest_document(self, file_path: Union[str, Path], metadata_override: Optional[Dict] = None):
        """Queue document ingestion operation."""
        if not self.is_ready():
            self.error_occurred.emit("ingest_document", "RAG bridge not ready")
            return
        
        try:
            # Submit operation to worker thread executor
            self._operation_executor.submit(
                self._worker.ingest_document_sync,
                str(file_path),
                metadata_override
            )
            
        except Exception as e:
            self.logger.error(f"Failed to queue document ingestion: {e}")
            self.error_occurred.emit("ingest_document", str(e))
    
    def query(self, query_text: str, top_k: int = 5, filters: Optional[Dict] = None):
        """Queue RAG query operation."""
        if not self.is_ready():
            self.error_occurred.emit("query", "RAG bridge not ready")
            return
        
        try:
            # Submit operation to worker thread executor  
            self._operation_executor.submit(
                self._worker.query_sync,
                query_text,
                top_k,
                filters
            )
            
        except Exception as e:
            self.logger.error(f"Failed to queue query: {e}")
            self.error_occurred.emit("query", str(e))
    
    def shutdown(self):
        """Shutdown bridge and cleanup resources."""
        try:
            self.logger.info("Shutting down QtRagBridge...")
            
            self._is_ready = False
            self.ready_changed.emit(False)
            
            # Shutdown operation executor
            if self._operation_executor:
                self._operation_executor.shutdown(wait=True)
            
            # Shutdown worker thread
            if self._worker_thread and self._worker_thread.isRunning():
                self._worker_thread.quit()
                if not self._worker_thread.wait(5000):  # 5 second timeout
                    self.logger.warning("Worker thread did not shut down gracefully")
                    self._worker_thread.terminate()
                    self._worker_thread.wait(1000)
            
            self.logger.info("QtRagBridge shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during bridge shutdown: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.shutdown()