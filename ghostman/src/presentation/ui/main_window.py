"""
Main Window for Ghostman Avatar Mode.

Provides the avatar interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QIcon, QCloseEvent, QPalette, QColor

logger = logging.getLogger("ghostman.main_window")


class MainWindow(QMainWindow):
    """
    Main application window for Avatar mode.
    
    This is a placeholder implementation that will be expanded with:
    - Chat interface
    - AI conversation display
    - Input controls
    - Settings access
    """
    
    # Signals
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    
    def __init__(self, app_coordinator):
        super().__init__()
        self.app_coordinator = app_coordinator
        self.repl_visible = False
        self.repl_widget = None
        self.repl_animation = None
        
        self._init_ui()
        self._setup_window()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface with avatar and REPL."""
        # Import widgets
        from ..widgets.avatar_widget import AvatarWidget
        from ..widgets.repl_widget import REPLWidget
        
        # Create main container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create horizontal layout for avatar and REPL
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create the avatar widget
        self.avatar_widget = AvatarWidget()
        self.avatar_widget.minimize_requested.connect(self.minimize_requested.emit)
        self.avatar_widget.avatar_clicked.connect(self._toggle_repl)
        self.main_layout.addWidget(self.avatar_widget)
        
        # Create REPL widget (initially hidden)
        self.repl_widget = REPLWidget()
        self.repl_widget.minimize_requested.connect(self._hide_repl)
        self.repl_widget.command_entered.connect(self._on_command_entered)
        self.repl_widget.setFixedWidth(400)
        self.repl_widget.hide()
        self.main_layout.addWidget(self.repl_widget)
        
        # Set window background
        self._set_window_style()
        
        logger.debug("UI components initialized")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Ghostman - AI Desktop Assistant")
        self.setMinimumSize(150, 150)
        self.resize(200, 200)  # Much smaller window
        
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
            
            self.move(x, y)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
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
        self.hide()
        self.minimize_requested.emit()
        logger.debug("Window minimized to tray")
    
    def _toggle_repl(self):
        """Toggle REPL visibility with animation."""
        if self.repl_visible:
            self._hide_repl()
        else:
            self._show_repl()
    
    def _show_repl(self):
        """Show the REPL interface."""
        if not self.repl_visible:
            # Adjust window size
            current_size = self.size()
            new_width = current_size.width() + 400
            self.resize(new_width, current_size.height())
            
            # Show REPL
            self.repl_widget.show()
            self.repl_visible = True
            
            logger.debug("REPL interface shown")
    
    def _hide_repl(self):
        """Hide the REPL interface."""
        if self.repl_visible:
            # Hide REPL
            self.repl_widget.hide()
            self.repl_visible = False
            
            # Adjust window size
            current_size = self.size()
            new_width = current_size.width() - 400
            self.resize(new_width, current_size.height())
            
            logger.debug("REPL interface hidden")
    
    def _on_command_entered(self, command: str):
        """Handle command from REPL."""
        logger.info(f"REPL command: {command}")
        # This would be connected to AI service