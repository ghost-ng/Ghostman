"""Shared models for services."""

from dataclasses import dataclass

@dataclass
class SimpleMessage:
    """Simple message structure for AI service."""
    content: str
    is_user: bool