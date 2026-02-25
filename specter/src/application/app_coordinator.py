"""
Application Coordinator for Specter.

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
from .single_instance import SingleInstanceDetector, SingleInstanceError
from ..infrastructure.rag_coordinator import initialize_rag_coordinator, cleanup_rag_coordinator, get_rag_coordinator
# UI imports - will be available after implementation
# from ..presentation.ui.main_window import MainWindow
# from ..presentation.ui.system_tray import EnhancedSystemTray

logger = logging.getLogger("specter.coordinator")


class AppCoordinator(QObject):
    """
    Central coordinator managing the entire Specter application.
    
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
        self._single_instance: Optional[SingleInstanceDetector] = None
        self._rag_coordinator = None  # RAG coordinator instance
        self._api_validator = None  # Periodic API validator instance

        logger.info("AppCoordinator created")
    
    def initialize(self) -> bool:
        """
        Initialize the application and all its components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Specter application...")
            
            # Initialize single instance detection first
            self._single_instance = SingleInstanceDetector(app_name="Specter")
            
            # Check if another instance is already running
            logger.info("Checking for existing instances...")
            try:
                detection_result = self._single_instance.detect_running_instance()
                if detection_result.is_running:
                    logger.error(f"Another instance of Specter is already running (detected via {detection_result.detection_method})")
                    return False
                logger.info("No existing instance detected")
                
                # Acquire instance lock
                if not self._single_instance.acquire_instance_lock():
                    logger.error("Failed to acquire single instance lock")
                    return False
                logger.info("Single instance lock acquired successfully")
            except Exception as e:
                logger.warning(f"Single instance detection failed: {e} - continuing anyway")
                self._single_instance = None
            
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

            # Initialize periodic API validator
            self._initialize_api_validator()

            # Wire up settings-change listener so session_manager auto-reconfigures
            # when SSL/PKI settings are modified at runtime.
            try:
                from ..infrastructure.ai.session_manager import session_manager
                settings.on_change(session_manager._on_settings_changed)
                logger.info("Settings change listener wired to session manager")
            except Exception as e:
                logger.warning(f"Failed to wire settings change listener: {e}")

            # Initialize RAG coordinator
            self._initialize_rag_system()

            # Initialize skills system
            self._initialize_skills_system()

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
            logger.info(f"🎯 Setting initial app state: {initial_state.value}")

            if initial_state == AppState.AVATAR:
                logger.info("📍 BEFORE: Calling _show_avatar_mode()")
                self._show_avatar_mode()
                logger.info("✓ AFTER: _show_avatar_mode() returned")
            else:
                logger.info("📍 BEFORE: Calling _show_tray_mode()")
                self._show_tray_mode()
                logger.info("✓ AFTER: _show_tray_mode() returned")

            logger.info("📍 BEFORE: Setting _initialized = True")
            self._initialized = True
            logger.info("✓ AFTER: _initialized set to True")

            logger.info("📍 BEFORE: Emitting app_initialized signal")
            try:
                self.app_initialized.emit()
                logger.info("✓ AFTER: app_initialized signal emitted successfully")
            except Exception as e:
                logger.error(f"✗ CRASH during app_initialized.emit(): {e}", exc_info=True)
                raise

            # Connect to REPL widget's startup_fully_complete signal to show toast only when ready
            # This prevents race conditions with clicking the toast before everything loads
            if self._main_window and hasattr(self._main_window, 'repl_widget'):
                try:
                    logger.info("📍 Connecting to startup_fully_complete signal for delayed toast")
                    self._main_window.repl_widget.startup_fully_complete.connect(self._show_startup_toast)
                except Exception as e:
                    logger.error(f"✗ Failed to connect startup signal: {e}")
                    # Fallback: show toast immediately if connection fails
                    self._show_startup_toast()
            else:
                logger.warning("⚠ Main window or REPL widget not available, showing toast immediately")
                self._show_startup_toast()

            # NOTE: Initial conversation creation is handled by REPLWidget creating the first tab
            # No need to create additional conversations here to avoid duplicates
            # The tab creation in REPLWidget automatically creates its conversation

            logger.info("Specter application initialized successfully")
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

    def _show_startup_toast(self):
        """Show startup toast notification after all async initialization is complete."""
        logger.info("📍 STARTUP FULLY COMPLETE: Showing system tray notification")
        if self._system_tray:
            try:
                # Use the same icon as the tray icon (which includes the avatar)
                # Use selected persona name for toast
                try:
                    from ..domain.models.avatar_personas import get_avatar, DEFAULT_AVATAR_ID
                    from ..infrastructure.storage.settings_manager import settings as _s
                    _aid = _s.get('avatar.selected', DEFAULT_AVATAR_ID)
                    _av = get_avatar(_aid)
                    _toast_name = _av.name if _av else "Specter"
                except Exception:
                    _toast_name = "Specter"
                self._system_tray.show_message(
                    _toast_name,
                    "AI Assistant is ready in system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
                logger.info("✓ System tray notification shown after full startup")
            except Exception as e:
                logger.error(f"✗ CRASH during show_message(): {e}", exc_info=True)
        else:
            logger.warning("⚠ System tray is None, skipping notification")

    def _initialize_ui_components(self):
        """Initialize UI components - MainWindow and SystemTray."""
        try:
            # Import here to avoid circular imports
            from ..presentation.ui.main_window import MainWindow
            from ..presentation.ui.system_tray import EnhancedSystemTray
            
            # Initialize system tray
            self._system_tray = EnhancedSystemTray(self)
            self._system_tray.show_avatar_requested.connect(self._show_avatar_mode)
            self._system_tray.screen_capture_requested.connect(self._trigger_screen_capture)
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
    
    def _initialize_api_validator(self):
        """Initialize periodic API validation service."""
        try:
            from ..infrastructure.ai.periodic_api_validator import PeriodicAPIValidator

            self._api_validator = PeriodicAPIValidator()

            # Signals are connected directly by FloatingREPLWindow's floating banner
            # No manual connection needed here

            # Start periodic validation checks
            self._api_validator.start_periodic_checks()
            logger.info("Periodic API validator initialized (5-minute intervals)")

        except Exception as e:
            logger.error(f"Failed to initialize API validator: {e}")
            self._api_validator = None

    def _initialize_rag_system(self):
        """Initialize RAG system integration."""
        try:
            # Import conversation service
            from ..infrastructure.conversation_management.services.conversation_service import ConversationService
            from ..infrastructure.conversation_management.repositories.conversation_repository import ConversationRepository

            # Initialize conversation service (if not already available)
            if not hasattr(self, '_conversation_service'):
                repo = ConversationRepository()
                self._conversation_service = ConversationService(repo)

            # Initialize RAG coordinator
            self._rag_coordinator = initialize_rag_coordinator(self._conversation_service)

            if self._rag_coordinator.is_enabled():
                logger.info("RAG system initialized successfully")

                # Enhance main window REPL if available
                self._enhance_main_window_rag()
            else:
                status = self._rag_coordinator.get_status()
                logger.info(f"RAG system disabled: {status.get('error', 'Unknown reason')}")

        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")

    def _initialize_skills_system(self):
        """Initialize skills system and register all built-in skills."""
        try:
            logger.info("Initializing skills system...")

            # Import skill manager and all built-in skills
            from ..infrastructure.skills.core.skill_manager import skill_manager
            from ..infrastructure.skills.skills_library import (
                OutlookEmailSkill,
                OutlookCalendarSkill,
                FileSearchSkill,
                ScreenCaptureSkill,
                TaskTrackerSkill,
                WebSearchSkill,
                DocxFormatterSkill,
            )

            # Register all built-in skills
            skills_to_register = [
                OutlookEmailSkill,
                OutlookCalendarSkill,
                FileSearchSkill,
                ScreenCaptureSkill,
                TaskTrackerSkill,
                WebSearchSkill,
                DocxFormatterSkill,
            ]

            registered_count = 0
            for skill_class in skills_to_register:
                try:
                    skill_manager.register_skill(skill_class)
                    registered_count += 1
                    logger.debug(f"Registered skill: {skill_class.__name__}")
                except Exception as e:
                    logger.error(f"Failed to register {skill_class.__name__}: {e}")

            logger.info(f"✓ Skills system initialized: {registered_count}/{len(skills_to_register)} skills registered")

        except Exception as e:
            logger.error(f"Failed to initialize skills system: {e}", exc_info=True)

    def _enhance_main_window_rag(self):
        """Enhance main window REPL with RAG capabilities."""
        if not self._main_window or not self._rag_coordinator:
            return
        
        try:
            # Check if main window has REPL widget
            if hasattr(self._main_window, 'repl_widget'):
                success = self._rag_coordinator.enhance_repl_widget(
                    self._main_window.repl_widget,
                    widget_id="main_window_repl"
                )
                
                if success:
                    logger.info("Main window REPL enhanced with RAG capabilities")
                else:
                    logger.warning("Failed to enhance main window REPL with RAG")
            
        except Exception as e:
            logger.error(f"Failed to enhance main window RAG: {e}")
    
    def start_in_tray_mode(self):
        """Start the application in tray mode."""
        if not self._initialized:
            logger.error("Cannot start - application not initialized")
            return
        
        self._state_machine.to_tray_mode("app_start")
        logger.info("Application started in tray mode")
    
    def shutdown(self):
        """Gracefully shutdown the application."""
        logger.info("Shutting down Specter application...")
        
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
        
        # Final emergency cleanup for single instance lock 
        try:
            if self._single_instance:
                self._single_instance.release_instance_lock()
                logger.debug("Emergency single instance lock cleanup completed")
        except Exception as e:
            logger.debug(f"Emergency single instance lock cleanup failed: {e}")
        
        logger.info("Specter application shutdown complete")
    
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
                    # Check if conversation has user messages before saving
                    repl_widget = self._main_window.floating_repl.repl_widget
                    has_user_messages = False
                    
                    # Check for user messages in the conversation
                    if hasattr(repl_widget, 'current_conversation') and repl_widget.current_conversation:
                        user_message_count = 0
                        for message in repl_widget.current_conversation.messages:
                            if hasattr(message, 'role') and message.role and str(message.role).lower() == 'user':
                                user_message_count += 1
                        
                        # Only save if there's at least one user message
                        has_user_messages = user_message_count > 0
                        logger.info(f"🔍 Conversation has {user_message_count} user messages")
                    
                    # Only save conversations that have user messages
                    if not has_user_messages:
                        logger.info(f"⏭️ Skipping save of conversation without user messages: {current_conversation_id}")
                        return
                    
                    # Save conversation ID to settings
                    settings.set('conversation.last_active_id', current_conversation_id)
                    logger.info(f"💾 Saved active conversation ID: {current_conversation_id}")
                    
                    # Check for unsaved messages first
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
            # Shutdown API validator
            if self._api_validator:
                self._api_validator.shutdown()
                logger.info("API validator shut down")

            # Cleanup RAG system first
            if self._rag_coordinator:
                cleanup_rag_coordinator()
                logger.info("RAG system cleaned up")
            
            # Continue with other cleanup operations
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
                specter_temp_files = [f for f in os.listdir(temp_dir) if f.startswith('specter_')]
                for temp_file in specter_temp_files:
                    try:
                        os.remove(os.path.join(temp_dir, temp_file))
                    except:
                        pass  # Ignore errors cleaning temp files
                if specter_temp_files:
                    logger.debug(f"✓ Cleaned up {len(specter_temp_files)} temporary files")
            except Exception as e:
                logger.debug(f"Temp file cleanup failed: {e}")
            
            # 4. Release single instance lock
            try:
                if self._single_instance:
                    self._single_instance.release_instance_lock()
                    logger.info("✓ Single instance lock released")
            except Exception as e:
                logger.error(f"✗ Failed to release single instance lock: {e}")
            
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
    
    def _create_startup_conversation(self):
        """Create a new conversation automatically when the app starts."""
        try:
            logger.info("🆕 Creating new conversation on app startup")
            
            # Clear any saved conversation ID to ensure fresh start
            settings.delete('conversation.last_active_id')
            
            # Get the main window and REPL widget to create a new conversation
            if self._main_window and hasattr(self._main_window, 'floating_repl'):
                repl_widget = self._main_window.floating_repl.repl_widget
                
                if hasattr(repl_widget, '_start_new_conversation'):
                    # Create new conversation without saving current (since this is startup)
                    repl_widget._start_new_conversation(save_current=False)
                    logger.info("✅ Successfully created startup conversation")
                else:
                    logger.warning("⚠️ REPL widget doesn't have _start_new_conversation method")
            else:
                logger.warning("⚠️ Main window or REPL widget not available for conversation creation")
                    
        except Exception as e:
            logger.error(f"✗ Failed to create startup conversation: {e}", exc_info=True)
    
    def _on_state_changed(self, event: StateChangeEvent):
        """Handle state change events from the state machine."""
        logger.info(f"🔄 State changed: {event.from_state.value} -> {event.to_state.value}")

        # Update UI based on new state
        try:
            if event.to_state == AppState.AVATAR:
                logger.info("  ➜ Transitioning to AVATAR mode...")
                self._show_main_window()
                logger.debug("  ➜ Updating tray icon...")
                self._update_tray_for_avatar_mode()
                logger.info("✓ AVATAR mode transition complete")
            elif event.to_state == AppState.TRAY:
                logger.info("  ➜ Transitioning to TRAY mode...")
                self._hide_main_window()
                logger.debug("  ➜ Updating tray icon...")
                self._update_tray_for_tray_mode()
                logger.info("✓ TRAY mode transition complete")
        except Exception as e:
            logger.error(f"✗ Error during state transition: {e}", exc_info=True)
    
    def _show_avatar_mode(self):
        """Transition to Avatar (maximized) mode."""
        logger.info("🔄 _show_avatar_mode() called")
        if self._state_machine:
            logger.debug("  - Calling state_machine.to_avatar_mode()")
            result = self._state_machine.to_avatar_mode("user_request")
            logger.debug(f"  - State machine returned: {result}")
            logger.info("✓ _show_avatar_mode() completed")
        else:
            logger.warning("⚠ Cannot show avatar mode - state machine is None")
    
    def _show_tray_mode(self):
        """Transition to Tray (minimized) mode."""
        if self._state_machine:
            self._state_machine.to_tray_mode("user_request")
    
    def _show_main_window(self):
        """Show and activate the main window."""
        if self._main_window:
            logger.info("🖥 Showing main window...")
            try:
                logger.debug("  - Calling show()")
                self._main_window.show()
                logger.debug("  - show() returned successfully")

                logger.debug("  - Calling raise_()")
                self._main_window.raise_()
                logger.debug("  - raise_() returned successfully")

                logger.debug("  - Calling activateWindow()")
                self._main_window.activateWindow()
                logger.debug("  - activateWindow() returned successfully")

                logger.info("✓ Main window shown successfully")
            except Exception as e:
                logger.error(f"✗ Error showing main window: {e}", exc_info=True)
                raise  # Re-raise to make crash visible
        else:
            logger.warning("⚠ Cannot show main window - window is None")
    
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
    
    def _trigger_screen_capture(self):
        """Trigger screen capture skill from system tray or avatar menu."""
        logger.info("Screen capture requested from menu")
        try:
            # Import skill manager
            from ..infrastructure.skills.core.skill_manager import skill_manager
            from PyQt6.QtCore import QTimer
            import asyncio

            async def execute_capture():
                try:
                    result = await skill_manager.execute_skill(
                        "screen_capture",
                        shape="rectangle",
                        border_width=0,
                        save_to_file=False,  # Don't auto-save, user clicks Save button
                        copy_to_clipboard=True
                    )

                    if result.success:
                        logger.info(f"✓ Screen capture completed: {result.message}")
                    else:
                        logger.warning(f"✗ Screen capture failed: {result.error}")

                except Exception as e:
                    logger.error(f"Screen capture failed: {e}", exc_info=True)

            def run_capture():
                """Run capture in a new event loop."""
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(execute_capture())
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Screen capture execution failed: {e}", exc_info=True)

            # Schedule execution in Qt event loop
            QTimer.singleShot(0, run_capture)

        except Exception as e:
            logger.error(f"Failed to trigger screen capture: {e}", exc_info=True)

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
            logger.info("Opening help documentation in browser")
            from ..utils.resource_resolver import resolve_help_file
            help_path = resolve_help_file("index.html")
            if help_path and help_path.exists():
                help_url = f'file:///{str(help_path).replace(os.sep, "/")}'
                webbrowser.open(help_url)
                logger.info(f"Opened help documentation: {help_url}")
            else:
                logger.error("Help file not found via resource resolver")
            
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

                # Reset API validator state when API settings change
                if self._api_validator:
                    logger.info("🔄 Resetting API validator due to AI model settings change")
                    self._api_validator.reset_failure_state()
                    # Trigger immediate validation (non-blocking, will run in background)
                    # Use QTimer to ensure it doesn't block settings dialog
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(100, self._api_validator.validate_now)
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

            # Apply avatar settings
            if "avatar" in config:
                logger.info("🎭 Applying avatar settings...")
                self._apply_avatar_settings(config["avatar"])
                settings_applied += 1
                logger.info("✓ Avatar settings applied")

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

        # Reinitialize SSL/PKI services first (in case base_url changed and requires different certs)
        logger.info("🔄 Reinitializing SSL/PKI services for new network configuration...")
        try:
            self._reinitialize_ssl_pki_services()
        except Exception as e:
            logger.error(f"✗ Error reinitializing SSL/PKI services: {e}")

        # CRITICAL: Reinitialize RAG pipeline with new AI settings
        logger.info("🔄 Reinitializing RAG pipeline with new AI settings...")
        try:
            self._reinitialize_rag_pipeline()
        except Exception as e:
            logger.error(f"✗ Error reinitializing RAG pipeline: {e}")
            import traceback
            logger.error(f"📝 Stack trace: {traceback.format_exc()}")

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
        ssl_or_pki_changed = False
        try:
            from ..infrastructure.ssl.ssl_service import ssl_service

            # Configure SSL service from settings (includes both ignore_ssl and PKI integration)
            if ssl_service.configure_from_settings(settings.get_all_settings()):
                logger.info("✓ SSL verification configured through unified SSL service")
                ssl_or_pki_changed = True
            else:
                logger.error("✗ Failed to configure SSL verification through unified service")
            settings_processed += 1

        except Exception as e:
            logger.error(f"Failed to apply SSL verification settings: {e}")
            settings_processed += 1

        # Reinitialize SSL/PKI/AI services if SSL or PKI settings changed
        if ssl_or_pki_changed:
            self._reinitialize_ssl_pki_services()
        
        # Log any additional advanced settings
        for key, value in advanced_config.items():
            if key not in ["log_level", "log_location", "log_retention_days", "ignore_ssl_verification"]:
                logger.info(f"  🔧 Advanced {key}: {value}")
                settings_processed += 1
        
        logger.info(f"🔍 Advanced settings processing complete: {settings_processed}/{len(advanced_config)} applied")

    def _reinitialize_ssl_pki_services(self):
        """
        Reinitialize SSL/PKI services and AI service to apply new security settings.

        This should be called whenever SSL verification or PKI settings change.
        """
        logger.info("🔄 Reinitializing SSL/PKI services...")

        # Reset PKI service initialization to pick up new certificates/settings
        try:
            from ..infrastructure.pki import pki_service
            logger.info("🔄 Resetting PKI service to apply new certificates...")
            pki_service.reset_initialization()

            # Reinitialize PKI to apply new settings
            if pki_service.initialize():
                logger.info("✓ PKI service reinitialized successfully")
            else:
                logger.warning("⚠ PKI service reinitialization completed without authentication")

        except Exception as pki_e:
            logger.error(f"Failed to reinitialize PKI service: {pki_e}")

        # Ensure the shared session picks up any SSL/PKI changes
        try:
            from ..infrastructure.ai.session_manager import session_manager
            session_manager.reconfigure_security()
            logger.info("✓ Session manager security reconfigured")
        except Exception as sm_e:
            logger.error(f"Failed to reconfigure session manager security: {sm_e}")

        # Reinitialize AI service to pick up new SSL/PKI settings
        try:
            logger.info("🔄 Reinitializing AI service with new SSL/PKI settings...")
            if self._main_window and hasattr(self._main_window, 'repl_widget'):
                repl_widget = self._main_window.repl_widget
                if hasattr(repl_widget, 'conversation_manager') and repl_widget.conversation_manager:
                    ai_service = repl_widget.conversation_manager.get_ai_service()
                    if ai_service:
                        if ai_service.initialize():
                            logger.info("✓ AI service reinitialized successfully with new SSL/PKI settings")
                        else:
                            logger.warning("⚠ AI service reinitialization returned False")
                    else:
                        logger.warning("⚠ No AI service available for reinitialization")
                else:
                    logger.warning("⚠ No conversation manager available for AI service reinitialization")
            else:
                logger.warning("⚠ No REPL widget available for AI service reinitialization")
        except Exception as ai_e:
            logger.error(f"Failed to reinitialize AI service: {ai_e}")

    def _reinitialize_rag_pipeline(self):
        """
        Reinitialize RAG pipeline to apply new AI settings.

        This creates a new SimpleFAISSSession with fresh configuration
        that reads from the updated settings.
        """
        logger.info("🔄 Reinitializing RAG pipeline...")

        try:
            # Access REPL widget
            if not self._main_window or not hasattr(self._main_window, 'repl_widget'):
                logger.warning("⚠ No REPL widget available for RAG reinitialization")
                return

            repl_widget = self._main_window.repl_widget

            # Close existing RAG session if present
            if hasattr(repl_widget, 'rag_session') and repl_widget.rag_session:
                try:
                    logger.info("🔄 Closing existing RAG session...")
                    if hasattr(repl_widget.rag_session, 'close'):
                        repl_widget.rag_session.close()
                    logger.info("✓ Existing RAG session closed")
                except Exception as e:
                    logger.warning(f"⚠ Error closing existing RAG session: {e}")

            # Create new RAG session with fresh configuration
            # The SimpleFAISSSession will read settings via RAGPipelineConfig.__post_init__
            logger.info("🔄 Creating new RAG session with updated settings...")
            from ..infrastructure.rag_pipeline.threading.simple_faiss_session import create_simple_faiss_session

            new_rag_session = create_simple_faiss_session()

            if new_rag_session and new_rag_session.validate(timeout=10.0):
                # Replace the RAG session in REPL widget
                repl_widget.rag_session = new_rag_session
                logger.info("✅ RAG pipeline reinitialized successfully with new settings")

                # Also update in Collections Manager if it's open
                try:
                    if hasattr(repl_widget, '_collections_dialog') and repl_widget._collections_dialog:
                        repl_widget._collections_dialog.rag_session = new_rag_session
                        logger.info("✓ Collections Manager RAG session updated")
                except Exception as e:
                    logger.debug(f"Collections Manager not available: {e}")

            else:
                logger.error("✗ RAG pipeline reinitialization failed - session validation failed")
                logger.warning("⚠ Keeping old RAG session")

        except Exception as e:
            logger.error(f"Failed to reinitialize RAG pipeline: {e}")
            import traceback
            logger.error(f"📝 Stack trace: {traceback.format_exc()}")

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

    def _apply_avatar_settings(self, avatar_config: dict):
        """Apply avatar persona settings (window title, tray tooltip, avatar image)."""
        from ..domain.models.avatar_personas import get_avatar, get_default_avatar
        avatar_id = avatar_config.get('selected', 'specter')
        avatar = get_avatar(avatar_id) or get_default_avatar()

        # Update window title
        if self._main_window:
            self._main_window.setWindowTitle(f"{avatar.name} - AI Assistant")

        # Apply avatar scale
        scale = avatar_config.get('scale', 1.0)
        base_size = 120
        new_size = max(72, min(int(base_size * scale), 600))

        # Reload floating avatar image and apply scale
        if self._main_window and hasattr(self._main_window, 'avatar_widget'):
            try:
                self._main_window.setFixedSize(new_size, new_size)
                self._main_window.avatar_widget.setFixedSize(new_size, new_size)
                self._main_window.avatar_widget._load_avatar()
                self._main_window.avatar_widget.update()
            except Exception as e:
                logger.debug(f"Failed to reload avatar image: {e}")

        # Update system tray tooltip (icon stays the same)
        if hasattr(self, '_system_tray') and self._system_tray:
            try:
                self._system_tray.tray_icon.setToolTip(f"{avatar.name} - AI Assistant")
            except Exception:
                pass

        logger.info(f"🎭 Avatar applied: {avatar.name} ({avatar_id}), scale={scale:.0%}")

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