"""
RAG Coordinator

Manages the FAISS-only RAG capabilities with the Ghostman application.
Handles initialization, configuration, and lifecycle management of FAISS RAG components.
"""

import os
import logging
from typing import Optional, Dict, Any

from ..infrastructure.storage.settings_manager import settings
from ..infrastructure.conversation_management.services.conversation_service import ConversationService
# FAISS-only imports - no LangChain dependencies

logger = logging.getLogger("ghostman.rag_coordinator")


class RAGCoordinator:
    """
    Coordinates FAISS-only RAG functionality across the Ghostman application.
    
    Responsibilities:
    - Initialize FAISS RAG components
    - Provide RAG status and statistics
    - Manage FAISS configuration and lifecycle
    - Support conversation-specific file isolation
    """
    
    def __init__(self, conversation_service: ConversationService):
        """
        Initialize RAG coordinator.
        
        Args:
            conversation_service: The conversation management service
        """
        self.conversation_service = conversation_service
        self.enhanced_widgets = {}  # widget_id -> enhancer
        self._rag_enabled = False
        self._initialization_error = None
        
        # Check if RAG should be enabled
        self._check_rag_availability()
        
        logger.info(f"RAG Coordinator initialized (enabled: {self._rag_enabled})")
    
    def _check_rag_availability(self):
        """Check if RAG functionality can be enabled."""
        try:
            # Check for OpenAI API key ONLY from settings
            api_key = settings.get("ai_model.api_key")
            
            if not api_key:
                self._initialization_error = "No OpenAI API key found"
                logger.info("RAG disabled: No OpenAI API key")
                return
            
            # Check for required packages (FAISS-only)
            try:
                import faiss
                import numpy as np
            except ImportError as e:
                self._initialization_error = f"Missing required packages for FAISS: {e}"
                logger.error(f"RAG disabled: {self._initialization_error}")
                return
            
            # Check if explicitly disabled in settings
            if not settings.get("rag.enabled", True):
                self._initialization_error = "RAG disabled in settings"
                logger.info("RAG disabled by user settings")
                return
            
            # Validate FAISS database initialization
            try:
                self._validate_faiss_initialization()
            except Exception as faiss_error:
                logger.warning(f"FAISS validation warning: {faiss_error}")
                # Don't disable RAG for FAISS issues, just log the warning
            
            self._rag_enabled = True
            logger.info("RAG functionality available")
            
        except Exception as e:
            self._initialization_error = f"RAG availability check failed: {e}"
            logger.error(self._initialization_error)
    
    def _validate_faiss_initialization(self):
        """Validate FAISS database can be initialized properly."""
        try:
            from .rag_pipeline.config.rag_config import get_config
            from .rag_pipeline.threading.simple_faiss_session import create_simple_faiss_session
            
            # Get RAG configuration (this will create directories)
            config = get_config()
            logger.info(f"FAISS persist directory: {config.vector_store.persist_directory}")
            
            # Test FAISS session creation
            test_session = create_simple_faiss_session(config)
            if test_session.is_ready:
                stats = test_session.get_stats()
                logger.info(f"FAISS validation successful: {stats}")
                test_session.close()
            else:
                logger.warning("FAISS session not ready after initialization")
                
        except Exception as e:
            logger.warning(f"FAISS validation failed: {e}")
            # Continue anyway - FAISS issues shouldn't prevent app startup
            raise e
    
    def is_enabled(self) -> bool:
        """Check if RAG is enabled."""
        return self._rag_enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get RAG system status."""
        return {
            'enabled': self._rag_enabled,
            'error': self._initialization_error,
            'enhanced_widgets': len(self.enhanced_widgets),
            'api_key_configured': bool(settings.get("ai_model.api_key")),
            'persist_directory': self._get_persist_directory()
        }
    
    def _get_persist_directory(self) -> str:
        """Get the directory for FAISS data persistence."""
        data_dir = settings.get('paths.data_dir', os.path.expanduser('~/.Ghostman'))
        return os.path.join(data_dir, 'rag', 'faiss_db')
    
    def enhance_repl_widget(self, repl_widget, widget_id: str = None) -> bool:
        """
        Enhance a REPL widget with FAISS RAG capabilities.
        
        Args:
            repl_widget: The REPL widget to enhance
            widget_id: Optional widget identifier
            
        Returns:
            True if enhancement was successful
        """
        if not self._rag_enabled:
            logger.debug(f"FAISS RAG enhancement skipped: {self._initialization_error}")
            return False
        
        try:
            widget_id = widget_id or f"repl_{id(repl_widget)}"
            
            # Check if already enhanced
            if widget_id in self.enhanced_widgets:
                logger.debug(f"REPL widget {widget_id} already enhanced with FAISS")
                return True
            
            # FAISS enhancement is now handled directly by the REPL widget
            # The REPL widget manages its own FAISS session
            logger.info(f"FAISS RAG enabled for widget {widget_id}")
            self.enhanced_widgets[widget_id] = {"type": "faiss", "enabled": True}
            return True
                
        except Exception as e:
            logger.error(f"Failed to enhance REPL widget: {e}")
            return False
    
    def _get_api_key(self) -> Optional[str]:
        """Get OpenAI API key from settings ONLY."""
        return settings.get("ai_model.api_key")
    
    def remove_widget_enhancement(self, widget_id: str):
        """Remove RAG enhancement from a widget."""
        if widget_id in self.enhanced_widgets:
            enhancer = self.enhanced_widgets[widget_id]
            enhancer.cleanup()
            del self.enhanced_widgets[widget_id]
            logger.info(f"Removed RAG enhancement from widget {widget_id}")
    
    def set_conversation_for_all_widgets(self, conversation_id: str):
        """Set current conversation for all enhanced widgets."""
        for widget_id, enhancer in self.enhanced_widgets.items():
            try:
                enhancer.set_conversation(conversation_id)
            except Exception as e:
                logger.error(f"Failed to set conversation for widget {widget_id}: {e}")
    
    def clear_context_for_all_widgets(self):
        """Clear RAG context for all enhanced widgets."""
        for widget_id, enhancer in self.enhanced_widgets.items():
            try:
                enhancer.clear_rag_context()
            except Exception as e:
                logger.error(f"Failed to clear context for widget {widget_id}: {e}")
    
    def get_widget_context_summary(self, widget_id: str) -> Dict[str, Any]:
        """Get context summary for a specific widget."""
        if widget_id in self.enhanced_widgets:
            try:
                return self.enhanced_widgets[widget_id].get_context_summary()
            except Exception as e:
                logger.error(f"Failed to get context for widget {widget_id}: {e}")
        
        return {'has_context': False, 'error': 'Widget not found or not enhanced'}
    
    def get_all_context_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get context summaries for all enhanced widgets."""
        summaries = {}
        for widget_id, enhancer in self.enhanced_widgets.items():
            try:
                summaries[widget_id] = enhancer.get_context_summary()
            except Exception as e:
                summaries[widget_id] = {'has_context': False, 'error': str(e)}
        
        return summaries
    
    def configure_rag_settings(self, settings_dict: Dict[str, Any]):
        """Configure RAG settings."""
        try:
            # Update settings
            for key, value in settings_dict.items():
                settings.set(f"rag.{key}", value)
            
            # Re-check availability if API key was updated
            if "openai_api_key" in settings_dict:
                self._check_rag_availability()
            
            logger.info("RAG settings updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update RAG settings: {e}")
            return False
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG usage statistics."""
        stats = {
            'total_widgets_enhanced': len(self.enhanced_widgets),
            'widgets_with_context': 0,
            'total_documents': 0,
            'total_chunks': 0
        }
        
        for widget_id, enhancer in self.enhanced_widgets.items():
            try:
                summary = enhancer.get_context_summary()
                if summary.get('has_context'):
                    stats['widgets_with_context'] += 1
                    stats['total_documents'] += summary.get('document_count', 0)
                    stats['total_chunks'] += summary.get('total_chunks', 0)
            except Exception as e:
                logger.debug(f"Failed to get stats for widget {widget_id}: {e}")
        
        return stats
    
    def cleanup(self):
        """Cleanup RAG coordinator resources."""
        logger.info("Cleaning up RAG coordinator...")
        
        # Cleanup all enhanced widgets
        for widget_id in list(self.enhanced_widgets.keys()):
            self.remove_widget_enhancement(widget_id)
        
        self.enhanced_widgets.clear()
        logger.info("RAG coordinator cleanup completed")


# Global RAG coordinator instance
_rag_coordinator: Optional[RAGCoordinator] = None


def get_rag_coordinator() -> Optional[RAGCoordinator]:
    """Get the global RAG coordinator instance."""
    return _rag_coordinator


def initialize_rag_coordinator(conversation_service: ConversationService) -> RAGCoordinator:
    """Initialize the global RAG coordinator."""
    global _rag_coordinator
    
    if _rag_coordinator is None:
        _rag_coordinator = RAGCoordinator(conversation_service)
    
    return _rag_coordinator


def cleanup_rag_coordinator():
    """Cleanup the global RAG coordinator."""
    global _rag_coordinator
    
    if _rag_coordinator:
        _rag_coordinator.cleanup()
        _rag_coordinator = None