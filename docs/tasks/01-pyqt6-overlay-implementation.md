# PyQt6 Overlay Implementation Plan

## Overview

This document outlines the implementation of the core PyQt6 overlay system for Ghostman, focusing on the two primary application states: maximized avatar mode and minimized tray mode. The implementation must work without administrator permissions while providing a seamless user experience.

## Core Requirements

### Application States
1. **Maximized Avatar Mode**: Full chat interface with AI interactions
2. **Minimized Tray Mode**: System tray only, no visible UI

### Technical Constraints
- **No admin permissions required**
- **Always-on-top behavior** (without UAC elevation)
- **Multi-monitor support**
- **Draggable interface**
- **System tray integration**

## Implementation Architecture

### 1. Main Application Structure

**File**: `ghostman/src/main.py`

```python
#!/usr/bin/env python3
"""Main entry point for Ghostman application."""

import sys
import os
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from presentation.main_window import GhostmanMainWindow
from infrastructure.logging.logging_config import LoggingConfig
from application.app_coordinator import AppCoordinator
from infrastructure.settings.settings_manager import SettingsManager

def setup_application() -> QApplication:
    """Setup QApplication with proper configuration."""
    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is hidden
    app.setApplicationName("Ghostman")
    app.setApplicationDisplayName("Ghostman AI Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Ghostman Team")
    app.setOrganizationDomain("ghostman.ai")
    
    return app

def setup_logging() -> LoggingConfig:
    """Setup logging system."""
    # Get user data directory (no admin needed)
    app_data_dir = Path.home() / ".ghostman"
    
    logging_config = LoggingConfig(app_data_dir, "INFO")
    logger = logging_config.get_logger("main")
    logger.info("Ghostman application starting...")
    
    return logging_config

def setup_signal_handlers(app: QApplication):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger = logging_config.get_logger("main")
        logger.info(f"Received signal {signum}, shutting down...")
        app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main application entry point."""
    global logging_config
    
    try:
        # Setup application
        app = setup_application()
        
        # Setup logging
        logging_config = setup_logging()
        logger = logging_config.get_logger("main")
        
        # Setup signal handlers
        setup_signal_handlers(app)
        
        # Create app coordinator
        coordinator = AppCoordinator(logging_config)
        
        # Start in tray mode
        coordinator.start_in_tray_mode()
        
        logger.info("Ghostman started successfully")
        
        # Run application
        exit_code = app.exec()
        
        # Cleanup
        coordinator.shutdown()
        logging_config.cleanup()
        
        return exit_code
        
    except Exception as e:
        print(f"Failed to start Ghostman: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 2. Application Coordinator

**File**: `ghostman/src/application/app_coordinator.py`

```python
"""Central coordinator for Ghostman application state and services."""

import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ..presentation.main_window import GhostmanMainWindow
from ..presentation.system_tray import GhostmanSystemTray
from ..infrastructure.settings.settings_manager import SettingsManager
from ..domain.services.memory_service import MemoryService
from ..domain.services.ai_service import AIService
from ..application.conversation_manager import ConversationManager

class AppCoordinator(QObject):
    """Coordinates all application components and state transitions."""
    
    # Signals
    state_changed = pyqtSignal(str)  # "maximized" or "tray"
    
    def __init__(self, logging_config):
        super().__init__()
        self.logging_config = logging_config
        self.logger = logging_config.get_logger("main")
        
        # Current state
        self.current_state = "tray"
        
        # Components
        self.settings_manager = None
        self.memory_service = None
        self.ai_service = None
        self.conversation_manager = None
        self.main_window = None
        self.system_tray = None
        
        self._initialize_services()
        self._setup_components()
    
    def _initialize_services(self):
        """Initialize core services."""
        # Get user data directory
        app_data_dir = Path.home() / ".ghostman"
        
        # Settings
        self.settings_manager = SettingsManager(app_data_dir / "settings.json")
        
        # Memory service
        self.memory_service = MemoryService(app_data_dir)
        
        # AI service
        self.ai_service = AIService(self.settings_manager)
        
        # Conversation manager
        self.conversation_manager = ConversationManager(
            self.memory_service, 
            self.ai_service
        )
    
    def _setup_components(self):
        """Setup UI components."""
        # Main window (initially hidden)
        self.main_window = GhostmanMainWindow(
            self.conversation_manager,
            self.settings_manager,
            self.logging_config
        )
        
        # Connect window events
        self.main_window.minimize_requested.connect(self.switch_to_tray_mode)
        self.main_window.window_state_changed.connect(self._on_window_state_changed)
        
        # System tray
        self.system_tray = GhostmanSystemTray(self.settings_manager)
        
        # Connect tray events
        self.system_tray.show_window_requested.connect(self.switch_to_maximized_mode)
        self.system_tray.settings_requested.connect(self.show_settings)
        self.system_tray.quit_requested.connect(self.shutdown)
        
        self.logger.info("Application components initialized")
    
    def start_in_tray_mode(self):
        """Start application in system tray mode."""
        self.system_tray.show()
        self.current_state = "tray"
        self.state_changed.emit("tray")
        self.logger.info("Application started in tray mode")
    
    def switch_to_maximized_mode(self):
        """Switch to maximized avatar mode."""
        if self.current_state == "maximized":
            return
        
        self.main_window.show_and_activate()
        self.current_state = "maximized"
        self.state_changed.emit("maximized")
        self.logger.info("Switched to maximized avatar mode")
    
    def switch_to_tray_mode(self):
        """Switch to minimized tray mode."""
        if self.current_state == "tray":
            return
        
        self.main_window.hide()
        self.current_state = "tray"
        self.state_changed.emit("tray")
        self.logger.info("Switched to tray mode")
    
    def show_settings(self):
        """Show settings dialog."""
        from ..presentation.settings_dialog import SettingsDialog
        
        settings_dialog = SettingsDialog(self.settings_manager, parent=self.main_window)
        settings_dialog.exec()
    
    def _on_window_state_changed(self, state):
        """Handle window state changes."""
        if state == "minimized":
            self.switch_to_tray_mode()
    
    def shutdown(self):
        """Shutdown application gracefully."""
        self.logger.info("Application shutdown initiated")
        
        # Hide UI
        if self.main_window:
            self.main_window.hide()
        if self.system_tray:
            self.system_tray.hide()
        
        # Shutdown services
        if self.memory_service:
            self.memory_service.shutdown()
        
        # Quit application
        QApplication.quit()
    
    def get_current_state(self) -> str:
        """Get current application state."""
        return self.current_state
```

### 3. Main Window Implementation

**File**: `ghostman/src/presentation/main_window.py`

```python
"""Main window implementation for Ghostman avatar mode."""

import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor

from ..widgets.chat_widget import ChatWidget
from ..widgets.input_widget import InputWidget
from ..widgets.avatar_header import AvatarHeader

class GhostmanMainWindow(QMainWindow):
    """Main window for maximized avatar mode."""
    
    # Signals
    minimize_requested = pyqtSignal()
    window_state_changed = pyqtSignal(str)
    
    def __init__(self, conversation_manager, settings_manager, logging_config):
        super().__init__()
        self.conversation_manager = conversation_manager
        self.settings_manager = settings_manager
        self.logger = logging_config.get_logger("main")
        
        self.is_dragging = False
        self.drag_start_position = QPoint()
        
        self._setup_ui()
        self._apply_settings()
        self._connect_signals()
        
        # Start hidden
        self.hide()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Window properties
        self.setWindowTitle("Ghostman AI Assistant")
        self.setMinimumSize(QSize(400, 500))
        self.resize(QSize(450, 600))
        
        # Window flags for overlay behavior
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Avatar header (draggable area)
        self.avatar_header = AvatarHeader()
        self.avatar_header.minimize_clicked.connect(self.minimize_requested.emit)
        self.avatar_header.close_clicked.connect(self.close)
        main_layout.addWidget(self.avatar_header)
        
        # Chat area
        self.chat_widget = ChatWidget(self.conversation_manager)
        main_layout.addWidget(self.chat_widget, 1)  # Stretch
        
        # Input area
        self.input_widget = InputWidget(self.conversation_manager)
        main_layout.addWidget(self.input_widget)
        
        # Apply styling
        self._apply_styling()
    
    def _apply_styling(self):
        """Apply custom styling to the window."""
        self.setStyleSheet("""
            GhostmanMainWindow {
                background-color: #2b2b2b;
                border: 2px solid #444444;
                border-radius: 12px;
            }
        """)
    
    def _apply_settings(self):
        """Apply settings to the window."""
        settings = self.settings_manager.get_all_settings()
        
        # Window opacity
        opacity = settings.get("window_opacity", 0.95)
        self.setWindowOpacity(opacity)
        
        # Window position
        if "window_position" in settings:
            pos = settings["window_position"]
            self.move(pos["x"], pos["y"])
        
        # Window size
        if "window_size" in settings:
            size = settings["window_size"]
            self.resize(size["width"], size["height"])
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.input_widget.message_sent.connect(self._on_message_sent)
        self.conversation_manager.ai_response_received.connect(
            self.chat_widget.add_ai_message
        )
    
    def _on_message_sent(self, message: str):
        """Handle message sent from input widget."""
        # Add user message to chat
        self.chat_widget.add_user_message(message)
        
        # Clear input
        self.input_widget.clear_input()
    
    def show_and_activate(self):
        """Show window and bring to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Focus input field
        self.input_widget.focus_input()
        
        self.logger.info("Main window shown and activated")
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is in draggable area (header)
            if self.avatar_header.geometry().contains(event.position().toPoint()):
                self.is_dragging = True
                self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_start_position
            self.move(new_pos)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            # Save position
            pos = self.pos()
            self.settings_manager.update_setting("window_position", {
                "x": pos.x(),
                "y": pos.y()
            })
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        """Show context menu on right click."""
        from ..menus.context_menu import GhostmanContextMenu
        
        menu = GhostmanContextMenu(self)
        menu.exec(event.globalPos())
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Instead of closing, minimize to tray
        event.ignore()
        self.minimize_requested.emit()
    
    def hideEvent(self, event):
        """Handle window hide event."""
        super().hideEvent(event)
        self.window_state_changed.emit("minimized")
        
        # Save window state
        geometry = self.geometry()
        self.settings_manager.update_setting("window_size", {
            "width": geometry.width(),
            "height": geometry.height()
        })
    
    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        self.window_state_changed.emit("maximized")
```

### 4. System Tray Implementation

**File**: `ghostman/src/presentation/system_tray.py`

```python
"""System tray implementation for Ghostman."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

class GhostmanSystemTray(QObject):
    """System tray icon and menu for Ghostman."""
    
    # Signals
    show_window_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.logger = logging.getLogger("ghostman.main")
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.error("System tray is not available")
            return
        
        self._setup_tray_icon()
        self._setup_menu()
        self._connect_signals()
    
    def _setup_tray_icon(self):
        """Setup the system tray icon."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        
        # Load icon
        icon_path = self._get_icon_path()
        if icon_path and icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # Fallback to default icon
            icon = QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_ComputerIcon
            )
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Ghostman AI Assistant")
        
        self.logger.info("System tray icon created")
    
    def _get_icon_path(self) -> Path:
        """Get path to tray icon."""
        # Look for icon in assets directory
        possible_paths = [
            Path(__file__).parent.parent.parent / "assets" / "icons" / "tray.png",
            Path(__file__).parent.parent.parent / "assets" / "icons" / "ghostman.png",
            Path(__file__).parent.parent.parent / "assets" / "icons" / "icon.png",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def _setup_menu(self):
        """Setup the context menu."""
        self.menu = QMenu()
        
        # Show/Hide Ghostman
        self.show_action = QAction("Show Ghostman", self)
        self.show_action.triggered.connect(self.show_window_requested.emit)
        self.menu.addAction(self.show_action)
        
        self.menu.addSeparator()
        
        # Settings
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.settings_action)
        
        # Help
        self.help_action = QAction("Help", self)
        self.help_action.triggered.connect(self._show_help)
        self.menu.addAction(self.help_action)
        
        # About
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self._show_about)
        self.menu.addAction(self.about_action)
        
        self.menu.addSeparator()
        
        # Quit
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)
        
        # Set context menu
        self.tray_icon.setContextMenu(self.menu)
        
        self.logger.info("System tray menu created")
    
    def _connect_signals(self):
        """Connect tray icon signals."""
        # Left click to show window
        self.tray_icon.activated.connect(self._on_tray_activated)
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click - show window
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # Right click - show context menu (handled automatically)
            pass
    
    def _show_help(self):
        """Show help information."""
        from ..dialogs.help_dialog import HelpDialog
        help_dialog = HelpDialog()
        help_dialog.exec()
    
    def _show_about(self):
        """Show about dialog."""
        from ..dialogs.about_dialog import AboutDialog
        about_dialog = AboutDialog()
        about_dialog.exec()
    
    def show(self):
        """Show the system tray icon."""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.show()
            self.logger.info("System tray icon shown")
    
    def hide(self):
        """Hide the system tray icon."""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            self.logger.info("System tray icon hidden")
    
    def update_tooltip(self, text: str):
        """Update tray icon tooltip."""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.setToolTip(text)
```

### 5. Window State Management

**File**: `ghostman/src/application/window_state_manager.py`

```python
"""Window state management for Ghostman."""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QRect, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen

class WindowStateManager(QObject):
    """Manages window state, positioning, and multi-monitor support."""
    
    # Signals
    state_changed = pyqtSignal(str, dict)  # state_name, state_data
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.logger = logging.getLogger("ghostman.main")
        
        # Current state
        self.current_state = "tray"
        self.window_geometry = None
        
        # Screen monitoring
        self.screen_monitor_timer = QTimer()
        self.screen_monitor_timer.timeout.connect(self._check_screen_configuration)
        self.screen_monitor_timer.start(5000)  # Check every 5 seconds
        
        self.known_screens = set()
        self._update_known_screens()
    
    def set_state(self, state: str, data: Optional[Dict[str, Any]] = None):
        """Set the current window state."""
        if state == self.current_state:
            return
        
        old_state = self.current_state
        self.current_state = state
        
        self.logger.info(f"Window state changed: {old_state} -> {state}")
        self.state_changed.emit(state, data or {})
        
        # Save state to settings
        self.settings_manager.update_setting("last_window_state", {
            "state": state,
            "timestamp": QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate)
        })
    
    def get_optimal_window_position(self, window_size: QRect) -> QRect:
        """Get optimal position for window on current screen setup."""
        # Get current screen
        screen = QApplication.primaryScreen()
        if not screen:
            return QRect(100, 100, window_size.width(), window_size.height())
        
        screen_geometry = screen.geometry()
        available_geometry = screen.availableGeometry()
        
        # Load saved position
        saved_pos = self.settings_manager.get_setting("window_position")
        if saved_pos:
            x, y = saved_pos["x"], saved_pos["y"]
            
            # Validate position is still on screen
            test_rect = QRect(x, y, window_size.width(), window_size.height())
            if self._is_rect_on_any_screen(test_rect):
                return test_rect
        
        # Default position: center-right of available area
        x = available_geometry.right() - window_size.width() - 50
        y = available_geometry.top() + 50
        
        return QRect(x, y, window_size.width(), window_size.height())
    
    def _is_rect_on_any_screen(self, rect: QRect) -> bool:
        """Check if rectangle is visible on any screen."""
        for screen in QApplication.screens():
            screen_geometry = screen.geometry()
            if screen_geometry.intersects(rect):
                intersection = screen_geometry.intersected(rect)
                # At least 25% of the window should be visible
                if (intersection.width() * intersection.height()) >= (rect.width() * rect.height() * 0.25):
                    return True
        return False
    
    def _update_known_screens(self):
        """Update list of known screens."""
        self.known_screens.clear()
        for screen in QApplication.screens():
            self.known_screens.add((screen.name(), screen.geometry()))
    
    def _check_screen_configuration(self):
        """Check for screen configuration changes."""
        current_screens = set()
        for screen in QApplication.screens():
            current_screens.add((screen.name(), screen.geometry()))
        
        if current_screens != self.known_screens:
            self.logger.info("Screen configuration changed")
            self.known_screens = current_screens
            
            # If window is visible, check if it needs repositioning
            if self.current_state == "maximized":
                self._handle_screen_change()
    
    def _handle_screen_change(self):
        """Handle screen configuration changes."""
        # This would be called by the main window to reposition if needed
        self.state_changed.emit("screen_config_changed", {
            "screens": [
                {"name": screen.name(), "geometry": screen.geometry()}
                for screen in QApplication.screens()
            ]
        })
    
    def save_window_geometry(self, geometry: QRect):
        """Save window geometry to settings."""
        self.window_geometry = geometry
        self.settings_manager.update_setting("window_position", {
            "x": geometry.x(),
            "y": geometry.y()
        })
        self.settings_manager.update_setting("window_size", {
            "width": geometry.width(),
            "height": geometry.height()
        })
    
    def get_saved_geometry(self) -> Optional[QRect]:
        """Get saved window geometry."""
        pos = self.settings_manager.get_setting("window_position")
        size = self.settings_manager.get_setting("window_size")
        
        if pos and size:
            return QRect(pos["x"], pos["y"], size["width"], size["height"])
        
        return None
    
    def cleanup(self):
        """Cleanup resources."""
        if self.screen_monitor_timer:
            self.screen_monitor_timer.stop()
```

## Key Implementation Features

### 1. State Management
- Clean separation between maximized avatar mode and tray mode
- Persistent state across application restarts
- Smooth transitions between states

### 2. Window Behavior
- Always-on-top without admin permissions
- Draggable interface with proper hit testing
- Multi-monitor support with position validation
- Frameless design with custom styling

### 3. System Integration
- Proper system tray integration
- Context menus for both window and tray
- Keyboard shortcuts and accessibility

### 4. Performance
- Efficient rendering and minimal resource usage
- Proper cleanup and memory management
- Responsive UI during AI interactions

This implementation provides a solid foundation for the Ghostman overlay system with the two core states, focusing on user experience while respecting system permissions and constraints.