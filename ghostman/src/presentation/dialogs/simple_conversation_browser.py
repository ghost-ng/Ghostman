"""
Simple conversation browser dialog for Ghostman.

Clean, uncluttered interface for browsing, restoring, and exporting conversations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QProgressBar,
    QFileDialog, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt6.QtGui import QFont

# Import conversation management
try:
    from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
    from ...infrastructure.conversation_management.models.conversation import Conversation
    from ...infrastructure.conversation_management.services.export_service import ExportService
    from ...infrastructure.conversation_management.models.enums import ConversationStatus, ExportFormat
except ImportError:
    ConversationManager = None
    Conversation = None
    ExportService = None
    ConversationStatus = None
    ExportFormat = None

logger = logging.getLogger("ghostman.simple_conversation_browser")


class ConversationLoader(QObject):
    """Background conversation loader."""
    
    conversations_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, conversation_manager: ConversationManager):
        super().__init__()
        self.conversation_manager = conversation_manager
    
    def load_conversations(self):
        """Load conversations in background."""
        try:
            # Get all conversations including current one
            conversations = []
            
            # Create new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Get recent conversations from database
                recent = loop.run_until_complete(
                    self.conversation_manager.conversation_service.get_recent_conversations(limit=100)
                )
                conversations.extend(recent)
                
                # Note: Current active conversation is already included in recent conversations
                
                self.conversations_loaded.emit(conversations)
                
            finally:
                loop.close()
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class SimpleConversationBrowser(QDialog):
    """
    Simple, clean conversation browser dialog.
    
    Features:
    - List conversations from SQLite database
    - Show current conversation with highlight
    - Restore conversation to REPL
    - Export conversations in various formats
    - Minimal, uncluttered interface
    """
    
    conversation_restore_requested = pyqtSignal(str)  # conversation_id
    
    def __init__(self, parent=None, conversation_manager=None):
        super().__init__(parent)
        self.conversation_manager: Optional[ConversationManager] = conversation_manager
        self.export_service: Optional[ExportService] = None
        self.conversations: List[Conversation] = []
        self.current_conversation_id: Optional[str] = None
        
        self._init_ui()
        self._init_conversation_manager()
        self._apply_styles()
        
        logger.info("Simple conversation browser initialized")
    
    def _init_ui(self):
        """Initialize clean, simple UI."""
        self.setWindowTitle("Conversations")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Saved Conversations")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_conversations)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Conversations table
        self.conversations_table = QTableWidget()
        self.conversations_table.setColumnCount(4)
        self.conversations_table.setHorizontalHeaderLabels([
            "Title", "Status", "Messages", "Updated"
        ])
        
        # Configure table
        header = self.conversations_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(0, 300)  # Title column
        header.resizeSection(1, 80)   # Status column  
        header.resizeSection(2, 80)   # Messages column
        
        self.conversations_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.conversations_table.setAlternatingRowColors(True)
        self.conversations_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.conversations_table, 1)
        
        # Progress bar for background operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        # Restore button
        self.restore_btn = QPushButton("Restore to REPL")
        self.restore_btn.clicked.connect(self._on_restore_clicked)
        self.restore_btn.setEnabled(False)
        button_layout.addWidget(self.restore_btn)
        
        # Export button
        self.export_btn = QPushButton("Export...")
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Connect table selection
        self.conversations_table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
    
    def _init_conversation_manager(self):
        """Initialize conversation management."""
        if not ConversationManager:
            self.status_label.setText("Conversation management not available")
            return
        
        # Use provided conversation manager or create a new one
        if self.conversation_manager:
            logger.info("Using provided conversation manager")
            # Pass the repository to the export service
            self.export_service = ExportService(self.conversation_manager.repository)
            self._load_conversations()
            return
        
        try:
            logger.info("Creating new conversation manager for browser")
            self.conversation_manager = ConversationManager()
            if self.conversation_manager.initialize():
                # Pass the repository to the export service
                self.export_service = ExportService(self.conversation_manager.repository)
                self._load_conversations()
            else:
                self.status_label.setText("Failed to initialize conversation manager")
                
        except Exception as e:
            logger.error(f"Failed to initialize conversation manager: {e}")
            self.status_label.setText(f"Error: {e}")
    
    def _load_conversations(self):
        """Load conversations from database."""
        if not self.conversation_manager:
            return
        
        self.status_label.setText("Loading conversations...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate
        
        # Load in background thread
        self.loader_thread = QThread()
        self.loader = ConversationLoader(self.conversation_manager)
        self.loader.moveToThread(self.loader_thread)
        
        # Connect signals
        self.loader.conversations_loaded.connect(self._on_conversations_loaded)
        self.loader.error_occurred.connect(self._on_load_error)
        self.loader_thread.started.connect(self.loader.load_conversations)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        
        self.loader_thread.start()
    
    def _on_conversations_loaded(self, conversations: List[Conversation]):
        """Handle conversations loaded."""
        self.conversations = conversations
        self._populate_table()
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Loaded {len(conversations)} conversations")
        
        # Clean up thread
        self.loader_thread.quit()
        self.loader_thread.wait()
    
    def _on_load_error(self, error: str):
        """Handle loading error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        
        QMessageBox.warning(self, "Error", f"Failed to load conversations:\n{error}")
        
        # Clean up thread
        self.loader_thread.quit()
        self.loader_thread.wait()
    
    def _populate_table(self):
        """Populate conversations table."""
        self.conversations_table.setRowCount(len(self.conversations))
        
        for row, conversation in enumerate(self.conversations):
            # Title (with current indicator)
            title = conversation.title
            if self._is_current_conversation(conversation):
                title = f"⭐ {title}"
            
            title_item = QTableWidgetItem(title)
            if self._is_current_conversation(conversation):
                title_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.conversations_table.setItem(row, 0, title_item)
            
            # Status
            status_text = self._get_status_text(conversation.status)
            status_item = QTableWidgetItem(status_text)
            self.conversations_table.setItem(row, 1, status_item)
            
            # Message count
            count_item = QTableWidgetItem(str(conversation.get_message_count()))
            self.conversations_table.setItem(row, 2, count_item)
            
            # Updated time
            updated_text = self._format_datetime(conversation.updated_at)
            updated_item = QTableWidgetItem(updated_text)
            self.conversations_table.setItem(row, 3, updated_item)
    
    def _is_current_conversation(self, conversation: Conversation) -> bool:
        """Check if this is the current active conversation."""
        if not self.conversation_manager:
            return False
        
        # For now, no specific current conversation highlighting
        return False
    
    def _get_status_text(self, status) -> str:
        """Get human-readable status text."""
        if not ConversationStatus:
            return str(status)
        
        status_map = {
            ConversationStatus.ACTIVE: "Active",
            ConversationStatus.PINNED: "Pinned", 
            ConversationStatus.ARCHIVED: "Archived"
        }
        return status_map.get(status, str(status))
    
    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display."""
        if not isinstance(dt, datetime):
            return str(dt)
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            return dt.strftime("%H:%M")
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return dt.strftime("%a %H:%M")
        else:
            return dt.strftime("%m/%d/%y")
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = self.conversations_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        self.restore_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
    
    def _on_restore_clicked(self):
        """Handle restore button click."""
        selected_rows = self.conversations_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.conversations):
            return
        
        conversation = self.conversations[row]
        
        # Confirm restore
        reply = QMessageBox.question(
            self,
            "Restore Conversation",
            f"Restore '{conversation.title}' to REPL?\n\n"
            "This will replace the current conversation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.conversation_restore_requested.emit(conversation.id)
            self.status_label.setText(f"Restored: {conversation.title}")
            logger.info(f"Conversation restore requested: {conversation.id}")
    
    def _on_export_clicked(self):
        """Handle export button click."""
        selected_rows = self.conversations_table.selectionModel().selectedRows()
        if not selected_rows or not self.export_service:
            return
        
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.conversations):
            return
        
        conversation = self.conversations[row]
        
        # Show export format dialog
        self._show_export_dialog(conversation)
    
    def _show_export_dialog(self, conversation: Conversation):
        """Show export format selection dialog."""
        # Simple export options dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Format")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"Export '{conversation.title}' as:"))
        
        # Format buttons
        txt_btn = QPushButton("Plain Text (.txt)")
        txt_btn.clicked.connect(lambda: self._export_conversation(conversation, ExportFormat.TXT))
        txt_btn.clicked.connect(dialog.accept)
        layout.addWidget(txt_btn)
        
        json_btn = QPushButton("JSON (.json)")
        json_btn.clicked.connect(lambda: self._export_conversation(conversation, ExportFormat.JSON))
        json_btn.clicked.connect(dialog.accept)
        layout.addWidget(json_btn)
        
        md_btn = QPushButton("Markdown (.md)")
        md_btn.clicked.connect(lambda: self._export_conversation(conversation, ExportFormat.MARKDOWN))
        md_btn.clicked.connect(dialog.accept)
        layout.addWidget(md_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.exec()
    
    def _export_conversation(self, conversation: Conversation, format: ExportFormat):
        """Export conversation in specified format."""
        try:
            # Get file extension
            ext_map = {
                ExportFormat.TXT: "txt",
                ExportFormat.JSON: "json", 
                ExportFormat.MARKDOWN: "md"
            }
            ext = ext_map.get(format, "txt")
            
            # Show save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Conversation",
                f"{conversation.title}.{ext}",
                f"{format.value.upper()} files (*.{ext})"
            )
            
            if not filename:
                return
            
            # Export conversation using async properly
            self.status_label.setText("Exporting...")
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # The export_service.export_conversation expects (conversation, file_path, format)
            success = loop.run_until_complete(
                self.export_service.export_conversation(
                    conversation,  # Pass the conversation object
                    filename,      # File path
                    format.value   # Format as string
                )
            )
            
            if success:
                self.status_label.setText(f"Exported to: {filename}")
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Conversation exported successfully to:\n{filename}"
                )
            else:
                self.status_label.setText("Export failed")
                QMessageBox.warning(self, "Export Error", "Failed to export conversation")
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.status_label.setText(f"Export error: {e}")
            QMessageBox.warning(self, "Export Error", f"Export failed:\n{e}")
    
    def _apply_styles(self):
        """Apply dark theme styles."""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border-color: #444444;
            }
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                color: #ffffff;
                gridline-color: #444444;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #ffffff;
                padding: 6px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2a2a2a;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
    
    def set_current_conversation(self, conversation_id: Optional[str]):
        """Set the current conversation ID for highlighting."""
        self.current_conversation_id = conversation_id
        if hasattr(self, 'conversations_table'):
            self._populate_table()