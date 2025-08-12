"""
Hit Zone Detection System for Frameless Window Resizing.

Provides efficient detection of resize zones around window edges and corners.
"""

from enum import Enum
from typing import Tuple, Optional
from PyQt6.QtCore import QPoint, QRect


class HitZone(Enum):
    """Defines the different resize zones around a window."""
    NONE = "none"
    
    # Edges
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    
    # Corners
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class HitZoneDetector:
    """
    Detects which resize zone a point is in relative to a widget.
    
    Provides efficient hit testing for resize operations with configurable
    border widths and optimized for high-frequency cursor tracking.
    """
    
    def __init__(self, border_width: int = 8):
        """
        Initialize the hit zone detector.
        
        Args:
            border_width: Width in pixels of the resize border around the window
        """
        self.border_width = border_width
        
        # Pre-calculate common values for performance
        self._double_border = border_width * 2
        
    def get_hit_zone(self, point: QPoint, widget_rect: QRect) -> HitZone:
        """
        Determine which resize zone a point falls into.
        
        Args:
            point: Point to test (in widget coordinates)
            widget_rect: Rectangle of the widget
            
        Returns:
            HitZone enum indicating which zone the point is in
        """
        x, y = point.x(), point.y()
        rect = widget_rect
        
        # Quick bounds check - if point is outside widget, return NONE
        if not rect.contains(point):
            return HitZone.NONE
        
        # Check if point is in the border region
        left_border = x <= self.border_width
        right_border = x >= rect.width() - self.border_width
        top_border = y <= self.border_width
        bottom_border = y >= rect.height() - self.border_width
        
        # Corner detection (highest priority)
        if top_border and left_border:
            return HitZone.TOP_LEFT
        elif top_border and right_border:
            return HitZone.TOP_RIGHT
        elif bottom_border and left_border:
            return HitZone.BOTTOM_LEFT
        elif bottom_border and right_border:
            return HitZone.BOTTOM_RIGHT
        
        # Edge detection
        elif top_border:
            return HitZone.TOP
        elif bottom_border:
            return HitZone.BOTTOM
        elif left_border:
            return HitZone.LEFT
        elif right_border:
            return HitZone.RIGHT
        
        # Point is inside the window
        return HitZone.NONE
    
    def is_resize_zone(self, zone: HitZone) -> bool:
        """Check if a zone allows resizing."""
        return zone != HitZone.NONE
    
    def get_resize_directions(self, zone: HitZone) -> Tuple[bool, bool]:
        """
        Get the resize directions for a zone.
        
        Returns:
            Tuple of (horizontal_resize, vertical_resize) booleans
        """
        if zone == HitZone.NONE:
            return False, False
        
        # Corner zones resize in both directions
        if zone in (HitZone.TOP_LEFT, HitZone.TOP_RIGHT, 
                   HitZone.BOTTOM_LEFT, HitZone.BOTTOM_RIGHT):
            return True, True
        
        # Edge zones resize in one direction
        if zone in (HitZone.LEFT, HitZone.RIGHT):
            return True, False
        elif zone in (HitZone.TOP, HitZone.BOTTOM):
            return False, True
        
        return False, False
    
    def set_border_width(self, width: int):
        """Update the border width for hit detection."""
        self.border_width = max(1, width)
        self._double_border = width * 2