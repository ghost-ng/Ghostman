"""
UI integration components for conversation management.

Provides integration points with existing UI components and new conversation management widgets.
"""

from .repl_integration import ConversationREPLWidget
from .conversation_list import ConversationListWidget
from .conversation_browser import ConversationBrowserDialog
from .search_widget import ConversationSearchWidget

__all__ = [
    'ConversationREPLWidget',
    'ConversationListWidget', 
    'ConversationBrowserDialog',
    'ConversationSearchWidget'
]