"""
Enhanced REPL widget with conversation management integration.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
    QLabel, QFrame, QMenuBar, QMenu, QMessageBox, QComboBox, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont

from ....presentation.widgets.repl_widget import REPLWidget
from ..integration.conversation_manager import ConversationManager

logger = logging.getLogger("ghostman.conversation_repl")


class ConversationREPLWidget(REPLWidget):
    """
    Enhanced REPL widget with conversation management features.
    
    Extends the existing REPLWidget to add conversation management capabilities
    including conversation switching, history browsing, and export functions.
    """
    
    # Additional signals for conversation management
    conversation_switched = pyqtSignal(str)  # conversation_id
    conversation_created = pyqtSignal(str)   # conversation_id
    export_requested = pyqtSignal(str, str)  # conversation_id, format
    
    def __init__(self, conversation_manager: Optional[ConversationManager] = None, parent=None):
        """Initialize conversation REPL widget."""
        super().__init__(parent)
        
        self.conversation_manager = conversation_manager
        self._current_conversation_id: Optional[str] = None
        self._ai_service = None
        
        # Conversation management UI elements
        self._conversation_toolbar = None
        self._conversation_selector = None
        self._status_label = None
        
        # Initialize conversation management UI
        self._init_conversation_ui()
        
        # Set up conversation manager integration
        if self.conversation_manager:
            self._setup_conversation_integration()
        
        logger.info("ConversationREPLWidget initialized")
    
    def _init_conversation_ui(self):
        """Initialize conversation management UI elements."""
        # Get the main layout
        main_layout = self.layout()
        
        # Insert conversation toolbar at the top (after title bar)
        self._conversation_toolbar = self._create_conversation_toolbar()
        main_layout.insertWidget(2, self._conversation_toolbar)  # After title and separator
        
        # Update the welcome message
        self.clear_output()
        self.append_output("🤖 Ghostman Conversation System", "system")
        self.append_output("Enhanced REPL with conversation management capabilities", "system")
        self.append_output("Type '/help' for conversation commands or 'help' for AI commands", "info")
        self.append_output("-" * 60, "system")
    
    def _create_conversation_toolbar(self) -> QFrame:
        """Create the conversation management toolbar."""
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 50, 50, 0.8);
                border-radius: 4px;
                padding: 5px;
                margin: 5px 0;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
            QComboBox {
                background-color: rgba(70, 70, 70, 0.9);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 3px 8px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QPushButton {
                background-color: rgba(70, 130, 180, 0.8);
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(70, 130, 180, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(50, 100, 150, 1.0);
            }
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(10)
        
        # Current conversation selector
        conv_label = QLabel("Conversation:")
        layout.addWidget(conv_label)
        
        self._conversation_selector = QComboBox()
        self._conversation_selector.setMinimumWidth(200)
        self._conversation_selector.currentTextChanged.connect(self._on_conversation_selected)
        layout.addWidget(self._conversation_selector)
        
        # New conversation button
        new_conv_btn = QPushButton("New")
        new_conv_btn.setToolTip("Start a new conversation")
        new_conv_btn.clicked.connect(self._create_new_conversation)
        layout.addWidget(new_conv_btn)
        
        # Browse conversations button
        browse_btn = QPushButton("📋 Browse")
        browse_btn.setToolTip("Open visual conversation browser")
        browse_btn.clicked.connect(self._browse_conversations)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 152, 0, 0.8);
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 152, 0, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(230, 136, 0, 1.0);
            }
        """)
        layout.addWidget(browse_btn)
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.setToolTip("Export current conversation")
        export_btn.clicked.connect(self._export_current_conversation)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # Status label
        self._status_label = QLabel("No conversation")
        self._status_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(self._status_label)
        
        return toolbar
    
    def _setup_conversation_integration(self):
        """Set up integration with conversation manager."""
        if not self.conversation_manager or not self.conversation_manager.is_initialized():
            return
        
        try:
            # Get the AI service
            self._ai_service = self.conversation_manager.get_ai_service()
            
            if self._ai_service:
                # Enable auto-save for conversations
                self._ai_service.set_auto_save(True)
                self._ai_service.set_auto_generate_titles(True)
                
                logger.info("✅ AI service integration enabled")
            
            # Set up status callbacks
            self.conversation_manager.add_status_callback(self._on_conversation_status)
            
            # Load recent conversations into selector
            self._refresh_conversation_list()
            
        except Exception as e:
            logger.error(f"❌ Failed to set up conversation integration: {e}")
    
    def _on_conversation_status(self, status: str, data: Dict[str, Any]):
        """Handle conversation manager status updates."""
        if status == "conversation_created":
            self._refresh_conversation_list()
            self._update_status_label(f"Created: {data.get('title', 'New conversation')}")
            
        elif status == "conversation_updated":
            self._refresh_conversation_list()
            self._update_status_label(f"Updated: {data.get('title', 'Conversation')}")
            
        elif status == "message_added":
            conv_id = data.get('conversation_id')
            if conv_id == self._current_conversation_id:
                self._update_status_label("Message saved")
    
    def _refresh_conversation_list(self):
        """Refresh the conversation selector with recent conversations."""
        if not self.conversation_manager:
            return
        
        try:
            # Run async operation in thread
            QTimer.singleShot(0, self._async_refresh_conversations)
        except Exception as e:
            logger.error(f"❌ Failed to refresh conversation list: {e}")
    
    def _async_refresh_conversations(self):
        """Asynchronously refresh conversations."""
        class ConversationLoader(QObject):
            conversations_loaded = pyqtSignal(list)
            
            def __init__(self, manager):
                super().__init__()
                self.manager = manager
            
            def load(self):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    conversations = loop.run_until_complete(
                        self.manager.get_recent_conversations(limit=20)
                    )
                    self.conversations_loaded.emit(conversations)
                except Exception as e:
                    logger.error(f"Failed to load conversations: {e}")
                    self.conversations_loaded.emit([])
        
        self._loader_thread = QThread()
        self._loader = ConversationLoader(self.conversation_manager)
        self._loader.moveToThread(self._loader_thread)
        
        self._loader_thread.started.connect(self._loader.load)
        self._loader.conversations_loaded.connect(self._update_conversation_selector)
        self._loader.conversations_loaded.connect(self._loader_thread.quit)
        self._loader.conversations_loaded.connect(self._loader.deleteLater)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        
        self._loader_thread.start()
    
    def _update_conversation_selector(self, conversations):
        """Update the conversation selector with loaded conversations."""
        current_text = self._conversation_selector.currentText()
        
        self._conversation_selector.clear()
        self._conversation_selector.addItem("-- Select Conversation --", None)
        
        for conv in conversations:
            display_text = f"{conv.title} ({conv.get_message_count()} msgs)"
            self._conversation_selector.addItem(display_text, conv.id)
        
        # Try to restore selection
        if current_text:
            index = self._conversation_selector.findText(current_text)
            if index >= 0:
                self._conversation_selector.setCurrentIndex(index)
    
    def _on_conversation_selected(self):
        """Handle conversation selection."""
        current_data = self._conversation_selector.currentData()
        if current_data and current_data != self._current_conversation_id:
            self._load_conversation(current_data)
    
    def _load_conversation(self, conversation_id: str):
        """Load a specific conversation."""
        if not self._ai_service:
            self.append_output("❌ AI service not available", "error")
            return
        
        try:
            # Load conversation in AI service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self._ai_service.load_conversation(conversation_id))
            
            if success:
                self._current_conversation_id = conversation_id
                
                # Clear and reload output
                self.clear_output()
                self.append_output("🔄 Conversation loaded", "system")
                
                # Get conversation info
                conv_info = loop.run_until_complete(self._ai_service.get_current_conversation_info())
                if conv_info:
                    self.append_output(f"📝 {conv_info['title']}", "info")
                    self.append_output(f"📅 Created: {conv_info['created_at'][:19]}", "info")
                    self.append_output(f"💬 Messages: {conv_info['message_count']}", "info")
                    if conv_info.get('tags'):
                        self.append_output(f"🏷️  Tags: {', '.join(conv_info['tags'])}", "info")
                
                self.append_output("-" * 40, "system")
                
                # Load conversation messages into display
                self._display_conversation_messages()
                
                self._update_status_label(f"Loaded: {conversation_id[:8]}...")
                self.conversation_switched.emit(conversation_id)
                
            else:
                self.append_output(f"❌ Failed to load conversation: {conversation_id}", "error")
            
        except Exception as e:
            logger.error(f"❌ Failed to load conversation: {e}")
            self.append_output(f"❌ Error loading conversation: {e}", "error")
    
    def _display_conversation_messages(self):
        """Display conversation messages in the output area."""
        if not self._ai_service:
            return
        
        try:
            # Get conversation context
            context = self._ai_service.conversation
            
            for msg in context.messages:
                if msg.role == 'system':
                    self.append_output(f"🔧 SYSTEM: {msg.content}", "system")
                elif msg.role == 'user':
                    self.append_output(f"👤 YOU: {msg.content}", "input")
                elif msg.role == 'assistant':
                    self.append_output(f"🤖 ASSISTANT: {msg.content}", "response")
                
        except Exception as e:
            logger.error(f"❌ Failed to display conversation messages: {e}")
    
    def _create_new_conversation(self):
        """Create a new conversation."""
        if not self._ai_service:
            self.append_output("❌ AI service not available", "error")
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            conversation_id = loop.run_until_complete(self._ai_service.start_new_conversation())
            
            if conversation_id:
                self._current_conversation_id = conversation_id
                
                # Clear output and show new conversation
                self.clear_output()
                self.append_output("✨ New conversation started", "system")
                self.append_output("Start chatting with the AI assistant!", "info")
                self.append_output("-" * 40, "system")
                
                self._update_status_label(f"New: {conversation_id[:8]}...")
                self.conversation_created.emit(conversation_id)
                
                # Refresh conversation list
                self._refresh_conversation_list()
                
            else:
                self.append_output("❌ Failed to create new conversation", "error")
                
        except Exception as e:
            logger.error(f"❌ Failed to create new conversation: {e}")
            self.append_output(f"❌ Error creating conversation: {e}", "error")
    
    def _browse_conversations(self):
        """Open conversation browser dialog."""
        self.append_output("🔍 Opening conversation browser...", "info")
        
        if not self.conversation_manager:
            self.append_output("❌ Conversation manager not available", "error")
            return
        
        try:
            from .conversation_browser import ConversationBrowserDialog
            
            # Create and show the conversation browser
            browser = ConversationBrowserDialog(self.conversation_manager, self.parent())
            
            # Connect signals
            browser.conversation_loaded.connect(self._on_browser_conversation_loaded)
            browser.conversation_selected.connect(self._on_browser_conversation_selected)
            
            # Show the browser
            browser.show()
            browser.raise_()
            browser.activateWindow()
            
            self.append_output("✅ Conversation browser opened", "info")
            
        except Exception as e:
            logger.error(f"❌ Failed to open conversation browser: {e}")
            self.append_output(f"❌ Error opening conversation browser: {e}", "error")
    
    def _on_browser_conversation_loaded(self, conversation_id: str):
        """Handle conversation loaded from browser."""
        self.append_output(f"📂 Loading conversation from browser: {conversation_id[:8]}...", "info")
        self._load_conversation(conversation_id)
    
    def _on_browser_conversation_selected(self, conversation_id: str):
        """Handle conversation selected in browser."""
        self.append_output(f"👆 Selected conversation: {conversation_id[:8]}...", "info")
    
    def _export_current_conversation(self):
        """Export the current conversation."""
        if not self._current_conversation_id:
            self.append_output("❌ No active conversation to export", "warning")
            return
        
        self.append_output("📤 Exporting current conversation...", "info")
        # TODO: Implement export dialog
        # For now, emit signal
        self.export_requested.emit(self._current_conversation_id, "json")
    
    def _update_status_label(self, text: str):
        """Update the status label."""
        if self._status_label:
            self._status_label.setText(text)
            # Auto-clear status after 5 seconds
            QTimer.singleShot(5000, lambda: self._status_label.setText("Ready"))
    
    # --- Override parent methods to add conversation support ---
    
    def _process_command(self, command: str):
        """Process command with conversation management support."""
        command_lower = command.lower()
        
        # Handle conversation management commands
        if command_lower.startswith('/'):
            self._process_conversation_command(command[1:])
        else:
            # Call parent implementation for regular commands
            super()._process_command(command)
    
    def _process_conversation_command(self, command: str):
        """Process conversation-specific commands."""
        parts = command.lower().split()
        cmd = parts[0] if parts else ""
        
        if cmd == "help":
            self._show_conversation_help()
        elif cmd == "new":
            self._create_new_conversation()
        elif cmd == "list":
            self._list_recent_conversations()
        elif cmd == "search" and len(parts) > 1:
            search_term = " ".join(parts[1:])
            self._search_conversations(search_term)
        elif cmd == "export":
            format_type = parts[1] if len(parts) > 1 else "json"
            self._export_current_conversation_format(format_type)
        elif cmd == "info":
            self._show_current_conversation_info()
        elif cmd == "tags" and len(parts) > 1:
            tags = set(parts[1:])
            self._add_tags_to_current_conversation(tags)
        else:
            self.append_output(f"Unknown conversation command: /{command}", "warning")
            self.append_output("Type '/help' for available commands", "info")
    
    def _show_conversation_help(self):
        """Show conversation management help."""
        self.append_output("Conversation Management Commands:", "info")
        self.append_output("  /help        - Show this help", "info")
        self.append_output("  /new         - Start a new conversation", "info")
        self.append_output("  /list        - List recent conversations", "info")
        self.append_output("  /search <term> - Search conversations", "info")
        self.append_output("  /export [format] - Export current conversation", "info")
        self.append_output("  /info        - Show current conversation info", "info")
        self.append_output("  /tags <tag1> <tag2> - Add tags to current conversation", "info")
        self.append_output("", "normal")
        self.append_output("Use the toolbar above for visual conversation management.", "info")
    
    def _list_recent_conversations(self):
        """List recent conversations."""
        if not self.conversation_manager:
            self.append_output("❌ Conversation manager not available", "error")
            return
        
        try:
            class ConversationLister(QObject):
                conversations_listed = pyqtSignal(list)
                
                def __init__(self, manager):
                    super().__init__()
                    self.manager = manager
                
                def list_conversations(self):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        conversations = loop.run_until_complete(
                            self.manager.get_recent_conversations(limit=10)
                        )
                        self.conversations_listed.emit(conversations)
                    except Exception as e:
                        logger.error(f"Failed to list conversations: {e}")
                        self.conversations_listed.emit([])
            
            def display_conversations(conversations):
                if conversations:
                    self.append_output("Recent Conversations:", "info")
                    for i, conv in enumerate(conversations, 1):
                        status_icon = {"active": "🟢", "pinned": "📌", "archived": "📦"}.get(conv.status.value, "⚫")
                        self.append_output(
                            f"  {i}. {status_icon} {conv.title} ({conv.get_message_count()} msgs) - {conv.updated_at.strftime('%Y-%m-%d %H:%M')}", 
                            "normal"
                        )
                else:
                    self.append_output("No conversations found", "warning")
            
            self._lister_thread = QThread()
            self._lister = ConversationLister(self.conversation_manager)
            self._lister.moveToThread(self._lister_thread)
            
            self._lister_thread.started.connect(self._lister.list_conversations)
            self._lister.conversations_listed.connect(display_conversations)
            self._lister.conversations_listed.connect(self._lister_thread.quit)
            self._lister.conversations_listed.connect(self._lister.deleteLater)
            self._lister_thread.finished.connect(self._lister_thread.deleteLater)
            
            self._lister_thread.start()
            
        except Exception as e:
            logger.error(f"❌ Failed to list conversations: {e}")
            self.append_output(f"❌ Error listing conversations: {e}", "error")
    
    def _search_conversations(self, search_term: str):
        """Search conversations."""
        self.append_output(f"🔍 Searching for: {search_term}", "info")
        # TODO: Implement search functionality
        self.append_output("Search functionality will be implemented in the full system.", "warning")
    
    def _export_current_conversation_format(self, format_type: str):
        """Export current conversation in specific format."""
        if not self._current_conversation_id:
            self.append_output("❌ No active conversation to export", "warning")
            return
        
        self.append_output(f"📤 Exporting to {format_type.upper()} format...", "info")
        self.export_requested.emit(self._current_conversation_id, format_type)
    
    def _show_current_conversation_info(self):
        """Show information about current conversation."""
        if not self._ai_service or not self._current_conversation_id:
            self.append_output("❌ No active conversation", "warning")
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            conv_info = loop.run_until_complete(self._ai_service.get_current_conversation_info())
            
            if conv_info:
                self.append_output("Current Conversation Info:", "info")
                self.append_output(f"  ID: {conv_info['id']}", "normal")
                self.append_output(f"  Title: {conv_info['title']}", "normal")
                self.append_output(f"  Status: {conv_info['status']}", "normal")
                self.append_output(f"  Created: {conv_info['created_at'][:19]}", "normal")
                self.append_output(f"  Updated: {conv_info['updated_at'][:19]}", "normal")
                self.append_output(f"  Messages: {conv_info['message_count']}", "normal")
                if conv_info.get('tags'):
                    self.append_output(f"  Tags: {', '.join(conv_info['tags'])}", "normal")
                if conv_info.get('category'):
                    self.append_output(f"  Category: {conv_info['category']}", "normal")
            else:
                self.append_output("❌ Could not retrieve conversation info", "error")
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversation info: {e}")
            self.append_output(f"❌ Error getting conversation info: {e}", "error")
    
    def _add_tags_to_current_conversation(self, tags: set):
        """Add tags to the current conversation."""
        if not self.conversation_manager or not self._current_conversation_id:
            self.append_output("❌ No active conversation", "warning")
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.conversation_manager.add_tags_to_conversation(self._current_conversation_id, tags)
            )
            
            if success:
                self.append_output(f"✅ Added tags: {', '.join(tags)}", "info")
            else:
                self.append_output("❌ Failed to add tags", "error")
                
        except Exception as e:
            logger.error(f"❌ Failed to add tags: {e}")
            self.append_output(f"❌ Error adding tags: {e}", "error")
    
    # --- Override AI message handling ---
    
    def _send_to_ai(self, message: str):
        """Send message to AI with conversation management."""
        if not self._ai_service:
            # Fall back to parent implementation
            super()._send_to_ai(message)
            return
        
        self.append_output("Processing with AI...", "system")
        
        # Disable input while processing
        self.command_input.setEnabled(False)
        
        # Use conversation-aware AI service
        class ConversationAIWorker(QObject):
            response_received = pyqtSignal(str, bool)  # response, success
            
            def __init__(self, ai_service, message):
                super().__init__()
                self.ai_service = ai_service
                self.message = message
            
            def run(self):
                try:
                    result = self.ai_service.send_message(self.message)
                    
                    if result['success']:
                        self.response_received.emit(result['response'], True)
                    else:
                        error_msg = f"❌ AI Error: {result.get('error', 'Unknown error')}"
                        self.response_received.emit(error_msg, False)
                        
                except Exception as e:
                    logger.error(f"AI worker error: {e}")
                    self.response_received.emit(f"❌ Error: {str(e)}", False)
        
        # Create and start worker thread
        self.ai_thread = QThread()
        self.ai_worker = ConversationAIWorker(self._ai_service, message)
        self.ai_worker.moveToThread(self.ai_thread)
        
        # Connect signals
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.response_received.connect(self._on_ai_response)
        self.ai_worker.response_received.connect(self.ai_thread.quit)
        self.ai_worker.response_received.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        
        # Start processing
        self.ai_thread.start()
    
    # --- Utility Methods ---
    
    def set_conversation_manager(self, conversation_manager: ConversationManager):
        """Set the conversation manager."""
        self.conversation_manager = conversation_manager
        self._setup_conversation_integration()
    
    def get_current_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return self._current_conversation_id