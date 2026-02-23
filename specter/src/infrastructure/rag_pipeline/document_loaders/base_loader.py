"""
Base Document Loader

Abstract base class and common interfaces for all document loaders in the RAG pipeline.
Provides consistent structure for loading, processing, and extracting metadata from documents.
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from urllib.parse import urlparse

logger = logging.getLogger("specter.document_loader")


@dataclass
class DocumentMetadata:
    """Metadata associated with a document."""
    source: str  # File path, URL, or identifier
    source_type: str  # file, url, text, etc.
    filename: Optional[str] = None
    file_extension: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    
    # Content metadata
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    
    # Processing metadata
    loader_type: Optional[str] = None
    processing_time: Optional[float] = None
    extraction_method: Optional[str] = None
    encoding: Optional[str] = None
    
    # Additional custom metadata
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        result = {}
        
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """Create metadata from dictionary."""
        # Convert datetime strings back to datetime objects
        datetime_fields = ['created_at', 'modified_at', 'accessed_at']
        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    data[field] = None
        
        return cls(**data)


@dataclass
class Document:
    """A document with content and metadata."""
    content: str
    metadata: DocumentMetadata
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate content hash if not provided."""
        if self.content_hash is None:
            self.content_hash = self.generate_hash()
        
        # Update character count
        self.metadata.char_count = len(self.content)
        
        # Estimate word count
        if self.content:
            self.metadata.word_count = len(self.content.split())
    
    def generate_hash(self) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            'content': self.content,
            'metadata': self.metadata.to_dict(),
            'content_hash': self.content_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary."""
        metadata = DocumentMetadata.from_dict(data['metadata'])
        return cls(
            content=data['content'],
            metadata=metadata,
            content_hash=data.get('content_hash')
        )


class DocumentLoadError(Exception):
    """Exception raised when document loading fails."""
    def __init__(self, message: str, source: str, cause: Optional[Exception] = None):
        self.message = message
        self.source = source
        self.cause = cause
        super().__init__(f"Failed to load document '{source}': {message}")


class BaseDocumentLoader(ABC):
    """
    Abstract base class for document loaders.
    
    All document loaders should inherit from this class and implement the
    abstract methods for loading documents with proper error handling and metadata extraction.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the document loader.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Performance tracking
        self._stats = {
            'documents_loaded': 0,
            'documents_failed': 0,
            'total_processing_time': 0.0,
            'total_content_size': 0,
        }
    
    @abstractmethod
    async def load(self, source: Union[str, Path]) -> Document:
        """
        Load a single document from the source.
        
        Args:
            source: Path to file, URL, or other identifier
            
        Returns:
            Document object with content and metadata
            
        Raises:
            DocumentLoadError: If loading fails
        """
        pass
    
    @abstractmethod
    def supports(self, source: Union[str, Path]) -> bool:
        """
        Check if this loader supports the given source.
        
        Args:
            source: Path to file, URL, or other identifier
            
        Returns:
            True if this loader can handle the source
        """
        pass
    
    async def load_batch(self, sources: List[Union[str, Path]], 
                        max_concurrent: int = 5) -> List[Optional[Document]]:
        """
        Load multiple documents concurrently.
        
        Args:
            sources: List of sources to load
            max_concurrent: Maximum concurrent loading operations
            
        Returns:
            List of Document objects (None for failed loads)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def load_with_semaphore(source):
            async with semaphore:
                try:
                    return await self.load(source)
                except Exception as e:
                    self.logger.error(f"Failed to load {source}: {e}")
                    self._stats['documents_failed'] += 1
                    return None
        
        results = await asyncio.gather(*[load_with_semaphore(source) for source in sources])
        return results
    
    def get_metadata_from_path(self, path: Union[str, Path]) -> DocumentMetadata:
        """
        Extract basic metadata from file path.
        
        Args:
            path: Path to the file
            
        Returns:
            DocumentMetadata with basic information
        """
        path = Path(path)
        
        # Get file stats if file exists
        file_size = None
        created_at = None
        modified_at = None
        
        if path.exists():
            try:
                stat = path.stat()
                file_size = stat.st_size
                created_at = datetime.fromtimestamp(stat.st_ctime)
                modified_at = datetime.fromtimestamp(stat.st_mtime)
            except OSError as e:
                self.logger.warning(f"Could not get file stats for {path}: {e}")
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        
        return DocumentMetadata(
            source=str(path),
            source_type="file",
            filename=path.name,
            file_extension=path.suffix.lower(),
            mime_type=mime_type,
            file_size=file_size,
            created_at=created_at,
            modified_at=modified_at,
            accessed_at=datetime.now(),
            loader_type=self.__class__.__name__
        )
    
    def get_metadata_from_url(self, url: str) -> DocumentMetadata:
        """
        Extract basic metadata from URL.
        
        Args:
            url: URL to the resource
            
        Returns:
            DocumentMetadata with basic information
        """
        parsed = urlparse(url)
        filename = Path(parsed.path).name if parsed.path else None
        file_extension = Path(parsed.path).suffix.lower() if parsed.path else None
        
        return DocumentMetadata(
            source=url,
            source_type="url",
            filename=filename,
            file_extension=file_extension,
            accessed_at=datetime.now(),
            loader_type=self.__class__.__name__
        )
    
    def validate_source(self, source: Union[str, Path]) -> None:
        """
        Validate the source before loading.
        
        Args:
            source: Source to validate
            
        Raises:
            DocumentLoadError: If source is invalid
        """
        if isinstance(source, (str, Path)):
            path = Path(source)
            
            # Check if it's a file path
            if not str(source).startswith(('http://', 'https://')) and not path.exists():
                raise DocumentLoadError(f"File not found", str(source))
            
            # Check file size if it's a local file
            if path.exists():
                try:
                    size_mb = path.stat().st_size / (1024 * 1024)
                    max_size = self.config.get('max_file_size_mb', 50)
                    
                    if size_mb > max_size:
                        raise DocumentLoadError(
                            f"File size ({size_mb:.1f}MB) exceeds maximum ({max_size}MB)", 
                            str(source)
                        )
                except OSError as e:
                    raise DocumentLoadError(f"Cannot access file: {e}", str(source))
    
    def clean_content(self, content: str) -> str:
        """
        Clean and normalize content.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        # Remove excessive whitespace
        if self.config.get('normalize_whitespace', True):
            content = ' '.join(content.split())
        
        # Remove empty lines
        if self.config.get('remove_empty_lines', False):
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)
        
        # Normalize unicode
        if self.config.get('normalize_unicode', True):
            import unicodedata
            content = unicodedata.normalize('NFKC', content)
        
        return content.strip()
    
    def extract_title(self, content: str, metadata: DocumentMetadata) -> Optional[str]:
        """
        Extract title from content or metadata.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            Extracted title or None
        """
        # Try to get title from metadata first
        if metadata.title:
            return metadata.title
        
        # Try to extract from filename
        if metadata.filename:
            title = Path(metadata.filename).stem
            # Clean up the title
            title = title.replace('_', ' ').replace('-', ' ')
            return title.title()
        
        # Try to extract from first line of content
        if content:
            lines = content.strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                if first_line and len(first_line) < 200:
                    return first_line
        
        return None
    
    def detect_language(self, content: str) -> Optional[str]:
        """
        Detect the language of the content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Language code (e.g., 'en', 'es') or None
        """
        # This is a simple heuristic-based approach
        # For production, consider using langdetect or similar libraries
        
        if not content or len(content.strip()) < 50:
            return None
        
        # Simple keyword-based detection for common languages
        english_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        spanish_words = {'el', 'la', 'y', 'o', 'en', 'de', 'del', 'con', 'por', 'para', 'que', 'es'}
        
        words = set(word.lower() for word in content.split()[:100])
        
        english_score = len(words & english_words)
        spanish_score = len(words & spanish_words)
        
        if english_score > spanish_score and english_score > 2:
            return 'en'
        elif spanish_score > english_score and spanish_score > 2:
            return 'es'
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loader performance statistics."""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset performance statistics."""
        for key in self._stats:
            self._stats[key] = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(loaded={self._stats['documents_loaded']}, failed={self._stats['documents_failed']})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config})"


class MultiFormatLoader:
    """
    A loader that can handle multiple document formats by delegating to appropriate loaders.
    """
    
    def __init__(self, loaders: List[BaseDocumentLoader]):
        """
        Initialize with a list of document loaders.
        
        Args:
            loaders: List of document loaders to use
        """
        self.loaders = loaders
        self.logger = logging.getLogger(f"{__name__}.MultiFormatLoader")
    
    def get_loader(self, source: Union[str, Path]) -> Optional[BaseDocumentLoader]:
        """
        Find an appropriate loader for the source.
        
        Args:
            source: Source to load
            
        Returns:
            Loader that can handle the source, or None
        """
        for loader in self.loaders:
            if loader.supports(source):
                return loader
        return None
    
    async def load(self, source: Union[str, Path]) -> Document:
        """
        Load document using the appropriate loader.
        
        Args:
            source: Source to load
            
        Returns:
            Document object
            
        Raises:
            DocumentLoadError: If no suitable loader found or loading fails
        """
        loader = self.get_loader(source)
        if not loader:
            raise DocumentLoadError(
                f"No loader found for source type", 
                str(source)
            )
        
        return await loader.load(source)
    
    async def load_batch(self, sources: List[Union[str, Path]], 
                        max_concurrent: int = 5) -> List[Optional[Document]]:
        """
        Load multiple documents using appropriate loaders.
        
        Args:
            sources: List of sources to load
            max_concurrent: Maximum concurrent operations
            
        Returns:
            List of Document objects (None for failed loads)
        """
        # Group sources by loader
        loader_groups = {}
        for source in sources:
            loader = self.get_loader(source)
            if loader:
                if loader not in loader_groups:
                    loader_groups[loader] = []
                loader_groups[loader].append(source)
            else:
                self.logger.warning(f"No loader found for {source}")
        
        # Load each group
        all_results = []
        for loader, group_sources in loader_groups.items():
            results = await loader.load_batch(group_sources, max_concurrent)
            all_results.extend(results)
        
        return all_results