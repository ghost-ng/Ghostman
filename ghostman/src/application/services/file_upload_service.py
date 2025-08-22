"""
File Upload Service for Ghostman.

Provides async file upload capabilities with progress tracking, error handling,
and integration with the validation and AI services.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .file_validation_service import FileValidationService, ValidationResult
from ...infrastructure.ai.file_service import FileService
from ...infrastructure.ai.file_models import FileUploadProgress, FileOperationResult

logger = logging.getLogger("ghostman.file_upload_service")


class UploadStatus(Enum):
    """Status enumeration for file uploads."""
    PENDING = "pending"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UploadTask:
    """Represents a single file upload task."""
    file_path: str
    purpose: str = "assistants"
    status: UploadStatus = UploadStatus.PENDING
    progress: float = 0.0
    bytes_uploaded: int = 0
    total_bytes: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    file_id: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if the upload task is complete (success or failure)."""
        return self.status in [UploadStatus.COMPLETED, UploadStatus.FAILED, UploadStatus.CANCELLED]
    
    @property
    def upload_speed_mbps(self) -> float:
        """Calculate upload speed in MB/s."""
        if not self.start_time or self.bytes_uploaded == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        
        return (self.bytes_uploaded / (1024 * 1024)) / elapsed
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining for upload completion."""
        if self.status != UploadStatus.UPLOADING or self.progress <= 0:
            return None
        
        if not self.start_time:
            return None
        
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return None
        
        remaining_progress = 1.0 - self.progress
        if remaining_progress <= 0:
            return 0.0
        
        return (elapsed / self.progress) * remaining_progress


@dataclass
class BatchUploadResult:
    """Result of a batch upload operation."""
    total_files: int
    successful_uploads: List[UploadTask]
    failed_uploads: List[UploadTask]
    cancelled_uploads: List[UploadTask]
    total_bytes_uploaded: int
    total_upload_time: float
    errors: List[str]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (len(self.successful_uploads) / self.total_files) * 100
    
    @property
    def average_speed_mbps(self) -> float:
        """Calculate average upload speed across all files."""
        if self.total_upload_time <= 0 or self.total_bytes_uploaded == 0:
            return 0.0
        return (self.total_bytes_uploaded / (1024 * 1024)) / self.total_upload_time


class FileUploadService(QObject):
    """
    Async file upload service with progress tracking and error handling.
    
    Features:
    - Async file uploads with progress callbacks
    - File validation before upload
    - Batch upload operations
    - Upload cancellation
    - Detailed progress tracking and statistics
    - PyQt signal integration for UI updates
    """
    
    # PyQt signals for UI integration
    upload_started = pyqtSignal(str)  # file_path
    upload_progress = pyqtSignal(str, float, int, int)  # file_path, progress, bytes_uploaded, total_bytes
    upload_completed = pyqtSignal(str, str)  # file_path, file_id
    upload_failed = pyqtSignal(str, str)  # file_path, error_message
    upload_cancelled = pyqtSignal(str)  # file_path
    batch_completed = pyqtSignal(object)  # BatchUploadResult
    
    def __init__(self, 
                 file_service: FileService,
                 validation_service: Optional[FileValidationService] = None):
        """
        Initialize the file upload service.
        
        Args:
            file_service: File service for handling uploads
            validation_service: Optional validation service for pre-upload validation
        """
        super().__init__()
        self.file_service = file_service
        self.validation_service = validation_service or FileValidationService()
        
        # Upload tracking
        self._active_uploads: Dict[str, UploadTask] = {}
        self._upload_queue: List[UploadTask] = []
        self._is_processing_queue = False
        self._cancelled_uploads: set = set()
        
        # Configuration
        self.max_concurrent_uploads = 3
        self.auto_validate = True
        self.auto_retry_attempts = 2
        self.retry_delay_seconds = 1.0
        
        logger.info("FileUploadService initialized")
    
    async def upload_file(self, 
                         file_path: str, 
                         purpose: str = "assistants",
                         validate: bool = None) -> UploadTask:
        """
        Upload a single file asynchronously.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file upload
            validate: Whether to validate before upload (uses auto_validate if None)
            
        Returns:
            UploadTask with upload results
        """
        logger.info(f"Starting file upload: {file_path}")
        
        # Create upload task
        task = UploadTask(file_path=file_path, purpose=purpose)
        self._active_uploads[file_path] = task
        
        try:
            # Emit start signal
            self.upload_started.emit(file_path)
            
            # Validation phase
            if validate if validate is not None else self.auto_validate:
                task.status = UploadStatus.VALIDATING
                validation_result = self.validation_service.validate_file(file_path)
                task.validation_result = validation_result
                
                if not validation_result.is_valid:
                    error_msg = f"Validation failed: {'; '.join(validation_result.errors)}"
                    logger.error(f"Upload failed for {file_path}: {error_msg}")
                    task.status = UploadStatus.FAILED
                    task.error_message = error_msg
                    self.upload_failed.emit(file_path, error_msg)
                    return task
                
                # Store file metadata
                task.total_bytes = validation_result.file_size
                task.metadata.update(validation_result.metadata)
            
            # Check if upload was cancelled during validation
            if file_path in self._cancelled_uploads:
                task.status = UploadStatus.CANCELLED
                self.upload_cancelled.emit(file_path)
                self._cancelled_uploads.discard(file_path)
                return task
            
            # Upload phase
            task.status = UploadStatus.UPLOADING
            task.start_time = time.time()
            
            # Create progress callback
            def progress_callback(progress: FileUploadProgress):
                if file_path in self._cancelled_uploads:
                    # Upload was cancelled
                    return
                
                task.progress = progress.percentage / 100.0
                task.bytes_uploaded = progress.bytes_uploaded
                if not task.total_bytes:
                    task.total_bytes = progress.total_bytes
                
                # Emit progress signal
                self.upload_progress.emit(
                    file_path, 
                    task.progress, 
                    task.bytes_uploaded, 
                    task.total_bytes
                )
            
            # Register progress callback with file service
            self.file_service.add_upload_progress_callback(progress_callback)
            
            try:
                # Perform the actual upload
                result = await self.file_service.upload_file_async(
                    file_path=file_path,
                    purpose=purpose,
                    notify_progress=True
                )
                
                # Check if upload was cancelled
                if file_path in self._cancelled_uploads:
                    task.status = UploadStatus.CANCELLED
                    self.upload_cancelled.emit(file_path)
                    self._cancelled_uploads.discard(file_path)
                    return task
                
                if result.success:
                    task.status = UploadStatus.COMPLETED
                    task.progress = 1.0
                    task.end_time = time.time()
                    task.file_id = result.data.id
                    task.metadata['openai_file'] = result.data
                    
                    logger.info(f"Upload completed for {file_path}: {task.file_id}")
                    self.upload_completed.emit(file_path, task.file_id)
                else:
                    task.status = UploadStatus.FAILED
                    task.error_message = result.error
                    task.end_time = time.time()
                    
                    logger.error(f"Upload failed for {file_path}: {result.error}")
                    self.upload_failed.emit(file_path, result.error)
            
            finally:
                # Cleanup progress callback
                self.file_service.remove_upload_progress_callback(progress_callback)
        
        except Exception as e:
            logger.error(f"Upload error for {file_path}: {e}")
            task.status = UploadStatus.FAILED
            task.error_message = str(e)
            task.end_time = time.time()
            self.upload_failed.emit(file_path, str(e))
        
        finally:
            # Cleanup
            if file_path in self._active_uploads:
                del self._active_uploads[file_path]
            self._cancelled_uploads.discard(file_path)
        
        return task
    
    async def upload_files_batch(self, 
                                file_paths: List[str], 
                                purpose: str = "assistants",
                                validate: bool = None) -> BatchUploadResult:
        """
        Upload multiple files in a batch with controlled concurrency.
        
        Args:
            file_paths: List of file paths to upload
            purpose: Purpose of the file uploads
            validate: Whether to validate before upload (uses auto_validate if None)
            
        Returns:
            BatchUploadResult with batch upload statistics
        """
        logger.info(f"Starting batch upload of {len(file_paths)} files")
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_uploads)
        
        async def upload_with_semaphore(file_path: str) -> UploadTask:
            async with semaphore:
                return await self.upload_file(file_path, purpose, validate)
        
        # Execute uploads with controlled concurrency
        tasks = [upload_with_semaphore(fp) for fp in file_paths]
        upload_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_uploads = []
        failed_uploads = []
        cancelled_uploads = []
        errors = []
        total_bytes_uploaded = 0
        
        for i, result in enumerate(upload_tasks):
            if isinstance(result, Exception):
                # Handle exceptions from gather
                error_msg = str(result)
                errors.append(f"{file_paths[i]}: {error_msg}")
                
                # Create a failed task for this file
                failed_task = UploadTask(
                    file_path=file_paths[i],
                    purpose=purpose,
                    status=UploadStatus.FAILED,
                    error_message=error_msg
                )
                failed_uploads.append(failed_task)
            else:
                # Normal upload task result
                task = result
                if task.status == UploadStatus.COMPLETED:
                    successful_uploads.append(task)
                    total_bytes_uploaded += task.bytes_uploaded
                elif task.status == UploadStatus.CANCELLED:
                    cancelled_uploads.append(task)
                else:
                    failed_uploads.append(task)
                    if task.error_message:
                        errors.append(f"{task.file_path}: {task.error_message}")
        
        # Create batch result
        total_upload_time = time.time() - start_time
        batch_result = BatchUploadResult(
            total_files=len(file_paths),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            cancelled_uploads=cancelled_uploads,
            total_bytes_uploaded=total_bytes_uploaded,
            total_upload_time=total_upload_time,
            errors=errors
        )
        
        logger.info(
            f"Batch upload completed: {len(successful_uploads)}/{len(file_paths)} "
            f"successful, {len(failed_uploads)} failed, {len(cancelled_uploads)} cancelled"
        )
        
        # Emit batch completion signal
        self.batch_completed.emit(batch_result)
        
        return batch_result
    
    def cancel_upload(self, file_path: str) -> bool:
        """
        Cancel an active upload.
        
        Args:
            file_path: Path of the file to cancel upload for
            
        Returns:
            True if cancellation was initiated, False if upload not found
        """
        if file_path in self._active_uploads:
            logger.info(f"Cancelling upload: {file_path}")
            self._cancelled_uploads.add(file_path)
            return True
        
        return False
    
    def cancel_all_uploads(self):
        """Cancel all active uploads."""
        active_files = list(self._active_uploads.keys())
        logger.info(f"Cancelling all uploads: {len(active_files)} files")
        
        for file_path in active_files:
            self._cancelled_uploads.add(file_path)
    
    def get_upload_status(self, file_path: str) -> Optional[UploadTask]:
        """
        Get the current status of an upload.
        
        Args:
            file_path: Path of the file to check
            
        Returns:
            UploadTask if found, None otherwise
        """
        return self._active_uploads.get(file_path)
    
    def get_active_uploads(self) -> Dict[str, UploadTask]:
        """Get all currently active uploads."""
        return self._active_uploads.copy()
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """Get current upload statistics."""
        active_uploads = list(self._active_uploads.values())
        
        total_bytes = sum(task.total_bytes for task in active_uploads)
        uploaded_bytes = sum(task.bytes_uploaded for task in active_uploads)
        
        uploading_tasks = [task for task in active_uploads if task.status == UploadStatus.UPLOADING]
        avg_speed = 0.0
        if uploading_tasks:
            speeds = [task.upload_speed_mbps for task in uploading_tasks]
            avg_speed = sum(speeds) / len(speeds)
        
        return {
            'active_uploads': len(active_uploads),
            'total_bytes': total_bytes,
            'uploaded_bytes': uploaded_bytes,
            'overall_progress': uploaded_bytes / total_bytes if total_bytes > 0 else 0.0,
            'average_speed_mbps': avg_speed,
            'uploading_count': len(uploading_tasks),
            'validating_count': len([t for t in active_uploads if t.status == UploadStatus.VALIDATING]),
            'pending_count': len([t for t in active_uploads if t.status == UploadStatus.PENDING])
        }
    
    def clear_completed_uploads(self):
        """Clear completed upload tasks from tracking."""
        to_remove = [
            file_path for file_path, task in self._active_uploads.items()
            if task.is_complete
        ]
        
        for file_path in to_remove:
            del self._active_uploads[file_path]
        
        logger.debug(f"Cleared {len(to_remove)} completed upload tasks")
    
    def update_configuration(self, **kwargs):
        """
        Update service configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated upload service config: {key} = {value}")
            else:
                logger.warning(f"Unknown upload service config parameter: {key}")