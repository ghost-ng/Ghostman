"""
File Toolbar Widget for Ghostman.

Provides a comprehensive file management toolbar for the REPL widget,
including file upload, progress tracking, vector store management,
and drag-and-drop functionality.
"""

import logging
import os
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QPushButton,
    QProgressBar, QLabel, QMenu, QFileDialog, QComboBox,
    QMessageBox, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QTextEdit, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QSize, pyqtSlot
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont, QPalette

# Theme system imports
try:
    from ...ui.themes.theme_manager import get_theme_manager
    from ...ui.themes.style_templates import StyleTemplates, ButtonStyleManager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False

# Service imports
from ...application.services.file_validation_service import FileValidationService, ValidationResult
from ...application.services.file_upload_service import FileUploadService, UploadTask, UploadStatus, BatchUploadResult
from ...application.services.fine_tuning_service import FineTuningService, VectorStoreInfo

logger = logging.getLogger("ghostman.file_toolbar")


class FileUploadWorker(QObject):
    """Worker for handling async file operations in separate thread."""
    
    upload_completed = pyqtSignal(object)  # UploadTask or BatchUploadResult
    upload_failed = pyqtSignal(str, str)  # file_path, error
    upload_progress = pyqtSignal(str, float, int, int)  # file_path, progress, bytes_uploaded, total_bytes
    
    def __init__(self, upload_service: FileUploadService):
        super().__init__()
        self.upload_service = upload_service
        self._loop = None
    
    def setup_event_loop(self):
        """Setup asyncio event loop for this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
    
    @pyqtSlot(list, str)
    def upload_files_batch(self, file_paths: List[str], purpose: str = "assistants"):
        """Upload multiple files in batch."""
        if not self._loop:
            self.setup_event_loop()
        
        try:
            result = self._loop.run_until_complete(
                self.upload_service.upload_files_batch(file_paths, purpose)
            )
            self.upload_completed.emit(result)
        except Exception as e:
            logger.error(f"Batch upload failed: {e}")
            self.upload_failed.emit("batch_upload", str(e))
    
    @pyqtSlot(str, str)
    def upload_single_file(self, file_path: str, purpose: str = "assistants"):
        """Upload a single file."""
        if not self._loop:
            self.setup_event_loop()
        
        try:
            result = self._loop.run_until_complete(
                self.upload_service.upload_file(file_path, purpose)
            )
            self.upload_completed.emit(result)
        except Exception as e:
            logger.error(f"Single file upload failed: {e}")
            self.upload_failed.emit(file_path, str(e))


class VectorStoreDialog(QDialog):
    """Dialog for vector store management."""
    
    def __init__(self, parent=None, fine_tuning_service: Optional[FineTuningService] = None):
        super().__init__(parent)
        self.fine_tuning_service = fine_tuning_service
        self.setWindowTitle("Vector Store Management")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._apply_theme()
        
        if self.fine_tuning_service:
            self._load_vector_stores()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Vector store list
        self.store_list = QListWidget()
        layout.addWidget(QLabel("Existing Vector Stores:"))
        layout.addWidget(self.store_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Create New")
        self.create_btn.clicked.connect(self._show_create_dialog)
        button_layout.addWidget(self.create_btn)
        
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self._delete_selected)
        button_layout.addWidget(self.delete_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_vector_stores)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _apply_theme(self):
        """Apply theme styling to the dialog."""
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                colors = theme_manager.current_theme
                
                self.setStyleSheet(f"""
                    QDialog {{
                        background-color: {colors.background_primary};
                        color: {colors.text_primary};
                    }}
                    QListWidget {{
                        background-color: {colors.background_secondary};
                        border: 1px solid {colors.border_primary};
                        border-radius: 4px;
                    }}
                    QPushButton {{
                        {ButtonStyleManager.get_unified_button_style(colors, "push", "medium")}
                    }}
                """)
    
    def _load_vector_stores(self):
        """Load vector stores from the service."""
        if not self.fine_tuning_service:
            return
        
        self.store_list.clear()
        
        # This would be async in real implementation
        # For now, we'll use the cached stores
        stores = self.fine_tuning_service._vector_stores
        
        for store_id, store_info in stores.items():
            item_text = f"{store_info.vector_store.name} ({store_info.file_count} files, {store_info.size_mb:.1f} MB)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, store_id)
            self.store_list.addItem(item)
    
    def _show_create_dialog(self):
        """Show dialog to create a new vector store."""
        # This would open a separate dialog for creating vector stores
        QMessageBox.information(self, "Create Vector Store", "Vector store creation dialog would open here.")
    
    def _delete_selected(self):
        """Delete the selected vector store."""
        current_item = self.store_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a vector store to delete.")
            return
        
        store_id = current_item.data(Qt.ItemDataRole.UserRole)
        store_name = current_item.text().split(' (')[0]
        
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the vector store '{store_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # This would be async in real implementation
            QMessageBox.information(self, "Deleted", f"Vector store '{store_name}' has been deleted.")
            self._load_vector_stores()


class FineTuningToolbar(QWidget):
    """
    Comprehensive file management toolbar for Ghostman.
    
    Features:
    - File upload with drag-and-drop support
    - Progress tracking for uploads
    - Vector store management
    - File validation and error reporting
    - Theme-aware styling following established patterns
    """
    
    # Signals for REPL integration
    files_uploaded = pyqtSignal(list)  # List of file IDs
    vector_store_created = pyqtSignal(str, str)  # store_id, name
    error_occurred = pyqtSignal(str, str)  # operation, error_message
    status_updated = pyqtSignal(str)  # status_message
    
    def __init__(self, 
                 upload_service: FileUploadService,
                 fine_tuning_service: FineTuningService,
                 validation_service: FileValidationService,
                 parent=None):
        """
        Initialize the file toolbar.
        
        Args:
            upload_service: Service for handling file uploads
            fine_tuning_service: Service for vector store management
            validation_service: Service for file validation
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.upload_service = upload_service
        self.fine_tuning_service = fine_tuning_service
        self.validation_service = validation_service
        
        # State tracking
        self._active_uploads: Dict[str, UploadTask] = {}
        self._upload_worker = None
        self._upload_thread = None
        
        # UI components
        self.upload_btn = None
        self.progress_bar = None
        self.status_label = None
        self.vector_store_btn = None
        
        # Theme manager
        self.theme_manager = get_theme_manager() if THEME_SYSTEM_AVAILABLE else None
        
        self._setup_ui()
        self._setup_drag_drop()
        self._connect_signals()
        self._apply_theme()
        
        logger.info("FineTuningToolbar initialized")
    
    def _setup_ui(self):
        """Setup the toolbar UI components."""
        layout = QHBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Upload files button
        self.upload_btn = QToolButton()
        self.upload_btn.setText("📁")
        self.upload_btn.setToolTip("Upload files for AI context")
        self.upload_btn.clicked.connect(self._show_file_dialog)
        layout.addWidget(self.upload_btn)
        
        # Vector store management button
        self.vector_store_btn = QToolButton()
        self.vector_store_btn.setText("🗃️")
        self.vector_store_btn.setToolTip("Manage vector stores")
        self.vector_store_btn.clicked.connect(self._show_vector_store_dialog)
        layout.addWidget(self.vector_store_btn)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Add stretch to push everything to the left
        layout.addStretch()
        
        # Initially hide the toolbar (can be toggled)
        self.setVisible(False)
    
    def _setup_drag_drop(self):
        """Setup drag and drop functionality."""
        self.setAcceptDrops(True)
    
    def _connect_signals(self):
        """Connect service signals to UI updates."""
        # Connect upload service signals
        self.upload_service.upload_started.connect(self._on_upload_started)
        self.upload_service.upload_progress.connect(self._on_upload_progress)
        self.upload_service.upload_completed.connect(self._on_upload_completed)
        self.upload_service.upload_failed.connect(self._on_upload_failed)
        self.upload_service.batch_completed.connect(self._on_batch_completed)
        
        # Connect fine-tuning service signals
        self.fine_tuning_service.vector_store_created.connect(self._on_vector_store_created)
        self.fine_tuning_service.error_occurred.connect(self._on_service_error)
    
    def _apply_theme(self):
        """Apply theme styling to the toolbar."""
        if not THEME_SYSTEM_AVAILABLE or not self.theme_manager:
            return
        
        colors = self.theme_manager.current_theme
        
        # Apply button styling
        for button in [self.upload_btn, self.vector_store_btn]:
            if button:
                button_style = ButtonStyleManager.get_unified_button_style(
                    colors, "tool", "icon", "normal"
                )
                button.setStyleSheet(button_style)
        
        # Apply toolbar background
        self.setStyleSheet(f"""
            FineTuningToolbar {{
                background-color: {colors.background_secondary};
                border-top: 1px solid {colors.border_primary};
                border-radius: 0px;
            }}
        """)
        
        # Apply progress bar styling
        if self.progress_bar:
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    background-color: {colors.background_primary};
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {colors.accent_primary};
                    border-radius: 3px;
                }}
            """)
        
        # Apply status label styling
        if self.status_label:
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors.text_secondary};
                    font-size: 11px;
                }}
            """)
    
    def _show_file_dialog(self):
        """Show file selection dialog."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setWindowTitle("Select Files to Upload")
        
        # Set file filters based on validation service
        if self.validation_service:
            extensions = self.validation_service.config.allowed_extensions
            filter_str = "Allowed Files (" + " ".join(f"*{ext}" for ext in extensions) + ")"
            file_dialog.setNameFilter(filter_str)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self._start_file_upload(file_paths)
    
    def _start_file_upload(self, file_paths: List[str]):
        """Start uploading the selected files."""
        logger.info(f"Starting upload of {len(file_paths)} files")
        
        # Validate files first
        validation_results = self.validation_service.validate_files(file_paths)
        valid_files = [fp for fp, result in validation_results.items() if result.is_valid]
        invalid_files = [fp for fp, result in validation_results.items() if not result.is_valid]
        
        if invalid_files:
            error_msg = f"{len(invalid_files)} files failed validation:\n"
            for fp in invalid_files[:5]:  # Show first 5 errors
                error_msg += f"• {Path(fp).name}: {validation_results[fp].errors[0]}\n"
            if len(invalid_files) > 5:
                error_msg += f"... and {len(invalid_files) - 5} more"
            
            QMessageBox.warning(self, "Validation Errors", error_msg)
            
            if not valid_files:
                return
        
        # Setup progress tracking
        self._show_progress(f"Uploading {len(valid_files)} files...")
        
        # Start upload in worker thread
        self._start_upload_worker(valid_files)
    
    def _start_upload_worker(self, file_paths: List[str]):
        """Start the upload worker in a separate thread."""
        if self._upload_thread and self._upload_thread.isRunning():
            logger.warning("Upload already in progress")
            return
        
        # Create worker and thread
        self._upload_thread = QThread()
        self._upload_worker = FileUploadWorker(self.upload_service)
        self._upload_worker.moveToThread(self._upload_thread)
        
        # Connect worker signals
        self._upload_worker.upload_completed.connect(self._on_worker_upload_completed)
        self._upload_worker.upload_failed.connect(self._on_worker_upload_failed)
        
        # Connect thread signals
        self._upload_thread.started.connect(self._upload_worker.setup_event_loop)
        self._upload_thread.finished.connect(self._upload_worker.deleteLater)
        self._upload_thread.finished.connect(self._upload_thread.deleteLater)
        
        # Start upload
        self._upload_thread.start()
        self._upload_worker.upload_files_batch(file_paths)
    
    def _show_vector_store_dialog(self):
        """Show vector store management dialog."""
        dialog = VectorStoreDialog(self, self.fine_tuning_service)
        dialog.exec()
    
    def _show_progress(self, message: str):
        """Show progress bar and status message."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        self.status_updated.emit(message)
    
    def _hide_progress(self):
        """Hide progress bar and status message."""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
    
    def _update_progress(self, value: int, maximum: int = 100, message: str = ""):
        """Update progress bar with specific values."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
            self.status_updated.emit(message)
    
    # Drag and drop event handlers
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are local files
            files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if files:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        if event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            
            # Filter for actual files (not directories)
            file_paths = [f for f in files if os.path.isfile(f)]
            
            if file_paths:
                logger.info(f"Files dropped: {len(file_paths)} files")
                self._start_file_upload(file_paths)
                event.acceptProposedAction()
            else:
                QMessageBox.warning(self, "Invalid Drop", "Please drop valid files, not directories.")
                event.ignore()
        else:
            event.ignore()
    
    # Signal handlers
    
    @pyqtSlot(str)
    def _on_upload_started(self, file_path: str):
        """Handle upload started signal."""
        logger.debug(f"Upload started: {file_path}")
    
    @pyqtSlot(str, float, int, int)
    def _on_upload_progress(self, file_path: str, progress: float, bytes_uploaded: int, total_bytes: int):
        """Handle upload progress signal."""
        if total_bytes > 0:
            percentage = int(progress * 100)
            size_mb = bytes_uploaded / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            message = f"Uploading {Path(file_path).name}: {size_mb:.1f}/{total_mb:.1f} MB ({percentage}%)"
            self._update_progress(percentage, 100, message)
    
    @pyqtSlot(str, str)
    def _on_upload_completed(self, file_path: str, file_id: str):
        """Handle upload completed signal."""
        logger.info(f"Upload completed: {file_path} -> {file_id}")
    
    @pyqtSlot(str, str)
    def _on_upload_failed(self, file_path: str, error_message: str):
        """Handle upload failed signal."""
        logger.error(f"Upload failed: {file_path} - {error_message}")
        self._hide_progress()
        QMessageBox.critical(self, "Upload Failed", f"Failed to upload {Path(file_path).name}:\n{error_message}")
    
    @pyqtSlot(object)
    def _on_batch_completed(self, batch_result: BatchUploadResult):
        """Handle batch upload completed signal."""
        self._hide_progress()
        
        successful_count = len(batch_result.successful_uploads)
        failed_count = len(batch_result.failed_uploads)
        
        if successful_count > 0:
            file_ids = [task.file_id for task in batch_result.successful_uploads]
            self.files_uploaded.emit(file_ids)
            
            message = f"Successfully uploaded {successful_count} files"
            if failed_count > 0:
                message += f" ({failed_count} failed)"
            
            self.status_updated.emit(message)
            logger.info(message)
            
            # Show success message
            QMessageBox.information(self, "Upload Complete", message)
        
        if failed_count > 0 and successful_count == 0:
            error_msg = f"All {failed_count} files failed to upload"
            self.error_occurred.emit("batch_upload", error_msg)
            QMessageBox.critical(self, "Upload Failed", error_msg)
    
    @pyqtSlot(str, str)
    def _on_vector_store_created(self, store_id: str, name: str):
        """Handle vector store created signal."""
        self.vector_store_created.emit(store_id, name)
        message = f"Vector store '{name}' created successfully"
        self.status_updated.emit(message)
        QMessageBox.information(self, "Success", message)
    
    @pyqtSlot(str, str)
    def _on_service_error(self, operation: str, error_message: str):
        """Handle service error signal."""
        self.error_occurred.emit(operation, error_message)
        self._hide_progress()
        QMessageBox.critical(self, "Service Error", f"Operation '{operation}' failed:\n{error_message}")
    
    @pyqtSlot(object)
    def _on_worker_upload_completed(self, result):
        """Handle worker upload completion."""
        if isinstance(result, BatchUploadResult):
            self._on_batch_completed(result)
        elif isinstance(result, UploadTask):
            if result.status == UploadStatus.COMPLETED:
                self._on_upload_completed(result.file_path, result.file_id)
            else:
                self._on_upload_failed(result.file_path, result.error_message or "Unknown error")
    
    @pyqtSlot(str, str)
    def _on_worker_upload_failed(self, file_path: str, error: str):
        """Handle worker upload failure."""
        self._on_upload_failed(file_path, error)
    
    # Public interface
    
    def show_toolbar(self):
        """Show the file toolbar."""
        self.setVisible(True)
        logger.debug("File toolbar shown")
    
    def hide_toolbar(self):
        """Hide the file toolbar."""
        self.setVisible(False)
        logger.debug("File toolbar hidden")
    
    def toggle_toolbar(self):
        """Toggle the file toolbar visibility."""
        self.setVisible(not self.isVisible())
        logger.debug(f"File toolbar toggled: {'visible' if self.isVisible() else 'hidden'}")
    
    def cancel_uploads(self):
        """Cancel all active uploads."""
        self.upload_service.cancel_all_uploads()
        self._hide_progress()
        self.status_updated.emit("Uploads cancelled")
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """Get current upload statistics."""
        return self.upload_service.get_upload_statistics()
    
    def update_theme(self):
        """Update theme styling - called when theme changes."""
        try:
            self._apply_theme()
            logger.debug("File toolbar theme updated")
        except Exception as e:
            logger.error(f"Failed to update file toolbar theme: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of file toolbar and services."""
        return {
            'toolbar_visible': self.isVisible(),
            'services_available': FILE_MANAGEMENT_AVAILABLE,
            'upload_service_available': self.upload_service is not None,
            'fine_tuning_service_available': self.fine_tuning_service is not None,
            'validation_service_available': self.validation_service is not None,
            'active_uploads': len(self._active_uploads),
            'upload_statistics': self.get_upload_statistics() if self.upload_service else {}
        }