"""
File storage infrastructure module.

Provides database models, repositories, and utilities for file metadata storage
in the Ghostman application. Integrates with the existing conversation management
database to provide a unified data layer.

Key Components:
- Database models for file metadata, vector stores, upload sessions, and analytics
- Repository classes for data operations
- Database manager extension for schema initialization
- Migration support for schema updates

Usage:
    from ghostman.src.infrastructure.file_storage import initialize_file_storage_schema
    
    # Initialize file storage tables
    success = initialize_file_storage_schema()
"""

from .database_manager_extension import (
    FileStorageDatabaseManager,
    get_shared_database_manager,
    initialize_file_storage_schema
)

__all__ = [
    'FileStorageDatabaseManager',
    'get_shared_database_manager', 
    'initialize_file_storage_schema'
]

__version__ = '1.0.0'
