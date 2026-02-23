"""
Enums for conversation management system.
"""

from enum import Enum, auto


class MessageRole(Enum):
    """Message roles in conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ConversationStatus(Enum):
    """Conversation status values."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    PINNED = "pinned"
    DELETED = "deleted"


class ExportFormat(Enum):
    """Export format options."""
    JSON = "json"
    TXT = "txt"
    MARKDOWN = "md"
    HTML = "html"


class SearchScope(Enum):
    """Search scope options."""
    ALL = "all"
    TITLE = "title"
    CONTENT = "content"
    TAGS = "tags"
    METADATA = "metadata"


class SortOrder(Enum):
    """Sorting options for conversations."""
    CREATED_ASC = "created_asc"
    CREATED_DESC = "created_desc"
    UPDATED_ASC = "updated_asc"  
    UPDATED_DESC = "updated_desc"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"
    MESSAGE_COUNT_ASC = "message_count_asc"
    MESSAGE_COUNT_DESC = "message_count_desc"