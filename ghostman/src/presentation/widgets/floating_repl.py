"""
Floating REPL Window for Ghostman.

A separate window that appears next to the avatar without moving it.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QWidget, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QCloseEvent

from .repl_widget import REPLWidget
try:
    from ...infrastructure.storage.settings_manager import settings as _global_settings
except Exception:  # pragma: no cover
    _global_settings = None

logger = logging.getLogger("ghostman.floating_repl")



class FloatingREPLWindow(QMainWindow):
    """
    Floating REPL window that appears next to the avatar.
    
    This is a separate window that positions itself relative to the avatar
    without affecting the avatar's position at all.
    """
    
    # Signals
    closed = pyqtSignal()
    command_entered = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.repl_widget = None
        
        self._init_ui()
        self._setup_window()
        
        logger.info("FloatingREPLWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create REPL widget as central widget
        self.repl_widget = REPLWidget()
        self.setCentralWidget(self.repl_widget)

        # REPL widget already loads its own opacity from settings in its constructor
        # No need to override it here since REPLWidget._load_opacity_from_settings() handles this
        
        # Connect REPL signals
        self.repl_widget.minimize_requested.connect(self.close)
        self.repl_widget.command_entered.connect(self.command_entered.emit)
        
        logger.debug("FloatingREPL UI initialized")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("")  # No window title
        self.resize(520, 450)  # Default size: 500px + padding for REPL content
        self.setMinimumSize(300, 250)  # Set minimum size instead of fixed size
        
        # Make window frameless and always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Prevents it from showing in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Enable mouse tracking for cursor changes without button press
        self.setMouseTracking(True)
        
        # Keep window fully opaque - only panel backgrounds will be transparent via CSS
        self.setWindowOpacity(1.0)
    
        
        
        logger.debug("FloatingREPL window properties configured")
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Save current conversation before closing
        if self.repl_widget and hasattr(self.repl_widget, 'save_current_conversation'):
            try:
                self.repl_widget.save_current_conversation()
                logger.debug("Current conversation saved before window close")
            except Exception as e:
                logger.error(f"Failed to save conversation on close: {e}")
        
        self.closed.emit()
        event.accept()
        logger.debug("FloatingREPL window closed")
    
    # Old eventFilter removed - no longer needed with ResizeGrip widgets
    
    # Resize functionality now handled by ResizeGrip widgets
    
    def position_relative_to_avatar(self, avatar_pos: QPoint, avatar_size: tuple, screen_geometry):
        """
        Position the REPL window relative to the avatar.
        
        Args:
            avatar_pos: Current position of the avatar window
            avatar_size: Size of the avatar window (width, height)
            screen_geometry: Available screen geometry
        """
        avatar_width, avatar_height = avatar_size
        repl_width = self.width()
        repl_height = self.height()
        
        # Default position: to the right of avatar
        repl_x = avatar_pos.x() + avatar_width + 10  # 10px gap
        repl_y = avatar_pos.y()
        
        logger.debug(f'Positioning REPL: avatar at {avatar_pos}, size {avatar_size}')
        logger.debug(f'Initial REPL position: ({repl_x}, {repl_y}), screen: {screen_geometry}')
        
        # Check if REPL would go off the right edge of screen
        if repl_x + repl_width > screen_geometry.right():
            logger.debug('REPL would go off-screen right, positioning on left')
            # Position to the left of avatar
            repl_x = avatar_pos.x() - repl_width - 10  # 10px gap on left
            
            # If it would still go off the left edge, clamp to screen edge
            if repl_x < screen_geometry.left():
                repl_x = screen_geometry.left() + 10
                logger.debug(f'Clamped to left edge: {repl_x}')
        
        # Check if REPL would go off the bottom edge
        if repl_y + repl_height > screen_geometry.bottom():
            logger.debug('REPL would go off-screen bottom, adjusting Y position')
            repl_y = screen_geometry.bottom() - repl_height - 10
            
            # If it would go off the top, clamp to top
            if repl_y < screen_geometry.top():
                repl_y = screen_geometry.top() + 10
                logger.debug(f'Clamped to top edge: {repl_y}')
        
        final_pos = QPoint(repl_x, repl_y)
        self.move(final_pos)
        
        logger.debug(f'FloatingREPL positioned at: {final_pos}')
    
    def show_and_activate(self):
        """Show the window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Focus on the command input
        if self.repl_widget and self.repl_widget.command_input:
            self.repl_widget.command_input.setFocus()
        
        logger.debug("FloatingREPL shown and activated")

    # Public API -----------------------------------------------------
    def set_panel_opacity(self, opacity: float):
        """Set only the panel (frame) opacity (content/text remains fully opaque)."""
        if self.repl_widget:
            self.repl_widget.set_panel_opacity(opacity)