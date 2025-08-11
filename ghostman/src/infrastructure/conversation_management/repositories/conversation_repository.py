"""
Repository for conversation data operations.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
import time

from ..models.conversation import Conversation, Message, ConversationSummary, ConversationMetadata
from ..models.enums import ConversationStatus, MessageRole, SortOrder, SearchScope
from ..models.search import SearchQuery, SearchResult, SearchResults
from .database import DatabaseManager

logger = logging.getLogger("ghostman.conversation_repo")


class ConversationRepository:
    """Repository for conversation data operations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize repository with database manager."""
        self.db = db_manager or DatabaseManager()
        if not self.db.is_initialized:
            self.db.initialize()
    
    # --- Conversation CRUD Operations ---
    
    async def create_conversation(self, conversation: Conversation) -> bool:
        """Create a new conversation."""
        try:
            with self.db.get_connection() as conn:
                # Insert conversation
                conn.execute("""
                    INSERT INTO conversations (id, title, status, created_at, updated_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    conversation.id,
                    conversation.title,
                    conversation.status.value,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                    json.dumps(conversation.metadata.to_dict())
                ))
                
                # Insert messages
                for message in conversation.messages:
                    await self._insert_message(conn, message)
                
                # Update FTS index
                await self._update_fts_index(conn, conversation)
                
                # Handle tags
                await self._update_conversation_tags(conn, conversation.id, conversation.metadata.tags)
                
                logger.info(f"✅ Created conversation: {conversation.id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create conversation {conversation.id}: {e}")
            return False
    
    async def get_conversation(self, conversation_id: str, include_messages: bool = True) -> Optional[Conversation]:
        """Get conversation by ID."""
        try:
            with self.db.get_connection() as conn:
                # Get conversation
                cursor = conn.execute("""
                    SELECT id, title, status, created_at, updated_at, metadata_json
                    FROM conversations 
                    WHERE id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Parse conversation
                conversation = self._parse_conversation_row(row)
                
                if include_messages:
                    # Load messages
                    conversation.messages = await self._get_conversation_messages(conn, conversation_id)
                    
                    # Load summary
                    conversation.summary = await self._get_conversation_summary(conn, conversation_id)
                
                return conversation
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversation {conversation_id}: {e}")
            return None
    
    async def update_conversation(self, conversation: Conversation) -> bool:
        """Update existing conversation."""
        try:
            with self.db.get_connection() as conn:
                # Update conversation
                conn.execute("""
                    UPDATE conversations 
                    SET title = ?, status = ?, updated_at = ?, metadata_json = ?
                    WHERE id = ?
                """, (
                    conversation.title,
                    conversation.status.value,
                    conversation.updated_at.isoformat(),
                    json.dumps(conversation.metadata.to_dict()),
                    conversation.id
                ))
                
                # Update FTS index
                await self._update_fts_index(conn, conversation)
                
                # Update tags
                await self._update_conversation_tags(conn, conversation.id, conversation.metadata.tags)
                
                logger.debug(f"Updated conversation: {conversation.id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update conversation {conversation.id}: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str, soft_delete: bool = True) -> bool:
        """Delete conversation (soft delete by default)."""
        try:
            with self.db.get_connection() as conn:
                if soft_delete:
                    # Soft delete - just mark as deleted
                    conn.execute("""
                        UPDATE conversations 
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    """, (ConversationStatus.DELETED.value, datetime.now().isoformat(), conversation_id))
                else:
                    # Hard delete - remove from database
                    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                    conn.execute("DELETE FROM conversations_fts WHERE conversation_id = ?", (conversation_id,))
                
                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted conversation: {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to delete conversation {conversation_id}: {e}")
            return False
    
    async def list_conversations(
        self, 
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_order: SortOrder = SortOrder.UPDATED_DESC
    ) -> List[Conversation]:
        """List conversations with optional filtering."""
        try:
            with self.db.get_connection() as conn:
                # Build query
                where_clause = []
                params = []
                
                if status:
                    where_clause.append("status = ?")
                    params.append(status.value)
                
                where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""
                order_sql = self._build_order_clause(sort_order)
                limit_sql = f" LIMIT {limit}" if limit else ""
                offset_sql = f" OFFSET {offset}" if offset > 0 else ""
                
                query = f"""
                    SELECT id, title, status, created_at, updated_at, metadata_json
                    FROM conversations
                    {where_sql}
                    {order_sql}
                    {limit_sql}
                    {offset_sql}
                """
                
                cursor = conn.execute(query, params)
                conversations = []
                
                for row in cursor.fetchall():
                    conversation = self._parse_conversation_row(row)
                    # Load message counts for listing
                    conversation.messages = []  # Don't load full messages for listing
                    conversations.append(conversation)
                
                return conversations
                
        except Exception as e:
            logger.error(f"❌ Failed to list conversations: {e}")
            return []
    
    # --- Message Operations ---
    
    async def add_message(self, message: Message) -> bool:
        """Add message to conversation."""
        try:
            with self.db.get_connection() as conn:
                await self._insert_message(conn, message)
                
                # Update conversation updated_at
                conn.execute("""
                    UPDATE conversations 
                    SET updated_at = ?
                    WHERE id = ?
                """, (message.timestamp.isoformat(), message.conversation_id))
                
                # Update FTS index with new message content
                await self._update_message_fts(conn, message)
                
                logger.debug(f"Added message to conversation {message.conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            return False
    
    async def get_conversation_messages(
        self, 
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation."""
        try:
            with self.db.get_connection() as conn:
                return await self._get_conversation_messages(conn, conversation_id, limit, offset)
        except Exception as e:
            logger.error(f"❌ Failed to get messages for {conversation_id}: {e}")
            return []
    
    # --- Search Operations ---
    
    async def search_conversations(self, query: SearchQuery) -> SearchResults:
        """Search conversations with full-text search and filtering."""
        start_time = time.time()
        
        try:
            with self.db.get_connection() as conn:
                # Build search query
                sql_query, params = self._build_search_query(query)
                
                # Execute search
                cursor = conn.execute(sql_query, params)
                
                results = []
                for row in cursor.fetchall():
                    result = SearchResult(
                        conversation_id=row['id'],
                        title=row['title'],
                        snippet=self._generate_snippet(row.get('content', ''), query.text),
                        relevance_score=row.get('rank'),
                        match_count=1  # TODO: Calculate actual match count
                    )
                    results.append(result)
                
                # Get total count
                count_query = sql_query.replace("SELECT DISTINCT c.*", "SELECT COUNT(DISTINCT c.id)")
                # Remove ORDER BY and LIMIT for count query
                count_query = count_query.split(" ORDER BY")[0]
                cursor = conn.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                query_time = (time.time() - start_time) * 1000
                
                return SearchResults(
                    results=results,
                    total_count=total_count,
                    query_time_ms=query_time,
                    offset=query.offset,
                    limit=query.limit
                )
                
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return SearchResults(results=[], total_count=0)
    
    # --- Summary Operations ---
    
    async def save_conversation_summary(self, summary: ConversationSummary) -> bool:
        """Save conversation summary."""
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_summaries 
                    (id, conversation_id, summary, key_topics_json, generated_at, model_used, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    summary.id,
                    summary.conversation_id,
                    summary.summary,
                    json.dumps(summary.key_topics),
                    summary.generated_at.isoformat(),
                    summary.model_used,
                    summary.confidence_score
                ))
                
                logger.debug(f"Saved summary for conversation {summary.conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save summary: {e}")
            return False
    
    # --- Tag Operations ---
    
    async def get_all_tags(self, min_usage: int = 1) -> List[Dict[str, Any]]:
        """Get all tags with usage counts."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name, usage_count, created_at
                    FROM tags 
                    WHERE usage_count >= ?
                    ORDER BY usage_count DESC, name ASC
                """, (min_usage,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Failed to get tags: {e}")
            return []
    
    async def get_conversation_tags(self, conversation_id: str) -> Set[str]:
        """Get tags for a specific conversation."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT t.name
                    FROM tags t
                    JOIN conversation_tags ct ON t.id = ct.tag_id
                    WHERE ct.conversation_id = ?
                """, (conversation_id,))
                
                return {row['name'] for row in cursor.fetchall()}
                
        except Exception as e:
            logger.error(f"❌ Failed to get tags for {conversation_id}: {e}")
            return set()
    
    # --- Analytics ---
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        try:
            with self.db.get_connection() as conn:
                stats = {}
                
                # Total conversations by status
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM conversations
                    GROUP BY status
                """)
                stats['by_status'] = dict(cursor.fetchall())
                
                # Messages per day (last 30 days)
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM messages
                    WHERE timestamp >= datetime('now', '-30 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """)
                stats['messages_per_day'] = [dict(row) for row in cursor.fetchall()]
                
                # Most active conversations
                cursor = conn.execute("""
                    SELECT c.id, c.title, COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.status != 'deleted'
                    GROUP BY c.id, c.title
                    ORDER BY message_count DESC
                    LIMIT 10
                """)
                stats['most_active'] = [dict(row) for row in cursor.fetchall()]
                
                # Token usage by model
                cursor = conn.execute("""
                    SELECT 
                        JSON_EXTRACT(metadata_json, '$.model_used') as model,
                        SUM(COALESCE(token_count, 0)) as total_tokens,
                        COUNT(*) as message_count
                    FROM messages
                    WHERE JSON_EXTRACT(metadata_json, '$.model_used') IS NOT NULL
                    GROUP BY model
                """)
                stats['token_usage_by_model'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversation stats: {e}")
            return {}
    
    # --- Helper Methods ---
    
    async def _insert_message(self, conn: sqlite3.Connection, message: Message):
        """Insert a message into the database."""
        conn.execute("""
            INSERT INTO messages (id, conversation_id, role, content, timestamp, token_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id,
            message.conversation_id,
            message.role.value,
            message.content,
            message.timestamp.isoformat(),
            message.token_count,
            json.dumps(message.metadata)
        ))
    
    async def _get_conversation_messages(
        self, 
        conn: sqlite3.Connection, 
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation from database."""
        limit_sql = f" LIMIT {limit}" if limit else ""
        offset_sql = f" OFFSET {offset}" if offset > 0 else ""
        
        cursor = conn.execute(f"""
            SELECT id, conversation_id, role, content, timestamp, token_count, metadata_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            {limit_sql}
            {offset_sql}
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            message = Message(
                id=row['id'],
                conversation_id=row['conversation_id'],
                role=MessageRole(row['role']),
                content=row['content'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                token_count=row['token_count'],
                metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {}
            )
            messages.append(message)
        
        return messages
    
    async def _get_conversation_summary(self, conn: sqlite3.Connection, conversation_id: str) -> Optional[ConversationSummary]:
        """Get conversation summary from database."""
        cursor = conn.execute("""
            SELECT id, conversation_id, summary, key_topics_json, generated_at, model_used, confidence_score
            FROM conversation_summaries
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return ConversationSummary(
            id=row['id'],
            conversation_id=row['conversation_id'],
            summary=row['summary'],
            key_topics=json.loads(row['key_topics_json']),
            generated_at=datetime.fromisoformat(row['generated_at']),
            model_used=row['model_used'],
            confidence_score=row['confidence_score']
        )
    
    def _parse_conversation_row(self, row: sqlite3.Row) -> Conversation:
        """Parse conversation from database row."""
        metadata_dict = json.loads(row['metadata_json']) if row['metadata_json'] else {}
        
        return Conversation(
            id=row['id'],
            title=row['title'],
            status=ConversationStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            metadata=ConversationMetadata.from_dict(metadata_dict)
        )
    
    async def _update_fts_index(self, conn: sqlite3.Connection, conversation: Conversation):
        """Update full-text search index for conversation."""
        # Combine all message content
        content = " ".join(msg.content for msg in conversation.messages)
        tags = " ".join(conversation.metadata.tags)
        category = conversation.metadata.category or ""
        
        conn.execute("""
            INSERT OR REPLACE INTO conversations_fts (conversation_id, title, content, tags, category)
            VALUES (?, ?, ?, ?, ?)
        """, (conversation.id, conversation.title, content, tags, category))
    
    async def _update_message_fts(self, conn: sqlite3.Connection, message: Message):
        """Update FTS index with new message content."""
        # Get existing FTS entry
        cursor = conn.execute("""
            SELECT content FROM conversations_fts WHERE conversation_id = ?
        """, (message.conversation_id,))
        
        row = cursor.fetchone()
        existing_content = row['content'] if row else ""
        
        # Append new message content
        updated_content = f"{existing_content} {message.content}".strip()
        
        conn.execute("""
            UPDATE conversations_fts 
            SET content = ?
            WHERE conversation_id = ?
        """, (updated_content, message.conversation_id))
    
    async def _update_conversation_tags(self, conn: sqlite3.Connection, conversation_id: str, tags: Set[str]):
        """Update tags for a conversation."""
        # Remove existing tags
        conn.execute("DELETE FROM conversation_tags WHERE conversation_id = ?", (conversation_id,))
        
        for tag_name in tags:
            # Insert or update tag
            conn.execute("""
                INSERT OR IGNORE INTO tags (name, usage_count, created_at) 
                VALUES (?, 0, ?)
            """, (tag_name, datetime.now().isoformat()))
            
            # Increment usage count
            conn.execute("""
                UPDATE tags SET usage_count = usage_count + 1 WHERE name = ?
            """, (tag_name,))
            
            # Get tag ID
            cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_id = cursor.fetchone()['id']
            
            # Link conversation to tag
            conn.execute("""
                INSERT INTO conversation_tags (conversation_id, tag_id) VALUES (?, ?)
            """, (conversation_id, tag_id))
    
    def _build_search_query(self, query: SearchQuery) -> Tuple[str, List[Any]]:
        """Build SQL search query from SearchQuery object."""
        params = []
        joins = []
        where_conditions = []
        
        # Base query
        base_select = "SELECT DISTINCT c.*"
        if query.text and query.scope in [SearchScope.ALL, SearchScope.CONTENT]:
            joins.append("LEFT JOIN conversations_fts fts ON c.id = fts.conversation_id")
            base_select = "SELECT DISTINCT c.*, fts.rank"
        
        # Text search
        if query.text:
            if query.scope == SearchScope.TITLE:
                where_conditions.append("c.title MATCH ?")
                params.append(query.text)
            elif query.scope == SearchScope.CONTENT:
                where_conditions.append("fts.content MATCH ?")
                params.append(query.text)
            elif query.scope == SearchScope.ALL:
                where_conditions.append("(c.title MATCH ? OR fts.content MATCH ?)")
                params.extend([query.text, query.text])
        
        # Status filter
        if query.status:
            where_conditions.append("c.status = ?")
            params.append(query.status.value)
        
        # Date filters
        if query.created_after:
            where_conditions.append("c.created_at >= ?")
            params.append(query.created_after.isoformat())
        
        if query.created_before:
            where_conditions.append("c.created_at <= ?")
            params.append(query.created_before.isoformat())
        
        if query.updated_after:
            where_conditions.append("c.updated_at >= ?")
            params.append(query.updated_after.isoformat())
        
        if query.updated_before:
            where_conditions.append("c.updated_at <= ?")
            params.append(query.updated_before.isoformat())
        
        # Category filter
        if query.category:
            where_conditions.append("JSON_EXTRACT(c.metadata_json, '$.category') = ?")
            params.append(query.category)
        
        # Priority filter  
        if query.priority is not None:
            where_conditions.append("JSON_EXTRACT(c.metadata_json, '$.priority') = ?")
            params.append(query.priority)
        
        # Tags filter
        if query.tags:
            joins.append("JOIN conversation_tags ct ON c.id = ct.conversation_id")
            joins.append("JOIN tags t ON ct.tag_id = t.id")
            placeholders = ",".join("?" * len(query.tags))
            where_conditions.append(f"t.name IN ({placeholders})")
            params.extend(query.tags)
        
        # Build final query
        joins_sql = " ".join(joins)
        where_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        order_sql = self._build_order_clause(query.sort_order)
        
        limit_sql = ""
        if query.limit:
            limit_sql = f" LIMIT {query.limit}"
            if query.offset > 0:
                limit_sql += f" OFFSET {query.offset}"
        
        final_query = f"""
            {base_select}
            FROM conversations c
            {joins_sql}
            {where_sql}
            {order_sql}
            {limit_sql}
        """
        
        return final_query.strip(), params
    
    def _build_order_clause(self, sort_order: SortOrder) -> str:
        """Build ORDER BY clause from sort order."""
        order_map = {
            SortOrder.CREATED_ASC: "ORDER BY c.created_at ASC",
            SortOrder.CREATED_DESC: "ORDER BY c.created_at DESC", 
            SortOrder.UPDATED_ASC: "ORDER BY c.updated_at ASC",
            SortOrder.UPDATED_DESC: "ORDER BY c.updated_at DESC",
            SortOrder.TITLE_ASC: "ORDER BY c.title ASC",
            SortOrder.TITLE_DESC: "ORDER BY c.title DESC",
        }
        return order_map.get(sort_order, "ORDER BY c.updated_at DESC")
    
    def _generate_snippet(self, content: str, search_term: Optional[str], max_length: int = 200) -> str:
        """Generate search result snippet."""
        if not search_term or not content:
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