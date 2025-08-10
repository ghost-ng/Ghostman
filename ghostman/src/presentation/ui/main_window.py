"""
Main Window for Ghostman Avatar Mode.

Provides the main chat interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QCloseEvent

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
        
        self._init_ui()
        self._setup_window()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Placeholder content
        title_label = QLabel("Ghostman AI Assistant")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        status_label = QLabel("Avatar Mode - Ready to chat!")
        status_label.setStyleSheet("font-size: 14px; color: #666; margin: 10px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)
        
        # Placeholder chat area
        chat_placeholder = QLabel("Chat interface will be implemented here.\n\n" +
                                "This is where you'll interact with the AI assistant.\n" +
                                "Features coming soon:\n" +
                                "• Conversation history\n" +
                                "• AI responses\n" +
                                "• Message input\n" +
                                "• File attachments")
        chat_placeholder.setStyleSheet("background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px;")
        chat_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(chat_placeholder, 1)  # Take remaining space
        
        # Minimize to tray button
        minimize_button = QPushButton("Minimize to Tray")
        minimize_button.clicked.connect(self.minimize_requested.emit)
        minimize_button.setStyleSheet("padding: 10px; margin: 10px;")
        layout.addWidget(minimize_button)
        
        logger.debug("UI components initialized")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Ghostman - AI Desktop Assistant")
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        # Center the window
        self._center_window()
        
        logger.debug("Window properties configured")
    
    def _center_window(self):
        """Center the window on the screen."""
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
    
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