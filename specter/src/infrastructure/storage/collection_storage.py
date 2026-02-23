"""
Collection Storage Service for file validation and management.

This service handles pure file operations without database dependencies.
Provides file validation, checksum calculation, metadata extraction, and path resolution.
Follows the SettingsManager pattern for singleton infrastructure services.
"""

import hashlib
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("specter.collection_storage")


class CollectionStorageService:
    """
    File storage service for collection operations.

    Provides file validation, checksum calculation, metadata extraction,
    and path resolution WITHOUT database dependencies. This is a pure
    file operations layer that can be used independently.

    Features:
    - SHA256 checksum calculation (matches RAG pipeline pattern)
    - File existence and readability validation
    - File metadata extraction (size, type, modified time)
    - Collection size validation with limits
    - Path resolution and normalization (Windows-aware)
    - File integrity verification
    - Missing file detection

    Singleton pattern ensures consistent file operations across the application.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one instance."""
        if cls._instance is None:
            cls._instance = super(CollectionStorageService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the storage service."""
        if self._initialized:
            return

        self._initialized = True
        logger.debug("CollectionStorageService initialized")

    # --- Checksum Operations ---

    def calculate_file_checksum(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA256 checksum of a file.

        Uses 8KB chunks for efficient processing of large files.
        Matches the pattern used in RAG pipeline and FileCollectionItem.

        Args:
            file_path: Path to the file

        Returns:
            64-character hex digest of SHA256 hash, or None on error

        Example:
            >>> service = CollectionStorageService()
            >>> checksum = service.calculate_file_checksum("/path/to/file.txt")
            >>> print(len(checksum))
            64
        """
        try:
            logger.debug(f"📊 Calculating checksum for: {file_path}")

            path = Path(file_path)

            if not path.exists():
                logger.error(f"✗ File not found for checksum: {file_path}")
                return None

            if not path.is_file():
                logger.error(f"✗ Path is not a file: {file_path}")
                return None

            sha256 = hashlib.sha256()

            # Read in 8KB chunks (same as FileCollectionItem pattern)
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)

            checksum = sha256.hexdigest()
            logger.debug(f"✓ Checksum calculated: {checksum[:16]}...")
            return checksum

        except PermissionError as e:
            logger.error(f"✗ Permission denied reading file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Failed to calculate checksum for {file_path}: {e}")
            return None

    # --- File Validation ---

    def validate_file_exists(self, file_path: str) -> bool:
        """
        Validate that a file exists.

        Args:
            file_path: Path to validate

        Returns:
            True if file exists, False otherwise
        """
        try:
            path = Path(file_path)
            exists = path.exists() and path.is_file()

            if not exists:
                logger.debug(f"⚠ File does not exist: {file_path}")

            return exists

        except Exception as e:
            logger.error(f"✗ Error checking file existence {file_path}: {e}")
            return False

    def validate_file_readable(self, file_path: str) -> bool:
        """
        Validate that a file is readable.

        Attempts to open the file for reading to verify permissions.

        Args:
            file_path: Path to validate

        Returns:
            True if file is readable, False otherwise
        """
        try:
            path = Path(file_path)

            if not path.exists():
                logger.debug(f"⚠ File does not exist: {file_path}")
                return False

            if not path.is_file():
                logger.debug(f"⚠ Path is not a file: {file_path}")
                return False

            # Try to open and read first byte
            with open(path, 'rb') as f:
                f.read(1)

            return True

        except PermissionError:
            logger.warning(f"⚠ Permission denied reading file: {file_path}")
            return False
        except Exception as e:
            logger.error(f"✗ Error validating file readability {file_path}: {e}")
            return False

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract file metadata.

        Returns comprehensive metadata including size, type, name, and modification time.
        Uses mimetypes.guess_type() to determine MIME type (matches FileCollectionItem pattern).

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with keys: 'size', 'type', 'name', 'modified'
            Returns None on error

        Example:
            >>> metadata = service.get_file_metadata("/path/to/file.pdf")
            >>> print(metadata)
            {
                'size': 1024000,
                'type': 'application/pdf',
                'name': 'file.pdf',
                'modified': datetime(2025, 1, 1, 12, 0, 0)
            }
        """
        try:
            logger.debug(f"📋 Extracting metadata for: {file_path}")

            path = Path(file_path)

            if not path.exists():
                logger.error(f"✗ File not found: {file_path}")
                return None

            if not path.is_file():
                logger.error(f"✗ Path is not a file: {file_path}")
                return None

            # Get file stats
            stat = path.stat()

            # Determine MIME type (matches FileCollectionItem pattern)
            mime_type, _ = mimetypes.guess_type(str(path))
            file_type = mime_type or path.suffix or "application/octet-stream"

            metadata = {
                'size': stat.st_size,
                'type': file_type,
                'name': path.name,
                'modified': datetime.fromtimestamp(stat.st_mtime)
            }

            logger.debug(
                f"✓ Metadata extracted: {metadata['name']} "
                f"({metadata['size']} bytes, {metadata['type']})"
            )

            return metadata

        except PermissionError as e:
            logger.error(f"✗ Permission denied accessing file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Failed to extract metadata for {file_path}: {e}")
            return None

    # --- Collection Size Validation ---

    def validate_collection_size(
        self,
        files: List[Any],
        max_size_mb: int
    ) -> Tuple[bool, str]:
        """
        Validate that a collection is within size limits.

        Calculates total size of all files and compares to limit.
        Provides helpful error messages for debugging.

        Args:
            files: List of FileCollectionItem objects (must have file_size attribute)
            max_size_mb: Maximum allowed size in megabytes

        Returns:
            Tuple of (is_valid, message)
            - (True, "") if within limit
            - (False, "helpful error message") if exceeds limit

        Example:
            >>> is_valid, msg = service.validate_collection_size(files, 100)
            >>> if not is_valid:
            ...     print(msg)
            "Collection exceeds size limit: 150.5 MB > 100 MB"
        """
        try:
            logger.debug(f"📏 Validating collection size (limit: {max_size_mb} MB)")

            # Calculate total size in bytes
            total_bytes = 0
            for file_item in files:
                if hasattr(file_item, 'file_size'):
                    total_bytes += file_item.file_size
                else:
                    logger.warning(f"⚠ File item missing file_size attribute: {file_item}")

            total_mb = total_bytes / (1024 * 1024)
            max_bytes = max_size_mb * 1024 * 1024

            if total_bytes <= max_bytes:
                logger.debug(f"✓ Collection size OK: {total_mb:.2f} MB / {max_size_mb} MB")
                return True, ""

            error_msg = (
                f"Collection exceeds size limit: "
                f"{total_mb:.2f} MB > {max_size_mb} MB"
            )
            logger.warning(f"⚠ {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Error validating collection size: {e}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg

    # --- Path Resolution ---

    def resolve_absolute_path(self, file_path: str) -> Optional[str]:
        """
        Resolve to absolute path.

        Handles relative paths, normalizes Windows paths, and follows symlinks.
        Returns normalized absolute path with proper separators for the platform.

        Args:
            file_path: Path to resolve (can be relative or absolute)

        Returns:
            Absolute path as string, or None on error

        Example:
            >>> service.resolve_absolute_path("../data/file.txt")
            "C:\\Users\\miguel\\Documents\\data\\file.txt"
        """
        try:
            path = Path(file_path)

            # resolve() makes path absolute and follows symlinks
            absolute_path = path.resolve()

            logger.debug(f"🔗 Resolved path: {file_path} -> {absolute_path}")
            return str(absolute_path)

        except Exception as e:
            logger.error(f"✗ Failed to resolve path {file_path}: {e}")
            return None

    def make_relative_path(self, file_path: str, base_path: str) -> Optional[str]:
        """
        Make a path relative to a base path.

        Useful for export functionality where you want portable relative paths
        instead of absolute machine-specific paths.

        Args:
            file_path: Path to make relative
            base_path: Base path to make it relative to

        Returns:
            Relative path as string, or None if paths are on different drives
            or if an error occurs

        Example:
            >>> service.make_relative_path(
            ...     "C:\\Users\\miguel\\Documents\\data\\file.txt",
            ...     "C:\\Users\\miguel\\Documents"
            ... )
            "data\\file.txt"
        """
        try:
            file_path_obj = Path(file_path).resolve()
            base_path_obj = Path(base_path).resolve()

            # relative_to() raises ValueError if paths are on different drives
            relative_path = file_path_obj.relative_to(base_path_obj)

            logger.debug(f"🔗 Made relative: {file_path} -> {relative_path} (base: {base_path})")
            return str(relative_path)

        except ValueError:
            logger.warning(
                f"⚠ Cannot make path relative: {file_path} is not relative to {base_path} "
                "(possibly on different drives)"
            )
            return None
        except Exception as e:
            logger.error(f"✗ Failed to make path relative: {e}")
            return None

    # --- File Integrity ---

    def verify_file_integrity(
        self,
        file_path: str,
        expected_checksum: str
    ) -> bool:
        """
        Verify file integrity by comparing checksums.

        Calculates current checksum and compares to expected value.
        Useful for detecting file corruption or modifications.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected SHA256 checksum (64-char hex)

        Returns:
            True if checksums match, False otherwise

        Example:
            >>> is_valid = service.verify_file_integrity(
            ...     "/path/to/file.txt",
            ...     "abc123..."
            ... )
            >>> if not is_valid:
            ...     print("File has been modified or corrupted!")
        """
        try:
            logger.debug(f"🔒 Verifying integrity: {file_path}")

            current_checksum = self.calculate_file_checksum(file_path)

            if current_checksum is None:
                logger.error(f"✗ Cannot verify integrity: failed to calculate checksum")
                return False

            if current_checksum == expected_checksum:
                logger.debug(f"✓ File integrity verified: {file_path}")
                return True

            logger.warning(
                f"⚠ File integrity check FAILED: {file_path}\n"
                f"  Expected: {expected_checksum[:16]}...\n"
                f"  Got:      {current_checksum[:16]}..."
            )
            return False

        except Exception as e:
            logger.error(f"✗ Error verifying file integrity {file_path}: {e}")
            return False

    def find_missing_files(self, collection: Any) -> List[str]:
        """
        Find missing files in a collection.

        Checks each file in the collection and returns list of missing file paths.
        Useful for validating collections after files have been moved or deleted.

        Args:
            collection: FileCollection domain model (must have 'files' attribute)

        Returns:
            List of file paths that are missing (empty list if all files exist)

        Example:
            >>> missing = service.find_missing_files(collection)
            >>> if missing:
            ...     print(f"Missing files: {', '.join(missing)}")
        """
        try:
            logger.debug(f"🔍 Checking for missing files in collection")

            missing_files = []

            if not hasattr(collection, 'files'):
                logger.error(f"✗ Collection object missing 'files' attribute")
                return []

            for file_item in collection.files:
                if not hasattr(file_item, 'file_path'):
                    logger.warning(f"⚠ File item missing file_path attribute")
                    continue

                if not self.validate_file_exists(file_item.file_path):
                    missing_files.append(file_item.file_path)
                    logger.warning(f"⚠ Missing file: {file_item.file_path}")

            if missing_files:
                logger.warning(f"⚠ Found {len(missing_files)} missing files")
            else:
                logger.debug(f"✓ All files exist")

            return missing_files

        except Exception as e:
            logger.error(f"✗ Error finding missing files: {e}")
            return []


# Global singleton instance
collection_storage_service = CollectionStorageService()
