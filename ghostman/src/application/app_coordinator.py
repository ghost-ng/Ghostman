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
            
            # Show startup notification
            if self._system_tray:
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
            self._system_tray.quit_requested.connect(self._quit_application)
            # Show the system tray icon
            self._system_tray.show()
            
            # Initialize main window (hidden initially)
            self._main_window = MainWindow(self)
            self._main_window.minimize_requested.connect(self._show_tray_mode)
            self._main_window.close_requested.connect(self._show_tray_mode)
            
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