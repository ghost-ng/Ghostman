"""
Enhanced REPL Widget with RAG Integration

Extension module that adds RAG capabilities to the existing REPL widget.
This is designed to be imported and applied to enhance the existing widget.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from ...infrastructure.rag.integration.repl_rag_integration import REPLRAGIntegration
from ...infrastructure.conversation_management.services.conversation_service import ConversationService

logger = logging.getLogger("specter.repl_rag_enhanced")


class REPLRAGEnhancement:
    """
    Enhancement mixin for REPL widget to add RAG capabilities.
    
    This class provides methods that can be mixed into the existing
    REPL widget to add RAG functionality without modifying the original code.
    """
    
    def __init__(self):
        """Initialize RAG enhancement."""
        self.rag_integration = None
        self._rag_enabled = True
        self._rag_initialized = False
        self._async_loop = None
        
        # Create async event loop for RAG operations
        self._init_async_loop()
    
    def _init_async_loop(self):
        """Initialize async event loop for background tasks."""
        try:
            self._async_loop = asyncio.new_event_loop()
            
            # Run loop in thread
            import threading
            def run_loop():
                asyncio.set_event_loop(self._async_loop)
                self._async_loop.run_forever()
            
            self._loop_thread = threading.Thread(target=run_loop, daemon=True)
            self._loop_thread.start()
            
            logger.debug("Async loop initialized for RAG operations")
            
        except Exception as e:
            logger.error(f"Failed to initialize async loop: {e}")
            self._async_loop = None
    
    def initialize_rag(self, conversation_service: ConversationService):
        """
        Initialize RAG integration.
        
        Args:
            conversation_service: The conversation service instance
        """
        if self._rag_initialized:
            return
        
        try:
            # Create RAG integration
            self.rag_integration = REPLRAGIntegration(conversation_service)
            self.rag_integration.set_event_loop(self._async_loop)
            
            # Initialize in async loop
            if self._async_loop:
                future = asyncio.run_coroutine_threadsafe(
                    self.rag_integration.initialize(),
                    self._async_loop
                )
                
                # Wait for initialization (with timeout)
                try:
                    result = future.result(timeout=10)
                    if result:
                        self._rag_initialized = True
                        logger.info("RAG integration initialized successfully")
                    else:
                        logger.error("RAG initialization returned False")
                except TimeoutError:
                    logger.error("RAG initialization timed out")
            
            # Connect RAG signals to UI updates
            self._connect_rag_signals()
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
            self._rag_enabled = False
    
    def _connect_rag_signals(self):
        """Connect RAG integration signals to UI handlers."""
        if not self.rag_integration:
            return
        
        try:
            # Connect file status updates to file browser bar
            if hasattr(self, 'file_browser_bar'):
                self.rag_integration.file_status_updated.connect(
                    self._on_rag_file_status_update
                )
            
            # Connect RAG response ready signal
            self.rag_integration.rag_response_ready.connect(
                self._on_rag_response_ready
            )
            
            # Connect context updates
            self.rag_integration.context_updated.connect(
                self._on_rag_context_updated
            )
            
            logger.debug("RAG signals connected")
            
        except Exception as e:
            logger.error(f"Failed to connect RAG signals: {e}")
    
    def _on_rag_file_status_update(self, file_id: str, status: str, progress: float):
        """Handle RAG file status update."""
        try:
            if hasattr(self, 'file_browser_bar'):
                self.file_browser_bar.update_file_status(file_id, status, progress)
                
                # Update token usage if completed
                if status == "completed" and self.rag_integration:
                    result = self.rag_integration.file_upload_service.get_processing_status(file_id)
                    if result:
                        self.file_browser_bar.update_file_usage(
                            file_id,
                            result.tokens_used,
                            0.8  # Default relevance score
                        )
            
        except Exception as e:
            logger.error(f"Failed to update file status: {e}")
    
    def _on_rag_response_ready(self, response: str, metadata: Dict[str, Any]):
        """Handle RAG response ready signal."""
        try:
            # Add context indicator to response
            if metadata.get('documents_used'):
                doc_count = len(metadata['documents_used'])
                context_note = f"\n\n📎 *Using {doc_count} document(s) for context*"
                
                # Append to current message if displaying
                if hasattr(self, 'output_display'):
                    cursor = self.output_display.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.insertText(context_note)
            
        except Exception as e:
            logger.error(f"Failed to handle RAG response: {e}")
    
    def _on_rag_context_updated(self, conversation_id: str, document_ids: List[str]):
        """Handle RAG context update."""
        try:
            logger.info(f"Context updated for conversation {conversation_id}: {len(document_ids)} documents")
            
            # Update UI to show document count
            if hasattr(self, 'file_browser_bar') and document_ids:
                # This could update a status label or badge
                pass
            
        except Exception as e:
            logger.error(f"Failed to handle context update: {e}")
    
    def enhance_file_upload(self, original_method):
        """
        Enhance the file upload method with RAG processing.
        
        Args:
            original_method: The original _process_uploaded_files method
            
        Returns:
            Enhanced method
        """
        def enhanced_method(file_paths):
            # Call original method first
            original_method(file_paths)
            
            # Process through RAG if enabled
            if self._rag_enabled and self.rag_integration and self._async_loop:
                # Get current conversation ID
                conv_id = None
                if hasattr(self, 'current_conversation_id'):
                    conv_id = self.current_conversation_id
                elif hasattr(self, 'conversation_manager'):
                    conv = self.conversation_manager.get_active_conversation()
                    if conv:
                        conv_id = conv.id
                
                if conv_id:
                    # Set current conversation in RAG
                    self.rag_integration.set_current_conversation(conv_id)
                    
                    # Process files asynchronously
                    asyncio.run_coroutine_threadsafe(
                        self.rag_integration.process_uploaded_files(file_paths),
                        self._async_loop
                    )
                else:
                    logger.warning("No active conversation for RAG file processing")
        
        return enhanced_method
    
    def enhance_message_sending(self, original_method):
        """
        Enhance the message sending method with RAG context.
        
        Args:
            original_method: The original send_message method
            
        Returns:
            Enhanced method
        """
        def enhanced_method(*args, **kwargs):
            # Extract message from args
            message = args[0] if args else kwargs.get('message', '')
            
            # Enhance with RAG if enabled
            if self._rag_enabled and self.rag_integration and message:
                # Get current conversation ID
                conv_id = None
                if hasattr(self, 'current_conversation_id'):
                    conv_id = self.current_conversation_id
                elif hasattr(self, 'conversation_manager'):
                    conv = self.conversation_manager.get_active_conversation()
                    if conv:
                        conv_id = conv.id
                
                if conv_id and self._async_loop:
                    # Enhance message asynchronously
                    future = asyncio.run_coroutine_threadsafe(
                        self.rag_integration.enhance_user_message(message, conv_id),
                        self._async_loop
                    )
                    
                    try:
                        # Get enhanced data (with short timeout)
                        enhanced_data = future.result(timeout=2)
                        
                        if enhanced_data.get('enhanced') and enhanced_data.get('context'):
                            # Add context indicator
                            logger.info(f"Message enhanced with RAG context: {len(enhanced_data.get('sources', []))} sources")
                    except Exception as e:
                        logger.debug(f"RAG enhancement skipped: {e}")
            
            # Call original method
            return original_method(*args, **kwargs)
        
        return enhanced_method
    
    def toggle_rag(self, enabled: bool):
        """Toggle RAG functionality."""
        self._rag_enabled = enabled
        logger.info(f"RAG {'enabled' if enabled else 'disabled'}")
    
    def cleanup_rag(self):
        """Cleanup RAG resources."""
        if self.rag_integration and self._async_loop:
            # Cleanup in async loop
            asyncio.run_coroutine_threadsafe(
                self.rag_integration.cleanup(),
                self._async_loop
            )
        
        # Stop async loop
        if self._async_loop:
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
            if hasattr(self, '_loop_thread'):
                self._loop_thread.join(timeout=2)
        
        logger.info("RAG enhancement cleaned up")


def apply_rag_enhancement(repl_widget, conversation_service: ConversationService):
    """
    Apply RAG enhancement to an existing REPL widget.
    
    Args:
        repl_widget: The REPL widget instance to enhance
        conversation_service: The conversation service instance
    """
    try:
        # Create enhancement instance
        enhancement = REPLRAGEnhancement()
        
        # Add enhancement methods to widget
        repl_widget._rag_enhancement = enhancement
        repl_widget.initialize_rag = lambda: enhancement.initialize_rag(conversation_service)
        repl_widget.toggle_rag = enhancement.toggle_rag
        repl_widget.cleanup_rag = enhancement.cleanup_rag
        
        # Enhance existing methods
        if hasattr(repl_widget, '_process_uploaded_files'):
            original_upload = repl_widget._process_uploaded_files
            repl_widget._process_uploaded_files = enhancement.enhance_file_upload(original_upload)
        
        # Initialize RAG
        enhancement.initialize_rag(conversation_service)
        
        # Connect to file browser bar if available
        if hasattr(repl_widget, 'file_browser_bar'):
            enhancement.rag_integration.connect_to_file_browser_bar(repl_widget.file_browser_bar)
        
        logger.info("RAG enhancement applied to REPL widget")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply RAG enhancement: {e}")
        return False