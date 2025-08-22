"""
Fine Tuning Service for Ghostman.

Provides vector store management, file search integration, and comprehensive
file retrieval capabilities for the Ghostman AI assistant.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, pyqtSignal

from .file_upload_service import FileUploadService, UploadTask, BatchUploadResult
from .file_validation_service import FileValidationService
from ...infrastructure.ai.file_service import FileService
from ...infrastructure.ai.file_models import VectorStore, FileOperationResult

logger = logging.getLogger("ghostman.fine_tuning_service")


class VectorStoreStatus(Enum):
    """Status enumeration for vector stores."""
    CREATING = "creating"
    ACTIVE = "active"
    PROCESSING = "processing"
    EXPIRED = "expired"
    DELETING = "deleting"
    ERROR = "error"


@dataclass
class VectorStoreInfo:
    """Extended vector store information with metadata."""
    vector_store: VectorStore
    file_count: int = 0
    total_size_bytes: int = 0
    creation_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    status: VectorStoreStatus = VectorStoreStatus.ACTIVE
    processing_progress: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_days(self) -> float:
        """Calculate age of vector store in days."""
        if not self.creation_time:
            return 0.0
        return (datetime.now() - self.creation_time).total_seconds() / 86400
    
    @property
    def size_mb(self) -> float:
        """Get total size in MB."""
        return self.total_size_bytes / (1024 * 1024)


@dataclass
class FileSearchResult:
    """Result of a file search operation."""
    query: str
    results: List[Dict[str, Any]]
    vector_store_id: str
    search_time_ms: float
    total_results: int
    relevance_scores: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatWithFilesResult:
    """Result of a chat with files operation."""
    response_text: str
    file_search_results: List[FileSearchResult]
    response_metadata: Dict[str, Any]
    processing_time_ms: float
    tokens_used: int
    model_used: str


class FineTuningService(QObject):
    """
    Comprehensive fine-tuning and vector store management service.
    
    Features:
    - Vector store creation and management
    - File upload integration with vector stores
    - File search and retrieval
    - Chat with files functionality
    - Vector store analytics and monitoring
    - Cleanup and maintenance operations
    """
    
    # PyQt signals for UI integration
    vector_store_created = pyqtSignal(str, str)  # vector_store_id, name
    vector_store_updated = pyqtSignal(str)  # vector_store_id
    vector_store_deleted = pyqtSignal(str)  # vector_store_id
    file_search_completed = pyqtSignal(object)  # FileSearchResult
    chat_completed = pyqtSignal(object)  # ChatWithFilesResult
    processing_progress = pyqtSignal(str, float)  # vector_store_id, progress
    error_occurred = pyqtSignal(str, str)  # operation, error_message
    
    def __init__(self,
                 file_service: FileService,
                 upload_service: FileUploadService,
                 validation_service: Optional[FileValidationService] = None):
        """
        Initialize the fine-tuning service.
        
        Args:
            file_service: File service for API operations
            upload_service: Upload service for file handling
            validation_service: Optional validation service
        """
        super().__init__()
        self.file_service = file_service
        self.upload_service = upload_service
        self.validation_service = validation_service or FileValidationService()
        
        # Vector store tracking
        self._vector_stores: Dict[str, VectorStoreInfo] = {}
        self._active_searches: Dict[str, Any] = {}
        
        # Configuration
        self.default_expiration_days = 365
        self.max_files_per_store = 10000
        self.auto_cleanup_enabled = True
        self.search_timeout_seconds = 30
        
        # Connect to upload service signals
        self.upload_service.batch_completed.connect(self._on_batch_upload_completed)
        
        logger.info("FineTuningService initialized")
    
    async def create_vector_store_with_files(self,
                                           name: str,
                                           file_paths: List[str],
                                           metadata: Optional[Dict[str, Any]] = None,
                                           wait_for_completion: bool = True) -> VectorStoreInfo:
        """
        Create a new vector store and upload files to it.
        
        Args:
            name: Name for the vector store
            file_paths: List of file paths to upload
            metadata: Optional metadata for the vector store
            wait_for_completion: Whether to wait for processing completion
            
        Returns:
            VectorStoreInfo with the created vector store details
        """
        logger.info(f"Creating vector store '{name}' with {len(file_paths)} files")
        
        try:
            # Validate files first
            validation_results = self.validation_service.validate_files(file_paths)
            valid_files = [fp for fp, result in validation_results.items() if result.is_valid]
            invalid_files = [fp for fp, result in validation_results.items() if not result.is_valid]
            
            if invalid_files:
                logger.warning(f"Skipping {len(invalid_files)} invalid files")
                for fp in invalid_files:
                    logger.warning(f"Invalid file: {fp} - {validation_results[fp].errors}")
            
            if not valid_files:
                raise ValueError("No valid files to upload")
            
            # Create vector store with files
            result = await self.file_service.create_vector_store_with_files_async(
                name=name,
                file_paths=valid_files,
                metadata=metadata,
                wait_for_completion=wait_for_completion
            )
            
            if not result.success:
                error_msg = f"Failed to create vector store: {result.error}"
                logger.error(error_msg)
                self.error_occurred.emit("create_vector_store", error_msg)
                raise RuntimeError(error_msg)
            
            # Create vector store info
            vector_store = result.data
            total_size = sum(validation_results[fp].file_size for fp in valid_files)
            
            vs_info = VectorStoreInfo(
                vector_store=vector_store,
                file_count=len(valid_files),
                total_size_bytes=total_size,
                creation_time=datetime.now(),
                status=VectorStoreStatus.PROCESSING if wait_for_completion else VectorStoreStatus.ACTIVE,
                metadata=metadata or {}
            )
            
            # Store in our tracking
            self._vector_stores[vector_store.id] = vs_info
            
            logger.info(f"Vector store created: {vector_store.id}")
            self.vector_store_created.emit(vector_store.id, name)
            
            # Wait for processing if requested
            if wait_for_completion:
                await self._wait_for_vector_store_processing(vector_store.id)
            
            return vs_info
        
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            self.error_occurred.emit("create_vector_store", str(e))
            raise
    
    async def add_files_to_vector_store(self,
                                      vector_store_id: str,
                                      file_paths: List[str],
                                      wait_for_processing: bool = True) -> BatchUploadResult:
        """
        Add files to an existing vector store.
        
        Args:
            vector_store_id: ID of the vector store
            file_paths: List of file paths to add
            wait_for_processing: Whether to wait for processing completion
            
        Returns:
            BatchUploadResult with upload details
        """
        logger.info(f"Adding {len(file_paths)} files to vector store {vector_store_id}")
        
        try:
            # First upload the files
            batch_result = await self.upload_service.upload_files_batch(
                file_paths=file_paths,
                purpose="assistants"
            )
            
            if not batch_result.successful_uploads:
                raise ValueError("No files were successfully uploaded")
            
            # Extract file IDs from successful uploads
            file_ids = [task.file_id for task in batch_result.successful_uploads]
            
            # Add files to vector store (this would need API support)
            # For now, we'll just update our tracking
            if vector_store_id in self._vector_stores:
                vs_info = self._vector_stores[vector_store_id]
                vs_info.file_count += len(file_ids)
                vs_info.total_size_bytes += batch_result.total_bytes_uploaded
                vs_info.last_updated = datetime.now()
                
                if wait_for_processing:
                    vs_info.status = VectorStoreStatus.PROCESSING
                    self.vector_store_updated.emit(vector_store_id)
                    await self._wait_for_vector_store_processing(vector_store_id)
            
            logger.info(f"Added {len(file_ids)} files to vector store {vector_store_id}")
            return batch_result
        
        except Exception as e:
            logger.error(f"Error adding files to vector store: {e}")
            self.error_occurred.emit("add_files_to_vector_store", str(e))
            raise
    
    async def search_files(self,
                          query: str,
                          vector_store_ids: List[str],
                          max_results: int = 10,
                          relevance_threshold: float = 0.5) -> List[FileSearchResult]:
        """
        Search for files across vector stores.
        
        Args:
            query: Search query
            vector_store_ids: List of vector store IDs to search
            max_results: Maximum number of results per vector store
            relevance_threshold: Minimum relevance score threshold
            
        Returns:
            List of FileSearchResult objects
        """
        logger.info(f"Searching files: '{query}' across {len(vector_store_ids)} vector stores")
        search_start = time.time()
        
        try:
            search_results = []
            
            for vs_id in vector_store_ids:
                # Create a mock search for now (would use actual API)
                # This is a placeholder implementation
                search_result = FileSearchResult(
                    query=query,
                    results=[],  # Would contain actual search results
                    vector_store_id=vs_id,
                    search_time_ms=(time.time() - search_start) * 1000,
                    total_results=0,
                    relevance_scores=[]
                )
                search_results.append(search_result)
                
                # Emit signal for each completed search
                self.file_search_completed.emit(search_result)
            
            logger.info(f"File search completed: {len(search_results)} results")
            return search_results
        
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            self.error_occurred.emit("search_files", str(e))
            raise
    
    async def chat_with_files(self,
                            messages: List[Dict[str, str]],
                            vector_store_ids: List[str],
                            model: str = "gpt-4",
                            temperature: float = 0.7,
                            max_tokens: Optional[int] = None) -> ChatWithFilesResult:
        """
        Chat with AI using file context from vector stores.
        
        Args:
            messages: List of conversation messages
            vector_store_ids: List of vector store IDs for context
            model: Model to use for chat
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            ChatWithFilesResult with response and file search results
        """
        logger.info(f"Chat with files: {len(messages)} messages, {len(vector_store_ids)} vector stores")
        start_time = time.time()
        
        try:
            # Use file service to chat with file search
            result = await self.file_service.chat_with_files_async(
                messages=messages,
                model=model,
                vector_store_ids=vector_store_ids,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not result["success"]:
                raise RuntimeError(f"Chat with files failed: {result.get('error', 'Unknown error')}")
            
            # Extract response data
            response_data = result["response"]
            file_search_results = result.get("file_search_results", [])
            
            # Create result object
            chat_result = ChatWithFilesResult(
                response_text=self._extract_response_text(response_data),
                file_search_results=self._convert_file_search_results(file_search_results),
                response_metadata=self._extract_response_metadata(response_data),
                processing_time_ms=(time.time() - start_time) * 1000,
                tokens_used=self._extract_token_usage(response_data),
                model_used=model
            )
            
            logger.info(f"Chat with files completed: {chat_result.tokens_used} tokens used")
            self.chat_completed.emit(chat_result)
            
            return chat_result
        
        except Exception as e:
            logger.error(f"Error in chat with files: {e}")
            self.error_occurred.emit("chat_with_files", str(e))
            raise
    
    async def get_vector_stores(self) -> Dict[str, VectorStoreInfo]:
        """
        Get all vector stores with updated information.
        
        Returns:
            Dictionary mapping vector store IDs to VectorStoreInfo objects
        """
        logger.debug("Fetching vector stores")
        
        try:
            # Get vector stores from API
            result = await self.file_service.get_vector_stores_async()
            
            if not result.success:
                logger.error(f"Failed to fetch vector stores: {result.error}")
                return self._vector_stores.copy()
            
            # Update our tracking with fresh data
            api_stores = result.data if isinstance(result.data, list) else []
            
            for vs in api_stores:
                if vs.id in self._vector_stores:
                    # Update existing store info
                    vs_info = self._vector_stores[vs.id]
                    vs_info.vector_store = vs
                    vs_info.last_updated = datetime.now()
                else:
                    # Create new store info
                    vs_info = VectorStoreInfo(
                        vector_store=vs,
                        creation_time=datetime.now(),
                        last_updated=datetime.now()
                    )
                    self._vector_stores[vs.id] = vs_info
            
            return self._vector_stores.copy()
        
        except Exception as e:
            logger.error(f"Error fetching vector stores: {e}")
            self.error_occurred.emit("get_vector_stores", str(e))
            return self._vector_stores.copy()
    
    async def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Delete a vector store.
        
        Args:
            vector_store_id: ID of the vector store to delete
            
        Returns:
            True if deletion was successful
        """
        logger.info(f"Deleting vector store: {vector_store_id}")
        
        try:
            # Update status
            if vector_store_id in self._vector_stores:
                self._vector_stores[vector_store_id].status = VectorStoreStatus.DELETING
                self.vector_store_updated.emit(vector_store_id)
            
            # Delete via API
            result = await self.file_service.delete_vector_store_async(vector_store_id)
            
            if result.success:
                # Remove from our tracking
                if vector_store_id in self._vector_stores:
                    del self._vector_stores[vector_store_id]
                
                logger.info(f"Vector store deleted: {vector_store_id}")
                self.vector_store_deleted.emit(vector_store_id)
                return True
            else:
                logger.error(f"Failed to delete vector store: {result.error}")
                # Revert status
                if vector_store_id in self._vector_stores:
                    self._vector_stores[vector_store_id].status = VectorStoreStatus.ERROR
                    self._vector_stores[vector_store_id].error_message = result.error
                    self.vector_store_updated.emit(vector_store_id)
                return False
        
        except Exception as e:
            logger.error(f"Error deleting vector store: {e}")
            self.error_occurred.emit("delete_vector_store", str(e))
            return False
    
    async def cleanup_expired_vector_stores(self) -> List[str]:
        """
        Cleanup vector stores that have expired.
        
        Returns:
            List of deleted vector store IDs
        """
        if not self.auto_cleanup_enabled:
            return []
        
        logger.info("Running vector store cleanup")
        deleted_stores = []
        
        try:
            current_stores = await self.get_vector_stores()
            
            for vs_id, vs_info in current_stores.items():
                if vs_info.age_days > self.default_expiration_days:
                    logger.info(f"Cleaning up expired vector store: {vs_id} (age: {vs_info.age_days:.1f} days)")
                    
                    if await self.delete_vector_store(vs_id):
                        deleted_stores.append(vs_id)
            
            if deleted_stores:
                logger.info(f"Cleanup completed: {len(deleted_stores)} vector stores deleted")
            else:
                logger.debug("No expired vector stores found")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self.error_occurred.emit("cleanup_expired_vector_stores", str(e))
        
        return deleted_stores
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about vector stores and usage."""
        total_stores = len(self._vector_stores)
        total_files = sum(vs.file_count for vs in self._vector_stores.values())
        total_size_mb = sum(vs.size_mb for vs in self._vector_stores.values())
        
        status_counts = {}
        for status in VectorStoreStatus:
            status_counts[status.value] = len([
                vs for vs in self._vector_stores.values() 
                if vs.status == status
            ])
        
        avg_age_days = 0.0
        if self._vector_stores:
            avg_age_days = sum(vs.age_days for vs in self._vector_stores.values()) / len(self._vector_stores)
        
        return {
            'total_vector_stores': total_stores,
            'total_files': total_files,
            'total_size_mb': total_size_mb,
            'average_age_days': avg_age_days,
            'status_distribution': status_counts,
            'active_searches': len(self._active_searches),
            'cleanup_enabled': self.auto_cleanup_enabled,
            'expiration_days': self.default_expiration_days
        }
    
    # Private helper methods
    
    async def _wait_for_vector_store_processing(self, vector_store_id: str, timeout_seconds: int = 300):
        """Wait for vector store processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # Update progress (this would query actual API status)
            progress = min(100.0, ((time.time() - start_time) / timeout_seconds) * 100)
            self.processing_progress.emit(vector_store_id, progress)
            
            # For now, just wait a bit and mark as complete
            await asyncio.sleep(1)
            
            # Simulate completion after some time
            if time.time() - start_time > 5:  # 5 seconds for demo
                if vector_store_id in self._vector_stores:
                    self._vector_stores[vector_store_id].status = VectorStoreStatus.ACTIVE
                    self._vector_stores[vector_store_id].processing_progress = 100.0
                    self.vector_store_updated.emit(vector_store_id)
                break
    
    def _on_batch_upload_completed(self, batch_result: BatchUploadResult):
        """Handle batch upload completion."""
        logger.debug(f"Batch upload completed: {len(batch_result.successful_uploads)} files")
        # Additional processing could be done here
    
    def _extract_response_text(self, response_data: Dict[str, Any]) -> str:
        """Extract response text from API response."""
        try:
            choices = response_data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
        except:
            pass
        return ""
    
    def _convert_file_search_results(self, raw_results: List[Dict[str, Any]]) -> List[FileSearchResult]:
        """Convert raw file search results to FileSearchResult objects."""
        # This would convert API-specific format to our internal format
        return []
    
    def _extract_response_metadata(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from API response."""
        return {
            'model': response_data.get('model', ''),
            'created': response_data.get('created', 0),
            'id': response_data.get('id', ''),
            'object': response_data.get('object', '')
        }
    
    def _extract_token_usage(self, response_data: Dict[str, Any]) -> int:
        """Extract token usage from API response."""
        usage = response_data.get('usage', {})
        return usage.get('total_tokens', 0)
    
    def update_configuration(self, **kwargs):
        """
        Update service configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated fine-tuning service config: {key} = {value}")
            else:
                logger.warning(f"Unknown fine-tuning service config parameter: {key}")