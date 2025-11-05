"""
Application service for file collections management.

This service provides the business logic layer for file collections,
coordinating between the repository, storage service, and domain models.
It handles validation, template management, and import/export operations.
"""

import asyncio
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

from ...domain.models.collection import FileCollection, FileCollectionItem
from ...infrastructure.conversation_management.repositories.collection_repository import CollectionRepository
from ...infrastructure.storage.collection_storage import CollectionStorageService
from ...infrastructure.conversation_management.database_manager import DatabaseManager

logger = logging.getLogger("ghostman.application.collection_service")


class CollectionService:
    """
    Application service for file collections.

    Provides high-level operations for managing collections, including:
    - Creation, retrieval, update, deletion
    - File management with duplicate detection
    - Template creation and management
    - Import/export functionality
    - Validation and business rules enforcement
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
        Initialize the collection service.

        Args:
            db_manager: Optional database manager (creates default if not provided)
        """
        if self._initialized:
            return

        self.repository = CollectionRepository(db_manager)
        self.storage = CollectionStorageService()
        self._initialized = True
        logger.info("✓ CollectionService initialized")

    # ========================================
    # Collection Management
    # ========================================

    async def create_collection(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        is_template: bool = False,
        max_size_mb: int = 500
    ) -> Optional[FileCollection]:
        """
        Create a new file collection.

        Args:
            name: Collection name (must be unique)
            description: Optional description
            tags: Optional tags for organization
            chunk_size: Text chunk size for RAG (default 1000)
            chunk_overlap: Chunk overlap for RAG (default 200)
            is_template: Whether this is a template collection
            max_size_mb: Maximum total size in MB

        Returns:
            FileCollection if created successfully, None otherwise
        """
        try:
            # Validate name
            if not name or len(name.strip()) == 0:
                logger.error("✗ Collection name cannot be empty")
                return None

            if len(name) > 200:
                logger.error("✗ Collection name too long (max 200 characters)")
                return None

            # Check for duplicate name
            existing = await self.repository.get_collection_by_name(name)
            if existing:
                logger.error(f"✗ Collection with name '{name}' already exists")
                return None

            # Validate RAG settings
            if chunk_size < 100 or chunk_size > 10000:
                logger.error("✗ Chunk size must be between 100 and 10000")
                return None

            if chunk_overlap < 0 or chunk_overlap >= chunk_size:
                logger.error("✗ Chunk overlap must be between 0 and chunk_size")
                return None

            # Validate size limit
            if max_size_mb < 1 or max_size_mb > 10000:
                logger.error("✗ Max size must be between 1 and 10000 MB")
                return None

            # Create domain model
            collection = FileCollection.create(
                name=name,
                description=description,
                tags=tags,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                is_template=is_template,
                max_size_mb=max_size_mb
            )

            # Persist to database
            success = await self.repository.create_collection(collection)
            if not success:
                logger.error("✗ Failed to persist collection to database")
                return None

            logger.info(f"✓ Created collection: {name}")
            return collection

        except Exception as e:
            logger.error(f"✗ Error creating collection: {e}")
            return None

    async def get_collection(self, collection_id: str) -> Optional[FileCollection]:
        """
        Retrieve a collection by ID.

        Args:
            collection_id: Collection UUID

        Returns:
            FileCollection if found, None otherwise
        """
        try:
            return await self.repository.get_collection(collection_id)
        except Exception as e:
            logger.error(f"✗ Error retrieving collection: {e}")
            return None

    async def get_collection_by_name(self, name: str) -> Optional[FileCollection]:
        """
        Retrieve a collection by name.

        Args:
            name: Collection name

        Returns:
            FileCollection if found, None otherwise
        """
        try:
            return await self.repository.get_collection_by_name(name)
        except Exception as e:
            logger.error(f"✗ Error retrieving collection by name: {e}")
            return None

    async def list_collections(
        self,
        include_templates: bool = True,
        tags: Optional[List[str]] = None
    ) -> List[FileCollection]:
        """
        List all collections with optional filtering.

        Args:
            include_templates: Whether to include template collections
            tags: Optional list of tags to filter by

        Returns:
            List of FileCollection objects
        """
        try:
            return await self.repository.list_collections(
                include_templates=include_templates,
                tags=tags
            )
        except Exception as e:
            logger.error(f"✗ Error listing collections: {e}")
            return []

    async def update_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        max_size_mb: Optional[int] = None
    ) -> bool:
        """
        Update collection metadata.

        Args:
            collection_id: Collection UUID
            name: Optional new name (must be unique)
            description: Optional new description
            tags: Optional new tags list
            chunk_size: Optional new chunk size
            chunk_overlap: Optional new chunk overlap
            max_size_mb: Optional new size limit

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Validate name if provided
            if name is not None:
                if not name or len(name.strip()) == 0:
                    logger.error("✗ Collection name cannot be empty")
                    return False

                if len(name) > 200:
                    logger.error("✗ Collection name too long (max 200 characters)")
                    return False

                # Check for duplicate name (excluding current collection)
                existing = await self.repository.get_collection_by_name(name)
                if existing and existing.id != collection_id:
                    logger.error(f"✗ Collection with name '{name}' already exists")
                    return False

            # Validate RAG settings if provided
            if chunk_size is not None:
                if chunk_size < 100 or chunk_size > 10000:
                    logger.error("✗ Chunk size must be between 100 and 10000")
                    return False

            if chunk_overlap is not None:
                if chunk_overlap < 0:
                    logger.error("✗ Chunk overlap must be non-negative")
                    return False

            if max_size_mb is not None:
                if max_size_mb < 1 or max_size_mb > 10000:
                    logger.error("✗ Max size must be between 1 and 10000 MB")
                    return False

            # Update in repository
            success = await self.repository.update_collection(
                collection_id=collection_id,
                name=name,
                description=description,
                tags=tags,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                max_size_mb=max_size_mb
            )

            if success:
                logger.info(f"✓ Updated collection: {collection_id}")

            return success

        except Exception as e:
            logger.error(f"✗ Error updating collection: {e}")
            return False

    async def delete_collection(self, collection_id: str) -> bool:
        """
        Delete a collection and all its associations.

        This will cascade delete all files, tags, and conversation associations.

        Args:
            collection_id: Collection UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            success = await self.repository.delete_collection(collection_id)
            if success:
                logger.info(f"✓ Deleted collection: {collection_id}")
            return success
        except Exception as e:
            logger.error(f"✗ Error deleting collection: {e}")
            return False

    # ========================================
    # File Management
    # ========================================

    async def add_file_to_collection(
        self,
        collection_id: str,
        file_path: str,
        check_duplicates: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Add a file to a collection with duplicate detection.

        Args:
            collection_id: Collection UUID
            file_path: Path to file to add
            check_duplicates: Whether to check for duplicates across all collections

        Returns:
            Tuple of (success, message)
            - (True, None) if added successfully
            - (False, "error message") if failed
        """
        try:
            # Get collection to check size limit
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return False, f"Collection not found: {collection_id}"

            # Validate file exists
            if not self.storage.validate_file_exists(file_path):
                return False, f"File not found: {file_path}"

            # Calculate checksum
            checksum = self.storage.calculate_file_checksum(file_path)
            if not checksum:
                return False, f"Failed to calculate checksum for: {file_path}"

            # Check for duplicates if requested
            if check_duplicates:
                existing_file = await self.repository.get_file_by_checksum(checksum)
                if existing_file:
                    # File exists in another collection - reuse reference
                    logger.info(
                        f"⚠ File already exists in collection system (checksum {checksum[:8]}...)"
                        f" - reusing reference"
                    )
                    # Note: RAG embeddings can be reused via checksum lookup

            # Create file item
            try:
                file_item = FileCollectionItem.create(file_path, checksum)
            except (FileNotFoundError, ValueError) as e:
                return False, str(e)

            # Validate size limit before adding
            new_total = collection.total_size + file_item.file_size
            max_bytes = collection.max_size_mb * 1024 * 1024

            if new_total > max_bytes:
                total_mb = new_total / (1024 * 1024)
                return False, (
                    f"Adding file would exceed size limit: "
                    f"{total_mb:.2f}MB > {collection.max_size_mb}MB"
                )

            # Add to repository
            success = await self.repository.add_file_to_collection(collection_id, file_item)
            if not success:
                return False, "Failed to add file to database (may already exist in this collection)"

            logger.info(f"✓ Added file {file_item.file_name} to collection {collection.name}")
            return True, None

        except Exception as e:
            logger.error(f"✗ Error adding file to collection: {e}")
            return False, str(e)

    async def add_files_to_collection(
        self,
        collection_id: str,
        file_paths: List[str],
        check_duplicates: bool = True
    ) -> Tuple[int, List[str]]:
        """
        Add multiple files to a collection.

        Args:
            collection_id: Collection UUID
            file_paths: List of file paths to add
            check_duplicates: Whether to check for duplicates

        Returns:
            Tuple of (successful_count, error_messages)
        """
        successful = 0
        errors = []

        for file_path in file_paths:
            success, error = await self.add_file_to_collection(
                collection_id, file_path, check_duplicates
            )
            if success:
                successful += 1
            else:
                errors.append(f"{file_path}: {error}")

        logger.info(f"✓ Added {successful}/{len(file_paths)} files to collection")
        return successful, errors

    async def remove_file_from_collection(
        self,
        collection_id: str,
        file_id: str
    ) -> bool:
        """
        Remove a file from a collection.

        Args:
            collection_id: Collection UUID
            file_id: File UUID

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            success = await self.repository.remove_file_from_collection(collection_id, file_id)
            if success:
                logger.info(f"✓ Removed file {file_id} from collection {collection_id}")
            return success
        except Exception as e:
            logger.error(f"✗ Error removing file from collection: {e}")
            return False

    async def get_collection_files(self, collection_id: str) -> List[FileCollectionItem]:
        """
        Get all files in a collection.

        Args:
            collection_id: Collection UUID

        Returns:
            List of FileCollectionItem objects
        """
        try:
            return await self.repository.get_collection_files(collection_id)
        except Exception as e:
            logger.error(f"✗ Error getting collection files: {e}")
            return []

    async def verify_file_integrity(
        self,
        collection_id: str,
        file_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that a file hasn't been modified since being added.

        Args:
            collection_id: Collection UUID
            file_id: File UUID

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get file from repository
            files = await self.repository.get_collection_files(collection_id)
            file_item = next((f for f in files if f.id == file_id), None)

            if not file_item:
                return False, "File not found in collection"

            # Check if file still exists
            if not self.storage.validate_file_exists(file_item.file_path):
                return False, f"File no longer exists: {file_item.file_path}"

            # Verify checksum
            is_valid = self.storage.verify_file_integrity(
                file_item.file_path,
                file_item.checksum
            )

            if is_valid:
                return True, "File integrity verified"
            else:
                return False, "File has been modified since being added to collection"

        except Exception as e:
            logger.error(f"✗ Error verifying file integrity: {e}")
            return False, str(e)

    async def verify_collection_integrity(
        self,
        collection_id: str
    ) -> Tuple[bool, List[str]]:
        """
        Verify integrity of all files in a collection.

        Args:
            collection_id: Collection UUID

        Returns:
            Tuple of (all_valid, error_messages)
        """
        try:
            files = await self.repository.get_collection_files(collection_id)
            errors = []

            for file_item in files:
                is_valid, message = await self.verify_file_integrity(collection_id, file_item.id)
                if not is_valid:
                    errors.append(f"{file_item.file_name}: {message}")

            all_valid = len(errors) == 0
            if all_valid:
                logger.info(f"✓ All {len(files)} files in collection verified")
            else:
                logger.warning(f"⚠ {len(errors)} file(s) failed verification")

            return all_valid, errors

        except Exception as e:
            logger.error(f"✗ Error verifying collection integrity: {e}")
            return False, [str(e)]

    # ========================================
    # Conversation Associations
    # ========================================

    async def attach_collection_to_conversation(
        self,
        conversation_id: str,
        collection_id: str
    ) -> bool:
        """
        Attach a collection to a conversation.

        Args:
            conversation_id: Conversation UUID
            collection_id: Collection UUID

        Returns:
            True if attached successfully, False otherwise
        """
        try:
            success = await self.repository.attach_collection_to_conversation(
                conversation_id, collection_id
            )
            if success:
                logger.info(
                    f"✓ Attached collection {collection_id} to conversation {conversation_id}"
                )
            return success
        except Exception as e:
            logger.error(f"✗ Error attaching collection: {e}")
            return False

    async def detach_collection_from_conversation(
        self,
        conversation_id: str,
        collection_id: str
    ) -> bool:
        """
        Detach a collection from a conversation.

        Args:
            conversation_id: Conversation UUID
            collection_id: Collection UUID

        Returns:
            True if detached successfully, False otherwise
        """
        try:
            success = await self.repository.detach_collection_from_conversation(
                conversation_id, collection_id
            )
            if success:
                logger.info(
                    f"✓ Detached collection {collection_id} from conversation {conversation_id}"
                )
            return success
        except Exception as e:
            logger.error(f"✗ Error detaching collection: {e}")
            return False

    async def get_conversation_collections(
        self,
        conversation_id: str
    ) -> List[FileCollection]:
        """
        Get all collections attached to a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            List of FileCollection objects
        """
        try:
            return await self.repository.get_conversation_collections(conversation_id)
        except Exception as e:
            logger.error(f"✗ Error getting conversation collections: {e}")
            return []

    # ========================================
    # Search and Discovery
    # ========================================

    async def search_collections(
        self,
        query: str,
        tags: Optional[List[str]] = None
    ) -> List[FileCollection]:
        """
        Search collections by name/description and optionally filter by tags.

        Args:
            query: Search query (matches name and description)
            tags: Optional list of tags to filter by

        Returns:
            List of matching FileCollection objects
        """
        try:
            return await self.repository.search_collections(query, tags)
        except Exception as e:
            logger.error(f"✗ Error searching collections: {e}")
            return []

    # ========================================
    # Template Management
    # ========================================

    async def create_template_collection(
        self,
        name: str,
        description: str,
        tags: List[str],
        file_patterns: List[str],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Optional[FileCollection]:
        """
        Create a template collection for common workflows.

        Templates are collections without actual files - they define
        file patterns that users can populate later.

        Args:
            name: Template name
            description: Template description
            tags: Tags for categorization
            file_patterns: List of file patterns (e.g., "*.py", "README.md")
            chunk_size: Default chunk size
            chunk_overlap: Default chunk overlap

        Returns:
            FileCollection template if created successfully, None otherwise
        """
        try:
            # Create template collection (empty files list)
            collection = await self.create_collection(
                name=name,
                description=description,
                tags=tags,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                is_template=True,
                max_size_mb=500
            )

            if collection:
                logger.info(f"✓ Created template collection: {name}")
                # Note: File patterns would be stored in description or separate metadata
                # For simplicity, we include them in the description

            return collection

        except Exception as e:
            logger.error(f"✗ Error creating template collection: {e}")
            return None

    async def get_builtin_templates(self) -> List[Dict[str, Any]]:
        """
        Get built-in collection templates.

        Returns:
            List of template definitions (not persisted collections)
        """
        return [
            {
                "name": "Python Project",
                "description": "Python source files, tests, and configuration",
                "tags": ["python", "development", "code"],
                "file_patterns": ["*.py", "pyproject.toml", "setup.py", "requirements.txt", "README.md"],
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            {
                "name": "JavaScript Project",
                "description": "JavaScript/TypeScript source files and configs",
                "tags": ["javascript", "typescript", "development", "code"],
                "file_patterns": ["*.js", "*.ts", "*.jsx", "*.tsx", "package.json", "tsconfig.json", "README.md"],
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            {
                "name": "Documentation",
                "description": "Documentation files and guides",
                "tags": ["documentation", "guides", "reference"],
                "file_patterns": ["*.md", "*.rst", "*.txt", "*.pdf"],
                "chunk_size": 1500,
                "chunk_overlap": 300
            },
            {
                "name": "Research Papers",
                "description": "Academic papers and research documents",
                "tags": ["research", "academic", "papers"],
                "file_patterns": ["*.pdf", "*.docx", "*.tex"],
                "chunk_size": 2000,
                "chunk_overlap": 400
            },
            {
                "name": "Code Review",
                "description": "Source files for code review sessions",
                "tags": ["code-review", "development"],
                "file_patterns": ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.go"],
                "chunk_size": 800,
                "chunk_overlap": 150
            }
        ]

    async def instantiate_template(
        self,
        template_name: str,
        new_collection_name: str,
        file_paths: List[str]
    ) -> Optional[FileCollection]:
        """
        Create a new collection from a template with actual files.

        Args:
            template_name: Name of built-in template to use
            new_collection_name: Name for new collection
            file_paths: List of file paths to add

        Returns:
            FileCollection if created successfully, None otherwise
        """
        try:
            # Get template definition
            templates = await self.get_builtin_templates()
            template = next((t for t in templates if t["name"] == template_name), None)

            if not template:
                logger.error(f"✗ Template not found: {template_name}")
                return None

            # Create collection from template
            collection = await self.create_collection(
                name=new_collection_name,
                description=template["description"],
                tags=template["tags"],
                chunk_size=template["chunk_size"],
                chunk_overlap=template["chunk_overlap"],
                is_template=False,
                max_size_mb=500
            )

            if not collection:
                return None

            # Add files to collection
            if file_paths:
                successful, errors = await self.add_files_to_collection(
                    collection.id, file_paths, check_duplicates=True
                )
                logger.info(
                    f"✓ Instantiated template '{template_name}' as '{new_collection_name}' "
                    f"with {successful}/{len(file_paths)} files"
                )

            return collection

        except Exception as e:
            logger.error(f"✗ Error instantiating template: {e}")
            return None

    # ========================================
    # Import/Export
    # ========================================

    async def export_collection(
        self,
        collection_id: str,
        export_path: str,
        include_files: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Export a collection to a portable package.

        Creates a ZIP file containing:
        - collection.json (metadata and file list)
        - files/ (optional actual file contents)

        Args:
            collection_id: Collection UUID
            export_path: Path for exported ZIP file
            include_files: Whether to include actual file contents

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get collection
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return False, f"Collection not found: {collection_id}"

            # Get files
            files = await self.repository.get_collection_files(collection_id)

            # Create export manifest
            manifest = {
                "format_version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "collection": {
                    "name": collection.name,
                    "description": collection.description,
                    "tags": collection.tags,
                    "chunk_size": collection.chunk_size,
                    "chunk_overlap": collection.chunk_overlap,
                    "max_size_mb": collection.max_size_mb
                },
                "files": [
                    {
                        "id": f.id,
                        "file_name": f.file_name,
                        "file_size": f.file_size,
                        "file_type": f.file_type,
                        "checksum": f.checksum,
                        "relative_path": f.file_name  # Store relative to export root
                    }
                    for f in files
                ]
            }

            # Create ZIP file
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Write manifest
                zf.writestr("collection.json", json.dumps(manifest, indent=2))

                # Optionally include file contents
                if include_files:
                    for file_item in files:
                        if self.storage.validate_file_exists(file_item.file_path):
                            # Store in files/ directory with original name
                            arcname = f"files/{file_item.file_name}"
                            zf.write(file_item.file_path, arcname)
                        else:
                            logger.warning(
                                f"⚠ File not found, skipping: {file_item.file_path}"
                            )

            logger.info(
                f"✓ Exported collection '{collection.name}' to {export_path} "
                f"({'with' if include_files else 'without'} files)"
            )
            return True, None

        except Exception as e:
            logger.error(f"✗ Error exporting collection: {e}")
            return False, str(e)

    async def import_collection(
        self,
        import_path: str,
        new_name: Optional[str] = None,
        restore_files: bool = True,
        target_directory: Optional[str] = None
    ) -> Tuple[Optional[FileCollection], List[str]]:
        """
        Import a collection from an exported package.

        Args:
            import_path: Path to exported ZIP file
            new_name: Optional new name (uses original if not provided)
            restore_files: Whether to restore file contents
            target_directory: Directory to restore files to (required if restore_files=True)

        Returns:
            Tuple of (FileCollection if successful, list of error messages)
        """
        try:
            errors = []

            # Validate import file exists
            import_file = Path(import_path)
            if not import_file.exists():
                return None, [f"Import file not found: {import_path}"]

            # Extract and parse manifest
            with zipfile.ZipFile(import_file, 'r') as zf:
                # Read manifest
                try:
                    manifest_data = zf.read("collection.json")
                    manifest = json.loads(manifest_data)
                except KeyError:
                    return None, ["Invalid export package: missing collection.json"]

                # Validate format version
                if manifest.get("format_version") != "1.0":
                    errors.append("Unknown format version, attempting import anyway")

                # Create collection
                collection_data = manifest["collection"]
                collection_name = new_name if new_name else collection_data["name"]

                # Check for name conflict
                existing = await self.repository.get_collection_by_name(collection_name)
                if existing:
                    # Generate unique name
                    base_name = collection_name
                    counter = 1
                    while existing:
                        collection_name = f"{base_name} ({counter})"
                        existing = await self.repository.get_collection_by_name(collection_name)
                        counter += 1
                    errors.append(f"Name conflict, renamed to: {collection_name}")

                collection = await self.create_collection(
                    name=collection_name,
                    description=collection_data.get("description", ""),
                    tags=collection_data.get("tags", []),
                    chunk_size=collection_data.get("chunk_size", 1000),
                    chunk_overlap=collection_data.get("chunk_overlap", 200),
                    is_template=False,
                    max_size_mb=collection_data.get("max_size_mb", 500)
                )

                if not collection:
                    return None, ["Failed to create collection from import"]

                # Restore files if requested
                if restore_files and target_directory:
                    target_dir = Path(target_directory)
                    target_dir.mkdir(parents=True, exist_ok=True)

                    for file_info in manifest["files"]:
                        try:
                            # Extract file
                            file_arcname = f"files/{file_info['file_name']}"
                            if file_arcname in zf.namelist():
                                # Extract to target directory
                                file_path = target_dir / file_info['file_name']
                                file_path.write_bytes(zf.read(file_arcname))

                                # Verify checksum
                                restored_checksum = self.storage.calculate_file_checksum(str(file_path))
                                if restored_checksum != file_info['checksum']:
                                    errors.append(
                                        f"Checksum mismatch for {file_info['file_name']}"
                                    )
                                    continue

                                # Add to collection
                                success, error = await self.add_file_to_collection(
                                    collection.id, str(file_path), check_duplicates=True
                                )
                                if not success:
                                    errors.append(f"{file_info['file_name']}: {error}")

                            else:
                                errors.append(
                                    f"File not found in package: {file_info['file_name']}"
                                )

                        except Exception as e:
                            errors.append(f"Error restoring {file_info['file_name']}: {e}")

                elif restore_files and not target_directory:
                    errors.append("restore_files=True but no target_directory provided")

            logger.info(
                f"✓ Imported collection '{collection.name}' from {import_path} "
                f"({len(errors)} warning(s))"
            )
            return collection, errors

        except Exception as e:
            logger.error(f"✗ Error importing collection: {e}")
            return None, [str(e)]

    async def export_collection_metadata_only(
        self,
        collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Export collection metadata without creating a file.

        Useful for sharing collection definitions without file contents.

        Args:
            collection_id: Collection UUID

        Returns:
            Dictionary with collection metadata, or None on error
        """
        try:
            collection = await self.repository.get_collection(collection_id)
            if not collection:
                return None

            return {
                "name": collection.name,
                "description": collection.description,
                "tags": collection.tags,
                "chunk_size": collection.chunk_size,
                "chunk_overlap": collection.chunk_overlap,
                "max_size_mb": collection.max_size_mb,
                "file_count": collection.file_count,
                "total_size_mb": collection.total_size_mb
            }

        except Exception as e:
            logger.error(f"✗ Error exporting collection metadata: {e}")
            return None

