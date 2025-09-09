"""
REPL-RAG Integration Module

Integrates the RAG pipeline with the REPL widget for seamless
file upload, context management, and conversational retrieval.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from ..conversation.conversation_rag_pipeline import ConversationRAGPipeline
from ..integration.file_upload_service import FileUploadService, ProcessingStatus
from ...conversation_management.services.conversation_service import ConversationService
from ...conversation_management.models.enums import MessageRole
from ...rag_pipeline.pipeline.rag_pipeline import get_rag_pipeline

logger = logging.getLogger("ghostman.repl_rag_integration")


class REPLRAGIntegration(QObject):
    """
    Integration layer between REPL widget and RAG pipeline.
    
    Handles:
    - File upload from REPL UI
    - Message enhancement with RAG context
    - Status updates to file browser bar
    - Conversation context management
    """
    
    # Signals for UI updates
    rag_response_ready = pyqtSignal(str, dict)  # response, metadata
    file_status_updated = pyqtSignal(str, str, float)  # file_id, status, progress
    context_updated = pyqtSignal(str, list)  # conversation_id, document_ids
    
    def __init__(self, conversation_service: ConversationService):
        """Initialize REPL-RAG integration."""
        super().__init__()
        
        self.conversation_service = conversation_service
        self.rag_pipeline = None
        self.conversation_rag = None
        self.file_upload_service = None
        
        # Current conversation tracking
        self._current_conversation_id = None
        
        # File tracking for UI updates
        self._file_ui_mapping = {}  # file_id -> UI element mapping
        
        # Async event loop for background tasks
        self._loop = None
        
        logger.info("REPLRAGIntegration initialized")
    
    async def initialize(self):
        """Initialize RAG components."""
        try:
            logger.info("Initializing RAG components...")
            
            # Get or create RAG pipeline
            self.rag_pipeline = get_rag_pipeline()
            
            # Create conversation-aware RAG pipeline
            self.conversation_rag = ConversationRAGPipeline(
                rag_pipeline=self.rag_pipeline,
                conversation_service=self.conversation_service
            )
            
            # Create file upload service
            self.file_upload_service = FileUploadService(
                conversation_rag_pipeline=self.conversation_rag
            )
            
            # Connect file upload service signals
            if hasattr(self.file_upload_service, 'file_processing_started'):
                self.file_upload_service.file_processing_started.connect(
                    self._on_file_processing_started
                )
                self.file_upload_service.file_processing_progress.connect(
                    self._on_file_processing_progress
                )
                self.file_upload_service.file_processing_completed.connect(
                    self._on_file_processing_completed
                )
                self.file_upload_service.file_processing_failed.connect(
                    self._on_file_processing_failed
                )
            
            # Start file upload service
            await self.file_upload_service.start()
            
            logger.info("RAG components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            return False
    
    def set_current_conversation(self, conversation_id: str):
        """Set the current active conversation."""
        self._current_conversation_id = conversation_id
        logger.debug(f"Current conversation set to: {conversation_id}")
    
    async def process_uploaded_files(
        self,
        file_paths: List[str],
        conversation_id: Optional[str] = None
    ) -> List[str]:
        """
        Process uploaded files for the current conversation.
        
        Args:
            file_paths: List of file paths to process
            conversation_id: Optional conversation ID (uses current if not provided)
            
        Returns:
            List of file IDs
        """
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id:
            logger.error("No conversation ID provided or set")
            return []
        
        try:
            # Upload files through the service
            file_ids = await self.file_upload_service.upload_files(
                conversation_id=conv_id,
                file_paths=file_paths,
                immediate_processing=True
            )
            
            logger.info(f"Uploaded {len(file_ids)} files to conversation {conv_id}")
            
            # Update context signal
            docs = self.conversation_rag.get_conversation_documents(conv_id)
            doc_ids = [doc['id'] for doc in docs]
            self.context_updated.emit(conv_id, doc_ids)
            
            return file_ids
            
        except Exception as e:
            logger.error(f"Failed to process uploaded files: {e}")
            return []
    
    async def enhance_user_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        Enhance user message with RAG context.
        
        Args:
            message: User message
            conversation_id: Optional conversation ID
            use_rag: Whether to use RAG enhancement
            
        Returns:
            Enhanced message data with context
        """
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id or not use_rag or not self.conversation_rag:
            return {'message': message, 'enhanced': False}
        
        try:
            # Check if conversation has documents
            docs = self.conversation_rag.get_conversation_documents(conv_id)
            if not docs:
                return {'message': message, 'enhanced': False}
            
            # Query RAG pipeline with conversation context
            response = await self.conversation_rag.query_with_conversation_context(
                conversation_id=conv_id,
                query=message,
                use_history=True,
                use_documents=True,
                rewrite_query=True
            )
            
            # Build enhanced response
            enhanced_data = {
                'message': message,
                'enhanced': True,
                'context': response.context_used,
                'sources': [
                    {
                        'content': source.content[:200],
                        'metadata': source.metadata
                    }
                    for source in response.sources[:3]  # Top 3 sources
                ],
                'suggested_response': response.answer,
                'metadata': response.metadata
            }
            
            # Emit signal for UI update
            self.rag_response_ready.emit(response.answer, response.metadata)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Failed to enhance message with RAG: {e}")
            return {'message': message, 'enhanced': False, 'error': str(e)}
    
    async def remove_document(
        self,
        document_id: str,
        conversation_id: Optional[str] = None
    ) -> bool:
        """Remove a document from conversation context."""
        conv_id = conversation_id or self._current_conversation_id
        if not conv_id:
            return False
        
        try:
            success = await self.conversation_rag.remove_document_from_conversation(
                conversation_id=conv_id,
                document_id=document_id
            )
            
            if success:
                # Update context signal
                docs = self.conversation_rag.get_conversation_documents(conv_id)
                doc_ids = [doc['id'] for doc in docs]
                self.context_updated.emit(conv_id, doc_ids)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove document: {e}")
            return False
    
    def _on_file_processing_started(self, file_id: str, filename: str):
        """Handle file processing started signal."""
        logger.debug(f"File processing started: {file_id} - {filename}")
        self.file_status_updated.emit(file_id, "processing", 0.0)
    
    def _on_file_processing_progress(self, file_id: str, progress: float):
        """Handle file processing progress signal."""
        logger.debug(f"File processing progress: {file_id} - {progress:.1%}")
        self.file_status_updated.emit(file_id, "processing", progress)
    
    def _on_file_processing_completed(self, file_id: str, result: Dict[str, Any]):
        """Handle file processing completed signal."""
        logger.info(f"File processing completed: {file_id}")
        self.file_status_updated.emit(file_id, "completed", 1.0)
    
    def _on_file_processing_failed(self, file_id: str, error: str):
        """Handle file processing failed signal."""
        logger.error(f"File processing failed: {file_id} - {error}")
        self.file_status_updated.emit(file_id, "failed", 0.0)
    
    def connect_to_repl_widget(self, repl_widget):
        """
        Connect integration to REPL widget.
        
        Args:
            repl_widget: The REPL widget instance
        """
        try:
            # Connect to file upload signals
            if hasattr(repl_widget, '_process_uploaded_files'):
                # Monkey-patch the upload handler
                original_handler = repl_widget._process_uploaded_files
                
                def enhanced_handler(file_paths):
                    # Call original handler
                    original_handler(file_paths)
                    
                    # Process through RAG pipeline
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(
                            self.process_uploaded_files(file_paths),
                            self._loop
                        )
                
                repl_widget._process_uploaded_files = enhanced_handler
            
            # Connect to file browser bar if available
            if hasattr(repl_widget, 'file_browser_bar'):
                bar = repl_widget.file_browser_bar
                
                # Connect our status updates to the bar
                self.file_status_updated.connect(
                    lambda fid, status, progress: bar.update_file_status(fid, status, progress)
                )
            
            logger.info("Connected to REPL widget")
            
        except Exception as e:
            logger.error(f"Failed to connect to REPL widget: {e}")
    
    def connect_to_file_browser_bar(self, file_browser_bar):
        """
        Connect integration to file browser bar.
        
        Args:
            file_browser_bar: The file browser bar widget
        """
        try:
            # Connect status updates
            self.file_status_updated.connect(
                lambda fid, status, progress: file_browser_bar.update_file_status(fid, status, progress)
            )
            
            # Connect file removal
            file_browser_bar.file_removed.connect(
                lambda fid: asyncio.run_coroutine_threadsafe(
                    self.remove_document(fid),
                    self._loop
                ) if self._loop else None
            )
            
            logger.info("Connected to file browser bar")
            
        except Exception as e:
            logger.error(f"Failed to connect to file browser bar: {e}")
    
    def set_event_loop(self, loop):
        """Set the async event loop for background tasks."""
        self._loop = loop
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.file_upload_service:
            await self.file_upload_service.stop()
        
        logger.info("REPLRAGIntegration cleaned up")