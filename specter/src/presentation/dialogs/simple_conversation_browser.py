"""
Simple conversation browser dialog for Specter.

Clean, uncluttered interface for browsing, restoring, and exporting conversations.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QProgressBar,
    QFileDialog, QWidget, QAbstractItemView, QLineEdit, QCheckBox,
    QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt6.QtGui import QFont, QAction

# Import conversation management
try:
    from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
    from ...infrastructure.conversation_management.models.conversation import Conversation
    from ...infrastructure.conversation_management.services.export_service import ExportService
    from ...infrastructure.conversation_management.models.enums import ConversationStatus, ExportFormat
    from ...infrastructure.conversation_management.models.search import SearchQuery, SearchResults, SearchResult
except ImportError:
    ConversationManager = None
    Conversation = None
    ExportService = None
    ConversationStatus = None
    ExportFormat = None
    SearchQuery = None
    SearchResults = None
    SearchResult = None

# Import theme system
try:
    from ...ui.themes.theme_manager import get_theme_manager
    from ...ui.themes.style_templates import StyleTemplates
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    get_theme_manager = None
    StyleTemplates = None
    THEME_SYSTEM_AVAILABLE = False

logger = logging.getLogger("specter.simple_conversation_browser")


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
            # Get all conversations except deleted ones
            conversations = []
            
            # Create new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Get non-deleted conversations from database using service-level filtering
                conversations = loop.run_until_complete(
                    self.conversation_manager.list_conversations(limit=100, include_deleted=False)
                )
                
                logger.debug(f"Loaded {len(conversations)} active conversations (deleted conversations excluded by service)")
                
                self.conversations_loaded.emit(conversations)
                
            finally:
                loop.close()
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ConversationSearchWorker(QObject):
    """Background conversation search worker."""
    
    search_completed = pyqtSignal(object)  # SearchResults
    search_error = pyqtSignal(str)
    
    def __init__(self, conversation_manager: ConversationManager, search_query: str, use_regex: bool = False, case_sensitive: bool = False):
        super().__init__()
        self.conversation_manager = conversation_manager
        self.search_query = search_query
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
    
    def perform_search(self):
        """Perform search in background thread."""
        try:
            if not SearchQuery:
                self.search_error.emit("Search functionality not available")
                return
            
            # Create new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if self.use_regex:
                    # Perform regex search across all conversations
                    search_results = loop.run_until_complete(
                        self._perform_regex_search()
                    )
                else:
                    # Create search query - simple text search with reasonable limit
                    query = SearchQuery.create_simple_text_search(
                        text=self.search_query.strip(),
                        limit=50
                    )
                    
                    # Perform search using conversation service
                    search_results = loop.run_until_complete(
                        self.conversation_manager.conversation_service.search_conversations(query)
                    )
                
                logger.debug(f"Search completed: {len(search_results.results)} results for '{self.search_query}' (regex: {self.use_regex})")
                self.search_completed.emit(search_results)
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.search_error.emit(str(e))
    
    async def _perform_regex_search(self):
        """Perform regex search across all conversations."""
        try:
            import re
            
            # Validate regex pattern
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(self.search_query.strip(), flags)
            except re.error as e:
                raise Exception(f"Invalid regex pattern: {e}")
            
            # Get all conversations
            all_conversations = await self.conversation_manager.list_conversations(limit=1000)
            
            # Search through conversations
            matching_results = []
            
            for conversation in all_conversations:
                match_found = False
                match_count = 0
                
                # Search in title
                if pattern.search(conversation.title):
                    match_found = True
                    match_count += len(pattern.findall(conversation.title))
                
                # Load conversation with messages for content search
                if not match_found:
                    full_conversation = await self.conversation_manager.get_conversation(
                        conversation.id, include_messages=True
                    )
                    
                    if full_conversation and full_conversation.messages:
                        # Search in message content
                        for message in full_conversation.messages:
                            if pattern.search(message.content):
                                match_found = True
                                match_count += len(pattern.findall(message.content))
                
                if match_found:
                    # Create search result
                    result = SearchResult(
                        conversation_id=conversation.id,
                        title=conversation.title,
                        match_count=match_count,
                        relevance_score=match_count / len(conversation.title + " " + (conversation.summary or "")),
                        matched_fields=["title", "content"] if match_count > 0 else ["title"]
                    )
                    matching_results.append(result)
            
            # Sort by relevance
            matching_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
            
            # Create search results object
            from ...infrastructure.conversation_management.models.search import SearchResults
            return SearchResults(
                results=matching_results,
                total_count=len(matching_results),
                query_time_ms=0.0,  # We're not tracking time for regex search
                offset=0,
                limit=len(matching_results)
            )
            
        except Exception as e:
            logger.error(f"Regex search failed: {e}")
            raise


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
    
    def __init__(self, parent=None, conversation_manager=None, theme_manager=None):
        super().__init__(parent)
        self.conversation_manager: Optional[ConversationManager] = conversation_manager
        self.export_service: Optional[ExportService] = None
        self.conversations: List[Conversation] = []
        self.current_conversation_id: Optional[str] = None
        
        # Initialize theme manager
        if theme_manager is None and THEME_SYSTEM_AVAILABLE:
            self.theme_manager = get_theme_manager()
        else:
            self.theme_manager = theme_manager
        
        self._init_ui()
        self._init_conversation_manager()
        self._apply_styles()

        # Connect to theme changes for live updates
        if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
            self.theme_manager.theme_changed.connect(lambda _: self._apply_styles())

        logger.info("Simple conversation browser initialized")
    
    def _init_ui(self):
        """Initialize clean, simple UI."""
        self.setWindowTitle("Conversations")
        self.setModal(False)  # Allow interaction with main app while browser is open
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
        
        # Search bar
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Search:")
        search_label.setMinimumWidth(50)
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search conversations by title, content, or tags...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)
        
        # Search button  
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._perform_search)
        search_layout.addWidget(search_btn)
        
        # Clear search button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # Search options
        options_layout = QHBoxLayout()
        
        # Regex checkbox
        self.regex_checkbox = QCheckBox("Use Regular Expressions")
        self.regex_checkbox.setToolTip("Enable regex pattern matching for advanced search")
        options_layout.addWidget(self.regex_checkbox)
        
        # Case sensitive checkbox
        self.case_checkbox = QCheckBox("Case Sensitive")
        self.case_checkbox.setToolTip("Match case exactly")
        options_layout.addWidget(self.case_checkbox)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Search state management
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.search_debounce_ms = 500  # 500ms debounce
        self.current_search_query = ""
        self.is_searching = False
        
        # Conversations table
        self.conversations_table = QTableWidget()
        self.conversations_table.setColumnCount(7)
        self.conversations_table.setHorizontalHeaderLabels([
            "☑", "Title", "Status", "Messages", "Files", "Collections", "Updated"
        ])

        # Configure table
        header = self.conversations_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(0, 40)   # Checkbox column
        header.resizeSection(1, 280)  # Title column
        header.resizeSection(2, 80)   # Status column
        header.resizeSection(3, 80)   # Messages column
        header.resizeSection(4, 90)   # Files column
        header.resizeSection(5, 120)  # Collections column

        # Enable clickable column headers for sorting
        self.conversations_table.setSortingEnabled(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)
        self._current_sort_column = 6  # Default sort by Updated
        self._current_sort_order = Qt.SortOrder.DescendingOrder

        self.conversations_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.conversations_table.setAlternatingRowColors(True)
        self.conversations_table.verticalHeader().setVisible(False)

        # Make table read-only - disable all editing
        self.conversations_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Set up context menu
        self.conversations_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conversations_table.customContextMenuRequested.connect(self._show_context_menu)
        
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
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.clicked.connect(self._on_restore_clicked)
        self.restore_btn.setEnabled(False)
        button_layout.addWidget(self.restore_btn)
        
        # Export button
        self.export_btn = QPushButton("Export...")
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        # Delete Selected button (handles both single and multiple selections)
        self.mass_delete_btn = QPushButton("Delete Selected")
        self.mass_delete_btn.clicked.connect(self._on_mass_delete_clicked)
        self.mass_delete_btn.setEnabled(False)
        self.mass_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: 1px solid #b71c1c;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #f44336;
                border-color: #c62828;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border-color: #444444;
            }
        """)
        button_layout.addWidget(self.mass_delete_btn)
        
        # Select all button
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._on_select_all_clicked)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: 1px solid #45a049;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
                border-color: #3d8b40;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.select_all_btn)
        
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
    
    def _safe_run_async(self, coro):
        """Safely run an async operation using async manager pattern."""
        try:
            # Use the same pattern as the fixed REPL widget
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def run_async_task():
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro)
                        result_queue.put(('success', result))
                    finally:
                        new_loop.close()
                except Exception as e:
                    result_queue.put(('error', str(e)))
            
            # Run in separate thread to avoid event loop conflicts
            thread = threading.Thread(target=run_async_task, daemon=True)
            thread.start()
            thread.join(timeout=10.0)  # 10 second timeout
            
            if not result_queue.empty():
                status, result = result_queue.get()
                if status == 'success':
                    return result
                else:
                    logger.debug(f"Async operation failed: {result}")
                    return None
            else:
                logger.debug("Async operation timed out")
                return None
                
        except Exception as e:
            logger.debug(f"Safe async run failed: {e}")
            return None
    
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
    
    def _on_header_clicked(self, logical_index: int):
        """Handle column header click for sorting."""
        if logical_index == 0:
            return  # Don't sort by checkbox column

        # Toggle sort order if clicking the same column
        if logical_index == self._current_sort_column:
            if self._current_sort_order == Qt.SortOrder.AscendingOrder:
                self._current_sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._current_sort_order = Qt.SortOrder.AscendingOrder
        else:
            self._current_sort_column = logical_index
            self._current_sort_order = Qt.SortOrder.AscendingOrder

        self.conversations_table.sortItems(logical_index, self._current_sort_order)

    def _populate_table(self):
        """Populate conversations table with optional search highlighting and batch file loading."""
        # Disable sorting while populating to avoid re-sort on each row insert
        self.conversations_table.setSortingEnabled(False)
        self.conversations_table.setRowCount(len(self.conversations))

        # Batch load file info for all conversations to solve N+1 query problem
        file_info = {}
        collection_tags = {}
        if self.conversations and self.conversation_manager:
            conversation_ids = [conv.id for conv in self.conversations]
            try:
                file_info = self._safe_run_async(
                    self.conversation_manager.get_conversations_with_file_info(conversation_ids)
                )
                if file_info is None:
                    file_info = {}
                logger.debug(f"Batch loaded file info for {len(file_info)} conversations")
            except Exception as e:
                logger.error(f"Failed to batch load file info: {e}")
                file_info = {}

            # Batch load collection tags for all conversations
            try:
                collection_tags = self._batch_load_collection_tags(conversation_ids)
                logger.debug(f"Batch loaded collection tags for {len(collection_tags)} conversations")
            except Exception as e:
                logger.error(f"Failed to batch load collection tags: {e}")
                collection_tags = {}
        
        for row, conversation in enumerate(self.conversations):
            # Checkbox column (column 0)
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self._on_checkbox_changed)
            self.conversations_table.setCellWidget(row, 0, checkbox)
            
            # Title (with current indicator and search highlighting) - column 1
            title = conversation.title
            if self._is_current_conversation(conversation):
                title = f"⭐ {title}"
            
            # Apply search highlighting if we have an active search
            if self.current_search_query and len(self.current_search_query) >= 2:
                title = self._highlight_search_text(title, self.current_search_query)
            
            title_item = QTableWidgetItem(title)
            if self._is_current_conversation(conversation):
                title_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            
            # Add visual indicator for search results
            if self.current_search_query:
                title_item.setToolTip(f"Search result for: {self.current_search_query}")
            
            self.conversations_table.setItem(row, 1, title_item)
            
            # Status - column 2
            status_text = self._get_status_text(conversation.status)
            status_item = QTableWidgetItem(status_text)
            self.conversations_table.setItem(row, 2, status_item)
            
            # Message count - column 3
            count_item = QTableWidgetItem(str(conversation.get_message_count()))
            self.conversations_table.setItem(row, 3, count_item)
            
            # Files - column 4 (using batch-loaded file info)
            files_text = self._get_files_text_from_info(conversation.id, file_info)
            files_item = QTableWidgetItem(files_text)
            # Set detailed tooltip with file names if available
            files = file_info.get(conversation.id, [])
            if files:
                tooltip_lines = ["Files attached to this conversation:"]
                for f in files[:5]:  # Show first 5 files in tooltip
                    status = f.get('processing_status', '')
                    status_text = f" ({status})" if status and status != 'completed' else ""
                    tooltip_lines.append(f"• {f['filename']}{status_text}")
                if len(files) > 5:
                    tooltip_lines.append(f"... and {len(files) - 5} more")
                files_item.setToolTip("\n".join(tooltip_lines))
            else:
                files_item.setToolTip("No files attached to this conversation")
            self.conversations_table.setItem(row, 4, files_item)

            # Collections - column 5
            tags = collection_tags.get(conversation.id, [])
            collections_text = ", ".join(tags) if tags else "—"
            collections_item = QTableWidgetItem(collections_text)
            if tags:
                collections_item.setToolTip(f"Collection tags used: {', '.join(tags)}")
            else:
                collections_item.setToolTip("No collection tags used")
            self.conversations_table.setItem(row, 5, collections_item)

            # Updated time - column 6
            updated_text = self._format_datetime(conversation.updated_at)
            updated_item = QTableWidgetItem(updated_text)
            self.conversations_table.setItem(row, 6, updated_item)

        # Re-enable sorting and apply default sort
        self.conversations_table.setSortingEnabled(True)
        self.conversations_table.sortItems(self._current_sort_column, self._current_sort_order)

    def _is_current_conversation(self, conversation: Conversation) -> bool:
        """Check if this is the current active conversation."""
        if not self.conversation_manager:
            return False
        
        # For now, no specific current conversation highlighting
        return False
    
    def _get_files_text(self, conversation_id: str) -> str:
        """Get files count text for a conversation."""
        try:
            if not self.conversation_manager:
                return "—"

            # Get conversation service
            conv_service = self.conversation_manager.conversation_service
            if not conv_service:
                return "—"

            # Safely get files count for this conversation - including all processing statuses
            files = self._safe_run_async(conv_service.get_conversation_files(conversation_id, enabled_only=False))

            if files is None:
                return "—"

            # Count files by status
            total_files = len(files)
            if total_files == 0:
                return "—"

            # Count completed files specifically
            completed_files = sum(1 for f in files if f.get('processing_status') == 'completed')
            processing_files = sum(1 for f in files if f.get('processing_status') in ['queued', 'processing'])
            failed_files = sum(1 for f in files if f.get('processing_status') == 'failed')

            # Create informative display text
            if total_files == 1:
                file_info = files[0]
                status = file_info.get('processing_status', 'unknown')
                if status == 'completed':
                    return "1 file"
                elif status in ['queued', 'processing']:
                    return "1 file (processing)"
                elif status == 'failed':
                    return "1 file (failed)"
                else:
                    return "1 file"
            else:
                # Multiple files - show summary
                if completed_files == total_files:
                    return f"{total_files} files"
                elif processing_files > 0:
                    return f"{total_files} files ({processing_files} processing)"
                elif failed_files > 0:
                    if completed_files > 0:
                        return f"{total_files} files ({failed_files} failed)"
                    else:
                        return f"{total_files} files (failed)"
                else:
                    return f"{total_files} files"

        except Exception as e:
            logger.debug(f"Error getting files for {conversation_id}: {e}")
            return "—"
    
    def _batch_load_collection_tags(self, conversation_ids: List[str]) -> Dict[str, List[str]]:
        """Batch load collection tags for multiple conversations."""
        try:
            from ...infrastructure.conversation_management.repositories.database import DatabaseManager
            from ...infrastructure.conversation_management.models.database_models import ConversationFileModel
            from sqlalchemy import func

            db_manager = DatabaseManager()
            with db_manager.get_session() as session:
                # Query for all collection tags grouped by conversation_id
                results = session.query(
                    ConversationFileModel.conversation_id,
                    func.group_concat(func.distinct(ConversationFileModel.collection_tag)).label('tags')
                ).filter(
                    ConversationFileModel.conversation_id.in_(conversation_ids),
                    ConversationFileModel.collection_tag.isnot(None)
                ).group_by(
                    ConversationFileModel.conversation_id
                ).all()

                # Convert to dict of conversation_id -> list of tags
                tags_dict = {}
                for conv_id, tags_str in results:
                    if tags_str:
                        # Split comma-separated tags
                        tags_dict[conv_id] = [tag.strip() for tag in tags_str.split(',')]

                return tags_dict

        except Exception as e:
            logger.error(f"Failed to batch load collection tags: {e}")
            return {}

    def _get_files_text_from_count(self, conversation_id: str, file_counts: Dict[str, int]) -> str:
        """Get files text from batch-loaded file counts - optimized for performance."""
        try:
            count = file_counts.get(conversation_id, 0)
            if count == 0:
                return "—"
            elif count == 1:
                return "1 file"
            else:
                return f"{count} files"
        except Exception as e:
            logger.error(f"Failed to format file count for conversation {conversation_id}: {e}")
            return "—"
    
    def _get_files_text_from_info(self, conversation_id: str, file_info: Dict[str, List[Dict[str, Any]]]) -> str:
        """Get files text from batch-loaded file info - shows actual file names."""
        try:
            files = file_info.get(conversation_id, [])
            if not files:
                return "—"
            
            # Format file names for display
            if len(files) == 1:
                # Single file - show the filename
                filename = files[0].get('filename', 'unknown')
                status = files[0].get('processing_status', '')
                if status and status != 'completed':
                    return f"{filename} ({status})"
                return filename
            elif len(files) <= 2:
                # Two files - show both names
                names = [f.get('filename', 'unknown') for f in files[:2]]
                return ", ".join(names)
            else:
                # Multiple files - show first file + count
                first_file = files[0].get('filename', 'unknown')
                return f"{first_file} +{len(files)-1} more"
        except Exception as e:
            logger.error(f"Failed to format file info for conversation {conversation_id}: {e}")
            return "—"
    
    def _get_status_text(self, status) -> str:
        """Get human-readable status text."""
        if not ConversationStatus:
            return str(status)
        
        status_map = {
            ConversationStatus.ACTIVE: "Active",
            ConversationStatus.PINNED: "Saved", 
            ConversationStatus.ARCHIVED: "Saved",
            ConversationStatus.DELETED: "Deleted"
        }
        return status_map.get(status, str(status))
    
    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display - always show full date and time."""
        if not isinstance(dt, datetime):
            return str(dt)
        
        # Always show full date and time as requested
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def _on_checkbox_changed(self):
        """Handle checkbox state change."""
        selected_conversations = self._get_selected_conversations()
        has_selected = len(selected_conversations) > 0
        self.mass_delete_btn.setEnabled(has_selected)
    
    def _get_selected_conversations(self) -> List[Conversation]:
        """Get list of conversations that are checked."""
        selected = []
        for row in range(self.conversations_table.rowCount()):
            checkbox = self.conversations_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                if row < len(self.conversations):
                    selected.append(self.conversations[row])
        return selected
    
    def _on_mass_delete_clicked(self):
        """Handle mass delete button click."""
        selected_conversations = self._get_selected_conversations()
        if not selected_conversations:
            return
        
        # Confirm mass deletion
        count = len(selected_conversations)
        reply = QMessageBox.question(
            self,
            "Delete Multiple Conversations",
            f"Delete {count} selected conversation{'s' if count > 1 else ''}?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete conversations using safe async approach
            failed_deletions = []
            
            for conversation in selected_conversations:
                try:
                    success = self._safe_run_async(
                        self.conversation_manager.conversation_service.delete_conversation(
                            conversation.id, permanent=True
                        )
                    )
                    if not success:
                        failed_deletions.append(conversation.title)
                except Exception as e:
                    logger.error(f"Failed to delete conversation {conversation.id}: {e}")
                    failed_deletions.append(conversation.title)
            
            # Show results
            if failed_deletions:
                QMessageBox.warning(
                    self,
                    "Deletion Incomplete",
                    f"Failed to delete {len(failed_deletions)} conversation(s):\n" +
                    "\n".join(failed_deletions[:5]) +
                    ("..." if len(failed_deletions) > 5 else "")
                )
            
            # Refresh the table
            self._load_conversations()
    
    def _on_select_all_clicked(self):
        """Handle select all button click - toggles between select all and select none."""
        if not self.conversations_table.rowCount():
            return
        
        # Check if any checkboxes are currently checked
        any_checked = False
        for row in range(self.conversations_table.rowCount()):
            checkbox = self.conversations_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                any_checked = True
                break
        
        # If any are checked, uncheck all; otherwise check all
        new_state = not any_checked
        for row in range(self.conversations_table.rowCount()):
            checkbox = self.conversations_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(new_state)
        
        # Update button text
        self.select_all_btn.setText("Select None" if new_state else "Select All")

    def _on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = self.conversations_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        self.restore_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        
        # Also update mass delete button based on checkbox states
        selected_conversations = self._get_selected_conversations()
        self.mass_delete_btn.setEnabled(len(selected_conversations) > 0)
    
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
            f"Switch to '{conversation.title}'?\n\n"
            "This will become your active conversation and any current unsaved messages will be saved first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.conversation_restore_requested.emit(conversation.id)
            self.status_label.setText(f"Switched to: {conversation.title}")
            logger.info(f"Conversation restore requested: {conversation.id}")
            
            # Simple refresh after a short delay (let the database update complete)
            QTimer.singleShot(300, self._load_conversations)
    
    # Removed _on_delete_clicked - now using _on_mass_delete_clicked for all deletions
    
    def _delete_conversation(self, conversation: Conversation):
        """Delete a conversation from the database."""
        try:
            self.status_label.setText(f"Deleting conversation...")
            
            # Delete conversation using safe async approach
            success = self._safe_run_async(
                self.conversation_manager.conversation_service.delete_conversation(conversation.id, permanent=True)
            )
            
            if success:
                self.status_label.setText(f"Deleted: {conversation.title}")
                logger.info(f"Conversation deleted: {conversation.id}")
                
                # Refresh the conversation list
                self._load_conversations()
                
                QMessageBox.information(
                    self,
                    "Conversation Deleted",
                    f"'{conversation.title}' has been deleted successfully."
                )
            else:
                self.status_label.setText("Delete failed")
                QMessageBox.warning(self, "Delete Error", "Failed to delete conversation")
                
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            self.status_label.setText(f"Delete error: {e}")
            QMessageBox.warning(self, "Delete Error", f"Delete failed:\n{e}")
    
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
        
        # HTML button
        html_btn = QPushButton("HTML (.html)")
        html_btn.clicked.connect(lambda: self._export_conversation(conversation, ExportFormat.HTML))
        html_btn.clicked.connect(dialog.accept)
        layout.addWidget(html_btn)
        
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
                ExportFormat.MARKDOWN: "md",
                ExportFormat.HTML: "html"
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
            
            # Load the full conversation with all messages
            full_conversation = loop.run_until_complete(
                self.conversation_manager.get_conversation(conversation.id, include_messages=True)
            )
            
            if not full_conversation:
                self.status_label.setText("Failed to load conversation")
                QMessageBox.warning(self, "Export Failed", "Could not load conversation data")
                return
            
            # The export_service.export_conversation expects (conversation, file_path, format)
            success = loop.run_until_complete(
                self.export_service.export_conversation(
                    full_conversation,  # Pass the full conversation with all messages
                    filename,           # File path
                    format.value        # Format as string
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
    
    def _on_search_text_changed(self, text: str):
        """Handle search input text changes with debouncing."""
        self.current_search_query = text.strip()
        
        # If search is empty, reload all conversations
        if not self.current_search_query:
            self._clear_search()
            return
        
        # Stop any pending search
        self.search_timer.stop()
        
        # Start debounce timer for search-as-you-type
        if len(self.current_search_query) >= 2:  # Minimum 2 characters
            self.search_timer.start(self.search_debounce_ms)
    
    def _perform_search(self):
        """Perform the actual search operation."""
        if not self.conversation_manager or not self.current_search_query:
            return
        
        if self.is_searching:
            return  # Prevent concurrent searches
        
        self.is_searching = True
        self.status_label.setText(f"Searching for '{self.current_search_query}'...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate
        
        # Perform search in background thread
        self.search_thread = QThread()
        self.search_worker = ConversationSearchWorker(
            self.conversation_manager, 
            self.current_search_query,
            use_regex=self.regex_checkbox.isChecked(),
            case_sensitive=self.case_checkbox.isChecked()
        )
        self.search_worker.moveToThread(self.search_thread)
        
        # Connect signals
        self.search_worker.search_completed.connect(self._on_search_completed)
        self.search_worker.search_error.connect(self._on_search_error)
        self.search_thread.started.connect(self.search_worker.perform_search)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        
        self.search_thread.start()
    
    def _on_search_completed(self, search_results):
        """Handle search completion."""
        self.is_searching = False
        self.progress_bar.setVisible(False)
        
        # Convert search results to conversations for display
        result_conversations = []
        for result in search_results.results:
            # Find the conversation in our current list
            for conv in self.conversations:
                if conv.id == result.conversation_id:
                    result_conversations.append(conv)
                    break
        
        # Update conversations list with search results
        self.conversations = result_conversations
        self._populate_table()
        
        # Update status
        result_count = len(result_conversations)
        query_time = search_results.query_time_ms or 0
        self.status_label.setText(
            f"Found {result_count} conversations in {query_time:.1f}ms"
        )
        
        logger.info(f"Search completed: {result_count} results")
        
        # Clean up thread
        self.search_thread.quit()
        self.search_thread.wait()
    
    def _on_search_error(self, error: str):
        """Handle search error."""
        self.is_searching = False
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Search error: {error}")
        
        logger.error(f"Search failed: {error}")
        QMessageBox.warning(self, "Search Error", f"Search failed:\n{error}")
        
        # Clean up thread
        self.search_thread.quit()
        self.search_thread.wait()
    
    def _clear_search(self):
        """Clear search and reload all conversations."""
        self.search_input.clear()
        self.current_search_query = ""
        self.search_timer.stop()
        
        if self.is_searching:
            return  # Don't interfere with ongoing search
        
        # Reload all conversations
        self._load_conversations()
    
    def _highlight_search_text(self, text: str, search_query: str) -> str:
        """Highlight search terms in text for visual feedback."""
        if not search_query or not text:
            return text
        
        # Simple case-insensitive highlighting
        # Note: QTableWidgetItem doesn't support rich text, so we use a simple marker
        # In a real implementation, you might want to use a custom delegate for rich text
        import re
        pattern = re.compile(re.escape(search_query), re.IGNORECASE)
        
        # For table items, we'll use a simple prefix marker
        if pattern.search(text):
            return f"🔍 {text}"
        return text
    
    def _apply_styles(self):
        """Apply theme-aware styles to the conversation browser."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            # Use theme system for consistent styling
            colors = self.theme_manager.current_theme
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {colors.background_primary};
                    color: {colors.text_primary};
                }}
                QLabel {{
                    color: {colors.text_primary};
                }}
                QPushButton {{
                    background-color: {colors.interactive_normal};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_secondary};
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {colors.interactive_hover};
                    border-color: {colors.border_focus};
                }}
                QPushButton:pressed {{
                    background-color: {colors.interactive_active};
                }}
                QPushButton:disabled {{
                    background-color: {colors.interactive_disabled};
                    color: {colors.text_disabled};
                    border-color: {colors.border_secondary};
                }}
                QTableWidget {{
                    background-color: {colors.background_tertiary};
                    alternate-background-color: {colors.background_secondary};
                    color: {colors.text_primary};
                    gridline-color: {colors.separator};
                    border: 1px solid {colors.border_primary};
                }}
                QHeaderView::section {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_primary};
                    padding: 6px;
                    border: 1px solid {colors.border_primary};
                    font-weight: bold;
                    cursor: pointer;
                }}
                QHeaderView::section:hover {{
                    background-color: {colors.interactive_hover};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.primary};
                    color: {colors.text_primary};
                }}
                QLineEdit {{
                    background-color: {colors.background_tertiary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                    padding: 6px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                }}
                QLineEdit:focus {{
                    border-color: {colors.border_focus};
                    background-color: {colors.background_secondary};
                }}
                QCheckBox {{
                    color: {colors.text_primary};
                    spacing: 5px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {colors.border_primary};
                    border-radius: 3px;
                    background-color: {colors.background_tertiary};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {colors.primary};
                    border-color: {colors.primary};
                }}
                QProgressBar {{
                    border: 1px solid {colors.border_primary};
                    border-radius: 3px;
                    background-color: {colors.background_secondary};
                    text-align: center;
                    color: {colors.text_primary};
                }}
                QProgressBar::chunk {{
                    background-color: {colors.primary};
                    border-radius: 2px;
                }}
            """)
        else:
            # Fallback to original dark theme styling
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
                QLineEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border-color: #4CAF50;
                    background-color: #252525;
                }
                QCheckBox {
                    color: #ffffff;
                    spacing: 5px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    background-color: #1e1e1e;
                }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border-color: #4CAF50;
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
    
    def _show_context_menu(self, position):
        """Show context menu for conversation table."""
        if not self.conversations_table.itemAt(position):
            return  # No item at this position
        
        # Get the selected conversation
        current_row = self.conversations_table.currentRow()
        if current_row < 0:
            return
        
        # Find conversation ID - it's stored in the row data or we need to get it from loaded conversations
        if current_row >= len(self.conversations):
            return
        
        conversation = self.conversations[current_row]
        conversation_id = conversation.id
        
        # Create context menu
        context_menu = QMenu(self)
        
        refresh_title_action = QAction("🔄 Refresh Title", self)
        refresh_title_action.triggered.connect(lambda: self._refresh_conversation_title(conversation_id, current_row))
        context_menu.addAction(refresh_title_action)
        
        set_title_action = QAction("✏️ Set Custom Title", self)
        set_title_action.triggered.connect(lambda: self._set_custom_title(conversation_id, current_row))
        context_menu.addAction(set_title_action)
        
        # Apply theme-aware menu styling
        self._style_menu(context_menu)
        
        # Show menu at cursor position
        context_menu.exec(self.conversations_table.mapToGlobal(position))
    
    def _style_menu(self, menu):
        """Apply theme-aware styling to QMenu widgets."""
        try:
            # Try to get the global theme manager
            theme_manager = None
            try:
                from specter.src.ui.themes.theme_manager import get_theme_manager
                theme_manager = get_theme_manager()
            except (ImportError, AttributeError):
                return
            
            if not theme_manager:
                return
                
            try:
                from specter.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                if not THEME_SYSTEM_AVAILABLE:
                    return
            except ImportError:
                return
            
            colors = theme_manager.current_theme
            if colors:
                from specter.src.ui.themes.style_templates import StyleTemplates
                menu_style = StyleTemplates.get_menu_style(colors)
                menu.setStyleSheet(menu_style)
                
        except Exception as e:
            # Silently handle errors to avoid breaking functionality
            pass
    
    def _refresh_conversation_title(self, conversation_id: str, row: int):
        """Refresh the conversation title by regenerating it."""
        try:
            if not self.conversation_manager:
                QMessageBox.warning(self, "Error", "Conversation manager not available")
                return
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Regenerating conversation title...")
            
            # Start async title generation
            self._generate_title_async(conversation_id, row)
            
        except Exception as e:
            logger.error(f"Failed to refresh conversation title: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh title: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _set_custom_title(self, conversation_id: str, row: int):
        """Set a custom title for the conversation."""
        try:
            # Get current title
            current_title_item = self.conversations_table.item(row, 0)
            current_title = current_title_item.text() if current_title_item else ""
            
            # Show input dialog
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
    
    def _generate_title_async(self, conversation_id: str, row: int):
        """Generate title asynchronously."""
        def on_complete():
            try:
                if hasattr(self.conversation_manager, 'conversation_service') and self.conversation_manager.conversation_service:
                    import asyncio
                    # Create async runner
                    async def generate_and_update():
                        try:
                            # Generate new title
                            new_title = await self.conversation_manager.conversation_service.generate_conversation_title(conversation_id)
                            
                            if new_title:
                                # Update title in database
                                await self.conversation_manager.conversation_service.update_conversation_title(conversation_id, new_title)
                                
                                # Update UI on main thread
                                QTimer.singleShot(0, lambda: self._update_table_title(row, new_title))
                            else:
                                QTimer.singleShot(0, lambda: self._show_title_generation_failed("No title generated"))
                                
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
                if hasattr(self.conversation_manager, 'conversation_service') and self.conversation_manager.conversation_service:
                    import asyncio
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
    
    def _update_table_title(self, row: int, new_title: str):
        """Update the title in the table at the specified row."""
        try:
            title_item = self.conversations_table.item(row, 0)
            if title_item:
                title_item.setText(new_title)
            
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Title updated successfully")
            
            # Also update our local conversations list
            if 0 <= row < len(self.conversations):
                self.conversations[row].title = new_title
            
        except Exception as e:
            logger.error(f"Failed to update table title: {e}")
            self.progress_bar.setVisible(False)
    
    def _show_title_generation_failed(self, error_msg: str = None):
        """Show error message when title generation fails."""
        self.progress_bar.setVisible(False)
        msg = f"Failed to generate title: {error_msg}" if error_msg else "Failed to generate title"
        self.status_label.setText(msg)
        QMessageBox.warning(self, "Title Generation Failed", msg)
    
    def _show_title_update_failed(self, error_msg: str):
        """Show error message when title update fails."""
        self.progress_bar.setVisible(False)
        msg = f"Failed to update title: {error_msg}"
        self.status_label.setText(msg)
        QMessageBox.warning(self, "Title Update Failed", msg)
    
    def set_current_conversation(self, conversation_id: Optional[str]):
        """Set the current conversation ID for highlighting."""
        self.current_conversation_id = conversation_id
        if hasattr(self, 'conversations_table'):
            self._populate_table()