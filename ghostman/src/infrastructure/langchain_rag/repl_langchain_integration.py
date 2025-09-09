"""
REPL Widget Integration with LangChain RAG

Connects the REPL widget with the LangChain RAG pipeline for
seamless file upload and conversational retrieval.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .langchain_integration_service import LangChainIntegrationService
from ..conversation_management.services.conversation_service import ConversationService
from ..conversation_management.models.enums import MessageRole

logger = logging.getLogger("ghostman.repl_langchain")


class REPLLangChainIntegration(QObject):
    """
    Integration layer for REPL widget with LangChain RAG.
    
    This class handles:
    - File uploads from REPL UI
    - Message enhancement with RAG context
    - Streaming responses
    - Status updates to file browser bar
    """
    
    # Signals for UI updates
    rag_response_ready = pyqtSignal(str, dict)  # response, metadata
    rag_streaming_token = pyqtSignal(str)  # streaming token
    file_status_changed = pyqtSignal(str, str, float)  # file_id, status, progress
    context_info_updated = pyqtSignal(int, int)  # doc_count, chunk_count
    
    def __init__(
        self,
        conversation_service: ConversationService,
        persist_directory: str = "./faiss_langchain_db",
        openai_api_key: Optional[str] = None
    ):
        """Initialize REPL-LangChain integration."""
        super().__init__()
        
        self.conversation_service = conversation_service
        
        # Initialize LangChain integration service
        self.langchain_service = LangChainIntegrationService(
            conversation_service=conversation_service,
            persist_directory=persist_directory,
            openai_api_key=openai_api_key
        )
        
        # Connect LangChain service signals
        self._connect_langchain_signals()
        
        # Current conversation tracking
        self._current_conversation_id = None
        
        # File tracking for UI
        self._active_files: Dict[str, Dict[str, Any]] = {}
        
        # Start the service
        self.langchain_service.start()
        
        logger.info("REPL-LangChain integration initialized")
    
    def _connect_langchain_signals(self):
        """Connect LangChain service signals to local handlers."""
        if hasattr(self.langchain_service, 'file_processing_started'):
            self.langchain_service.file_processing_started.connect(
                self._on_file_processing_started
            )
            self.langchain_service.file_processing_progress.connect(
                self._on_file_processing_progress
            )
            self.langchain_service.file_processing_completed.connect(
                self._on_file_processing_completed
            )
            self.langchain_service.file_processing_failed.connect(
                self._on_file_processing_failed
            )
            
            self.langchain_service.response_streaming.connect(
                self._on_response_streaming
            )
            self.langchain_service.response_completed.connect(
                self._on_response_completed
            )
            self.langchain_service.context_updated.connect(
                self._on_context_updated
            )
    
    def set_current_conversation(self, conversation_id: str):
        """Set the current active conversation."""
        self._current_conversation_id = conversation_id
        self.langchain_service.set_current_conversation(conversation_id)
        logger.debug(f"Current conversation set to: {conversation_id}")
    
    def process_uploaded_files(self, file_paths: List[str]) -> List[str]:
        """
        Process uploaded files through LangChain.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of file IDs
        """
        if not self._current_conversation_id:
            logger.error("No current conversation set")
            return []
        
        # Track files
        file_ids = self.langchain_service.upload_files(
            file_paths=file_paths,
            conversation_id=self._current_conversation_id
        )
        
        # Store file info for UI tracking
        for file_id, file_path in zip(file_ids, file_paths):
            path = Path(file_path)
            self._active_files[file_id] = {
                'path': file_path,
                'name': path.name,
                'size': path.stat().st_size if path.exists() else 0,
                'status': 'queued'
            }
        
        logger.info(f"Processing {len(file_ids)} files for conversation {self._current_conversation_id}")
        return file_ids
    
    def enhance_message_with_rag(
        self,
        message: str,
        use_streaming: bool = True
    ) -> Dict[str, Any]:
        """
        Enhance a user message with RAG context.
        
        Args:
            message: User message
            use_streaming: Whether to use streaming response
            
        Returns:
            Enhanced message data
        """
        if not self._current_conversation_id:
            logger.warning("No current conversation for RAG enhancement")
            return {'message': message, 'enhanced': False}
        
        try:
            if use_streaming:
                # Query with streaming
                response = self.langchain_service.query_with_streaming(
                    question=message,
                    conversation_id=self._current_conversation_id,
                    streaming_callback=self._handle_streaming_token
                )
            else:
                # Regular query
                response = self.langchain_service.query(
                    question=message,
                    conversation_id=self._current_conversation_id
                )
            
            # Extract sources
            sources = []
            for doc in response.get('source_documents', [])[:3]:
                sources.append({
                    'content': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content,
                    'metadata': doc.metadata
                })
            
            return {
                'message': message,
                'enhanced': True,
                'answer': response.get('answer', ''),
                'sources': sources,
                'has_context': len(sources) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance message with RAG: {e}")
            return {'message': message, 'enhanced': False, 'error': str(e)}
    
    def _handle_streaming_token(self, token: str):
        """Handle streaming token from LangChain."""
        self.rag_streaming_token.emit(token)
    
    def _on_file_processing_started(self, file_id: str, filename: str):
        """Handle file processing started."""
        logger.debug(f"File processing started: {file_id}")
        
        if file_id in self._active_files:
            self._active_files[file_id]['status'] = 'processing'
        
        self.file_status_changed.emit(file_id, "processing", 0.0)
    
    def _on_file_processing_progress(self, file_id: str, progress: float):
        """Handle file processing progress."""
        self.file_status_changed.emit(file_id, "processing", progress)
    
    def _on_file_processing_completed(self, file_id: str, result: Dict):
        """Handle file processing completed."""
        logger.info(f"File processing completed: {file_id}")
        
        if file_id in self._active_files:
            self._active_files[file_id]['status'] = 'completed'
            self._active_files[file_id]['chunks'] = result.get('chunks', 0)
        
        self.file_status_changed.emit(file_id, "completed", 1.0)
    
    def _on_file_processing_failed(self, file_id: str, error: str):
        """Handle file processing failed."""
        logger.error(f"File processing failed: {file_id} - {error}")
        
        if file_id in self._active_files:
            self._active_files[file_id]['status'] = 'failed'
            self._active_files[file_id]['error'] = error
        
        self.file_status_changed.emit(file_id, "failed", 0.0)
    
    def _on_response_streaming(self, token: str):
        """Handle streaming response token."""
        # Re-emit for UI
        self.rag_streaming_token.emit(token)
    
    def _on_response_completed(self, answer: str, sources: List):
        """Handle response completion."""
        metadata = {
            'sources_count': len(sources),
            'has_context': len(sources) > 0
        }
        self.rag_response_ready.emit(answer, metadata)
    
    def _on_context_updated(self, conversation_id: str, doc_count: int):
        """Handle context update."""
        # Get more detailed stats
        stats = self.langchain_service.rag_pipeline.get_collection_stats()
        chunk_count = stats.get('count', 0)
        
        self.context_info_updated.emit(doc_count, chunk_count)
    
    def connect_to_repl_widget(self, repl_widget):
        """
        Connect this integration to a REPL widget.
        
        Args:
            repl_widget: The REPL widget instance
        """
        try:
            # Store reference
            self.repl_widget = repl_widget
            
            # Monkey-patch file upload handler
            if hasattr(repl_widget, '_process_uploaded_files'):
                original_handler = repl_widget._process_uploaded_files
                
                def enhanced_handler(file_paths):
                    # Call original handler
                    original_handler(file_paths)
                    
                    # Process through LangChain
                    self.process_uploaded_files(file_paths)
                
                repl_widget._process_uploaded_files = enhanced_handler
            
            # Connect to file browser bar if available
            if hasattr(repl_widget, 'file_browser_bar'):
                self.file_status_changed.connect(
                    lambda fid, status, progress: 
                    repl_widget.file_browser_bar.update_file_status(fid, status, progress)
                )
            
            # Add RAG enhancement to message sending
            if hasattr(repl_widget, '_send_message'):
                original_send = repl_widget._send_message
                
                def enhanced_send(message):
                    # Enhance with RAG if documents are loaded
                    if self._current_conversation_id:
                        stats = self.langchain_service.get_conversation_stats(
                            self._current_conversation_id
                        )
                        if stats.get('document_count', 0) > 0:
                            # Add context indicator
                            logger.info(f"Enhancing message with {stats['document_count']} documents")
                    
                    # Call original send
                    return original_send(message)
                
                repl_widget._send_message = enhanced_send
            
            logger.info("Connected to REPL widget")
            
        except Exception as e:
            logger.error(f"Failed to connect to REPL widget: {e}")
    
    def connect_to_file_browser_bar(self, file_browser_bar):
        """
        Connect to file browser bar for status updates.
        
        Args:
            file_browser_bar: The file browser bar widget
        """
        try:
            # Connect status updates
            self.file_status_changed.connect(
                lambda fid, status, progress:
                file_browser_bar.update_file_status(fid, status, progress)
            )
            
            # Update file usage info when processing completes
            def update_usage(file_id, status, progress):
                if status == "completed" and file_id in self._active_files:
                    file_info = self._active_files[file_id]
                    chunks = file_info.get('chunks', 0)
                    # Estimate tokens (rough approximation)
                    tokens = chunks * 200  # Assume ~200 tokens per chunk
                    file_browser_bar.update_file_usage(file_id, tokens, 0.9)
            
            self.file_status_changed.connect(update_usage)
            
            logger.info("Connected to file browser bar")
            
        except Exception as e:
            logger.error(f"Failed to connect to file browser bar: {e}")
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        if not self._current_conversation_id:
            return {'has_context': False}
        
        stats = self.langchain_service.get_conversation_stats(self._current_conversation_id)
        collection_stats = self.langchain_service.rag_pipeline.get_collection_stats()
        
        return {
            'has_context': True,
            'conversation_id': self._current_conversation_id,
            'document_count': stats.get('document_count', 0),
            'total_chunks': collection_stats.get('count', 0),
            'active_files': len(self._active_files),
            'files': list(self._active_files.values())
        }
    
    def clear_current_context(self):
        """Clear context for current conversation."""
        if self._current_conversation_id:
            self.langchain_service.clear_conversation_context(self._current_conversation_id)
            self._active_files.clear()
            logger.info(f"Cleared context for conversation {self._current_conversation_id}")
    
    def cleanup(self):
        """Cleanup resources."""
        self.langchain_service.stop()
        logger.info("REPL-LangChain integration cleaned up")