"""
UI integration components for conversation management.

Provides integration points with existing UI components and new conversation management widgets.
"""

from .repl_integration import ConversationREPLWidget
from .conversation_browser import ConversationBrowserDialog

__all__ = [
    'ConversationREPLWidget',
    'ConversationBrowserDialog'
]