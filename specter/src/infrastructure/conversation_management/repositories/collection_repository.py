"""
Simple tag-based collection repository.

Collections are just tags on conversation_files. No complex schemas or relationships.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..models.database_models import ConversationFileModel
from .database import DatabaseManager

logger = logging.getLogger("specter.collection_repo")


class CollectionRepository:
    """Simple repository for managing file collections via tags."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize repository with database manager."""
        self.db = db_manager or DatabaseManager()
        if not self.db.is_initialized:
            self.db.initialize()
        logger.debug("CollectionRepository initialized (tag-based)")

    async def list_collection_tags(self) -> List[str]:
        """
        Get all unique collection tags.

        Returns:
            List of collection tag names
        """
        try:
            with self.db.get_session() as session:
                # Get distinct tags
                result = session.query(ConversationFileModel.collection_tag)\
                    .filter(ConversationFileModel.collection_tag.isnot(None))\
                    .distinct()\
                    .order_by(ConversationFileModel.collection_tag)\
                    .all()

                tags = [row[0] for row in result if row[0]]
                logger.debug(f"✓ Found {len(tags)} collection tags")
                return tags

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error listing collection tags: {e}")
            return []
        except Exception as e:
            logger.error(f"✗ Unexpected error listing collection tags: {e}")
            return []

    async def get_files_by_tag(self, tag: str) -> List[Dict]:
        """
        Get all files with a specific collection tag.

        Args:
            tag: Collection tag name

        Returns:
            List of file dictionaries with metadata
        """
        try:
            with self.db.get_session() as session:
                files = session.query(ConversationFileModel)\
                    .filter(ConversationFileModel.collection_tag == tag)\
                    .order_by(ConversationFileModel.upload_timestamp.desc())\
                    .all()

                result = []
                for file in files:
                    result.append({
                        'id': file.id,
                        'file_id': file.file_id,
                        'filename': file.filename,
                        'file_path': file.file_path,
                        'file_size': file.file_size,
                        'file_type': file.file_type,
                        'upload_timestamp': file.upload_timestamp,
                        'processing_status': file.processing_status,
                        'chunk_count': file.chunk_count,
                        'is_enabled': file.is_enabled,
                        'collection_tag': file.collection_tag,
                        'conversation_id': file.conversation_id
                    })

                logger.debug(f"✓ Found {len(result)} files with tag '{tag}'")
                return result

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error getting files by tag: {e}")
            return []
        except Exception as e:
            logger.error(f"✗ Unexpected error getting files by tag: {e}")
            return []

    async def get_tag_stats(self, tag: str) -> Dict:
        """
        Get statistics for a collection tag.

        Args:
            tag: Collection tag name

        Returns:
            Dictionary with file count, total size, etc.
        """
        try:
            with self.db.get_session() as session:
                stats = session.query(
                    func.count(ConversationFileModel.id).label('file_count'),
                    func.sum(ConversationFileModel.file_size).label('total_size'),
                    func.sum(ConversationFileModel.chunk_count).label('total_chunks')
                ).filter(
                    ConversationFileModel.collection_tag == tag
                ).first()

                return {
                    'tag': tag,
                    'file_count': stats.file_count or 0,
                    'total_size': stats.total_size or 0,
                    'total_chunks': stats.total_chunks or 0
                }

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error getting tag stats: {e}")
            return {'tag': tag, 'file_count': 0, 'total_size': 0, 'total_chunks': 0}
        except Exception as e:
            logger.error(f"✗ Unexpected error getting tag stats: {e}")
            return {'tag': tag, 'file_count': 0, 'total_size': 0, 'total_chunks': 0}

    async def add_file_to_collection(self, file_id: str, conversation_id: str, tag: str) -> bool:
        """
        Tag a file with a collection tag.

        Args:
            file_id: File identifier
            conversation_id: Conversation ID
            tag: Collection tag to apply

        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                file = session.query(ConversationFileModel).filter(
                    ConversationFileModel.file_id == file_id,
                    ConversationFileModel.conversation_id == conversation_id
                ).first()

                if not file:
                    logger.warning(f"⚠ File {file_id} not found in conversation {conversation_id}")
                    return False

                file.collection_tag = tag
                logger.info(f"✓ Tagged file {file.filename} with '{tag}'")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error adding file to collection: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error adding file to collection: {e}")
            return False

    async def remove_file_from_collection(self, file_id: str, conversation_id: str) -> bool:
        """
        Remove collection tag from a file.

        Args:
            file_id: File identifier
            conversation_id: Conversation ID

        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                file = session.query(ConversationFileModel).filter(
                    ConversationFileModel.file_id == file_id,
                    ConversationFileModel.conversation_id == conversation_id
                ).first()

                if not file:
                    logger.warning(f"⚠ File {file_id} not found")
                    return False

                file.collection_tag = None
                logger.info(f"✓ Removed collection tag from {file.filename}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error removing file from collection: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error removing file from collection: {e}")
            return False

    async def delete_collection_tag(self, tag: str) -> bool:
        """
        Remove a collection tag from all files.

        Args:
            tag: Collection tag to remove

        Returns:
            True if successful
        """
        try:
            with self.db.get_session() as session:
                session.query(ConversationFileModel)\
                    .filter(ConversationFileModel.collection_tag == tag)\
                    .update({'collection_tag': None})

                logger.info(f"✓ Removed collection tag '{tag}' from all files")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Database error deleting collection tag: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error deleting collection tag: {e}")
            return False
