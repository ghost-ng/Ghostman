"""
Comprehensive Conversation Management System for Specter.

This package provides a complete conversation management solution including:
- Persistent conversation storage with SQLite
- Full-text search and advanced filtering
- AI-powered conversation summaries
- Export capabilities (JSON, TXT, Markdown, HTML)
- Tag management and categorization
- Analytics and statistics
- Seamless integration with existing AI service

Main Components:
- ConversationManager: Primary entry point and coordinator
- ConversationService: High-level business logic
- ConversationRepository: Data access layer
- ConversationAIService: AI service integration
- Export services for multiple formats

Usage:
    from specter.src.infrastructure.conversation_management import ConversationManager
    
    # Initialize conversation manager
    manager = ConversationManager()
    if manager.initialize():
        # Get AI service with conversation support
        ai_service = manager.get_ai_service()
        
        # Create and manage conversations
        conversation = await manager.create_conversation(
            title="My First Conversation",
            tags={"python", "ai"}
        )
"""

# Main entry points
from .integration.conversation_manager import ConversationManager
from .integration.ai_service_integration import ConversationAIService, ConversationContextAdapter

# Core services
from .services.conversation_service import ConversationService
from .services.summary_service import SummaryService
from .services.export_service import ExportService

# Data models
from .models.conversation import Conversation, Message, ConversationSummary, ConversationMetadata
from .models.search import SearchQuery, SearchResults, SearchResult
from .models.enums import ConversationStatus, MessageRole, ExportFormat, SearchScope, SortOrder

# Repository layer
from .repositories.conversation_repository import ConversationRepository
from .repositories.database import DatabaseManager

__version__ = "1.0.0"

__all__ = [
    # Main entry points
    'ConversationManager',
    'ConversationAIService',
    'ConversationContextAdapter',
    
    # Services
    'ConversationService',
    'SummaryService', 
    'ExportService',
    
    # Models
    'Conversation',
    'Message',
    'ConversationSummary',
    'ConversationMetadata',
    'SearchQuery',
    'SearchResults',
    'SearchResult',
    
    # Enums
    'ConversationStatus',
    'MessageRole',
    'ExportFormat',
    'SearchScope',
    'SortOrder',
    
    # Repository
    'ConversationRepository',
    'DatabaseManager',
]