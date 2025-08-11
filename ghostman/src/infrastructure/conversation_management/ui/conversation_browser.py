"""
Conversation browser dialog for managing conversations.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QLabel,
    QTextEdit, QSplitter, QGroupBox, QCheckBox, QMessageBox,
    QProgressBar, QStatusBar, QMenuBar, QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer, QModelIndex
from PyQt6.QtGui import QAction, QIcon, QFont, QCursor

from ..integration.conversation_manager import ConversationManager
from ..models.enums import ConversationStatus, SortOrder
from ..models.search import SearchQuery

logger = logging.getLogger("ghostman.conversation_browser")


class ConversationBrowserDialog(QDialog):
    """
    Comprehensive conversation browser and management dialog.
    
    Provides a full-featured interface for:
    - Browsing and searching conversations
    - Viewing conversation details and messages
    - Managing conversation metadata (tags, categories)
    - Bulk operations (export, delete, archive)
    - Analytics and statistics
    """
    
    # Signals
    conversation_selected = pyqtSignal(str)  # conversation_id
    conversation_loaded = pyqtSignal(str)    # conversation_id
    
    def __init__(self, conversation_manager: ConversationManager, parent=None):
        """Initialize conversation browser dialog."""
        super().__init__(parent)
        
        self.conversation_manager = conversation_manager
        self.conversations: List = []
        self.selected_conversation_id: Optional[str] = None
        
        # UI components
        self.conversation_table: Optional[QTableWidget] = None
        self.preview_area: Optional[QTextEdit] = None
        self.search_input: Optional[QLineEdit] = None
        self.filter_combo: Optional[QComboBox] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None
        
        self._init_ui()
        self._load_conversations()
        
        logger.info("ConversationBrowserDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Conversation Browser - Ghostman")
        self.setGeometry(200, 200, 1200, 800)
        self.setModal(False)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Menu bar
        self._create_menu_bar(main_layout)
        
        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Main content area (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Left side: Conversation list
        left_panel = self._create_conversation_list_panel()
        splitter.addWidget(left_panel)
        
        # Right side: Preview and details
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (70% list, 30% preview)
        splitter.setSizes([840, 360])
        
        # Status bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Apply styling
        self._apply_styles()
    
    def _create_menu_bar(self, parent_layout):
        """Create menu bar."""
        menu_bar = QMenuBar()
        parent_layout.addWidget(menu_bar)
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        export_action = QAction("Export Selected...", self)
        export_action.triggered.connect(self._export_selected)
        file_menu.addAction(export_action)
        
        export_all_action = QAction("Export All...", self)
        export_all_action.triggered.connect(self._export_all)
        file_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        close_action = QAction("Close", self)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self._select_all)
        edit_menu.addAction(select_all_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._load_conversations)
        view_menu.addAction(refresh_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        stats_action = QAction("Statistics...", self)
        stats_action.triggered.connect(self._show_statistics)
        tools_menu.addAction(stats_action)
        
        cleanup_action = QAction("Cleanup...", self)
        cleanup_action.triggered.connect(self._cleanup_conversations)
        tools_menu.addAction(cleanup_action)
    
    def _create_toolbar(self) -> QGroupBox:
        """Create toolbar with search and filters."""
        toolbar = QGroupBox("Search & Filter")
        layout = QHBoxLayout(toolbar)
        
        # Search
        layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search conversations, messages, tags...")
        self.search_input.returnPressed.connect(self._search_conversations)
        layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search_conversations)
        layout.addWidget(search_btn)
        
        # Filter
        layout.addWidget(QLabel("Status:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All",
            "Active",
            "Pinned",
            "Archived",
            "Deleted"
        ])
        self.filter_combo.currentTextChanged.connect(self._filter_changed)
        layout.addWidget(self.filter_combo)
        
        # Sort
        layout.addWidget(QLabel("Sort:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Updated (Newest)",
            "Updated (Oldest)",
            "Created (Newest)",
            "Created (Oldest)",
            "Title (A-Z)",
            "Title (Z-A)"
        ])
        self.sort_combo.currentTextChanged.connect(self._sort_changed)
        layout.addWidget(self.sort_combo)
        
        layout.addStretch()
        
        # Action buttons
        new_btn = QPushButton("New Conversation")
        new_btn.clicked.connect(self._create_new_conversation)
        layout.addWidget(new_btn)
        
        return toolbar
    
    def _create_conversation_list_panel(self) -> QGroupBox:
        """Create the conversation list panel."""
        panel = QGroupBox("Conversations")
        layout = QVBoxLayout(panel)
        
        # Table
        self.conversation_table = QTableWidget()
        self.conversation_table.setColumnCount(6)
        self.conversation_table.setHorizontalHeaderLabels([
            "Title", "Status", "Messages", "Created", "Updated", "Tags"
        ])
        
        # Configure table
        header = self.conversation_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Messages
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Created
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Updated
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Tags
        header.resizeSection(5, 150)
        
        self.conversation_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.conversation_table.setAlternatingRowColors(True)
        self.conversation_table.setSortingEnabled(True)
        
        # Connect signals
        self.conversation_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.conversation_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.conversation_table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_selected_conversation)
        button_layout.addWidget(load_btn)
        
        archive_btn = QPushButton("Archive")
        archive_btn.clicked.connect(self._archive_selected)
        button_layout.addWidget(archive_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected)
        button_layout.addWidget(delete_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return panel
    
    def _create_preview_panel(self) -> QGroupBox:
        """Create the preview panel."""
        panel = QGroupBox("Preview")
        layout = QVBoxLayout(panel)
        
        # Conversation info
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)
        
        self.info_label = QLabel("Select a conversation to view details")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_group)
        
        # Message preview
        preview_group = QGroupBox("Messages")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setPlainText("Select a conversation to preview messages...")
        preview_layout.addWidget(self.preview_area)
        
        layout.addWidget(preview_group, 1)
        
        return panel
    
    def _apply_styles(self):
        """Apply custom styles."""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f8f8f8;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 3px;
                border: 1px solid #ccc;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d4edda;
            }
            QLineEdit, QComboBox {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
    
    def _load_conversations(self):
        """Load conversations into the table."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.showMessage("Loading conversations...")
        
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
                        self.manager.list_conversations(limit=None)  # Load all
                    )
                    self.conversations_loaded.emit(conversations)
                except Exception as e:
                    logger.error(f"Failed to load conversations: {e}")
                    self.conversations_loaded.emit([])
        
        self._loader_thread = QThread()
        self._loader = ConversationLoader(self.conversation_manager)
        self._loader.moveToThread(self._loader_thread)
        
        self._loader_thread.started.connect(self._loader.load)
        self._loader.conversations_loaded.connect(self._populate_table)
        self._loader.conversations_loaded.connect(self._loader_thread.quit)
        self._loader.conversations_loaded.connect(self._loader.deleteLater)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        
        self._loader_thread.start()
    
    def _populate_table(self, conversations):
        """Populate the conversation table."""
        self.conversations = conversations
        self.conversation_table.setRowCount(len(conversations))
        
        for i, conv in enumerate(conversations):
            # Title
            title_item = QTableWidgetItem(conv.title)
            title_item.setData(Qt.ItemDataRole.UserRole, conv.id)
            self.conversation_table.setItem(i, 0, title_item)
            
            # Status
            status_icon = {
                "active": "🟢",
                "pinned": "📌", 
                "archived": "📦",
                "deleted": "🗑️"
            }.get(conv.status.value, "⚫")
            
            status_item = QTableWidgetItem(f"{status_icon} {conv.status.value.title()}")
            self.conversation_table.setItem(i, 1, status_item)
            
            # Message count
            msg_count = QTableWidgetItem(str(conv.get_message_count()))
            msg_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.conversation_table.setItem(i, 2, msg_count)
            
            # Created date
            created_item = QTableWidgetItem(conv.created_at.strftime("%Y-%m-%d %H:%M"))
            self.conversation_table.setItem(i, 3, created_item)
            
            # Updated date
            updated_item = QTableWidgetItem(conv.updated_at.strftime("%Y-%m-%d %H:%M"))
            self.conversation_table.setItem(i, 4, updated_item)
            
            # Tags
            tags_text = ", ".join(list(conv.metadata.tags)[:3])  # Show first 3 tags
            if len(conv.metadata.tags) > 3:
                tags_text += f" (+{len(conv.metadata.tags) - 3})"
            
            tags_item = QTableWidgetItem(tags_text)
            self.conversation_table.setItem(i, 5, tags_item)
        
        # Update status
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Loaded {len(conversations)} conversations", 3000)
        
        # Auto-select first row
        if conversations:
            self.conversation_table.selectRow(0)
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = self.conversation_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_conversation_id = None
            self._clear_preview()
            return
        
        row = selected_rows[0].row()
        if row < len(self.conversations):
            conversation = self.conversations[row]
            self.selected_conversation_id = conversation.id
            self._update_preview(conversation)
    
    def _update_preview(self, conversation):
        """Update the preview panel with conversation details."""
        # Update info
        info_text = f"""
        <b>Title:</b> {conversation.title}<br>
        <b>ID:</b> {conversation.id}<br>
        <b>Status:</b> {conversation.status.value.title()}<br>
        <b>Created:</b> {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
        <b>Updated:</b> {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
        <b>Messages:</b> {conversation.get_message_count()}<br>
        <b>Tokens:</b> {conversation.get_token_count()}<br>
        """
        
        if conversation.metadata.tags:
            info_text += f"<b>Tags:</b> {', '.join(conversation.metadata.tags)}<br>"
        
        if conversation.metadata.category:
            info_text += f"<b>Category:</b> {conversation.metadata.category}<br>"
        
        if conversation.summary:
            info_text += f"<b>Summary:</b> {conversation.summary.summary}<br>"
        
        self.info_label.setText(info_text)
        
        # Update message preview
        if conversation.messages:
            preview_text = []
            for msg in conversation.messages[-5:]:  # Show last 5 messages
                role_icon = {"system": "🔧", "user": "👤", "assistant": "🤖"}.get(msg.role.value, "💬")
                timestamp = msg.timestamp.strftime("%H:%M")
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                preview_text.append(f"[{timestamp}] {role_icon} {msg.role.value.upper()}: {content}")
            
            self.preview_area.setPlainText("\n\n".join(preview_text))
        else:
            self.preview_area.setPlainText("No messages in this conversation.")
    
    def _clear_preview(self):
        """Clear the preview panel."""
        self.info_label.setText("Select a conversation to view details")
        self.preview_area.setPlainText("Select a conversation to preview messages...")
    
    def _on_item_double_clicked(self):
        """Handle double-click on table item."""
        self._load_selected_conversation()
    
    def _load_selected_conversation(self):
        """Load the selected conversation."""
        if self.selected_conversation_id:
            self.conversation_loaded.emit(self.selected_conversation_id)
            self.close()
    
    def _search_conversations(self):
        """Search conversations."""
        search_text = self.search_input.text().strip()
        if not search_text:
            self._load_conversations()
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage(f"Searching for: {search_text}")
        
        # TODO: Implement search functionality
        QTimer.singleShot(1000, lambda: self._search_complete([]))
    
    def _search_complete(self, results):
        """Handle search completion."""
        self._populate_table(results)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Search completed: {len(results)} results", 3000)
    
    def _filter_changed(self):
        """Handle filter change."""
        filter_text = self.filter_combo.currentText()
        # TODO: Implement filtering
        logger.info(f"Filter changed to: {filter_text}")
    
    def _sort_changed(self):
        """Handle sort change."""
        sort_text = self.sort_combo.currentText()
        # TODO: Implement sorting
        logger.info(f"Sort changed to: {sort_text}")
    
    def _create_new_conversation(self):
        """Create a new conversation."""
        # TODO: Open new conversation dialog
        QMessageBox.information(self, "New Conversation", "New conversation dialog will be implemented.")
    
    def _archive_selected(self):
        """Archive selected conversations."""
        if not self.selected_conversation_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Archive Conversation",
            "Are you sure you want to archive the selected conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement archiving
            QMessageBox.information(self, "Archive", "Conversation archived.")
    
    def _delete_selected(self):
        """Delete selected conversations."""
        if not self.selected_conversation_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            "Are you sure you want to delete the selected conversation?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement deletion
            QMessageBox.information(self, "Delete", "Conversation deleted.")
    
    def _export_selected(self):
        """Export selected conversations."""
        if not self.selected_conversation_id:
            QMessageBox.warning(self, "Export", "No conversation selected.")
            return
        
        # TODO: Implement export dialog
        QMessageBox.information(self, "Export", "Export dialog will be implemented.")
    
    def _export_all(self):
        """Export all conversations."""
        if not self.conversations:
            QMessageBox.warning(self, "Export", "No conversations to export.")
            return
        
        # TODO: Implement bulk export
        QMessageBox.information(self, "Export All", "Bulk export will be implemented.")
    
    def _select_all(self):
        """Select all conversations."""
        self.conversation_table.selectAll()
    
    def _show_statistics(self):
        """Show conversation statistics."""
        # TODO: Implement statistics dialog
        QMessageBox.information(self, "Statistics", "Statistics dialog will be implemented.")
    
    def _cleanup_conversations(self):
        """Show cleanup dialog."""
        # TODO: Implement cleanup dialog
        QMessageBox.information(self, "Cleanup", "Cleanup dialog will be implemented.")
    
    # Utility methods for integration
    def refresh_conversations(self):
        """Refresh the conversation list."""
        self._load_conversations()
    
    def select_conversation(self, conversation_id: str):
        """Programmatically select a conversation."""
        if conversation_id in self.conversation_cards:
            self._on_card_selected(conversation_id)
    
    # Window event handling
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Conversation browser closing")
        event.accept()
    
    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        # Center the window
        if QApplication.primaryScreen():
            screen = QApplication.primaryScreen().geometry()
            window_geometry = self.frameGeometry()
            center_point = screen.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
        
        # Focus the search input
        if self.search_input:
            QTimer.singleShot(100, self.search_input.setFocus)