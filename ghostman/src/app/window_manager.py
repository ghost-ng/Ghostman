"""Window state management for Ghostman application."""

from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import QApplication, QMenu
from PyQt6.QtGui import QAction
from enum import Enum
from typing import Optional
import logging
import json
from pathlib import Path

class WindowState(Enum):
    AVATAR = "avatar"
    MAIN_INTERFACE = "main_interface"
    HIDDEN = "hidden"

class WindowManager(QObject):
    """Manages window states and positioning."""
    
    # Signals
    state_changed = pyqtSignal(str, str)  # old_state, new_state
    
    def __init__(self, avatar_widget, toast_manager, settings_path: Optional[Path] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        self.avatar_widget = avatar_widget
        self.toast_manager = toast_manager
        self.prompt_window = None  # Will be set later
        self.application = None  # Will be set later for Settings access
        
        self.current_state = WindowState.AVATAR
        
        # Use proper config path
        if settings_path:
            self.settings_path = settings_path
        else:
            import os
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.settings_path = Path(appdata) / "Ghostman" / "window_positions.json"
            else:
                self.settings_path = Path.home() / ".ghostman" / "window_positions.json"
        
        # Default positions
        self.default_avatar_pos = None
        self.default_prompt_pos = None
        
        self.load_window_positions()
        self.setup_connections()
        
        # Screen change detection
        self.screen_timer = QTimer()
        self.screen_timer.timeout.connect(self.check_screen_changes)
        self.screen_timer.start(5000)  # Check every 5 seconds
    
    def setup_connections(self):
        """Setup signal connections - MINIMAL."""
        # Avatar widget signals - ONLY right-click context menu
        self.avatar_widget.right_clicked.connect(self.show_avatar_context_menu)
    
    def set_prompt_window(self, prompt_window):
        """Set the prompt window reference."""
        self.prompt_window = prompt_window
        if prompt_window:
            # Connect prompt window signals  
            prompt_window.minimize_requested.connect(self.hide_main_interface_animated)
            prompt_window.window_closed.connect(self.hide_main_interface_animated)
            # Also connect to position changes if it has that signal
            if hasattr(prompt_window, 'position_changed'):
                prompt_window.position_changed.connect(self.save_prompt_position)
            self.logger.debug("Prompt window signals connected")
    
    def set_application(self, application):
        """Set the application reference for accessing settings."""
        self.application = application
        self.logger.debug("Application reference set")
    
    def set_state(self, new_state: WindowState):
        """Change window state."""
        if new_state == self.current_state:
            return
        
        old_state = self.current_state
        self.current_state = new_state
        
        self.logger.info(f"State changing from {old_state.value} to {new_state.value}")
        
        # Hide all windows first
        self.avatar_widget.hide()
        if self.prompt_window:
            self.prompt_window.hide()
        
        # Show appropriate window
        if new_state == WindowState.AVATAR:
            try:
                # Log screen information
                from PyQt6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().geometry()
                self.logger.info(f"Primary screen geometry: {screen.width()}x{screen.height()}")
                
                # CRITICAL FIX: Just call show() - it handles everything now
                self.avatar_widget.show()
                
                # Add delay to allow window to be fully rendered
                QTimer.singleShot(300, self.check_avatar_visibility)  # Even longer delay for Windows
                
                self.logger.info(f"Avatar widget shown and raised. Visible: {self.avatar_widget.isVisible()}")
                self.logger.info(f"Avatar window state: {self.avatar_widget.windowState()}")
                self.logger.info(f"Avatar geometry: {self.avatar_widget.geometry()}")
                self.logger.info(f"Avatar flags: {self.avatar_widget.windowFlags()}")
                
            except Exception as e:
                self.logger.error(f"Error showing avatar widget: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                if self.toast_manager:
                    self.toast_manager.error(
                        "Avatar Error", 
                        "Failed to show avatar widget"
                    )
            
            self.toast_manager.info(
                "Ghostman", 
                "Minimized to avatar mode", 
                duration=2000
            )
            
        elif new_state == WindowState.MAIN_INTERFACE:
            if self.prompt_window:
                try:
                    self.position_prompt_window()
                    self.prompt_window.show()
                    self.prompt_window.raise_()
                    self.prompt_window.activateWindow()
                except Exception as e:
                    self.logger.error(f"Error showing prompt window: {e}")
                    if self.toast_manager:
                        self.toast_manager.error(
                            "Interface Error", 
                            "Failed to show main interface"
                        )
                    # Fallback to avatar mode
                    self.set_state(WindowState.AVATAR)
                    return
            else:
                self.logger.warning("Prompt window not set, cannot show main interface")
                if self.toast_manager:
                    self.toast_manager.warning(
                        "Interface Warning", 
                        "Main interface not available"
                    )
                return
        
        self.state_changed.emit(old_state.value, new_state.value)
        self.logger.info(f"State changed to {new_state.value}")
    
    def show_avatar(self):
        """Show avatar widget - SIMPLIFIED."""
        self.logger.info("show_avatar() called")
        self.set_state(WindowState.AVATAR)
        # Avatar widget handles its own positioning and visibility now
    
    def show_main_interface(self):
        """Show main interface."""
        self.set_state(WindowState.MAIN_INTERFACE)
    
    def hide_main_interface_animated(self):
        """Hide main interface with animation and show avatar."""
        if self.current_state == WindowState.MAIN_INTERFACE and self.prompt_window:
            if hasattr(self.prompt_window, 'hide_with_animation'):
                self.prompt_window.hide_with_animation()
                # Show avatar after a short delay to allow animation to start
                QTimer.singleShot(100, self.show_avatar)
            else:
                self.show_avatar()
    
    def position_avatar_widget(self):
        """CRITICAL FIX: Simplified positioning without interfering with show()."""
        # This method is now only called from avatar_widget.show() internally
        # The avatar widget handles its own positioning via position_in_corner()
        pass  # Let avatar widget handle its own positioning
    
    def position_prompt_window(self):
        """Position prompt window on screen."""
        if not self.prompt_window:
            return
            
        if self.default_prompt_pos:
            pos = QPoint(*self.default_prompt_pos)
            if self.is_position_on_screen(pos):
                self.prompt_window.move(pos)
                return
        
        # Default positioning (center-right)
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.prompt_window.width() - 50
        y = (screen.height() - self.prompt_window.height()) // 2
        self.prompt_window.move(x, y)
        self.logger.debug(f"Prompt window positioned at default location ({x}, {y})")
    
    def is_position_on_screen(self, pos: QPoint) -> bool:
        """Check if position is visible on any screen."""
        for screen in QApplication.screens():
            if screen.geometry().contains(pos):
                return True
        return False
    
    def save_avatar_position(self, pos: QPoint):
        """Save avatar position."""
        self.default_avatar_pos = (pos.x(), pos.y())
        self.save_window_positions()
        self.logger.debug(f"Avatar position saved: {self.default_avatar_pos}")
    
    def save_prompt_position(self, pos: QPoint):
        """Save prompt window position."""
        self.default_prompt_pos = (pos.x(), pos.y())
        self.save_window_positions()
        self.logger.debug(f"Prompt window position saved: {self.default_prompt_pos}")
    
    def load_window_positions(self):
        """Load saved window positions."""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    
                avatar_pos = data.get('avatar_position')
                if avatar_pos:
                    self.default_avatar_pos = tuple(avatar_pos)
                    
                prompt_pos = data.get('prompt_position')
                if prompt_pos:
                    self.default_prompt_pos = tuple(prompt_pos)
                
                self.logger.debug("Window positions loaded")
        except Exception as e:
            self.logger.error(f"Error loading window positions: {e}")
    
    def save_window_positions(self):
        """Save window positions to file."""
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            if self.default_avatar_pos:
                data['avatar_position'] = list(self.default_avatar_pos)
            if self.default_prompt_pos:
                data['prompt_position'] = list(self.default_prompt_pos)
            
            with open(self.settings_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving window positions: {e}")
    
    def check_screen_changes(self):
        """Check for screen configuration changes."""
        try:
            # Ensure windows are still visible after screen changes
            if self.current_state == WindowState.AVATAR:
                if not self.is_position_on_screen(self.avatar_widget.pos()):
                    self.position_avatar_widget()
                    self.logger.info("Avatar repositioned after screen change")
                    
            elif self.current_state == WindowState.MAIN_INTERFACE and self.prompt_window:
                if not self.is_position_on_screen(self.prompt_window.pos()):
                    self.position_prompt_window()
                    self.logger.info("Prompt window repositioned after screen change")
        except Exception as e:
            self.logger.error(f"Error checking screen changes: {e}")
    
    def show_avatar_context_menu(self, position: QPoint):
        """Show context menu for avatar widget - BASIC MENU."""
        try:
            menu = QMenu()
            
            # Quit action only for now
            quit_action = QAction("Quit Ghostman", menu)
            quit_action.triggered.connect(QApplication.instance().quit)
            menu.addAction(quit_action)
            
            # Show the menu
            menu.exec(position)
            
            self.logger.info("Avatar context menu shown")
            
        except Exception as e:
            self.logger.error(f"Error showing avatar context menu: {e}")
    
    def show_settings_placeholder(self):
        """Show settings dialog."""
        if self.application and hasattr(self.application, 'show_settings'):
            self.application.show_settings()
        else:
            self.toast_manager.info("Settings", "Settings dialog not connected")
    
    def show_help_placeholder(self):
        """Show help dialog."""
        # TODO: Implement help dialog
        self.toast_manager.info("Help", "Help documentation coming soon!\n\nFor now, check README.md")
    
    def show_about_placeholder(self):
        """Show about dialog."""
        about_text = (
            "Ghostman v0.1.0\n"
            "AI Desktop Assistant\n\n"
            "A privacy-focused AI overlay for your desktop.\n"
            "No admin permissions required."
        )
        self.toast_manager.info("About", about_text)
    
    def check_avatar_visibility(self):
        """Check and report avatar visibility status after show attempt."""
        try:
            if self.avatar_widget:
                visible = self.avatar_widget.isVisible()
                opacity = self.avatar_widget.windowOpacity()
                pos = self.avatar_widget.pos()
                size = self.avatar_widget.size()
                geometry = self.avatar_widget.geometry()
                
                self.logger.info(f"Avatar visibility check - Visible: {visible}, Opacity: {opacity}")
                self.logger.info(f"Avatar position: ({pos.x()}, {pos.y()}), Size: {size.width()}x{size.height()}")
                self.logger.info(f"Avatar geometry: {geometry}")
                
                # Check if position is on screen
                from PyQt6.QtWidgets import QApplication
                screen_geometry = QApplication.primaryScreen().geometry()
                on_screen = screen_geometry.intersects(geometry)
                self.logger.info(f"Avatar on screen: {on_screen}, Screen: {screen_geometry}")
                
                if not visible:
                    self.logger.warning("Avatar is not visible! Attempting to force show...")
                    self.avatar_widget.show()
                    self.avatar_widget.raise_()
                    self.avatar_widget.activateWindow()
                    
                if opacity < 1.0:
                    self.logger.warning(f"Avatar opacity is low: {opacity}. Setting to full opacity...")
                    self.avatar_widget.setWindowOpacity(1.0)
                    
                # Force a repaint
                self.avatar_widget.repaint()
                
        except Exception as e:
            self.logger.error(f"Error checking avatar visibility: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        self.screen_timer.stop()
        self.save_window_positions()
        self.logger.info("Window manager cleaned up")