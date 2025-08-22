"""
SQLAlchemy database models for file storage and retrieval metadata.

Provides ORM models for file metadata, vector stores, upload sessions,
and usage analytics with proper relationships and indexing.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean, Float, 
    ForeignKey, CheckConstraint, Index, JSON, LargeBinary,
    UniqueConstraint, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.sqlite import TEXT
import bleach

# Use the same Base as the conversation management system
from ...conversation_management.models.database_models import Base, sanitize_text, sanitize_html

# File-specific sanitization
def sanitize_file_metadata(text: str) -> str:
    """Sanitize file metadata content."""
    if not text:
        return text
    return bleach.clean(text, tags=[], strip=True).strip()


class FileMetadataModel(Base):
    """SQLAlchemy model for file metadata table."""
    
    __tablename__ = 'file_metadata'
    
    id = Column(String(36), primary_key=True)  # UUID
    openai_file_id = Column(String(100), unique=True, nullable=False, index=True)
    original_filename = Column(String(500), nullable=False, index=True)
    file_path = Column(Text, nullable=False)  # Original local file path
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for deduplication
    mime_type = Column(String(100))
    file_extension = Column(String(20), index=True)
    purpose = Column(String(50), nullable=False, index=True)  # assistants, fine-tune, etc.
    
    # OpenAI API specific fields
    openai_status = Column(String(50), index=True)  # uploaded, processed, error
    openai_status_details = Column(Text)
    openai_created_at = Column(DateTime, index=True)
    
    # Local metadata
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    uploaded_by = Column(String(100))  # User identifier
    description = Column(Text)
    tags_json = Column(Text, default='[]')
    custom_metadata_json = Column(Text, default='{}')
    
    # Processing status
    processing_status = Column(String(50), default='pending', index=True)  # pending, processing, completed, failed
    processing_error = Column(Text)
    processing_completed_at = Column(DateTime, index=True)
    
    # Usage tracking
    download_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, index=True)
    
    # Foreign keys
    upload_session_id = Column(String(36), ForeignKey('upload_sessions.id'), index=True)
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name='check_file_size_positive'),
        CheckConstraint("purpose IN ('assistants', 'fine-tune', 'batch', 'vision')", name='check_purpose'),
        CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed')", name='check_processing_status'),
        Index('idx_file_metadata_purpose_status', 'purpose', 'processing_status'),
        Index('idx_file_metadata_uploaded_at_status', 'uploaded_at', 'processing_status'),
        Index('idx_file_metadata_hash_size', 'file_hash', 'file_size_bytes'),  # For deduplication
        Index('idx_file_metadata_deleted', 'is_deleted', 'deleted_at'),
        Index('idx_file_metadata_access_pattern', 'last_accessed_at', 'download_count'),
    )
    
    @validates('original_filename')
    def validate_filename(self, key, value):
        """Validate and sanitize filename."""
        if not value or not value.strip():
            raise ValueError("Filename cannot be empty")
        return sanitize_file_metadata(value)[:500]
    
    @validates('file_path')
    def validate_file_path(self, key, value):
        """Validate file path."""
        if not value or not value.strip():
            raise ValueError("File path cannot be empty")
        return sanitize_file_metadata(value)
    
    @validates('purpose')
    def validate_purpose(self, key, value):
        """Validate file purpose."""
        valid_purposes = ['assistants', 'fine-tune', 'batch', 'vision']
        if value not in valid_purposes:
            raise ValueError(f"Invalid purpose: {value}")
        return value
    
    @validates('description')
    def validate_description(self, key, value):
        """Validate and sanitize description."""
        if value:
            return sanitize_html(value)[:2000]
        return value
    
    @hybrid_property
    def tags(self) -> List[str]:
        """Get tags as a list."""
        try:
            return json.loads(self.tags_json or '[]')
        except (json.JSONDecodeError, TypeError):
            return []
    
    @tags.setter
    def tags(self, value: List[str]):
        """Set tags from a list."""
        if value:
            clean_tags = [sanitize_file_metadata(tag)[:50] for tag in value if tag and tag.strip()]
            self.tags_json = json.dumps(clean_tags)
        else:
            self.tags_json = '[]'
    
    @hybrid_property
    def custom_metadata(self) -> Dict[str, Any]:
        """Get custom metadata as dictionary."""
        try:
            return json.loads(self.custom_metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @custom_metadata.setter
    def custom_metadata(self, value: Dict[str, Any]):
        """Set custom metadata from dictionary."""
        if value:
            clean_metadata = {}
            for k, v in value.items():
                if isinstance(v, str):
                    clean_metadata[k] = sanitize_file_metadata(v)
                else:
                    clean_metadata[k] = v
            self.custom_metadata_json = json.dumps(clean_metadata)
        else:
            self.custom_metadata_json = '{}'
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size_bytes / (1024 * 1024)
    
    def mark_deleted(self):
        """Mark file as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def track_access(self):
        """Track file access."""
        self.download_count += 1
        self.last_accessed_at = datetime.utcnow()


class VectorStoreMetadataModel(Base):
    """SQLAlchemy model for vector store metadata table."""
    
    __tablename__ = 'vector_store_metadata'
    
    id = Column(String(36), primary_key=True)  # UUID
    openai_vector_store_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    
    # OpenAI API specific fields
    openai_status = Column(String(50), index=True)  # expired, in_progress, completed
    openai_created_at = Column(DateTime, index=True)
    openai_expires_at = Column(DateTime, index=True)
    openai_last_active_at = Column(DateTime, index=True)
    usage_bytes = Column(Integer, default=0)
    
    # File counts from OpenAI
    file_count_total = Column(Integer, default=0)
    file_count_completed = Column(Integer, default=0)
    file_count_in_progress = Column(Integer, default=0)
    file_count_failed = Column(Integer, default=0)
    file_count_cancelled = Column(Integer, default=0)
    
    # Local metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_by = Column(String(100))  # User identifier
    tags_json = Column(Text, default='[]')
    custom_metadata_json = Column(Text, default='{}')
    
    # Usage tracking
    query_count = Column(Integer, default=0)
    last_queried_at = Column(DateTime, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, index=True)
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("usage_bytes >= 0", name='check_usage_bytes_positive'),
        CheckConstraint("file_count_total >= 0", name='check_file_count_positive'),
        Index('idx_vector_store_status_created', 'openai_status', 'created_at'),
        Index('idx_vector_store_expires', 'openai_expires_at', 'is_deleted'),
        Index('idx_vector_store_usage', 'last_queried_at', 'query_count'),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        """Validate and sanitize vector store name."""
        if not value or not value.strip():
            raise ValueError("Vector store name cannot be empty")
        return sanitize_file_metadata(value)[:500]
    
    @validates('description')
    def validate_description(self, key, value):
        """Validate and sanitize description."""
        if value:
            return sanitize_html(value)[:2000]
        return value
    
    @hybrid_property
    def tags(self) -> List[str]:
        """Get tags as a list."""
        try:
            return json.loads(self.tags_json or '[]')
        except (json.JSONDecodeError, TypeError):
            return []
    
    @tags.setter
    def tags(self, value: List[str]):
        """Set tags from a list."""
        if value:
            clean_tags = [sanitize_file_metadata(tag)[:50] for tag in value if tag and tag.strip()]
            self.tags_json = json.dumps(clean_tags)
        else:
            self.tags_json = '[]'
    
    @hybrid_property
    def custom_metadata(self) -> Dict[str, Any]:
        """Get custom metadata as dictionary."""
        try:
            return json.loads(self.custom_metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @custom_metadata.setter
    def custom_metadata(self, value: Dict[str, Any]):
        """Set custom metadata from dictionary."""
        if value:
            self.custom_metadata_json = json.dumps(value)
        else:
            self.custom_metadata_json = '{}'
    
    @property
    def usage_mb(self) -> float:
        """Get usage in MB."""
        return self.usage_bytes / (1024 * 1024)
    
    def mark_deleted(self):
        """Mark vector store as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def track_query(self):
        """Track vector store query."""
        self.query_count += 1
        self.last_queried_at = datetime.utcnow()


class VectorStoreFileMetadataModel(Base):
    """SQLAlchemy model for file-vector store relationship table."""
    
    __tablename__ = 'vector_store_file_metadata'
    
    id = Column(String(36), primary_key=True)  # UUID
    vector_store_id = Column(String(36), ForeignKey('vector_store_metadata.id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = Column(String(36), ForeignKey('file_metadata.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # OpenAI API specific fields
    openai_vector_store_file_id = Column(String(100), index=True)
    openai_status = Column(String(50), index=True)  # in_progress, completed, cancelled, failed
    usage_bytes = Column(Integer, default=0)
    last_error_json = Column(Text)
    chunking_strategy_json = Column(Text)
    
    # Relationship metadata
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    added_by = Column(String(100))  # User identifier
    processing_completed_at = Column(DateTime, index=True)
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('vector_store_id', 'file_id', name='uq_vector_store_file'),
        CheckConstraint("usage_bytes >= 0", name='check_vs_file_usage_bytes_positive'),
        Index('idx_vs_file_status_added', 'openai_status', 'added_at'),
        Index('idx_vs_file_processing', 'processing_completed_at', 'openai_status'),
    )
    
    @hybrid_property
    def last_error(self) -> Optional[Dict[str, Any]]:
        """Get last error as dictionary."""
        try:
            return json.loads(self.last_error_json or '{}') if self.last_error_json else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    @last_error.setter
    def last_error(self, value: Optional[Dict[str, Any]]):
        """Set last error from dictionary."""
        if value:
            self.last_error_json = json.dumps(value)
        else:
            self.last_error_json = None
    
    @hybrid_property
    def chunking_strategy(self) -> Optional[Dict[str, Any]]:
        """Get chunking strategy as dictionary."""
        try:
            return json.loads(self.chunking_strategy_json or '{}') if self.chunking_strategy_json else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    @chunking_strategy.setter
    def chunking_strategy(self, value: Optional[Dict[str, Any]]):
        """Set chunking strategy from dictionary."""
        if value:
            self.chunking_strategy_json = json.dumps(value)
        else:
            self.chunking_strategy_json = None

class UploadSessionModel(Base):
    """SQLAlchemy model for upload session tracking."""
    
    __tablename__ = 'upload_sessions'
    
    id = Column(String(36), primary_key=True)  # UUID
    session_name = Column(String(500), index=True)
    session_type = Column(String(50), nullable=False, index=True)
    
    # Session status
    status = Column(String(50), default='started', index=True)
    total_files = Column(Integer, default=0)
    files_completed = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    bytes_uploaded = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, index=True)
    estimated_completion_at = Column(DateTime)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_upload_speed_bps = Column(Float, default=0.0)
    error_message = Column(Text)
    
    # User context
    created_by = Column(String(100))
    metadata_json = Column(Text, default='{}')
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("total_files >= 0", name='check_total_files_positive'),
        CheckConstraint("files_completed >= 0", name='check_files_completed_positive'),
        CheckConstraint("files_failed >= 0", name='check_files_failed_positive'),
        CheckConstraint("total_bytes >= 0", name='check_total_bytes_positive'),
        CheckConstraint("bytes_uploaded >= 0", name='check_bytes_uploaded_positive'),
        CheckConstraint("progress_percentage >= 0.0 AND progress_percentage <= 100.0", name='check_progress_percentage'),
        CheckConstraint("session_type IN ('single_file', 'batch_upload', 'vector_store_creation')", name='check_session_type'),
        CheckConstraint("status IN ('started', 'in_progress', 'completed', 'failed', 'cancelled')", name='check_status'),
        Index('idx_upload_session_status_started', 'status', 'started_at'),
        Index('idx_upload_session_type_status', 'session_type', 'status'),
        Index('idx_upload_session_progress', 'progress_percentage', 'status'),
    )

    @validates('session_name')
    def validate_session_name(self, key, value):
        if value:
            return sanitize_file_metadata(value)[:500]
        return value
    
    @hybrid_property
    def metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = '{}'
    
    def update_progress(self, files_completed: int = None, bytes_uploaded: int = None):
        if files_completed is not None:
            self.files_completed = files_completed
        if bytes_uploaded is not None:
            self.bytes_uploaded = bytes_uploaded
        
        if self.total_files > 0:
            file_progress = (self.files_completed / self.total_files) * 100
        else:
            file_progress = 0
        
        if self.total_bytes > 0:
            byte_progress = (self.bytes_uploaded / self.total_bytes) * 100
        else:
            byte_progress = 0
        
        self.progress_percentage = (file_progress + byte_progress) / 2
    
    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100.0
    
    def mark_failed(self, error_message: str):
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = sanitize_file_metadata(error_message)[:2000]


class FileUsageAnalyticsModel(Base):
    __tablename__ = 'file_usage_analytics'
    
    id = Column(String(36), primary_key=True)
    file_id = Column(String(36), ForeignKey('file_metadata.id', ondelete='CASCADE'), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    
    source_ip = Column(String(45))
    user_agent = Column(String(500))
    referrer = Column(String(1000))
    
    response_time_ms = Column(Integer)
    file_size_at_event = Column(Integer)
    
    metadata_json = Column(Text, default='{}')
    
    __table_args__ = (
        CheckConstraint("response_time_ms >= 0", name='check_response_time_positive'),
        CheckConstraint("file_size_at_event >= 0", name='check_file_size_at_event_positive'),
        CheckConstraint("event_type IN ('upload', 'download', 'view', 'search', 'delete', 'error')", name='check_event_type'),
        Index('idx_file_usage_event_time', 'event_type', 'event_timestamp'),
        Index('idx_file_usage_user_time', 'user_id', 'event_timestamp'),
        Index('idx_file_usage_session', 'session_id', 'event_timestamp'),
        Index('idx_file_usage_performance', 'response_time_ms', 'file_size_at_event'),
    )
    
    @validates('user_agent')
    def validate_user_agent(self, key, value):
        if value:
            return sanitize_file_metadata(value)[:500]
        return value
    
    @validates('referrer')
    def validate_referrer(self, key, value):
        if value:
            return sanitize_file_metadata(value)[:1000]
        return value
    
    @hybrid_property
    def metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = '{}'


class VectorStoreUsageAnalyticsModel(Base):
    __tablename__ = 'vector_store_usage_analytics'
    
    id = Column(String(36), primary_key=True)
    vector_store_id = Column(String(36), ForeignKey('vector_store_metadata.id', ondelete='CASCADE'), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    
    query_text = Column(Text)
    results_count = Column(Integer)
    response_time_ms = Column(Integer)
    
    source_ip = Column(String(45))
    user_agent = Column(String(500))
    
    metadata_json = Column(Text, default='{}')
    
    __table_args__ = (
        CheckConstraint("results_count >= 0", name='check_results_count_positive'),
        CheckConstraint("response_time_ms >= 0", name='check_vs_response_time_positive'),
        CheckConstraint("event_type IN ('query', 'create', 'update', 'delete', 'error')", name='check_vs_event_type'),
        Index('idx_vs_usage_event_time', 'event_type', 'event_timestamp'),
        Index('idx_vs_usage_user_time', 'user_id', 'event_timestamp'),
        Index('idx_vs_usage_performance', 'response_time_ms', 'results_count'),
    )
    
    @validates('query_text')
    def validate_query_text(self, key, value):
        if value:
            return sanitize_file_metadata(value)[:2000]
        return value
    
    @validates('user_agent')
    def validate_user_agent(self, key, value):
        if value:
            return sanitize_file_metadata(value)[:500]
        return value
    
    @hybrid_property
    def metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        if value:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = '{}'


# Add relationships after all models are defined
FileMetadataModel.vector_store_files = relationship("VectorStoreFileMetadataModel", back_populates="file_metadata", cascade="all, delete-orphan")
FileMetadataModel.upload_session = relationship("UploadSessionModel", back_populates="files", foreign_keys=[FileMetadataModel.upload_session_id])
FileMetadataModel.usage_analytics = relationship("FileUsageAnalyticsModel", back_populates="file_metadata", cascade="all, delete-orphan")

VectorStoreMetadataModel.vector_store_files = relationship("VectorStoreFileMetadataModel", back_populates="vector_store_metadata", cascade="all, delete-orphan")
VectorStoreMetadataModel.usage_analytics = relationship("VectorStoreUsageAnalyticsModel", back_populates="vector_store_metadata", cascade="all, delete-orphan")

VectorStoreFileMetadataModel.vector_store_metadata = relationship("VectorStoreMetadataModel", back_populates="vector_store_files")
VectorStoreFileMetadataModel.file_metadata = relationship("FileMetadataModel", back_populates="vector_store_files")

UploadSessionModel.files = relationship("FileMetadataModel", back_populates="upload_session")

FileUsageAnalyticsModel.file_metadata = relationship("FileMetadataModel", back_populates="usage_analytics")

VectorStoreUsageAnalyticsModel.vector_store_metadata = relationship("VectorStoreMetadataModel", back_populates="usage_analytics")
