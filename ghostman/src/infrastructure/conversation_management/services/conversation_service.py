"""
Main conversation service providing high-level conversation management.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Callable
from uuid import uuid4

from ..models.conversation import Conversation, Message, ConversationMetadata
from ..models.enums import ConversationStatus, MessageRole, SortOrder
from ..models.search import SearchQuery, SearchResults
from ..repositories.conversation_repository import ConversationRepository
from .summary_service import SummaryService
from .export_service import ExportService

logger = logging.getLogger("ghostman.conversation_service")


class ConversationServiceError(Exception):
    """Base exception for conversation service errors."""
    pass


class ConversationService:
    """
    Main conversation service providing high-level operations.
    
    This service orchestrates conversation management operations,
    integrates with AI services, and provides event notifications.
    """
    
    def __init__(self, repository: Optional[ConversationRepository] = None):
        """Initialize conversation service."""
        self.repository = repository or ConversationRepository()
        self.summary_service = SummaryService(self.repository)
        self.export_service = ExportService(self.repository)
        
        # Event callbacks
        self._conversation_created_callbacks: List[Callable[[Conversation], None]] = []
        self._conversation_updated_callbacks: List[Callable[[Conversation], None]] = []
        self._message_added_callbacks: List[Callable[[Message], None]] = []
        
        # Active conversation tracking
        self._active_conversation_id: Optional[str] = None
        
        logger.info("ConversationService initialized")
    
    # --- Core Conversation Operations ---
    
    async def create_conversation(
        self,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        category: Optional[str] = None,
        auto_title: bool = True
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            title: Conversation title (auto-generated if None and auto_title=True)
            initial_message: Optional initial system message
            tags: Optional set of tags
            category: Optional category
            auto_title: Auto-generate title from first user message
            
        Returns:
            Created conversation
        """
        try:
            # Create metadata
            metadata = ConversationMetadata(
                tags=tags or set(),
                category=category
            )
            
            # Create conversation
            conversation = Conversation.create(
                title=title or "New Conversation",
                initial_message=initial_message,
                metadata=metadata
            )
            
            # Save to repository with better error handling
            try:
                success = await self.repository.create_conversation(conversation)
                if not success:
                    # Try to get more detailed error information
                    logger.error("Database save returned False - attempting to diagnose issue")
                    
                    # Check if database is accessible
                    try:
                        test_conversations = await self.repository.list_conversations(limit=1)
                        logger.info(f"Database is accessible - can list {len(test_conversations)} conversations")
                    except Exception as db_test_error:
                        logger.error(f"Database accessibility test failed: {db_test_error}")
                        raise ConversationServiceError(f"Database is not accessible: {db_test_error}")
                    
                    raise ConversationServiceError("Failed to create conversation in database - reason unknown")
                    
            except Exception as repo_error:
                logger.error(f"Repository create_conversation failed: {repo_error}")
                raise ConversationServiceError(f"Repository error: {repo_error}")
            
            # Set as active conversation
            self._active_conversation_id = conversation.id
            
            # Notify callbacks
            for callback in self._conversation_created_callbacks:
                try:
                    callback(conversation)
                except Exception as e:
                    logger.error(f"Conversation created callback error: {e}")
            
            logger.info(f"✓ Created conversation: {conversation.id} - {conversation.title}")
            return conversation
            
        except Exception as e:
            logger.error(f"✗ Failed to create conversation: {e}")
            raise ConversationServiceError(f"Failed to create conversation: {e}")
    
    async def get_conversation(self, conversation_id: str, include_messages: bool = True) -> Optional[Conversation]:
        """Get conversation by ID."""
        try:
            return await self.repository.get_conversation(conversation_id, include_messages)
        except Exception as e:
            logger.error(f"✗ Failed to get conversation {conversation_id}: {e}")
            return None
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.update_title(title)
            success = await self.repository.update_conversation(conversation)
            
            if success:
                # Notify callbacks
                for callback in self._conversation_updated_callbacks:
                    try:
                        callback(conversation)
                    except Exception as e:
                        logger.error(f"Conversation updated callback error: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to update conversation title: {e}")
            return False
    
    async def update_conversation_status(self, conversation_id: str, status: 'ConversationStatus') -> bool:
        """Update conversation status."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.status = status
            conversation.updated_at = datetime.now()
            success = await self.repository.update_conversation(conversation)
            
            if success:
                # Notify callbacks
                for callback in self._conversation_updated_callbacks:
                    try:
                        callback(conversation)
                    except Exception as e:
                        logger.error(f"Conversation updated callback error: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to update conversation status: {e}")
            return False
    
    async def set_conversation_as_active(self, conversation_id: str) -> bool:
        """
        DEPRECATED: Use ConversationManager.set_conversation_active_simple() instead.
        
        Set a conversation as active and ensure all others are pinned.
        This is an atomic operation that prevents multiple active conversations.
        """
        try:
            logger.info(f"🔄 Setting conversation {conversation_id[:8]}... as active")
            
            # First, set all conversations to pinned
            await self.repository.update_all_conversations_status(ConversationStatus.PINNED, 
                                                                 exclude_statuses=[ConversationStatus.DELETED, ConversationStatus.ARCHIVED])
            
            # Then, set the target conversation as active
            success = await self.update_conversation_status(conversation_id, ConversationStatus.ACTIVE)
            
            if success:
                logger.info(f"✓ Conversation {conversation_id[:8]}... is now active, all others are pinned")
            
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to set conversation as active: {e}")
            return False
    
    async def add_message_to_conversation(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Add a message to a conversation."""
        try:
            # Create message
            message = Message.create(
                conversation_id=conversation_id,
                role=role,
                content=content,
                token_count=token_count,
                metadata=metadata
            )
            
            # Save message
            success = await self.repository.add_message(message)
            if not success:
                return None
            
            # Update active conversation
            if conversation_id == self._active_conversation_id:
                # Trigger auto-title generation for first user message
                if role == MessageRole.USER:
                    conversation = await self.get_conversation(conversation_id, include_messages=False)
                    if conversation and conversation.title == "New Conversation":
                        auto_title = self._generate_auto_title(content)
                        await self.update_conversation_title(conversation_id, auto_title)
            
            # Notify callbacks
            for callback in self._message_added_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Message added callback error: {e}")
            
            logger.debug(f"Added {role.value} message to conversation {conversation_id}")
            return message
            
        except Exception as e:
            logger.error(f"✗ Failed to add message: {e}")
            return None
    
    async def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.archive()
            success = await self.repository.update_conversation(conversation)
            
            if success and conversation_id == self._active_conversation_id:
                self._active_conversation_id = None
            
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to archive conversation: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str, permanent: bool = False) -> bool:
        """Delete a conversation (soft delete by default)."""
        try:
            if permanent:
                success = await self.repository.delete_conversation(conversation_id, soft_delete=False)
            else:
                conversation = await self.get_conversation(conversation_id, include_messages=False)
                if not conversation:
                    return False
                
                conversation.delete()
                success = await self.repository.update_conversation(conversation)
            
            if success and conversation_id == self._active_conversation_id:
                self._active_conversation_id = None
            
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to delete conversation: {e}")
            return False
    
    async def restore_conversation(self, conversation_id: str) -> bool:
        """Restore a deleted conversation."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.restore()
            return await self.repository.update_conversation(conversation)
            
        except Exception as e:
            logger.error(f"✗ Failed to restore conversation: {e}")
            return False
    
    # --- Conversation Management ---
    
    async def list_conversations(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_order: SortOrder = SortOrder.UPDATED_DESC,
        include_deleted: bool = False
    ) -> List[Conversation]:
        """List conversations with filtering and pagination."""
        try:
            conversations = await self.repository.list_conversations(status, limit, offset, sort_order, include_deleted)
            return conversations
        except Exception as e:
            logger.error(f"✗ Failed to list conversations: {e}")
            return []
    
    async def get_conversations_with_file_counts(self, conversation_ids: List[str]) -> Dict[str, int]:
        """Get file counts for multiple conversations in a single batch query."""
        try:
            return await self.repository.get_conversations_file_counts(conversation_ids)
        except Exception as e:
            logger.error(f"✗ Failed to get conversations file counts: {e}")
            return {}
    
    async def search_conversations(self, query: SearchQuery) -> SearchResults:
        """Search conversations using full-text search and filters."""
        try:
            return await self.repository.search_conversations(query)
        except Exception as e:
            logger.error(f"✗ Search failed: {e}")
            return SearchResults(results=[], total_count=0)
    
    async def get_recent_conversations(self, days: int = 7, limit: int = 10) -> List[Conversation]:
        """Get recently updated conversations."""
        query = SearchQuery.create_recent_search(days, limit)
        results = await self.search_conversations(query)
        
        # Load full conversations
        conversations = []
        for result in results.results:
            conv = await self.get_conversation(result.conversation_id, include_messages=False)
            if conv:
                conversations.append(conv)
        
        return conversations
    
    # --- Tag Management ---
    
    async def add_tags_to_conversation(self, conversation_id: str, tags: Set[str]) -> bool:
        """Add tags to a conversation."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.add_tags(*tags)
            return await self.repository.update_conversation(conversation)
            
        except Exception as e:
            logger.error(f"✗ Failed to add tags: {e}")
            return False
    
    async def remove_tags_from_conversation(self, conversation_id: str, tags: Set[str]) -> bool:
        """Remove tags from a conversation."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if not conversation:
                return False
            
            conversation.remove_tags(*tags)
            return await self.repository.update_conversation(conversation)
            
        except Exception as e:
            logger.error(f"✗ Failed to remove tags: {e}")
            return False
    
    async def get_all_tags(self, min_usage: int = 1) -> List[Dict[str, Any]]:
        """Get all tags with usage statistics."""
        try:
            return await self.repository.get_all_tags(min_usage)
        except Exception as e:
            logger.error(f"✗ Failed to get tags: {e}")
            return []
    
    # --- Active Conversation Management ---
    
    def set_active_conversation(self, conversation_id: Optional[str]):
        """Set the active conversation."""
        self._active_conversation_id = conversation_id
        logger.debug(f"Active conversation set to: {conversation_id}")
    
    def get_active_conversation_id(self) -> Optional[str]:
        """Get the current active conversation ID."""
        return self._active_conversation_id
    
    async def get_active_conversation(self) -> Optional[Conversation]:
        """Get the current active conversation."""
        if not self._active_conversation_id:
            return None
        return await self.get_conversation(self._active_conversation_id)
    
    # --- Summary Operations ---
    
    async def generate_conversation_summary(self, conversation_id: str) -> bool:
        """Generate AI summary for a conversation."""
        try:
            return await self.summary_service.generate_summary(conversation_id)
        except Exception as e:
            logger.error(f"✗ Failed to generate summary: {e}")
            return False
    
    async def generate_conversation_title(self, conversation_id: str) -> Optional[str]:
        """Generate AI title for a conversation."""
        try:
            return await self.summary_service.generate_title(conversation_id)
        except Exception as e:
            logger.error(f"✗ Failed to generate title: {e}")
            return None
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Get conversation summary if available."""
        try:
            conversation = await self.get_conversation(conversation_id, include_messages=False)
            if conversation and conversation.summary:
                return conversation.summary.summary
            return None
        except Exception as e:
            logger.error(f"✗ Failed to get summary: {e}")
            return None
    
    # --- Export Operations ---
    
    async def export_conversation(self, conversation_id: str, format: str, file_path: str) -> bool:
        """Export conversation to file."""
        try:
            return await self.export_service.export_conversation(conversation_id, format, file_path)
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
        try:
            return await self.export_service.export_conversations(conversation_ids, format, file_path)
        except Exception as e:
            logger.error(f"✗ Bulk export failed: {e}")
            return False
    
    # --- Analytics ---
    
    async def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive conversation statistics."""
        try:
            stats = await self.repository.get_conversation_stats()
            
            # Add service-level stats
            stats['active_conversation_id'] = self._active_conversation_id
            stats['total_callbacks'] = {
                'created': len(self._conversation_created_callbacks),
                'updated': len(self._conversation_updated_callbacks),
                'message_added': len(self._message_added_callbacks)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"✗ Failed to get statistics: {e}")
            return {}
    
    # --- Event System ---
    
    def add_conversation_created_callback(self, callback: Callable[[Conversation], None]):
        """Add callback for conversation created events."""
        self._conversation_created_callbacks.append(callback)
    
    def add_conversation_updated_callback(self, callback: Callable[[Conversation], None]):
        """Add callback for conversation updated events."""
        self._conversation_updated_callbacks.append(callback)
    
    def add_message_added_callback(self, callback: Callable[[Message], None]):
        """Add callback for message added events."""
        self._message_added_callbacks.append(callback)
    
    def remove_conversation_created_callback(self, callback: Callable[[Conversation], None]):
        """Remove conversation created callback."""
        if callback in self._conversation_created_callbacks:
            self._conversation_created_callbacks.remove(callback)
    
    def remove_conversation_updated_callback(self, callback: Callable[[Conversation], None]):
        """Remove conversation updated callback."""
        if callback in self._conversation_updated_callbacks:
            self._conversation_updated_callbacks.remove(callback)
    
    def remove_message_added_callback(self, callback: Callable[[Message], None]):
        """Remove message added callback."""
        if callback in self._message_added_callbacks:
            self._message_added_callbacks.remove(callback)
    
    # --- Utilities ---
    
    def _generate_auto_title(self, content: str, max_length: int = 50) -> str:
        """Generate automatic title from message content."""
        # Clean up content
        clean_content = content.strip()
        
        # Remove common prefixes
        prefixes_to_remove = ["please ", "can you ", "could you ", "would you ", "help me "]
        lower_content = clean_content.lower()
        for prefix in prefixes_to_remove:
            if lower_content.startswith(prefix):
                clean_content = clean_content[len(prefix):]
                break
        
        # Capitalize first letter
        if clean_content:
            clean_content = clean_content[0].upper() + clean_content[1:]
        
        # Truncate if too long
        if len(clean_content) <= max_length:
            return clean_content
        
        # Find last complete word within limit
        truncated = clean_content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.7:  # If we can keep at least 70% of the text
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    async def cleanup_old_conversations(
        self,
        older_than_days: int = 90,
        keep_pinned: bool = True,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old deleted conversations."""
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            # Find old deleted conversations
            query = SearchQuery(
                status=ConversationStatus.DELETED,
                updated_before=cutoff_date,
                limit=None  # Get all matching
            )
            
            results = await self.search_conversations(query)
            cleanup_candidates = []
            
            for result in results.results:
                conversation = await self.get_conversation(result.conversation_id, include_messages=False)
                if conversation:
                    # Skip pinned conversations if requested
                    if keep_pinned and conversation.status == ConversationStatus.PINNED:
                        continue
                    cleanup_candidates.append(conversation)
            
            cleanup_stats = {
                'candidates_found': len(cleanup_candidates),
                'cutoff_date': cutoff_date.isoformat(),
                'dry_run': dry_run,
                'deleted_count': 0,
                'errors': []
            }
            
            if not dry_run:
                for conversation in cleanup_candidates:
                    success = await self.delete_conversation(conversation.id, permanent=True)
                    if success:
                        cleanup_stats['deleted_count'] += 1
                    else:
                        cleanup_stats['errors'].append(f"Failed to delete {conversation.id}")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
            return {'error': str(e)}
    
    # --- Conversation-File Association Management ---
    
    async def add_file_to_conversation(
        self,
        conversation_id: str,
        file_id: str,
        filename: str,
        file_path: Optional[str] = None,
        file_size: int = 0,
        file_type: Optional[str] = None,
        chunk_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a file association to a conversation.
        
        Args:
            conversation_id: The conversation ID
            file_id: Unique file identifier (used in RAG pipeline)
            filename: Original filename
            file_path: Original file path
            file_size: File size in bytes
            file_type: File type/extension
            chunk_count: Number of chunks created in RAG
            metadata: Additional file metadata
            
        Returns:
            True if successfully added
        """
        try:
            from ..models.database_models import ConversationFileModel
            from uuid import uuid4
            
            # Create file association record
            file_record = ConversationFileModel(
                id=str(uuid4()),
                conversation_id=conversation_id,
                file_id=file_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                processing_status='queued',
                chunk_count=chunk_count,
                is_enabled=True,
                file_metadata=metadata or {}
            )
            
            # Save to database
            await self.repository._execute_with_session(
                lambda session: session.add(file_record)
            )
            
            logger.info(f"✓ Added file {filename} to conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to add file to conversation: {e}")
            return False
    
    async def update_file_processing_status(
        self,
        file_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update file processing status.
        
        Args:
            file_id: The file ID
            status: New processing status (queued, processing, completed, failed)
            chunk_count: Number of chunks created
            metadata: Additional metadata
            
        Returns:
            True if successfully updated
        """
        try:
            from ..models.database_models import ConversationFileModel
            
            def update_file(session):
                file_record = session.query(ConversationFileModel).filter_by(file_id=file_id).first()
                if file_record:
                    file_record.processing_status = status
                    if chunk_count is not None:
                        file_record.chunk_count = chunk_count
                    if metadata:
                        current_metadata = file_record.file_metadata
                        current_metadata.update(metadata)
                        file_record.file_metadata = current_metadata
                    return True
                return False
            
            success = await self.repository._execute_with_session(update_file)
            
            if success:
                logger.info(f"✓ Updated file {file_id} status to {status}")
            else:
                logger.warning(f"⚠ File {file_id} not found for status update")
                
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to update file status: {e}")
            return False
    
    async def toggle_file_enabled_status(self, file_id: str, enabled: bool) -> bool:
        """
        Toggle whether a file is enabled for context inclusion.
        
        Args:
            file_id: The file ID
            enabled: Whether file should be enabled
            
        Returns:
            True if successfully toggled
        """
        try:
            from ..models.database_models import ConversationFileModel
            
            def toggle_file(session):
                file_record = session.query(ConversationFileModel).filter_by(file_id=file_id).first()
                if file_record:
                    file_record.is_enabled = enabled
                    return True
                return False
            
            success = await self.repository._execute_with_session(toggle_file)
            
            if success:
                logger.info(f"✓ File {file_id} {'enabled' if enabled else 'disabled'} for context")
            else:
                logger.warning(f"⚠ File {file_id} not found for toggle")
                
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to toggle file status: {e}")
            return False
    
    async def remove_file_from_conversation(self, file_id: str) -> bool:
        """
        Remove a file association from a conversation.
        
        Args:
            file_id: The file ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            from ..models.database_models import ConversationFileModel
            
            def remove_file(session):
                file_record = session.query(ConversationFileModel).filter_by(file_id=file_id).first()
                if file_record:
                    session.delete(file_record)
                    return True
                return False
            
            success = await self.repository._execute_with_session(remove_file)
            
            if success:
                logger.info(f"✓ Removed file {file_id} from conversation")
            else:
                logger.warning(f"⚠ File {file_id} not found for removal")
                
            return success
            
        except Exception as e:
            logger.error(f"✗ Failed to remove file from conversation: {e}")
            return False
    
    async def get_conversation_files(self, conversation_id: str, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all files associated with a conversation.
        
        Args:
            conversation_id: The conversation ID
            enabled_only: If True, only return enabled files
            
        Returns:
            List of file information dictionaries
        """
        try:
            from ..models.database_models import ConversationFileModel
            
            def get_files(session):
                query = session.query(ConversationFileModel).filter_by(conversation_id=conversation_id)
                if enabled_only:
                    query = query.filter_by(is_enabled=True)
                
                files = query.order_by(ConversationFileModel.upload_timestamp).all()
                
                return [
                    {
                        'id': f.id,
                        'file_id': f.file_id,
                        'filename': f.filename,
                        'file_path': f.file_path,
                        'file_size': f.file_size,
                        'file_type': f.file_type,
                        'upload_timestamp': f.upload_timestamp,
                        'processing_status': f.processing_status,
                        'chunk_count': f.chunk_count,
                        'is_enabled': f.is_enabled,
                        'metadata': f.file_metadata
                    }
                    for f in files
                ]
            
            files = await self.repository._execute_with_session(get_files)
            logger.info(f"✓ Retrieved {len(files)} files for conversation {conversation_id}")
            return files
            
        except Exception as e:
            logger.error(f"✗ Failed to get conversation files: {e}")
            return []
    
    async def clear_conversation_files(self, conversation_id: str) -> bool:
        """
        Clear all file associations for a conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if successfully cleared
        """
        try:
            from ..models.database_models import ConversationFileModel
            
            def clear_files(session):
                deleted_count = session.query(ConversationFileModel).filter_by(conversation_id=conversation_id).delete()
                return deleted_count
            
            deleted_count = await self.repository._execute_with_session(clear_files)
            logger.info(f"✓ Cleared {deleted_count} files from conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to clear conversation files: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the conversation service."""
        logger.info("Shutting down conversation service...")
        
        # Clear callbacks
        self._conversation_created_callbacks.clear()
        self._conversation_updated_callbacks.clear()
        self._message_added_callbacks.clear()
        
        # Reset active conversation
        self._active_conversation_id = None
        
        logger.info("✓ Conversation service shut down")