"""
File Service for OpenAI Files API integration.

High-level service that manages file uploads, vector stores, and file search
functionality for the Ghostman application.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .api_client import OpenAICompatibleClient
from .file_models import (
    OpenAIFile, VectorStore, VectorStoreFile, FileUploadProgress,
    FileOperationResult, ProgressCallback, validate_file_for_upload
)

logger = logging.getLogger("ghostman.file_service")


class FileService:
    """
    High-level file management service for OpenAI integration.
    
    Provides simplified interfaces for:
    - File uploads with progress tracking
    - Vector store management
    - File search integration
    - Async operations for UI responsiveness
    """
    
    def __init__(self, client: OpenAICompatibleClient):
        """
        Initialize the file service.
        
        Args:
            client: OpenAI-compatible API client
        """
        self.client = client
        self._upload_callbacks: List[ProgressCallback] = []
        self._error_callbacks: List[Callable[[str, Exception], None]] = []
        
        logger.info("FileService initialized")
    
    # File Upload Management
    def add_upload_progress_callback(self, callback: ProgressCallback):
        """Add a callback for upload progress updates."""
        self._upload_callbacks.append(callback)
    
    def remove_upload_progress_callback(self, callback: ProgressCallback):
        """Remove an upload progress callback."""
        if callback in self._upload_callbacks:
            self._upload_callbacks.remove(callback)
    
    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """Add a callback for error notifications."""
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[str, Exception], None]):
        """Remove an error callback."""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def _notify_upload_progress(self, progress: FileUploadProgress):
        """Notify all upload progress callbacks."""
        for callback in self._upload_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in upload progress callback: {e}")
    
    def _notify_error(self, operation: str, error: Exception):
        """Notify all error callbacks."""
        for callback in self._error_callbacks:
            try:
                callback(operation, error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    # File Operations
    async def upload_file_async(
        self,
        file_path: str,
        purpose: str = "assistants",
        notify_progress: bool = True
    ) -> FileOperationResult:
        """
        Upload a file asynchronously with progress tracking.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (assistants, fine-tune, etc.)
            notify_progress: Whether to notify progress callbacks
            
        Returns:
            FileOperationResult with uploaded file information
        """
        try:
            logger.info(f"Starting async file upload: {file_path}")
            
            # Prepare progress callback if needed
            progress_callback = None
            if notify_progress:
                progress_callback = self._notify_upload_progress
            
            # Upload the file
            result = await self.client.upload_file_async(
                file_path=file_path,
                purpose=purpose,
                progress_callback=progress_callback
            )
            
            if result.success:
                logger.info(f"✓ File uploaded successfully: {result.data.id}")
            else:
                logger.error(f"✗ File upload failed: {result.error}")
                if self._error_callbacks:
                    self._notify_error("file_upload", Exception(result.error))
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Error in async file upload: {e}")
            if self._error_callbacks:
                self._notify_error("file_upload", e)
            return FileOperationResult(success=False, error=str(e))
    
    def upload_file_sync(
        self,
        file_path: str,
        purpose: str = "assistants",
        notify_progress: bool = True
    ) -> FileOperationResult:
        """
        Upload a file synchronously with progress tracking.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (assistants, fine-tune, etc.)
            notify_progress: Whether to notify progress callbacks
            
        Returns:
            FileOperationResult with uploaded file information
        """
        try:
            logger.info(f"Starting sync file upload: {file_path}")
            
            # Prepare progress callback if needed
            progress_callback = None
            if notify_progress:
                progress_callback = self._notify_upload_progress
            
            # Upload the file
            result = self.client.upload_file(
                file_path=file_path,
                purpose=purpose,
                progress_callback=progress_callback
            )
            
            if result.success:
                logger.info(f"✓ File uploaded successfully: {result.data.id}")
            else:
                logger.error(f"✗ File upload failed: {result.error}")
                if self._error_callbacks:
                    self._notify_error("file_upload", Exception(result.error))
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Error in sync file upload: {e}")
            if self._error_callbacks:
                self._notify_error("file_upload", e)
            return FileOperationResult(success=False, error=str(e))
    
    async def get_files_async(
        self,
        purpose: Optional[str] = None,
        limit: Optional[int] = None
    ) -> FileOperationResult:
        """Get list of uploaded files asynchronously."""
        try:
            logger.debug(f"Getting files list (purpose: {purpose}, limit: {limit})")
            return await self.client.list_files_async(purpose=purpose, limit=limit)
        except Exception as e:
            logger.error(f"Error getting files list: {e}")
            if self._error_callbacks:
                self._notify_error("list_files", e)
            return FileOperationResult(success=False, error=str(e))
    
    async def delete_file_async(self, file_id: str) -> FileOperationResult:
        """Delete a file asynchronously."""
        try:
            logger.info(f"Deleting file: {file_id}")
            result = await self.client.delete_file_async(file_id)
            
            if result.success:
                logger.info(f"✓ File deleted successfully: {file_id}")
            else:
                logger.error(f"✗ File deletion failed: {result.error}")
                if self._error_callbacks:
                    self._notify_error("delete_file", Exception(result.error))
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            if self._error_callbacks:
                self._notify_error("delete_file", e)
            return FileOperationResult(success=False, error=str(e))
    
    # Vector Store Operations
    async def create_vector_store_with_files_async(
        self,
        name: str,
        file_paths: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        timeout_seconds: int = 300
    ) -> FileOperationResult:
        """
        Create a vector store and upload files to it in one operation.
        
        Args:
            name: Name for the vector store
            file_paths: List of file paths to upload and add
            metadata: Optional metadata for the vector store
            wait_for_completion: Whether to wait for processing to complete
            timeout_seconds: Timeout for waiting for completion
            
        Returns:
            FileOperationResult with vector store information
        """
        try:
            logger.info(f"Creating vector store '{name}' with {len(file_paths)} files")
            
            # First, upload all files
            uploaded_files = []
            for file_path in file_paths:
                logger.info(f"Uploading file for vector store: {file_path}")
                upload_result = await self.upload_file_async(file_path, purpose="assistants")
                
                if upload_result.success:
                    uploaded_files.append(upload_result.data.id)
                    logger.debug(f"✓ File uploaded: {upload_result.data.id}")
                else:
                    logger.error(f"✗ Failed to upload {file_path}: {upload_result.error}")
                    # Clean up already uploaded files on failure
                    for file_id in uploaded_files:
                        try:
                            await self.client.delete_file_async(file_id)
                        except:
                            pass  # Ignore cleanup errors
                    return FileOperationResult(
                        success=False,
                        error=f"Failed to upload {file_path}: {upload_result.error}"
                    )
            
            # Create vector store with uploaded files
            vs_result = await self.client.create_vector_store_async(
                name=name,
                file_ids=uploaded_files,
                metadata=metadata
            )
            
            if not vs_result.success:
                logger.error(f"✗ Failed to create vector store: {vs_result.error}")
                # Clean up uploaded files
                for file_id in uploaded_files:
                    try:
                        await self.client.delete_file_async(file_id)
                    except:
                        pass  # Ignore cleanup errors
                return vs_result
            
            vector_store = vs_result.data
            logger.info(f"✓ Vector store created: {vector_store.id}")
            
            # Wait for completion if requested
            if wait_for_completion:
                logger.info(f"Waiting for vector store processing to complete...")
                # Note: This would need to be implemented as an async version
                # For now, we'll return the initial result
                pass
            
            return vs_result
            
        except Exception as e:
            logger.error(f"Error creating vector store with files: {e}")
            if self._error_callbacks:
                self._notify_error("create_vector_store", e)
            return FileOperationResult(success=False, error=str(e))
    
    async def get_vector_stores_async(
        self,
        limit: Optional[int] = None
    ) -> FileOperationResult:
        """Get list of vector stores asynchronously."""
        try:
            logger.debug(f"Getting vector stores list (limit: {limit})")
            return await self.client.list_vector_stores_async(limit=limit)
        except Exception as e:
            logger.error(f"Error getting vector stores list: {e}")
            if self._error_callbacks:
                self._notify_error("list_vector_stores", e)
            return FileOperationResult(success=False, error=str(e))
    
    async def delete_vector_store_async(self, vector_store_id: str) -> FileOperationResult:
        """Delete a vector store asynchronously."""
        try:
            logger.info(f"Deleting vector store: {vector_store_id}")
            result = await self.client.delete_vector_store_async(vector_store_id)
            
            if result.success:
                logger.info(f"✓ Vector store deleted successfully: {vector_store_id}")
            else:
                logger.error(f"✗ Vector store deletion failed: {result.error}")
                if self._error_callbacks:
                    self._notify_error("delete_vector_store", Exception(result.error))
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting vector store: {e}")
            if self._error_callbacks:
                self._notify_error("delete_vector_store", e)
            return FileOperationResult(success=False, error=str(e))
    
    # File Search Integration
    async def chat_with_files_async(
        self,
        messages: List[Dict[str, str]],
        model: str,
        vector_store_ids: List[str],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat with file search enabled.
        
        Args:
            messages: List of message objects
            model: Model name to use
            vector_store_ids: List of vector store IDs to search
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Dict with response and file search results
        """
        try:
            logger.info(f"Chat with file search: {len(vector_store_ids)} vector stores")
            
            response = await self.client.chat_completion_with_file_search_async(
                messages=messages,
                model=model,
                vector_store_ids=vector_store_ids,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            if response.success:
                # Extract file search results if present
                result = {
                    "success": True,
                    "response": response.data,
                    "file_search_results": self._extract_file_search_results(response.data)
                }
                
                logger.info(f"✓ Chat with file search completed")
                return result
            else:
                logger.error(f"✗ Chat with file search failed: {response.error}")
                if self._error_callbacks:
                    self._notify_error("chat_with_files", Exception(response.error))
                return {
                    "success": False,
                    "error": response.error
                }
                
        except Exception as e:
            logger.error(f"Error in chat with files: {e}")
            if self._error_callbacks:
                self._notify_error("chat_with_files", e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_file_search_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract file search results from chat completion response."""
        file_results = []
        
        try:
            choices = response_data.get("choices", [])
            for choice in choices:
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                for tool_call in tool_calls:
                    if tool_call.get("type") == "file_search":
                        function_data = tool_call.get("function", {})
                        results = function_data.get("results", [])
                        file_results.extend(results)
                        
        except Exception as e:
            logger.debug(f"No file search results found in response: {e}")
        
        return file_results
    
    # Utility Methods
    def validate_files_for_upload(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Validate multiple files for upload.
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dict with validation results
        """
        results = {
            "valid_files": [],
            "invalid_files": [],
            "total_size": 0,
            "errors": []
        }
        
        for file_path in file_paths:
            is_valid, error_msg = validate_file_for_upload(file_path)
            
            if is_valid:
                results["valid_files"].append(file_path)
                try:
                    file_size = Path(file_path).stat().st_size
                    results["total_size"] += file_size
                except:
                    pass  # Ignore size calculation errors
            else:
                results["invalid_files"].append(file_path)
                results["errors"].append(f"{file_path}: {error_msg}")
        
        return results
    
    def get_upload_summary(self) -> Dict[str, Any]:
        """Get summary of current upload state."""
        return {
            "progress_callbacks": len(self._upload_callbacks),
            "error_callbacks": len(self._error_callbacks),
            "client_configured": self.client is not None
        }