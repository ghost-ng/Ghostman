"""
Application Coordinator for Ghostman.

Central coordination point that manages the 2-state system,
UI components, and application lifecycle.
"""

import logging
import sys
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from ..domain.models.app_state import AppState, StateChangeEvent
from ..domain.services.state_machine import TwoStateMachine
from ..infrastructure.storage.settings_manager import settings
# UI imports - will be available after implementation
# from ..presentation.ui.main_window import MainWindow
# from ..presentation.ui.system_tray import EnhancedSystemTray

logger = logging.getLogger("ghostman.coordinator")


class AppCoordinator(QObject):
    """
    Central coordinator managing the entire Ghostman application.
    
    Responsibilities:
    - Initialize and coordinate all major components
    - Manage the 2-state system (Avatar ↔ Tray)
    - Handle application lifecycle events
    - Coordinate communication between UI and services
    """
    
    # Application lifecycle signals
    app_initialized = pyqtSignal()
    app_shutdown = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._app: Optional[QApplication] = None
        self._state_machine: Optional[TwoStateMachine] = None
        self._main_window = None  # Will be MainWindow instance
        self._system_tray = None  # Will be EnhancedSystemTray instance
        self._initialized = False
        
        logger.info("AppCoordinator created")
    
    def initialize(self) -> bool:
        """
        Initialize the application and all its components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Ghostman application...")
            
            # Get current QApplication instance
            self._app = QApplication.instance()
            if not self._app:
                logger.error("QApplication not found - must be created before AppCoordinator")
                return False
            
            # Initialize state machine
            self._state_machine = TwoStateMachine(settings)
            self._state_machine.state_changed.connect(self._on_state_changed)
            
            # Initialize UI components (will be implemented)
            self._initialize_ui_components()
            
            # Set initial state based on settings
            initial_state = AppState(settings.get('app.current_state', 'tray'))
            
            if initial_state == AppState.AVATAR:
                self._show_avatar_mode()
            else:
                self._show_tray_mode()
            
            self._initialized = True
            self.app_initialized.emit()
            
            # Show startup notification with avatar icon
            if self._system_tray:
                # Use the same icon as the tray icon (which includes the avatar)
                self._system_tray.show_message(
                    "Ghostman Started",
                    "AI Assistant is ready in system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            
            logger.info("Ghostman application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return False
    
    def _initialize_ui_components(self):
        """Initialize UI components - MainWindow and SystemTray."""
        try:
            # Import here to avoid circular imports
            from ..presentation.ui.main_window import MainWindow
            from ..presentation.ui.system_tray import EnhancedSystemTray
            
            # Initialize system tray
            self._system_tray = EnhancedSystemTray(self)
            self._system_tray.show_avatar_requested.connect(self._show_avatar_mode)
            self._system_tray.settings_requested.connect(self._show_settings)
            self._system_tray.quit_requested.connect(self._quit_application)
            # Show the system tray icon
            self._system_tray.show()
            
            # Initialize main window (hidden initially)
            self._main_window = MainWindow(self)
            self._main_window.minimize_requested.connect(self._show_tray_mode)
            self._main_window.close_requested.connect(self._show_tray_mode)
            self._main_window.settings_requested.connect(self._show_settings)
            
            logger.debug("UI components initialized successfully")
            
        except ImportError as e:
            logger.error(f"UI components not yet implemented: {e}")
            # Create placeholder components for testing
            self._system_tray = None
            self._main_window = None
    
    def start_in_tray_mode(self):
        """Start the application in tray mode."""
        if not self._initialized:
            logger.error("Cannot start - application not initialized")
            return
        
        self._state_machine.to_tray_mode("app_start")
        logger.info("Application started in tray mode")
    
    def shutdown(self):
        """Gracefully shutdown the application."""
        logger.info("Shutting down Ghostman application...")
        
        self.app_shutdown.emit()
        
        # Hide UI components
        if self._main_window:
            self._main_window.hide()
        
        if self._system_tray:
            self._system_tray.hide()
        
        # Save final state
        if self._state_machine:
            settings.set('app.current_state', self._state_machine.current_state.value)
        
        logger.info("Ghostman application shutdown complete")
    
    def _on_state_changed(self, event: StateChangeEvent):
        """Handle state change events from the state machine."""
        logger.debug(f"State changed: {event.from_state.value} -> {event.to_state.value}")
        
        # Update UI based on new state
        if event.to_state == AppState.AVATAR:
            self._show_main_window()
            self._update_tray_for_avatar_mode()
        elif event.to_state == AppState.TRAY:
            self._hide_main_window()
            self._update_tray_for_tray_mode()
    
    def _show_avatar_mode(self):
        """Transition to Avatar (maximized) mode."""
        if self._state_machine:
            self._state_machine.to_avatar_mode("user_request")
    
    def _show_tray_mode(self):
        """Transition to Tray (minimized) mode."""
        if self._state_machine:
            self._state_machine.to_tray_mode("user_request")
    
    def _show_main_window(self):
        """Show and activate the main window."""
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()
            logger.debug("Main window shown")
    
    def _hide_main_window(self):
        """Hide the main window and any floating REPL."""
        if self._main_window:
            # Hide floating REPL if it's visible
            if hasattr(self._main_window, 'floating_repl') and self._main_window.floating_repl and self._main_window.floating_repl.isVisible():
                self._main_window.floating_repl.hide()
                logger.debug("Floating REPL hidden due to main window hide")
            
            self._main_window.hide()
            logger.debug("Main window hidden")
    
    def _update_tray_for_avatar_mode(self):
        """Update system tray appearance for avatar mode."""
        if self._system_tray:
            self._system_tray.set_avatar_mode()
    
    def _update_tray_for_tray_mode(self):
        """Update system tray appearance for tray mode."""
        if self._system_tray:
            self._system_tray.set_tray_mode()
    
    def _quit_application(self):
        """Handle application quit request."""
        logger.info("Quit request received")
        self.shutdown()
        if self._app:
            self._app.quit()
    
    # Public API for other components
    
    @property
    def state_machine(self) -> Optional[TwoStateMachine]:
        """Get the state machine instance."""
        return self._state_machine
    
    @property
    def main_window(self):
        """Get the main window instance."""
        return self._main_window
    
    @property
    def system_tray(self):
        """Get the system tray instance."""
        return self._system_tray
    
    @property
    def is_initialized(self) -> bool:
        """Check if the application is initialized."""
        return self._initialized
    
    def toggle_state(self):
        """Toggle between Avatar and Tray modes."""
        if self._state_machine:
            self._state_machine.toggle_state("user_toggle")
    
    def _show_settings(self):
        """Show the settings dialog."""
        logger.info("=== SETTINGS REQUESTED - OPENING SETTINGS DIALOG ===")
        try:
            logger.debug("Importing settings dialog components...")
            from ..presentation.dialogs.settings_dialog import SettingsDialog
            from ..infrastructure.storage.settings_manager import SettingsManager
            
            logger.debug("Creating settings manager...")
            # Get settings manager (create if doesn't exist)
            if not hasattr(self, '_settings_manager') or not self._settings_manager:
                self._settings_manager = SettingsManager()
            
            logger.debug("Creating settings dialog...")
            # Create and show settings dialog
            settings_dialog = SettingsDialog(self._settings_manager, parent=self._main_window)
            settings_dialog.settings_applied.connect(self._on_settings_applied)
            settings_dialog.opacity_preview_changed.connect(self._on_opacity_preview)
            
            logger.debug("Showing settings dialog...")
            result = settings_dialog.exec()
            logger.info(f"Settings dialog closed with result: {result}")
            
        except Exception as e:
            logger.error(f"Failed to show settings dialog: {e}")
            import traceback
            traceback.print_exc()
            # Show error message if possible
            if self._main_window:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self._main_window, 
                    "Error", 
                    f"Failed to open settings dialog:\n{str(e)}"
                )
    
    def _on_settings_applied(self, config: dict):
        """Handle settings being applied."""
        logger.info("=== COORDINATOR: APPLYING SETTINGS TO RUNNING APPLICATION ===")
        logger.info(f"Settings categories received: {list(config.keys())}")
        
        try:
            # Apply interface settings
            if "interface" in config:
                self._apply_interface_settings(config["interface"])
            
            # Apply AI model settings  
            if "ai_model" in config:
                self._apply_ai_model_settings(config["ai_model"])
            
            # Apply advanced settings
            if "advanced" in config:
                self._apply_advanced_settings(config["advanced"])
            
            logger.info("=== SETTINGS SUCCESSFULLY APPLIED TO RUNNING APPLICATION ===")
            
        except Exception as e:
            logger.error(f"Failed to apply settings to running application: {e}")
    
    def _on_opacity_preview(self, opacity: float):
        """Handle live opacity preview changes from settings dialog."""
        logger.debug(f"Live opacity preview: {opacity:.2f}")
        
        # Apply immediate preview to floating REPL if available
        if (self._main_window and 
            hasattr(self._main_window, 'floating_repl') and 
            self._main_window.floating_repl and
            self._main_window.floating_repl.isVisible()):
            
            self._main_window.floating_repl.set_panel_opacity(opacity)
            logger.debug(f"Applied live opacity preview to REPL: {opacity:.2f}")
    
    def _apply_interface_settings(self, interface_config: dict):
        """Apply interface settings to the running UI."""
        logger.debug(f"Applying interface settings: {interface_config}")
        
        if self._main_window:
            # Apply opacity ONLY to floating REPL panel backgrounds, NOT the entire window
            if "opacity" in interface_config:
                opacity_percent = interface_config["opacity"]
                # Convert percent (10-100) to float (0.1-1.0) for panel opacity
                if isinstance(opacity_percent, (int, float)):
                    panel_opacity = max(0.1, min(1.0, float(opacity_percent) / 100.0))
                    
                    # Apply panel opacity to floating REPL (background only)
                    if hasattr(self._main_window, 'floating_repl') and self._main_window.floating_repl:
                        self._main_window.floating_repl.set_panel_opacity(panel_opacity)
                        logger.info(f"Floating REPL panel opacity set to: {panel_opacity:.2f} ({opacity_percent}%)")
                    else:
                        logger.debug("Floating REPL not available for panel opacity setting")
                    
                    # Avatar window opacity remains unchanged (fully opaque)
                    logger.debug("Avatar window opacity unchanged - panel opacity only affects REPL backgrounds")
            
            # Apply always on top
            if "always_on_top" in interface_config:
                always_on_top = interface_config["always_on_top"]
                self._update_window_flags(always_on_top)
                logger.info(f"Always on top set to: {always_on_top}")
    
    def _apply_ai_model_settings(self, ai_model_config: dict):
        """Apply AI model settings."""
        logger.debug(f"AI model configuration updated: {ai_model_config.get('model_name', 'unknown')}")
        # TODO: Update AI service configuration when implemented
        # This would configure the actual AI client with new model settings
        for key, value in ai_model_config.items():
            display_value = "***MASKED***" if key == "api_key" and value else value
            logger.debug(f"  AI {key}: {display_value}")
    
    def _apply_advanced_settings(self, advanced_config: dict):
        """Apply advanced settings."""
        logger.debug(f"Applying advanced settings: {advanced_config}")
        
        # Apply log level changes
        if "log_level" in advanced_config:
            log_level = advanced_config["log_level"]
            logger.info(f"Log level would be set to: {log_level} (requires restart to take full effect)")
        
        if "enable_debug" in advanced_config:
            debug_enabled = advanced_config["enable_debug"]
            logger.info(f"Debug logging set to: {debug_enabled}")
    
    def _update_window_flags(self, always_on_top: bool):
        """Update window flags for always on top behavior."""
        if not self._main_window:
            return
        
        try:
            from PyQt6.QtCore import Qt
            current_flags = self._main_window.windowFlags()
            
            if always_on_top:
                new_flags = current_flags | Qt.WindowType.WindowStaysOnTopHint
                logger.debug("Adding WindowStaysOnTopHint flag")
            else:
                new_flags = current_flags & ~Qt.WindowType.WindowStaysOnTopHint
                logger.debug("Removing WindowStaysOnTopHint flag")
            
            # Apply new flags
            was_visible = self._main_window.isVisible()
            self._main_window.setWindowFlags(new_flags)
            
            if was_visible:
                self._main_window.show()
                logger.debug("Window flags updated and window reshown")
            
            # Also apply to floating REPL
            if hasattr(self._main_window, 'floating_repl') and self._main_window.floating_repl:
                repl_flags = self._main_window.floating_repl.windowFlags()
                if always_on_top:
                    repl_new_flags = repl_flags | Qt.WindowType.WindowStaysOnTopHint
                else:
                    repl_new_flags = repl_flags & ~Qt.WindowType.WindowStaysOnTopHint
                
                repl_was_visible = self._main_window.floating_repl.isVisible()
                self._main_window.floating_repl.setWindowFlags(repl_new_flags)
                if repl_was_visible:
                    self._main_window.floating_repl.show()
                    logger.debug("Floating REPL window flags also updated")
            
        except Exception as e:
            logger.error(f"Failed to update window flags: {e}")