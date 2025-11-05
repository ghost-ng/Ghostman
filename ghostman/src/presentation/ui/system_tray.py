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
    
    def _get_theme_icon(self, icon_name: str) -> QIcon:
        """Get theme-aware icon for system tray menu (dark icons for light themes, light icons for dark themes)."""
        try:
            # Get theme manager to determine if current theme is dark or light
            from ghostman.src.ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()

            # Determine icon variant based on theme
            icon_variant = "_lite"  # Default to lite for dark themes
            if theme_manager and theme_manager.current_theme:
                # If background is light (luminance > 0.5), use dark icons
                bg_color = theme_manager.current_theme.background_primary
                if bg_color:
                    # Simple luminance check: light backgrounds need dark icons
                    # Extract RGB from hex color
                    if bg_color.startswith('#'):
                        r = int(bg_color[1:3], 16) / 255.0
                        g = int(bg_color[3:5], 16) / 255.0
                        b = int(bg_color[5:7], 16) / 255.0
                        # Calculate relative luminance
                        luminance = 0.299 * r + 0.587 * g + 0.114 * b
                        if luminance > 0.5:
                            icon_variant = "_dark"  # Light theme needs dark icons

            from ...utils.resource_resolver import resolve_icon
            icon_path = resolve_icon(icon_name, icon_variant)
            if icon_path:
                return QIcon(str(icon_path))
        except Exception as e:
            logger.debug(f"Failed to load icon {icon_name}{icon_variant}.png: {e}")

        return QIcon()  # Empty icon as fallback
    
    def _init_context_menu(self):
        """Initialize the context menu."""
        self.context_menu = QMenu()
        
        # Show Avatar action
        show_avatar_action = QAction(self._get_theme_icon("chat"), "Show Avatar", self.context_menu)
        show_avatar_action.triggered.connect(self.show_avatar_requested.emit)
        self.context_menu.addAction(show_avatar_action)
        
        self.context_menu.addSeparator()
        
        # Settings action
        settings_action = QAction(self._get_theme_icon("gear"), "Settings...", self.context_menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self.context_menu.addAction(settings_action)
        
        # Help action
        help_action = QAction(self._get_theme_icon("help"), "Help...", self.context_menu)
        help_action.triggered.connect(self.help_requested.emit)
        self.context_menu.addAction(help_action)

        self.context_menu.addSeparator()
        
        # Quit action
        quit_action = QAction(self._get_theme_icon("exit"), "Quit", self.context_menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self.context_menu.addAction(quit_action)
        
        # Apply theme-aware menu styling
        self._style_menu(self.context_menu)
        
        # Set context menu
        if self.tray_icon:
            self.tray_icon.setContextMenu(self.context_menu)
        
        logger.debug("Context menu initialized")
    
    def _style_menu(self, menu):
        """Apply theme-aware styling to QMenu widgets."""
        try:
            # Try to get the global theme manager
            theme_manager = None
            try:
                from ghostman.src.ui.themes.theme_manager import get_theme_manager
                theme_manager = get_theme_manager()
            except (ImportError, AttributeError):
                return
            
            if not theme_manager:
                return
                
            try:
                from ghostman.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                if not THEME_SYSTEM_AVAILABLE:
                    return
            except ImportError:
                return
            
            colors = theme_manager.current_theme
            if colors:
                from ghostman.src.ui.themes.style_templates import StyleTemplates
                menu_style = StyleTemplates.get_menu_style(colors)
                menu.setStyleSheet(menu_style)
                
        except Exception as e:
            # Silently handle errors to avoid breaking functionality
            pass
    
    def _create_default_icon(self) -> QIcon:
        """Create a default icon if no icon file is available."""
        try:
            from ...utils.resource_resolver import resolve_multiple_icons
            
            # Try to load icon from assets - prioritize avatar.png
            icon_names = ["avatar", "icon", "ghost"]
            icon_path = resolve_multiple_icons(icon_names)
            
            if icon_path:
                logger.debug(f"Loading icon from: {icon_path}")
                return QIcon(str(icon_path))
        except Exception as e:
            logger.debug(f"Failed to resolve icon: {e}")
        
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

    def refresh_menu_theme(self):
        """Refresh menu styling and icons when theme changes."""
        if not self.context_menu:
            return

        # Re-apply theme-aware styling
        self._style_menu(self.context_menu)

        # Update all action icons to match new theme
        for action in self.context_menu.actions():
            if action.isSeparator():
                continue

            text = action.text()
            # Map action text to icon name
            icon_map = {
                "Show Avatar": "chat",
                "Settings...": "gear",
                "Help...": "help",
                "Quit": "exit"
            }

            if text in icon_map:
                icon = self._get_theme_icon(icon_map[text])
                action.setIcon(icon)

        logger.debug("System tray menu theme refreshed")