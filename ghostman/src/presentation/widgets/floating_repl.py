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
        
        # Connect REPL signals
        self.repl_widget.minimize_requested.connect(self.close)
        self.repl_widget.command_entered.connect(self.command_entered.emit)
        
        logger.debug("FloatingREPL UI initialized")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Chat with Spector")
        self.setFixedSize(520, 450)  # 500px + padding for REPL content
        
        # Make window frameless and always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Prevents it from showing in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        logger.debug("FloatingREPL window properties configured")
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        self.closed.emit()
        event.accept()
        logger.debug("FloatingREPL window closed")
    
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