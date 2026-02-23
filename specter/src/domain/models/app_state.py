"""
Application State Models for Specter.

Defines the two primary states and state transitions for the application.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


class AppState(Enum):
    """Two primary application states."""
    AVATAR = "avatar"  # Maximized avatar mode with chat interface
    TRAY = "tray"      # Minimized tray mode, system tray only


class StateTransition(Enum):
    """Valid state transitions."""
    AVATAR_TO_TRAY = "avatar_to_tray"    # User minimizes to tray
    TRAY_TO_AVATAR = "tray_to_avatar"    # User opens from tray


@dataclass
class StateChangeEvent:
    """Represents a state change event with metadata."""
    from_state: AppState
    to_state: AppState
    transition: StateTransition
    timestamp: datetime
    trigger: str  # What triggered the transition (user_click, auto_restore, etc.)
    metadata: Optional[Dict[str, Any]] = None