"""
Cursor Management System for Resize Operations.

Provides efficient cursor state management during resize operations.
"""

from typing import Dict, Optional
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget

from .hit_zones import HitZone


class CursorManager(QObject):
    """
    Manages cursor changes during resize operations.
    
    Provides efficient cursor state management with automatic restoration
    and optimized cursor updates to minimize visual flicker.
    """
    
    # Cursor mappings for each resize zone
    ZONE_CURSORS: Dict[HitZone, Qt.CursorShape] = {
        HitZone.NONE: Qt.CursorShape.ArrowCursor,
        HitZone.LEFT: Qt.CursorShape.SizeHorCursor,
        HitZone.RIGHT: Qt.CursorShape.SizeHorCursor,
        HitZone.TOP: Qt.CursorShape.SizeVerCursor,
        HitZone.BOTTOM: Qt.CursorShape.SizeVerCursor,
        HitZone.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
        HitZone.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
        HitZone.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
        HitZone.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    }
    
    def __init__(self, widget: QWidget):
        """
        Initialize the cursor manager.
        
        Args:
            widget: Widget to manage cursors for
        """
        super().__init__(widget)
        self.widget = widget
        self.current_zone = HitZone.NONE
        self.original_cursor: Optional[Qt.CursorShape] = None
        self.cursor_override_active = False
        
    def update_cursor(self, zone: HitZone):
        """
        Update cursor for the given hit zone.
        
        Args:
            zone: Hit zone to set cursor for
        """
        # Avoid unnecessary cursor changes for performance
        if zone == self.current_zone:
            return
        
        self.current_zone = zone
        
        # Get the cursor for this zone
        cursor_shape = self.ZONE_CURSORS.get(zone, Qt.CursorShape.ArrowCursor)
        
        # Store original cursor on first override
        if not self.cursor_override_active and zone != HitZone.NONE:
            self.original_cursor = self.widget.cursor().shape()
            self.cursor_override_active = True
        
        # Set the new cursor
        self.widget.setCursor(QCursor(cursor_shape))
        
        # If returning to normal zone, restore original cursor
        if zone == HitZone.NONE and self.cursor_override_active:
            self.restore_cursor()
    
    def restore_cursor(self):
        """Restore the original cursor."""
        if self.cursor_override_active:
            if self.original_cursor is not None:
                self.widget.setCursor(QCursor(self.original_cursor))
            else:
                self.widget.unsetCursor()
            
            self.cursor_override_active = False
            self.original_cursor = None
            self.current_zone = HitZone.NONE
    
    def is_resize_cursor_active(self) -> bool:
        """Check if a resize cursor is currently active."""
        return self.cursor_override_active and self.current_zone != HitZone.NONE
    
    def force_cursor_update(self):
        """Force a cursor update for the current zone."""
        current = self.current_zone
        self.current_zone = HitZone.NONE  # Reset to force update
        self.update_cursor(current)