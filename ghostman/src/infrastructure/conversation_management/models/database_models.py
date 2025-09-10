"""
SQLAlchemy database models for conversation management.

Provides ORM models for all conversation-related tables with proper relationships,
indexes, and full-text search capabilities.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean, Float, 
    ForeignKey, CheckConstraint, Index, JSON, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.sqlite import TEXT
import bleach

from .enums import ConversationStatus, MessageRole

Base = declarative_base()

# Bleach configuration for sanitizing HTML content
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 
    'code', 'pre', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
}

def sanitize_html(text: str) -> str:
    """Sanitize HTML content using bleach."""
    if not text:
        return text
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)

def sanitize_text(text: str) -> str:
    """Sanitize plain text content."""
    if not text:
        return text
    # Strip dangerous characters and normalize whitespace
    return bleach.clean(text, tags=[], strip=True).strip()


class ConversationModel(Base):
    """SQLAlchemy model for conversations table."""
    
    __tablename__ = 'conversations'
    
    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    message_count = Column(Integer, default=0)
    model_used = Column(String(100))
    tags_json = Column(Text, default='[]')
    category = Column(String(100), index=True)
    priority = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False, index=True)
    metadata_json = Column(Text, default='{}')
    
    # Relationships
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan", lazy="select")
    summary = relationship("ConversationSummaryModel", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    conversation_tags = relationship("ConversationTagModel", back_populates="conversation", cascade="all, delete-orphan")
    fts_entries = relationship("MessageFTSModel", back_populates="conversation", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'pinned', 'deleted')", name='check_status'),
        CheckConstraint("priority BETWEEN -1 AND 1", name='check_priority'),
        Index('idx_conversations_status_updated', 'status', 'updated_at'),
        Index('idx_conversations_category_status', 'category', 'status'),
        Index('idx_conversations_status_only', 'status'),  # Fast status lookups
    )
    
    @validates('title')
    def validate_title(self, key, value):
        """Validate and sanitize conversation title."""
        if not value or not value.strip():
            raise ValueError("Conversation title cannot be empty")
        return sanitize_text(value)[:500]  # Limit length
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate conversation status."""
        if value not in ['active', 'archived', 'pinned', 'deleted']:
            raise ValueError(f"Invalid status: {value}")
        return value
    
    @validates('category')
    def validate_category(self, key, value):
        """Validate and sanitize category."""
        if value:
            return sanitize_text(value)[:100]
        return value
    
    @hybrid_property
    def tags(self) -> Set[str]:
        """Get tags as a set."""
        try:
            return set(json.loads(self.tags_json or '[]'))
        except (json.JSONDecodeError, TypeError):
            return set()
    
    @tags.setter
    def tags(self, value: Set[str]):
        """Set tags from a set."""
        if value:
            # Sanitize each tag
            clean_tags = [sanitize_text(tag)[:50] for tag in value if tag and tag.strip()]
            self.tags_json = json.dumps(list(clean_tags))
        else:
            self.tags_json = '[]'
    
    @hybrid_property
    def conversation_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @conversation_metadata.setter
    def conversation_metadata(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        if value:
            # Sanitize text values in metadata
            clean_metadata = {}
            for k, v in value.items():
                if isinstance(v, str):
                    clean_metadata[k] = sanitize_text(v)
                else:
                    clean_metadata[k] = v
            self.metadata_json = json.dumps(clean_metadata)
        else:
            self.metadata_json = '{}'
    
    def to_domain_model(self):
        """Convert to domain model."""
        from .conversation import Conversation, ConversationMetadata
        
        metadata = ConversationMetadata(
            tags=self.tags,
            category=self.category,
            priority=self.priority,
            model_used=self.model_used,
            custom_fields=self.conversation_metadata
        )
        
        conversation = Conversation(
            id=self.id,
            title=self.title,
            status=ConversationStatus(self.status),
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=metadata
        )
        
        # Set cached message count from database to avoid loading all messages
        conversation._message_count = self.message_count
        
        return conversation


class MessageModel(Base):
    """SQLAlchemy model for messages table."""
    
    __tablename__ = 'messages'
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    token_count = Column(Integer)
    metadata_json = Column(Text, default='{}')
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('system', 'user', 'assistant')", name='check_role'),
        Index('idx_messages_conversation_timestamp', 'conversation_id', 'timestamp'),
        Index('idx_messages_role_timestamp', 'role', 'timestamp'),
    )
    
    @validates('role')
    def validate_role(self, key, value):
        """Validate message role."""
        if value not in ['system', 'user', 'assistant']:
            raise ValueError(f"Invalid role: {value}")
        return value
    
    @validates('content')
    def validate_content(self, key, value):
        """Validate and sanitize message content."""
        if not value:
            raise ValueError("Message content cannot be empty")
        # Sanitize HTML content for messages
        return sanitize_html(value)
    
    @hybrid_property
    def message_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @message_metadata.setter
    def message_metadata(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = '{}'
    
    def to_domain_model(self):
        """Convert to domain model."""
        from .conversation import Message
        
        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            role=MessageRole(self.role),
            content=self.content,
            timestamp=self.timestamp,
            token_count=self.token_count,
            metadata=self.message_metadata
        )


class TagModel(Base):
    """SQLAlchemy model for tags table."""
    
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    usage_count = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    conversation_tags = relationship("ConversationTagModel", back_populates="tag", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index('idx_tags_usage_name', 'usage_count', 'name'),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        """Validate and sanitize tag name."""
        if not value or not value.strip():
            raise ValueError("Tag name cannot be empty")
        return sanitize_text(value)[:100].lower()  # Normalize to lowercase


class ConversationTagModel(Base):
    """SQLAlchemy model for conversation_tags association table."""
    
    __tablename__ = 'conversation_tags'
    
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="conversation_tags")
    tag = relationship("TagModel", back_populates="conversation_tags")


class MessageFTSModel(Base):
    """SQLAlchemy model for full-text search table."""
    
    __tablename__ = 'conversations_fts'
    
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), primary_key=True)
    title = Column(Text)
    content = Column(Text)
    tags = Column(Text)
    category = Column(Text)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="fts_entries")
    
    @validates('title')
    def validate_title(self, key, value):
        """Sanitize FTS title content."""
        return sanitize_text(value) if value else value
    
    @validates('content')
    def validate_content(self, key, value):
        """Sanitize FTS content."""
        return sanitize_text(value) if value else value
    
    @validates('tags')
    def validate_tags(self, key, value):
        """Sanitize FTS tags."""
        return sanitize_text(value) if value else value
    
    @validates('category')
    def validate_category(self, key, value):
        """Sanitize FTS category."""
        return sanitize_text(value) if value else value


class ConversationSummaryModel(Base):
    """SQLAlchemy model for conversation summaries table."""
    
    __tablename__ = 'conversation_summaries'
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False)
    key_topics_json = Column(Text, default='[]')
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    model_used = Column(String(100))
    confidence_score = Column(Float)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="summary")
    
    @validates('summary')
    def validate_summary(self, key, value):
        """Validate and sanitize summary content."""
        if not value or not value.strip():
            raise ValueError("Summary cannot be empty")
        return sanitize_html(value)
    
    @hybrid_property
    def key_topics(self) -> List[str]:
        """Get key topics as list."""
        try:
            topics = json.loads(self.key_topics_json or '[]')
            return [sanitize_text(topic) for topic in topics if topic and topic.strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    
    @key_topics.setter
    def key_topics(self, value: List[str]):
        """Set key topics from list."""
        if value:
            clean_topics = [sanitize_text(topic)[:100] for topic in value if topic and topic.strip()]
            self.key_topics_json = json.dumps(clean_topics)
        else:
            self.key_topics_json = '[]'
    
    def to_domain_model(self):
        """Convert to domain model."""
        from .conversation import ConversationSummary
        
        return ConversationSummary(
            id=self.id,
            conversation_id=self.conversation_id,
            summary=self.summary,
            key_topics=self.key_topics,
            generated_at=self.generated_at,
            model_used=self.model_used,
            confidence_score=self.confidence_score
        )


class ConversationFileModel(Base):
    """SQLAlchemy model for conversation-file associations."""
    
    __tablename__ = 'conversation_files'
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = Column(String(500), nullable=False, index=True)  # File identifier used in RAG pipeline
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000))  # Original file path
    file_size = Column(Integer, default=0)
    file_type = Column(String(100))
    upload_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processing_status = Column(String(20), default='queued', index=True)  # queued, processing, completed, failed
    chunk_count = Column(Integer, default=0)  # Number of chunks created in RAG
    is_enabled = Column(Boolean, default=True, index=True)  # Whether file is enabled for context
    metadata_json = Column(Text, default='{}')
    
    # Relationships
    conversation = relationship("ConversationModel", backref="conversation_files")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("processing_status IN ('queued', 'processing', 'completed', 'failed')", name='check_processing_status'),
        Index('idx_conversation_files_conv_status', 'conversation_id', 'processing_status'),
        Index('idx_conversation_files_conv_enabled', 'conversation_id', 'is_enabled'),
        Index('idx_conversation_files_file_id', 'file_id'),  # For efficient file lookups
    )
    
    @validates('filename')
    def validate_filename(self, key, value):
        """Validate and sanitize filename."""
        if not value or not value.strip():
            raise ValueError("Filename cannot be empty")
        return sanitize_text(value)[:500]
    
    @validates('file_path')
    def validate_file_path(self, key, value):
        """Validate and sanitize file path."""
        if value:
            return sanitize_text(value)[:1000]
        return value
    
    @validates('processing_status')
    def validate_processing_status(self, key, value):
        """Validate processing status."""
        if value not in ['queued', 'processing', 'completed', 'failed']:
            raise ValueError(f"Invalid processing status: {value}")
        return value
    
    @hybrid_property
    def file_metadata(self) -> Dict[str, Any]:
        """Get file metadata as dictionary."""
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @file_metadata.setter
    def file_metadata(self, value: Dict[str, Any]):
        """Set file metadata from dictionary."""
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = '{}'


class SchemaVersionModel(Base):
    """SQLAlchemy model for schema version tracking."""
    
    __tablename__ = 'schema_version'
    
    version = Column(Integer, primary_key=True)
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)