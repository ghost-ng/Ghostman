"""
Main Window for Ghostman Avatar Mode.

Provides the avatar interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCloseEvent

logger = logging.getLogger("ghostman.main_window")


class MainWindow(QMainWindow):
    """
    Main application window for Avatar mode.
    
    Contains only the avatar widget - REPL is now a separate floating window.
    """
    
    # Signals
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    
    def __init__(self, app_coordinator):
        super().__init__()
        self.app_coordinator = app_coordinator
        self.floating_repl = None
        
        self._init_ui()
        self._setup_window()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface with only the avatar widget."""
        # Import widgets
        from ..widgets.avatar_widget import AvatarWidget
        from ..widgets.floating_repl import FloatingREPLWindow
        
        # Create the avatar widget as central widget
        self.avatar_widget = AvatarWidget()
        self.avatar_widget.minimize_requested.connect(self.minimize_requested.emit)
        self.avatar_widget.avatar_clicked.connect(self._toggle_repl)
        self.setCentralWidget(self.avatar_widget)
        
        # Create floating REPL window (initially hidden)
        self.floating_repl = FloatingREPLWindow()
        self.floating_repl.closed.connect(self._on_repl_closed)
        self.floating_repl.command_entered.connect(self._on_command_entered)
        
        # Set window background
        self._set_window_style()
        
        logger.debug("UI components initialized - avatar only, REPL is floating")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Spector - AI Assistant")
        self.setMinimumSize(90, 90)
        self.resize(120, 120)  # 40% smaller (200 * 0.6 = 120)
        
        # Make window frameless for a cleaner look
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Center the window
        self._center_window()
        
        logger.debug("Window properties configured")
    
    def _set_window_style(self):
        """Set the window style and background."""
        # Set a gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2
                );
                border-radius: 20px;
            }
        """)
    
    def _center_window(self):
        """Position the window near the lower right corner."""
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            
            # Position near lower right with some padding
            padding = 50
            x = screen_geometry.right() - window_geometry.width() - padding
            y = screen_geometry.bottom() - window_geometry.height() - padding
            
            logger.debug(f'Positioning window: screen={screen_geometry}, window_geometry={window_geometry}')
            logger.debug(f'Final position: ({x}, {y})')
            self.move(x, y)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Hide floating REPL if it's visible
        if self.floating_repl and self.floating_repl.isVisible():
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to window close")
        
        # Don't actually close, just minimize to tray
        event.ignore()
        self.hide()
        self.close_requested.emit()
        logger.debug("Window close event - minimizing to tray")
    
    def show_and_activate(self):
        """Show the window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        logger.debug("Window shown and activated")
    
    def minimize_to_tray(self):
        """Minimize the window to system tray."""
        # Hide floating REPL if it's visible
        if self.floating_repl and self.floating_repl.isVisible():
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to minimize to tray")
        
        self.hide()
        self.minimize_requested.emit()
        logger.debug("Window minimized to tray")
    
    def _toggle_repl(self):
        """Toggle floating REPL visibility."""
        if self.floating_repl.isVisible():
            self._hide_repl()
        else:
            self._show_repl()
    
    def _show_repl(self):
        """Show the floating REPL positioned relative to avatar - avatar never moves."""
        # Get current avatar position and screen info
        avatar_pos = self.pos()
        avatar_size = (self.width(), self.height())
        screen = self.screen()
        
        logger.debug(f'Showing floating REPL: avatar at {avatar_pos}, size {avatar_size}')
        
        if screen:
            screen_geometry = screen.availableGeometry()
            
            # Position REPL relative to avatar (avatar position unchanged)
            self.floating_repl.position_relative_to_avatar(
                avatar_pos, avatar_size, screen_geometry
            )
            
            # Show and activate the REPL
            self.floating_repl.show_and_activate()
            
            logger.debug(f'Floating REPL shown, avatar remains at: {self.pos()}')
    
    def _hide_repl(self):
        """Hide the floating REPL - avatar position completely unaffected."""
        logger.debug(f'Hiding floating REPL, avatar at: {self.pos()}')
        self.floating_repl.hide()
        logger.debug(f'Floating REPL hidden, avatar still at: {self.pos()}')
    
    def _on_repl_closed(self):
        """Handle floating REPL window being closed."""
        logger.debug(f'Floating REPL closed by user, avatar remains at: {self.pos()}')
    
    def _on_command_entered(self, command: str):
        """Handle command from REPL."""
        logger.info(f"REPL command: {command}")
        # This would be connected to AI service