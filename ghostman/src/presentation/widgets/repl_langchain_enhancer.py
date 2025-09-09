"""
REPL Widget LangChain Enhancer

Enhances the existing REPL widget with LangChain RAG capabilities.
This module provides a non-invasive enhancement that can be applied to existing widgets.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ...infrastructure.langchain_rag.repl_langchain_integration import REPLLangChainIntegration
from ...infrastructure.conversation_management.services.conversation_service import ConversationService

logger = logging.getLogger("ghostman.repl_langchain_enhancer")


class REPLLangChainEnhancer(QObject):
    """
    Enhancer that adds LangChain RAG capabilities to existing REPL widget.
    
    This class wraps the existing REPL widget methods to add RAG functionality
    without modifying the original widget code.
    """
    
    # Enhanced signals
    rag_enhanced_response = pyqtSignal(str, dict)  # response, metadata
    rag_file_processed = pyqtSignal(str, dict)     # file_id, processing_info
    rag_context_changed = pyqtSignal(int)          # document_count
    
    def __init__(
        self,
        repl_widget,
        conversation_service: ConversationService,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the enhancer.
        
        Args:
            repl_widget: The REPL widget to enhance
            conversation_service: Conversation management service
            openai_api_key: OpenAI API key (uses env var if not provided)
        """
        super().__init__()
        
        self.repl_widget = repl_widget
        self.conversation_service = conversation_service
        
        # Initialize LangChain integration
        self.rag_integration = None
        self._rag_enabled = bool(openai_api_key or os.getenv("OPENAI_API_KEY"))
        
        if self._rag_enabled:
            try:
                self.rag_integration = REPLLangChainIntegration(
                    conversation_service=conversation_service,
                    persist_directory=self._get_persist_directory(),
                    openai_api_key=openai_api_key
                )
                
                # Connect RAG signals
                self._connect_rag_signals()
                
                logger.info("LangChain RAG enhancer initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize RAG integration: {e}")
                self._rag_enabled = False
        else:
            logger.warning("RAG enhancer disabled - no OpenAI API key")
        
        # Store original methods
        self._original_methods = {}
        
        # Apply enhancements
        self._enhance_widget()
    
    def _get_persist_directory(self) -> str:
        """Get the directory for Chroma persistence."""
        # Use Ghostman data directory
        try:
            from ...infrastructure.storage.settings_manager import settings
            data_dir = settings.get('paths.data_dir', os.path.expanduser('~/.Ghostman'))
            return os.path.join(data_dir, 'chroma_db')
        except:
            return os.path.join(os.path.expanduser('~/.Ghostman'), 'chroma_db')
    
    def _connect_rag_signals(self):
        """Connect RAG integration signals to local handlers."""
        if not self.rag_integration:
            return
        
        # Connect file status updates
        self.rag_integration.file_status_changed.connect(
            self._on_rag_file_status_changed
        )
        
        # Connect RAG response signals
        self.rag_integration.rag_response_ready.connect(
            self._on_rag_response_ready
        )
        
        # Connect streaming tokens
        self.rag_integration.rag_streaming_token.connect(
            self._on_rag_streaming_token
        )
        
        # Connect context info
        self.rag_integration.context_info_updated.connect(
            self._on_rag_context_updated
        )
    
    def _enhance_widget(self):
        """Apply enhancements to the REPL widget."""
        if not self._rag_enabled:
            return
        
        # Enhance file upload processing
        if hasattr(self.repl_widget, '_process_uploaded_files'):
            original_method = self.repl_widget._process_uploaded_files
            self._original_methods['_process_uploaded_files'] = original_method
            
            # Replace with enhanced version
            self.repl_widget._process_uploaded_files = self._enhanced_process_uploaded_files
            logger.debug("Enhanced _process_uploaded_files method")
        
        # Connect to file browser bar if available
        if hasattr(self.repl_widget, 'file_browser_bar'):
            self.rag_integration.connect_to_file_browser_bar(
                self.repl_widget.file_browser_bar
            )
        
        # Set current conversation if available
        if hasattr(self.repl_widget, 'current_conversation_id'):
            conv_id = self.repl_widget.current_conversation_id
            if conv_id:
                self.rag_integration.set_current_conversation(conv_id)
    
    def _enhanced_process_uploaded_files(self, file_paths: List[str]):
        """Enhanced file upload processing with RAG integration."""
        
        # Call original method first
        original_method = self._original_methods.get('_process_uploaded_files')
        if original_method:
            try:
                original_method(file_paths)
                logger.debug(f"Original file processing completed for {len(file_paths)} files")
            except Exception as e:
                logger.error(f"Original file processing failed: {e}")
        
        # Process with RAG if enabled
        if self._rag_enabled and self.rag_integration:
            try:
                # Set current conversation
                conv_id = self._get_current_conversation_id()
                if conv_id:
                    self.rag_integration.set_current_conversation(conv_id)
                    
                    # Process files through RAG
                    file_ids = self.rag_integration.process_uploaded_files(file_paths)
                    logger.info(f"RAG processing initiated for {len(file_ids)} files")
                    
                else:
                    logger.warning("No active conversation for RAG processing")
                    
            except Exception as e:
                logger.error(f"RAG file processing failed: {e}")
    
    def _get_current_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID from the REPL widget."""
        
        # Try different ways to get conversation ID
        if hasattr(self.repl_widget, 'current_conversation_id'):
            return self.repl_widget.current_conversation_id
        
        if hasattr(self.repl_widget, 'conversation_manager'):
            manager = self.repl_widget.conversation_manager
            if hasattr(manager, 'get_active_conversation'):
                conv = manager.get_active_conversation()
                if conv:
                    return conv.id
        
        # Try to get from tab system
        if hasattr(self.repl_widget, 'parent') and self.repl_widget.parent():
            parent = self.repl_widget.parent()
            if hasattr(parent, 'current_conversation_id'):
                return parent.current_conversation_id
        
        return None
    
    def _on_rag_file_status_changed(self, file_id: str, status: str, progress: float):
        """Handle RAG file status changes."""
        logger.debug(f"RAG file status: {file_id} -> {status} ({progress:.1%})")
        
        # Update file browser bar
        if hasattr(self.repl_widget, 'file_browser_bar'):
            bar = self.repl_widget.file_browser_bar
            bar.update_file_status(file_id, status, progress)
            
            # Add token count estimate when completed
            if status == "completed":
                # Rough estimate: 200 tokens per chunk, 1000 char chunks
                estimated_tokens = int(progress * 1000 * 0.3)  # ~300 tokens per 1000 chars
                bar.update_file_usage(file_id, estimated_tokens, 0.85)
        
        # Emit our signal
        processing_info = {
            'status': status,
            'progress': progress,
            'timestamp': self._get_timestamp()
        }
        self.rag_file_processed.emit(file_id, processing_info)
    
    def _on_rag_response_ready(self, response: str, metadata: Dict[str, Any]):
        """Handle RAG response ready."""
        logger.info(f"RAG response ready with {metadata.get('sources_count', 0)} sources")
        
        # Add context indicator to response display
        if metadata.get('has_context'):
            context_note = f"\n\n📎 *Response enhanced with document context*"
            
            # Try to append to current output
            if hasattr(self.repl_widget, 'output_display'):
                try:
                    cursor = self.repl_widget.output_display.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.insertText(context_note)
                except Exception as e:
                    logger.debug(f"Could not append context note: {e}")
        
        self.rag_enhanced_response.emit(response, metadata)
    
    def _on_rag_streaming_token(self, token: str):
        """Handle RAG streaming token."""
        # Could be used to show real-time response streaming
        pass
    
    def _on_rag_context_updated(self, doc_count: int, chunk_count: int):
        """Handle RAG context updates."""
        logger.info(f"RAG context updated: {doc_count} documents, {chunk_count} chunks")
        self.rag_context_changed.emit(doc_count)
        
        # Update title bar or status if needed
        if hasattr(self.repl_widget, 'parent') and doc_count > 0:
            try:
                parent = self.repl_widget.parent()
                if hasattr(parent, 'setWindowTitle'):
                    current_title = parent.windowTitle()
                    if "📎" not in current_title and doc_count > 0:
                        parent.setWindowTitle(f"{current_title} 📎({doc_count})")
            except:
                pass
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def enhance_message_with_rag(self, message: str) -> Dict[str, Any]:
        """
        Enhance a user message with RAG context.
        
        Args:
            message: User message
            
        Returns:
            Enhanced message data
        """
        if not self._rag_enabled or not self.rag_integration:
            return {'message': message, 'enhanced': False}
        
        try:
            # Set current conversation
            conv_id = self._get_current_conversation_id()
            if conv_id:
                self.rag_integration.set_current_conversation(conv_id)
                
                # Enhance message
                return self.rag_integration.enhance_message_with_rag(
                    message=message,
                    use_streaming=False  # For now, disable streaming
                )
            
        except Exception as e:
            logger.error(f"Failed to enhance message with RAG: {e}")
        
        return {'message': message, 'enhanced': False}
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current RAG context."""
        if not self._rag_enabled or not self.rag_integration:
            return {'has_context': False, 'reason': 'RAG not enabled'}
        
        try:
            return self.rag_integration.get_context_summary()
        except Exception as e:
            logger.error(f"Failed to get context summary: {e}")
            return {'has_context': False, 'error': str(e)}
    
    def clear_rag_context(self):
        """Clear RAG context for current conversation."""
        if not self._rag_enabled or not self.rag_integration:
            return
        
        try:
            self.rag_integration.clear_current_context()
            logger.info("RAG context cleared")
        except Exception as e:
            logger.error(f"Failed to clear RAG context: {e}")
    
    def set_conversation(self, conversation_id: str):
        """Set the current conversation for RAG."""
        if self._rag_enabled and self.rag_integration:
            self.rag_integration.set_current_conversation(conversation_id)
            logger.debug(f"RAG conversation set to: {conversation_id}")
    
    def cleanup(self):
        """Cleanup the enhancer."""
        if self.rag_integration:
            self.rag_integration.cleanup()
        
        # Restore original methods
        for method_name, original_method in self._original_methods.items():
            if hasattr(self.repl_widget, method_name):
                setattr(self.repl_widget, method_name, original_method)
        
        logger.info("RAG enhancer cleaned up")


def enhance_repl_with_langchain(
    repl_widget,
    conversation_service: ConversationService,
    openai_api_key: Optional[str] = None
) -> Optional[REPLLangChainEnhancer]:
    """
    Enhance a REPL widget with LangChain RAG capabilities.
    
    Args:
        repl_widget: The REPL widget to enhance
        conversation_service: Conversation management service
        openai_api_key: OpenAI API key (optional, uses env var if not provided)
        
    Returns:
        REPLLangChainEnhancer instance or None if failed
    """
    try:
        enhancer = REPLLangChainEnhancer(
            repl_widget=repl_widget,
            conversation_service=conversation_service,
            openai_api_key=openai_api_key
        )
        
        # Store enhancer reference on widget
        repl_widget._rag_enhancer = enhancer
        
        # Add convenience methods to widget
        repl_widget.enhance_message_with_rag = enhancer.enhance_message_with_rag
        repl_widget.get_rag_context_summary = enhancer.get_context_summary
        repl_widget.clear_rag_context = enhancer.clear_rag_context
        repl_widget.set_rag_conversation = enhancer.set_conversation
        
        logger.info("REPL widget enhanced with LangChain RAG capabilities")
        return enhancer
        
    except Exception as e:
        logger.error(f"Failed to enhance REPL widget with LangChain: {e}")
        return None