"""
File Upload Integration Service

Bridges the UI file upload functionality with the RAG pipeline.
Handles immediate processing, status tracking, and UI updates.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from ..conversation.conversation_rag_pipeline import ConversationRAGPipeline

logger = logging.getLogger("ghostman.file_upload_service")


class ProcessingStatus(Enum):
    """File processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileProcessingResult:
    """Result of file processing operation."""
    file_id: str
    filename: str
    status: ProcessingStatus
    chunks_created: int = 0
    tokens_used: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class FileUploadService(QObject if PYQT_AVAILABLE else object):
    """
    Service to handle file uploads and integrate with RAG pipeline.
    
    Features:
    - Immediate file processing upon upload
    - Progress tracking and status updates
    - Integration with conversation context
    - Batch processing support
    """
    
    # Qt signals for UI updates
    if PYQT_AVAILABLE:
        file_processing_started = pyqtSignal(str, str)  # file_id, filename
        file_processing_progress = pyqtSignal(str, float)  # file_id, progress
        file_processing_completed = pyqtSignal(str, dict)  # file_id, result
        file_processing_failed = pyqtSignal(str, str)  # file_id, error
        batch_processing_completed = pyqtSignal(list)  # results
    
    def __init__(
        self,
        conversation_rag_pipeline: ConversationRAGPipeline,
        max_concurrent: int = 3
    ):
        """Initialize file upload service."""
        if PYQT_AVAILABLE:
            super().__init__()
        
        self.rag_pipeline = conversation_rag_pipeline
        self.max_concurrent = max_concurrent
        
        # Processing queue
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._processing_results: Dict[str, FileProcessingResult] = {}
        
        # Start background processor
        self._processor_task = None
        
        logger.info("FileUploadService initialized")
    
    async def start(self):
        """Start the background processor."""
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_queue())
            logger.info("File processor started")
    
    async def stop(self):
        """Stop the background processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
            logger.info("File processor stopped")
    
    async def upload_files(
        self,
        conversation_id: str,
        file_paths: List[str],
        immediate_processing: bool = True
    ) -> List[str]:
        """
        Upload files for a conversation.
        
        Args:
            conversation_id: Target conversation ID
            file_paths: List of file paths to upload
            immediate_processing: Process immediately vs queue
            
        Returns:
            List of file IDs
        """
        file_ids = []
        
        for file_path in file_paths:
            file_id = await self.upload_file(
                conversation_id,
                file_path,
                immediate_processing
            )
            file_ids.append(file_id)
        
        return file_ids
    
    async def upload_file(
        self,
        conversation_id: str,
        file_path: str,
        immediate_processing: bool = True
    ) -> str:
        """
        Upload a single file.
        
        Args:
            conversation_id: Target conversation ID
            file_path: Path to file
            immediate_processing: Process immediately vs queue
            
        Returns:
            File ID
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Generate file ID
            file_id = f"file_{conversation_id}_{path.stem}_{datetime.now().timestamp()}"
            
            # Emit processing started signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_started'):
                self.file_processing_started.emit(file_id, path.name)
            
            # Create processing task
            task_data = {
                'file_id': file_id,
                'conversation_id': conversation_id,
                'file_path': str(path),
                'filename': path.name
            }
            
            if immediate_processing:
                # Process immediately
                result = await self._process_file(task_data)
                self._processing_results[file_id] = result
                
                # Emit completion signal
                if PYQT_AVAILABLE and hasattr(self, 'file_processing_completed'):
                    self.file_processing_completed.emit(
                        file_id,
                        self._result_to_dict(result)
                    )
            else:
                # Queue for processing
                await self._processing_queue.put(task_data)
                
                # Create initial result
                self._processing_results[file_id] = FileProcessingResult(
                    file_id=file_id,
                    filename=path.name,
                    status=ProcessingStatus.QUEUED
                )
            
            logger.info(f"File uploaded: {file_id} - {path.name}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            
            # Emit failure signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_failed'):
                self.file_processing_failed.emit(file_id, str(e))
            
            raise
    
    async def _process_file(self, task_data: Dict[str, Any]) -> FileProcessingResult:
        """Process a single file."""
        file_id = task_data['file_id']
        conversation_id = task_data['conversation_id']
        file_path = task_data['file_path']
        filename = task_data['filename']
        
        start_time = datetime.now()
        
        try:
            # Update status to processing
            if file_id in self._processing_results:
                self._processing_results[file_id].status = ProcessingStatus.PROCESSING
            
            # Emit progress signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_progress'):
                self.file_processing_progress.emit(file_id, 0.3)
            
            # Add document to conversation RAG pipeline
            doc_id = await self.rag_pipeline.add_document_to_conversation(
                conversation_id=conversation_id,
                file_path=file_path,
                metadata={
                    'upload_time': datetime.now().isoformat(),
                    'original_filename': filename
                }
            )
            
            # Emit progress signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_progress'):
                self.file_processing_progress.emit(file_id, 0.7)
            
            # Get processing stats from RAG pipeline
            stats = await self.rag_pipeline.rag_pipeline.get_stats()
            
            # Calculate tokens (approximate)
            path = Path(file_path)
            content = path.read_text(encoding='utf-8', errors='ignore')
            tokens_used = len(content.split()) * 1.3  # Rough token estimate
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create success result
            result = FileProcessingResult(
                file_id=file_id,
                filename=filename,
                status=ProcessingStatus.COMPLETED,
                chunks_created=stats.get('chunks_created', 0),
                tokens_used=int(tokens_used),
                processing_time=processing_time,
                metadata={'document_id': doc_id}
            )
            
            # Emit completion signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_completed'):
                self.file_processing_completed.emit(
                    file_id,
                    self._result_to_dict(result)
                )
            
            logger.info(f"File processed successfully: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process file {file_id}: {e}")
            
            # Create failure result
            result = FileProcessingResult(
                file_id=file_id,
                filename=filename,
                status=ProcessingStatus.FAILED,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_message=str(e)
            )
            
            # Emit failure signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_failed'):
                self.file_processing_failed.emit(file_id, str(e))
            
            return result
    
    async def _process_queue(self):
        """Background task to process queued files."""
        logger.info("File processing queue started")
        
        while True:
            try:
                # Get task from queue
                task_data = await self._processing_queue.get()
                
                # Check concurrent limit
                while len(self._active_tasks) >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                    # Clean up completed tasks
                    completed = [
                        fid for fid, task in self._active_tasks.items()
                        if task.done()
                    ]
                    for fid in completed:
                        del self._active_tasks[fid]
                
                # Create processing task
                file_id = task_data['file_id']
                task = asyncio.create_task(self._process_file(task_data))
                self._active_tasks[file_id] = task
                
            except asyncio.CancelledError:
                logger.info("File processing queue cancelled")
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    def _result_to_dict(self, result: FileProcessingResult) -> Dict[str, Any]:
        """Convert result to dictionary for signals."""
        return {
            'file_id': result.file_id,
            'filename': result.filename,
            'status': result.status.value,
            'chunks_created': result.chunks_created,
            'tokens_used': result.tokens_used,
            'processing_time': result.processing_time,
            'error_message': result.error_message,
            'metadata': result.metadata or {}
        }
    
    def get_processing_status(self, file_id: str) -> Optional[FileProcessingResult]:
        """Get processing status for a file."""
        return self._processing_results.get(file_id)
    
    def get_all_statuses(self) -> Dict[str, FileProcessingResult]:
        """Get all processing statuses."""
        return self._processing_results.copy()
    
    async def retry_failed_file(self, file_id: str) -> bool:
        """Retry processing a failed file."""
        result = self._processing_results.get(file_id)
        if not result or result.status != ProcessingStatus.FAILED:
            return False
        
        # Find original task data
        # This would need to be stored for retry capability
        logger.warning(f"Retry not implemented for {file_id}")
        return False
    
    async def cancel_processing(self, file_id: str) -> bool:
        """Cancel file processing."""
        if file_id in self._active_tasks:
            task = self._active_tasks[file_id]
            task.cancel()
            del self._active_tasks[file_id]
            
            # Update status
            if file_id in self._processing_results:
                self._processing_results[file_id].status = ProcessingStatus.FAILED
                self._processing_results[file_id].error_message = "Cancelled by user"
            
            logger.info(f"Cancelled processing for {file_id}")
            return True
        
        return False