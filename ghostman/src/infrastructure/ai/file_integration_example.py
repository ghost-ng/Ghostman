"""
Example implementation showing how to integrate the OpenAI Files API
with the existing Ghostman AI service.

This demonstrates:
1. File upload with progress tracking
2. Vector store creation and management
3. Chat completion with file search
4. Async operations for UI responsiveness
"""

import asyncio
import logging
from typing import Dict, Any, List

from .api_client import OpenAICompatibleClient
from .file_service import FileService
from .file_models import FileUploadProgress
from .ai_service import AIService

logger = logging.getLogger("ghostman.file_integration_example")


class GhostmanFileIntegration:
    """
    Example integration of OpenAI Files API with Ghostman AI Service.
    
    This class shows how to extend the existing AIService with file
    search capabilities while maintaining compatibility.
    """
    
    def __init__(self, ai_service: AIService):
        """
        Initialize the file integration.
        
        Args:
            ai_service: Existing Ghostman AI service instance
        """
        self.ai_service = ai_service
        self.file_service = None
        self._setup_file_service()
        
        # Progress tracking
        self._upload_progress = {}
        self._active_vector_stores = {}
        
        logger.info("GhostmanFileIntegration initialized")
    
    def _setup_file_service(self):
        """Set up the file service using the AI service's client."""
        if self.ai_service.client:
            self.file_service = FileService(self.ai_service.client)
            
            # Set up callbacks
            self.file_service.add_upload_progress_callback(self._on_upload_progress)
            self.file_service.add_error_callback(self._on_error)
            
            logger.info("File service configured with AI service client")
        else:
            logger.warning("AI service client not available, file service not configured")
    
    def _on_upload_progress(self, progress: FileUploadProgress):
        """Handle upload progress updates."""
        self._upload_progress[progress.file_path] = progress
        
        # Log progress updates
        if progress.status == "uploading":
            logger.info(f"Upload progress: {progress.file_path} - {progress.percentage:.1f}%")
        elif progress.status == "completed":
            logger.info(f"✓ Upload completed: {progress.file_path}")
        elif progress.status == "error":
            logger.error(f"✗ Upload failed: {progress.file_path} - {progress.error}")
    
    def _on_error(self, operation: str, error: Exception):
        """Handle file operation errors."""
        logger.error(f"File operation error in {operation}: {error}")
    
    # File Management Methods
    async def upload_documents_async(
        self,
        file_paths: List[str],
        purpose: str = "assistants"
    ) -> Dict[str, Any]:
        """
        Upload multiple documents asynchronously.
        
        Args:
            file_paths: List of file paths to upload
            purpose: Purpose for the files
            
        Returns:
            Dict with upload results
        """
        if not self.file_service:
            return {"success": False, "error": "File service not configured"}
        
        logger.info(f"Starting upload of {len(file_paths)} documents")
        
        # Validate files first
        validation = self.file_service.validate_files_for_upload(file_paths)
        if validation["invalid_files"]:
            logger.warning(f"Found {len(validation['invalid_files'])} invalid files")
            for error in validation["errors"]:
                logger.warning(f"Validation error: {error}")
        
        # Upload valid files
        upload_results = []
        for file_path in validation["valid_files"]:
            try:
                result = await self.file_service.upload_file_async(file_path, purpose)
                upload_results.append({
                    "file_path": file_path,
                    "success": result.success,
                    "file_id": result.data.id if result.success else None,
                    "error": result.error if not result.success else None
                })
            except Exception as e:
                upload_results.append({
                    "file_path": file_path,
                    "success": False,
                    "file_id": None,
                    "error": str(e)
                })
        
        successful_uploads = [r for r in upload_results if r["success"]]
        failed_uploads = [r for r in upload_results if not r["success"]]
        
        logger.info(f"Upload complete: {len(successful_uploads)} successful, {len(failed_uploads)} failed")
        
        return {
            "success": len(successful_uploads) > 0,
            "uploaded_files": successful_uploads,
            "failed_uploads": failed_uploads,
            "validation_errors": validation["errors"],
            "total_files": len(file_paths),
            "successful_count": len(successful_uploads),
            "failed_count": len(failed_uploads)
        }
    
    async def create_knowledge_base_async(
        self,
        name: str,
        document_paths: List[str],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a knowledge base (vector store) from documents.
        
        Args:
            name: Name for the knowledge base
            document_paths: List of document paths to include
            metadata: Optional metadata for the knowledge base
            
        Returns:
            Dict with knowledge base creation results
        """
        if not self.file_service:
            return {"success": False, "error": "File service not configured"}
        
        logger.info(f"Creating knowledge base '{name}' with {len(document_paths)} documents")
        
        try:
            # Create vector store with files
            result = await self.file_service.create_vector_store_with_files_async(
                name=name,
                file_paths=document_paths,
                metadata=metadata,
                wait_for_completion=True
            )
            
            if result.success:
                vector_store = result.data
                self._active_vector_stores[vector_store.id] = {
                    "name": name,
                    "created_at": vector_store.created_datetime,
                    "file_count": len(document_paths),
                    "metadata": metadata
                }
                
                logger.info(f"✓ Knowledge base created successfully: {vector_store.id}")
                return {
                    "success": True,
                    "vector_store_id": vector_store.id,
                    "name": name,
                    "file_count": len(document_paths),
                    "vector_store": vector_store.to_dict()
                }
            else:
                logger.error(f"✗ Failed to create knowledge base: {result.error}")
                return {
                    "success": False,
                    "error": result.error
                }
                
        except Exception as e:
            logger.error(f"Error creating knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def chat_with_documents_async(
        self,
        message: str,
        vector_store_ids: List[str],
        model: str = None,
        temperature: float = 0.7,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Chat with document-backed AI using file search.
        
        Args:
            message: User message
            vector_store_ids: List of vector store IDs to search
            model: Model to use (defaults to AI service model)
            temperature: Sampling temperature
            include_sources: Whether to include source information
            
        Returns:
            Dict with chat response and source information
        """
        if not self.file_service:
            return {"success": False, "error": "File service not configured"}
        
        if not self.ai_service.is_initialized:
            return {"success": False, "error": "AI service not initialized"}
        
        # Use AI service model if not specified
        if model is None:
            model = self.ai_service.current_config.get("model_name", "gpt-3.5-turbo")
        
        logger.info(f"Chat with documents: {len(vector_store_ids)} knowledge bases")
        
        try:
            # Prepare messages in the same format as AI service
            messages = []
            
            # Add system prompt if available
            system_messages = [msg for msg in self.ai_service.conversation.messages if msg.role == 'system']
            if system_messages:
                messages.append({
                    "role": "system",
                    "content": system_messages[-1].content
                })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Make chat request with file search
            result = await self.file_service.chat_with_files_async(
                messages=messages,
                model=model,
                vector_store_ids=vector_store_ids,
                temperature=temperature,
                max_tokens=self.ai_service.current_config.get("max_tokens")
            )
            
            if result["success"]:
                response_data = result["response"]
                file_search_results = result.get("file_search_results", [])
                
                # Extract response content using AI service method
                assistant_message = self.ai_service._extract_response_content(response_data)
                
                # Add to conversation history
                self.ai_service.conversation.add_message('user', message)
                self.ai_service.conversation.add_message('assistant', assistant_message)
                
                logger.info(f"✓ Chat with documents completed - {len(file_search_results)} sources found")
                
                chat_result = {
                    "success": True,
                    "response": assistant_message,
                    "usage": response_data.get("usage", {}),
                    "model_used": model,
                    "vector_stores_searched": len(vector_store_ids)
                }
                
                if include_sources and file_search_results:
                    chat_result["sources"] = file_search_results
                    chat_result["source_count"] = len(file_search_results)
                
                return chat_result
            else:
                logger.error(f"✗ Chat with documents failed: {result['error']}\")\n                return {\n                    \"success\": False,\n                    \"error\": result[\"error\"]\n                }\n                \n        except Exception as e:\n            logger.error(f\"Error in chat with documents: {e}\")\n            return {\n                \"success\": False,\n                \"error\": str(e)\n            }\n    \n    # Knowledge Base Management\n    async def list_knowledge_bases_async(self) -> Dict[str, Any]:\n        \"\"\"List available knowledge bases (vector stores).\"\"\"\n        if not self.file_service:\n            return {\"success\": False, \"error\": \"File service not configured\"}\n        \n        try:\n            result = await self.file_service.get_vector_stores_async()\n            \n            if result.success:\n                vector_stores = result.data\n                knowledge_bases = []\n                \n                for vs in vector_stores:\n                    kb_info = {\n                        \"id\": vs.id,\n                        \"name\": vs.name or \"Unnamed\",\n                        \"created_at\": vs.created_datetime.isoformat(),\n                        \"file_count\": vs.file_counts.total if vs.file_counts else 0,\n                        \"usage_mb\": vs.usage_mb,\n                        \"status\": vs.status\n                    }\n                    knowledge_bases.append(kb_info)\n                \n                logger.info(f\"✓ Retrieved {len(knowledge_bases)} knowledge bases\")\n                return {\n                    \"success\": True,\n                    \"knowledge_bases\": knowledge_bases,\n                    \"total_count\": len(knowledge_bases)\n                }\n            else:\n                logger.error(f\"✗ Failed to list knowledge bases: {result.error}\")\n                return {\n                    \"success\": False,\n                    \"error\": result.error\n                }\n                \n        except Exception as e:\n            logger.error(f\"Error listing knowledge bases: {e}\")\n            return {\n                \"success\": False,\n                \"error\": str(e)\n            }\n    \n    async def delete_knowledge_base_async(self, vector_store_id: str) -> Dict[str, Any]:\n        \"\"\"Delete a knowledge base (vector store).\"\"\"\n        if not self.file_service:\n            return {\"success\": False, \"error\": \"File service not configured\"}\n        \n        try:\n            result = await self.file_service.delete_vector_store_async(vector_store_id)\n            \n            if result.success:\n                # Remove from active tracking\n                if vector_store_id in self._active_vector_stores:\n                    del self._active_vector_stores[vector_store_id]\n                \n                logger.info(f\"✓ Knowledge base deleted: {vector_store_id}\")\n                return {\n                    \"success\": True,\n                    \"vector_store_id\": vector_store_id\n                }\n            else:\n                logger.error(f\"✗ Failed to delete knowledge base: {result.error}\")\n                return {\n                    \"success\": False,\n                    \"error\": result.error\n                }\n                \n        except Exception as e:\n            logger.error(f\"Error deleting knowledge base: {e}\")\n            return {\n                \"success\": False,\n                \"error\": str(e)\n            }\n    \n    # Status and Monitoring\n    def get_upload_progress(self) -> Dict[str, Any]:\n        \"\"\"Get current upload progress for all files.\"\"\"\n        return {\n            \"active_uploads\": len([p for p in self._upload_progress.values() \n                                 if p.status == \"uploading\"]),\n            \"completed_uploads\": len([p for p in self._upload_progress.values() \n                                    if p.status == \"completed\"]),\n            \"failed_uploads\": len([p for p in self._upload_progress.values() \n                                 if p.status == \"error\"]),\n            \"progress_details\": {path: progress.to_dict() \n                               for path, progress in self._upload_progress.items()}\n        }\n    \n    def get_integration_status(self) -> Dict[str, Any]:\n        \"\"\"Get overall integration status.\"\"\"\n        return {\n            \"ai_service_initialized\": self.ai_service.is_initialized,\n            \"file_service_configured\": self.file_service is not None,\n            \"active_vector_stores\": len(self._active_vector_stores),\n            \"upload_progress_tracked\": len(self._upload_progress),\n            \"client_available\": self.ai_service.client is not None,\n            \"base_url\": self.ai_service.current_config.get(\"base_url\"),\n            \"model\": self.ai_service.current_config.get(\"model_name\")\n        }\n    \n    def clear_upload_history(self):\n        \"\"\"Clear upload progress history.\"\"\"\n        self._upload_progress.clear()\n        logger.info(\"Upload progress history cleared\")\n\n\n# Example usage function\nasync def example_usage():\n    \"\"\"\n    Example of how to use the file integration with existing AI service.\n    \"\"\"\n    from ...infrastructure.storage.settings_manager import settings\n    \n    # Initialize AI service (as normally done in Ghostman)\n    ai_service = AIService()\n    config_success = ai_service.initialize()\n    \n    if not config_success:\n        print(\"Failed to initialize AI service\")\n        return\n    \n    # Create file integration\n    file_integration = GhostmanFileIntegration(ai_service)\n    \n    # Check integration status\n    status = file_integration.get_integration_status()\n    print(f\"Integration status: {status}\")\n    \n    # Example: Upload documents and create knowledge base\n    document_paths = [\n        \"/path/to/document1.pdf\",\n        \"/path/to/document2.txt\",\n        \"/path/to/document3.md\"\n    ]\n    \n    # Upload documents\n    upload_result = await file_integration.upload_documents_async(document_paths)\n    print(f\"Upload result: {upload_result}\")\n    \n    # Create knowledge base\n    if upload_result[\"success\"]:\n        kb_result = await file_integration.create_knowledge_base_async(\n            name=\"My Knowledge Base\",\n            document_paths=document_paths,\n            metadata={\"project\": \"example\", \"version\": \"1.0\"}\n        )\n        print(f\"Knowledge base result: {kb_result}\")\n        \n        # Chat with documents\n        if kb_result[\"success\"]:\n            chat_result = await file_integration.chat_with_documents_async(\n                message=\"What are the main topics covered in these documents?\",\n                vector_store_ids=[kb_result[\"vector_store_id\"]],\n                include_sources=True\n            )\n            print(f\"Chat result: {chat_result}\")\n    \n    # List knowledge bases\n    kb_list = await file_integration.list_knowledge_bases_async()\n    print(f\"Knowledge bases: {kb_list}\")\n\n\nif __name__ == \"__main__\":\n    # Run example\n    asyncio.run(example_usage())