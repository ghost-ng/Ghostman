"""
Data models for OpenAI Files API integration.

Provides structured representations of files, vector stores, and related
OpenAI API entities for type safety and easier data handling.
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger("ghostman.file_models")


class FilePurpose(Enum):
    """OpenAI file purpose types."""
    ASSISTANTS = "assistants"
    ASSISTANTS_OUTPUT = "assistants_output"
    BATCH = "batch"
    BATCH_OUTPUT = "batch_output"
    FINE_TUNE = "fine-tune"
    FINE_TUNE_RESULTS = "fine-tune-results"
    VISION = "vision"


class FileStatus(Enum):
    """File processing status."""
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    ERROR = "error"


class VectorStoreStatus(Enum):
    """Vector store status types."""
    EXPIRED = "expired"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class VectorStoreFileStatus(Enum):
    """Vector store file status types."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class FileUploadProgress:
    """Progress tracking for file uploads."""
    file_path: str
    file_size: int
    bytes_uploaded: int = 0
    percentage: float = 0.0
    speed_bytes_per_sec: float = 0.0
    eta_seconds: Optional[float] = None
    status: str = "uploading"
    error: Optional[str] = None
    
    def update_progress(self, bytes_uploaded: int, speed: float = 0.0):
        """Update upload progress."""
        self.bytes_uploaded = min(bytes_uploaded, self.file_size)
        self.percentage = (self.bytes_uploaded / self.file_size) * 100.0
        self.speed_bytes_per_sec = speed
        
        if speed > 0:
            remaining_bytes = self.file_size - self.bytes_uploaded
            self.eta_seconds = remaining_bytes / speed
        else:
            self.eta_seconds = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for callbacks."""
        return {
            "file_path": self.file_path,
            "file_size": self.file_size,
            "bytes_uploaded": self.bytes_uploaded,
            "percentage": self.percentage,
            "speed_bytes_per_sec": self.speed_bytes_per_sec,
            "eta_seconds": self.eta_seconds,
            "status": self.status,
            "error": self.error
        }


@dataclass
class OpenAIFile:
    """Represents an OpenAI file object."""
    id: str
    object: str
    bytes: int
    created_at: int
    filename: str
    purpose: str
    status: Optional[str] = None
    status_details: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'OpenAIFile':
        """Create instance from API response data."""
        return cls(
            id=data["id"],
            object=data["object"],
            bytes=data["bytes"],
            created_at=data["created_at"],
            filename=data["filename"],
            purpose=data["purpose"],
            status=data.get("status"),
            status_details=data.get("status_details")
        )
    
    @property
    def created_datetime(self) -> datetime:
        """Get creation time as datetime."""
        return datetime.fromtimestamp(self.created_at)
    
    @property
    def size_mb(self) -> float:
        """Get file size in MB."""
        return self.bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": self.object,
            "bytes": self.bytes,
            "created_at": self.created_at,
            "filename": self.filename,
            "purpose": self.purpose,
            "status": self.status,
            "status_details": self.status_details
        }


@dataclass
class VectorStoreFileCounts:
    """Vector store file counts."""
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'VectorStoreFileCounts':
        """Create instance from API response data."""
        return cls(
            in_progress=data.get("in_progress", 0),
            completed=data.get("completed", 0),
            failed=data.get("failed", 0),
            cancelled=data.get("cancelled", 0),
            total=data.get("total", 0)
        )


@dataclass
class VectorStore:
    """Represents an OpenAI vector store object."""
    id: str
    object: str
    created_at: int
    name: Optional[str] = None
    usage_bytes: int = 0
    file_counts: Optional[VectorStoreFileCounts] = None
    status: Optional[str] = None
    expires_after: Optional[Dict[str, Any]] = None
    expires_at: Optional[int] = None
    last_active_at: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'VectorStore':
        """Create instance from API response data."""
        file_counts = None
        if "file_counts" in data:
            file_counts = VectorStoreFileCounts.from_api_response(data["file_counts"])
        
        return cls(
            id=data["id"],
            object=data["object"],
            created_at=data["created_at"],
            name=data.get("name"),
            usage_bytes=data.get("usage_bytes", 0),
            file_counts=file_counts,
            status=data.get("status"),
            expires_after=data.get("expires_after"),
            expires_at=data.get("expires_at"),
            last_active_at=data.get("last_active_at"),
            metadata=data.get("metadata")
        )
    
    @property
    def created_datetime(self) -> datetime:
        """Get creation time as datetime."""
        return datetime.fromtimestamp(self.created_at)
    
    @property
    def expires_datetime(self) -> Optional[datetime]:
        """Get expiration time as datetime."""
        if self.expires_at:
            return datetime.fromtimestamp(self.expires_at)
        return None
    
    @property
    def last_active_datetime(self) -> Optional[datetime]:
        """Get last active time as datetime."""
        if self.last_active_at:
            return datetime.fromtimestamp(self.last_active_at)
        return None
    
    @property
    def usage_mb(self) -> float:
        """Get usage in MB."""
        return self.usage_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": self.object,
            "created_at": self.created_at,
            "name": self.name,
            "usage_bytes": self.usage_bytes,
            "file_counts": self.file_counts.__dict__ if self.file_counts else None,
            "status": self.status,
            "expires_after": self.expires_after,
            "expires_at": self.expires_at,
            "last_active_at": self.last_active_at,
            "metadata": self.metadata
        }


@dataclass
class VectorStoreFile:
    """Represents a file in a vector store."""
    id: str
    object: str
    usage_bytes: int
    created_at: int
    vector_store_id: str
    status: str
    last_error: Optional[Dict[str, Any]] = None
    chunking_strategy: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'VectorStoreFile':
        """Create instance from API response data."""
        return cls(
            id=data["id"],
            object=data["object"],
            usage_bytes=data["usage_bytes"],
            created_at=data["created_at"],
            vector_store_id=data["vector_store_id"],
            status=data["status"],
            last_error=data.get("last_error"),
            chunking_strategy=data.get("chunking_strategy")
        )
    
    @property
    def created_datetime(self) -> datetime:
        """Get creation time as datetime."""
        return datetime.fromtimestamp(self.created_at)
    
    @property
    def usage_mb(self) -> float:
        """Get usage in MB."""
        return self.usage_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": self.object,
            "usage_bytes": self.usage_bytes,
            "created_at": self.created_at,
            "vector_store_id": self.vector_store_id,
            "status": self.status,
            "last_error": self.last_error,
            "chunking_strategy": self.chunking_strategy
        }


@dataclass
class FileSearchTool:
    """File search tool configuration for chat completions."""
    type: str = "file_search"
    ranking_options: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        result = {"type": self.type}
        if self.ranking_options:
            result["file_search"] = {"ranking_options": self.ranking_options}
        return result


@dataclass
class ToolResources:
    """Tool resources configuration for chat completions."""
    file_search: Optional[Dict[str, Any]] = None
    code_interpreter: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        result = {}
        if self.file_search:
            result["file_search"] = self.file_search
        if self.code_interpreter:
            result["code_interpreter"] = self.code_interpreter
        return result


@dataclass
class FileSearchResult:
    """Result from file search operation."""
    file_id: str
    filename: str
    score: float
    content: str
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'FileSearchResult':
        """Create instance from API response data."""
        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            score=data["score"],
            content=data["content"]
        )


# Type aliases for progress callbacks
ProgressCallback = Callable[[FileUploadProgress], None]
ErrorCallback = Callable[[str, Exception], None]


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    success: bool
    data: Optional[Union[OpenAIFile, VectorStore, VectorStoreFile, List[OpenAIFile]]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "error": self.error,
            "status_code": self.status_code
        }
        
        if self.data:
            if hasattr(self.data, 'to_dict'):
                result["data"] = self.data.to_dict()
            elif isinstance(self.data, list):
                result["data"] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.data]
            else:
                result["data"] = self.data
        
        return result


def validate_file_purpose(purpose: str) -> bool:
    """Validate if a file purpose is supported."""
    try:
        FilePurpose(purpose)
        return True
    except ValueError:
        return False


def get_supported_file_extensions() -> List[str]:
    """Get list of supported file extensions for uploads."""
    return [
        ".txt", ".md", ".pdf", ".doc", ".docx", 
        ".csv", ".json", ".jsonl", ".xml", ".html",
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h",
        ".sql", ".yaml", ".yml", ".toml", ".ini", ".cfg"
    ]


def validate_file_for_upload(file_path: str, max_size_mb: int = 512) -> tuple[bool, Optional[str]]:
    """
    Validate a file for upload to OpenAI.
    
    Args:
        file_path: Path to the file to validate
        max_size_mb: Maximum file size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import os
    
    # Check if file exists
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if file_size > max_size_mb * 1024 * 1024:
            return False, f"File too large: {file_size / (1024*1024):.1f}MB (max: {max_size_mb}MB)"
    except OSError as e:
        return False, f"Cannot access file: {e}"
    
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    supported_extensions = get_supported_file_extensions()
    
    if file_ext not in supported_extensions:
        return False, f"Unsupported file type: {file_ext}. Supported: {', '.join(supported_extensions)}"
    
    return True, None