"""
Platform-specific Resize Handlers.

Provides optimized resize handling for different platforms with native integration
where possible and manual fallbacks.
"""

import sys
import logging
from abc import ABC, abstractmethod, ABCMeta
from typing import Optional, Tuple
from PyQt6.QtCore import QObject, QEvent, QPoint, QRect, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget

from .hit_zones import HitZone, HitZoneDetector
from .constraints import SizeConstraints

logger = logging.getLogger("ghostman.resize.platform")


class QObjectABCMeta(ABCMeta, type(QObject)):
    """Metaclass that combines ABC and QObject metaclasses."""
    pass


class BasePlatformHandler(QObject, ABC, metaclass=QObjectABCMeta):
    """Base class for platform-specific resize handlers."""
    
    def __init__(self, widget: QWidget, constraints: Optional[SizeConstraints] = None):
        """
        Initialize the platform handler.
        
        Args:
            widget: Widget to handle resizing for
            constraints: Size constraints to enforce
        """
        super().__init__(widget)
        self.widget = widget
        self.constraints = constraints or SizeConstraints()
        self.hit_detector = HitZoneDetector()
        
        # Resize state
        self.is_resizing = False
        self.resize_zone = HitZone.NONE
        self.resize_start_pos = QPoint()
        self.resize_start_geometry = QRect()
        
    @abstractmethod
    def install_handler(self) -> bool:
        """Install the platform-specific resize handler."""
        pass
    
    @abstractmethod
    def uninstall_handler(self):
        """Remove the platform-specific resize handler."""
        pass
    
    def get_hit_zone(self, point: QPoint) -> HitZone:
        """Get the hit zone for a point."""
        return self.hit_detector.get_hit_zone(point, self.widget.rect())
    
    def start_resize(self, zone: HitZone, start_pos: QPoint):
        """Start a resize operation."""
        if zone == HitZone.NONE:
            return
        
        self.is_resizing = True
        self.resize_zone = zone
        self.resize_start_pos = start_pos
        self.resize_start_geometry = self.widget.geometry()
        
        logger.debug(f"Started resize operation in zone: {zone}")
    
    def update_resize(self, current_pos: QPoint):
        """Update resize operation."""
        if not self.is_resizing or self.resize_zone == HitZone.NONE:
            return
        
        # Calculate delta from start position
        delta = current_pos - self.resize_start_pos
        
        # Calculate new geometry based on resize zone
        new_geometry = self._calculate_new_geometry(delta)
        
        # Apply constraints
        constrained_geometry = self._apply_constraints(new_geometry)
        
        # Update widget geometry
        self.widget.setGeometry(constrained_geometry)
    
    def end_resize(self):
        """End the current resize operation."""
        if self.is_resizing:
            logger.debug(f"Ended resize operation in zone: {self.resize_zone}")
        
        self.is_resizing = False
        self.resize_zone = HitZone.NONE
        self.resize_start_pos = QPoint()
        self.resize_start_geometry = QRect()
    
    def _calculate_new_geometry(self, delta: QPoint) -> QRect:
        """Calculate new geometry based on resize delta."""
        start_geo = self.resize_start_geometry
        zone = self.resize_zone
        
        # Start with original geometry
        x, y = start_geo.x(), start_geo.y()
        w, h = start_geo.width(), start_geo.height()
        
        dx, dy = delta.x(), delta.y()
        
        # Apply delta based on resize zone
        if zone in (HitZone.LEFT, HitZone.TOP_LEFT, HitZone.BOTTOM_LEFT):
            # Left edge - move x and adjust width
            x = start_geo.x() + dx
            w = start_geo.width() - dx
        
        if zone in (HitZone.RIGHT, HitZone.TOP_RIGHT, HitZone.BOTTOM_RIGHT):
            # Right edge - adjust width
            w = start_geo.width() + dx
        
        if zone in (HitZone.TOP, HitZone.TOP_LEFT, HitZone.TOP_RIGHT):
            # Top edge - move y and adjust height
            y = start_geo.y() + dy
            h = start_geo.height() - dy
        
        if zone in (HitZone.BOTTOM, HitZone.BOTTOM_LEFT, HitZone.BOTTOM_RIGHT):
            # Bottom edge - adjust height
            h = start_geo.height() + dy
        
        return QRect(x, y, w, h)
    
    def _apply_constraints(self, geometry: QRect) -> QRect:
        """Apply size constraints to geometry."""
        # Apply size constraints
        constrained_w, constrained_h = self.constraints.constrain_size(
            geometry.width(), geometry.height()
        )
        
        # Adjust position if we're resizing from top/left edges
        x, y = geometry.x(), geometry.y()
        
        # If width was constrained and we're resizing from left edge
        if (constrained_w != geometry.width() and 
            self.resize_zone in (HitZone.LEFT, HitZone.TOP_LEFT, HitZone.BOTTOM_LEFT)):
            x = geometry.right() - constrained_w
        
        # If height was constrained and we're resizing from top edge
        if (constrained_h != geometry.height() and 
            self.resize_zone in (HitZone.TOP, HitZone.TOP_LEFT, HitZone.TOP_RIGHT)):
            y = geometry.bottom() - constrained_h
        
        return QRect(x, y, constrained_w, constrained_h)


class WindowsHandler(BasePlatformHandler):
    """Windows-specific resize handler using native WM_NCHITTEST."""
    
    def __init__(self, widget: QWidget, constraints: Optional[SizeConstraints] = None):
        super().__init__(widget, constraints)
        self.native_event_installed = False
    
    def install_handler(self) -> bool:
        """Install Windows native resize handler."""
        try:
            # Install event filter for native events
            self.widget.winId()  # Ensure native window exists
            self.widget.installEventFilter(self)
            self.native_event_installed = True
            
            logger.debug("Windows native resize handler installed")
            return True
        except Exception as e:
            logger.error(f"Failed to install Windows handler: {e}")
            return False
    
    def uninstall_handler(self):
        """Remove Windows native resize handler."""
        if self.native_event_installed:
            self.widget.removeEventFilter(self)
            self.native_event_installed = False
            logger.debug("Windows native resize handler removed")
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter native Windows events."""
        if obj != self.widget:
            return False
        
        # Handle native Windows messages for resize
        if hasattr(event, 'nativeEvent'):
            return self._handle_native_event(event)
        
        return False
    
    def _handle_native_event(self, event) -> bool:
        """Handle native Windows WM_NCHITTEST messages."""
        try:
            # This would handle WM_NCHITTEST for native resize
            # For now, we'll use the manual handler approach
            return False
        except Exception as e:
            logger.debug(f"Native event handling failed: {e}")
            return False


class ManualHandler(BasePlatformHandler):
    """Manual resize handler using Qt events (cross-platform fallback)."""
    
    def __init__(self, widget: QWidget, constraints: Optional[SizeConstraints] = None):
        super().__init__(widget, constraints)
        self.event_filter_installed = False
    
    def install_handler(self) -> bool:
        """Install manual resize handler."""
        try:
            # Install event filter to handle mouse events
            self.widget.installEventFilter(self)
            
            # Enable mouse tracking for hover cursor changes
            self.widget.setMouseTracking(True)
            
            self.event_filter_installed = True
            logger.debug("Manual resize handler installed")
            return True
        except Exception as e:
            logger.error(f"Failed to install manual handler: {e}")
            return False
    
    def uninstall_handler(self):
        """Remove manual resize handler."""
        if self.event_filter_installed:
            self.widget.removeEventFilter(self)
            self.event_filter_installed = False
            logger.debug("Manual resize handler removed")
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter Qt events for manual resize handling."""
        if obj != self.widget:
            return False
        
        event_type = event.type()
        
        if event_type == QEvent.Type.MouseButtonPress:
            return self._handle_mouse_press(event)
        elif event_type == QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)
        elif event_type == QEvent.Type.MouseButtonRelease:
            return self._handle_mouse_release(event)
        
        return False
    
    def _handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        # Get hit zone for press position
        zone = self.get_hit_zone(event.position().toPoint())
        
        if zone != HitZone.NONE:
            # Start resize operation
            self.start_resize(zone, event.globalPosition().toPoint())
            return True  # Consume event
        
        return False
    
    def _handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if self.is_resizing:
            # Update resize operation
            self.update_resize(event.globalPosition().toPoint())
            return True  # Consume event
        
        return False
    
    def _handle_mouse_release(self, event: QMouseEvent) -> bool:
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_resizing:
            # End resize operation
            self.end_resize()
            return True  # Consume event
        
        return False


def create_platform_handler(
    widget: QWidget, 
    constraints: Optional[SizeConstraints] = None
) -> BasePlatformHandler:
    """
    Create the appropriate platform handler for the current system.
    
    Args:
        widget: Widget to handle resizing for
        constraints: Size constraints to enforce
        
    Returns:
        Platform-specific resize handler
    """
    platform = sys.platform.lower()
    
    # For now, always use manual handler for reliability
    # Windows native handler can be enabled later after more testing
    if platform.startswith('win') and False:  # Disabled for now
        handler = WindowsHandler(widget, constraints)
        if handler.install_handler():
            logger.debug("Using Windows native resize handler")
            return handler
        else:
            logger.debug("Windows handler failed, falling back to manual")
    
    # Use manual handler as default/fallback
    handler = ManualHandler(widget, constraints)
    if handler.install_handler():
        logger.debug("Using manual resize handler")
        return handler
    else:
        raise RuntimeError("Failed to install any resize handler")