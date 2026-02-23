"""
Repository layer for conversation management.

Provides data access abstractions over SQLite database.
"""

from .conversation_repository import ConversationRepository
from .database import DatabaseManager

__all__ = ['ConversationRepository', 'DatabaseManager']