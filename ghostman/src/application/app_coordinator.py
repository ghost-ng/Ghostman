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
        self._settings_dialog = None  # Keep reference to prevent garbage collection
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
            
            # Apply interface settings (opacity, always on top) immediately
            try:
                interface_cfg = {
                    'opacity': settings.get('interface.opacity', 90),
                    'always_on_top': settings.get('interface.always_on_top', settings.get('ui.always_on_top', True))
                }
                self._apply_interface_settings(interface_cfg)
            except Exception as e:
                logger.warning(f"Failed applying startup interface settings: {e}")

            # Set initial state based on settings (tray/avatar)
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
                    "Spector",
                    "AI Assistant is ready in system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            
            # Disabled auto-loading of last conversation - user requested not to auto-load
            # from PyQt6.QtCore import QTimer
            # QTimer.singleShot(500, self._restore_current_conversation_state)
            
            logger.info("Ghostman application initialized successfully")
            # Diagnostic path logging
            try:
                from ..infrastructure.logging.logging_config import _resolve_log_dir  # type: ignore
                paths = settings.get_paths() if hasattr(settings, 'get_paths') else {}
                logger.info("PATHS: settings_dir=%s settings_file=%s key_file=%s logs_dir=%s",
                            paths.get('settings_dir'),
                            paths.get('settings_file'),
                            paths.get('key_file'),
                            str(_resolve_log_dir()))
            except Exception:
                pass
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
            self._system_tray.help_requested.connect(self._show_browser_help)
            self._system_tray.quit_requested.connect(self._quit_application)
            # Show the system tray icon
            self._system_tray.show()
            
            # Initialize main window (hidden initially)
            self._main_window = MainWindow(self)
            self._main_window.minimize_requested.connect(self._show_tray_mode)
            self._main_window.close_requested.connect(self._show_tray_mode)
            self._main_window.settings_requested.connect(self._show_settings)
            self._main_window.help_requested.connect(self._show_browser_help)
            self._main_window.quit_requested.connect(self._quit_application)
            # Note: conversations signal is handled directly in MainWindow
            
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
        
        # Run cleanup operations
        self._cleanup_on_shutdown()
        
        # Hide UI components
        if self._main_window:
            self._main_window.hide()
        
        if self._system_tray:
            self._system_tray.hide()
        
        # Save final state
        if self._state_machine:
            settings.set('app.current_state', self._state_machine.current_state.value)
        
        logger.info("Ghostman application shutdown complete")
    
    def _save_current_conversation_state(self):
        """Save the currently active conversation with unsaved messages and auto-generated title."""
        try:
            if (self._main_window and 
                hasattr(self._main_window, 'floating_repl') and
                self._main_window.floating_repl and
                hasattr(self._main_window.floating_repl, 'repl_widget') and
                self._main_window.floating_repl.repl_widget):
                
                current_conversation_id = self._main_window.floating_repl.repl_widget.get_current_conversation_id()
                
                if current_conversation_id:
                    # Save conversation ID to settings
                    settings.set('conversation.last_active_id', current_conversation_id)
                    logger.info(f"💾 Saved active conversation ID: {current_conversation_id}")
                    
                    # Check for unsaved messages first
                    repl_widget = self._main_window.floating_repl.repl_widget
                    has_unsaved = False
                    if hasattr(repl_widget, '_has_unsaved_messages'):
                        has_unsaved = repl_widget._has_unsaved_messages()
                        if has_unsaved:
                            logger.info("💾 Detected unsaved messages, will save before shutdown")
                    
                    # Get the AI service integration to save the conversation and generate title
                    ai_service = None
                    if hasattr(repl_widget, 'conversation_manager') and repl_widget.conversation_manager:
                        ai_service = repl_widget.conversation_manager.get_ai_service()
                    
                    if ai_service and hasattr(ai_service, 'conversation_service'):
                        # Use Qt timer to safely handle async operations
                        from PyQt6.QtCore import QTimer
                        
                        def save_with_title():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    # Save current conversation context and any unsaved messages
                                    logger.info("💾 Saving current conversation context and any unsaved messages...")
                                    loop.run_until_complete(ai_service._save_current_conversation())
                                    
                                    # Generate and update title if conversation has substantial content
                                    conversation = loop.run_until_complete(
                                        ai_service.conversation_service.get_conversation(current_conversation_id, include_messages=True)
                                    )
                                    
                                    if conversation and len(conversation.messages) >= 2:
                                        # Check if title is still default/generic
                                        if conversation.title in ["New Conversation", "Untitled Conversation"] or not conversation.title.strip():
                                            generated_title = loop.run_until_complete(
                                                ai_service.conversation_service.generate_conversation_title(current_conversation_id)
                                            )
                                            
                                            if generated_title:
                                                # Update conversation title
                                                loop.run_until_complete(
                                                    ai_service.conversation_service.update_conversation_title(
                                                        current_conversation_id, generated_title
                                                    )
                                                )
                                                logger.info(f"📝 Generated and saved conversation title: {generated_title}")
                                            else:
                                                logger.debug("No title generated - keeping current title")
                                        else:
                                            logger.debug(f"Conversation already has custom title: {conversation.title}")
                                    else:
                                        logger.debug("Conversation too short for title generation")
                                        
                                finally:
                                    loop.close()
                            except Exception as e:
                                logger.error(f"✗ Failed to save conversation with title: {e}")
                        
                        # Schedule the save operation
                        QTimer.singleShot(100, save_with_title)
                    else:
                        logger.debug("AI service doesn't support conversation management")
                else:
                    # Clear any previously saved conversation ID
                    settings.delete('conversation.last_active_id')
                    logger.debug("No active conversation to save")
            else:
                logger.debug("REPL widget not available to save conversation state")
                
        except Exception as e:
            logger.error(f"✗ Failed to save current conversation state: {e}")
    
    def _cleanup_on_shutdown(self):
        """Comprehensive cleanup operations on application shutdown."""
        logger.info("🧹 Running comprehensive cleanup operations...")
        
        try:
            # 1. Save current conversation with any unsaved messages
            self._save_current_conversation_state()
            
            # 2. Shutdown conversation manager if available
            if (self._main_window and 
                hasattr(self._main_window, 'floating_repl') and
                self._main_window.floating_repl and
                hasattr(self._main_window.floating_repl, 'repl_widget')):
                
                repl_widget = self._main_window.floating_repl.repl_widget
                
                # Shutdown conversation manager
                if hasattr(repl_widget, 'conversation_manager') and repl_widget.conversation_manager:
                    try:
                        repl_widget.conversation_manager.shutdown()
                        logger.info("✓ Conversation manager shutdown complete")
                    except Exception as e:
                        logger.error(f"✗ Failed to shutdown conversation manager: {e}")
                
                # Stop any running timers in REPL widget
                if hasattr(repl_widget, 'autosave_timer') and repl_widget.autosave_timer:
                    try:
                        repl_widget.autosave_timer.stop()
                        logger.debug("✓ Autosave timer stopped")
                    except Exception as e:
                        logger.error(f"✗ Failed to stop autosave timer: {e}")
            
            # 3. Clear any temporary data
            try:
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                ghostman_temp_files = [f for f in os.listdir(temp_dir) if f.startswith('ghostman_')]
                for temp_file in ghostman_temp_files:
                    try:
                        os.remove(os.path.join(temp_dir, temp_file))
                    except:
                        pass  # Ignore errors cleaning temp files
                if ghostman_temp_files:
                    logger.debug(f"✓ Cleaned up {len(ghostman_temp_files)} temporary files")
            except Exception as e:
                logger.debug(f"Temp file cleanup failed: {e}")
            
            logger.info("✓ Cleanup operations completed successfully")
            
        except Exception as e:
            logger.error(f"✗ Error during cleanup operations: {e}")
    
    def _restore_current_conversation_state(self):
        """Start with fresh conversation - user must explicitly load conversations."""
        try:
            logger.debug("🆕 Starting with fresh conversation (no auto-restore)")
            # User requested that both new tabs and app start should begin with fresh conversations
            # The user must explicitly load conversations through the conversation dialog
            
            # Clear any saved conversation ID to ensure fresh start
            settings.delete('conversation.last_active_id')
            
            # The REPL widget will initialize with a fresh conversation by default
            logger.info("✨ App initialized with fresh conversation - user must load conversations explicitly")
                    
        except Exception as e:
            logger.error(f"✗ Failed to initialize fresh conversation: {e}", exc_info=True)
    
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
            # Reuse global settings singleton (avoid divergent instances / lost writes)
            self._settings_manager = settings
            
            # Create or reuse existing settings dialog (prevent multiple instances)
            if self._settings_dialog is None or not self._settings_dialog.isVisible():
                logger.debug("Creating new settings dialog...")
                self._settings_dialog = SettingsDialog(self._settings_manager, parent=self._main_window)
                self._settings_dialog.settings_applied.connect(self._on_settings_applied)
                self._settings_dialog.opacity_preview_changed.connect(self._on_opacity_preview)
            else:
                logger.debug("Bringing existing settings dialog to front...")
            
            logger.debug("Showing settings dialog...")
            self._settings_dialog.show()
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            logger.info("Settings dialog opened (non-modal)")
            
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
    
    def _show_help(self):
        """Show the help documentation."""
        logger.info("=== HELP REQUESTED - OPENING HELP DOCUMENTATION ===")
        import os
        import webbrowser
        try:
            logger.info("📖 Opening help documentation in browser")
            # Get the help file path
            current_dir = os.path.dirname(__file__)
            # Go up from src/application to src, then stay in ghostman, then to assets
            ghostman_src_root = os.path.dirname(os.path.dirname(current_dir))
            help_file = os.path.join(ghostman_src_root, 'assets', 'help', 'index.html')
            help_url = f'file:///{help_file.replace(os.sep, "/")}'
            webbrowser.open(help_url)
            logger.info(f"📖 Opened help documentation: {help_url}")
            
        except Exception as e:
            logger.error(f"Failed to open help documentation: {e}")
            import traceback
            traceback.print_exc()
            # Show error message if possible
            if self._main_window:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self._main_window, 
                    "Error", 
                    f"Failed to open help documentation:\n{str(e)}"
                )
    
    def _show_browser_help(self):
        """Open help documentation directly in the browser."""
        logger.info("=== BROWSER HELP REQUESTED - OPENING HELP IN BROWSER ===")
        try:
            import webbrowser
            from ..utils.resource_resolver import resolve_help_file
            
            help_path = resolve_help_file()
            
            if help_path:
                webbrowser.open(f"file://{help_path.absolute()}")
                logger.info("Opened help documentation in browser")
            else:
                logger.warning("Help documentation not found locally, opening online docs")
                webbrowser.open("https://github.com/ghost-ng/ghost-ng/tree/main/docs")
                
        except Exception as e:
            logger.error(f"Failed to open help in browser: {e}")
            # Fallback to regular help dialog
            self._show_help()
    
    def _on_settings_applied(self, config: dict):
        """Handle settings being applied."""
        logger.info("=== 🎛️  COORDINATOR: APPLYING SETTINGS TO RUNNING APPLICATION ===")
        logger.info(f"📦 Settings categories received: {list(config.keys())} (total: {len(config)})")
        
        # Log detailed received configuration
        for category, settings in config.items():
            logger.info(f"📂 Processing category: {category}")
            if isinstance(settings, dict):
                for key, value in settings.items():
                    display_value = "***MASKED***" if key == "api_key" and value else value
                    logger.info(f"  📋 {key}: {display_value}")
            else:
                display_value = "***MASKED***" if "api_key" in str(category).lower() and settings else settings
                logger.info(f"  📋 {category}: {display_value}")
        
        try:
            settings_applied = 0
            
            # Apply interface settings
            if "interface" in config:
                logger.info("🎨 Applying interface settings...")
                self._apply_interface_settings(config["interface"])
                settings_applied += len(config["interface"]) if isinstance(config["interface"], dict) else 1
                logger.info("✓ Interface settings applied")
            
            # Apply AI model settings  
            if "ai_model" in config:
                logger.info("🤖 Applying AI model settings...")
                self._apply_ai_model_settings(config["ai_model"])
                settings_applied += len(config["ai_model"]) if isinstance(config["ai_model"], dict) else 1
                logger.info("✓ AI model settings applied")
            
            # Apply advanced settings
            if "advanced" in config:
                logger.info("🔍 Applying advanced settings...")
                self._apply_advanced_settings(config["advanced"])
                settings_applied += len(config["advanced"]) if isinstance(config["advanced"], dict) else 1
                logger.info("✓ Advanced settings applied")
            
            # Apply font settings
            if "fonts" in config:
                logger.info("🔤 Applying font settings...")
                self._apply_font_settings(config["fonts"])
                settings_applied += len(config["fonts"]) if isinstance(config["fonts"], dict) else 1
                logger.info("✓ Font settings applied")
            
            logger.info(f"=== ✓ SETTINGS SUCCESSFULLY APPLIED: {settings_applied} items ===")
            
        except Exception as e:
            logger.error(f"✗ Failed to apply settings to running application: {e}")
            import traceback
            logger.error(f"📝 Stack trace: {traceback.format_exc()}")
        
        logger.info("")  # Add blank line for readability
    
    def _on_opacity_preview(self, opacity: float):
        """Handle live opacity preview changes from settings dialog."""
        logger.info(f"🎨 Live opacity preview triggered: {opacity:.2f}")
        
        # Apply immediate preview to floating REPL - make it visible if needed
        if (self._main_window and 
            hasattr(self._main_window, 'floating_repl') and 
            self._main_window.floating_repl):
            
            # Show the REPL if it's not visible so user can see the opacity change
            if not self._main_window.floating_repl.isVisible():
                logger.info("🎨 Making floating REPL visible for opacity preview")
                self._main_window.floating_repl.show()
                self._main_window.floating_repl.raise_()
                self._main_window.floating_repl.activateWindow()
            
            # Apply the opacity
            self._main_window.floating_repl.set_panel_opacity(opacity)
            logger.info(f"✓ Applied live opacity preview to REPL: {opacity:.2f}")
        else:
            logger.warning("⚠  No floating REPL available for opacity preview")
    
    def _apply_interface_settings(self, interface_config: dict):
        """Apply interface settings to the running UI."""
        logger.info(f"🎨 Processing interface settings: {len(interface_config)} items")
        for key, value in interface_config.items():
            logger.info(f"  🎛️  {key}: {value}")
        
        if not self._main_window:
            logger.error("⚠  No main window available - interface settings cannot be applied")
            logger.error("This indicates a critical initialization failure - shutting down")
            self.shutdown()
            return False
        
        settings_processed = 0
        
        # Apply opacity ONLY to floating REPL panel backgrounds, NOT the entire window
        if "opacity" in interface_config:
            opacity_percent = interface_config["opacity"]
            logger.info(f"🎨 Processing opacity setting: {opacity_percent}%")
            
            # Convert percent (10-100) to float (0.1-1.0) for panel opacity
            if isinstance(opacity_percent, (int, float)):
                panel_opacity = max(0.1, min(1.0, float(opacity_percent) / 100.0))
                logger.info(f"🔢 Opacity conversion: {opacity_percent}% -> {panel_opacity:.3f} (clamped: 0.1-1.0)")
                
                # Apply panel opacity to floating REPL (background only)
                if hasattr(self._main_window, 'floating_repl') and self._main_window.floating_repl:
                    logger.info("🪟 Applying opacity to floating REPL panels...")
                    self._main_window.floating_repl.set_panel_opacity(panel_opacity)
                    logger.info(f"✓ Floating REPL panel opacity applied: {panel_opacity:.3f} ({opacity_percent}%)")
                    settings_processed += 1
                else:
                    logger.warning("⚠  Floating REPL not available for panel opacity setting")
                
                # Avatar window opacity remains unchanged (fully opaque)
                logger.info("🎯 Avatar window opacity unchanged - panel opacity only affects REPL backgrounds")
            else:
                logger.error(f"✗ Invalid opacity type: {type(opacity_percent)} (expected int/float)")
        
        # Apply always on top
        if "always_on_top" in interface_config:
            always_on_top = interface_config["always_on_top"]
            logger.debug(f"📌 Processing always on top setting: {always_on_top}")
            try:
                self._update_window_flags(always_on_top)
                logger.info(f"✓ Always on top applied: {always_on_top}")
                settings_processed += 1
            except Exception as e:
                logger.error(f"✗ Failed to apply always on top: {e}")
        
        logger.info(f"🎨 Interface settings processing complete: {settings_processed}/{len(interface_config)} applied")
    
    def _apply_ai_model_settings(self, ai_model_config: dict):
        """Apply AI model settings."""
        logger.info(f"🤖 Processing AI model settings: {len(ai_model_config)} items")
        
        settings_processed = 0
        model_name = ai_model_config.get('model_name', 'not set')
        base_url = ai_model_config.get('base_url', 'not set')
        
        logger.info(f"🤖 AI Model configuration: {model_name} at {base_url}")
        
        # Log all AI model settings with proper masking
        for key, value in ai_model_config.items():
            if key == "api_key" and value:
                display_value = f"***MASKED*** (length: {len(str(value))})"
            else:
                display_value = value
            logger.info(f"  🔧 AI {key}: {display_value}")
            settings_processed += 1
        
        # TODO: Update AI service configuration when implemented
        logger.info("📝 AI service integration pending - settings stored for future use")
        logger.info(f"🤖 AI model settings processing complete: {settings_processed} items logged")
    
    def _apply_advanced_settings(self, advanced_config: dict):
        """Apply advanced settings."""
        logger.info(f"🔍 Processing advanced settings: {len(advanced_config)} items")
        
        settings_processed = 0
        
        # Apply log level changes
        if "log_level" in advanced_config:
            log_level = advanced_config["log_level"]
            logger.info(f"📊 Logging mode: {log_level}")
            if log_level == "Detailed":
                logger.info("🔍 Detailed logging mode enabled - verbose logging active")
            else:
                logger.info("📝 Standard logging mode - normal verbosity")
            logger.info(f"⚠  Logging changes require application restart to take full effect")
            settings_processed += 1
        
        # Apply log location settings
        if "log_location" in advanced_config:
            log_location = advanced_config["log_location"]
            if log_location:
                logger.info(f"📁 Custom log location: {log_location}")
            else:
                logger.info("📁 Using default log location")
            logger.info(f"⚠  Log location changes require application restart to take full effect")
            settings_processed += 1
        
        # Apply log retention settings
        if "log_retention_days" in advanced_config:
            retention_days = advanced_config["log_retention_days"]
            logger.info(f"🗑️ Log retention: {retention_days} days")
            logger.info(f"⚠  Log retention changes require application restart to take full effect")
            settings_processed += 1
        
        # Apply SSL verification settings using unified SSL service
        try:
            from ..infrastructure.ssl.ssl_service import ssl_service
            
            # Configure SSL service from settings (includes both ignore_ssl and PKI integration)
            if ssl_service.configure_from_settings(settings.get_all_settings()):
                logger.info("✓ SSL verification configured through unified SSL service")
            else:
                logger.error("✗ Failed to configure SSL verification through unified service")
            settings_processed += 1
            
        except Exception as e:
            logger.error(f"Failed to apply SSL verification settings: {e}")
            # Fallback to old behavior for backward compatibility
            if "ignore_ssl_verification" in advanced_config:
                ignore_ssl = advanced_config["ignore_ssl_verification"]
                logger.info(f"🔒 SSL verification (fallback): {'DISABLED' if ignore_ssl else 'ENABLED'}")
                
                try:
                    from ..infrastructure.ai.session_manager import session_manager
                    session_manager.configure_session(disable_ssl_verification=ignore_ssl)
                    logger.info(f"✓ SSL verification setting applied to session manager (fallback)")
                except Exception as fallback_e:
                    logger.error(f"Failed to apply SSL verification setting (fallback): {fallback_e}")
            settings_processed += 1
        
        # Log any additional advanced settings
        for key, value in advanced_config.items():
            if key not in ["log_level", "log_location", "log_retention_days", "ignore_ssl_verification"]:
                logger.info(f"  🔧 Advanced {key}: {value}")
                settings_processed += 1
        
        logger.info(f"🔍 Advanced settings processing complete: {settings_processed}/{len(advanced_config)} applied")
    
    def _apply_font_settings(self, fonts_config: dict):
        """Apply font settings to the UI."""
        logger.info(f"🔤 Processing font settings: {len(fonts_config)} categories")
        
        settings_processed = 0
        
        # Process each font category
        for font_type, font_config in fonts_config.items():
            if isinstance(font_config, dict):
                logger.info(f"  📝 {font_type} font: {font_config}")
                settings_processed += 1
        
        # Refresh fonts in REPL widget if available
        if (hasattr(self._main_window, 'floating_repl') and 
            self._main_window.floating_repl and 
            hasattr(self._main_window.floating_repl, 'repl_widget')):
            repl_widget = self._main_window.floating_repl.repl_widget
            if hasattr(repl_widget, 'refresh_fonts'):
                try:
                    repl_widget.refresh_fonts()
                    logger.info("🔤 REPL fonts refreshed successfully")
                except Exception as e:
                    logger.error(f"Failed to refresh REPL fonts: {e}")
        
        logger.info(f"🔤 Font settings processing complete: {settings_processed}/{len(fonts_config)} applied")
    
    def _update_window_flags(self, always_on_top: bool):
        """Update window flags for always on top behavior with minimal flicker."""
        if not self._main_window:
            return
        
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QApplication
            
            # Batch updates to minimize flicker
            windows_to_update = []
            
            # Check main window (avatar)
            current_flags = self._main_window.windowFlags()
            if always_on_top:
                new_flags = current_flags | Qt.WindowType.WindowStaysOnTopHint
            else:
                new_flags = current_flags & ~Qt.WindowType.WindowStaysOnTopHint
                
            # Only update if flags actually changed
            if new_flags != current_flags:
                windows_to_update.append((self._main_window, new_flags, self._main_window.isVisible(), "avatar"))
            
            # Check floating REPL
            if hasattr(self._main_window, 'floating_repl') and self._main_window.floating_repl:
                repl_flags = self._main_window.floating_repl.windowFlags()
                if always_on_top:
                    repl_new_flags = repl_flags | Qt.WindowType.WindowStaysOnTopHint
                else:
                    repl_new_flags = repl_flags & ~Qt.WindowType.WindowStaysOnTopHint
                
                # Only update if flags actually changed
                if repl_new_flags != repl_flags:
                    windows_to_update.append((self._main_window.floating_repl, repl_new_flags, self._main_window.floating_repl.isVisible(), "REPL"))
            
            # Apply all updates quickly in sequence to minimize flicker
            if windows_to_update:
                # Disable updates during flag changes
                QApplication.setQuitOnLastWindowClosed(False)
                
                for window, flags, was_visible, window_type in windows_to_update:
                    window.setWindowFlags(flags)
                    if was_visible:
                        window.show()
                
                QApplication.setQuitOnLastWindowClosed(True)
                window_names = [item[3] for item in windows_to_update]
                logger.debug(f"Updated {len(windows_to_update)} windows ({', '.join(window_names)}) with always_on_top={always_on_top}")
            else:
                logger.debug(f"No window flag changes needed for always_on_top={always_on_top}")
                logger.debug("Floating REPL window flags also updated")
            
        except Exception as e:
            logger.error(f"Failed to update window flags: {e}")