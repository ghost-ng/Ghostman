"""
REPL Widget for Ghostman.

Provides a Read-Eval-Print-Loop interface for interacting with the AI.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QLabel, QFrame, QComboBox,
    QToolButton, QMenu, QProgressBar, QListWidget,
    QListWidgetItem, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QSize, pyqtSlot
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QColor, QPalette, QIcon, QPixmap, QAction

# Settings import (percent-based opacity)
try:
    from ...infrastructure.storage.settings_manager import settings as _global_settings
except Exception:  # pragma: no cover
    _global_settings = None

# Conversation management imports
try:
    from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
    from ...infrastructure.conversation_management.models.conversation import Conversation, Message
    from ...infrastructure.conversation_management.models.enums import ConversationStatus, MessageRole
except Exception:  # pragma: no cover
    ConversationManager = None
    Conversation = None
    Message = None
    ConversationStatus = None
    MessageRole = None

logger = logging.getLogger("ghostman.repl_widget")


class ConversationCard(QWidget):
    """
    Visual card widget for displaying conversation metadata in dropdown.
    """
    def __init__(self, conversation: 'Conversation', parent=None):
        super().__init__(parent)
        self.conversation = conversation
        self._init_ui()
    
    def _init_ui(self):
        """Initialize conversation card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Title and status row
        title_row = QHBoxLayout()
        
        # Status indicator
        status_label = QLabel(self._get_status_icon())
        status_label.setToolTip(f"Status: {self.conversation.status.value.title()}")
        title_row.addWidget(status_label)
        
        # Title
        title_label = QLabel(self.conversation.title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)
        
        # Summary indicator
        if self.conversation.summary:
            summary_label = QLabel("💡")
            summary_label.setToolTip("Has AI summary")
            title_row.addWidget(summary_label)
        
        layout.addLayout(title_row)
        
        # Metadata row
        meta_row = QHBoxLayout()
        
        # Message count
        msg_count = QLabel(f"📝 {len(self.conversation.messages)} msgs")
        msg_count.setStyleSheet("color: #888; font-size: 9px;")
        meta_row.addWidget(msg_count)
        
        # Last updated
        time_diff = datetime.now() - self.conversation.updated_at
        if time_diff.days > 0:
            time_text = f"{time_diff.days}d ago"
        elif time_diff.seconds > 3600:
            time_text = f"{time_diff.seconds // 3600}h ago"
        else:
            time_text = f"{time_diff.seconds // 60}m ago"
        
        time_label = QLabel(f"🕒 {time_text}")
        time_label.setStyleSheet("color: #888; font-size: 9px;")
        meta_row.addWidget(time_label)
        
        meta_row.addStretch()
        layout.addLayout(meta_row)
        
        # Tags if any
        if self.conversation.metadata.tags:
            tags_text = " ".join([f"#{tag}" for tag in list(self.conversation.metadata.tags)[:3]])
            if len(self.conversation.metadata.tags) > 3:
                tags_text += "..."
            tags_label = QLabel(tags_text)
            tags_label.setStyleSheet("color: #666; font-size: 8px; font-style: italic;")
            layout.addWidget(tags_label)
    
    def _get_status_icon(self) -> str:
        """Get status icon based on conversation status."""
        status_icons = {
            ConversationStatus.ACTIVE: "🔥",
            ConversationStatus.PINNED: "⭐", 
            ConversationStatus.ARCHIVED: "📦",
            ConversationStatus.DELETED: "🗑️"
        }
        return status_icons.get(self.conversation.status, "💬")


class IdleDetector(QObject):
    """
    Detects user inactivity for background summarization.
    """
    idle_detected = pyqtSignal(str)  # conversation_id
    
    def __init__(self, idle_threshold_minutes: int = 5):
        super().__init__()
        self.idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self.last_activity = datetime.now()
        self.current_conversation_id: Optional[str] = None
        
        # Timer to check for idle state
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_idle_state)
        self.check_timer.start(60000)  # Check every minute
    
    def reset_activity(self, conversation_id: Optional[str] = None):
        """Reset activity timer."""
        self.last_activity = datetime.now()
        if conversation_id:
            self.current_conversation_id = conversation_id
    
    def _check_idle_state(self):
        """Check if user has been idle."""
        if not self.current_conversation_id:
            return
            
        time_since_activity = datetime.now() - self.last_activity
        if time_since_activity >= self.idle_threshold:
            self.idle_detected.emit(self.current_conversation_id)
            self.current_conversation_id = None  # Prevent repeated signals


class REPLWidget(QWidget):
    """
    Enhanced REPL interface with visual conversation management.
    
    Features:
    - Visual conversation management toolbar
    - Conversation selector dropdown with rich cards
    - Status indicators and action buttons
    - Message type icons
    - Background AI summarization
    - Command input with history
    - Scrollable output display
    """
    
    # Signals
    command_entered = pyqtSignal(str)
    minimize_requested = pyqtSignal()
    conversation_changed = pyqtSignal(str)  # conversation_id
    export_requested = pyqtSignal(str)  # conversation_id
    browse_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_history = []
        self.history_index = -1
        self.current_input = ""
        
        # Panel (frame) opacity (only background, not text/content). 0.0 - 1.0
        # Initialize with default 90% opacity
        self._panel_opacity = 0.90
        
        # Conversation management
        self.conversation_manager: Optional[ConversationManager] = None
        self.current_conversation: Optional[Conversation] = None
        self.conversations_list: List[Conversation] = []
        
        # Idle detection for background summarization
        self.idle_detector = IdleDetector(idle_threshold_minutes=5)
        self.idle_detector.idle_detected.connect(self._on_idle_detected)
        
        # Background summarization state
        self.summarization_queue: List[str] = []  # conversation IDs
        self.is_summarizing = False
        
        # Load from settings if available
        self._load_opacity_from_settings()
        
        # Assign object name so selective stylesheet rules don't leak globally
        self.setObjectName("repl-root")

        self._init_ui()
        self._apply_styles()
        self._init_conversation_manager()
        
        # Load conversations after UI is fully initialized
        QTimer.singleShot(100, self._load_conversations_deferred)
        
        logger.info("Enhanced REPLWidget initialized with conversation management")
    
    def _init_conversation_manager(self):
        """Initialize conversation management system."""
        if not ConversationManager:
            logger.warning("Conversation management not available - running in basic mode")
            return
        
        try:
            self.conversation_manager = ConversationManager()
            if self.conversation_manager.initialize():
                logger.info("✅ Conversation manager initialized successfully")
            else:
                logger.error("❌ Failed to initialize conversation manager")
                self.conversation_manager = None
        except Exception as e:
            logger.error(f"❌ Conversation manager initialization failed: {e}")
            self.conversation_manager = None
    
    def _load_conversations_deferred(self):
        """Load conversations after UI is fully initialized."""
        if not self.conversation_manager:
            logger.debug("No conversation manager available for deferred loading")
            return
        
        try:
            logger.debug("Starting deferred conversation loading...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.debug("Event loop is running, creating task for deferred loading...")
                asyncio.create_task(self._load_conversations())
            else:
                logger.debug("Event loop not running, using run_until_complete for deferred loading...")
                loop.run_until_complete(self._load_conversations())
            logger.debug("Deferred conversation loading initiated successfully")
        except Exception as e:
            logger.error(f"❌ Failed deferred conversation loading: {e}", exc_info=True)
            # Ensure state is valid
            self.conversations_list = []
            self.current_conversation = None
    
    async def _load_conversations(self):
        """Load recent conversations into selector."""
        if not self.conversation_manager:
            logger.warning("No conversation manager available for loading conversations")
            return
        
        try:
            logger.debug("Loading conversations from conversation manager...")
            # Get recent active conversations
            conversations = await self.conversation_manager.get_recent_conversations(limit=20)
            logger.debug(f"Loaded {len(conversations)} conversations")
            self.conversations_list = conversations
            
            # Set current conversation to most recent
            if conversations:
                self.current_conversation = conversations[0]
                logger.debug(f"Set current conversation to most recent: {conversations[0].title}")
            else:
                self.current_conversation = None
                logger.debug("No conversations found - no current conversation set")
            
            logger.info(f"📋 Loaded {len(conversations)} conversations")
            
        except Exception as e:
            logger.error(f"❌ Failed to load conversations: {e}", exc_info=True)
            # Ensure state is valid even if conversation loading fails
            self.conversations_list = []
            self.current_conversation = None
    
    def _get_status_icon(self, conversation: Optional[Conversation]) -> str:
        """Get status icon for conversation."""
        if not conversation:
            return "🆕"
        
        if not ConversationStatus:
            return "💬"
        
        status_icons = {
            ConversationStatus.ACTIVE: "🔥",
            ConversationStatus.PINNED: "⭐", 
            ConversationStatus.ARCHIVED: "📦",
            ConversationStatus.DELETED: "🗑️"
        }
        return status_icons.get(conversation.status, "💬")
    
    def _update_status_label(self, conversation: Optional[Conversation]):
        """Update status label based on conversation."""
        if not conversation:
            self.status_label.setText("🆕 New")
            self.status_label.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 10px;")
            return
        
        status_text = conversation.status.value.title()
        icon = self._get_status_icon(conversation)
        self.status_label.setText(f"{icon} {status_text}")
        
        # Color coding based on status
        colors = {
            "Active": "#4CAF50",
            "Pinned": "#FFD700", 
            "Archived": "#888888",
            "Deleted": "#FF5555"
        }
        color = colors.get(status_text, "#4CAF50")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
        
        # Show summary indicator if available
        if conversation.summary:
            tooltip = f"Status: {status_text}\nSummary available: {conversation.summary.summary[:100]}..."
        else:
            tooltip = f"Status: {status_text}"
        
        self.status_label.setToolTip(tooltip)
    
    def _init_title_bar(self, parent_layout):
        """Initialize enhanced title bar with conversation dropdown."""
        title_layout = QHBoxLayout()
        
        # Conversation selector dropdown
        self.conversation_selector = QComboBox()
        self.conversation_selector.setMinimumWidth(200)
        self.conversation_selector.currentTextChanged.connect(self._on_conversation_selected)
        self.conversation_selector.setToolTip("Select active conversation")
        self._style_conversation_selector()
        title_layout.addWidget(self.conversation_selector)
        
        title_layout.addStretch()
        
        # Status indicators
        self.status_label = QLabel("🔥 Active")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 10px;")
        self.status_label.setToolTip("Conversation status")
        title_layout.addWidget(self.status_label)
        
        # Minimize button
        minimize_btn = QPushButton("_")
        minimize_btn.setMaximumSize(20, 20)
        minimize_btn.clicked.connect(self.minimize_requested.emit)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        title_layout.addWidget(minimize_btn)
        
        parent_layout.addLayout(title_layout)
    
    def _init_conversation_toolbar(self, parent_layout):
        """Initialize conversation management toolbar."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # Browse conversations button
        browse_btn = QToolButton()
        browse_btn.setText("📋")
        browse_btn.setToolTip("Browse conversations")
        browse_btn.clicked.connect(self.browse_requested.emit)
        self._style_tool_button(browse_btn)
        toolbar_layout.addWidget(browse_btn)
        
        # Export button
        export_btn = QToolButton()
        export_btn.setText("📤")
        export_btn.setToolTip("Export current conversation")
        export_btn.clicked.connect(self._on_export_requested)
        self._style_tool_button(export_btn)
        toolbar_layout.addWidget(export_btn)
        
        # Settings button
        settings_btn = QToolButton()
        settings_btn.setText("⚙️")
        settings_btn.setToolTip("Conversation settings")
        settings_btn.clicked.connect(self.settings_requested.emit)
        self._style_tool_button(settings_btn)
        toolbar_layout.addWidget(settings_btn)
        
        toolbar_layout.addStretch()
        
        # Background summarization progress
        self.summary_progress = QProgressBar()
        self.summary_progress.setMaximum(0)  # Indeterminate
        self.summary_progress.setVisible(False)
        self.summary_progress.setMaximumHeight(3)
        self.summary_progress.setTextVisible(False)
        toolbar_layout.addWidget(self.summary_progress)
        
        # Summary notification label
        self.summary_notification = QLabel()
        self.summary_notification.setVisible(False)
        self.summary_notification.setStyleSheet("color: #4CAF50; font-size: 9px; font-style: italic;")
        toolbar_layout.addWidget(self.summary_notification)
        
        parent_layout.addLayout(toolbar_layout)
    
    def _style_conversation_selector(self):
        """Apply custom styling to conversation selector."""
        self.conversation_selector.setStyleSheet("""
            QComboBox {
                background-color: rgba(40, 40, 40, 0.8);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid white;
                margin-top: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 30, 30, 0.95);
                color: white;
                selection-background-color: #4CAF50;
                border: 1px solid rgba(255, 255, 255, 0.3);
                outline: none;
            }
        """)
    
    def _style_tool_button(self, button: QToolButton):
        """Apply consistent styling to toolbar buttons."""
        button.setMaximumSize(30, 25)
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                font-size: 12px;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
    
    def _load_opacity_from_settings(self):
        """Load panel opacity from settings manager."""
        if not _global_settings:
            return
            
        try:
            # Try new percent-based settings first
            percent = _global_settings.get('interface.opacity', None)
            if percent is None:
                # Backward compatibility with legacy float-based settings
                legacy_opacity = _global_settings.get('ui.window_opacity', None)
                if isinstance(legacy_opacity, (int, float)):
                    if legacy_opacity <= 1.0:
                        percent = int(round(legacy_opacity * 100))
                    else:
                        percent = int(legacy_opacity)
            
            if percent is not None:
                if isinstance(percent, (int, float)):
                    percent_int = max(10, min(100, int(percent)))
                    self._panel_opacity = percent_int / 100.0
                    logger.debug(f"Loaded panel opacity from settings: {percent_int}% -> {self._panel_opacity:.2f}")
        except Exception as e:
            logger.warning(f"Failed to load opacity from settings: {e}")
    
    def _init_ui(self):
        """Initialize the enhanced user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title bar completely removed for cleaner interface
        # All conversation management moved to avatar right-click menu
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Consolas", 11))
        self.output_display.setMinimumHeight(300)
        layout.addWidget(self.output_display, 1)
        
        # Input area with background styling for prompt
        input_layout = QHBoxLayout()
        
        # Prompt label with background styling for better visual separation
        prompt_label = QLabel(">>>")
        prompt_label.setStyleSheet("""
            color: #00ff00; 
            font-family: Consolas; 
            font-size: 11px;
            background-color: rgba(0, 255, 0, 0.1);
            border-radius: 3px;
            padding: 5px 8px;
            margin-right: 5px;
        """)
        input_layout.addWidget(prompt_label)
        
        # Command input
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont("Consolas", 10))
        self.command_input.returnPressed.connect(self._on_command_entered)
        self.command_input.installEventFilter(self)
        input_layout.addWidget(self.command_input)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._on_command_entered)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # Initial welcome message
        self.append_output("💬 Ghostman Conversation Manager v2.0", "system")
        self.append_output("🚀 Clean REPL interface - conversation management via avatar menu", "system")
        self.append_output("Type 'help' for commands or start chatting with AI.", "system")
        self.append_output("-" * 50, "system")
        
        # Focus on input
        self.command_input.setFocus()
    
    def _apply_styles(self):
        """(Re)apply stylesheet using current panel opacity for background only."""
        logger.debug(f"🎨 Applying REPL styles with opacity: {self._panel_opacity:.3f}")
        
        # Clamp opacity
        alpha = max(0.0, min(1.0, self._panel_opacity))
        panel_bg = f"rgba(30, 30, 30, {alpha:.3f})"
        # Use the same alpha for text areas - no additional reduction
        textedit_bg = f"rgba(20, 20, 20, {alpha:.3f})"
        lineedit_bg = f"rgba(40, 40, 40, {alpha:.3f})"
        
        logger.debug(f"🎨 CSS colors generated:")
        logger.debug(f"  📦 Panel background: {panel_bg}")
        logger.debug(f"  📝 Text area background: {textedit_bg}")
        logger.debug(f"  ⌨️  Input background: {lineedit_bg}")
        self.setStyleSheet(f"""
            #repl-root {{
                background-color: {panel_bg};
                border-radius: 6px;
            }}
            #repl-root QTextEdit {{
                background-color: {textedit_bg};
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                padding: 5px;
            }}
            #repl-root QLineEdit {{
                background-color: {lineedit_bg};
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 5px;
            }}
            #repl-root QLineEdit:focus {{
                border: 1px solid #4CAF50;
            }}
        """)

    def set_panel_opacity(self, opacity: float):
        """Set the frame (panel) background opacity only.

        Args:
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque) for panel background.
        """
        logger.info(f"🎨 REPL panel opacity change requested: {opacity:.3f}")
        
        if not isinstance(opacity, (float, int)):
            logger.error(f"❌ Invalid opacity type: {type(opacity)} (expected float/int)")
            return
            
        old_val = self._panel_opacity
        new_val = max(0.0, min(1.0, float(opacity)))
        
        if abs(new_val - self._panel_opacity) < 0.001:
            logger.debug(f"🎨 Opacity unchanged: {old_val:.3f} -> {new_val:.3f} (difference < 0.001)")
            return
            
        logger.info(f"🎨 Applying panel opacity: {old_val:.3f} -> {new_val:.3f}")
        self._panel_opacity = new_val
        self._apply_styles()
        logger.info(f"✅ REPL panel opacity applied successfully: {new_val:.3f}")
    
    def eventFilter(self, obj, event):
        """Event filter for command input navigation."""
        if obj == self.command_input and event.type() == event.Type.KeyPress:
            key_event = event
            
            # Up arrow - previous command
            if key_event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            
            # Down arrow - next command
            elif key_event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        
        return super().eventFilter(obj, event)
    
    def _navigate_history(self, direction: int):
        """Navigate through command history."""
        if not self.command_history:
            return
        
        # Save current input if starting to navigate
        if self.history_index == -1:
            self.current_input = self.command_input.text()
        
        # Update index
        self.history_index += direction
        
        # Clamp index
        if self.history_index < -1:
            self.history_index = -1
        elif self.history_index >= len(self.command_history):
            self.history_index = len(self.command_history) - 1
        
        # Update input
        if self.history_index == -1:
            self.command_input.setText(self.current_input)
        else:
            self.command_input.setText(self.command_history[self.history_index])
    
    # Enhanced event handlers for conversation management
    @pyqtSlot(str)
    def _on_conversation_selected(self, display_name: str):
        """Handle conversation selection from dropdown."""
        current_index = self.conversation_selector.currentIndex()
        if current_index < 0:
            return
        
        conversation_id = self.conversation_selector.itemData(current_index)
        
        if not conversation_id:  # New conversation selected
            self._create_new_conversation()
            return
        
        # Find conversation in list
        selected_conversation = None
        for conv in self.conversations_list:
            if conv.id == conversation_id:
                selected_conversation = conv
                break
        
        if selected_conversation:
            self._switch_to_conversation(selected_conversation)
        else:
            logger.warning(f"Conversation not found: {conversation_id}")
    
    def _switch_to_conversation(self, conversation: Conversation):
        """Switch to a different conversation."""
        if self.current_conversation and self.current_conversation.id == conversation.id:
            return  # Already active
        
        logger.info(f"🔄 Switching to conversation: {conversation.title}")
        
        # Save current conversation state if needed
        if self.current_conversation:
            self.idle_detector.reset_activity(conversation.id)
        
        # Switch to new conversation
        self.current_conversation = conversation
        self._update_status_label(conversation)
        
        # Load conversation messages in output
        self._load_conversation_messages(conversation)
        
        # CRITICAL: Update AI service context when switching conversations
        if self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                logger.info(f"🔄 Updating AI service context for conversation switch")
                
                # Use the proper method to set conversation and load context
                ai_service.set_current_conversation(conversation.id)
                
                logger.info(f"✅ AI service context updated for conversation: {conversation.id}")
        
        # Reset idle detector for new conversation
        self.idle_detector.reset_activity(conversation.id)
        
        # Emit signal for external components
        self.conversation_changed.emit(conversation.id)
        
        logger.info(f"✅ Switched to conversation: {conversation.title}")
    
    def _create_new_conversation(self):
        """Create a new conversation."""
        if not self.conversation_manager:
            logger.warning("Cannot create conversation - manager not available")
            return
        
        logger.info("🆕 Creating new conversation...")
        
        # Create new conversation asynchronously
        import asyncio
        
        async def create_async():
            try:
                # Generate a default title
                title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                conversation = await self.conversation_manager.create_conversation(
                    title=title,
                    initial_message="New conversation started"
                )
                
                if conversation:
                    # Add to conversations list
                    self.conversations_list.insert(0, conversation)
                    
                    # Update selector
                    display_name = f"{self._get_status_icon(conversation)} {conversation.title}"
                    self.conversation_selector.insertItem(0, display_name, conversation.id)
                    self.conversation_selector.setCurrentIndex(0)
                    
                    # Switch to new conversation
                    self._switch_to_conversation(conversation)
                    
                    self.append_output(f"✨ Created new conversation: {conversation.title}", "system")
                    logger.info(f"✅ New conversation created: {conversation.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create conversation: {e}")
                self.append_output("❌ Failed to create new conversation", "error")
        
        # Run async task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task if loop is already running
                asyncio.create_task(create_async())
            else:
                loop.run_until_complete(create_async())
        except Exception as e:
            logger.error(f"Failed to run async conversation creation: {e}")
    
    def _load_conversation_messages(self, conversation: Conversation):
        """Load conversation messages into output display."""
        self.clear_output()
        
        self.append_output(f"💬 Conversation: {conversation.title}", "system")
        
        if conversation.summary:
            self.append_output(f"💡 Summary: {conversation.summary.summary}", "info")
            if conversation.summary.key_topics:
                topics = ", ".join(conversation.summary.key_topics)
                self.append_output(f"📝 Topics: {topics}", "info")
        
        self.append_output("-" * 50, "system")
        
        # Load messages with appropriate icons
        for message in conversation.messages:
            if message.role == MessageRole.SYSTEM:
                continue  # Skip system messages in display
            
            role_icon = "👤" if message.role == MessageRole.USER else "🤖"
            role_name = "You" if message.role == MessageRole.USER else "AI"
            style = "input" if message.role == MessageRole.USER else "response"
            
            timestamp = message.timestamp.strftime("%H:%M")
            self.append_output(f"[{timestamp}] {role_icon} {role_name}: {message.content}", style)
        
        if not conversation.messages:
            self.append_output("🎆 Start a new conversation!", "info")
    
    @pyqtSlot()
    def _on_export_requested(self):
        """Handle export request for current conversation."""
        if not self.current_conversation:
            self.append_output("⚠️ No conversation selected for export", "warning")
            return
        
        logger.info(f"📤 Export requested for conversation: {self.current_conversation.id}")
        self.export_requested.emit(self.current_conversation.id)
    
    @pyqtSlot(str)
    def _on_idle_detected(self, conversation_id: str):
        """Handle idle detection for background summarization."""
        if not self.conversation_manager or not conversation_id:
            return
        
        # Add to summarization queue if not already present
        if conversation_id not in self.summarization_queue:
            self.summarization_queue.append(conversation_id)
            logger.info(f"🕰️ Idle detected - queued conversation for summarization: {conversation_id}")
        
        # Start background summarization if not already running
        if not self.is_summarizing:
            self._start_background_summarization()
    
    def _start_background_summarization(self):
        """Start background summarization process."""
        if not self.summarization_queue or self.is_summarizing:
            return
        
        self.is_summarizing = True
        
        # Show progress indicator
        self.summary_progress.setVisible(True)
        self.summary_notification.setText("🧪 Generating summary...")
        self.summary_notification.setVisible(True)
        
        logger.info("🔄 Starting background summarization...")
        
        # Create background worker
        class SummarizationWorker(QObject):
            finished = pyqtSignal(str, bool)  # conversation_id, success
            
            def __init__(self, conversation_manager, conversation_id):
                super().__init__()
                self.conversation_manager = conversation_manager
                self.conversation_id = conversation_id
            
            def run(self):
                try:
                    # Get summary service
                    if hasattr(self.conversation_manager, 'conversation_service'):
                        summary_service = self.conversation_manager.conversation_service.summary_service
                        
                        # Generate summary asynchronously
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            success = loop.run_until_complete(
                                summary_service.generate_summary(self.conversation_id)
                            )
                            self.finished.emit(self.conversation_id, success)
                        finally:
                            loop.close()
                    else:
                        self.finished.emit(self.conversation_id, False)
                        
                except Exception as e:
                    logger.error(f"Summarization worker error: {e}")
                    self.finished.emit(self.conversation_id, False)
        
        # Process first conversation in queue
        conversation_id = self.summarization_queue[0]
        
        # Create and start worker thread
        self.summary_thread = QThread()
        self.summary_worker = SummarizationWorker(self.conversation_manager, conversation_id)
        self.summary_worker.moveToThread(self.summary_thread)
        
        # Connect signals
        self.summary_thread.started.connect(self.summary_worker.run)
        self.summary_worker.finished.connect(self._on_summarization_finished)
        self.summary_worker.finished.connect(self.summary_thread.quit)
        self.summary_worker.finished.connect(self.summary_worker.deleteLater)
        self.summary_thread.finished.connect(self.summary_thread.deleteLater)
        
        # Start processing
        self.summary_thread.start()
    
    @pyqtSlot(str, bool)
    def _on_summarization_finished(self, conversation_id: str, success: bool):
        """Handle completion of background summarization."""
        # Remove from queue
        if conversation_id in self.summarization_queue:
            self.summarization_queue.remove(conversation_id)
        
        if success:
            self.summary_notification.setText("✅ Summary generated")
            logger.info(f"✅ Summary generated for conversation: {conversation_id}")
            
            # Update conversation data if it's the current one
            if self.current_conversation and self.current_conversation.id == conversation_id:
                self._refresh_current_conversation()
        else:
            self.summary_notification.setText("❌ Summary failed")
            logger.warning(f"❌ Summary generation failed for conversation: {conversation_id}")
        
        # Hide progress after delay
        QTimer.singleShot(3000, self._hide_summary_notification)
        
        # Process next item in queue
        self.is_summarizing = False
        if self.summarization_queue:
            QTimer.singleShot(1000, self._start_background_summarization)
    
    def _hide_summary_notification(self):
        """Hide summary notification and progress bar."""
        self.summary_progress.setVisible(False)
        self.summary_notification.setVisible(False)
    
    def _refresh_current_conversation(self):
        """Refresh current conversation data from database."""
        if not self.current_conversation or not self.conversation_manager:
            return
        
        async def refresh_async():
            try:
                updated_conv = await self.conversation_manager.get_conversation(
                    self.current_conversation.id
                )
                if updated_conv:
                    self.current_conversation = updated_conv
                    self._update_status_label(updated_conv)
                    
                    # Update conversation in list
                    for i, conv in enumerate(self.conversations_list):
                        if conv.id == updated_conv.id:
                            self.conversations_list[i] = updated_conv
                            break
            except Exception as e:
                logger.error(f"Failed to refresh conversation: {e}")
        
        # Run refresh asynchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(refresh_async())
            else:
                loop.run_until_complete(refresh_async())
        except Exception as e:
            logger.error(f"Failed to run async conversation refresh: {e}")
    
    def _on_command_entered(self):
        """Handle command entry."""
        command = self.command_input.text().strip()
        
        if not command:
            return
        
        # Add to history
        if not self.command_history or command != self.command_history[-1]:
            self.command_history.append(command)
        
        # Reset history navigation
        self.history_index = -1
        self.current_input = ""
        
        # Display command in output
        self.append_output(f">>> {command}", "input")
        
        # Clear input
        self.command_input.clear()
        
        # Process command
        self._process_command(command)
        
        # Emit signal for external processing
        self.command_entered.emit(command)
    
    def _process_command(self, command: str):
        """Process built-in commands."""
        command_lower = command.lower()
        
        if command_lower == "help":
            self.append_output("Available commands:", "info")
            self.append_output("  help     - Show this help message", "info")
            self.append_output("  clear    - Clear the output display", "info")
            self.append_output("  history  - Show command history", "info")
            self.append_output("  exit     - Minimize to system tray", "info")
            self.append_output("  quit     - Exit the application", "info")
            self.append_output("  context  - Show AI context status (debug)", "info")
            self.append_output("\nAny other input will be sent to the AI assistant.", "info")
        
        elif command_lower == "clear":
            self.clear_output()
            self.append_output("Output cleared", "system")
        
        elif command_lower == "history":
            if self.command_history:
                self.append_output("Command history:", "info")
                for i, cmd in enumerate(self.command_history[-10:], 1):
                    self.append_output(f"  {i}. {cmd}", "info")
            else:
                self.append_output("No command history", "info")
        
        elif command_lower == "exit":
            self.minimize_requested.emit()
        
        elif command_lower == "quit":
            # Would need to connect to app quit
            self.append_output("Use system tray menu to quit application", "warning")
        
        elif command_lower == "context":
            # Debug command to show AI context status
            self._show_context_status()
        
        else:
            # Send to AI service
            self._send_to_ai(command)
    
    def append_output(self, text: str, style: str = "normal"):
        """
        Append text to the output display with styling.
        
        Args:
            text: Text to append
            style: Style type (normal, input, response, system, info, warning, error)
        """
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Set color based on style
        colors = {
            "normal": "#f0f0f0",
            "input": "#00ff00",
            "response": "#00bfff",
            "system": "#808080",
            "info": "#ffff00",
            "warning": "#ffa500",
            "error": "#ff0000"
        }
        
        color = colors.get(style, "#f0f0f0")
        
        # Insert formatted text
        cursor.insertHtml(f'<span style="color: {color};">{text}</span><br>')
        
        # Auto-scroll to bottom
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
    
    def clear_output(self):
        """Clear the output display."""
        self.output_display.clear()
    
    def _show_context_status(self):
        """Show AI context status for debugging."""
        self.append_output("=== AI Context Status ===", "info")
        
        # Current conversation info
        if self.current_conversation:
            self.append_output(f"Current Conversation: {self.current_conversation.title}", "info")
            self.append_output(f"Conversation ID: {self.current_conversation.id}", "info")
            if hasattr(self.current_conversation, 'messages'):
                self.append_output(f"Messages in DB: {len(self.current_conversation.messages)}", "info")
        else:
            self.append_output("Current Conversation: None", "warning")
        
        # AI service context info
        if self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                self.append_output(f"AI Service Available: Yes", "info")
                self.append_output(f"AI Current Conversation: {ai_service.get_current_conversation_id()}", "info")
                self.append_output(f"AI Context Messages: {len(ai_service.conversation.messages)}", "info")
                self.append_output(f"AI Max Messages: {ai_service.conversation.max_messages}", "info")
                
                # Show recent messages in context
                if ai_service.conversation.messages:
                    self.append_output("Recent AI Context Messages:", "info")
                    for i, msg in enumerate(ai_service.conversation.messages[-5:]):  # Last 5 messages
                        preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                        self.append_output(f"  {msg.role}: {preview}", "info")
                else:
                    self.append_output("AI Context: Empty", "warning")
            else:
                self.append_output("AI Service Available: No", "warning")
        else:
            self.append_output("Conversation Manager AI Service: Not Available", "warning")
        
        self.append_output("========================", "info")
    
    def _send_to_ai(self, message: str):
        """Send message to AI service with conversation management."""
        # Ensure we have an active conversation
        if not self.current_conversation and self.conversation_manager:
            logger.info("🆕 Auto-creating conversation for AI interaction")
            self._create_new_conversation_for_message(message)
            
        # Ensure AI service has the correct conversation context
        if self.current_conversation and self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                # Make sure the current conversation is set in the AI service
                current_ai_conversation = ai_service.get_current_conversation_id()
                if current_ai_conversation != self.current_conversation.id:
                    logger.info(f"🔄 Syncing AI service conversation context: {current_ai_conversation} -> {self.current_conversation.id}")
                    ai_service.set_current_conversation(self.current_conversation.id)
        
        self.append_output("🤖 Processing with AI...", "system")
        
        # Reset idle detector
        self.idle_detector.reset_activity(
            self.current_conversation.id if self.current_conversation else None
        )
        
        # Disable input while processing
        self.command_input.setEnabled(False)
        
        # Create enhanced AI worker thread
        class EnhancedAIWorker(QObject):
            response_received = pyqtSignal(str, bool)  # response, success
            
            def __init__(self, message, conversation_manager, current_conversation):
                super().__init__()
                self.message = message
                self.conversation_manager = conversation_manager
                self.current_conversation = current_conversation
            
            def run(self):
                try:
                    # ALWAYS prefer conversation-aware AI service for context persistence
                    ai_service = None
                    if self.conversation_manager:
                        # Call get_ai_service() which will initialize it if needed
                        ai_service = self.conversation_manager.get_ai_service()
                        if ai_service:
                            logger.info("🎯 Using conversation-aware AI service for context persistence")
                        
                        if ai_service:
                            # Ensure current conversation context is set
                            if self.current_conversation:
                                logger.debug(f"Setting AI service conversation context to: {self.current_conversation.id}")
                                ai_service.set_current_conversation(self.current_conversation.id)
                            
                            # Send message with full conversation context
                            result = ai_service.send_message(self.message, save_conversation=True)
                            
                            if result.get('success', False):
                                logger.info(f"✅ AI response received with context (context size: {len(ai_service.conversation.messages)} messages)")
                                self.response_received.emit(result['response'], True)
                            else:
                                error_msg = f"❌ AI Error: {result.get('error', 'Unknown error')}"
                                logger.error(f"AI service error: {error_msg}")
                                self.response_received.emit(error_msg, False)
                            return
                        else:
                            logger.warning("⚠️  Conversation manager AI service not available")
                    
                    # Only fallback to basic AI service if conversation manager not available
                    logger.warning("🔄 Falling back to basic AI service (context may be lost)")
                    ai_service = self._get_basic_ai_service()
                    
                    if not ai_service or not ai_service.is_initialized:
                        self.response_received.emit(
                            "❌ AI service not available. Please configure AI settings first.", 
                            False
                        )
                        return
                    
                    # Send message to basic AI service (without conversation context)
                    logger.debug("Sent Message: %s", self.message)
                    result = ai_service.send_message(self.message)
                    
                    if result.get('success', False):
                        logger.warning("⚠️  Using basic AI service - conversation context may be limited")
                        self.response_received.emit(result['response'], True)
                    else:
                        error_msg = f"❌ AI Error: {result.get('error', 'Unknown error')}"
                        self.response_received.emit(error_msg, False)
                        
                except Exception as e:
                    logger.error(f"Enhanced AI worker error: {e}")
                    self.response_received.emit(f"❌ Error: {str(e)}", False)
            
            def _get_basic_ai_service(self):
                """Get basic AI service instance as fallback."""
                try:
                    from ...infrastructure.ai.ai_service import AIService
                    ai_service = AIService()
                    
                    # Initialize with current settings
                    if ai_service.initialize():
                        return ai_service
                    else:
                        return None
                        
                except ImportError:
                    logger.error("AI service not available")
                    return None
                except Exception as e:
                    logger.error(f"Failed to get AI service: {e}")
                    return None
        
        # Create and start worker thread
        self.ai_thread = QThread()
        self.ai_worker = EnhancedAIWorker(message, self.conversation_manager, self.current_conversation)
        self.ai_worker.moveToThread(self.ai_thread)
        
        # Connect signals
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.response_received.connect(self._on_ai_response)
        self.ai_worker.response_received.connect(self.ai_thread.quit)
        self.ai_worker.response_received.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        
        # Start processing
        self.ai_thread.start()
    
    def _on_ai_response(self, response: str, success: bool):
        """Handle AI response with conversation management."""
        # Re-enable input
        self.command_input.setEnabled(True)
        self.command_input.setFocus()
        
        # Reset idle detector
        self.idle_detector.reset_activity(
            self.current_conversation.id if self.current_conversation else None
        )
        
        # Display response with appropriate icon
        if success:
            self.append_output(f"🤖 AI: {response}", "response")
            
            # If we have a conversation manager and current conversation,
            # the response should already be saved via the conversation-aware AI service
            if not self.conversation_manager and self.current_conversation:
                # Manual fallback - add to conversation if needed
                logger.info("Manual message saving not yet implemented")
        else:
            self.append_output(response, "error")
        
        logger.debug(f"Enhanced AI response displayed: success={success}")
    
    # Public methods for external integration
    
    def set_conversation_manager(self, conversation_manager: ConversationManager):
        """Set the conversation manager instance."""
        self.conversation_manager = conversation_manager
        if conversation_manager and conversation_manager.is_initialized():
            # Reload conversations
            try:
                logger.debug("Reloading conversations after setting manager...")
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._load_conversations())
                else:
                    loop.run_until_complete(self._load_conversations())
                logger.debug("Conversation reload initiated successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load conversations after setting manager: {e}", exc_info=True)
        logger.info("Conversation manager set for REPL widget")
    
    def get_current_conversation_id(self) -> Optional[str]:
        """Get the ID of the currently active conversation."""
        # Don't return ID for empty conversations
        if self.current_conversation:
            # Check if conversation has any messages
            if hasattr(self.current_conversation, 'message_count') and self.current_conversation.message_count > 0:
                return self.current_conversation.id
            elif hasattr(self.current_conversation, 'messages') and len(self.current_conversation.messages) > 0:
                return self.current_conversation.id
        return None
    
    def restore_conversation(self, conversation_id: str):
        """Restore a specific conversation by ID."""
        if not self.conversation_manager:
            logger.warning("Cannot restore conversation - no conversation manager available")
            return
            
        try:
            logger.debug(f"Attempting to restore conversation: {conversation_id}")
            
            # Create async task to load the conversation
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._restore_conversation_async(conversation_id))
            else:
                loop.run_until_complete(self._restore_conversation_async(conversation_id))
                
        except Exception as e:
            logger.error(f"❌ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
    
    async def _restore_conversation_async(self, conversation_id: str):
        """Restore conversation asynchronously."""
        try:
            # Load the conversation from database with messages
            conversation = await self.conversation_manager.get_conversation(conversation_id, include_messages=True)
            
            if conversation:
                # Set as current conversation
                self.current_conversation = conversation
                logger.info(f"✅ Restored conversation: {conversation.title}")
                
                # Load conversation messages into REPL display
                self.clear_output()
                self.append_output(f"📂 Restored conversation: {conversation.title}", "system")
                
                # Display conversation history
                if hasattr(conversation, 'messages') and conversation.messages:
                    logger.info(f"📜 Restoring {len(conversation.messages)} messages")
                    for message in conversation.messages:
                        if hasattr(message, 'role') and hasattr(message, 'content'):
                            if message.role.value == 'user':
                                self.append_output(f">>> {message.content}", "input")
                            elif message.role.value == 'assistant':
                                self.append_output(message.content, "response")
                            elif message.role.value == 'system':
                                self.append_output(f"[System] {message.content}", "system")
                else:
                    logger.debug("No messages found for conversation")
                
                self.append_output("", "system")  # Add spacing
                self.append_output("💬 Conversation restored. Continue chatting...", "system")
                
                # Update idle detector
                self.idle_detector.reset_activity(conversation_id)
                
                # Update AI service context if available - CRITICAL for maintaining context
                if hasattr(conversation, 'messages') and conversation.messages:
                    # Get or initialize conversation-aware AI service from conversation manager
                    ai_service = None
                    if self.conversation_manager:
                        # Call get_ai_service() which will initialize it if needed
                        ai_service = self.conversation_manager.get_ai_service()
                    
                    if ai_service:
                        logger.info(f"🔄 Setting AI service to restored conversation context")
                        
                        # Use the proper method to set conversation and load context
                        ai_service.set_current_conversation(conversation_id)
                        
                        logger.info(f"✅ AI service context restored for conversation: {conversation_id}")
                    else:
                        logger.warning("⚠️  No AI service available for context rebuilding")
                
            else:
                logger.warning(f"⚠️  Conversation {conversation_id} not found in database")
                self.append_output(f"⚠️ Could not restore conversation {conversation_id[:8]}... (not found)", "warning")
                
        except Exception as e:
            logger.error(f"❌ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
            self.append_output(f"❌ Failed to restore conversation: {str(e)}", "error")
    
    def _create_new_conversation_for_message(self, message: str):
        """Create a new conversation automatically when user starts chatting."""
        if not self.conversation_manager:
            return
            
        try:
            # Generate a title from the message (first few words)
            words = message.strip().split()[:5]  # First 5 words
            title = " ".join(words)
            if len(title) > 50:
                title = title[:47] + "..."
            elif len(title) < 5:
                title = f"Chat {datetime.now().strftime('%H:%M')}"
            
            logger.debug(f"Creating conversation with title: {title}")
            
            # Create conversation synchronously to ensure it's ready for AI processing
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't use run_until_complete in running loop, so create task
                # but this won't block - conversation will be created in background
                asyncio.create_task(self._create_conversation_async(title, message))
            else:
                # Run synchronously
                conversation = loop.run_until_complete(self._create_conversation_async(title, message))
                if conversation:
                    self.current_conversation = conversation
                    logger.info(f"✅ Auto-created conversation: {conversation.title}")
                
        except Exception as e:
            logger.error(f"❌ Failed to auto-create conversation: {e}", exc_info=True)
    
    async def _create_conversation_async(self, title: str, initial_message: str):
        """Create conversation asynchronously."""
        try:
            conversation = await self.conversation_manager.create_conversation(
                title=title,
                initial_message=initial_message
            )
            
            if conversation:
                # Update current conversation if this was called synchronously
                self.current_conversation = conversation
                # Add to conversations list
                if conversation not in self.conversations_list:
                    self.conversations_list.insert(0, conversation)
                logger.info(f"✅ Created conversation: {conversation.title}")
                return conversation
            
        except Exception as e:
            logger.error(f"❌ Failed to create conversation async: {e}")
        
        return None
    
    def refresh_conversations(self):
        """Refresh the conversations list from the database."""
        if not self.conversation_manager:
            return
        
        try:
            logger.debug("Refreshing conversations list...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._load_conversations())
            else:
                loop.run_until_complete(self._load_conversations())
            logger.debug("Conversation refresh initiated successfully")
        except Exception as e:
            logger.error(f"❌ Failed to refresh conversations: {e}", exc_info=True)
    
    def create_new_conversation_with_title(self, title: str):
        """Create a new conversation with a specific title."""
        if not self.conversation_manager:
            logger.warning("Cannot create conversation - manager not available")
            return
        
        async def create_with_title():
            try:
                conversation = await self.conversation_manager.create_conversation(
                    title=title,
                    initial_message=f"New conversation: {title}"
                )
                
                if conversation:
                    # Add to conversations list and update UI
                    self.conversations_list.insert(0, conversation)
                    
                    display_name = f"{self._get_status_icon(conversation)} {conversation.title}"
                    self.conversation_selector.insertItem(0, display_name, conversation.id)
                    self.conversation_selector.setCurrentIndex(0)
                    
                    # Switch to new conversation
                    self._switch_to_conversation(conversation)
                    
                    self.append_output(f"✨ Created conversation: {conversation.title}", "system")
                    logger.info(f"✅ Conversation created with title: {title}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create conversation with title: {e}")
                self.append_output("❌ Failed to create new conversation", "error")
        
        # Run async task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(create_with_title())
            else:
                loop.run_until_complete(create_with_title())
        except Exception as e:
            logger.error(f"Failed to run async conversation creation: {e}")
    
    def set_ai_service(self, ai_service):
        """Set the AI service instance (for backward compatibility)."""
        self._ai_service = ai_service
        logger.debug("AI service set for REPL widget")
    
    def shutdown(self):
        """Shutdown the enhanced REPL widget."""
        logger.info("Shutting down Enhanced REPL Widget...")
        
        try:
            # Stop idle detector
            if hasattr(self, 'idle_detector'):
                self.idle_detector.check_timer.stop()
            
            # Stop any running AI threads
            if hasattr(self, 'ai_thread') and self.ai_thread.isRunning():
                self.ai_thread.quit()
                self.ai_thread.wait(3000)  # Wait up to 3 seconds
            
            # Stop summarization threads
            if hasattr(self, 'summary_thread') and self.summary_thread.isRunning():
                self.summary_thread.quit()
                self.summary_thread.wait(3000)
            
            # Clear conversation references
            self.current_conversation = None
            self.conversations_list.clear()
            
            logger.info("✅ Enhanced REPL Widget shut down successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during REPL widget shutdown: {e}")