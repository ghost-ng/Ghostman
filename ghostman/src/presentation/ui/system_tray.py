"""
Enhanced System Tray for Ghostman.

Provides a system tray icon with context menu and state management.
"""

import logging
import os
from typing import Optional
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QFont
from PyQt6.QtCore import Qt

logger = logging.getLogger("ghostman.system_tray")


class EnhancedSystemTray(QObject):
    """
    Enhanced system tray icon with context menu and state-aware behavior.
    
    Provides:
    - System tray icon with context menu
    - State-aware icon changes (Avatar mode vs Tray mode)
    - Quick actions and settings access
    """
    
    # Signals
    show_avatar_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    help_requested = pyqtSignal()
    about_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, app_coordinator):
        super().__init__()
        self.app_coordinator = app_coordinator
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.context_menu: Optional[QMenu] = None
        self._current_mode = "tray"  # Default mode
        
        self._init_tray_icon()
        self._init_context_menu()
        
        logger.info("EnhancedSystemTray initialized")
    
    def _init_tray_icon(self):
        """Initialize the system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.error("System tray is not available on this system")
            return
        
        self.tray_icon = QSystemTrayIcon()
        
        # Set initial icon
        icon = self._create_default_icon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Spector - AI Assistant")
        
        # Connect tray icon signals
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.messageClicked.connect(self._on_message_clicked)
        
        logger.debug("System tray icon initialized")
    
    def _init_context_menu(self):
        """Initialize the context menu."""
        self.context_menu = QMenu()
        
        # Show Avatar action
        show_avatar_action = QAction("Show Avatar", self.context_menu)
        show_avatar_action.triggered.connect(self.show_avatar_requested.emit)
        self.context_menu.addAction(show_avatar_action)
        
        self.context_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings...", self.context_menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self.context_menu.addAction(settings_action)
        
        # Help action
        help_action = QAction("Help...", self.context_menu)
        help_action.triggered.connect(self.help_requested.emit)
        self.context_menu.addAction(help_action)
        
        # About action
        about_action = QAction("About ghost-ng", self.context_menu)
        about_action.triggered.connect(self.about_requested.emit)
        self.context_menu.addAction(about_action)
        
        self.context_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self.context_menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self.context_menu.addAction(quit_action)
        
        # Set context menu
        if self.tray_icon:
            self.tray_icon.setContextMenu(self.context_menu)
        
        logger.debug("Context menu initialized")
    
    def _create_default_icon(self) -> QIcon:
        """Create a default icon if no icon file is available."""
        # Try to load icon from assets - prioritize avatar.png
        icon_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "avatar.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "icon.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "ghost.png")
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                logger.debug(f"Loading icon from: {icon_path}")
                return QIcon(icon_path)
        
        # Create a simple default icon
        logger.debug("Creating default programmatic icon")
        return self._create_programmatic_icon()
    
    def _create_programmatic_icon(self) -> QIcon:
        """Create a simple programmatic icon."""
        # Create a 32x32 pixmap
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a simple ghost-like shape
        if self._current_mode == "avatar":
            # Active state - blue circle
            painter.setBrush(Qt.GlobalColor.blue)
            painter.setPen(Qt.GlobalColor.darkBlue)
        else:
            # Tray state - gray circle
            painter.setBrush(Qt.GlobalColor.gray)
            painter.setPen(Qt.GlobalColor.darkGray)
        
        # Draw main circle
        painter.drawEllipse(4, 4, 24, 24)
        
        # Draw "G" for Ghostman
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(10, 22, "G")
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _get_avatar_icon(self) -> QIcon:
        """Get the avatar icon for notifications."""
        # Try to load avatar icon from assets
        avatar_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "assets", "avatar.png"
        )
        
        if os.path.exists(avatar_path):
            try:
                # Load and resize avatar for notification (typically 32x32 or 64x64)
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    # Scale to appropriate size for notifications
                    scaled_pixmap = pixmap.scaled(
                        32, 32, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    logger.debug(f"Loaded avatar icon from: {avatar_path}")
                    return QIcon(scaled_pixmap)
            except Exception as e:
                logger.warning(f"Failed to load avatar icon: {e}")
        
        logger.debug("Avatar icon not found, will use system icon")
        return QIcon()  # Return empty icon to trigger fallback
    
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            logger.debug("Tray icon double-clicked - showing avatar")
            self.show_avatar_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            logger.debug("Tray icon single-clicked")
            # Single click could show a quick menu or toggle
            pass
    
    def _on_message_clicked(self):
        """Handle tray message clicked."""
        logger.debug("Tray message clicked")
        self.show_avatar_requested.emit()
    
    def show(self):
        """Show the system tray icon."""
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()
            logger.info("System tray icon shown")
        else:
            logger.warning("Cannot show system tray - not available")
    
    def hide(self):
        """Hide the system tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
            logger.debug("System tray icon hidden")
    
    def set_avatar_mode(self):
        """Set the tray icon appearance for avatar mode."""
        self._current_mode = "avatar"
        if self.tray_icon:
            icon = self._create_default_icon()  # This will use avatar colors
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip("Ghostman - Avatar Mode (Active)")
            logger.debug("System tray set to avatar mode")
    
    def set_tray_mode(self):
        """Set the tray icon appearance for tray mode."""
        self._current_mode = "tray"
        if self.tray_icon:
            icon = self._create_default_icon()  # This will use tray colors
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip("Ghostman - Tray Mode")
            logger.debug("System tray set to tray mode")
    
    def show_message(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information, duration: int = 3000):
        """
        Show a tray notification message.
        
        Args:
            title: Message title
            message: Message text
            icon_type: Type of icon to show
            duration: Duration in milliseconds
        """
        if self.tray_icon and self.tray_icon.isVisible():
            # Use custom avatar icon for notifications instead of system icons
            avatar_icon = self._get_avatar_icon()
            if avatar_icon and not avatar_icon.isNull():
                self.tray_icon.showMessage(title, message, avatar_icon, duration)
                logger.debug(f"Tray message shown with avatar icon: {title}")
            else:
                # Fallback to system icon if avatar not available
                self.tray_icon.showMessage(title, message, icon_type, duration)
                logger.debug(f"Tray message shown with system icon: {title}")
        else:
            logger.warning("Cannot show tray message - tray icon not visible")
    
    def is_visible(self) -> bool:
        """Check if the tray icon is visible."""
        return self.tray_icon.isVisible() if self.tray_icon else False