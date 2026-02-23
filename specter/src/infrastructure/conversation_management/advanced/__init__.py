"""
Advanced features for conversation management.

Provides additional features like templates, favorites, analytics, and plugins.
"""

from .templates import ConversationTemplateService
from .favorites import ConversationFavoriteService
from .analytics import ConversationAnalyticsService

__all__ = ['ConversationTemplateService', 'ConversationFavoriteService', 'ConversationAnalyticsService']