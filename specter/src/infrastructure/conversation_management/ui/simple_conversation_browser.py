"""
Simple conversation browser for clean conversation management.

Provides a streamlined interface focusing on essential functionality:
- View saved conversations 
- Show current active conversation
- Restore conversation to REPL
- Export conversations
- Clean, minimal design following Specter aesthetics
"""

import logging
import asyncio
from typing import List, Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QFileDialog,
    QProgressBar, QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon

from ..integration.conversation_manager import ConversationManager
from ..models.conversation import Conversation
from ..models.enums import ConversationStatus
from ..services.export_service import ExportService

logger = logging.getLogger("specter.simple_conversation_browser")


class SimpleConversationBrowser(QDialog):
    """
    Clean, simplified conversation management dialog.
    
    Features:
    - Simple table view of conversations
    - Current active conversation highlighted
    - Essential actions: Restore, Export
    - Dark theme consistency with Specter
    """
    
    # Signals
    conversation_restore_requested = pyqtSignal(str)  # conversation_id to restore
    
    def __init__(self, conversation_manager: ConversationManager, current_conversation_id: Optional[str] = None, parent=None):
        """Initialize simple conversation browser."""
        super().__init__(parent)
        
        self.conversation_manager = conversation_manager
        self.current_conversation_id = current_conversation_id
        self.conversations: List[Conversation] = []
        self.selected_conversation_id: Optional[str] = None
        
        # Export service for conversation exports
        self.export_service = ExportService()
        
        # UI components
        self.conversation_table: Optional[QTableWidget] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.restore_btn: Optional[QPushButton] = None
        self.export_btn: Optional[QPushButton] = None
        
        self._init_ui()
        self._apply_dark_theme()
        self._load_conversations()
        
        logger.info("SimpleConversationBrowser initialized")
    
    def _init_ui(self):
        """Initialize the clean user interface."""
        self.setWindowTitle("Conversations - Specter")
        self.setGeometry(300, 200, 800, 600)
        self.setModal(False)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel("Conversation Management")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Current conversation info
        if self.current_conversation_id:
            current_label = QLabel(f"Current Active: {self.current_conversation_id[:8]}...")
            current_label.setStyleSheet("color: #4CAF50; font-style: italic; font-size: 11px;")
            current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(current_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 5px 0;")
        main_layout.addWidget(separator)
        
        # Conversation table
        self.conversation_table = QTableWidget()
        self.conversation_table.setColumnCount(4)
        self.conversation_table.setHorizontalHeaderLabels([
            "Title", "Status", "Messages", "Updated"
        ])
        
        # Configure table for clean appearance
        header = self.conversation_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Status  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Messages
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Updated
        
        self.conversation_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.conversation_table.setAlternatingRowColors(True)
        self.conversation_table.setSortingEnabled(True)
        self.conversation_table.setMinimumHeight(350)
        
        # Connect table selection
        self.conversation_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.conversation_table.itemDoubleClicked.connect(self._restore_selected)
        
        main_layout.addWidget(self.conversation_table, 1)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Restore button
        self.restore_btn = QPushButton("Restore to REPL")
        self.restore_btn.clicked.connect(self._restore_selected)
        self.restore_btn.setEnabled(False)
        self.restore_btn.setMinimumHeight(35)
        button_layout.addWidget(self.restore_btn)
        
        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_selected)
        self.export_btn.setEnabled(False)
        self.export_btn.setMinimumHeight(35)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumHeight(35)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { border-top: 1px solid rgba(255, 255, 255, 0.1); }")
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        main_layout.addWidget(self.status_bar)
    
    def _apply_dark_theme(self):
        """Apply clean dark theme consistent with Specter design."""
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 0.95);
                color: #f0f0f0;
            }
            QLabel {
                color: #f0f0f0;
            }
            QTableWidget {
                background-color: rgba(20, 20, 20, 0.8);
                color: #f0f0f0;
                gridline-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                alternate-background-color: rgba(40, 40, 40, 0.5);
            }
            QTableWidget::item:selected {
                background-color: rgba(76, 175, 80, 0.6);
                color: white;
            }
            QTableWidget::item:hover {
                background-color: rgba(76, 175, 80, 0.3);
            }
            QHeaderView::section {
                background-color: rgba(40, 40, 40, 0.8);
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 8px;
                font-weight: bold;
            }
            QPushButton {
                background-color: rgba(76, 175, 80, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(56, 155, 60, 1.0);
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.5);
                color: rgba(200, 200, 200, 0.5);
            }
            QProgressBar {
                background-color: rgba(100, 100, 100, 0.3);
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 1px;
            }
            QStatusBar {
                color: #cccccc;
                font-size: 10px;
            }
        """)
    
    def _load_conversations(self):
        """Load conversations into the table."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.showMessage("Loading conversations...")
        
        class ConversationLoader(QObject):
            """Background worker for loading conversations."""
            conversations_loaded = pyqtSignal(list)
            
            def __init__(self, manager):
                super().__init__()
                self.manager = manager
            
            def load(self):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        conversations = loop.run_until_complete(
                            self.manager.list_conversations(limit=100)
                        )
                        self.conversations_loaded.emit(conversations)
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Failed to load conversations: {e}")
                    self.conversations_loaded.emit([])
        
        # Create background loader
        self._loader_thread = QThread()
        self._loader = ConversationLoader(self.conversation_manager)
        self._loader.moveToThread(self._loader_thread)
        
        # Connect signals
        self._loader_thread.started.connect(self._loader.load)
        self._loader.conversations_loaded.connect(self._populate_table)
        self._loader.conversations_loaded.connect(self._loader_thread.quit)
        self._loader.conversations_loaded.connect(self._loader.deleteLater)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        
        # Start loading
        self._loader_thread.start()
    
    def _populate_table(self, conversations: List[Conversation]):
        """Populate the conversation table."""
        self.conversations = conversations
        self.conversation_table.setRowCount(len(conversations))
        
        for i, conv in enumerate(conversations):
            # Title - highlight current conversation
            title_text = conv.title
            if conv.id == self.current_conversation_id:
                title_text = f"⭐ {title_text} (ACTIVE)"
            
            title_item = QTableWidgetItem(title_text)
            title_item.setData(Qt.ItemDataRole.UserRole, conv.id)
            
            # Bold font for current conversation
            if conv.id == self.current_conversation_id:
                font = title_item.font()
                font.setBold(True)
                title_item.setFont(font)
                title_item.setToolTip("Currently active conversation in REPL")
            
            self.conversation_table.setItem(i, 0, title_item)
            
            # Status with icon
            status_icons = {
                ConversationStatus.ACTIVE: "🟢",
                ConversationStatus.PINNED: "📌",
                ConversationStatus.ARCHIVED: "📦", 
                ConversationStatus.DELETED: "🗑️"
            }
            status_icon = status_icons.get(conv.status, "⚫")
            
            status_item = QTableWidgetItem(f"{status_icon} {conv.status.value.title()}")
            self.conversation_table.setItem(i, 1, status_item)
            
            # Message count
            msg_count = QTableWidgetItem(str(conv.get_message_count()))
            msg_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.conversation_table.setItem(i, 2, msg_count)
            
            # Updated time (relative)
            updated_text = self._format_relative_time(conv.updated_at)
            updated_item = QTableWidgetItem(updated_text)
            updated_item.setToolTip(conv.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
            self.conversation_table.setItem(i, 3, updated_item)
        
        # Update status
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Loaded {len(conversations)} conversations", 3000)
        
        # Auto-select current conversation if present
        if self.current_conversation_id:
            for i, conv in enumerate(conversations):
                if conv.id == self.current_conversation_id:
                    self.conversation_table.selectRow(i)
                    break
        elif conversations:
            # Otherwise select first row
            self.conversation_table.selectRow(0)
    
    def _format_relative_time(self, timestamp: datetime) -> str:
        """Format timestamp as relative time string."""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago" 
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = self.conversation_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_conversation_id = None
            self.restore_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            return
        
        row = selected_rows[0].row()
        if row < len(self.conversations):
            conversation = self.conversations[row]
            self.selected_conversation_id = conversation.id
            
            # Enable/disable buttons based on selection
            self.restore_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            
            # Update button text if it's the current conversation
            if conversation.id == self.current_conversation_id:
                self.restore_btn.setText("Already Active")
                self.restore_btn.setEnabled(False)
            else:
                self.restore_btn.setText("Restore to REPL")
                self.restore_btn.setEnabled(True)
    
    def _restore_selected(self):
        """Restore selected conversation to REPL."""
        if not self.selected_conversation_id:
            return
        
        # Don't restore if it's already the current conversation
        if self.selected_conversation_id == self.current_conversation_id:
            QMessageBox.information(
                self,
                "Already Active",
                "This conversation is already active in the REPL."
            )
            return
        
        # Emit signal to restore conversation
        logger.info(f"Restoring conversation: {self.selected_conversation_id}")
        self.conversation_restore_requested.emit(self.selected_conversation_id)
        
        # Update UI to reflect the change
        self.current_conversation_id = self.selected_conversation_id
        self._refresh_table_display()
        
        # Show confirmation
        self.status_bar.showMessage("Conversation restored to REPL", 2000)
    
    def _export_selected(self):
        """Export selected conversation."""
        if not self.selected_conversation_id:
            return
        
        # Find the selected conversation
        selected_conv = None
        for conv in self.conversations:
            if conv.id == self.selected_conversation_id:
                selected_conv = conv
                break
        
        if not selected_conv:
            QMessageBox.warning(self, "Export Error", "Selected conversation not found.")
            return
        
        # Choose export format and location
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilters([
            "Text files (*.txt)",
            "JSON files (*.json)",
            "Markdown files (*.md)"
        ])
        
        default_filename = f"{selected_conv.title.replace(' ', '_')}_export"
        file_dialog.selectFile(default_filename)
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                file_path = file_paths[0]
                selected_filter = file_dialog.selectedNameFilter()
                
                # Determine format from filter
                if "JSON" in selected_filter:
                    export_format = "json"
                elif "Markdown" in selected_filter:
                    export_format = "markdown"
                else:
                    export_format = "text"
                
                # Perform export in background
                self._export_conversation(selected_conv, file_path, export_format)
    
    def _export_conversation(self, conversation: Conversation, file_path: str, format_type: str):
        """Export conversation to file."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage(f"Exporting conversation...")
        
        class ExportWorker(QObject):
            """Background worker for exporting conversations."""
            export_completed = pyqtSignal(bool, str)  # success, message
            
            def __init__(self, export_service, conversation, file_path, format_type):
                super().__init__()
                self.export_service = export_service
                self.conversation = conversation
                self.file_path = file_path
                self.format_type = format_type
            
            def export(self):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success = loop.run_until_complete(
                            self.export_service.export_conversation(
                                self.conversation,
                                self.file_path,
                                self.format_type
                            )
                        )
                        if success:
                            self.export_completed.emit(True, f"Exported to {self.file_path}")
                        else:
                            self.export_completed.emit(False, "Export failed")
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Export error: {e}")
                    self.export_completed.emit(False, f"Export error: {str(e)}")
        
        # Create export worker
        self._export_thread = QThread()
        self._export_worker = ExportWorker(
            self.export_service, conversation, file_path, format_type
        )
        self._export_worker.moveToThread(self._export_thread)
        
        # Connect signals
        self._export_thread.started.connect(self._export_worker.export)
        self._export_worker.export_completed.connect(self._on_export_completed)
        self._export_worker.export_completed.connect(self._export_thread.quit)
        self._export_worker.export_completed.connect(self._export_worker.deleteLater)
        self._export_thread.finished.connect(self._export_thread.deleteLater)
        
        # Start export
        self._export_thread.start()
    
    def _on_export_completed(self, success: bool, message: str):
        """Handle export completion."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.showMessage(message, 3000)
            QMessageBox.information(self, "Export Successful", message)
        else:
            self.status_bar.showMessage(f"Export failed: {message}", 5000)
            QMessageBox.warning(self, "Export Failed", message)
    
    def _refresh_table_display(self):
        """Refresh the table display to reflect current state."""
        # Simply repopulate with current data
        self._populate_table(self.conversations)
    
    # Public API methods
    def refresh(self):
        """Refresh the conversation list."""
        self._load_conversations()
    
    def set_current_conversation(self, conversation_id: Optional[str]):
        """Update the current active conversation."""
        self.current_conversation_id = conversation_id
        self._refresh_table_display()
    
    # Window event handling
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Simple conversation browser closing")
        event.accept()
    
    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        
        # Center the window on screen
        if hasattr(self, 'parent') and self.parent():
            # Center relative to parent
            parent_geometry = self.parent().geometry()
            self.move(
                parent_geometry.x() + (parent_geometry.width() - self.width()) // 2,
                parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            )
        else:
            # Center on screen
            from PyQt6.QtWidgets import QApplication
            if QApplication.primaryScreen():
                screen = QApplication.primaryScreen().geometry()
                self.move(
                    (screen.width() - self.width()) // 2,
                    (screen.height() - self.height()) // 2
                )