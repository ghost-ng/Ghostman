"""
LangChain Integration Service for Ghostman

Bridges the LangChain RAG pipeline with the existing Ghostman UI and conversation system.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import queue

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from .unified_session_langchain import UnifiedSessionLangChainRAGPipeline
from ..conversation_management.services.conversation_service import ConversationService
from ..conversation_management.models.enums import MessageRole

logger = logging.getLogger("ghostman.langchain_integration")


class ProcessingStatus(Enum):
    """File processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentProcessingResult:
    """Result of document processing."""
    file_id: str
    file_path: str
    status: ProcessingStatus
    chunks_created: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class LangChainIntegrationService(QObject if PYQT_AVAILABLE else object):
    """
    Integration service connecting LangChain RAG with Ghostman UI.
    
    Features:
    - File upload and processing
    - Conversation-aware querying
    - Real-time streaming responses
    - Progress tracking and status updates
    """
    
    # Qt signals for UI updates
    if PYQT_AVAILABLE:
        file_processing_started = pyqtSignal(str, str)  # file_id, filename
        file_processing_progress = pyqtSignal(str, float)  # file_id, progress
        file_processing_completed = pyqtSignal(str, dict)  # file_id, result
        file_processing_failed = pyqtSignal(str, str)  # file_id, error
        
        response_streaming = pyqtSignal(str)  # token
        response_completed = pyqtSignal(str, list)  # full_response, sources
        
        context_updated = pyqtSignal(str, int)  # conversation_id, document_count
    
    def __init__(
        self,
        conversation_service: ConversationService,
        persist_directory: str = "./faiss_langchain_db",
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4",
        embedding_model: str = "text-embedding-3-large"
    ):
        """
        Initialize the integration service.
        
        Args:
            conversation_service: Ghostman conversation service
            persist_directory: Directory for Chroma persistence
            openai_api_key: OpenAI API key
            model_name: OpenAI model name
            embedding_model: Embedding model name
        """
        if PYQT_AVAILABLE:
            super().__init__()
        
        self.conversation_service = conversation_service
        
        # Initialize Unified Session LangChain RAG pipeline
        self.rag_pipeline = UnifiedSessionLangChainRAGPipeline(
            persist_directory=persist_directory,
            model_name=model_name,
            embedding_model=embedding_model
        )
        
        # Processing queue and thread
        self.processing_queue = queue.Queue()
        self.processing_thread = None
        self.stop_processing = False
        
        # Track documents per conversation
        self.conversation_documents: Dict[str, List[str]] = {}
        
        # Current active conversation
        self._current_conversation_id = None
        
        # Response streaming buffer
        self._streaming_buffer = ""
        
        logger.info("LangChain Integration Service initialized")
    
    def start(self):
        """Start the background processing thread."""
        if not self.processing_thread:
            self.stop_processing = False
            self.processing_thread = threading.Thread(
                target=self._process_queue,
                daemon=True
            )
            self.processing_thread.start()
            logger.info("Processing thread started")
    
    def stop(self):
        """Stop the background processing thread."""
        self.stop_processing = True
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
            self.processing_thread = None
            logger.info("Processing thread stopped")
    
    def set_current_conversation(self, conversation_id: str):
        """Set the current active conversation."""
        self._current_conversation_id = conversation_id
        logger.debug(f"Current conversation set to: {conversation_id}")
    
    def upload_files(
        self,
        file_paths: List[str],
        conversation_id: Optional[str] = None
    ) -> List[str]:
        """
        Upload files for processing.
        
        Args:
            file_paths: List of file paths to upload
            conversation_id: Optional conversation ID (uses current if not provided)
            
        Returns:
            List of file IDs
        """
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id:
            logger.error("No conversation ID provided or set")
            return []
        
        file_ids = []
        
        for file_path in file_paths:
            # Generate file ID
            path = Path(file_path)
            file_id = f"file_{conv_id}_{path.stem}_{datetime.now().timestamp()}"
            
            # Add to processing queue
            task = {
                'file_id': file_id,
                'file_path': file_path,
                'conversation_id': conv_id
            }
            self.processing_queue.put(task)
            
            file_ids.append(file_id)
            
            # Emit signal
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_started'):
                self.file_processing_started.emit(file_id, path.name)
        
        logger.info(f"Queued {len(file_ids)} files for processing")
        return file_ids
    
    def _process_queue(self):
        """Background thread to process file uploads."""
        while not self.stop_processing:
            try:
                # Get task from queue (timeout to check stop flag)
                task = self.processing_queue.get(timeout=1)
                
                # Process the file
                self._process_file(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
    
    def _process_file(self, task: Dict[str, Any]):
        """Process a single file."""
        file_id = task['file_id']
        file_path = task['file_path']
        conversation_id = task['conversation_id']
        
        start_time = datetime.now()
        
        try:
            # Emit progress
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_progress'):
                self.file_processing_progress.emit(file_id, 0.3)
            
            # Add document to RAG pipeline
            doc_ids = self.rag_pipeline.add_documents(
                file_paths=[file_path],
                conversation_id=conversation_id
            )
            
            # Track documents for conversation
            if conversation_id not in self.conversation_documents:
                self.conversation_documents[conversation_id] = []
            self.conversation_documents[conversation_id].extend(doc_ids)
            
            # Emit progress
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_progress'):
                self.file_processing_progress.emit(file_id, 0.8)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = DocumentProcessingResult(
                file_id=file_id,
                file_path=file_path,
                status=ProcessingStatus.COMPLETED,
                chunks_created=len(doc_ids),
                processing_time=processing_time,
                metadata={'document_ids': doc_ids}
            )
            
            # Emit completion
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_completed'):
                self.file_processing_completed.emit(
                    file_id,
                    {
                        'status': 'completed',
                        'chunks': len(doc_ids),
                        'time': processing_time
                    }
                )
            
            # Update context
            if PYQT_AVAILABLE and hasattr(self, 'context_updated'):
                doc_count = len(self.conversation_documents.get(conversation_id, []))
                self.context_updated.emit(conversation_id, doc_count)
            
            # Add system message to conversation
            asyncio.run(self._add_system_message(
                conversation_id,
                f"📎 Document added: {Path(file_path).name} ({len(doc_ids)} chunks)"
            ))
            
            logger.info(f"File processed: {file_id} - {len(doc_ids)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to process file {file_id}: {e}")
            
            # Emit failure
            if PYQT_AVAILABLE and hasattr(self, 'file_processing_failed'):
                self.file_processing_failed.emit(file_id, str(e))
    
    async def _add_system_message(self, conversation_id: str, message: str):
        """Add a system message to the conversation."""
        try:
            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM,
                content=message,
                metadata={'type': 'document_notification'}
            )
        except Exception as e:
            logger.error(f"Failed to add system message: {e}")
    
    def query_with_streaming(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        streaming_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system with streaming response.
        
        Args:
            question: User question
            conversation_id: Optional conversation ID
            streaming_callback: Callback for streaming tokens
            
        Returns:
            Query response with sources
        """
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id:
            logger.error("No conversation ID for query")
            return {"answer": "No active conversation", "source_documents": []}
        
        # Reset streaming buffer
        self._streaming_buffer = ""
        
        # Define streaming handler
        def stream_handler(token: str):
            self._streaming_buffer += token
            
            # Emit streaming signal
            if PYQT_AVAILABLE and hasattr(self, 'response_streaming'):
                self.response_streaming.emit(token)
            
            # Call custom callback
            if streaming_callback:
                streaming_callback(token)
        
        # Execute query using unified session
        response = self.rag_pipeline.query_with_unified_session(
            conversation_id=conv_id,
            question=question,
            streaming_callback=stream_handler
        )
        
        # Emit completion signal
        if PYQT_AVAILABLE and hasattr(self, 'response_completed'):
            sources = [
                {
                    'content': doc.page_content[:200],
                    'metadata': doc.metadata
                }
                for doc in response.get('source_documents', [])[:3]
            ]
            self.response_completed.emit(response['answer'], sources)
        
        return response
    
    def query(
        self,
        question: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system (non-streaming).
        
        Args:
            question: User question
            conversation_id: Optional conversation ID
            
        Returns:
            Query response with sources
        """
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id:
            logger.error("No conversation ID for query")
            return {"answer": "No active conversation", "source_documents": []}
        
        return self.rag_pipeline.query_with_unified_session(
            conversation_id=conv_id,
            question=question
        )
    
    def remove_document(self, file_id: str, conversation_id: Optional[str] = None) -> bool:
        """
        Remove a specific document from the RAG pipeline.
        
        Args:
            file_id: The file ID to remove
            conversation_id: Optional conversation ID to update tracking
            
        Returns:
            True if removal was successful
        """
        try:
            # Try to remove by file_id metadata first
            removed_ids = self.rag_pipeline.remove_documents_by_metadata({"file_id": file_id})
            
            if not removed_ids:
                # Try alternative metadata patterns
                removed_ids = self.rag_pipeline.remove_documents_by_metadata({"source": file_id})
            
            if not removed_ids:
                # Try filename-based removal
                removed_ids = self.rag_pipeline.remove_documents_by_metadata({"filename": file_id})
            
            # Update conversation document tracking
            conv_id = conversation_id or self._current_conversation_id
            if conv_id and conv_id in self.conversation_documents:
                # Remove any document IDs that match this file
                original_count = len(self.conversation_documents[conv_id])
                self.conversation_documents[conv_id] = [
                    doc_id for doc_id in self.conversation_documents[conv_id] 
                    if doc_id not in removed_ids
                ]
                new_count = len(self.conversation_documents[conv_id])
                logger.info(f"Updated document tracking: {original_count} -> {new_count}")
            
            if removed_ids:
                logger.info(f"Successfully removed document {file_id} ({len(removed_ids)} chunks)")
                return True
            else:
                logger.warning(f"No documents found for file_id: {file_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove document {file_id}: {e}")
            return False
    
    def clear_conversation_context(self, conversation_id: str):
        """Clear the context for a conversation."""
        # Clear from RAG pipeline
        if hasattr(self.rag_pipeline, 'conversation_memories') and conversation_id in self.rag_pipeline.conversation_memories:
            del self.rag_pipeline.conversation_memories[conversation_id]
        
        # Clear document tracking
        if conversation_id in self.conversation_documents:
            del self.conversation_documents[conversation_id]
        
        logger.info(f"Cleared context for conversation {conversation_id}")
    
    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation."""
        doc_count = len(self.conversation_documents.get(conversation_id, []))
        
        return {
            'conversation_id': conversation_id,
            'document_count': doc_count,
            'has_memory': hasattr(self.rag_pipeline, 'conversation_memories') and conversation_id in self.rag_pipeline.conversation_memories
        }
    
    def get_similar_documents(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Get similar documents for a query."""
        # Use vector store for similarity search
        docs = self.rag_pipeline.vector_store.similarity_search(query, k=k)
        
        return [
            {
                'content': doc.page_content,
                'metadata': doc.metadata,
                'relevance': 1.0  # Similarity score would go here if available
            }
            for doc in docs
        ]