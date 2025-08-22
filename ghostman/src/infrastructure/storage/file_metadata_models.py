"""
Database models for file metadata storage in the Ghostman file retrieval system.

This module defines SQLAlchemy models for:
- File metadata tracking
- Vector store management
- Upload session tracking
- Usage analytics
- File-vector store relationships

All models follow Ghostman's established database patterns and include
proper indexing, relationships, and data validation.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, JSON,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    create_engine, MetaData
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.sql import func

# Import existing database utilities
try:
    from .database_manager import DatabaseManager
    from .settings_manager import settings
except ImportError:
    # Fallback for testing
    DatabaseManager = None
    settings = None

# Create base class for models
Base = declarative_base()

# Metadata for schema management
metadata = MetaData()


class FileMetadataModel(Base):
    """
    Model for tracking uploaded file metadata.
    
    Stores comprehensive information about files uploaded to OpenAI,
    including local metadata, processing status, and usage analytics.
    """
    __tablename__ = 'file_metadata'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    openai_file_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=True)  # May be None for uploaded files
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 for deduplication
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # OpenAI-specific fields
    openai_purpose = Column(String(50), nullable=False, default='assistants')
    openai_status = Column(String(20), nullable=True)  # OpenAI processing status
    openai_created_at = Column(DateTime, nullable=True)
    
    # Local metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    custom_metadata = Column(JSON, nullable=True)  # Extensible metadata
    
    # Processing status
    status = Column(String(20), nullable=False, default='pending', index=True)
    # Status values: pending, uploading, processing, completed, failed, deleted
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Upload tracking
    upload_session_id = Column(String(36), nullable=True, index=True)
    upload_progress = Column(Float, nullable=False, default=0.0)
    upload_speed_mbps = Column(Float, nullable=True)
    
    # Usage analytics
    download_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime, nullable=True)
    access_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc), index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete
    
    # Relationships
    vector_store_files = relationship("VectorStoreFileMetadataModel", back_populates="file_metadata")
    usage_analytics = relationship("FileUsageAnalyticsModel", back_populates="file_metadata")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('file_size >= 0', name='ck_file_size_positive'),
        CheckConstraint('upload_progress >= 0.0 AND upload_progress <= 100.0', name='ck_upload_progress_range'),
        CheckConstraint('retry_count >= 0', name='ck_retry_count_positive'),
        CheckConstraint('download_count >= 0', name='ck_download_count_positive'),
        CheckConstraint('access_count >= 0', name='ck_access_count_positive'),
        Index('ix_file_metadata_status_created', 'status', 'created_at'),
        Index('ix_file_metadata_hash_size', 'file_hash', 'file_size'),  # For deduplication
        Index('ix_file_metadata_purpose_status', 'openai_purpose', 'status'),
        Index('ix_file_metadata_updated_status', 'updated_at', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'openai_file_id': self.openai_file_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'status': self.status,
            'upload_progress': self.upload_progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': self.tags,
            'description': self.description
        }
    
    def is_deleted(self) -> bool:
        """Check if file is soft deleted."""
        return self.deleted_at is not None
    
    def mark_deleted(self):
        """Mark file as deleted (soft delete)."""
        self.deleted_at = datetime.now(timezone.utc)
        self.status = 'deleted'


class VectorStoreMetadataModel(Base):
    """
    Model for tracking vector store metadata.
    
    Stores information about OpenAI vector stores including
    file counts, usage metrics, and configuration.
    """
    __tablename__ = 'vector_store_metadata'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    openai_vector_store_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # File counts (from OpenAI API)
    total_files = Column(Integer, nullable=False, default=0)
    completed_files = Column(Integer, nullable=False, default=0)
    in_progress_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)
    cancelled_files = Column(Integer, nullable=False, default=0)
    
    # Usage information
    usage_bytes = Column(Integer, nullable=False, default=0)
    query_count = Column(Integer, nullable=False, default=0)
    last_queried = Column(DateTime, nullable=True)
    
    # Configuration
    expires_after = Column(JSON, nullable=True)  # Expiration policy
    openai_metadata = Column(JSON, nullable=True)  # OpenAI metadata
    
    # Status
    status = Column(String(20), nullable=False, default='active', index=True)
    # Status values: active, expired, deleted, error
    
    # Timestamps
    openai_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc), index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    vector_store_files = relationship("VectorStoreFileMetadataModel", back_populates="vector_store_metadata")
    usage_analytics = relationship("VectorStoreUsageAnalyticsModel", back_populates="vector_store_metadata")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('total_files >= 0', name='ck_total_files_positive'),
        CheckConstraint('completed_files >= 0', name='ck_completed_files_positive'),
        CheckConstraint('in_progress_files >= 0', name='ck_in_progress_files_positive'),
        CheckConstraint('failed_files >= 0', name='ck_failed_files_positive'),
        CheckConstraint('cancelled_files >= 0', name='ck_cancelled_files_positive'),
        CheckConstraint('usage_bytes >= 0', name='ck_usage_bytes_positive'),
        CheckConstraint('query_count >= 0', name='ck_query_count_positive'),
        Index('ix_vector_store_status_created', 'status', 'created_at'),
        Index('ix_vector_store_name_status', 'name', 'status'),
        Index('ix_vector_store_usage_updated', 'usage_bytes', 'updated_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'openai_vector_store_id': self.openai_vector_store_id,
            'name': self.name,
            'description': self.description,
            'total_files': self.total_files,
            'completed_files': self.completed_files,
            'in_progress_files': self.in_progress_files,
            'failed_files': self.failed_files,
            'usage_bytes': self.usage_bytes,
            'query_count': self.query_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_completion_percentage(self) -> float:
        """Get file processing completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files / self.total_files) * 100.0
    
    def is_processing_complete(self) -> bool:
        """Check if all files have been processed."""
        return self.total_files > 0 and self.completed_files == self.total_files and self.in_progress_files == 0


class VectorStoreFileMetadataModel(Base):
    """
    Model for tracking file-vector store relationships.
    
    Many-to-many relationship between files and vector stores
    with additional metadata about the association.
    """
    __tablename__ = 'vector_store_file_metadata'
    
    # Composite primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_metadata_id = Column(String(36), ForeignKey('file_metadata.id'), nullable=False, index=True)
    vector_store_metadata_id = Column(String(36), ForeignKey('vector_store_metadata.id'), nullable=False, index=True)
    
    # OpenAI-specific information
    openai_vector_store_file_id = Column(String(100), nullable=True, index=True)
    
    # Processing information
    status = Column(String(20), nullable=False, default='pending', index=True)
    # Status values: pending, in_progress, completed, failed, cancelled
    
    usage_bytes = Column(Integer, nullable=False, default=0)
    chunking_strategy = Column(JSON, nullable=True)  # OpenAI chunking configuration
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    added_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    file_metadata = relationship("FileMetadataModel", back_populates="vector_store_files")
    vector_store_metadata = relationship("VectorStoreMetadataModel", back_populates="vector_store_files")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('file_metadata_id', 'vector_store_metadata_id', 
                        name='uq_file_vector_store'),
        CheckConstraint('usage_bytes >= 0', name='ck_usage_bytes_positive'),
        CheckConstraint('retry_count >= 0', name='ck_retry_count_positive'),
        Index('ix_vs_file_status_added', 'status', 'added_at'),
        Index('ix_vs_file_processed_status', 'processed_at', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'file_metadata_id': self.file_metadata_id,
            'vector_store_metadata_id': self.vector_store_metadata_id,
            'status': self.status,
            'usage_bytes': self.usage_bytes,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }


class UploadSessionModel(Base):
    """
    Model for tracking upload sessions and batch operations.
    
    Groups related file uploads and tracks overall progress
    for batch operations and user experience.
    """
    __tablename__ = 'upload_session'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Session information
    session_type = Column(String(50), nullable=False, index=True)
    # Types: single_file, batch_upload, vector_store_creation
    
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Progress tracking
    total_files = Column(Integer, nullable=False, default=0)
    completed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)
    
    total_bytes = Column(Integer, nullable=False, default=0)
    uploaded_bytes = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    upload_speed_mbps = Column(Float, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default='pending', index=True)
    # Status values: pending, in_progress, completed, failed, cancelled
    
    error_message = Column(Text, nullable=True)
    
    # User context
    user_id = Column(String(100), nullable=True, index=True)
    session_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('total_files >= 0', name='ck_total_files_positive'),
        CheckConstraint('completed_files >= 0', name='ck_completed_files_positive'),
        CheckConstraint('failed_files >= 0', name='ck_failed_files_positive'),
        CheckConstraint('total_bytes >= 0', name='ck_total_bytes_positive'),
        CheckConstraint('uploaded_bytes >= 0', name='ck_uploaded_bytes_positive'),
        Index('ix_upload_session_type_status', 'session_type', 'status'),
        Index('ix_upload_session_started_status', 'started_at', 'status'),
        Index('ix_upload_session_user_started', 'user_id', 'started_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'session_type': self.session_type,
            'name': self.name,
            'total_files': self.total_files,
            'completed_files': self.completed_files,
            'failed_files': self.failed_files,
            'total_bytes': self.total_bytes,
            'uploaded_bytes': self.uploaded_bytes,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def get_progress_percentage(self) -> float:
        """Get upload progress percentage by bytes."""
        if self.total_bytes == 0:
            return 0.0
        return (self.uploaded_bytes / self.total_bytes) * 100.0
    
    def get_file_completion_percentage(self) -> float:
        """Get completion percentage by file count."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files / self.total_files) * 100.0


class FileUsageAnalyticsModel(Base):
    """
    Model for tracking file usage analytics.
    
    Records file access patterns, downloads, and usage
    for analytics and optimization purposes.
    """
    __tablename__ = 'file_usage_analytics'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_metadata_id = Column(String(36), ForeignKey('file_metadata.id'), nullable=False, index=True)
    
    # Event information
    event_type = Column(String(50), nullable=False, index=True)
    # Types: upload, download, view, search, delete, error
    
    event_details = Column(JSON, nullable=True)
    
    # Context information
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    file_size_accessed = Column(Integer, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    file_metadata = relationship("FileMetadataModel", back_populates="usage_analytics")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('response_time_ms >= 0', name='ck_response_time_positive'),
        CheckConstraint('file_size_accessed >= 0', name='ck_file_size_accessed_positive'),
        Index('ix_file_usage_type_timestamp', 'event_type', 'timestamp'),
        Index('ix_file_usage_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_file_usage_session_timestamp', 'session_id', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'file_metadata_id': self.file_metadata_id,
            'event_type': self.event_type,
            'event_details': self.event_details,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class VectorStoreUsageAnalyticsModel(Base):
    """
    Model for tracking vector store usage analytics.
    
    Records vector store queries, performance metrics,
    and usage patterns for optimization.
    """
    __tablename__ = 'vector_store_usage_analytics'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vector_store_metadata_id = Column(String(36), ForeignKey('vector_store_metadata.id'), nullable=False, index=True)
    
    # Query information
    query_type = Column(String(50), nullable=False, index=True)
    # Types: search, create, update, delete, list
    
    query_text = Column(Text, nullable=True)  # Sanitized query text
    result_count = Column(Integer, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Context information
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    vector_store_metadata = relationship("VectorStoreMetadataModel", back_populates="usage_analytics")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('result_count >= 0', name='ck_result_count_positive'),
        CheckConstraint('response_time_ms >= 0', name='ck_response_time_positive'),
        CheckConstraint('tokens_used >= 0', name='ck_tokens_used_positive'),
        Index('ix_vs_usage_type_timestamp', 'query_type', 'timestamp'),
        Index('ix_vs_usage_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_vs_usage_performance', 'response_time_ms', 'result_count'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'vector_store_metadata_id': self.vector_store_metadata_id,
            'query_type': self.query_type,
            'result_count': self.result_count,
            'response_time_ms': self.response_time_ms,
            'tokens_used': self.tokens_used,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class FileStorageDatabaseManager:
    """
    Database manager for file storage metadata.
    
    Extends the existing Ghostman database infrastructure to include
    file management tables while maintaining consistency.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize file storage database manager.
        
        Args:
            db_path: Path to database file. If None, uses default from settings.
        """
        self.db_path = db_path
        if self.db_path is None and settings:
            # Use default database path from settings
            self.db_path = settings.get('database.file_storage_path', 'ghostman_files.db')
        elif self.db_path is None:
            self.db_path = 'ghostman_files.db'
        
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize database connection and create tables.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Create engine
            self.engine = create_engine(
                f'sqlite:///{self.db_path}',
                echo=False,  # Set to True for SQL debugging
                connect_args={'check_same_thread': False}
            )
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Failed to initialize file storage database: {e}")
            return False
    
    def get_session(self):
        """
        Get database session context manager.
        
        Returns:
            SQLAlchemy session context manager.
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.session_factory()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized


# Utility functions for common operations
def create_file_metadata(
    openai_file_id: str,
    filename: str,
    file_size: int,
    file_path: Optional[str] = None,
    file_hash: Optional[str] = None,
    mime_type: Optional[str] = None,
    **kwargs
) -> FileMetadataModel:
    """
    Create a new file metadata record.
    
    Args:
        openai_file_id: OpenAI file ID
        filename: Original filename
        file_size: File size in bytes
        file_path: Local file path (optional)
        file_hash: SHA-256 hash for deduplication (optional)
        mime_type: MIME type (optional)
        **kwargs: Additional metadata
        
    Returns:
        FileMetadataModel instance
    """
    return FileMetadataModel(
        openai_file_id=openai_file_id,
        filename=filename,
        file_size=file_size,
        file_path=file_path,
        file_hash=file_hash,
        mime_type=mime_type,
        **kwargs
    )


def create_vector_store_metadata(
    openai_vector_store_id: str,
    name: str,
    description: Optional[str] = None,
    **kwargs
) -> VectorStoreMetadataModel:
    """
    Create a new vector store metadata record.
    
    Args:
        openai_vector_store_id: OpenAI vector store ID
        name: Vector store name
        description: Optional description
        **kwargs: Additional metadata
        
    Returns:
        VectorStoreMetadataModel instance
    """
    return VectorStoreMetadataModel(
        openai_vector_store_id=openai_vector_store_id,
        name=name,
        description=description,
        **kwargs
    )


def get_file_by_hash(session, file_hash: str) -> Optional[FileMetadataModel]:
    """
    Find file by hash for deduplication.
    
    Args:
        session: Database session
        file_hash: SHA-256 file hash
        
    Returns:
        FileMetadataModel if found, None otherwise
    """
    return session.query(FileMetadataModel).filter_by(
        file_hash=file_hash,
        deleted_at=None  # Only active files
    ).first()


def get_active_vector_stores(session) -> List[VectorStoreMetadataModel]:
    """
    Get all active vector stores.
    
    Args:
        session: Database session
        
    Returns:
        List of active VectorStoreMetadataModel instances
    """
    return session.query(VectorStoreMetadataModel).filter_by(
        status='active',
        deleted_at=None
    ).order_by(VectorStoreMetadataModel.created_at.desc()).all()


def get_upload_statistics(session, hours: int = 24) -> Dict[str, Any]:
    """
    Get upload statistics for the last N hours.
    
    Args:
        session: Database session
        hours: Number of hours to look back
        
    Returns:
        Dictionary with upload statistics
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Query recent uploads
    recent_uploads = session.query(FileMetadataModel).filter(
        FileMetadataModel.created_at >= cutoff_time,
        FileMetadataModel.deleted_at.is_(None)
    ).all()
    
    # Calculate statistics
    total_files = len(recent_uploads)
    total_size = sum(f.file_size for f in recent_uploads)
    completed_files = len([f for f in recent_uploads if f.status == 'completed'])
    failed_files = len([f for f in recent_uploads if f.status == 'failed'])
    
    return {
        'total_files': total_files,
        'total_size_bytes': total_size,
        'total_size_mb': total_size / (1024 * 1024),
        'completed_files': completed_files,
        'failed_files': failed_files,
        'success_rate': (completed_files / total_files * 100) if total_files > 0 else 0,
        'period_hours': hours
    }


# Export main classes and functions
__all__ = [
    'FileMetadataModel',
    'VectorStoreMetadataModel', 
    'VectorStoreFileMetadataModel',
    'UploadSessionModel',
    'FileUsageAnalyticsModel',
    'VectorStoreUsageAnalyticsModel',
    'FileStorageDatabaseManager',
    'create_file_metadata',
    'create_vector_store_metadata',
    'get_file_by_hash',
    'get_active_vector_stores',
    'get_upload_statistics',
    'Base'
]