"""
AI Service Infrastructure for Ghostman.

Provides OpenAI-compatible API integration for AI functionality.
"""

from .ai_service import AIService, AIServiceError, AIConfigurationError
from .api_client import OpenAICompatibleClient

__all__ = [
    'AIService',
    'AIServiceError', 
    'AIConfigurationError',
    'OpenAICompatibleClient'
]