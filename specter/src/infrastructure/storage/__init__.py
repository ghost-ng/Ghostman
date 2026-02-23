"""
Storage infrastructure for Specter.

Provides settings management, file operations, and collection storage services.
"""

from .settings_manager import SettingsManager, settings
from .collection_storage import CollectionStorageService, collection_storage_service

__all__ = [
    'SettingsManager',
    'settings',
    'CollectionStorageService',
    'collection_storage_service',
]
