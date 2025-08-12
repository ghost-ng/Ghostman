"""
Frameless Window Resize System for Ghostman.

This package provides a robust, cross-platform resize system for frameless PyQt6 windows.
"""

from .resize_manager import ResizeManager
from .resize_mixin import (
    ResizableMixin, 
    AvatarResizableMixin, 
    REPLResizableMixin,
    add_resize_to_widget,
    remove_resize_from_widget
)
from .hit_zones import HitZone, HitZoneDetector
from .constraints import SizeConstraints
from .cursor_manager import CursorManager
from .integration_helpers import (
    setup_avatar_resize,
    setup_repl_resize,
    update_resize_settings,
    get_resize_status_info
)

__all__ = [
    'ResizeManager',
    'ResizableMixin',
    'AvatarResizableMixin',
    'REPLResizableMixin',
    'add_resize_to_widget',
    'remove_resize_from_widget',
    'HitZone',
    'HitZoneDetector',
    'SizeConstraints',
    'CursorManager',
    'setup_avatar_resize',
    'setup_repl_resize',
    'update_resize_settings',
    'get_resize_status_info'
]