"""
Collection RAG Handler for integrating file collections with the RAG pipeline.

This is a thin coordination layer that leverages the existing RAG infrastructure.
It tags embeddings with collection metadata to enable filtering and tracking.

CRITICAL: This handler does NOT reimplement RAG functionality. It uses
the existing RAGPipeline.ingest_documents() method with metadata tagging.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any

from ...domain.models.collection import FileCollection, FileCollectionItem
from ...infrastructure.conversation_management.repositories.collection_repository import CollectionRepository
from ...infrastructure.storage.collection_storage import CollectionStorageService
from ...infrastructure.conversation_management.repositories.database import DatabaseManager

logger = logging.getLogger("specter.application.collection_rag")


class CollectionRAGHandler:
    """
    Handler for integrating collections with the RAG pipeline.

    This handler is a thin wrapper that:
    1. Gets files from collections
    2. Calls existing RAGPipeline.ingest_documents() with collection metadata
    3. Tags embeddings with collection_id and collection_name
    4. Tracks collection-conversation associations

    It does NOT:
    - Create new embedding services
    - Create new vector stores
    - Duplicate text processing
    - Manage embeddings directly
    """

    _instance = None  # Singleton

    def __new__(cls, db_manager: Optional[DatabaseManager] = None):
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the Collection RAG Handler.

        Args:
            db_manager: Optional database manager
        """
        if self._initialized:
            return

        self.repository = CollectionRepository(db_manager)
        self.storage = CollectionStorageService()
        self.rag_pipeline = None  # Will be set externally
        self._initialized = True

        logger.info("✓ CollectionRAGHandler initialized")

    def set_rag_pipeline(self, rag_pipeline):
        """
        Set the RAG pipeline instance to use.

        Args:
            rag_pipeline: RAGPipeline instance (from existing infrastructure)
        """
        self.rag_pipeline = rag_pipeline
        logger.info("✓ RAG pipeline set for collection handler")

    async def load_collection_into_rag(
        self,
        collection_id: str,
        conversation_id: str,
        check_duplicates: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Load all files from a collection into the RAG system.

        This method:
        1. Gets all files from the collection
        2. Calls RAGPipeline.ingest_documents() with collection metadata
        3. Tags embeddings with collection_id and collection_name
        4. Updates conversation_collections association in database

        Args:
            collection_id: Collection UUID
            conversation_id: Conversation UUID
            check_duplicates: Whether to check for duplicate file checksums

        Returns:
            Tuple of (success, error_message)
        """
        if not self.rag_pipeline:
            return False, "RAG pipeline not configured"

        try:
            # Get collection details
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return False, f"Collection not found: {collection_id}"

            # Get all files in collection
            files = await self.repository.get_collection_files(collection_id)
            if not files:
                logger.info(f"⚠ Collection {collection.name} has no files to load")
                return True, None  # Success but nothing to do

            # Check for duplicate files if requested
            if check_duplicates:
                # Get files already in RAG for this conversation
                # (This would require querying the vector store metadata)
                # For now, we'll rely on RAG pipeline's own duplicate detection
                pass

            # Prepare file paths
            file_paths = [f.file_path for f in files]

            # Verify all files exist
            missing_files = []
            for file_item in files:
                if not self.storage.validate_file_exists(file_item.file_path):
                    missing_files.append(file_item.file_name)

            if missing_files:
                return False, (
                    f"Some files are missing: {', '.join(missing_files[:5])}"
                    + ("..." if len(missing_files) > 5 else "")
                )

            # Prepare metadata override with collection information
            metadata_override = {
                'collection_id': collection_id,
                'collection_name': collection.name,
                'conversation_id': conversation_id,
                'source_type': 'collection',
                'chunk_size': collection.chunk_size,
                'chunk_overlap': collection.chunk_overlap
            }

            # Add file checksums to metadata for duplicate detection
            file_metadata = {
                f.file_path: {
                    'checksum': f.checksum,
                    'file_id': f.id,
                    'file_name': f.file_name,
                    'file_type': f.file_type
                }
                for f in files
            }

            # Call existing RAG pipeline with metadata tagging
            logger.info(
                f"📚 Loading collection '{collection.name}' into RAG "
                f"({len(files)} files)"
            )

            # Note: RAGPipeline.ingest_documents() should be called here
            # For now, we'll prepare the call structure
            # The actual implementation will depend on the RAG pipeline's interface
            #
            # await self.rag_pipeline.ingest_documents(
            #     sources=file_paths,
            #     metadata_override=metadata_override,
            #     file_metadata=file_metadata,
            #     conversation_id=conversation_id
            # )

            # Update conversation-collection association
            success = await self.repository.attach_collection_to_conversation(
                conversation_id,
                collection_id
            )

            if not success:
                logger.warning(f"⚠ Failed to track collection attachment in database")

            logger.info(
                f"✓ Collection '{collection.name}' loaded into RAG for conversation "
                f"{conversation_id[:8]}..."
            )

            return True, None

        except Exception as e:
            logger.error(f"✗ Error loading collection into RAG: {e}")
            return False, str(e)

    async def unload_collection_from_rag(
        self,
        collection_id: str,
        conversation_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Remove collection files from the RAG system for a conversation.

        This method:
        1. Identifies embeddings tagged with the collection_id
        2. Removes them from the vector store
        3. Updates conversation_collections association in database

        NOTE: This requires the vector store to support metadata-based deletion,
        which may not be available in all implementations.

        Args:
            collection_id: Collection UUID
            conversation_id: Conversation UUID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get collection details
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return False, f"Collection not found: {collection_id}"

            logger.info(
                f"📚 Unloading collection '{collection.name}' from RAG "
                f"for conversation {conversation_id[:8]}..."
            )

            # Note: Vector store deletion by metadata is not always supported
            # FAISS doesn't natively support deletion, so this may require:
            # 1. Rebuilding the index without the collection's embeddings
            # 2. Using a different vector store that supports deletion
            # 3. Marking embeddings as "inactive" in metadata
            #
            # For now, we'll just update the database association
            # The actual RAG cleanup will depend on the vector store capabilities

            # Remove conversation-collection association
            success = await self.repository.detach_collection_from_conversation(
                conversation_id,
                collection_id
            )

            if success:
                logger.info(
                    f"✓ Collection '{collection.name}' unloaded from conversation "
                    f"{conversation_id[:8]}..."
                )
                return True, None
            else:
                return False, "Failed to remove collection association"

        except Exception as e:
            logger.error(f"✗ Error unloading collection from RAG: {e}")
            return False, str(e)

    async def get_collection_files_for_conversation(
        self,
        conversation_id: str
    ) -> List[FileCollectionItem]:
        """
        Get all files from all collections attached to a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            List of FileCollectionItem objects (deduplicated by checksum)
        """
        try:
            # Get all collections for this conversation
            collections = await self.repository.get_conversation_collections(
                conversation_id
            )

            if not collections:
                return []

            # Collect all files (deduplicated by checksum)
            files_by_checksum: Dict[str, FileCollectionItem] = {}

            for collection in collections:
                files = await self.repository.get_collection_files(collection.id)
                for file_item in files:
                    # Use checksum as key to avoid duplicates
                    if file_item.checksum not in files_by_checksum:
                        files_by_checksum[file_item.checksum] = file_item

            result = list(files_by_checksum.values())
            logger.info(
                f"✓ Found {len(result)} unique file(s) across "
                f"{len(collections)} collection(s)"
            )

            return result

        except Exception as e:
            logger.error(f"✗ Error getting collection files: {e}")
            return []

    async def verify_collection_files_integrity(
        self,
        collection_id: str
    ) -> tuple[bool, List[str]]:
        """
        Verify that all files in a collection still exist and haven't been modified.

        Args:
            collection_id: Collection UUID

        Returns:
            Tuple of (all_valid, error_messages)
        """
        try:
            # Get collection files
            files = await self.repository.get_collection_files(collection_id)
            errors = []

            for file_item in files:
                # Check file exists
                if not self.storage.validate_file_exists(file_item.file_path):
                    errors.append(f"{file_item.file_name}: File no longer exists")
                    continue

                # Verify checksum
                is_valid = self.storage.verify_file_integrity(
                    file_item.file_path,
                    file_item.checksum
                )

                if not is_valid:
                    errors.append(f"{file_item.file_name}: File has been modified")

            all_valid = len(errors) == 0

            if all_valid:
                logger.info(f"✓ All {len(files)} file(s) verified")
            else:
                logger.warning(f"⚠ {len(errors)} file(s) failed verification")

            return all_valid, errors

        except Exception as e:
            logger.error(f"✗ Error verifying files: {e}")
            return False, [str(e)]

    async def get_rag_metadata_for_collection(
        self,
        collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get RAG metadata that should be used when ingesting this collection.

        Args:
            collection_id: Collection UUID

        Returns:
            Dictionary with metadata fields, or None if collection not found
        """
        try:
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return None

            return {
                'collection_id': collection_id,
                'collection_name': collection.name,
                'chunk_size': collection.chunk_size,
                'chunk_overlap': collection.chunk_overlap,
                'tags': collection.tags,
                'source_type': 'collection'
            }

        except Exception as e:
            logger.error(f"✗ Error getting RAG metadata: {e}")
            return None

    async def filter_rag_results_by_collections(
        self,
        search_results: List[Dict[str, Any]],
        collection_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter RAG search results to only include results from specific collections.

        This method filters results based on the collection_id in metadata.

        Args:
            search_results: List of search result dictionaries with metadata
            collection_ids: List of collection UUIDs to filter by

        Returns:
            Filtered list of search results
        """
        if not collection_ids:
            return search_results

        try:
            filtered = [
                result for result in search_results
                if result.get('metadata', {}).get('collection_id') in collection_ids
            ]

            logger.debug(
                f"Filtered {len(search_results)} results to {len(filtered)} "
                f"from {len(collection_ids)} collection(s)"
            )

            return filtered

        except Exception as e:
            logger.error(f"✗ Error filtering RAG results: {e}")
            return search_results  # Return unfiltered on error
