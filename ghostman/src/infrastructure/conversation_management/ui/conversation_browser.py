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
        
        # Set up context menu
        self.conversation_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conversation_table.customContextMenuRequested.connect(self._show_context_menu)
        
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
    
    def _show_context_menu(self, position):
        """Show context menu for conversation table."""
        if not self.conversation_table.itemAt(position):
            return  # No item at this position
        
        # Get the selected conversation
        current_row = self.conversation_table.currentRow()
        if current_row < 0:
            return
        
        conversation_id_item = self.conversation_table.item(current_row, 0)
        if not conversation_id_item:
            return
        
        conversation_id = conversation_id_item.data(Qt.ItemDataRole.UserRole)
        if not conversation_id:
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        refresh_title_action = QAction("🔄 Refresh Title", self)
        refresh_title_action.triggered.connect(lambda: self._refresh_conversation_title(conversation_id))
        context_menu.addAction(refresh_title_action)
        
        set_title_action = QAction("✏️ Set Custom Title", self)
        set_title_action.triggered.connect(lambda: self._set_custom_title(conversation_id, current_row))
        context_menu.addAction(set_title_action)
        
        # Apply theme-aware menu styling
        self._style_menu(context_menu)
        
        # Show menu at cursor position
        context_menu.exec(self.conversation_table.mapToGlobal(position))
    
    def _style_menu(self, menu):
        """Apply theme-aware styling to QMenu widgets."""
        try:
            # Try to get the global theme manager
            theme_manager = None
            try:
                from ghostman.src.ui.themes.theme_manager import get_theme_manager
                theme_manager = get_theme_manager()
            except (ImportError, AttributeError):
                return
            
            if not theme_manager:
                return
                
            try:
                from ghostman.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                if not THEME_SYSTEM_AVAILABLE:
                    return
            except ImportError:
                return
            
            colors = theme_manager.current_theme
            if colors:
                from ghostman.src.ui.themes.style_templates import StyleTemplates
                menu_style = StyleTemplates.get_menu_style(colors)
                menu.setStyleSheet(menu_style)
                
        except Exception as e:
            # Silently handle errors to avoid breaking functionality
            pass
    
    def _load_selected_conversation(self):
        """Load the selected conversation."""
        if self.selected_conversation_id:
            self.conversation_loaded.emit(self.selected_conversation_id)
            self.close()
    
    def _refresh_conversation_title(self, conversation_id: str):
        """Refresh the conversation title by regenerating it."""
        try:
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_bar.showMessage("Regenerating conversation title...")
            
            # Start async title generation
            self._generate_title_async(conversation_id)
            
        except Exception as e:
            logger.error(f"Failed to refresh conversation title: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh title: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _set_custom_title(self, conversation_id: str, row: int):
        """Set a custom title for the conversation."""
        try:
            # Get current title
            current_title_item = self.conversation_table.item(row, 0)
            current_title = current_title_item.text() if current_title_item else ""
            
            # Show input dialog
            from PyQt6.QtWidgets import QInputDialog
            new_title, ok = QInputDialog.getText(
                self, 
                "Set Conversation Title",
                "Enter new title:", 
                QLineEdit.EchoMode.Normal,
                current_title
            )
            
            if ok and new_title.strip():
                new_title = new_title.strip()
                
                # Update title in database
                self._update_title_async(conversation_id, new_title, row)
                
        except Exception as e:
            logger.error(f"Failed to set custom title: {e}")
            QMessageBox.warning(self, "Error", f"Failed to set title: {str(e)}")
    
    def _generate_title_async(self, conversation_id: str):
        """Generate title asynchronously."""
        def on_complete():
            try:
                # Use the conversation manager's title generation service
                if hasattr(self.conversation_manager, 'conversation_service'):
                    # Create a simple async runner
                    async def generate_and_update():
                        try:
                            # Generate new title
                            new_title = await self.conversation_manager.conversation_service.generate_conversation_title(conversation_id)
                            
                            if new_title:
                                # Update title in database
                                await self.conversation_manager.conversation_service.update_conversation_title(conversation_id, new_title)
                                
                                # Update UI on main thread
                                QTimer.singleShot(0, lambda: self._update_ui_after_title_change(conversation_id, new_title))
                            else:
                                QTimer.singleShot(0, lambda: self._show_title_generation_failed())
                                
                        except Exception as e:
                            logger.error(f"Title generation failed: {e}")
                            QTimer.singleShot(0, lambda: self._show_title_generation_failed(str(e)))
                    
                    # Run async operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(generate_and_update())
                    finally:
                        loop.close()
                else:
                    QTimer.singleShot(0, lambda: self._show_title_generation_failed("Title generation not available"))
                    
            except Exception as e:
                logger.error(f"Async title generation error: {e}")
                QTimer.singleShot(0, lambda: self._show_title_generation_failed(str(e)))
        
        # Run in background
        QTimer.singleShot(100, on_complete)
    
    def _update_title_async(self, conversation_id: str, new_title: str, row: int):
        """Update title asynchronously."""
        def on_complete():
            try:
                if hasattr(self.conversation_manager, 'conversation_service'):
                    # Create async runner
                    async def update_title():
                        try:
                            await self.conversation_manager.conversation_service.update_conversation_title(conversation_id, new_title)
                            
                            # Update UI on main thread
                            QTimer.singleShot(0, lambda: self._update_table_title(row, new_title))
                            
                        except Exception as e:
                            logger.error(f"Title update failed: {e}")
                            QTimer.singleShot(0, lambda: self._show_title_update_failed(str(e)))
                    
                    # Run async operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(update_title())
                    finally:
                        loop.close()
                else:
                    QTimer.singleShot(0, lambda: self._show_title_update_failed("Title update not available"))
                    
            except Exception as e:
                logger.error(f"Async title update error: {e}")
                QTimer.singleShot(0, lambda: self._show_title_update_failed(str(e)))
        
        # Run in background
        QTimer.singleShot(100, on_complete)
    
    def _update_ui_after_title_change(self, conversation_id: str, new_title: str):
        """Update UI after title has been changed."""
        try:
            # Find the row with this conversation ID
            for row in range(self.conversation_table.rowCount()):
                item = self.conversation_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == conversation_id:
                    item.setText(new_title)
                    break
            
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"Title updated successfully", 3000)
            
        except Exception as e:
            logger.error(f"Failed to update UI after title change: {e}")
            self.progress_bar.setVisible(False)
    
    def _update_table_title(self, row: int, new_title: str):
        """Update the title in the table at the specified row."""
        try:
            title_item = self.conversation_table.item(row, 0)
            if title_item:
                title_item.setText(new_title)
            
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"Title set successfully", 3000)
            
        except Exception as e:
            logger.error(f"Failed to update table title: {e}")
            self.progress_bar.setVisible(False)
    
    def _show_title_generation_failed(self, error_msg: str = None):
        """Show error message when title generation fails."""
        self.progress_bar.setVisible(False)
        msg = f"Failed to generate title: {error_msg}" if error_msg else "Failed to generate title"
        self.status_bar.showMessage(msg, 5000)
        QMessageBox.warning(self, "Title Generation Failed", msg)
    
    def _show_title_update_failed(self, error_msg: str):
        """Show error message when title update fails."""
        self.progress_bar.setVisible(False)
        msg = f"Failed to update title: {error_msg}"
        self.status_bar.showMessage(msg, 5000)
        QMessageBox.warning(self, "Title Update Failed", msg)
    
    def _search_conversations(self):
        """Search conversations."""
        search_text = self.search_input.text().strip()
        if not search_text:
            # No search text - reload all with current filter
            filter_text = self.filter_combo.currentText() if self.filter_combo else "All"
            filtered = self._apply_filter(self.conversations, filter_text)
            self._populate_filtered_table(filtered)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage(f"Searching for: {search_text}")

        # Apply current filter first
        filter_text = self.filter_combo.currentText() if self.filter_combo else "All"
        filtered = self._apply_filter(self.conversations, filter_text)

        # Then apply search
        results = self._apply_search(filtered, search_text)

        # Then apply current sort
        sort_text = self.sort_combo.currentText() if self.sort_combo else "Updated (Newest)"
        results = self._apply_sort(results, sort_text)

        self._populate_filtered_table(results)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Search completed: {len(results)} results", 3000)
    
    def _filter_changed(self):
        """Handle filter change."""
        filter_text = self.filter_combo.currentText()
        logger.info(f"Filter changed to: {filter_text}")

        # Get the current search text if any
        search_text = self.search_input.text().strip() if self.search_input else ""

        # Re-populate table with filtered results
        filtered_conversations = self._apply_filter(self.conversations, filter_text)

        # Apply search if there's search text
        if search_text:
            filtered_conversations = self._apply_search(filtered_conversations, search_text)

        self._populate_filtered_table(filtered_conversations)

    def _sort_changed(self):
        """Handle sort change."""
        sort_text = self.sort_combo.currentText()
        logger.info(f"Sort changed to: {sort_text}")

        # Get current filtered conversations (from visible table rows)
        current_conversations = self._get_visible_conversations()

        # Sort the conversations
        sorted_conversations = self._apply_sort(current_conversations, sort_text)

        # Re-populate table with sorted results
        self._populate_filtered_table(sorted_conversations)

    def _apply_filter(self, conversations: List, filter_text: str) -> List:
        """Apply status filter to conversations."""
        if filter_text == "All":
            return conversations

        filtered = []
        for conv in conversations:
            status = conv.status.value.lower()

            if filter_text == "Active" and status == "active":
                filtered.append(conv)
            elif filter_text == "Pinned" and status == "pinned":
                filtered.append(conv)
            elif filter_text == "Archived" and status == "archived":
                filtered.append(conv)
            elif filter_text == "Deleted" and status == "deleted":
                filtered.append(conv)

        return filtered

    def _apply_search(self, conversations: List, search_text: str) -> List:
        """Filter conversations by search text."""
        search_lower = search_text.lower()
        filtered = []

        for conv in conversations:
            # Search in title
            if search_lower in conv.title.lower():
                filtered.append(conv)
                continue

            # Search in tags
            if hasattr(conv, 'metadata') and conv.metadata and hasattr(conv.metadata, 'tags'):
                if any(search_lower in tag.lower() for tag in conv.metadata.tags):
                    filtered.append(conv)
                    continue

            # Search in messages (first 100 chars of each message)
            if hasattr(conv, 'messages') and conv.messages:
                for msg in conv.messages:
                    if search_lower in msg.content[:100].lower():
                        filtered.append(conv)
                        break

        return filtered

    def _apply_sort(self, conversations: List, sort_text: str) -> List:
        """Sort conversations by the selected option."""
        if not conversations:
            return conversations

        sorted_convs = conversations.copy()

        if sort_text == "Updated (Newest)":
            sorted_convs.sort(key=lambda c: c.updated_at, reverse=True)
        elif sort_text == "Updated (Oldest)":
            sorted_convs.sort(key=lambda c: c.updated_at, reverse=False)
        elif sort_text == "Created (Newest)":
            sorted_convs.sort(key=lambda c: c.created_at, reverse=True)
        elif sort_text == "Created (Oldest)":
            sorted_convs.sort(key=lambda c: c.created_at, reverse=False)
        elif sort_text == "Title (A-Z)":
            sorted_convs.sort(key=lambda c: c.title.lower())
        elif sort_text == "Title (Z-A)":
            sorted_convs.sort(key=lambda c: c.title.lower(), reverse=True)

        return sorted_convs

    def _get_visible_conversations(self) -> List:
        """Get currently visible conversations from the table."""
        visible = []
        for row in range(self.conversation_table.rowCount()):
            if not self.conversation_table.isRowHidden(row):
                item = self.conversation_table.item(row, 0)
                if item:
                    conv_id = item.data(Qt.ItemDataRole.UserRole)
                    # Find conversation in self.conversations
                    for conv in self.conversations:
                        if conv.id == conv_id:
                            visible.append(conv)
                            break
        return visible

    def _populate_filtered_table(self, conversations: List):
        """Populate table with filtered/sorted conversations."""
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
            }.get(conv.status.value.lower(), "❓")
            status_item = QTableWidgetItem(f"{status_icon} {conv.status.value.title()}")
            self.conversation_table.setItem(i, 1, status_item)

            # Message count
            msg_count = len(conv.messages) if hasattr(conv, 'messages') and conv.messages else 0
            count_item = QTableWidgetItem(str(msg_count))
            self.conversation_table.setItem(i, 2, count_item)

            # Created date
            created_item = QTableWidgetItem(conv.created_at.strftime("%Y-%m-%d %H:%M"))
            self.conversation_table.setItem(i, 3, created_item)

            # Updated date
            updated_item = QTableWidgetItem(conv.updated_at.strftime("%Y-%m-%d %H:%M"))
            self.conversation_table.setItem(i, 4, updated_item)

            # Tags
            tags = ""
            if hasattr(conv, 'metadata') and conv.metadata and hasattr(conv.metadata, 'tags'):
                tags = ", ".join(conv.metadata.tags[:3])  # Show first 3 tags
                if len(conv.metadata.tags) > 3:
                    tags += "..."
            tags_item = QTableWidgetItem(tags)
            self.conversation_table.setItem(i, 5, tags_item)

        count_text = f"{len(conversations)} conversation(s)"
        if len(conversations) != len(self.conversations):
            count_text += f" (filtered from {len(self.conversations)})"
        self.status_bar.showMessage(count_text)
    
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