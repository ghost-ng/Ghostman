"""
Simple tag-based collection service.

Manages file uploads and tagging for collections. Files are uploaded through RAG pipeline
and can be tagged into groups for reuse across conversations.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict
from uuid import uuid4

from ...infrastructure.conversation_management.repositories.collection_repository import CollectionRepository
from ...infrastructure.conversation_management.repositories.database import DatabaseManager

logger = logging.getLogger("specter.application.collection_service")


class CollectionService:
    """Service for managing file collections via tags."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the collection service.

        Args:
            db_manager: Optional database manager (uses singleton if not provided)
        """
        self.repository = CollectionRepository(db_manager)
        logger.info("✓ CollectionService initialized (tag-based)")

    async def list_collection_tags(self) -> List[str]:
        """
        Get all unique collection tags.

        Returns:
            List of collection tag names
        """
        try:
            return await self.repository.list_collection_tags()
        except Exception as e:
            logger.error(f"✗ Error listing collection tags: {e}")
            return []

    async def get_files_by_tag(self, tag: str) -> List[Dict]:
        """
        Get all files with a specific collection tag.

        Args:
            tag: Collection tag name

        Returns:
            List of file dictionaries
        """
        try:
            return await self.repository.get_files_by_tag(tag)
        except Exception as e:
            logger.error(f"✗ Error getting files by tag: {e}")
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
            return await self.repository.get_tag_stats(tag)
        except Exception as e:
            logger.error(f"✗ Error getting tag stats: {e}")
            return {'tag': tag, 'file_count': 0, 'total_size': 0, 'total_chunks': 0}

    async def tag_file(self, file_id: str, conversation_id: str, tag: str) -> bool:
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
            if not tag or not tag.strip():
                logger.error("✗ Tag cannot be empty")
                return False

            # Sanitize tag (lowercase, no special chars except dash/underscore)
            clean_tag = tag.strip().lower().replace(' ', '-')
            clean_tag = ''.join(c for c in clean_tag if c.isalnum() or c in '-_')

            if not clean_tag:
                logger.error("✗ Tag contains only invalid characters")
                return False

            return await self.repository.add_file_to_collection(file_id, conversation_id, clean_tag)
        except Exception as e:
            logger.error(f"✗ Error tagging file: {e}")
            return False

    async def untag_file(self, file_id: str, conversation_id: str) -> bool:
        """
        Remove collection tag from a file.

        Args:
            file_id: File identifier
            conversation_id: Conversation ID

        Returns:
            True if successful
        """
        try:
            return await self.repository.remove_file_from_collection(file_id, conversation_id)
        except Exception as e:
            logger.error(f"✗ Error untagging file: {e}")
            return False

    async def delete_tag(self, tag: str) -> bool:
        """
        Remove a collection tag from all files.

        Args:
            tag: Collection tag to remove

        Returns:
            True if successful
        """
        try:
            return await self.repository.delete_collection_tag(tag)
        except Exception as e:
            logger.error(f"✗ Error deleting tag: {e}")
            return False

    async def get_all_files(self) -> List[Dict]:
        """
        Get all uploaded files across all conversations.

        Returns:
            List of all file dictionaries
        """
        try:
            # Get all tags first
            tags = await self.repository.list_collection_tags()

            # Get files for each tag
            all_files = []
            seen_file_ids = set()

            for tag in tags:
                files = await self.repository.get_files_by_tag(tag)
                for file in files:
                    # Deduplicate by file_id
                    if file['file_id'] not in seen_file_ids:
                        all_files.append(file)
                        seen_file_ids.add(file['file_id'])

            # Also get untagged files from conversation_files
            # (This requires a new repository method - for now return tagged files only)

            return all_files
        except Exception as e:
            logger.error(f"✗ Error getting all files: {e}")
            return []
