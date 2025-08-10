# Conversation Memory System Implementation Plan

## Overview

This document outlines the comprehensive implementation plan for Ghostman's conversation memory system, which manages AI conversations with token-based limits, intelligent storage, and efficient retrieval. The system is designed to maintain context while respecting API token constraints.

## Memory System Architecture

### Core Components
1. **Token Counter**: Accurate token counting for different AI models
2. **Memory Manager**: Intelligent conversation trimming and summarization
3. **Storage Engine**: Efficient local storage with SQLite and JSON
4. **Search System**: Full-text and semantic search capabilities
5. **Archive Manager**: Long-term storage and cleanup
6. **Logging Integration**: Comprehensive logging of memory operations, performance metrics, and data management events

## Implementation Details

### 1. Conversation Models

**File**: `ghostman/src/domain/models/conversation.py`

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import tiktoken

class TokenCounter:
    """Utility class for accurate token counting."""
    
    _encoders = {}
    
    @classmethod
    def get_encoder(cls, model: str = "gpt-3.5-turbo"):
        """Get or create encoder for model."""
        if model not in cls._encoders:
            try:
                cls._encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
        return cls._encoders[model]
    
    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in text for specified model."""
        encoder = cls.get_encoder(model)
        return len(encoder.encode(text))
    
    @classmethod
    def count_message_tokens(cls, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in a list of messages."""
        encoder = cls.get_encoder(model)
        
        # Token overhead per message (role, content structure)
        tokens_per_message = 3
        tokens_per_name = 1
        
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(encoder.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        
        # Every reply is primed with <|start|>assistant<|message|>
        num_tokens += 3
        
        return num_tokens

class Message(BaseModel):
    """Individual message in a conversation."""
    
    id: UUID = Field(default_factory=uuid4)
    role: str = Field(..., regex="^(system|user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields for memory management
    importance_score: float = Field(default=1.0, ge=0.0, le=10.0)
    is_summary: bool = Field(default=False)
    summarized_message_ids: List[UUID] = Field(default_factory=list)
    
    def calculate_tokens(self, model: str = "gpt-3.5-turbo") -> int:
        """Calculate and cache token count."""
        self.token_count = TokenCounter.count_tokens(self.content, model)
        return self.token_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role,
            "content": self.content
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class Conversation(BaseModel):
    """Complete conversation with memory management."""
    
    id: UUID = Field(default_factory=uuid4)
    title: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Token management
    max_tokens: int = Field(default=4000, ge=1000, le=128000)
    model: str = Field(default="gpt-3.5-turbo")
    current_token_count: int = Field(default=0)
    
    # Memory management settings
    memory_strategy: str = Field(default="sliding_window")  # sliding_window, summarization, hybrid
    window_size: int = Field(default=10)  # For sliding window
    summary_threshold: int = Field(default=2000)  # Tokens before summarization
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the conversation."""
        message = Message(role=role, content=content, **kwargs)
        message.calculate_tokens(self.model)
        
        self.messages.append(message)
        self.current_token_count += message.token_count or 0
        self.updated_at = datetime.utcnow()
        
        # Check if memory management is needed
        if self.current_token_count > self.max_tokens:
            self.manage_memory()
        
        return message
    
    def manage_memory(self) -> None:
        """Apply memory management strategy."""
        if self.memory_strategy == "sliding_window":
            self._apply_sliding_window()
        elif self.memory_strategy == "summarization":
            self._apply_summarization()
        elif self.memory_strategy == "hybrid":
            self._apply_hybrid_strategy()
    
    def _apply_sliding_window(self) -> None:
        """Keep only recent messages within window."""
        if len(self.messages) <= self.window_size:
            return
        
        # Keep system messages and recent messages
        system_messages = [m for m in self.messages if m.role == "system"]
        recent_messages = self.messages[-self.window_size:]
        
        self.messages = system_messages + recent_messages
        self._recalculate_tokens()
    
    def _apply_summarization(self) -> None:
        """Summarize older messages when threshold exceeded."""
        if self.current_token_count <= self.summary_threshold:
            return
        
        # Find messages to summarize (keep recent ones)
        messages_to_keep = []
        messages_to_summarize = []
        recent_tokens = 0
        
        for message in reversed(self.messages):
            if recent_tokens < self.max_tokens // 2:
                messages_to_keep.insert(0, message)
                recent_tokens += message.token_count or 0
            else:
                messages_to_summarize.insert(0, message)
        
        if messages_to_summarize:
            # Create summary (placeholder - would use AI in production)
            summary = self._create_summary(messages_to_summarize)
            self.messages = [summary] + messages_to_keep
            self._recalculate_tokens()
    
    def _apply_hybrid_strategy(self) -> None:
        """Combine sliding window with summarization."""
        # First apply summarization to older messages
        if self.current_token_count > self.summary_threshold:
            self._apply_summarization()
        
        # Then apply sliding window to recent messages
        if len(self.messages) > self.window_size:
            self._apply_sliding_window()
    
    def _create_summary(self, messages: List[Message]) -> Message:
        """Create a summary message from multiple messages."""
        # In production, this would call the AI API to generate a summary
        summary_content = f"[Summary of {len(messages)} previous messages]\n"
        summary_content += "Key points discussed:\n"
        
        # Extract key points (simplified version)
        for msg in messages[-3:]:  # Last 3 messages as example
            if msg.role != "system":
                summary_content += f"- {msg.role}: {msg.content[:50]}...\n"
        
        summary_message = Message(
            role="system",
            content=summary_content,
            is_summary=True,
            summarized_message_ids=[m.id for m in messages]
        )
        summary_message.calculate_tokens(self.model)
        
        return summary_message
    
    def _recalculate_tokens(self) -> None:
        """Recalculate total token count."""
        self.current_token_count = sum(
            m.token_count or 0 for m in self.messages
        )
    
    def get_context_messages(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get messages formatted for API call within token limit."""
        max_tokens = max_tokens or self.max_tokens
        
        result = []
        token_count = 0
        
        # Always include system messages first
        for message in self.messages:
            if message.role == "system":
                result.append(message.to_dict())
                token_count += message.token_count or 0
        
        # Add other messages in reverse order (most recent first)
        for message in reversed(self.messages):
            if message.role != "system":
                message_tokens = message.token_count or 0
                if token_count + message_tokens <= max_tokens:
                    result.insert(len([m for m in result if m['role'] == 'system']), 
                                message.to_dict())
                    token_count += message_tokens
                else:
                    break
        
        return result
    
    def estimate_response_tokens(self) -> int:
        """Estimate tokens needed for AI response."""
        # Use historical average or heuristic
        avg_response_tokens = 150
        
        # Adjust based on recent message patterns
        recent_assistant_messages = [
            m for m in self.messages[-5:] 
            if m.role == "assistant"
        ]
        
        if recent_assistant_messages:
            avg_response_tokens = sum(
                m.token_count or 0 for m in recent_assistant_messages
            ) // len(recent_assistant_messages)
        
        return min(avg_response_tokens * 2, 500)  # Cap at 500 tokens
    
    def can_fit_response(self) -> bool:
        """Check if there's room for an AI response."""
        estimated_response = self.estimate_response_tokens()
        return self.current_token_count + estimated_response <= self.max_tokens
    
    def generate_title(self) -> str:
        """Generate a title from the first user message."""
        if self.title:
            return self.title
        
        for message in self.messages:
            if message.role == "user":
                # Use first 50 characters of first user message
                self.title = message.content[:50]
                if len(message.content) > 50:
                    self.title += "..."
                return self.title
        
        self.title = f"Conversation {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return self.title
```

### 2. Conversation Storage Engine

**File**: `ghostman/src/infrastructure/storage/conversation_store.py`

```python
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager

class ConversationStore:
    """SQLite-based conversation storage with optimizations."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self._init_database()
        self._optimize_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    model TEXT DEFAULT 'gpt-3.5-turbo',
                    memory_strategy TEXT DEFAULT 'sliding_window',
                    metadata TEXT,  -- JSON
                    tags TEXT,      -- JSON array
                    is_archived BOOLEAN DEFAULT 0
                )
            """)
            
            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INTEGER,
                    importance_score REAL DEFAULT 1.0,
                    is_summary BOOLEAN DEFAULT 0,
                    metadata TEXT,  -- JSON
                    sequence_number INTEGER,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                )
            """)
            
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(is_archived)")
            
            # Full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
                USING fts5(conversation_id, role, content, timestamp)
            """)
            
            # Triggers to keep FTS updated
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS messages_ai 
                AFTER INSERT ON messages 
                BEGIN
                    INSERT INTO messages_fts(conversation_id, role, content, timestamp)
                    VALUES (new.conversation_id, new.role, new.content, new.timestamp);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS messages_ad 
                AFTER DELETE ON messages 
                BEGIN
                    DELETE FROM messages_fts 
                    WHERE rowid = old.rowid;
                END
            """)
    
    def _optimize_database(self):
        """Apply database optimizations."""
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("ANALYZE")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_conversation(self, conversation: 'Conversation') -> None:
        """Save or update a conversation."""
        with self._get_connection() as conn:
            # Check if conversation exists
            existing = conn.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (str(conversation.id),)
            ).fetchone()
            
            if existing:
                # Update existing conversation
                conn.execute("""
                    UPDATE conversations 
                    SET title = ?, updated_at = ?, message_count = ?, 
                        total_tokens = ?, model = ?, memory_strategy = ?,
                        metadata = ?, tags = ?
                    WHERE id = ?
                """, (
                    conversation.title,
                    conversation.updated_at,
                    len(conversation.messages),
                    conversation.current_token_count,
                    conversation.model,
                    conversation.memory_strategy,
                    json.dumps(conversation.metadata),
                    json.dumps(conversation.tags),
                    str(conversation.id)
                ))
                
                # Delete existing messages (we'll re-insert all)
                conn.execute(
                    "DELETE FROM messages WHERE conversation_id = ?",
                    (str(conversation.id),)
                )
            else:
                # Insert new conversation
                conn.execute("""
                    INSERT INTO conversations 
                    (id, title, created_at, updated_at, message_count, 
                     total_tokens, model, memory_strategy, metadata, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(conversation.id),
                    conversation.title,
                    conversation.created_at,
                    conversation.updated_at,
                    len(conversation.messages),
                    conversation.current_token_count,
                    conversation.model,
                    conversation.memory_strategy,
                    json.dumps(conversation.metadata),
                    json.dumps(conversation.tags)
                ))
            
            # Insert messages
            for idx, message in enumerate(conversation.messages):
                conn.execute("""
                    INSERT INTO messages 
                    (id, conversation_id, role, content, timestamp, 
                     token_count, importance_score, is_summary, metadata, sequence_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(message.id),
                    str(conversation.id),
                    message.role,
                    message.content,
                    message.timestamp,
                    message.token_count,
                    message.importance_score,
                    message.is_summary,
                    json.dumps(message.metadata),
                    idx
                ))
    
    def load_conversation(self, conversation_id: str) -> Optional['Conversation']:
        """Load a conversation by ID."""
        from ...domain.models.conversation import Conversation, Message
        
        with self._get_connection() as conn:
            # Load conversation
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,)
            ).fetchone()
            
            if not conv_row:
                return None
            
            # Load messages
            message_rows = conn.execute(
                """SELECT * FROM messages 
                   WHERE conversation_id = ? 
                   ORDER BY sequence_number""",
                (conversation_id,)
            ).fetchall()
            
            # Reconstruct conversation
            messages = []
            for row in message_rows:
                message = Message(
                    id=row['id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    token_count=row['token_count'],
                    importance_score=row['importance_score'],
                    is_summary=bool(row['is_summary']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                messages.append(message)
            
            conversation = Conversation(
                id=conv_row['id'],
                title=conv_row['title'],
                messages=messages,
                created_at=datetime.fromisoformat(conv_row['created_at']),
                updated_at=datetime.fromisoformat(conv_row['updated_at']),
                current_token_count=conv_row['total_tokens'],
                model=conv_row['model'],
                memory_strategy=conv_row['memory_strategy'],
                metadata=json.loads(conv_row['metadata']) if conv_row['metadata'] else {},
                tags=json.loads(conv_row['tags']) if conv_row['tags'] else []
            )
            
            return conversation
    
    def list_conversations(self, 
                          limit: int = 50, 
                          offset: int = 0,
                          include_archived: bool = False) -> List[Dict[str, Any]]:
        """List conversations with pagination."""
        with self._get_connection() as conn:
            query = """
                SELECT id, title, created_at, updated_at, 
                       message_count, total_tokens, tags
                FROM conversations
                WHERE is_archived = ? OR ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """
            
            rows = conn.execute(
                query,
                (0 if not include_archived else 1, include_archived, limit, offset)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def search_conversations(self, 
                            query: str, 
                            limit: int = 20) -> List[Dict[str, Any]]:
        """Search conversations using full-text search."""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT DISTINCT c.id, c.title, c.updated_at,
                       snippet(messages_fts, 2, '<b>', '</b>', '...', 32) as snippet
                FROM messages_fts 
                JOIN conversations c ON messages_fts.conversation_id = c.id
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            
            return [dict(row) for row in results]
    
    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,)
            )
    
    def archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE conversations SET is_archived = 1 WHERE id = ?",
                (conversation_id,)
            )
    
    def cleanup_old_conversations(self, days: int = 90) -> int:
        """Delete conversations older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self._get_connection() as conn:
            result = conn.execute(
                """DELETE FROM conversations 
                   WHERE updated_at < ? AND is_archived = 0""",
                (cutoff_date,)
            )
            
            deleted_count = result.rowcount
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            
            return deleted_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}
            
            # Total conversations
            stats['total_conversations'] = conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            
            # Total messages
            stats['total_messages'] = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]
            
            # Total tokens
            stats['total_tokens'] = conn.execute(
                "SELECT SUM(total_tokens) FROM conversations"
            ).fetchone()[0] or 0
            
            # Database size
            stats['database_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
            
            # Active conversations (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            stats['active_conversations'] = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE updated_at > ?",
                (week_ago,)
            ).fetchone()[0]
            
            return stats
```

### 3. Memory Service Implementation

**File**: `ghostman/src/domain/services/memory_service.py`

```python
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from pathlib import Path
import logging
from datetime import datetime, timedelta

from ..models.conversation import Conversation, Message
from ...infrastructure.storage.conversation_store import ConversationStore

class MemoryService(QObject):
    """Service for managing conversation memory and persistence."""
    
    # Signals
    conversation_saved = pyqtSignal(str)  # conversation_id
    conversation_loaded = pyqtSignal(str)  # conversation_id
    memory_managed = pyqtSignal(str, int)  # conversation_id, tokens_freed
    storage_cleaned = pyqtSignal(int)  # conversations_deleted
    
    def __init__(self, storage_path: Path):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.storage = ConversationStore(storage_path / "conversations.db")
        
        # In-memory cache
        self.active_conversations: Dict[str, Conversation] = {}
        self.current_conversation_id: Optional[str] = None
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_conversations)
        self.auto_save_timer.start(30000)  # Save every 30 seconds
        
        # Cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_old_data)
        self.cleanup_timer.start(3600000)  # Cleanup every hour
    
    def create_conversation(self, 
                          model: str = "gpt-3.5-turbo",
                          max_tokens: int = 4000,
                          memory_strategy: str = "hybrid") -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            model=model,
            max_tokens=max_tokens,
            memory_strategy=memory_strategy
        )
        
        # Add to cache
        self.active_conversations[str(conversation.id)] = conversation
        self.current_conversation_id = str(conversation.id)
        
        # Save to storage
        self.storage.save_conversation(conversation)
        self.conversation_saved.emit(str(conversation.id))
        
        self.logger.info(f"Created new conversation: {conversation.id}")
        return conversation
    
    def get_current_conversation(self) -> Optional[Conversation]:
        """Get the current active conversation."""
        if self.current_conversation_id:
            return self.active_conversations.get(self.current_conversation_id)
        return None
    
    def set_current_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Set the current active conversation."""
        # Load if not in cache
        if conversation_id not in self.active_conversations:
            conversation = self.storage.load_conversation(conversation_id)
            if conversation:
                self.active_conversations[conversation_id] = conversation
                self.conversation_loaded.emit(conversation_id)
        
        if conversation_id in self.active_conversations:
            self.current_conversation_id = conversation_id
            return self.active_conversations[conversation_id]
        
        return None
    
    def add_message(self, 
                   role: str, 
                   content: str,
                   conversation_id: Optional[str] = None) -> Message:
        """Add a message to a conversation."""
        # Use current conversation if not specified
        if not conversation_id:
            conversation_id = self.current_conversation_id
        
        if not conversation_id:
            # Create new conversation if none exists
            conversation = self.create_conversation()
            conversation_id = str(conversation.id)
        
        conversation = self.active_conversations.get(conversation_id)
        if not conversation:
            conversation = self.set_current_conversation(conversation_id)
        
        if conversation:
            # Add message
            message = conversation.add_message(role, content)
            
            # Check if memory management occurred
            if conversation.current_token_count > conversation.max_tokens * 0.8:
                tokens_before = conversation.current_token_count
                conversation.manage_memory()
                tokens_freed = tokens_before - conversation.current_token_count
                if tokens_freed > 0:
                    self.memory_managed.emit(conversation_id, tokens_freed)
            
            # Mark for saving
            self._mark_conversation_dirty(conversation_id)
            
            return message
        
        raise ValueError(f"Conversation {conversation_id} not found")
    
    def get_context_for_api(self, 
                           conversation_id: Optional[str] = None,
                           max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation context formatted for API call."""
        if not conversation_id:
            conversation_id = self.current_conversation_id
        
        conversation = self.active_conversations.get(conversation_id)
        if conversation:
            return conversation.get_context_messages(max_tokens)
        
        return []
    
    def save_conversation(self, conversation_id: Optional[str] = None) -> None:
        """Save a specific conversation to storage."""
        if not conversation_id:
            conversation_id = self.current_conversation_id
        
        if conversation_id and conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            self.storage.save_conversation(conversation)
            self.conversation_saved.emit(conversation_id)
            self.logger.info(f"Saved conversation: {conversation_id}")
    
    def auto_save_conversations(self) -> None:
        """Auto-save all dirty conversations."""
        for conversation_id, conversation in self.active_conversations.items():
            if self._is_conversation_dirty(conversation_id):
                self.storage.save_conversation(conversation)
                self._clear_dirty_flag(conversation_id)
        
        self.logger.debug(f"Auto-saved {len(self.active_conversations)} conversations")
    
    def list_conversations(self, 
                          limit: int = 50,
                          include_archived: bool = False) -> List[Dict[str, Any]]:
        """List available conversations."""
        return self.storage.list_conversations(
            limit=limit,
            include_archived=include_archived
        )
    
    def search_conversations(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search conversations."""
        return self.storage.search_conversations(query, limit)
    
    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        # Remove from cache
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
        
        # Remove from storage
        self.storage.delete_conversation(conversation_id)
        
        # Update current conversation if needed
        if self.current_conversation_id == conversation_id:
            self.current_conversation_id = None
        
        self.logger.info(f"Deleted conversation: {conversation_id}")
    
    def archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation."""
        # Remove from active cache
        if conversation_id in self.active_conversations:
            # Save before removing from cache
            self.save_conversation(conversation_id)
            del self.active_conversations[conversation_id]
        
        # Archive in storage
        self.storage.archive_conversation(conversation_id)
        
        self.logger.info(f"Archived conversation: {conversation_id}")
    
    def cleanup_old_data(self) -> None:
        """Clean up old conversations and data."""
        # Clean up conversations older than 90 days
        deleted_count = self.storage.cleanup_old_conversations(days=90)
        
        if deleted_count > 0:
            self.storage_cleaned.emit(deleted_count)
            self.logger.info(f"Cleaned up {deleted_count} old conversations")
        
        # Clear inactive conversations from cache
        inactive_threshold = datetime.utcnow() - timedelta(hours=1)
        
        for conv_id in list(self.active_conversations.keys()):
            conversation = self.active_conversations[conv_id]
            if conversation.updated_at < inactive_threshold:
                # Save before removing from cache
                self.save_conversation(conv_id)
                del self.active_conversations[conv_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        stats = self.storage.get_statistics()
        
        # Add cache statistics
        stats['cached_conversations'] = len(self.active_conversations)
        stats['total_cached_tokens'] = sum(
            conv.current_token_count 
            for conv in self.active_conversations.values()
        )
        
        return stats
    
    def export_conversation(self, 
                           conversation_id: str,
                           format: str = "json") -> str:
        """Export a conversation in specified format."""
        conversation = self.active_conversations.get(conversation_id)
        if not conversation:
            conversation = self.storage.load_conversation(conversation_id)
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if format == "json":
            return conversation.json(indent=2)
        elif format == "markdown":
            return self._export_as_markdown(conversation)
        elif format == "text":
            return self._export_as_text(conversation)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_as_markdown(self, conversation: Conversation) -> str:
        """Export conversation as Markdown."""
        md = f"# {conversation.generate_title()}\n\n"
        md += f"*Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M')}*\n\n"
        
        for message in conversation.messages:
            role_label = {
                "system": "🔧 System",
                "user": "👤 User",
                "assistant": "🤖 Assistant"
            }.get(message.role, message.role)
            
            md += f"## {role_label}\n\n"
            md += f"{message.content}\n\n"
            md += f"*{message.timestamp.strftime('%H:%M:%S')}*\n\n"
            md += "---\n\n"
        
        return md
    
    def _export_as_text(self, conversation: Conversation) -> str:
        """Export conversation as plain text."""
        text = f"{conversation.generate_title()}\n"
        text += f"{'=' * 50}\n\n"
        
        for message in conversation.messages:
            text += f"{message.role.upper()}: {message.content}\n"
            text += f"[{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]\n\n"
        
        return text
    
    # Dirty tracking for auto-save
    _dirty_conversations = set()
    
    def _mark_conversation_dirty(self, conversation_id: str):
        """Mark conversation as needing save."""
        self._dirty_conversations.add(conversation_id)
    
    def _is_conversation_dirty(self, conversation_id: str) -> bool:
        """Check if conversation needs saving."""
        return conversation_id in self._dirty_conversations
    
    def _clear_dirty_flag(self, conversation_id: str):
        """Clear dirty flag after saving."""
        self._dirty_conversations.discard(conversation_id)
    
    def shutdown(self):
        """Clean shutdown of memory service."""
        # Stop timers
        self.auto_save_timer.stop()
        self.cleanup_timer.stop()
        
        # Save all conversations
        for conversation_id in self.active_conversations:
            self.save_conversation(conversation_id)
        
        self.logger.info("Memory service shut down")
```

### 4. Integration with Main Application

**File**: `ghostman/src/app/conversation_manager.py`

```python
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, AsyncIterator
import asyncio
import logging

from ..domain.services.memory_service import MemoryService
from ..domain.services.ai_service import AIService
from ..domain.models.conversation import Conversation, Message

class ConversationManager(QObject):
    """Manages conversation flow between UI, memory, and AI service."""
    
    # Signals
    ai_request_started = pyqtSignal()
    ai_response_received = pyqtSignal(str)
    ai_response_chunk = pyqtSignal(str)
    ai_error = pyqtSignal(str)
    conversation_changed = pyqtSignal(str)  # conversation_id
    
    def __init__(self, memory_service: MemoryService, ai_service: AIService):
        super().__init__()
        self.memory_service = memory_service
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)
        
        # Current response tracking
        self.is_processing = False
        self.current_response = ""
    
    async def send_message(self, user_message: str) -> None:
        """Send a user message and get AI response."""
        if self.is_processing:
            self.logger.warning("Already processing a message")
            return
        
        try:
            self.is_processing = True
            self.ai_request_started.emit()
            
            # Add user message to conversation
            user_msg = self.memory_service.add_message("user", user_message)
            
            # Get context for API
            context = self.memory_service.get_context_for_api()
            
            # Get AI response (streaming)
            self.current_response = ""
            async for chunk in self.ai_service.send_message_stream(context):
                self.current_response += chunk
                self.ai_response_chunk.emit(chunk)
            
            # Add complete response to conversation
            self.memory_service.add_message("assistant", self.current_response)
            
            self.ai_response_received.emit(self.current_response)
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.ai_error.emit(str(e))
        
        finally:
            self.is_processing = False
    
    def start_new_conversation(self) -> Conversation:
        """Start a new conversation."""
        conversation = self.memory_service.create_conversation()
        self.conversation_changed.emit(str(conversation.id))
        return conversation
    
    def switch_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Switch to a different conversation."""
        conversation = self.memory_service.set_current_conversation(conversation_id)
        if conversation:
            self.conversation_changed.emit(conversation_id)
        return conversation
    
    def get_current_conversation(self) -> Optional[Conversation]:
        """Get current conversation."""
        return self.memory_service.get_current_conversation()
    
    def update_ai_settings(self):
        """Update AI service with new settings."""
        # This would reload AI service configuration
        pass
```

This comprehensive conversation memory system provides efficient token management, intelligent storage, and seamless integration with the AI service while maintaining conversation context within API limits.