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

logger = logging.getLogger("ghostman.conversation_repo")


class ConversationRepository:
    """Repository for conversation data operations using SQLAlchemy ORM."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize repository with database manager."""
        self.db = db_manager or DatabaseManager()
        if not self.db.is_initialized:
            self.db.initialize()
    
    # --- Conversation CRUD Operations ---
    
    async def create_conversation(self, conversation: Conversation) -> bool:
        """Create a new conversation using SQLAlchemy ORM."""
        # Check if conversation is empty and should not be saved
        if self._is_empty_conversation(conversation):
            logger.debug(f"Skipping creation of empty conversation: {conversation.id}")
            return False
            
        try:
            with self.db.get_session() as session:
                # Create conversation model
                conv_model = ConversationModel(
                    id=conversation.id,
                    title=sanitize_text(conversation.title),
                    status=conversation.status.value,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    message_count=len(conversation.messages)
                )
                # Set metadata using the proper property
                conv_model.conversation_metadata = conversation.metadata.to_dict()
                session.add(conv_model)
                
                # Add messages
                for message in conversation.messages:
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
                
                # Update FTS index
                await self._update_fts_index(session, conversation)
                
                # Handle tags
                await self._update_conversation_tags(session, conversation.id, conversation.metadata.tags)
                
                logger.info(f"✓ Created conversation: {conversation.id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to create conversation {conversation.id}: {e}")
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
        # Check if conversation has become empty and should be deleted instead
        if self._is_empty_conversation(conversation):
            logger.debug(f"Conversation {conversation.id} is empty, marking as deleted")
            conversation.delete()
            
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
                    # Hard delete - remove from database (cascading will handle related records)
                    session.delete(conv_model)
                
                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted conversation: {conversation_id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to delete conversation {conversation_id}: {e}")
            return False
    
    async def list_conversations(
        self, 
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_order: SortOrder = SortOrder.UPDATED_DESC
    ) -> List[Conversation]:
        """List conversations with optional filtering using SQLAlchemy ORM."""
        try:
            with self.db.get_session() as session:
                query = session.query(ConversationModel)
                
                # Apply filters
                if status:
                    query = query.filter(ConversationModel.status == status.value)
                
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
                    new_count = session.query(MessageModel).filter(
                        MessageModel.conversation_id == message.conversation_id
                    ).count() + 1  # +1 for the message we're adding
                    
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
        
        # Check if there are any non-system messages or system messages with meaningful content
        meaningful_messages = []
        for message in conversation.messages:
            if message.role != MessageRole.SYSTEM:
                meaningful_messages.append(message)
            elif message.content and message.content.strip():
                meaningful_messages.append(message)
        
        return len(meaningful_messages) == 0
    
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