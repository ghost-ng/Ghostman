"""
Collections Manager - Simple Tag-Based File Organization
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QLabel, QGroupBox, QFileDialog, QMessageBox, QWidget,
    QInputDialog, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QProgressDialog, QApplication
)

from ...application.services.collection_service import CollectionService
from ...infrastructure.conversation_management.repositories.database import DatabaseManager
from ...infrastructure.storage.settings_manager import settings
from ...ui.themes.improved_preset_themes import get_improved_preset_themes, ColorSystem

logger = logging.getLogger("ghostman.presentation.collections_manager")


class FileUploadWorker(QThread):
    """Background worker for uploading files to RAG without blocking UI."""

    # Signals
    file_started = pyqtSignal(int, str)  # row, filename
    file_completed = pyqtSignal(int, dict)  # row, file_data
    file_failed = pyqtSignal(int, str, str)  # row, filename, error
    all_completed = pyqtSignal(list, list)  # successful_files, failed_files

    def __init__(self, file_paths, collection_tag, conversation_id, rag_session, db_manager):
        super().__init__()
        self.file_paths = file_paths
        self.collection_tag = collection_tag
        self.conversation_id = conversation_id
        self.rag_session = rag_session
        self.db_manager = db_manager
        self.successful_files = []
        self.failed_files = []

    def run(self):
        """Run file uploads in background thread."""
        for i, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)

            self.file_started.emit(i, filename)

            try:
                # Validate file
                if not os.path.exists(file_path):
                    self.failed_files.append((filename, "File not found"))
                    self.file_failed.emit(i, filename, "File not found")
                    continue

                if os.path.isdir(file_path):
                    self.failed_files.append((filename, "Cannot upload directories"))
                    self.file_failed.emit(i, filename, "Cannot upload directories")
                    continue

                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:
                    error = f"File too large ({file_size/1024/1024:.1f}MB > 50MB)"
                    self.failed_files.append((filename, error))
                    self.file_failed.emit(i, filename, error)
                    continue

                # Check file extension
                file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
                supported_extensions = {'txt', 'py', 'js', 'json', 'md', 'csv', 'html', 'css', 'xml', 'yaml', 'yml', 'java', 'cpp', 'c', 'h', 'rs', 'go', 'rb', 'php', 'ts', 'tsx', 'jsx'}
                if file_ext not in supported_extensions:
                    error = f"Unsupported format: .{file_ext}"
                    self.failed_files.append((filename, error))
                    self.file_failed.emit(i, filename, error)
                    continue

                # Generate file ID
                timestamp = datetime.now().timestamp()
                file_id = f"file_{Path(file_path).stem}_{int(timestamp)}"

                # Process through RAG
                try:
                    metadata_override = {
                        'pending_conversation_id': self.conversation_id,
                        'conversation_id': self.conversation_id,
                        'collection_tag': self.collection_tag  # CRITICAL: Add collection tag to FAISS metadata
                    }

                    document_id = self.rag_session.ingest_document(
                        file_path=str(file_path),
                        metadata_override=metadata_override,
                        timeout=120.0
                    )

                    if not document_id:
                        self.failed_files.append((filename, 'Document ingestion returned None'))
                        self.file_failed.emit(i, filename, 'Document ingestion returned None')
                        continue

                    stats = self.rag_session.get_stats(timeout=10.0) or {}
                    rag_stats = stats.get('rag_pipeline', {})
                    chunk_count = rag_stats.get('chunks_created', 1)

                    logger.info(f"✓ RAG processed: {filename} ({chunk_count} chunks)")

                except Exception as rag_error:
                    error_msg = f"RAG error: {str(rag_error)}"
                    self.failed_files.append((filename, error_msg))
                    self.file_failed.emit(i, filename, error_msg)
                    logger.error(f"RAG processing failed for {filename}: {rag_error}")
                    continue

                # Save to database
                try:
                    from ...infrastructure.conversation_management.models.database_models import ConversationFileModel

                    with self.db_manager.get_session() as session:
                        file_record = ConversationFileModel(
                            id=str(uuid.uuid4()),
                            conversation_id=self.conversation_id,
                            file_id=file_id,
                            filename=filename,
                            file_path=file_path,
                            file_size=file_size,
                            file_type=file_ext,
                            upload_timestamp=datetime.now(),
                            processing_status='completed',
                            chunk_count=chunk_count,
                            is_enabled=True,
                            collection_tag=self.collection_tag
                        )
                        session.add(file_record)
                        session.commit()

                    self.successful_files.append(filename)
                    logger.info(f"✅ Uploaded: {filename} ({chunk_count} chunks, tag: {self.collection_tag or 'none'})")

                    # Emit success with file data
                    file_data = {
                        'filename': filename,
                        'file_size': file_size,
                        'chunk_count': chunk_count,
                        'collection_tag': self.collection_tag
                    }
                    self.file_completed.emit(i, file_data)

                except Exception as db_error:
                    error_msg = f"DB error: {str(db_error)}"
                    self.failed_files.append((filename, error_msg))
                    self.file_failed.emit(i, filename, error_msg)
                    logger.error(f"Database error for {filename}: {db_error}")
                    import traceback
                    traceback.print_exc()

            except Exception as e:
                error_msg = str(e)
                self.failed_files.append((filename, error_msg))
                self.file_failed.emit(i, filename, error_msg)
                logger.error(f"Failed to process {filename}: {e}")

        # Emit completion signal
        self.all_completed.emit(self.successful_files, self.failed_files)


class CollectionsManagerDialog(QDialog):
    """Simple tag-based Collections Manager."""

    tag_insert_requested = pyqtSignal(str)  # Emit when user wants to insert @tag

    # Legacy signals for backwards compatibility (not used in tag-based system)
    collection_created = pyqtSignal(object)
    collection_updated = pyqtSignal(object)
    collection_deleted = pyqtSignal(str)

    def __init__(self, parent=None, db_manager=None, theme_name=None):
        super().__init__(parent)
        self.service = CollectionService(db_manager)
        self.db_manager = db_manager or DatabaseManager()

        # Get RAG session from parent (REPL widget pattern)
        self.rag_session = None
        if parent and hasattr(parent, 'rag_session'):
            self.rag_session = parent.rag_session
            logger.info("✓ Using parent's RAG session")

        # Get theme from settings
        if theme_name is None:
            from ...infrastructure.storage.settings_manager import settings
            theme_name = settings.get('ui.theme', 'professional_dark')

        self.theme_name = theme_name
        self.current_tag = None
        self.all_files = []

        # Track upload workers and row mappings
        self._upload_workers = []
        self._upload_row_mapping = {}  # Maps worker index to table row

        self.setWindowTitle("Collections Manager")
        self.setMinimumSize(1200, 700)

        # Make dialog non-modal so it doesn't block the app
        self.setModal(False)

        self._init_ui()
        self._apply_theme()

        # Don't load data in __init__ - let it load when dialog is shown
        # This prevents recursion issues during initialization
        QTimer.singleShot(100, self._load_data)

        logger.info("✓ Collections Manager initialized (tag-based)")

    def _init_ui(self):
        """Create 3-panel UI."""
        layout = QVBoxLayout(self)

        # Top: Upload + Create Tag buttons
        top_bar = QHBoxLayout()
        self.upload_btn = QPushButton("Upload Files")
        self.upload_btn.clicked.connect(self._on_upload_files)
        self.new_tag_btn = QPushButton("Create Tag")
        self.new_tag_btn.clicked.connect(self._on_create_tag)

        top_bar.addWidget(QLabel("Collections Manager"))
        top_bar.addStretch()
        top_bar.addWidget(self.upload_btn)
        top_bar.addWidget(self.new_tag_btn)
        layout.addLayout(top_bar)

        # Middle: 3-panel splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Tags list
        left_panel = QGroupBox("Tags")
        left_layout = QVBoxLayout(left_panel)
        self.tag_search = QLineEdit()
        self.tag_search.setPlaceholderText("Search tags...")
        self.tag_search.textChanged.connect(self._filter_tags)
        self.tags_list = QListWidget()
        self.tags_list.itemClicked.connect(self._on_tag_selected)
        self.show_all_btn = QPushButton("Show All Files")
        self.show_all_btn.clicked.connect(self._on_show_all)
        left_layout.addWidget(self.tag_search)
        left_layout.addWidget(self.tags_list)
        left_layout.addWidget(self.show_all_btn)

        # MIDDLE: Files table
        middle_panel = QGroupBox("Files")
        middle_layout = QVBoxLayout(middle_panel)
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(['☑', 'Filename', 'Tag', 'Size', 'Chunks'])
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.selection_label = QLabel("0 selected")
        middle_layout.addWidget(self.files_table)
        middle_layout.addWidget(self.selection_label)

        # RIGHT: Actions
        right_panel = QGroupBox("Actions")
        right_layout = QVBoxLayout(right_panel)
        self.current_tag_label = QLabel("No tag selected")
        self.tag_files_btn = QPushButton("Tag Selected Files")
        self.tag_files_btn.clicked.connect(self._on_tag_files)
        self.untag_btn = QPushButton("Remove Tags")
        self.untag_btn.clicked.connect(self._on_untag_files)
        self.insert_btn = QPushButton("Insert @tag into Chat")
        self.insert_btn.clicked.connect(self._on_insert_tag)
        self.insert_btn.setEnabled(False)
        self.delete_tag_btn = QPushButton("Delete Tag")
        self.delete_tag_btn.clicked.connect(self._on_delete_tag)
        self.delete_tag_btn.setEnabled(False)
        self.delete_files_btn = QPushButton("Delete Selected Files")
        self.delete_files_btn.clicked.connect(self._on_delete_files)

        right_layout.addWidget(self.current_tag_label)
        right_layout.addStretch()
        right_layout.addWidget(self.tag_files_btn)
        right_layout.addWidget(self.untag_btn)
        right_layout.addWidget(self.insert_btn)
        right_layout.addWidget(self.delete_files_btn)
        right_layout.addStretch()
        right_layout.addWidget(self.delete_tag_btn)

        splitter.addWidget(left_panel)
        splitter.addWidget(middle_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 650, 300])
        layout.addWidget(splitter)

        # Bottom: Close
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    def _apply_theme(self):
        """Apply theme using StyleTemplates like settings dialog."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...ui.themes.style_templates import StyleTemplates

            theme_manager = get_theme_manager()
            style = StyleTemplates.get_settings_dialog_style(theme_manager.current_theme)
            self.setStyleSheet(style)

            logger.debug(f"Applied theme: {theme_manager.current_theme_name}")
        except ImportError:
            logger.warning("Theme system not available, using fallback")
            self._apply_fallback_theme()

    def _apply_fallback_theme(self):
        """Apply fallback dark theme styling when theme system is not available."""
        self.setStyleSheet("""
            /* Main dialog styling */
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }

            /* Group box styling */
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }

            /* Label styling */
            QLabel {
                color: #ffffff;
            }

            /* Input field styling */
            QLineEdit, QTextEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4CAF50;
            }

            /* Button styling */
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }

            /* List widget styling */
            QListWidget {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }

            /* Table widget styling */
            QTableWidget {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                gridline-color: #555555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
                font-weight: bold;
            }

            /* Splitter styling */
            QSplitter::handle {
                background-color: #555555;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
        """)

    def _load_data(self):
        """Load tags and files from ALL conversations."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Load tags
            tags = loop.run_until_complete(self.service.list_collection_tags())

            # Load ALL files from ALL conversations (not just collections)
            from ...infrastructure.conversation_management.models.database_models import ConversationFileModel
            all_files = []

            with self.db_manager.get_session() as session:
                # Get ALL files from database (from all conversations)
                file_records = session.query(ConversationFileModel).all()

                # Convert to dict format (same as service returns)
                for record in file_records:
                    all_files.append({
                        'file_id': record.file_id,
                        'filename': record.filename,
                        'file_path': record.file_path,
                        'file_size': record.file_size,
                        'file_type': record.file_type,
                        'chunk_count': record.chunk_count,
                        'collection_tag': record.collection_tag,
                        'conversation_id': record.conversation_id,
                        'processing_status': record.processing_status
                    })

            self.all_files = all_files
            loop.close()

            # Populate tags
            self.tags_list.clear()
            for tag in tags:
                loop2 = asyncio.new_event_loop()
                stats = loop2.run_until_complete(self.service.get_tag_stats(tag))
                loop2.close()
                item = QListWidgetItem(f"{tag} ({stats['file_count']} files)")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                self.tags_list.addItem(item)

            self._display_files(all_files)
            logger.info(f"✓ Loaded {len(tags)} tags, {len(all_files)} files")

        except Exception as e:
            logger.error(f"✗ Error loading: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", str(e))

    def _display_files(self, files):
        """Show files in table."""
        self.files_table.setRowCount(len(files))
        for row, file in enumerate(files):
            checkbox = QCheckBox()
            self.files_table.setCellWidget(row, 0, checkbox)
            self.files_table.setItem(row, 1, QTableWidgetItem(file['filename']))
            self.files_table.setItem(row, 2, QTableWidgetItem(file.get('collection_tag', 'Untagged')))
            self.files_table.setItem(row, 3, QTableWidgetItem(f"{file['file_size']/1024/1024:.2f} MB"))
            self.files_table.setItem(row, 4, QTableWidgetItem(str(file['chunk_count'])))
            self.files_table.item(row, 1).setData(Qt.ItemDataRole.UserRole, file)

    def _get_selected_files(self):
        """Get checked files."""
        selected = []
        for row in range(self.files_table.rowCount()):
            cb = self.files_table.cellWidget(row, 0)
            if cb and cb.isChecked():
                selected.append(self.files_table.item(row, 1).data(Qt.ItemDataRole.UserRole))
        return selected

    def _on_tag_selected(self, item):
        """Handle tag click."""
        tag = item.data(Qt.ItemDataRole.UserRole)
        self.current_tag = tag
        self.current_tag_label.setText(f"Tag: {tag}")
        self.insert_btn.setEnabled(True)
        self.delete_tag_btn.setEnabled(True)

        # Load files for tag
        loop = asyncio.new_event_loop()
        files = loop.run_until_complete(self.service.get_files_by_tag(tag))
        loop.close()
        self._display_files(files)

    def _on_show_all(self):
        """Show all files."""
        self.current_tag = None
        self.current_tag_label.setText("All files")
        self.insert_btn.setEnabled(False)
        self.delete_tag_btn.setEnabled(False)
        self._display_files(self.all_files)

    def _filter_tags(self, text):
        """Filter tags by search."""
        for i in range(self.tags_list.count()):
            item = self.tags_list.item(i)
            tag = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(text.lower() not in tag.lower())

    def _on_upload_files(self):
        """Upload files using REPL's existing RAG session approach."""
        if not self.rag_session or not getattr(self.rag_session, 'is_ready', False):
            QMessageBox.warning(
                self,
                "RAG Not Available",
                "File upload requires RAG to be initialized.\n\n"
                "This usually happens automatically when the app starts with an API key configured."
            )
            return

        # Show file picker
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Upload",
            "",
            "Supported Files (*.txt *.py *.js *.json *.md *.csv *.html *.css *.xml *.yaml *.yml *.java *.cpp *.c *.h *.rs *.go *.rb *.php *.ts *.tsx *.jsx);;All Files (*.*)"
        )

        if not file_paths:
            return

        # Check for duplicates
        from ...infrastructure.conversation_management.models.database_models import ConversationFileModel
        duplicates = []
        unique_files = []

        with self.db_manager.get_session() as session:
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                # Check if this exact file path already exists
                existing = session.query(ConversationFileModel).filter(
                    ConversationFileModel.file_path == file_path
                ).first()

                if existing:
                    duplicates.append(filename)
                else:
                    unique_files.append(file_path)

        # Show duplicate warning if any
        if duplicates:
            if len(duplicates) == len(file_paths):
                QMessageBox.warning(
                    self,
                    "Duplicate Files",
                    f"All selected files are already uploaded:\n\n" + "\n".join(f"• {f}" for f in duplicates[:10])
                )
                return
            else:
                reply = QMessageBox.question(
                    self,
                    "Duplicate Files Found",
                    f"Found {len(duplicates)} duplicate file(s):\n\n" +
                    "\n".join(f"• {f}" for f in duplicates[:5]) +
                    (f"\n... and {len(duplicates) - 5} more" if len(duplicates) > 5 else "") +
                    f"\n\nContinue uploading {len(unique_files)} new file(s)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        if not unique_files:
            return

        # Ask for optional collection tag
        tag, ok = QInputDialog.getText(
            self,
            "Collection Tag (Optional)",
            f"Tag for {len(unique_files)} file(s):\n(Leave empty to upload without tag)"
        )

        if ok:  # User clicked OK (even if tag is empty)
            tag = tag.strip() if tag else None
            self._process_files_with_rag(unique_files, tag)

    def _process_files_with_rag(self, file_paths: List[str], collection_tag: Optional[str] = None):
        """Start async file upload using worker thread."""
        # Ensure special collections conversation exists
        conversation_id = "00000000-0000-0000-0000-000000000000"
        from ...infrastructure.conversation_management.models.database_models import ConversationModel

        with self.db_manager.get_session() as session:
            existing = session.query(ConversationModel).filter(
                ConversationModel.id == conversation_id
            ).first()

            if not existing:
                collections_conv = ConversationModel(
                    id=conversation_id,
                    title="Collections Library",
                    status='active',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(collections_conv)
                session.commit()

        # Add files to table with hourglass
        for i, file_path in enumerate(file_paths):
            filename = os.path.basename(file_path)
            current_row = self.files_table.rowCount()
            self.files_table.setRowCount(current_row + 1)

            # Hourglass in checkbox column
            hourglass_label = QLabel("⏳")
            hourglass_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hourglass_label.setStyleSheet("font-size: 18px;")
            self.files_table.setCellWidget(current_row, 0, hourglass_label)

            self.files_table.setItem(current_row, 1, QTableWidgetItem(filename))
            self.files_table.setItem(current_row, 2, QTableWidgetItem(collection_tag or "Untagged"))
            self.files_table.setItem(current_row, 3, QTableWidgetItem("Uploading..."))
            self.files_table.setItem(current_row, 4, QTableWidgetItem("..."))

            self._upload_row_mapping[i] = current_row

        # Create and start worker thread
        worker = FileUploadWorker(
            file_paths=file_paths,
            collection_tag=collection_tag,
            conversation_id=conversation_id,
            rag_session=self.rag_session,
            db_manager=self.db_manager
        )

        # Connect signals
        worker.file_started.connect(self._on_file_upload_started)
        worker.file_completed.connect(self._on_file_upload_completed)
        worker.file_failed.connect(self._on_file_upload_failed)
        worker.all_completed.connect(self._on_all_uploads_completed)

        # Start upload
        self._upload_workers.append(worker)
        worker.start()

        logger.info(f"🚀 Started async upload of {len(file_paths)} file(s)")

    def _on_file_upload_started(self, worker_idx: int, filename: str):
        """Handle file upload start."""
        logger.info(f"📤 Starting upload: {filename}")

    def _on_file_upload_completed(self, worker_idx: int, file_data: dict):
        """Handle successful file upload."""
        if worker_idx not in self._upload_row_mapping:
            return

        row = self._upload_row_mapping[worker_idx]
        filename = file_data['filename']

        # Replace hourglass with checkbox
        checkbox = QCheckBox()
        self.files_table.setCellWidget(row, 0, checkbox)

        # Update size and chunks
        self.files_table.setItem(row, 3, QTableWidgetItem(f"{file_data['file_size']/1024/1024:.2f} MB"))
        self.files_table.setItem(row, 4, QTableWidgetItem(str(file_data['chunk_count'])))

        logger.info(f"✅ Upload completed: {filename}")

    def _on_file_upload_failed(self, worker_idx: int, filename: str, error: str):
        """Handle failed file upload."""
        if worker_idx not in self._upload_row_mapping:
            return

        row = self._upload_row_mapping[worker_idx]

        # Replace hourglass with error icon
        error_label = QLabel("❌")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.files_table.setCellWidget(row, 0, error_label)

        self.files_table.setItem(row, 3, QTableWidgetItem("Failed"))
        self.files_table.setItem(row, 4, QTableWidgetItem("Error"))

        logger.error(f"❌ Upload failed: {filename} - {error}")

    def _on_all_uploads_completed(self, successful_files: list, failed_files: list):
        """Handle completion of all uploads."""
        self._upload_row_mapping.clear()

        # Reload data to show all files
        self._load_data()

        # Show results
        message = f"✅ Successfully uploaded: {len(successful_files)} file(s)"
        if failed_files:
            message += f"\n❌ Failed: {len(failed_files)} file(s)"
            for fname, error in failed_files[:5]:
                message += f"\n  - {fname}: {error}"
            if len(failed_files) > 5:
                message += f"\n  ... and {len(failed_files) - 5} more"

        QMessageBox.information(self, "Upload Complete", message)
        logger.info(f"🏁 All uploads completed: {len(successful_files)} success, {len(failed_files)} failed")

    def _on_create_tag(self):
        """Create tag (just info message)."""
        tag, ok = QInputDialog.getText(self, "Create Tag", "Tag name:")
        if ok and tag:
            QMessageBox.information(self, "Tag Created", f"Select files and tag them with '{tag}'")

    def _on_tag_files(self):
        """Tag selected files."""
        selected = self._get_selected_files()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select files first")
            return

        tag, ok = QInputDialog.getText(self, "Tag Files", f"Tag for {len(selected)} files:")
        if ok and tag:
            loop = asyncio.new_event_loop()
            count = 0
            for file in selected:
                if loop.run_until_complete(self.service.tag_file(file['file_id'], file['conversation_id'], tag)):
                    count += 1
            loop.close()
            QMessageBox.information(self, "Done", f"Tagged {count}/{len(selected)} files")
            self._load_data()

    def _on_untag_files(self):
        """Remove tags from selected."""
        selected = self._get_selected_files()
        if not selected:
            return

        loop = asyncio.new_event_loop()
        count = 0
        for file in selected:
            if loop.run_until_complete(self.service.untag_file(file['file_id'], file['conversation_id'])):
                count += 1
        loop.close()
        QMessageBox.information(self, "Done", f"Untagged {count} files")
        self._load_data()

    def _on_insert_tag(self):
        """Emit signal to insert @tag."""
        if self.current_tag:
            self.tag_insert_requested.emit(self.current_tag)
            QMessageBox.information(self, "Inserted", f"@{self.current_tag} will be inserted")

    def _on_delete_tag(self):
        """Delete tag from all files."""
        if not self.current_tag:
            return

        reply = QMessageBox.question(self, "Delete?", f"Remove '{self.current_tag}' from all files?")
        if reply == QMessageBox.StandardButton.Yes:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.service.delete_tag(self.current_tag))
            loop.close()
            self._load_data()

    def _on_delete_files(self):
        """Delete selected files from collections and RAG."""
        selected = self._get_selected_files()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select files to delete")
            return

        reply = QMessageBox.question(
            self,
            "Delete Files?",
            f"Permanently delete {len(selected)} file(s) from collections?\n\nThis will remove them from the database and RAG index."
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_count = 0
        failed = []

        for file_data in selected:
            try:
                file_id = file_data['file_id']
                conversation_id = file_data['conversation_id']
                filename = file_data['filename']

                # Delete from database
                from ...infrastructure.conversation_management.models.database_models import ConversationFileModel
                with self.db_manager.get_session() as session:
                    file_record = session.query(ConversationFileModel).filter(
                        ConversationFileModel.file_id == file_id,
                        ConversationFileModel.conversation_id == conversation_id
                    ).first()

                    if file_record:
                        session.delete(file_record)
                        session.commit()
                        deleted_count += 1
                        logger.info(f"✅ Deleted file from database: {filename}")
                    else:
                        failed.append((filename, "Not found in database"))

                # TODO: Delete from RAG index when RAG session supports deletion
                # For now, just delete from database

            except Exception as e:
                logger.error(f"Failed to delete {filename}: {e}")
                failed.append((filename, str(e)))

        # Show results
        message = f"✅ Deleted {deleted_count} file(s)"
        if failed:
            message += f"\n❌ Failed: {len(failed)}"
            for fname, error in failed[:5]:
                message += f"\n  - {fname}: {error}"

        QMessageBox.information(self, "Delete Complete", message)
        self._load_data()
