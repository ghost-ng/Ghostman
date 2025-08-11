"""
Integration layer for conversation management system.

Provides seamless integration with existing AIService and UI components.
"""

from .ai_service_integration import ConversationAIService, ConversationContextAdapter
from .conversation_manager import ConversationManager

__all__ = ['ConversationAIService', 'ConversationContextAdapter', 'ConversationManager']