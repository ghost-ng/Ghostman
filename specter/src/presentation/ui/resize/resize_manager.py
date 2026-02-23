"""
Central Resize Manager for Frameless Windows.

Coordinates all resize operations with platform-specific optimizations.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from .platform_handlers import BasePlatformHandler, create_platform_handler
from .cursor_manager import CursorManager
from .constraints import SizeConstraints
from .hit_zones import HitZone

logger = logging.getLogger("specter.resize.manager")


class ResizeManager(QObject):
    """
    Central coordinator for window resize operations.
    
    Manages platform-specific handlers, cursor updates, and constraint enforcement
    for frameless window resizing.
    """
    
    # Signals
    resize_started = pyqtSignal(HitZone)
    resize_updated = pyqtSignal(HitZone, int, int)  # zone, width, height
    resize_finished = pyqtSignal(HitZone, int, int)  # zone, width, height
    
    def __init__(
        self, 
        widget: QWidget, 
        constraints: Optional[SizeConstraints] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the resize manager.
        
        Args:
            widget: Widget to manage resizing for
            constraints: Size constraints to enforce
            config: Configuration options
        """
        super().__init__(widget)
        self.widget = widget
        self.constraints = constraints or SizeConstraints()
        self.config = config or {}
        
        # Core components
        self.platform_handler: Optional[BasePlatformHandler] = None
        self.cursor_manager: Optional[CursorManager] = None
        
        # State tracking
        self.is_enabled = True
        self.current_zone = HitZone.NONE
        
        # Configuration
        self.border_width = self.config.get('border_width', 8)
        self.enable_cursor_changes = self.config.get('enable_cursor_changes', True)
        
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all resize components."""
        try:
            # Create platform handler
            self.platform_handler = create_platform_handler(self.widget, self.constraints)
            
            # Create cursor manager if enabled
            if self.enable_cursor_changes:
                self.cursor_manager = CursorManager(self.widget)
            
            # Connect signals if platform handler supports them
            if hasattr(self.platform_handler, 'resize_started'):
                self.platform_handler.resize_started.connect(self._on_resize_started)
            if hasattr(self.platform_handler, 'resize_updated'):
                self.platform_handler.resize_updated.connect(self._on_resize_updated)
            if hasattr(self.platform_handler, 'resize_finished'):
                self.platform_handler.resize_finished.connect(self._on_resize_finished)
            
            # Install mouse tracking for cursor updates
            if self.cursor_manager:
                self._install_cursor_tracking()
            
            logger.debug("ResizeManager components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize resize components: {e}")
            raise
    
    def _install_cursor_tracking(self):
        """Install mouse tracking for cursor updates."""
        if not self.cursor_manager:
            return
        
        # Enable mouse tracking
        self.widget.setMouseTracking(True)
        
        # Install event filter for cursor updates
        self.widget.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle events for cursor updates."""
        if not self.is_enabled or obj != self.widget or not self.cursor_manager:
            return False
        
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QMouseEvent
        
        if event.type() == QEvent.Type.MouseMove:
            mouse_event = event
            if isinstance(mouse_event, QMouseEvent):
                # Only update cursor if not currently resizing
                if not self.is_resizing():
                    zone = self.get_hit_zone(mouse_event.position().toPoint())
                    self.cursor_manager.update_cursor(zone)
        
        elif event.type() == QEvent.Type.Leave:
            # Restore cursor when leaving widget
            if not self.is_resizing():
                self.cursor_manager.restore_cursor()
        
        return False
    
    def get_hit_zone(self, point):
        """Get hit zone for a point."""
        if self.platform_handler:
            return self.platform_handler.get_hit_zone(point)
        return HitZone.NONE
    
    def is_resizing(self) -> bool:
        """Check if currently resizing."""
        return (self.platform_handler is not None and 
                self.platform_handler.is_resizing)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable resize functionality."""
        self.is_enabled = enabled
        
        if not enabled and self.cursor_manager:
            self.cursor_manager.restore_cursor()
        
        logger.debug(f"Resize manager {'enabled' if enabled else 'disabled'}")
    
    def set_constraints(self, constraints: SizeConstraints):
        """Update size constraints."""
        self.constraints = constraints
        if self.platform_handler:
            self.platform_handler.constraints = constraints
        
        logger.debug("Size constraints updated")
    
    def set_border_width(self, width: int):
        """Update resize border width."""
        self.border_width = max(1, width)
        
        if self.platform_handler and hasattr(self.platform_handler, 'hit_detector'):
            self.platform_handler.hit_detector.set_border_width(width)
        
        logger.debug(f"Border width set to: {width}px")
    
    def cleanup(self):
        """Clean up resources."""
        if self.platform_handler:
            self.platform_handler.uninstall_handler()
            self.platform_handler = None
        
        if self.cursor_manager:
            self.cursor_manager.restore_cursor()
            self.cursor_manager = None
        
        # Remove event filter
        self.widget.removeEventFilter(self)
        
        logger.debug("ResizeManager cleaned up")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status information."""
        return {
            'enabled': self.is_enabled,
            'resizing': self.is_resizing(),
            'current_zone': self.current_zone.value,
            'border_width': self.border_width,
            'cursor_changes_enabled': self.enable_cursor_changes,
            'platform_handler': type(self.platform_handler).__name__ if self.platform_handler else None,
            'constraints': {
                'min_width': self.constraints.min_width,
                'min_height': self.constraints.min_height,
                'max_width': self.constraints.max_width,
                'max_height': self.constraints.max_height,
                'aspect_ratio': self.constraints.aspect_ratio,
            }
        }
    
    # Signal handlers
    def _on_resize_started(self, zone: HitZone):
        """Handle resize started."""
        self.current_zone = zone
        self.resize_started.emit(zone)
        logger.debug(f"Resize started in zone: {zone}")
    
    def _on_resize_updated(self, zone: HitZone, width: int, height: int):
        """Handle resize updated."""
        self.current_zone = zone
        self.resize_updated.emit(zone, width, height)
    
    def _on_resize_finished(self, zone: HitZone, width: int, height: int):
        """Handle resize finished."""
        self.current_zone = HitZone.NONE
        self.resize_finished.emit(zone, width, height)
        logger.debug(f"Resize finished in zone: {zone} (final size: {width}x{height})")
        
        # Restore cursor after resize
        if self.cursor_manager:
            self.cursor_manager.restore_cursor()