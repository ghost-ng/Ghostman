"""
Repository for file collection data operations using SQLAlchemy ORM.

Provides comprehensive CRUD operations, file management, search, and
conversation association functionality for file collections.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from ..models.database_models import (
    CollectionModel, CollectionFileModel, CollectionTagModel,
    ConversationCollectionModel, sanitize_text
)
from .database import DatabaseManager

logger = logging.getLogger("ghostman.collection_repo")


class CollectionRepository:
    """Repository for file collection data operations using SQLAlchemy ORM."""

    _instance = None

    def __new__(cls, db_manager: Optional[DatabaseManager] = None):
        """Singleton pattern to ensure only one repository instance."""
        if cls._instance is None:
            cls._instance = super(CollectionRepository, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize repository with database manager."""
        if self._initialized:
            return

        self.db = db_manager or DatabaseManager()
        if not self.db.is_initialized:
            self.db.initialize()

        self._initialized = True
        logger.debug("CollectionRepository initialized")

    # --- CRUD Operations ---

    async def create_collection(self, collection) -> bool:
        """
        Create a new file collection.

        Args:
            collection: FileCollection domain model

        Returns:
            True if created successfully, False otherwise
        """
        logger.info(f"🔄 Creating collection: {collection.name}")

        try:
            with self.db.get_session() as session:
                # Check for duplicate collection name
                existing = session.query(CollectionModel).filter(
                    CollectionModel.name == collection.name
                ).first()

                if existing:
                    logger.warning(f"⚠ Collection with name '{collection.name}' already exists")
                    return False

                # Create collection model
                collection_model = CollectionModel(
                    id=collection.id,
                    name=sanitize_text(collection.name),
                    description=sanitize_text(collection.description) if collection.description else '',
                    created_at=collection.created_at,
                    updated_at=collection.updated_at,
                    chunk_size=collection.chunk_size,
                    chunk_overlap=collection.chunk_overlap,
                    is_template=collection.is_template,
                    max_size_mb=collection.max_size_mb
                )
                session.add(collection_model)

                # Add tags
                for tag in collection.tags:
                    tag_model = CollectionTagModel(
                        collection_id=collection.id,
                        tag=sanitize_text(tag)
                    )
                    session.add(tag_model)

                # Add files
                for file_item in collection.files:
                    file_model = CollectionFileModel(
                        id=file_item.id,
                        collection_id=collection.id,
                        file_path=file_item.file_path,
                        file_name=file_item.file_name,
                        file_size=file_item.file_size,
                        file_type=file_item.file_type,
                        added_at=file_item.added_at,
                        checksum=file_item.checksum
                    )
                    session.add(file_model)

                logger.info(f"✓ Successfully created collection: {collection.name} with {len(collection.files)} files")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to create collection {collection.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error creating collection {collection.name}: {e}")
            return False

    async def get_collection(self, collection_id: str) -> Optional[object]:
        """
        Get collection by ID with all related data.

        Args:
            collection_id: Collection UUID

        Returns:
            FileCollection domain model or None if not found
        """
        try:
            logger.debug(f"🔍 Fetching collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                query = session.query(CollectionModel).filter(
                    CollectionModel.id == collection_id
                ).options(
                    selectinload(CollectionModel.files),
                    selectinload(CollectionModel.tags),
                    selectinload(CollectionModel.conversations)
                )

                collection_model = query.first()
                if not collection_model:
                    logger.warning(f"⚠ Collection {collection_id[:8]}... not found")
                    return None

                logger.debug(f"✓ Found collection: {collection_model.name} with {len(collection_model.files)} files")
                return collection_model.to_domain_model()

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get collection {collection_id[:8]}...: {e}")
            return None

    async def list_collections(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filter_tags: Optional[List[str]] = None
    ) -> List[object]:
        """
        List all collections with optional filtering.

        Args:
            limit: Maximum number of collections to return
            offset: Number of collections to skip
            filter_tags: Filter collections by tags (returns collections with ANY of these tags)

        Returns:
            List of FileCollection domain models
        """
        try:
            logger.debug(f"🔍 Listing collections (limit={limit}, offset={offset}, tags={filter_tags})")

            with self.db.get_session() as session:
                query = session.query(CollectionModel).options(
                    selectinload(CollectionModel.files),
                    selectinload(CollectionModel.tags)
                )

                # Filter by tags if specified
                if filter_tags:
                    query = query.join(CollectionTagModel).filter(
                        CollectionTagModel.tag.in_([sanitize_text(tag).lower() for tag in filter_tags])
                    ).distinct()

                # Sort by updated_at descending (most recent first)
                query = query.order_by(desc(CollectionModel.updated_at))

                # Apply pagination
                if offset > 0:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)

                collection_models = query.all()
                collections = [model.to_domain_model() for model in collection_models]

                logger.debug(f"✓ Found {len(collections)} collections")
                return collections

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to list collections: {e}")
            return []

    async def update_collection(self, collection) -> bool:
        """
        Update existing collection.

        Args:
            collection: FileCollection domain model with updated data

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            logger.info(f"🔄 Updating collection: {collection.name}")

            with self.db.get_session() as session:
                collection_model = session.query(CollectionModel).filter(
                    CollectionModel.id == collection.id
                ).first()

                if not collection_model:
                    logger.warning(f"⚠ Collection {collection.id[:8]}... not found for update")
                    return False

                # Check for duplicate name (excluding current collection)
                duplicate = session.query(CollectionModel).filter(
                    and_(
                        CollectionModel.name == collection.name,
                        CollectionModel.id != collection.id
                    )
                ).first()

                if duplicate:
                    logger.warning(f"⚠ Collection name '{collection.name}' already exists")
                    return False

                # Update collection fields
                collection_model.name = sanitize_text(collection.name)
                collection_model.description = sanitize_text(collection.description) if collection.description else ''
                collection_model.updated_at = datetime.utcnow()
                collection_model.chunk_size = collection.chunk_size
                collection_model.chunk_overlap = collection.chunk_overlap
                collection_model.is_template = collection.is_template
                collection_model.max_size_mb = collection.max_size_mb

                # Update tags - remove existing and add new ones
                session.query(CollectionTagModel).filter(
                    CollectionTagModel.collection_id == collection.id
                ).delete()

                for tag in collection.tags:
                    tag_model = CollectionTagModel(
                        collection_id=collection.id,
                        tag=sanitize_text(tag)
                    )
                    session.add(tag_model)

                logger.info(f"✓ Successfully updated collection: {collection.name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to update collection {collection.id[:8]}...: {e}")
            return False

    async def delete_collection(self, collection_id: str) -> bool:
        """
        Delete collection and all associated data.

        Args:
            collection_id: Collection UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"🗑 Deleting collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                collection_model = session.query(CollectionModel).filter(
                    CollectionModel.id == collection_id
                ).first()

                if not collection_model:
                    logger.warning(f"⚠ Collection {collection_id[:8]}... not found for deletion")
                    return False

                # Delete will cascade to files, tags, and conversation associations
                session.delete(collection_model)

                logger.info(f"✓ Successfully deleted collection: {collection_model.name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to delete collection {collection_id[:8]}...: {e}")
            return False

    # --- File Operations ---

    async def add_file_to_collection(self, collection_id: str, file_item) -> bool:
        """
        Add a file to a collection.

        Args:
            collection_id: Collection UUID
            file_item: FileCollectionItem domain model

        Returns:
            True if added successfully, False otherwise
        """
        try:
            logger.debug(f"📎 Adding file {file_item.file_name} to collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                # Verify collection exists
                collection = session.query(CollectionModel).filter(
                    CollectionModel.id == collection_id
                ).first()

                if not collection:
                    logger.warning(f"⚠ Collection {collection_id[:8]}... not found")
                    return False

                # Check if file with same checksum already exists in this collection
                existing_file = session.query(CollectionFileModel).filter(
                    and_(
                        CollectionFileModel.collection_id == collection_id,
                        CollectionFileModel.checksum == file_item.checksum
                    )
                ).first()

                if existing_file:
                    logger.warning(f"⚠ File with checksum {file_item.checksum[:8]}... already exists in collection")
                    return False

                # Create file model
                file_model = CollectionFileModel(
                    id=file_item.id,
                    collection_id=collection_id,
                    file_path=file_item.file_path,
                    file_name=file_item.file_name,
                    file_size=file_item.file_size,
                    file_type=file_item.file_type,
                    added_at=file_item.added_at,
                    checksum=file_item.checksum
                )
                session.add(file_model)

                # Update collection timestamp
                collection.updated_at = datetime.utcnow()

                logger.debug(f"✓ Successfully added file {file_item.file_name} to collection")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to add file to collection: {e}")
            return False

    async def remove_file_from_collection(self, collection_id: str, file_item_id: str) -> bool:
        """
        Remove a file from a collection.

        Args:
            collection_id: Collection UUID
            file_item_id: File item UUID

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            logger.debug(f"🗑 Removing file {file_item_id[:8]}... from collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                # Find the file
                file_model = session.query(CollectionFileModel).filter(
                    and_(
                        CollectionFileModel.id == file_item_id,
                        CollectionFileModel.collection_id == collection_id
                    )
                ).first()

                if not file_model:
                    logger.warning(f"⚠ File {file_item_id[:8]}... not found in collection {collection_id[:8]}...")
                    return False

                # Delete the file
                session.delete(file_model)

                # Update collection timestamp
                collection = session.query(CollectionModel).filter(
                    CollectionModel.id == collection_id
                ).first()
                if collection:
                    collection.updated_at = datetime.utcnow()

                logger.debug(f"✓ Successfully removed file from collection")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to remove file from collection: {e}")
            return False

    async def get_collection_files(self, collection_id: str) -> List[object]:
        """
        Get all files in a collection.

        Args:
            collection_id: Collection UUID

        Returns:
            List of FileCollectionItem domain models
        """
        try:
            logger.debug(f"🔍 Fetching files for collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                file_models = session.query(CollectionFileModel).filter(
                    CollectionFileModel.collection_id == collection_id
                ).order_by(CollectionFileModel.added_at.desc()).all()

                files = [model.to_domain_model() for model in file_models]
                logger.debug(f"✓ Found {len(files)} files in collection")
                return files

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get collection files: {e}")
            return []

    async def get_file_by_checksum(self, checksum: str) -> Optional[object]:
        """
        Find a file by checksum across ALL collections.

        This enables reusing RAG embeddings when the same file appears
        in multiple collections.

        Args:
            checksum: SHA256 checksum of the file

        Returns:
            FileCollectionItem domain model or None if not found
        """
        try:
            logger.debug(f"🔍 Searching for file with checksum {checksum[:8]}... across all collections")

            with self.db.get_session() as session:
                file_model = session.query(CollectionFileModel).filter(
                    CollectionFileModel.checksum == checksum
                ).first()

                if not file_model:
                    logger.debug(f"⚠ No file found with checksum {checksum[:8]}...")
                    return None

                logger.debug(f"✓ Found existing file: {file_model.file_name} in collection {file_model.collection_id[:8]}...")
                return file_model.to_domain_model()

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to search for file by checksum: {e}")
            return None

    # --- Search ---

    async def search_collections(self, query: str) -> List[object]:
        """
        Search collections by name, description, or tags.

        Args:
            query: Search query string

        Returns:
            List of FileCollection domain models matching the query
        """
        try:
            logger.debug(f"🔍 Searching collections for: {query}")

            if not query or not query.strip():
                return []

            search_term = f"%{sanitize_text(query)}%"

            with self.db.get_session() as session:
                # Search in name, description, and tags
                query_obj = session.query(CollectionModel).options(
                    selectinload(CollectionModel.files),
                    selectinload(CollectionModel.tags)
                ).outerjoin(CollectionTagModel).filter(
                    or_(
                        CollectionModel.name.like(search_term),
                        CollectionModel.description.like(search_term),
                        CollectionTagModel.tag.like(search_term)
                    )
                ).distinct().order_by(desc(CollectionModel.updated_at))

                collection_models = query_obj.all()
                collections = [model.to_domain_model() for model in collection_models]

                logger.debug(f"✓ Found {len(collections)} collections matching query")
                return collections

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to search collections: {e}")
            return []

    # --- Conversation Associations ---

    async def attach_collection_to_conversation(self, conversation_id: str, collection_id: str) -> bool:
        """
        Attach a collection to a conversation.

        Args:
            conversation_id: Conversation UUID
            collection_id: Collection UUID

        Returns:
            True if attached successfully, False otherwise
        """
        try:
            logger.debug(f"🔗 Attaching collection {collection_id[:8]}... to conversation {conversation_id[:8]}...")

            with self.db.get_session() as session:
                # Verify both collection and conversation exist
                collection = session.query(CollectionModel).filter(
                    CollectionModel.id == collection_id
                ).first()

                if not collection:
                    logger.warning(f"⚠ Collection {collection_id[:8]}... not found")
                    return False

                # Check if already attached
                existing = session.query(ConversationCollectionModel).filter(
                    and_(
                        ConversationCollectionModel.conversation_id == conversation_id,
                        ConversationCollectionModel.collection_id == collection_id
                    )
                ).first()

                if existing:
                    logger.debug(f"⚠ Collection already attached to conversation")
                    return True  # Return True since the desired state is achieved

                # Create association
                association = ConversationCollectionModel(
                    conversation_id=conversation_id,
                    collection_id=collection_id,
                    attached_at=datetime.utcnow()
                )
                session.add(association)

                logger.debug(f"✓ Successfully attached collection to conversation")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to attach collection to conversation: {e}")
            return False

    async def detach_collection_from_conversation(self, conversation_id: str, collection_id: str) -> bool:
        """
        Detach a collection from a conversation.

        Args:
            conversation_id: Conversation UUID
            collection_id: Collection UUID

        Returns:
            True if detached successfully, False otherwise
        """
        try:
            logger.debug(f"🔓 Detaching collection {collection_id[:8]}... from conversation {conversation_id[:8]}...")

            with self.db.get_session() as session:
                # Find association
                association = session.query(ConversationCollectionModel).filter(
                    and_(
                        ConversationCollectionModel.conversation_id == conversation_id,
                        ConversationCollectionModel.collection_id == collection_id
                    )
                ).first()

                if not association:
                    logger.debug(f"⚠ Collection not attached to conversation")
                    return True  # Return True since the desired state is achieved

                # Delete association
                session.delete(association)

                logger.debug(f"✓ Successfully detached collection from conversation")
                return True

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to detach collection from conversation: {e}")
            return False

    async def get_conversation_collections(self, conversation_id: str) -> List[object]:
        """
        Get all collections attached to a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            List of FileCollection domain models
        """
        try:
            logger.debug(f"🔍 Fetching collections for conversation {conversation_id[:8]}...")

            with self.db.get_session() as session:
                # Query collections through the association table
                collection_models = session.query(CollectionModel).options(
                    selectinload(CollectionModel.files),
                    selectinload(CollectionModel.tags)
                ).join(ConversationCollectionModel).filter(
                    ConversationCollectionModel.conversation_id == conversation_id
                ).order_by(ConversationCollectionModel.attached_at.desc()).all()

                collections = [model.to_domain_model() for model in collection_models]
                logger.debug(f"✓ Found {len(collections)} collections for conversation")
                return collections

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get conversation collections: {e}")
            return []

    async def get_collection_conversations(self, collection_id: str) -> List[str]:
        """
        Get all conversation IDs that have this collection attached.

        Args:
            collection_id: Collection UUID

        Returns:
            List of conversation IDs (strings)
        """
        try:
            logger.debug(f"🔍 Fetching conversations for collection {collection_id[:8]}...")

            with self.db.get_session() as session:
                # Query conversation IDs through the association table
                associations = session.query(ConversationCollectionModel).filter(
                    ConversationCollectionModel.collection_id == collection_id
                ).order_by(ConversationCollectionModel.attached_at.desc()).all()

                conversation_ids = [assoc.conversation_id for assoc in associations]
                logger.debug(f"✓ Found {len(conversation_ids)} conversations with this collection")
                return conversation_ids

        except SQLAlchemyError as e:
            logger.error(f"✗ Failed to get collection conversations: {e}")
            return []
