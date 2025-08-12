"""
Main Window for Ghostman Avatar Mode.

Provides the avatar interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCloseEvent

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
        
        self._init_ui()
        self._setup_window()
        
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
        """Position the window near the lower right corner."""
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            
            # Position near lower right with some padding
            padding = 50
            x = screen_geometry.right() - window_geometry.width() - padding
            y = screen_geometry.bottom() - window_geometry.height() - padding
            
            logger.debug(f'Positioning window: screen={screen_geometry}, window_geometry={window_geometry}')
            logger.debug(f'Final position: ({x}, {y})')
            self.move(x, y)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Hide floating REPL if it's visible
        if self.floating_repl and self.floating_repl.isVisible():
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to window close")
        
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
                self.conversation_browser = SimpleConversationBrowser(parent=self, conversation_manager=conversation_manager)
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