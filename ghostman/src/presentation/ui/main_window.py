"""
Main Window for Ghostman Avatar Mode.

Provides the avatar interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QCloseEvent, QMouseEvent, QShortcut, QKeySequence

# Import window state management
from ...application.window_state import save_window_state, load_window_state
from ...infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.main_window")


class MainWindow(QMainWindow):
    """
    Main application window for Avatar mode.
    
    Contains only the avatar widget - REPL is now a separate floating window.
    """
    
    # Signals
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    conversations_requested = pyqtSignal()
    
    def __init__(self, app_coordinator):
        super().__init__()
        self.app_coordinator = app_coordinator
        self.floating_repl = None
        self.conversation_browser = None  # Simple conversation browser
        # Attach state (REPL snapped to avatar)
        self._repl_attached: bool = bool(settings.get('interface.repl_attached', False))
        off = settings.get('interface.repl_attach_offset', None)
        if isinstance(off, dict) and 'x' in off and 'y' in off:
            self._repl_attach_offset = QPoint(int(off['x']), int(off['y']))
        else:
            self._repl_attach_offset = QPoint(140, 0)  # sensible default; will be recalculated when attaching
        
        self._init_ui()
        self._setup_window()
        self._setup_keyboard_shortcuts()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface with only the avatar widget."""
        # Import widgets
        from ..widgets.avatar_widget import AvatarWidget
        from ..widgets.floating_repl import FloatingREPLWindow
        
        # Create the avatar widget as central widget
        self.avatar_widget = AvatarWidget()
        self.avatar_widget.minimize_requested.connect(self.minimize_requested.emit)
        self.avatar_widget.avatar_clicked.connect(self._toggle_repl)
        self.avatar_widget.settings_requested.connect(self.settings_requested.emit)
        self.avatar_widget.conversations_requested.connect(self._show_conversations)
        self.setCentralWidget(self.avatar_widget)
        
        # Create floating REPL window (initially hidden)
        self.floating_repl = FloatingREPLWindow()
        self.floating_repl.closed.connect(self._on_repl_closed)
        self.floating_repl.command_entered.connect(self._on_command_entered)
        # Connect REPL widget signals through floating REPL
        self.floating_repl.repl_widget.settings_requested.connect(self.settings_requested.emit)
        self.floating_repl.repl_widget.browse_requested.connect(self._show_conversations)
        # Wire attach toggle from REPL title bar
        if hasattr(self.floating_repl.repl_widget, 'attach_toggle_requested'):
            self.floating_repl.repl_widget.attach_toggle_requested.connect(self._on_attach_toggle)
            # Sync initial visual state
            if hasattr(self.floating_repl.repl_widget, 'set_attach_state'):
                self.floating_repl.repl_widget.set_attach_state(self._repl_attached)
        # Update offset when user manually moves REPL while attached
        if hasattr(self.floating_repl, 'window_moved'):
            self.floating_repl.window_moved.connect(self._on_repl_moved)
        
        # Set window background
        self._set_window_style()
        
        logger.debug("UI components initialized - avatar only, REPL is floating")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Spector - AI Assistant")
        self.setMinimumSize(90, 90)
        self.resize(120, 120)  # 40% smaller (200 * 0.6 = 120)
        
        # Make window frameless for a cleaner look
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Center the window
        self._center_window()
        
        logger.debug("Window properties configured")
    
    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts for the main window."""
        # Ctrl+M to minimize to taskbar/tray
        minimize_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        minimize_shortcut.activated.connect(self._minimize_to_taskbar)
        
        logger.debug("MainWindow keyboard shortcuts configured: Ctrl+M to minimize")
    
    def _minimize_to_taskbar(self):
        """Minimize the entire application to taskbar/tray."""
        logger.info("Minimize shortcut activated (Ctrl+M)")
        # Emit minimize signal which will be handled by the app coordinator
        self.minimize_requested.emit()
    
    def _set_window_style(self):
        """Set the window style and background."""
        # Set a gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2
                );
                border-radius: 20px;
            }
        """)
    
    def _center_window(self):
        """Position the window using saved position or default to bottom right corner."""
        try:
            # Load saved window state
            window_state = load_window_state('avatar')
            saved_position = window_state['position']
            saved_size = window_state['size']
            
            # Apply saved size
            self.resize(saved_size['width'], saved_size['height'])
            
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                
                # If no saved position, use bottom-right default
                if saved_position is None:
                    logger.info("No saved avatar position - using bottom-right default")
                    window_geometry = self.frameGeometry()
                    padding = 50
                    x = screen_geometry.right() - window_geometry.width() - padding
                    y = screen_geometry.bottom() - window_geometry.height() - padding
                else:
                    # Use saved position if valid
                    x, y = saved_position['x'], saved_position['y']
                    
                    # Validate position is on screen
                    if (x < screen_geometry.left() or x > screen_geometry.right() - 100 or
                        y < screen_geometry.top() or y > screen_geometry.bottom() - 100):
                        
                        logger.info("Saved avatar position is off-screen, using bottom-right default")
                        # Fall back to bottom-right default
                        window_geometry = self.frameGeometry()
                        padding = 50
                        x = screen_geometry.right() - window_geometry.width() - padding
                        y = screen_geometry.bottom() - window_geometry.height() - padding
                
                logger.debug(f'Positioning avatar window at: ({x}, {y}), size: {saved_size}')
                self.move(x, y)
                
        except Exception as e:
            logger.error(f"Failed to load avatar window position, using bottom-right default: {e}")
            # Fall back to bottom-right positioning
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.frameGeometry()
                
                padding = 50
                x = screen_geometry.right() - window_geometry.width() - padding
                y = screen_geometry.bottom() - window_geometry.height() - padding
                
                logger.debug(f'Using bottom-right default positioning: ({x}, {y})')
                self.move(x, y)
    
    def save_current_window_state(self):
        """Save current window position and size."""
        try:
            pos = self.pos()
            size = self.size()
            save_window_state('avatar', pos.x(), pos.y(), size.width(), size.height())
        except Exception as e:
            logger.error(f"Failed to save avatar window state: {e}")
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Save window state when mouse is released (after move/resize)."""
        super().mouseReleaseEvent(event)
        # Save state after any mouse operation that could have moved/resized the window
        self.save_current_window_state()
    
    def resizeEvent(self, event):
        """Save window state when resized."""
        super().resizeEvent(event)
        # Save state after resize
        self.save_current_window_state()
    
    def moveEvent(self, event):
        """Save window state when moved."""
        super().moveEvent(event)
        # If REPL is attached, move it along with the avatar using stored offset
        try:
            if self._repl_attached and self.floating_repl and self.floating_repl.isVisible():
                self._move_attached_repl()
        except Exception as e:
            logger.debug(f"Failed to move attached REPL: {e}")
        # Save state after move
        self.save_current_window_state()
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Hide floating REPL if it's visible
        if self.floating_repl and self.floating_repl.isVisible():
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to window close")
        
        # Save current conversation state before closing
        try:
            if (hasattr(self.app_coordinator, '_cleanup_on_shutdown') and 
                hasattr(self, 'floating_repl') and 
                self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget')):
                
                repl_widget = self.floating_repl.repl_widget
                if hasattr(repl_widget, '_has_unsaved_messages') and repl_widget._has_unsaved_messages():
                    logger.info("💾 Saving unsaved messages before window close...")
                    # Let app coordinator handle the cleanup
                    
        except Exception as e:
            logger.error(f"Failed to check/save unsaved messages: {e}")
        
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
        # Hide floating REPL if it's visible
        if self.floating_repl and self.floating_repl.isVisible():
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to minimize to tray")
        
        self.hide()
        self.minimize_requested.emit()
        logger.debug("Window minimized to tray")
    
    def _toggle_repl(self):
        """Toggle floating REPL visibility."""
        if self.floating_repl.isVisible():
            self._hide_repl()
        else:
            self._show_repl()
    
    def _show_repl(self):
        """Show the floating REPL positioned relative to avatar - avatar never moves."""
        # Get current avatar position and screen info
        avatar_pos = self.pos()
        avatar_size = (self.width(), self.height())
        screen = self.screen()
        
        logger.debug(f'Showing floating REPL: avatar at {avatar_pos}, size {avatar_size}')
        
        if screen:
            screen_geometry = screen.availableGeometry()
            
            if self._repl_attached:
                # Move REPL using current offset
                self._ensure_attach_offset_default()
                self.floating_repl.move_attached(avatar_pos, self._repl_attach_offset, screen_geometry)
            else:
                # Position REPL relative to avatar (avatar position unchanged)
                self.floating_repl.position_relative_to_avatar(
                    avatar_pos, avatar_size, screen_geometry
                )
            
            # Show and activate the REPL
            self.floating_repl.show_and_activate()
            
            logger.debug(f'Floating REPL shown, avatar remains at: {self.pos()}')
    
    def _hide_repl(self):
        """Hide the floating REPL - avatar position completely unaffected."""
        logger.debug(f'Hiding floating REPL, avatar at: {self.pos()}')
        self.floating_repl.hide()
        logger.debug(f'Floating REPL hidden, avatar still at: {self.pos()}')
    
    def _on_repl_closed(self):
        """Handle floating REPL window being closed."""
        logger.debug(f'Floating REPL closed by user, avatar remains at: {self.pos()}')

    def _on_attach_toggle(self, attached: bool):
        """Handle attach toggle from REPL title bar."""
        self._repl_attached = bool(attached)
        try:
            # Persist state
            settings.set('interface.repl_attached', self._repl_attached)
            # Compute and persist offset when attaching
            if self._repl_attached and self.floating_repl:
                # If REPL not visible yet, compute a sensible default to the right of avatar
                if not self.floating_repl.isVisible():
                    self._ensure_attach_offset_default()
                else:
                    self._repl_attach_offset = self.floating_repl.pos() - self.pos()
                settings.set('interface.repl_attach_offset', {
                    'x': int(self._repl_attach_offset.x()),
                    'y': int(self._repl_attach_offset.y()),
                })
                # If visible, snap immediately
                if self.floating_repl.isVisible():
                    screen = self.screen()
                    if screen:
                        self.floating_repl.move_attached(self.pos(), self._repl_attach_offset, screen.availableGeometry())
            # Update button visual if needed
            if hasattr(self.floating_repl.repl_widget, 'set_attach_state'):
                self.floating_repl.repl_widget.set_attach_state(self._repl_attached)
        except Exception as e:
            logger.error(f"Failed to handle attach toggle: {e}")

    def _ensure_attach_offset_default(self):
        """Ensure we have a reasonable default offset when attaching."""
        # Default: place REPL to the right of avatar with 10px gap and current REPL size if known
        try:
            gap = 10
            default_x = self.width() + gap
            default_y = 0
            self._repl_attach_offset = QPoint(default_x, default_y)
        except Exception:
            self._repl_attach_offset = QPoint(140, 0)

    def _move_attached_repl(self):
        """Move REPL based on avatar position and stored offset, clamped to screen."""
        screen = self.screen()
        if not screen or not self.floating_repl:
            return
        geom = screen.availableGeometry()
        self.floating_repl.move_attached(self.pos(), self._repl_attach_offset, geom)

    def _on_repl_moved(self, repl_pos: QPoint):
        """When attached and user drags REPL, recompute offset and persist."""
        try:
            if self._repl_attached:
                self._repl_attach_offset = repl_pos - self.pos()
                settings.set('interface.repl_attach_offset', {
                    'x': int(self._repl_attach_offset.x()),
                    'y': int(self._repl_attach_offset.y()),
                })
        except Exception as e:
            logger.debug(f"Failed to update attach offset on move: {e}")
    
    def _on_command_entered(self, command: str):
        """Handle command from REPL."""
        logger.info(f"REPL command: {command}")
        # This would be connected to AI service
    
    def _show_conversations(self):
        """Show the simple conversation management window."""
        try:
            from ..dialogs.simple_conversation_browser import SimpleConversationBrowser
            from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
            
            # Get conversation manager from REPL widget if available (to share same instance)
            conversation_manager = None
            current_conversation_id = None
            
            if (self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget') and
                self.floating_repl.repl_widget):
                # Get conversation manager from REPL widget
                if hasattr(self.floating_repl.repl_widget, 'conversation_manager'):
                    conversation_manager = self.floating_repl.repl_widget.conversation_manager
                    logger.info("Using shared conversation manager from REPL widget")
                # Get current conversation ID
                current_conversation_id = self.floating_repl.repl_widget.get_current_conversation_id()
            
            # If no conversation manager from REPL, create one
            if not conversation_manager:
                logger.info("Creating new conversation manager for browser")
                if not hasattr(self, '_conversation_manager') or not self._conversation_manager:
                    self._conversation_manager = ConversationManager()
                    if not self._conversation_manager.initialize():
                        logger.error("Failed to initialize conversation manager")
                        from PyQt6.QtWidgets import QMessageBox
                        
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Conversations Unavailable")
                        msg_box.setText("Conversation management system could not be initialized.")
                        msg_box.setIcon(QMessageBox.Icon.Warning)
                        msg_box.setStyleSheet("""
                            QMessageBox {
                                background-color: #2b2b2b;
                                color: #ffffff;
                                border: 1px solid #555555;
                            }
                            QMessageBox QLabel {
                                color: #ffffff;
                            }
                            QMessageBox QPushButton {
                                background-color: #ff9800;
                                color: white;
                                border: none;
                                padding: 8px 16px;
                                border-radius: 4px;
                                min-width: 80px;
                            }
                            QMessageBox QPushButton:hover {
                                background-color: #f57c00;
                            }
                        """)
                        msg_box.exec()
                        return
                conversation_manager = self._conversation_manager
            
            # Create or show conversation browser with shared conversation manager
            if not self.conversation_browser:
                # Get theme manager if available
                try:
                    from ...ui.themes.theme_manager import get_theme_manager
                    theme_manager = get_theme_manager()
                except ImportError:
                    theme_manager = None
                    
                self.conversation_browser = SimpleConversationBrowser(
                    parent=self, 
                    conversation_manager=conversation_manager,
                    theme_manager=theme_manager
                )
                self.conversation_browser.conversation_restore_requested.connect(
                    self._restore_conversation_to_repl
                )
            else:
                # Update current conversation and refresh the list
                self.conversation_browser.set_current_conversation(current_conversation_id)
                # Reload conversations to show any new ones
                self.conversation_browser._load_conversations()
            
            # Show the browser
            self.conversation_browser.show()
            self.conversation_browser.raise_()
            self.conversation_browser.activateWindow()
            
            logger.info("Simple conversation browser opened")
            
        except ImportError as e:
            logger.error(f"Conversation management not available: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Feature Unavailable")
            msg_box.setText("Conversation management is not yet available.")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                }
                QMessageBox QPushButton {
                    background-color: #ff9800;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"Failed to show conversations: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open conversations:\n{str(e)}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                }
                QMessageBox QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            msg_box.exec()
    
    def _restore_conversation_to_repl(self, conversation_id: str):
        """Restore a conversation to the REPL."""
        logger.info(f"Restoring conversation to REPL: {conversation_id}")
        
        try:
            # Show REPL if not visible
            if not self.floating_repl.isVisible():
                self._show_repl()
            
            # Load conversation in REPL widget
            if (self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget') and 
                self.floating_repl.repl_widget):
                
                # Restore the conversation in the REPL widget
                if hasattr(self.floating_repl.repl_widget, 'restore_conversation'):
                    self.floating_repl.repl_widget.restore_conversation(conversation_id)
                    logger.info(f"✅ Conversation {conversation_id} restoration initiated in REPL")
                else:
                    logger.error("❌ REPL widget doesn't have restore_conversation method")
                
                # Update conversation browser to reflect the change
                if self.conversation_browser:
                    self.conversation_browser.set_current_conversation(conversation_id)
                    # The browser will handle its own status update and refresh
                
                # Show success message with conversation details
                from PyQt6.QtWidgets import QMessageBox
                
                # Get conversation details for better message
                try:
                    conversation_manager = getattr(self.floating_repl.repl_widget, 'conversation_manager', None)
                    if conversation_manager:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            conversation = loop.run_until_complete(
                                conversation_manager.get_conversation(conversation_id, include_messages=False)
                            )
                            if conversation:
                                title = conversation.title or "Untitled Conversation"
                                message = f"Conversation '{title}' has been loaded into the REPL."
                            else:
                                message = "Conversation has been loaded into the REPL."
                        finally:
                            loop.close()
                    else:
                        message = "Conversation has been loaded into the REPL."
                except Exception as e:
                    logger.warning(f"Could not get conversation details for message: {e}")
                    message = "Conversation has been loaded into the REPL."
                
                # Create themed message box
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Conversation Restored")
                msg_box.setText(message)
                msg_box.setIcon(QMessageBox.Icon.Information)
                
                # Apply dark theme styling
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #2b2b2b;
                        color: #ffffff;
                        border: 1px solid #555555;
                    }
                    QMessageBox QLabel {
                        color: #ffffff;
                    }
                    QMessageBox QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        min-width: 80px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #45a049;
                    }
                    QMessageBox QPushButton:pressed {
                        background-color: #3e8e41;
                    }
                """)
                
                msg_box.exec()
            else:
                logger.error("REPL widget not available for conversation restore")
                
        except Exception as e:
            logger.error(f"Failed to restore conversation: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            # Create themed error message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Restore Failed")
            msg_box.setText(f"Failed to restore conversation:\n{str(e)}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            
            # Apply dark theme styling
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                }
                QMessageBox QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #da190b;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
            
            msg_box.exec()