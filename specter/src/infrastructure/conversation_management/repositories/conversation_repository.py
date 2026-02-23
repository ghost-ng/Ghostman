"""
Repository for conversation data operations using SQLAlchemy ORM.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from uuid import uuid4

from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.exc import SQLAlchemyError

from ..models.conversation import Conversation, Message, ConversationSummary, ConversationMetadata
from ..models.enums import ConversationStatus, MessageRole, SortOrder, SearchScope
from ..models.search import SearchQuery, SearchResult, SearchResults
from ..models.database_models import (
    ConversationModel, MessageModel, TagModel, ConversationTagModel,
    MessageFTSModel, ConversationSummaryModel, ConversationFileModel,
    sanitize_text, sanitize_html
)
from .database import DatabaseManager

logger = logging.getLogger("specter.conversation_repo")


class ConversationRepository:
    """Repository for conversation data operations using SQLAlchemy ORM."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize repository with database manager."""
        self.db = db_manager or DatabaseManager()
        if not self.db.is_initialized:
            self.db.initialize()
    
    # --- Conversation CRUD Operations ---
    
    async def create_conversation(self, conversation: Conversation, force_create: bool = False) -> bool:
        """Create a new conversation using SQLAlchemy ORM with detailed diagnostics."""
        logger.info(f"🔄 Repository: Creating conversation {conversation.id}")
        logger.debug(f"  🔍 Force create: {force_create}")
        logger.debug(f"  🔍 Conversation messages: {len(conversation.messages)}")
        logger.debug(f"  🔍 Conversation status: {conversation.status}")
        logger.debug(f"  🔍 Database initialized: {self.db.is_initialized}")
        
        # Check if conversation is empty and should not be saved (unless forced)
        if not force_create and self._is_empty_conversation(conversation):
            logger.info(f"📝 Skipping creation of empty conversation: {conversation.id} (use force_create=True to override)")
            return False
            
        try:
            logger.debug("🔍 Attempting to get database session...")
            with self.db.get_session() as session:
                logger.debug("✓ Database session acquired successfully")
                
                # Check if conversation already exists
                existing = session.query(ConversationModel).filter(
                    ConversationModel.id == conversation.id
                ).first()
                
                if existing:
                    logger.warning(f"⚠️ Conversation {conversation.id} already exists in database")
                    if not force_create:
                        logger.info(f"❌ Returning False - conversation exists and force_create=False")
                        return False
                    else:
                        logger.info(f"🔄 force_create=True - will overwrite existing conversation")
                
                # Create conversation model
                logger.debug("🔄 Creating ConversationModel...")
                conv_model = ConversationModel(
                    id=conversation.id,
                    title=sanitize_text(conversation.title),
                    status=conversation.status.value,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    message_count=len(conversation.messages)
                )
                
                # Set metadata using the proper property
                logger.debug("🔄 Setting conversation metadata...")
                metadata_dict = conversation.metadata.to_dict()
                logger.debug(f"  📊 Metadata: {metadata_dict}")
                conv_model.conversation_metadata = metadata_dict
                
                logger.debug("🔄 Adding conversation to session...")
                session.add(conv_model)
                logger.debug("✓ Conversation added to session")
                
                # Add messages
                logger.debug(f"🔄 Adding {len(conversation.messages)} messages...")
                for i, message in enumerate(conversation.messages):
                    logger.debug(f"  📝 Adding message {i+1}: {message.role.value} - {message.content[:50]}...")
                    message_model = MessageModel(
                        id=message.id,
                        conversation_id=message.conversation_id,
                        role=message.role.value,
                        content=sanitize_html(message.content),
                        timestamp=message.timestamp,
                        token_count=message.token_count,
                        metadata=message.metadata
                    )
                    session.add(message_model)
                
                logger.debug("✓ All messages added to session")
                
                # Update FTS index
                logger.debug("🔄 Updating FTS index...")
                try:
                    await self._update_fts_index(session, conversation)
                    logger.debug("✓ FTS index updated")
                except Exception as fts_error:
                    logger.warning(f"⚠️ FTS index update failed (non-critical): {fts_error}")
                
                # Handle tags
                logger.debug(f"🔄 Updating tags: {conversation.metadata.tags}")
                try:
                    await self._update_conversation_tags(session, conversation.id, conversation.metadata.tags)
                    logger.debug("✓ Tags updated")
                except Exception as tag_error:
                    logger.warning(f"⚠️ Tag update failed (non-critical): {tag_error}")
                
                # The session context manager will commit here
                logger.debug("🔄 Session context manager will now commit...")
                
            # If we reach here, the context manager completed successfully
            logger.info(f"✅ Successfully created conversation: {conversation.id}")
            
            # Verify the conversation was actually saved
            logger.debug("🔍 Verifying conversation was saved...")
            try:
                with self.db.get_session() as verify_session:
                    verify_conv = verify_session.query(ConversationModel).filter(
                        ConversationModel.id == conversation.id
                    ).first()
                    
                    if verify_conv:
                        logger.debug(f"✅ Verification successful: Found conversation with {len(verify_conv.messages) if verify_conv.messages else 0} messages")
                    else:
                        logger.error(f"🚨 VERIFICATION FAILED: Conversation {conversation.id} not found after creation!")
                        return False
                        
            except Exception as verify_error:
                logger.error(f"🚨 Verification check failed: {verify_error}")
                # Don't fail the creation for verification errors
                
            return True
                
        except SQLAlchemyError as e:
            logger.error(f"💥 SQLAlchemy error creating conversation {conversation.id}: {e}")
            logger.error(f"  🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"  📋 Full traceback:\n{traceback.format_exc()}")
            return False
        except Exception as e:
            logger.error(f"💥 Unexpected error creating conversation {conversation.id}: {e}")
            logger.error(f"  🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"  📋 Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def get_conversation(self, conversation_id: str, include_messages: bool = True) -> Optional[Conversation]:
        """Get conversation by ID using SQLAlchemy ORM with enhanced logging."""
        try:
            logger.debug(f"🔍 Fetching conversation {conversation_id} from database (include_messages: {include_messages})")
            
            with self.db.get_session() as session:
                query = session.query(ConversationModel).filter(ConversationModel.id == conversation_id)
                
                if include_messages:
                    query = query.options(
                        selectinload(ConversationModel.messages),
                        joinedload(ConversationModel.summary)
                    )
                
                conv_model = query.first()
                if not conv_model:
                    logger.warning(f"⚠ Conversation {conversation_id} not found in database")
                    return None
                
                logger.debug(f"📋 Found conversation in database: {conv_model.title}")
                logger.debug(f"📊 Raw message count from database: {len(conv_model.messages) if conv_model.messages else 0}")
                
                # Convert to domain model
                conversation = conv_model.to_domain_model()
                
                if include_messages:
                    # Load messages with detailed logging
                    messages = []
                    raw_messages = sorted(conv_model.messages, key=lambda m: m.timestamp) if conv_model.messages else []
                    
                    logger.debug(f"📝 Processing {len(raw_messages)} messages from database:")
                    for i, msg_model in enumerate(raw_messages):
                        try:
                            domain_message = msg_model.to_domain_model()
                            messages.append(domain_message)
                            preview = domain_message.content[:50] + "..." if len(domain_message.content) > 50 else domain_message.content
                            logger.debug(f"  📨 Message {i+1}: [{domain_message.role.value}] {preview}")
                        except Exception as msg_error:
                            logger.error(f"✗ Failed to convert message {i+1}: {msg_error}")
                    
                    conversation.messages = messages
                    logger.debug(f"✓ Loaded {len(messages)} messages into conversation object")
                    
                    # Load summary
                    if conv_model.summary:
                        conversation.summary = conv_model.summary.to_domain_model()
                        logger.debug("📄 Loaded conversation summary")
                else:
                    logger.debug("📋 Skipping message loading (include_messages=False)")
                
                logger.debug(f"✓ Successfully loaded conversation {conversation_id} with {len(conversation.messages)} messages")
                return conversation
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get conversation {conversation_id}: {e}", exc_info=True)
            return None
    
    async def update_conversation(self, conversation: Conversation) -> bool:
        """Update existing conversation using SQLAlchemy ORM."""
        # REMOVED AUTO-DELETION: Conversations should only be deleted when explicitly requested by user,
        # not automatically during updates. This was causing conversations to be marked as deleted
        # when update_conversation() was called before messages were added.
        #
        # The previous code would mark conversations as "deleted" if they had no messages,
        # which caused new conversations to appear as deleted before messages were saved.

        try:
            with self.db.get_session() as session:
                conv_model = session.query(ConversationModel).filter(
                    ConversationModel.id == conversation.id
                ).first()
                
                if not conv_model:
                    logger.warning(f"Conversation {conversation.id} not found for update")
                    return False
                
                # Update conversation fields
                conv_model.title = sanitize_text(conversation.title)
                conv_model.status = conversation.status.value
                conv_model.updated_at = conversation.updated_at
                conv_model.conversation_metadata = conversation.metadata.to_dict()
                conv_model.message_count = len(conversation.messages)
                
                # Update FTS index
                await self._update_fts_index(session, conversation)
                
                # Update tags
                await self._update_conversation_tags(session, conversation.id, conversation.metadata.tags)
                
                logger.debug(f"Updated conversation: {conversation.id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to update conversation {conversation.id}: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str, soft_delete: bool = True) -> bool:
        """Delete conversation using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                conv_model = session.query(ConversationModel).filter(
                    ConversationModel.id == conversation_id
                ).first()

                if not conv_model:
                    logger.warning(f"Conversation {conversation_id} not found for deletion")
                    return False

                if soft_delete:
                    # Soft delete - just mark as deleted
                    conv_model.status = ConversationStatus.DELETED.value
                    conv_model.updated_at = datetime.utcnow()
                else:
                    # Hard delete - get file records before deleting conversation
                    from ..models.database_models import ConversationFileModel
                    file_records = session.query(ConversationFileModel).filter(
                        ConversationFileModel.conversation_id == conversation_id
                    ).all()

                    # Delete physical files from disk
                    if file_records:
                        logger.info(f"🗑 Deleting {len(file_records)} physical files for conversation {conversation_id[:8]}...")
                        for file_record in file_records:
                            self._delete_physical_file(file_record)

                    # Delete FAISS index for this conversation
                    self._delete_conversation_faiss_index(conversation_id)

                    # Hard delete - remove from database (cascading will handle related records)
                    session.delete(conv_model)

                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted conversation: {conversation_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to delete conversation {conversation_id}: {e}")
            return False

    def _delete_physical_file(self, file_record) -> None:
        """Delete a physical file from disk if it exists."""
        try:
            if hasattr(file_record, 'file_path') and file_record.file_path:
                from pathlib import Path
                file_path = Path(file_record.file_path)
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    logger.debug(f"  ✓ Deleted physical file: {file_path.name}")
                else:
                    logger.debug(f"  ⚠ File not found on disk: {file_path}")
        except Exception as e:
            logger.warning(f"  ✗ Failed to delete physical file {file_record.filename}: {e}")

    def _delete_conversation_faiss_index(self, conversation_id: str) -> None:
        """Delete FAISS index directory for a conversation."""
        try:
            from pathlib import Path
            # FAISS indexes are stored in: specter_data/rag_indexes/<conversation_id>/
            from ...storage.settings_manager import settings
            settings_paths = settings.get_paths()
            settings_dir = Path(settings_paths['settings_dir'])
            specter_root = settings_dir.parent
            indexes_dir = specter_root / "rag_indexes" / conversation_id

            if indexes_dir.exists() and indexes_dir.is_dir():
                import shutil
                shutil.rmtree(indexes_dir)
                logger.info(f"  ✓ Deleted FAISS index: {indexes_dir}")
            else:
                logger.debug(f"  ℹ No FAISS index found for conversation {conversation_id[:8]}")
        except Exception as e:
            logger.warning(f"  ✗ Failed to delete FAISS index for {conversation_id[:8]}: {e}")
    
    async def list_conversations(
        self, 
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_order: SortOrder = SortOrder.UPDATED_DESC,
        include_deleted: bool = False
    ) -> List[Conversation]:
        """List conversations with optional filtering using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                query = session.query(ConversationModel)
                
                # Apply filters
                if status:
                    query = query.filter(ConversationModel.status == status.value)
                
                # Always exclude deleted conversations unless explicitly requested
                if not include_deleted:
                    query = query.filter(ConversationModel.status != ConversationStatus.DELETED.value)
                
                # Apply sorting
                query = self._apply_sort_order(query, sort_order)
                
                # Apply pagination
                if offset > 0:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                conv_models = query.all()
                conversations = []
                
                for conv_model in conv_models:
                    conversation = conv_model.to_domain_model()
                    conversation.messages = []  # Don't load full messages for listing
                    conversations.append(conversation)
                
                return conversations
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to list conversations: {e}")
            return []
    
    async def get_conversations_file_counts(self, conversation_ids: List[str]) -> Dict[str, int]:
        """Get file counts for multiple conversations in single batch query - solves N+1 problem."""
        try:
            with self.db.get_session() as session:
                # Single query to get file counts for all conversations
                query = session.query(
                    ConversationFileModel.conversation_id,
                    func.count(ConversationFileModel.id).label('file_count')
                ).filter(
                    ConversationFileModel.conversation_id.in_(conversation_ids),
                    ConversationFileModel.is_enabled == True
                ).group_by(ConversationFileModel.conversation_id)
                
                results = query.all()
                return {conv_id: count for conv_id, count in results}
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to batch load file counts: {e}")
            return {}
    
    async def get_conversations_file_info(self, conversation_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get file names and info for multiple conversations in single batch query."""
        try:
            with self.db.get_session() as session:
                # Single query to get all files for all conversations
                query = session.query(ConversationFileModel).filter(
                    ConversationFileModel.conversation_id.in_(conversation_ids),
                    ConversationFileModel.is_enabled == True
                ).order_by(
                    ConversationFileModel.conversation_id,
                    ConversationFileModel.upload_timestamp
                )
                
                files = query.all()
                
                # Group files by conversation_id
                result = {}
                for file in files:
                    conv_id = file.conversation_id
                    if conv_id not in result:
                        result[conv_id] = []
                    
                    result[conv_id].append({
                        'file_id': file.file_id,
                        'filename': file.filename,
                        'processing_status': file.processing_status,
                        'file_size': file.file_size,
                        'chunk_count': file.chunk_count
                    })
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to batch load file info: {e}")
            return {}
    
    async def reassign_orphaned_files(self, target_conversation_id: str) -> int:
        """Reassign files from deleted conversations to target conversation."""
        try:
            with self.db.get_session() as session:
                # Find files belonging to deleted conversations
                deleted_conversations = session.query(ConversationModel.id).filter(
                    ConversationModel.status == ConversationStatus.DELETED.value
                ).subquery()
                
                # Update files to point to target conversation
                update_count = session.query(ConversationFileModel).filter(
                    ConversationFileModel.conversation_id.in_(
                        session.query(deleted_conversations.c.id)
                    )
                ).update(
                    {ConversationFileModel.conversation_id: target_conversation_id},
                    synchronize_session='fetch'
                )
                
                logger.info(f"✅ Reassigned {update_count} orphaned files to conversation {target_conversation_id[:8]}...")
                return update_count
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to reassign orphaned files: {e}")
            return 0
    
    # --- Message Operations ---
    
    async def add_message(self, message: Message) -> bool:
        """Add message to conversation using SQLAlchemy ORM with enhanced logging."""
        try:
            logger.debug(f"💾 Adding message to conversation {message.conversation_id}: [{message.role.value}] {message.content[:50]}...")
            
            with self.db.get_session() as session:
                # Create message model
                message_model = MessageModel(
                    id=message.id,
                    conversation_id=message.conversation_id,
                    role=message.role.value,
                    content=sanitize_html(message.content),
                    timestamp=message.timestamp,
                    token_count=message.token_count,
                    metadata_json=json.dumps(message.metadata) if message.metadata else '{}'
                )
                session.add(message_model)
                logger.debug(f"📝 Created message model with ID: {message.id}")
                
                # Update conversation updated_at and message_count
                conv_model = session.query(ConversationModel).filter(
                    ConversationModel.id == message.conversation_id
                ).first()

                if conv_model:
                    old_count = conv_model.message_count
                    # Flush the session first to ensure the new message is visible in the query
                    session.flush()
                    # Count messages after adding the new one (no +1 needed)
                    new_count = session.query(MessageModel).filter(
                        MessageModel.conversation_id == message.conversation_id
                    ).count()

                    conv_model.updated_at = message.timestamp
                    conv_model.message_count = new_count

                    logger.debug(f"📊 Updated conversation message count: {old_count} -> {new_count}")
                else:
                    logger.warning(f"⚠ Conversation {message.conversation_id} not found for message count update")
                
                # Update FTS index with new message content
                await self._update_message_fts(session, message)
                
                # Verify the message was added by checking the session
                session.flush()  # Ensure the message is written to database
                
                # Count messages for verification
                total_messages = session.query(MessageModel).filter(
                    MessageModel.conversation_id == message.conversation_id
                ).count()
                
                logger.debug(f"✓ Added message to conversation {message.conversation_id} (total messages now: {total_messages})")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to add message to conversation {message.conversation_id}: {e}", exc_info=True)
            return False
    
    async def get_conversation_messages(
        self, 
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                query = session.query(MessageModel).filter(
                    MessageModel.conversation_id == conversation_id
                ).order_by(MessageModel.timestamp.asc())
                
                if offset > 0:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                message_models = query.all()
                return [msg_model.to_domain_model() for msg_model in message_models]
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get messages for {conversation_id}: {e}")
            return []
    
    # --- Search Operations ---
    
    async def search_conversations(self, query: SearchQuery) -> SearchResults:
        """Search conversations using SQLAlchemy ORM with full-text search."""
        start_time = time.time()
        
        try:
            with self.db.get_session() as session:
                # Build base query
                base_query = session.query(ConversationModel)
                
                # Apply text search filters
                base_query = self._apply_text_filters(base_query, query)
                
                # Apply other filters
                base_query = self._apply_other_filters(base_query, query)
                
                # Get total count before pagination
                total_count = base_query.count()
                
                # Apply sorting
                base_query = self._apply_sort_order(base_query, query.sort_order)
                
                # Apply pagination
                if query.offset > 0:
                    base_query = base_query.offset(query.offset)
                if query.limit:
                    base_query = base_query.limit(query.limit)
                
                conv_models = base_query.all()
                
                # Convert to search results
                results = []
                for conv_model in conv_models:
                    # Generate snippet from FTS content
                    snippet = await self._generate_snippet(session, conv_model.id, query.text)
                    
                    result = SearchResult(
                        conversation_id=conv_model.id,
                        title=conv_model.title,
                        snippet=snippet,
                        relevance_score=None,  # TODO: Implement relevance scoring
                        match_count=1
                    )
                    results.append(result)
                
                query_time = (time.time() - start_time) * 1000
                
                return SearchResults(
                    results=results,
                    total_count=total_count,
                    query_time_ms=query_time,
                    offset=query.offset,
                    limit=query.limit
                )
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Search failed: {e}")
            return SearchResults(results=[], total_count=0)
    
    # --- Summary Operations ---
    
    async def save_conversation_summary(self, summary: ConversationSummary) -> bool:
        """Save conversation summary using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                # Check if summary already exists
                existing_summary = session.query(ConversationSummaryModel).filter(
                    ConversationSummaryModel.conversation_id == summary.conversation_id
                ).first()
                
                if existing_summary:
                    # Update existing summary
                    existing_summary.summary = sanitize_html(summary.summary)
                    existing_summary.key_topics = summary.key_topics
                    existing_summary.generated_at = summary.generated_at
                    existing_summary.model_used = summary.model_used
                    existing_summary.confidence_score = summary.confidence_score
                else:
                    # Create new summary
                    summary_model = ConversationSummaryModel(
                        id=summary.id,
                        conversation_id=summary.conversation_id,
                        summary=sanitize_html(summary.summary),
                        key_topics=summary.key_topics,
                        generated_at=summary.generated_at,
                        model_used=summary.model_used,
                        confidence_score=summary.confidence_score
                    )
                    session.add(summary_model)
                
                logger.debug(f"Saved summary for conversation {summary.conversation_id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to save summary: {e}")
            return False
    
    # --- Tag Operations ---
    
    async def get_all_tags(self, min_usage: int = 1) -> List[Dict[str, Any]]:
        """Get all tags with usage counts using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                tags = session.query(TagModel).filter(
                    TagModel.usage_count >= min_usage
                ).order_by(desc(TagModel.usage_count), TagModel.name).all()
                
                return [
                    {
                        'name': tag.name,
                        'usage_count': tag.usage_count,
                        'created_at': tag.created_at.isoformat()
                    }
                    for tag in tags
                ]
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get tags: {e}")
            return []
    
    async def get_conversation_tags(self, conversation_id: str) -> Set[str]:
        """Get tags for a specific conversation using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                tags = session.query(TagModel).join(ConversationTagModel).filter(
                    ConversationTagModel.conversation_id == conversation_id
                ).all()
                
                return {tag.name for tag in tags}
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get tags for {conversation_id}: {e}")
            return set()
    
    # --- Analytics ---
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                stats = {}
                
                # Total conversations by status
                status_counts = session.query(
                    ConversationModel.status,
                    func.count(ConversationModel.id)
                ).group_by(ConversationModel.status).all()
                stats['by_status'] = {status: count for status, count in status_counts}
                
                # Messages per day (last 30 days)
                messages_per_day = session.query(
                    func.date(MessageModel.timestamp).label('date'),
                    func.count(MessageModel.id).label('count')
                ).filter(
                    MessageModel.timestamp >= datetime.utcnow().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) - timedelta(days=30)
                ).group_by(func.date(MessageModel.timestamp)).all()
                stats['messages_per_day'] = [
                    {'date': str(date), 'count': count}
                    for date, count in messages_per_day
                ]
                
                # Most active conversations
                most_active = session.query(
                    ConversationModel.id,
                    ConversationModel.title,
                    func.count(MessageModel.id).label('message_count')
                ).join(MessageModel, ConversationModel.id == MessageModel.conversation_id
                ).filter(ConversationModel.status != 'deleted'
                ).group_by(ConversationModel.id, ConversationModel.title
                ).order_by(desc(func.count(MessageModel.id))
                ).limit(10).all()
                stats['most_active'] = [
                    {'id': conv_id, 'title': title, 'message_count': count}
                    for conv_id, title, count in most_active
                ]
                
                return stats
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get conversation stats: {e}")
            return {}
    
    # --- Helper Methods ---
    
    async def _update_fts_index(self, session, conversation: Conversation):
        """Update full-text search index for conversation."""
        try:
            # Combine all message content
            content = " ".join(sanitize_text(msg.content) for msg in conversation.messages)
            tags = " ".join(conversation.metadata.tags)
            category = conversation.metadata.category or ""
            
            # Check if FTS entry exists
            fts_model = session.query(MessageFTSModel).filter(
                MessageFTSModel.conversation_id == conversation.id
            ).first()
            
            if fts_model:
                # Update existing entry
                fts_model.title = sanitize_text(conversation.title)
                fts_model.content = content
                fts_model.tags = sanitize_text(tags)
                fts_model.category = sanitize_text(category)
            else:
                # Create new entry
                fts_model = MessageFTSModel(
                    conversation_id=conversation.id,
                    title=sanitize_text(conversation.title),
                    content=content,
                    tags=sanitize_text(tags),
                    category=sanitize_text(category)
                )
                session.add(fts_model)
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to update FTS index for {conversation.id}: {e}")
    
    async def _update_message_fts(self, session, message: Message):
        """Update FTS index with new message content."""
        try:
            fts_model = session.query(MessageFTSModel).filter(
                MessageFTSModel.conversation_id == message.conversation_id
            ).first()
            
            if fts_model:
                # Append new message content
                existing_content = fts_model.content or ""
                fts_model.content = f"{existing_content} {sanitize_text(message.content)}".strip()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update message FTS for {message.conversation_id}: {e}")
    
    async def _update_conversation_tags(self, session, conversation_id: str, tags: Set[str]):
        """Update tags for a conversation using SQLAlchemy ORM."""
        try:
            # Remove existing conversation-tag associations
            session.query(ConversationTagModel).filter(
                ConversationTagModel.conversation_id == conversation_id
            ).delete()
            
            for tag_name in tags:
                tag_name = sanitize_text(tag_name)
                if not tag_name:
                    continue
                    
                # Get or create tag
                tag_model = session.query(TagModel).filter(TagModel.name == tag_name).first()
                if not tag_model:
                    tag_model = TagModel(
                        name=tag_name,
                        usage_count=0,
                        created_at=datetime.utcnow()
                    )
                    session.add(tag_model)
                    session.flush()  # Get the ID
                
                # Increment usage count
                tag_model.usage_count += 1
                
                # Create conversation-tag association
                conv_tag = ConversationTagModel(
                    conversation_id=conversation_id,
                    tag_id=tag_model.id
                )
                session.add(conv_tag)
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to update tags for {conversation_id}: {e}")
    
    def _apply_text_filters(self, query, search_query: SearchQuery):
        """Apply text search filters to query."""
        if not search_query.text:
            return query
        
        # For SQLite FTS, we'll use LIKE for simple text search
        # In production, you might want to use SQLite FTS5 or other full-text search
        search_term = f"%{search_query.text}%"
        
        if search_query.scope == SearchScope.TITLE:
            return query.filter(ConversationModel.title.like(search_term))
        elif search_query.scope == SearchScope.CONTENT:
            return query.join(MessageFTSModel).filter(
                MessageFTSModel.content.like(search_term)
            )
        elif search_query.scope == SearchScope.ALL:
            return query.outerjoin(MessageFTSModel).filter(
                or_(
                    ConversationModel.title.like(search_term),
                    MessageFTSModel.content.like(search_term)
                )
            )
        
        return query
    
    def _apply_other_filters(self, query, search_query: SearchQuery):
        """Apply non-text filters to query."""
        if search_query.status:
            query = query.filter(ConversationModel.status == search_query.status.value)
        
        if search_query.created_after:
            query = query.filter(ConversationModel.created_at >= search_query.created_after)
        
        if search_query.created_before:
            query = query.filter(ConversationModel.created_at <= search_query.created_before)
        
        if search_query.updated_after:
            query = query.filter(ConversationModel.updated_at >= search_query.updated_after)
        
        if search_query.updated_before:
            query = query.filter(ConversationModel.updated_at <= search_query.updated_before)
        
        if search_query.category:
            query = query.filter(ConversationModel.category == search_query.category)
        
        if search_query.priority is not None:
            query = query.filter(ConversationModel.priority == search_query.priority)
        
        if search_query.tags:
            # Filter by tags using joins
            query = query.join(ConversationTagModel).join(TagModel).filter(
                TagModel.name.in_(search_query.tags)
            )
        
        return query
    
    def _apply_sort_order(self, query, sort_order: SortOrder):
        """Apply sorting to query."""
        if sort_order == SortOrder.CREATED_ASC:
            return query.order_by(asc(ConversationModel.created_at))
        elif sort_order == SortOrder.CREATED_DESC:
            return query.order_by(desc(ConversationModel.created_at))
        elif sort_order == SortOrder.UPDATED_ASC:
            return query.order_by(asc(ConversationModel.updated_at))
        elif sort_order == SortOrder.UPDATED_DESC:
            return query.order_by(desc(ConversationModel.updated_at))
        elif sort_order == SortOrder.TITLE_ASC:
            return query.order_by(asc(ConversationModel.title))
        elif sort_order == SortOrder.TITLE_DESC:
            return query.order_by(desc(ConversationModel.title))
        else:
            return query.order_by(desc(ConversationModel.updated_at))
    
    async def _generate_snippet(self, session, conversation_id: str, search_term: Optional[str], max_length: int = 200) -> str:
        """Generate search result snippet from FTS content."""
        try:
            fts_model = session.query(MessageFTSModel).filter(
                MessageFTSModel.conversation_id == conversation_id
            ).first()
            
            if not fts_model or not fts_model.content:
                return ""
            
            content = fts_model.content
            if not search_term:
                return content[:max_length] + "..." if len(content) > max_length else content
            
            # Find first occurrence of search term
            lower_content = content.lower()
            lower_term = search_term.lower()
            
            pos = lower_content.find(lower_term)
            if pos == -1:
                return content[:max_length] + "..." if len(content) > max_length else content
            
            # Extract snippet around the match
            start = max(0, pos - max_length // 2)
            end = min(len(content), start + max_length)
            
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."
            
            return snippet
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to generate snippet for {conversation_id}: {e}")
            return ""
    
    def _is_empty_conversation(self, conversation: Conversation) -> bool:
        """Check if a conversation is empty and should not be saved."""
        if not conversation.messages:
            return True
        
        # Only save conversations that have actual USER or ASSISTANT messages (not just system messages)
        non_system_messages = []
        for message in conversation.messages:
            if message.role in (MessageRole.USER, MessageRole.ASSISTANT):
                non_system_messages.append(message)
        
        # Conversation is empty if it has only system messages (no user/assistant interaction)
        # This allows conversations with files to be saved even without user messages yet
        return len(non_system_messages) == 0
    
    async def update_all_conversations_status(self, new_status: ConversationStatus, exclude_statuses: List[ConversationStatus] = None) -> bool:
        """
        Update status for all conversations, optionally excluding certain statuses.
        This is used for atomic operations like setting only one conversation as active.
        """
        try:
            from sqlalchemy import update
            
            with self.db.get_session() as session:
                # Build query to update all conversations
                query = update(ConversationModel).values(status=new_status.value, updated_at=datetime.now())
                
                # Exclude certain statuses if specified
                if exclude_statuses:
                    exclude_values = [status.value for status in exclude_statuses]
                    query = query.where(~ConversationModel.status.in_(exclude_values))
                
                result = session.execute(query)
                session.commit()
                
                updated_count = result.rowcount
                logger.info(f"✓ Updated {updated_count} conversations to status: {new_status.value}")
                
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to update all conversations status: {e}")
            return False
    
    async def _execute_with_session(self, func):
        """
        Execute a function with a database session.
        
        Args:
            func: Function that takes a session as parameter and returns a result
            
        Returns:
            The result of the function, or None if an error occurred
        """
        try:
            with self.db.get_session() as session:
                result = func(session)
                session.commit()
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Database operation failed: {e}")
            return None