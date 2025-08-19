"""
Main conversation manager coordinating all conversation management components.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Set, Callable
from pathlib import Path

from ..services.conversation_service import ConversationService
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.database import DatabaseManager
from ..models.conversation import Conversation
from ..models.search import SearchQuery, SearchResults
from ..models.enums import ConversationStatus, SortOrder
from .ai_service_integration import ConversationAIService

logger = logging.getLogger("ghostman.conversation_manager")


class ConversationManager:
    """
    Main conversation manager providing unified access to all conversation features.
    
    This is the primary entry point for the conversation management system.
    It coordinates all services and provides a clean API for UI integration.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize conversation manager."""
        # Initialize database and repository
        self.db_manager = DatabaseManager(db_path)
        self.repository = ConversationRepository(self.db_manager)
        self.conversation_service = ConversationService(self.repository)
        
        # AI service integration
        self._ai_service: Optional[ConversationAIService] = None
        
        # Event callbacks
        self._status_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Initialization state
        self._initialized = False
        
        logger.info("ConversationManager created")
    
    # --- Initialization ---
    
    def initialize(self) -> bool:
        """Initialize the conversation manager."""
        try:
            # Initialize database
            if not self.db_manager.initialize():
                logger.error("Failed to initialize database")
                return False
            
            # Set up event callbacks
            self._setup_service_callbacks()
            
            self._initialized = True
            logger.info("✓ ConversationManager initialized successfully")
            
            # Notify status callbacks
            self._notify_status("initialized", {"success": True})
            
            return True
            
        except Exception as e:
            logger.error(f"✗ ConversationManager initialization failed: {e}")
            self._notify_status("initialization_failed", {"error": str(e)})
            return False
    
    def _setup_service_callbacks(self):
        """Set up callbacks from conversation service."""
        def on_conversation_created(conversation: Conversation):
            self._notify_status("conversation_created", {
                "conversation_id": conversation.id,
                "title": conversation.title
            })
        
        def on_conversation_updated(conversation: Conversation):
            self._notify_status("conversation_updated", {
                "conversation_id": conversation.id,
                "title": conversation.title
            })
        
        def on_message_added(message):
            self._notify_status("message_added", {
                "conversation_id": message.conversation_id,
                "role": message.role.value,
                "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
            })
        
        self.conversation_service.add_conversation_created_callback(on_conversation_created)
        self.conversation_service.add_conversation_updated_callback(on_conversation_updated)
        self.conversation_service.add_message_added_callback(on_message_added)
    
    # --- AI Service Integration ---
    
    def get_ai_service(self) -> Optional[ConversationAIService]:
        """Get the conversation-aware AI service."""
        if not self._initialized:
            logger.error("ConversationManager not initialized")
            return None
        
        if not self._ai_service:
            self._ai_service = ConversationAIService(self.conversation_service)
            
            # Initialize AI service with current settings
            try:
                if not self._ai_service.initialize():
                    logger.error("Failed to initialize AI service")
                    self._ai_service = None
                    return None
                    
                logger.info("✓ ConversationAIService initialized")
                
            except Exception as e:
                logger.error(f"✗ AI service initialization failed: {e}")
                self._ai_service = None
                return None
        
        return self._ai_service
    
    def has_ai_service(self) -> bool:
        """Check if AI service is available and initialized."""
        return self._ai_service is not None and self._ai_service.is_initialized
    
    # --- Conversation Operations ---
    
    async def create_conversation(
        self,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        category: Optional[str] = None
    ) -> Optional[Conversation]:
        """Create a new conversation."""
        if not self._initialized:
            logger.error("ConversationManager not initialized")
            return None
        
        try:
            return await self.conversation_service.create_conversation(
                title=title,
                initial_message=initial_message,
                tags=tags,
                category=category
            )
        except Exception as e:
            logger.error(f"✗ Failed to create conversation: {e}")
            self._notify_status("error", {"operation": "create_conversation", "error": str(e)})
            return None
    
    async def get_conversation(self, conversation_id: str, include_messages: bool = True) -> Optional[Conversation]:
        """Get conversation by ID."""
        if not self._initialized:
            return None
        
        try:
            return await self.conversation_service.get_conversation(conversation_id, include_messages=include_messages)
        except Exception as e:
            logger.error(f"✗ Failed to get conversation: {e}")
            return None
    
    async def list_conversations(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = 20,
        offset: int = 0,
        sort_order: SortOrder = SortOrder.UPDATED_DESC
    ) -> List[Conversation]:
        """List conversations with filtering."""
        if not self._initialized:
            return []
        
        try:
            return await self.conversation_service.list_conversations(
                status=status,
                limit=limit,
                offset=offset,
                sort_order=sort_order
            )
        except Exception as e:
            logger.error(f"✗ Failed to list conversations: {e}")
            return []
    
    async def search_conversations(self, query: SearchQuery) -> SearchResults:
        """Search conversations."""
        if not self._initialized:
            return SearchResults(results=[], total_count=0)
        
        try:
            return await self.conversation_service.search_conversations(query)
        except Exception as e:
            logger.error(f"✗ Search failed: {e}")
            return SearchResults(results=[], total_count=0)
    
    async def delete_conversation(self, conversation_id: str, permanent: bool = False) -> bool:
        """Delete a conversation."""
        if not self._initialized:
            return False
        
        try:
            success = await self.conversation_service.delete_conversation(conversation_id, permanent)
            if success:
                self._notify_status("conversation_deleted", {
                    "conversation_id": conversation_id,
                    "permanent": permanent
                })
            return success
        except Exception as e:
            logger.error(f"✗ Failed to delete conversation: {e}")
            return False
    
    # --- Export Operations ---
    
    async def export_conversation(
        self,
        conversation_id: str,
        format: str,
        file_path: str
    ) -> bool:
        """Export a conversation to file."""
        if not self._initialized:
            return False
        
        try:
            success = await self.conversation_service.export_conversation(
                conversation_id, format, file_path
            )
            if success:
                self._notify_status("conversation_exported", {
                    "conversation_id": conversation_id,
                    "format": format,
                    "file_path": file_path
                })
            return success
        except Exception as e:
            logger.error(f"✗ Export failed: {e}")
            return False
    
    async def export_conversations(
        self,
        conversation_ids: List[str],
        format: str,
        file_path: str
    ) -> bool:
        """Export multiple conversations to file."""
        if not self._initialized:
            return False
        
        try:
            success = await self.conversation_service.export_conversations(
                conversation_ids, format, file_path
            )
            if success:
                self._notify_status("conversations_exported", {
                    "conversation_count": len(conversation_ids),
                    "format": format,
                    "file_path": file_path
                })
            return success
        except Exception as e:
            logger.error(f"✗ Bulk export failed: {e}")
            return False
    
    # --- Quick Access Methods ---
    
    async def get_recent_conversations(self, limit: int = 10) -> List[Conversation]:
        """Get recently updated conversations."""
        return await self.list_conversations(
            status=ConversationStatus.ACTIVE,
            limit=limit,
            sort_order=SortOrder.UPDATED_DESC
        )
    
    async def get_pinned_conversations(self) -> List[Conversation]:
        """Get pinned conversations."""
        return await self.list_conversations(
            status=ConversationStatus.PINNED,
            sort_order=SortOrder.UPDATED_DESC
        )
    
    async def search_by_text(self, text: str, limit: int = 10) -> SearchResults:
        """Simple text search."""
        query = SearchQuery.create_simple_text_search(text, limit)
        return await self.search_conversations(query)
    
    # --- Tag Management ---
    
    async def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all conversation tags with usage statistics."""
        if not self._initialized:
            return []
        
        try:
            return await self.conversation_service.get_all_tags()
        except Exception as e:
            logger.error(f"✗ Failed to get tags: {e}")
            return []
    
    async def add_tags_to_conversation(self, conversation_id: str, tags: Set[str]) -> bool:
        """Add tags to a conversation."""
        if not self._initialized:
            return False
        
        try:
            return await self.conversation_service.add_tags_to_conversation(conversation_id, tags)
        except Exception as e:
            logger.error(f"✗ Failed to add tags: {e}")
            return False
    
    # --- Analytics and Statistics ---
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive conversation statistics."""
        if not self._initialized:
            return {}
        
        try:
            # Get conversation stats
            conv_stats = await self.conversation_service.get_conversation_statistics()
            
            # Get database stats
            db_stats = self.db_manager.get_stats()
            
            # Get AI service stats
            ai_stats = {}
            if self.has_ai_service():
                ai_stats = self._ai_service.get_conversation_summary()
            
            # Combine all stats
            return {
                'conversation_stats': conv_stats,
                'database_stats': db_stats,
                'ai_service_stats': ai_stats,
                'system_info': {
                    'initialized': self._initialized,
                    'has_ai_service': self.has_ai_service(),
                    'database_path': str(self.db_manager.db_path)
                }
            }
            
        except Exception as e:
            logger.error(f"✗ Failed to get statistics: {e}")
            return {}
    
    # --- Maintenance Operations ---
    
    async def cleanup_old_conversations(
        self,
        older_than_days: int = 90,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old deleted conversations."""
        if not self._initialized:
            return {"error": "Not initialized"}
        
        try:
            return await self.conversation_service.cleanup_old_conversations(
                older_than_days=older_than_days,
                dry_run=dry_run
            )
        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
            return {"error": str(e)}
    
    def optimize_database(self) -> bool:
        """Optimize the database for better performance."""
        if not self._initialized:
            return False
        
        try:
            self.db_manager.vacuum()
            self._notify_status("database_optimized", {})
            return True
        except Exception as e:
            logger.error(f"✗ Database optimization failed: {e}")
            return False
    
    # --- Event System ---
    
    def add_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for status updates."""
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Remove status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status(self, status: str, data: Dict[str, Any]):
        """Notify all status callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    # --- Status Management ---
    
    async def update_conversation_status(self, conversation_id: str, status: 'ConversationStatus') -> bool:
        """Update conversation status."""
        if not self._initialized:
            return False
        
        try:
            # Update via the conversation service
            success = await self.conversation_service.update_conversation_status(conversation_id, status)
            if success:
                self._notify_status("conversation_status_updated", {
                    "conversation_id": conversation_id,
                    "status": status.value
                })
                logger.debug(f"Updated conversation {conversation_id[:8]}... status to {status.value}")
            return success
        except Exception as e:
            logger.error(f"✗ Failed to update conversation status: {e}")
            return False
    
    def set_conversation_active_simple(self, conversation_id: str) -> bool:
        """
        Simple, bulletproof way to set a conversation as active.
        No async, no complex logic, just works.
        """
        if not self._initialized:
            return False
        
        # Use the simple status service
        if not hasattr(self, '_simple_status'):
            from ..services.simple_status_service import SimpleStatusService
            self._simple_status = SimpleStatusService(self.db_manager)
        
        success = self._simple_status.set_conversation_active(conversation_id)
        if success:
            self._notify_status("conversation_activated", {
                "conversation_id": conversation_id
            })
        return success
    
    def get_active_conversation_id_simple(self) -> Optional[str]:
        """Get active conversation ID - simple way."""
        if not self._initialized:
            return None
            
        if not hasattr(self, '_simple_status'):
            from ..services.simple_status_service import SimpleStatusService
            self._simple_status = SimpleStatusService(self.db_manager)
        
        return self._simple_status.get_active_conversation_id()
    
    def fix_multiple_active_conversations(self) -> bool:
        """Fix any issues with multiple active conversations."""
        if not self._initialized:
            return False
            
        if not hasattr(self, '_simple_status'):
            from ..services.simple_status_service import SimpleStatusService
            self._simple_status = SimpleStatusService(self.db_manager)
        
        return self._simple_status.fix_multiple_active_conversations()
    
    # --- Utilities ---
    
    def get_active_conversation_id(self) -> Optional[str]:
        """Get the currently active conversation ID."""
        if self.has_ai_service():
            return self._ai_service.get_current_conversation_id()
        return self.conversation_service.get_active_conversation_id()
    
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._initialized
    
    def get_database_path(self) -> str:
        """Get the database file path."""
        return str(self.db_manager.db_path)
    
    # --- Shutdown ---
    
    def shutdown(self):
        """Shutdown the conversation manager."""
        logger.info("Shutting down ConversationManager...")
        
        try:
            # Shutdown AI service
            if self._ai_service:
                self._ai_service.shutdown()
                self._ai_service = None
            
            # Shutdown conversation service
            if self.conversation_service:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(self.conversation_service.shutdown())
            
            # Close database connections
            if self.db_manager:
                self.db_manager.close_all_connections()
            
            # Clear callbacks
            self._status_callbacks.clear()
            
            self._initialized = False
            
            logger.info("✓ ConversationManager shut down successfully")
            
        except Exception as e:
            logger.error(f"✗ Error during ConversationManager shutdown: {e}")
        finally:
            self._notify_status("shutdown", {"success": True})