"""Main application class for Ghostman."""

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox, QMenu, QGraphicsOpacityEffect
from PyQt6.QtCore import QObject, QTimer, Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QIcon, QPixmap, QAction
import sys
import logging
from pathlib import Path

from ui.components.avatar_widget import AvatarWidget
from ui.components.toast_manager import SimpleToastManager
from ui.components.prompt_interface import PromptInterface
from ui.components.settings_dialog import SettingsDialog
from ui.themes.theme_manager import ThemeManager
from app.window_manager import WindowManager
from services.ai_service import AIService

class GhostmanApplication(QObject):
    """Main application class for Ghostman."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.app = None
        self.avatar_widget = None
        self.prompt_interface = None
        self.toast_manager = None
        self.window_manager = None
        self.system_tray = None
        self.ai_service = None
        self.theme_manager = None
        
        # Application state
        self.is_running = False
        
        # Use APPDATA on Windows, fallback to home on other systems
        import os
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            self.config_dir = Path(appdata) / "Ghostman"
        else:
            self.config_dir = Path.home() / ".ghostman"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self):
        """Initialize the application."""
        try:
            self.logger.info("Initializing Ghostman application...")
            
            # Initialize theme manager first
            theme_config_path = self.config_dir / "themes.json"
            self.theme_manager = ThemeManager(theme_config_path)
            
            # Initialize core components
            self.toast_manager = SimpleToastManager()
            self.avatar_widget = AvatarWidget()
            self.prompt_interface = PromptInterface()
            
            # Apply initial theme to components
            self.apply_current_theme()
            
            # Initialize AI service
            ai_config_path = self.config_dir / "ai_config.json"
            self.ai_service = AIService(ai_config_path)
            
            # Initialize window manager
            settings_path = self.config_dir / "window_positions.json"
            self.window_manager = WindowManager(
                self.avatar_widget, 
                self.toast_manager,
                settings_path
            )
            # Set the prompt window reference
            self.window_manager.set_prompt_window(self.prompt_interface)
            # Set the application reference for settings access
            self.window_manager.set_application(self)
            
            # No system tray - keep it simple
            self.system_tray = None
            
            # Connect application signals
            self.setup_connections()
            
            # Connect AI service
            self.setup_ai_connections()
            
            self.logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            return False
    
    def setup_system_tray(self):
        """Setup system tray integration."""
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.logger.warning("System tray not available")
                if self.toast_manager:
                    self.toast_manager.warning(
                        "System Tray", 
                        "System tray is not available on this system"
                    )
                return
            
            # Try to load the avatar image as icon
            icon = self.load_tray_icon()
            
            self.system_tray = QSystemTrayIcon(icon)
            self.system_tray.setToolTip("Ghostman AI Assistant")
            
            # Create context menu
            self.setup_tray_menu()
            
            # Tray click handler
            self.system_tray.activated.connect(self.on_tray_activated)
            
            self.system_tray.show()
            self.logger.info("System tray setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup system tray: {e}")
            if self.toast_manager:
                self.toast_manager.error(
                    "System Tray Error", 
                    f"Failed to initialize system tray: {str(e)[:50]}..."
                )
    
    def load_tray_icon(self) -> QIcon:
        """Load the tray icon from assets."""
        try:
            # Get the path to the assets folder
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                application_path = Path(sys.executable).parent
                assets_path = application_path / "assets"
            else:
                # Running as script - find the ghostman/assets folder
                current_file = Path(__file__)
                app_dir = current_file.parent  # app/
                src_dir = app_dir.parent  # src/
                ghostman_root = src_dir.parent  # ghostman/
                assets_path = ghostman_root / "assets"
            
            avatar_image_path = assets_path / "avatar.png"
            
            if avatar_image_path.exists():
                # Load and create icon
                pixmap = QPixmap(str(avatar_image_path))
                if not pixmap.isNull():
                    # Create multiple sizes for better display on different DPI settings
                    icon = QIcon()
                    for size in [16, 20, 24, 32, 48, 64]:
                        scaled_pixmap = pixmap.scaled(
                            size, size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        icon.addPixmap(scaled_pixmap)
                    self.logger.info(f"System tray icon loaded successfully from: {avatar_image_path}")
                    return icon
            
            # Fallback to ghost emoji icon
            self.logger.warning("Avatar image not found, using fallback ghost icon")
            return self._create_fallback_icon()
            
        except Exception as e:
            self.logger.error(f"Error loading tray icon: {e}")
            return self._create_fallback_icon()
    
    def _create_fallback_icon(self) -> QIcon:
        """Create a fallback icon with ghost emoji."""
        from PyQt6.QtGui import QPainter, QFont, QBrush
        from PyQt6.QtCore import Qt
        
        try:
            # Create pixmap with ghost emoji
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw a circular background
            painter.setBrush(QBrush(Qt.GlobalColor.darkBlue))
            painter.drawEllipse(2, 2, 28, 28)
            
            # Draw ghost emoji
            font = QFont("Segoe UI Emoji", 16)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "👻")
            
            painter.end()
            return QIcon(pixmap)
        except Exception:
            # Ultimate fallback - simple blue circle
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.darkBlue)
            return QIcon(pixmap)
    
    def setup_tray_menu(self):
        """Setup system tray context menu - MINIMAL."""
        try:
            menu = QMenu()
            
            # Quit action only
            quit_action = QAction("Quit Ghostman", menu)
            quit_action.triggered.connect(self.quit_application)
            menu.addAction(quit_action)
            
            self.system_tray.setContextMenu(menu)
            
        except Exception as e:
            self.logger.error(f"Error setting up tray menu: {e}")
    
    def show_avatar(self):
        """Show the avatar widget."""
        self.logger.info("Show avatar requested from tray menu")
        if self.window_manager:
            self.window_manager.show_avatar()
            # Show a toast to confirm the action
            self.toast_manager.info("Ghostman", "Avatar is now visible on your desktop")
        else:
            self.logger.error("Window manager not available")
    
    def show_main_interface(self):
        """Show the main interface."""
        if self.window_manager:
            self.window_manager.show_main_interface()
    
    def show_settings_placeholder(self):
        """Show settings dialog."""
        self.show_settings()
    
    def show_settings(self):
        """Show the settings dialog."""
        try:
            # Create settings dialog with theme manager
            settings_dialog = SettingsDialog(self.ai_service.get_config(), self.theme_manager, parent=None)
            settings_dialog.settings_saved.connect(self.on_settings_saved)
            settings_dialog.theme_changed.connect(self.on_theme_changed)
            
            # Apply current theme to settings dialog
            if self.theme_manager:
                settings_dialog.setStyleSheet(self.theme_manager.get_stylesheet('settings'))
            
            # Show dialog
            settings_dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Error showing settings dialog: {e}")
            self.toast_manager.error("Settings Error", f"Could not open settings: {str(e)}")
    
    def on_settings_saved(self, settings_dict: dict):
        """Handle settings being saved."""
        try:
            # Update AI service configuration
            if 'ai_config' in settings_dict:
                ai_config = settings_dict['ai_config']
                self.ai_service.config = ai_config
                self.ai_service.save_config()
                
                self.logger.info("AI settings updated")
                self.toast_manager.success("Settings", "AI configuration updated successfully!")
            
        except Exception as e:
            self.logger.error(f"Error updating settings: {e}")
            self.toast_manager.error("Settings Error", f"Failed to update settings: {str(e)}")
    
    def show_about_placeholder(self):
        """Show about placeholder."""
        self.toast_manager.info("About", "Ghostman v0.1.0 - AI Desktop Assistant")
    
    def quit_application(self):
        """Quit the application."""
        if self.app:
            self.app.quit()
    
    def setup_connections(self):
        """Setup signal connections."""
        try:
            # Window manager connections
            self.window_manager.state_changed.connect(self.on_window_state_changed)
            
            # App quit handling
            if self.app:
                self.app.aboutToQuit.connect(self.shutdown)
            
            self.logger.debug("Connections setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup connections: {e}")
    
    def setup_ai_connections(self):
        """Setup AI service connections."""
        try:
            # Connect prompt interface to AI service
            self.prompt_interface.message_sent.connect(self.ai_service.send_message)
            
            # Connect AI service responses back to prompt interface
            self.ai_service.response_received.connect(self.on_ai_response)
            self.ai_service.error_occurred.connect(self.on_ai_error)
            self.ai_service.request_started.connect(self.on_ai_request_started)
            self.ai_service.request_finished.connect(self.on_ai_request_finished)
            
            self.logger.debug("AI service connections setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup AI connections: {e}")
    
    def on_ai_response(self, response: str):
        """Handle AI response."""
        try:
            # Add AI response to prompt interface
            self.prompt_interface.add_ai_response(response)
            
            # Show success toast
            self.toast_manager.success("AI", "Response received", duration=2000)
            
        except Exception as e:
            self.logger.error(f"Error handling AI response: {e}")
    
    def on_ai_error(self, error_type: str, error_message: str):
        """Handle AI service errors."""
        try:
            # Hide typing indicator
            if hasattr(self.prompt_interface, 'hide_typing_indicator'):
                self.prompt_interface.hide_typing_indicator()
            
            # Show error message in prompt interface
            error_response = f"Error: {error_message}"
            if error_type == "not_configured":
                error_response = "⚠️ AI service not configured. Please set your OpenAI API key in Settings."
            elif error_type == "auth_error":
                error_response = "🔐 Invalid API key. Please check your OpenAI API key in Settings."
            elif error_type == "rate_limit":
                error_response = "⏳ Rate limit exceeded. Please try again in a moment."
            elif error_type == "network_error":
                error_response = "🌐 Network error. Please check your internet connection."
            elif error_type == "timeout":
                error_response = "⏱️ Request timed out. Please try again."
            
            self.prompt_interface.add_ai_response(error_response)
            
            # Show error toast
            self.toast_manager.error("AI Error", error_message, duration=5000)
            
        except Exception as e:
            self.logger.error(f"Error handling AI error: {e}")
    
    def on_ai_request_started(self):
        """Handle AI request started."""
        try:
            # Update system tray tooltip
            if self.system_tray:
                self.system_tray.setToolTip("Ghostman AI Assistant (Processing...)")
                
            self.logger.debug("AI request started")
            
        except Exception as e:
            self.logger.error(f"Error handling AI request started: {e}")
    
    def on_ai_request_finished(self):
        """Handle AI request finished."""
        try:
            # Update system tray tooltip
            if self.system_tray:
                if self.window_manager.current_state.value == "avatar":
                    self.system_tray.setToolTip("Ghostman AI Assistant (Minimized)")
                else:
                    self.system_tray.setToolTip("Ghostman AI Assistant (Active)")
                    
            self.logger.debug("AI request finished")
            
        except Exception as e:
            self.logger.error(f"Error handling AI request finished: {e}")
    
    def run(self):
        """Run the application."""
        try:
            if self.is_running:
                self.logger.warning("Application is already running")
                return 1
            
            # Create QApplication if not exists
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
            else:
                self.app = QApplication.instance()
            
            # Set application properties
            self.app.setApplicationName("Ghostman")
            self.app.setApplicationVersion("0.1.0")
            self.app.setOrganizationName("Ghostman")
            
            # Initialize components
            if not self.initialize():
                if self.app and QSystemTrayIcon.isSystemTrayAvailable():
                    # Show critical error via system tray if available
                    tray = QSystemTrayIcon()
                    tray.showMessage(
                        "Ghostman Error",
                        "Failed to initialize application components",
                        QSystemTrayIcon.MessageIcon.Critical,
                        3000
                    )
                return 1
            
            # Start in avatar mode
            self.window_manager.show_avatar()
            
            # Show welcome toast
            self.toast_manager.success(
                "Ghostman", 
                "AI Assistant started! Click the avatar to begin.",
                duration=4000
            )
            
            self.is_running = True
            self.logger.info("Starting main event loop...")
            
            # Run event loop
            return self.app.exec()
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            return 0
        except Exception as e:
            self.logger.error(f"Failed to run application: {e}")
            return 1
    
    def on_window_state_changed(self, old_state: str, new_state: str):
        """Handle window state changes."""
        self.logger.info(f"Window state changed: {old_state} -> {new_state}")
        
        # Update system tray tooltip
        if self.system_tray:
            if new_state == "avatar":
                self.system_tray.setToolTip("Ghostman AI Assistant (Minimized)")
            elif new_state == "main_interface":
                self.system_tray.setToolTip("Ghostman AI Assistant (Active)")
    
    def on_tray_activated(self, reason):
        """Handle system tray activation - DISABLED for simplicity."""
        # No action on taskbar clicks - keep it simple
        pass
    
    def shutdown(self):
        """Shutdown the application."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Shutting down application...")
            
            # Hide tray icon
            if self.system_tray:
                self.system_tray.hide()
            
            # Clean up window manager
            if self.window_manager:
                self.window_manager.cleanup()
            
            # Hide all windows
            if self.avatar_widget:
                self.avatar_widget.hide()
            if self.prompt_interface:
                self.prompt_interface.hide()
            
            self.is_running = False
            self.logger.info("Application shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def apply_current_theme(self):
        """Apply the current theme to all components."""
        if not self.theme_manager:
            return
            
        try:
            # Apply theme to avatar widget
            if self.avatar_widget:
                self.avatar_widget.setStyleSheet(self.theme_manager.get_stylesheet('avatar'))
                self.update_avatar_theming()
            
            # Apply theme to prompt interface
            if self.prompt_interface:
                self.prompt_interface.setStyleSheet(self.theme_manager.get_stylesheet('prompt_interface'))
                # Apply detailed theme colors to components
                if hasattr(self.prompt_interface, 'apply_theme_colors'):
                    theme = self.theme_manager.current_theme
                    self.prompt_interface.apply_theme_colors(theme.colors, theme.fonts, theme.spacing)
            
            # Update system tray icon if theme-aware
            self.update_system_tray_theming()
            
            self.logger.info(f"Applied theme: {self.theme_manager.current_theme.name}")
            
        except Exception as e:
            self.logger.error(f"Error applying theme: {e}")
    
    def on_theme_changed(self, theme_name: str):
        """Handle theme changes from settings dialog with smooth transition."""
        try:
            if self.theme_manager.apply_theme(theme_name):
                self.apply_theme_with_transition(theme_name)
                self.logger.info(f"Theme changed to: {theme_name}")
            else:
                self.toast_manager.error("Theme Error", f"Could not apply theme: {theme_name}")
                
        except Exception as e:
            self.logger.error(f"Error changing theme: {e}")
            self.toast_manager.error("Theme Error", f"Failed to change theme: {str(e)}")
    
    def apply_theme_with_transition(self, theme_name: str):
        """Apply theme with smooth transition animation."""
        try:
            # Create fade-out animation for current theme
            components = []
            
            if self.avatar_widget and self.avatar_widget.isVisible():
                components.append(self.avatar_widget)
            
            if self.prompt_interface and self.prompt_interface.isVisible():
                components.append(self.prompt_interface)
            
            if not components:
                # No visible components, apply theme immediately
                self.apply_current_theme()
                self.toast_manager.success("Theme", f"Applied theme: {theme_name}")
                return
            
            # Create animation group for fade out
            self.theme_transition_group = QParallelAnimationGroup()
            
            for component in components:
                # Create opacity effect if it doesn't exist
                if not component.graphicsEffect():
                    opacity_effect = QGraphicsOpacityEffect()
                    component.setGraphicsEffect(opacity_effect)
                
                # Create fade-out animation
                fade_out = QPropertyAnimation(component.graphicsEffect(), b"opacity")
                fade_out.setDuration(200)
                fade_out.setStartValue(1.0)
                fade_out.setEndValue(0.7)
                fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
                
                self.theme_transition_group.addAnimation(fade_out)
            
            # Connect to apply theme when fade out completes
            self.theme_transition_group.finished.connect(
                lambda: self.complete_theme_transition(theme_name, components)
            )
            
            # Start fade-out
            self.theme_transition_group.start()
            
        except Exception as e:
            self.logger.error(f"Error during theme transition: {e}")
            # Fallback to immediate theme application
            self.apply_current_theme()
            self.toast_manager.success("Theme", f"Applied theme: {theme_name}")
    
    def complete_theme_transition(self, theme_name: str, components: list):
        """Complete the theme transition by applying the new theme and fading back in."""
        try:
            # Apply the new theme
            self.apply_current_theme()
            
            # Create fade-in animation group
            fade_in_group = QParallelAnimationGroup()
            
            for component in components:
                if component.graphicsEffect():
                    # Create fade-in animation
                    fade_in = QPropertyAnimation(component.graphicsEffect(), b"opacity")
                    fade_in.setDuration(300)
                    fade_in.setStartValue(0.7)
                    fade_in.setEndValue(1.0)
                    fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
                    
                    fade_in_group.addAnimation(fade_in)
            
            # Connect to show success message when fade in completes
            fade_in_group.finished.connect(
                lambda: self.toast_manager.success("Theme", f"Applied theme: {theme_name}")
            )
            
            # Start fade-in
            fade_in_group.start()
            
        except Exception as e:
            self.logger.error(f"Error completing theme transition: {e}")
            self.toast_manager.success("Theme", f"Applied theme: {theme_name}")
    
    def update_avatar_theming(self):
        """Update avatar widget theme-specific styling."""
        if not self.theme_manager or not self.avatar_widget:
            return
            
        try:
            theme = self.theme_manager.current_theme
            colors = theme.colors
            spacing = theme.spacing
            
            # Use the avatar widget's theme method
            if hasattr(self.avatar_widget, 'apply_theme_colors'):
                self.avatar_widget.apply_theme_colors(colors, spacing)
            else:
                # Fallback to direct styling
                self.avatar_widget.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {colors.background_dark};
                        border: 2px solid {colors.avatar_border};
                        border-radius: 30px;
                    }}
                """)
                
                # Update glow effect color
                if hasattr(self.avatar_widget, 'shadow_effect'):
                    from PyQt6.QtGui import QColor
                    glow_color = QColor()
                    glow_color.setNamedColor(colors.avatar_glow)
                    self.avatar_widget.shadow_effect.setColor(glow_color)
            
        except Exception as e:
            self.logger.error(f"Error updating avatar theming: {e}")
    
    def update_system_tray_theming(self):
        """Update system tray icon based on current theme."""
        if not self.system_tray or not self.theme_manager:
            return
            
        try:
            # For now, we'll keep the existing icon but could add theme-aware icons later
            theme = self.theme_manager.current_theme
            tooltip = f"Ghostman AI Assistant ({theme.name} theme)"
            
            if hasattr(self, 'window_manager') and self.window_manager:
                if self.window_manager.current_state.value == "avatar":
                    tooltip += " (Minimized)"
                else:
                    tooltip += " (Active)"
            
            self.system_tray.setToolTip(tooltip)
            
        except Exception as e:
            self.logger.error(f"Error updating system tray theming: {e}")
    
    def get_theme_manager(self):
        """Get the theme manager instance."""
        return self.theme_manager

def setup_logging():
    """Setup application logging."""
    import os
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_dir = Path(appdata) / "Ghostman"
    else:
        log_dir = Path.home() / ".ghostman"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                log_dir / "ghostman.log", 
                encoding='utf-8'
            )
        ]
    )