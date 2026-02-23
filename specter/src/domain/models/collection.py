"""
Domain models for File Collections.

Collections allow users to group files for reusable context across conversations.
These are pure domain models with no database or infrastructure dependencies.
"""

import hashlib
import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

logger = logging.getLogger("specter.domain.collection")


@dataclass
class FileCollectionItem:
    """
    Individual file within a collection.

    Represents a single file with its metadata and checksum for integrity verification.
    """
    file_path: str  # Absolute path to file
    file_name: str  # Display name (basename)
    file_size: int  # Size in bytes
    file_type: str  # MIME type or extension
    added_at: datetime  # When file was added to collection
    checksum: str  # SHA256 hash for integrity checking
    id: str = field(default_factory=lambda: str(uuid4()))  # Unique identifier

    @classmethod
    def create(
        cls,
        file_path: str,
        checksum: Optional[str] = None
    ) -> "FileCollectionItem":
        """
        Create a FileCollectionItem from a file path.

        Args:
            file_path: Path to the file
            checksum: Optional pre-computed checksum (will calculate if not provided)

        Returns:
            FileCollectionItem instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file path is invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Get file metadata
        stat = path.stat()
        file_name = path.name
        file_size = stat.st_size

        # Determine file type
        mime_type, _ = mimetypes.guess_type(str(path))
        file_type = mime_type or path.suffix or "application/octet-stream"

        # Calculate checksum if not provided
        if checksum is None:
            checksum = cls._calculate_checksum(str(path))

        return cls(
            file_path=str(path.resolve()),  # Store absolute path
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            added_at=datetime.now(),
            checksum=checksum
        )

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        """
        Calculate SHA256 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA256 hash (64 characters)
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'added_at': self.added_at.isoformat(),
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileCollectionItem":
        """Create from dictionary."""
        return cls(
            id=data['id'],
            file_path=data['file_path'],
            file_name=data['file_name'],
            file_size=data['file_size'],
            file_type=data['file_type'],
            added_at=datetime.fromisoformat(data['added_at']),
            checksum=data['checksum']
        )


@dataclass
class FileCollection:
    """
    A named collection of files for reusable context.

    Collections allow users to group related files together and attach them
    to conversations all at once. Each collection has its own RAG settings.
    """
    id: str
    name: str
    description: str
    files: List[FileCollectionItem]
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)

    # RAG settings per collection
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Metadata
    is_template: bool = False  # Template collections for quick start
    max_size_mb: int = 500  # Size limit in megabytes

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        is_template: bool = False,
        max_size_mb: int = 500
    ) -> "FileCollection":
        """
        Create a new file collection.

        Args:
            name: Collection name
            description: Optional description
            tags: Optional tags for organization
            chunk_size: Text chunk size for RAG (default 1000)
            chunk_overlap: Chunk overlap for RAG (default 200)
            is_template: Whether this is a template collection
            max_size_mb: Maximum total size in MB

        Returns:
            FileCollection instance
        """
        now = datetime.now()

        return cls(
            id=str(uuid4()),
            name=name,
            description=description,
            files=[],
            created_at=now,
            updated_at=now,
            tags=tags or [],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            is_template=is_template,
            max_size_mb=max_size_mb
        )

    @property
    def total_size(self) -> int:
        """Total size of all files in bytes."""
        return sum(f.file_size for f in self.files)

    @property
    def total_size_mb(self) -> float:
        """Total size of all files in megabytes."""
        return self.total_size / (1024 * 1024)

    @property
    def file_count(self) -> int:
        """Number of files in collection."""
        return len(self.files)

    def add_file(self, file_item: FileCollectionItem) -> bool:
        """
        Add a file to the collection.

        Args:
            file_item: FileCollectionItem to add

        Returns:
            True if added, False if duplicate (by checksum)
        """
        # Check for duplicate by checksum
        if any(f.checksum == file_item.checksum for f in self.files):
            logger.warning(f"File with checksum {file_item.checksum} already in collection {self.name}")
            return False

        # Check size limit
        new_total_size = self.total_size + file_item.file_size
        max_bytes = self.max_size_mb * 1024 * 1024

        if new_total_size > max_bytes:
            logger.warning(
                f"Adding file would exceed size limit: "
                f"{new_total_size / (1024 * 1024):.2f}MB > {self.max_size_mb}MB"
            )
            return False

        self.files.append(file_item)
        self.updated_at = datetime.now()
        logger.info(f"✓ Added file {file_item.file_name} to collection {self.name}")
        return True

    def remove_file(self, file_id: str) -> bool:
        """
        Remove a file from the collection by ID.

        Args:
            file_id: ID of file to remove

        Returns:
            True if removed, False if not found
        """
        original_count = len(self.files)
        self.files = [f for f in self.files if f.id != file_id]

        if len(self.files) < original_count:
            self.updated_at = datetime.now()
            logger.info(f"✓ Removed file {file_id} from collection {self.name}")
            return True

        logger.warning(f"File {file_id} not found in collection {self.name}")
        return False

    def remove_file_by_checksum(self, checksum: str) -> bool:
        """
        Remove a file from the collection by checksum.

        Args:
            checksum: SHA256 checksum of file to remove

        Returns:
            True if removed, False if not found
        """
        original_count = len(self.files)
        self.files = [f for f in self.files if f.checksum != checksum]

        if len(self.files) < original_count:
            self.updated_at = datetime.now()
            logger.info(f"✓ Removed file with checksum {checksum} from collection {self.name}")
            return True

        logger.warning(f"File with checksum {checksum} not found in collection {self.name}")
        return False

    def get_file_by_checksum(self, checksum: str) -> Optional[FileCollectionItem]:
        """
        Get file by checksum.

        Args:
            checksum: SHA256 checksum

        Returns:
            FileCollectionItem if found, None otherwise
        """
        for f in self.files:
            if f.checksum == checksum:
                return f
        return None

    def validate_size_limit(self) -> tuple[bool, str]:
        """
        Validate that collection is within size limit.

        Returns:
            Tuple of (is_valid, message)
        """
        max_bytes = self.max_size_mb * 1024 * 1024
        current_bytes = self.total_size

        if current_bytes <= max_bytes:
            return True, f"Collection size OK: {self.total_size_mb:.2f}MB / {self.max_size_mb}MB"

        return False, (
            f"Collection exceeds size limit: "
            f"{self.total_size_mb:.2f}MB > {self.max_size_mb}MB"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'files': [f.to_dict() for f in self.files],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': self.tags,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'is_template': self.is_template,
            'max_size_mb': self.max_size_mb,
            'total_size': self.total_size,
            'file_count': self.file_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileCollection":
        """Create from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            files=[FileCollectionItem.from_dict(f) for f in data['files']],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            tags=data.get('tags', []),
            chunk_size=data.get('chunk_size', 1000),
            chunk_overlap=data.get('chunk_overlap', 200),
            is_template=data.get('is_template', False),
            max_size_mb=data.get('max_size_mb', 500)
        )
