"""
Database manager extension for file storage integration.

Extends the existing database manager to include file storage tables
and maintains consistency with the conversation management system.
"""

import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from ..conversation_management.repositories.database import DatabaseManager
from .models.file_metadata_models import (
    FileMetadataModel, VectorStoreMetadataModel, VectorStoreFileMetadataModel,
    UploadSessionModel, FileUsageAnalyticsModel, VectorStoreUsageAnalyticsModel
)

logger = logging.getLogger("ghostman.file_storage_db")


class FileStorageDatabaseManager:
    """
    Extended database manager that includes file storage tables.
    
    This class wraps the existing DatabaseManager and ensures that
    file storage tables are created alongside conversation tables.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with shared database manager."""
        self.db_manager = DatabaseManager(db_path)
        self._file_storage_initialized = False
    
    def initialize_file_storage(self) -> bool:
        """Initialize file storage tables in the existing database."""
        try:
            if not self.db_manager.is_initialized:
                # Initialize the main database first
                if not self.db_manager.initialize(run_migrations=True):
                    logger.error("Failed to initialize main database")
                    return False
            
            # Create file storage tables
            from .models.file_metadata_models import Base
            engine = self.db_manager.get_engine()
            
            # Create only the file storage tables
            file_storage_tables = [
                FileMetadataModel.__table__,
                VectorStoreMetadataModel.__table__,
                VectorStoreFileMetadataModel.__table__,
                UploadSessionModel.__table__,
                FileUsageAnalyticsModel.__table__,
                VectorStoreUsageAnalyticsModel.__table__
            ]
            
            for table in file_storage_tables:
                table.create(engine, checkfirst=True)
            
            self._file_storage_initialized = True
            logger.info("✓ File storage tables initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize file storage tables: {e}")
            return False
    
    @contextmanager
    def get_session(self):
        """Get database session from the shared database manager."""
        with self.db_manager.get_session() as session:
            yield session
    
    @property
    def is_initialized(self) -> bool:
        """Check if both main database and file storage are initialized."""
        return self.db_manager.is_initialized and self._file_storage_initialized
    
    def get_engine(self):
        """Get the database engine."""
        return self.db_manager.get_engine()
    
    def create_session(self):
        """Create a new database session."""
        return self.db_manager.create_session()
    
    def vacuum(self):
        """Optimize database."""
        self.db_manager.vacuum()
    
    def close_all_connections(self):
        """Close all database connections."""
        self.db_manager.close_all_connections()
        self._file_storage_initialized = False


def get_shared_database_manager() -> FileStorageDatabaseManager:
    """
    Get a shared database manager instance for file storage.
    
    This ensures that file storage uses the same database as
    conversation management.
    """
    return FileStorageDatabaseManager()


def initialize_file_storage_schema() -> bool:
    """
    Initialize file storage schema in the existing Ghostman database.
    
    This function should be called during application startup to ensure
    file storage tables are available.
    """
    try:
        db_manager = get_shared_database_manager()
        return db_manager.initialize_file_storage()
    except Exception as e:
        logger.error(f"Failed to initialize file storage schema: {e}")
        return False
