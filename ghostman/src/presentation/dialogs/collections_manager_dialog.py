"""
Collections Manager Dialog for managing file collections.

Provides a comprehensive UI for creating, editing, and organizing
file collections with drag-and-drop support, search, and filtering.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QLabel, QGroupBox, QSpinBox, QCheckBox, QTextEdit,
    QFileDialog, QMessageBox, QWidget, QComboBox,
    QInputDialog
)

from ...application.services.collection_service import CollectionService
from ...domain.models.collection import FileCollection, FileCollectionItem
from ...infrastructure.conversation_management.database_manager import DatabaseManager
from ..ui.themes.improved_preset_themes import get_theme_by_name, ColorSystem

logger = logging.getLogger("ghostman.presentation.collections_manager")


class CollectionsManagerDialog(QDialog):
    """
    Dialog for managing file collections.

    Features:
    - Split view: collections list (left) and file details (right)
    - Search and filter by tags
    - Create/edit/delete collections
    - Add/remove files with drag-and-drop
    - Import/export collections
    - Template instantiation
    - RAG settings configuration
    """

    # Signals
    collection_created = pyqtSignal(FileCollection)
    collection_updated = pyqtSignal(FileCollection)
    collection_deleted = pyqtSignal(str)  # collection_id

    def __init__(
        self,
        parent=None,
        db_manager: Optional[DatabaseManager] = None,
        theme_name: str = "Matrix"
    ):
        """
        Initialize the Collections Manager Dialog.

        Args:
            parent: Parent widget
            db_manager: Optional database manager
            theme_name: Theme to apply
        """
        super().__init__(parent)
        self.service = CollectionService(db_manager)
        self.current_collection: Optional[FileCollection] = None
        self.theme_name = theme_name
        self.colors: Optional[ColorSystem] = None

        self.setWindowTitle("Collections Manager")
        self.setMinimumSize(1000, 700)

        self._init_ui()
        self._apply_theme()
        self._load_collections()

        logger.info("✓ Collections Manager Dialog initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Top bar with search and actions
        top_bar = self._create_top_bar()
        layout.addLayout(top_bar)

        # Main content area (split view)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Collections list
        left_panel = self._create_collections_panel()
        splitter.addWidget(left_panel)

        # Right panel: Collection details and files
        right_panel = self._create_details_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

        # Bottom buttons
        bottom_buttons = self._create_bottom_buttons()
        layout.addLayout(bottom_buttons)

    def _create_top_bar(self) -> QHBoxLayout:
        """Create the top bar with search and action buttons."""
        layout = QHBoxLayout()

        # Search box
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search collections...")
        self.search_input.textChanged.connect(self._on_search_changed)

        # Tag filter
        tag_filter_label = QLabel("Filter by tag:")
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All tags", None)
        self.tag_filter.currentIndexChanged.connect(self._on_filter_changed)

        # Template checkbox
        self.show_templates = QCheckBox("Show templates")
        self.show_templates.setChecked(True)
        self.show_templates.stateChanged.connect(self._on_filter_changed)

        # New collection button
        self.new_collection_btn = QPushButton("New Collection")
        self.new_collection_btn.clicked.connect(self._on_new_collection)

        # New from template button
        self.new_from_template_btn = QPushButton("From Template")
        self.new_from_template_btn.clicked.connect(self._on_new_from_template)

        # Import button
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._on_import_collection)

        layout.addWidget(search_label)
        layout.addWidget(self.search_input, stretch=2)
        layout.addWidget(tag_filter_label)
        layout.addWidget(self.tag_filter, stretch=1)
        layout.addWidget(self.show_templates)
        layout.addStretch()
        layout.addWidget(self.new_collection_btn)
        layout.addWidget(self.new_from_template_btn)
        layout.addWidget(self.import_btn)

        return layout

    def _create_collections_panel(self) -> QWidget:
        """Create the left panel with collections list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Collections list
        self.collections_list = QListWidget()
        self.collections_list.itemClicked.connect(self._on_collection_selected)

        layout.addWidget(QLabel("Collections:"))
        layout.addWidget(self.collections_list)

        return panel

    def _create_details_panel(self) -> QWidget:
        """Create the right panel with collection details and files."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Collection info section
        info_group = QGroupBox("Collection Details")
        info_layout = QVBoxLayout()

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Collection name")
        self.name_input.textChanged.connect(self._on_details_changed)
        name_layout.addWidget(self.name_input)
        info_layout.addLayout(name_layout)

        # Description
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Optional description")
        self.description_input.setMaximumHeight(80)
        self.description_input.textChanged.connect(self._on_details_changed)
        desc_layout.addWidget(self.description_input)
        info_layout.addLayout(desc_layout)

        # Tags
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags:"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags")
        self.tags_input.textChanged.connect(self._on_details_changed)
        tags_layout.addWidget(self.tags_input)
        info_layout.addLayout(tags_layout)

        # Statistics
        self.stats_label = QLabel("Files: 0 | Size: 0 MB")
        self.stats_label.setStyleSheet("font-style: italic; opacity: 0.7;")
        info_layout.addWidget(self.stats_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # RAG settings section
        rag_group = QGroupBox("RAG Settings")
        rag_layout = QHBoxLayout()

        chunk_size_layout = QVBoxLayout()
        chunk_size_layout.addWidget(QLabel("Chunk Size:"))
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 10000)
        self.chunk_size_spin.setValue(1000)
        self.chunk_size_spin.setSingleStep(100)
        self.chunk_size_spin.valueChanged.connect(self._on_details_changed)
        chunk_size_layout.addWidget(self.chunk_size_spin)

        chunk_overlap_layout = QVBoxLayout()
        chunk_overlap_layout.addWidget(QLabel("Chunk Overlap:"))
        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 1000)
        self.chunk_overlap_spin.setValue(200)
        self.chunk_overlap_spin.setSingleStep(50)
        self.chunk_overlap_spin.valueChanged.connect(self._on_details_changed)
        chunk_overlap_layout.addWidget(self.chunk_overlap_spin)

        max_size_layout = QVBoxLayout()
        max_size_layout.addWidget(QLabel("Max Size (MB):"))
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(1, 10000)
        self.max_size_spin.setValue(500)
        self.max_size_spin.setSingleStep(100)
        self.max_size_spin.valueChanged.connect(self._on_details_changed)
        max_size_layout.addWidget(self.max_size_spin)

        rag_layout.addLayout(chunk_size_layout)
        rag_layout.addLayout(chunk_overlap_layout)
        rag_layout.addLayout(max_size_layout)
        rag_layout.addStretch()

        rag_group.setLayout(rag_layout)
        layout.addWidget(rag_group)

        # Files section
        files_group = QGroupBox("Files")
        files_layout = QVBoxLayout()

        # File list with drag-and-drop
        self.files_list = FileListWidget()
        self.files_list.files_dropped.connect(self._on_files_dropped)

        # File action buttons
        file_buttons = QHBoxLayout()
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self._on_add_files)
        self.remove_file_btn = QPushButton("Remove Selected")
        self.remove_file_btn.clicked.connect(self._on_remove_file)
        self.verify_integrity_btn = QPushButton("Verify Integrity")
        self.verify_integrity_btn.clicked.connect(self._on_verify_integrity)

        file_buttons.addWidget(self.add_files_btn)
        file_buttons.addWidget(self.remove_file_btn)
        file_buttons.addWidget(self.verify_integrity_btn)
        file_buttons.addStretch()

        files_layout.addWidget(self.files_list)
        files_layout.addLayout(file_buttons)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group, stretch=1)

        # Collection action buttons
        action_buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._on_save_collection)
        self.save_btn.setEnabled(False)

        self.delete_btn = QPushButton("Delete Collection")
        self.delete_btn.clicked.connect(self._on_delete_collection)
        self.delete_btn.setEnabled(False)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._on_export_collection)
        self.export_btn.setEnabled(False)

        action_buttons.addWidget(self.save_btn)
        action_buttons.addWidget(self.delete_btn)
        action_buttons.addWidget(self.export_btn)
        action_buttons.addStretch()

        layout.addLayout(action_buttons)

        return panel

    def _create_bottom_buttons(self) -> QHBoxLayout:
        """Create bottom dialog buttons."""
        layout = QHBoxLayout()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(self.close_btn)

        return layout

    def _apply_theme(self):
        """Apply the current theme to the dialog."""
        theme = get_theme_by_name(self.theme_name)
        if theme:
            self.colors = theme.colors

            # Apply background color
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {self.colors.background_primary};
                    color: {self.colors.text_primary};
                }}
                QGroupBox {{
                    border: 1px solid {self.colors.border};
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }}
                QGroupBox::title {{
                    color: {self.colors.primary};
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }}
                QLineEdit, QTextEdit, QSpinBox, QComboBox {{
                    background-color: {self.colors.background_secondary};
                    color: {self.colors.text_primary};
                    border: 1px solid {self.colors.border};
                    border-radius: 3px;
                    padding: 5px;
                }}
                QListWidget {{
                    background-color: {self.colors.background_secondary};
                    color: {self.colors.text_primary};
                    border: 1px solid {self.colors.border};
                    border-radius: 3px;
                }}
                QPushButton {{
                    background-color: {self.colors.primary};
                    color: {self.colors.text_primary};
                    border: none;
                    border-radius: 3px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.colors.primary_hover};
                }}
                QPushButton:pressed {{
                    background-color: {self.colors.primary_active};
                }}
                QPushButton:disabled {{
                    background-color: {self.colors.background_tertiary};
                    color: {self.colors.text_secondary};
                }}
            """)

            logger.info(f"✓ Applied theme: {self.theme_name}")

    # ========================================
    # Data Loading
    # ========================================

    def _load_collections(self):
        """Load collections from database."""
        try:
            # Get filter settings
            include_templates = self.show_templates.isChecked()
            selected_tag = self.tag_filter.currentData()
            tags = [selected_tag] if selected_tag else None

            # Load collections
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collections = loop.run_until_complete(
                self.service.list_collections(
                    include_templates=include_templates,
                    tags=tags
                )
            )
            loop.close()

            # Apply search filter
            search_query = self.search_input.text().lower()
            if search_query:
                collections = [
                    c for c in collections
                    if search_query in c.name.lower() or
                       search_query in c.description.lower()
                ]

            # Update list
            self.collections_list.clear()
            for collection in collections:
                item = QListWidgetItem(
                    f"{collection.name} ({collection.file_count} files)"
                )
                item.setData(Qt.ItemDataRole.UserRole, collection)
                self.collections_list.addItem(item)

            # Update tag filter options
            self._update_tag_filter(collections)

            logger.info(f"✓ Loaded {len(collections)} collections")

        except Exception as e:
            logger.error(f"✗ Error loading collections: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load collections: {e}"
            )

    def _update_tag_filter(self, collections: List[FileCollection]):
        """Update tag filter dropdown with available tags."""
        # Collect all unique tags
        all_tags = set()
        for collection in collections:
            all_tags.update(collection.tags)

        # Update combobox
        current_tag = self.tag_filter.currentData()
        self.tag_filter.clear()
        self.tag_filter.addItem("All tags", None)

        for tag in sorted(all_tags):
            self.tag_filter.addItem(tag, tag)

        # Restore selection if possible
        if current_tag:
            index = self.tag_filter.findData(current_tag)
            if index >= 0:
                self.tag_filter.setCurrentIndex(index)

    # ========================================
    # Event Handlers - Collections
    # ========================================

    def _on_collection_selected(self, item: QListWidgetItem):
        """Handle collection selection."""
        collection = item.data(Qt.ItemDataRole.UserRole)
        if collection:
            self._load_collection_details(collection)

    def _load_collection_details(self, collection: FileCollection):
        """Load collection details into the form."""
        self.current_collection = collection

        # Update form fields
        self.name_input.setText(collection.name)
        self.description_input.setPlainText(collection.description)
        self.tags_input.setText(", ".join(collection.tags))
        self.chunk_size_spin.setValue(collection.chunk_size)
        self.chunk_overlap_spin.setValue(collection.chunk_overlap)
        self.max_size_spin.setValue(collection.max_size_mb)

        # Update statistics
        self._update_statistics()

        # Load files
        self._load_collection_files()

        # Enable action buttons
        self.save_btn.setEnabled(False)  # No changes yet
        self.delete_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

        logger.info(f"✓ Loaded collection: {collection.name}")

    def _load_collection_files(self):
        """Load files for the current collection."""
        if not self.current_collection:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            files = loop.run_until_complete(
                self.service.get_collection_files(self.current_collection.id)
            )
            loop.close()

            # Update files list
            self.files_list.clear()
            for file_item in files:
                list_item = QListWidgetItem(
                    f"{file_item.file_name} ({file_item.file_size / 1024:.1f} KB)"
                )
                list_item.setData(Qt.ItemDataRole.UserRole, file_item)
                self.files_list.addItem(list_item)

            logger.info(f"✓ Loaded {len(files)} files")

        except Exception as e:
            logger.error(f"✗ Error loading files: {e}")

    def _update_statistics(self):
        """Update collection statistics display."""
        if not self.current_collection:
            self.stats_label.setText("Files: 0 | Size: 0 MB")
            return

        # Reload collection to get latest stats
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collection = loop.run_until_complete(
                self.service.get_collection(self.current_collection.id)
            )
            loop.close()

            if collection:
                self.current_collection = collection
                self.stats_label.setText(
                    f"Files: {collection.file_count} | "
                    f"Size: {collection.total_size_mb:.2f} MB / {collection.max_size_mb} MB"
                )

        except Exception as e:
            logger.error(f"✗ Error updating statistics: {e}")

    def _on_details_changed(self):
        """Handle changes to collection details."""
        if self.current_collection:
            self.save_btn.setEnabled(True)

    def _on_search_changed(self):
        """Handle search query changes."""
        self._load_collections()

    def _on_filter_changed(self):
        """Handle filter changes."""
        self._load_collections()

    def _on_new_collection(self):
        """Create a new empty collection."""
        name, ok = QInputDialog.getText(
            self,
            "New Collection",
            "Collection name:"
        )

        if not ok or not name:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collection = loop.run_until_complete(
                self.service.create_collection(name=name)
            )
            loop.close()

            if collection:
                self.collection_created.emit(collection)
                self._load_collections()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Collection '{name}' created successfully"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to create collection (name may already exist)"
                )

        except Exception as e:
            logger.error(f"✗ Error creating collection: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_new_from_template(self):
        """Create a new collection from a template."""
        # Get available templates
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        templates = loop.run_until_complete(self.service.get_builtin_templates())
        loop.close()

        # Show template selection dialog
        template_names = [t["name"] for t in templates]
        template_name, ok = QInputDialog.getItem(
            self,
            "Select Template",
            "Choose a template:",
            template_names,
            0,
            False
        )

        if not ok:
            return

        # Get collection name
        collection_name, ok = QInputDialog.getText(
            self,
            "Collection Name",
            "Enter name for new collection:"
        )

        if not ok or not collection_name:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collection = loop.run_until_complete(
                self.service.instantiate_template(
                    template_name=template_name,
                    new_collection_name=collection_name,
                    file_paths=[]
                )
            )
            loop.close()

            if collection:
                self.collection_created.emit(collection)
                self._load_collections()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Collection '{collection_name}' created from template"
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to create collection")

        except Exception as e:
            logger.error(f"✗ Error creating from template: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_save_collection(self):
        """Save changes to the current collection."""
        if not self.current_collection:
            return

        try:
            # Get updated values
            name = self.name_input.text()
            description = self.description_input.toPlainText()
            tags_text = self.tags_input.text()
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]
            chunk_size = self.chunk_size_spin.value()
            chunk_overlap = self.chunk_overlap_spin.value()
            max_size_mb = self.max_size_spin.value()

            # Update collection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.service.update_collection(
                    collection_id=self.current_collection.id,
                    name=name if name != self.current_collection.name else None,
                    description=description,
                    tags=tags,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    max_size_mb=max_size_mb
                )
            )
            loop.close()

            if success:
                # Reload collection
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                updated = loop.run_until_complete(
                    self.service.get_collection(self.current_collection.id)
                )
                loop.close()

                if updated:
                    self.current_collection = updated
                    self.collection_updated.emit(updated)
                    self._load_collections()
                    self.save_btn.setEnabled(False)
                    QMessageBox.information(
                        self,
                        "Success",
                        "Collection updated successfully"
                    )

            else:
                QMessageBox.warning(self, "Error", "Failed to update collection")

        except Exception as e:
            logger.error(f"✗ Error saving collection: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_delete_collection(self):
        """Delete the current collection."""
        if not self.current_collection:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete collection '{self.current_collection.name}'?\n\n"
            f"This will remove all file associations and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            collection_id = self.current_collection.id

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.service.delete_collection(collection_id)
            )
            loop.close()

            if success:
                self.collection_deleted.emit(collection_id)
                self.current_collection = None
                self._clear_details_form()
                self._load_collections()
                QMessageBox.information(
                    self,
                    "Success",
                    "Collection deleted successfully"
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to delete collection")

        except Exception as e:
            logger.error(f"✗ Error deleting collection: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _clear_details_form(self):
        """Clear the details form."""
        self.name_input.clear()
        self.description_input.clear()
        self.tags_input.clear()
        self.chunk_size_spin.setValue(1000)
        self.chunk_overlap_spin.setValue(200)
        self.max_size_spin.setValue(500)
        self.files_list.clear()
        self.stats_label.setText("Files: 0 | Size: 0 MB")
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

    # ========================================
    # Event Handlers - Files
    # ========================================

    def _on_add_files(self):
        """Add files to the current collection."""
        if not self.current_collection:
            QMessageBox.warning(
                self,
                "No Collection",
                "Please select or create a collection first"
            )
            return

        # Show file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Add",
            "",
            "All Files (*.*)"
        )

        if not file_paths:
            return

        self._add_files_to_collection(file_paths)

    def _on_files_dropped(self, file_paths: List[str]):
        """Handle files dropped onto the list."""
        if not self.current_collection:
            QMessageBox.warning(
                self,
                "No Collection",
                "Please select or create a collection first"
            )
            return

        self._add_files_to_collection(file_paths)

    def _add_files_to_collection(self, file_paths: List[str]):
        """Add files to the current collection."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            successful, errors = loop.run_until_complete(
                self.service.add_files_to_collection(
                    self.current_collection.id,
                    file_paths,
                    check_duplicates=True
                )
            )
            loop.close()

            # Show results
            if successful > 0:
                self._load_collection_files()
                self._update_statistics()

            if errors:
                QMessageBox.warning(
                    self,
                    "Some Files Failed",
                    f"Added {successful}/{len(file_paths)} files.\n\nErrors:\n" +
                    "\n".join(errors[:5])  # Show first 5 errors
                )
            else:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Added {successful} file(s) successfully"
                )

        except Exception as e:
            logger.error(f"✗ Error adding files: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_remove_file(self):
        """Remove selected file from collection."""
        if not self.current_collection:
            return

        current_item = self.files_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a file to remove")
            return

        file_item = current_item.data(Qt.ItemDataRole.UserRole)
        if not file_item:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.service.remove_file_from_collection(
                    self.current_collection.id,
                    file_item.id
                )
            )
            loop.close()

            if success:
                self._load_collection_files()
                self._update_statistics()
            else:
                QMessageBox.warning(self, "Error", "Failed to remove file")

        except Exception as e:
            logger.error(f"✗ Error removing file: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_verify_integrity(self):
        """Verify integrity of all files in collection."""
        if not self.current_collection:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            all_valid, errors = loop.run_until_complete(
                self.service.verify_collection_integrity(self.current_collection.id)
            )
            loop.close()

            if all_valid:
                QMessageBox.information(
                    self,
                    "Verification Success",
                    "All files passed integrity verification"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Verification Failed",
                    f"{len(errors)} file(s) failed verification:\n\n" +
                    "\n".join(errors[:10])  # Show first 10 errors
                )

        except Exception as e:
            logger.error(f"✗ Error verifying integrity: {e}")
            QMessageBox.critical(self, "Error", str(e))

    # ========================================
    # Import/Export
    # ========================================

    def _on_export_collection(self):
        """Export the current collection."""
        if not self.current_collection:
            return

        # Show save dialog
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Collection",
            f"{self.current_collection.name}.zip",
            "ZIP Files (*.zip)"
        )

        if not export_path:
            return

        # Ask if files should be included
        include_files = QMessageBox.question(
            self,
            "Include Files",
            "Include file contents in export?\n\n"
            "Yes: Full export with files (larger file size)\n"
            "No: Metadata only (smaller, requires files to exist on import)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        ) == QMessageBox.StandardButton.Yes

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, error = loop.run_until_complete(
                self.service.export_collection(
                    self.current_collection.id,
                    export_path,
                    include_files=include_files
                )
            )
            loop.close()

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Collection exported to:\n{export_path}"
                )
            else:
                QMessageBox.warning(self, "Error", f"Export failed: {error}")

        except Exception as e:
            logger.error(f"✗ Error exporting collection: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _on_import_collection(self):
        """Import a collection from file."""
        # Show open dialog
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Collection",
            "",
            "ZIP Files (*.zip)"
        )

        if not import_path:
            return

        # Ask about file restoration
        restore_files = QMessageBox.question(
            self,
            "Restore Files",
            "Restore file contents from import package?\n\n"
            "This will extract files to a directory you choose.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

        target_directory = None
        if restore_files:
            target_directory = QFileDialog.getExistingDirectory(
                self,
                "Select Target Directory for Files"
            )
            if not target_directory:
                return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collection, errors = loop.run_until_complete(
                self.service.import_collection(
                    import_path,
                    restore_files=restore_files,
                    target_directory=target_directory
                )
            )
            loop.close()

            if collection:
                self.collection_created.emit(collection)
                self._load_collections()

                if errors:
                    QMessageBox.warning(
                        self,
                        "Import with Warnings",
                        f"Collection imported: {collection.name}\n\n"
                        f"Warnings:\n" + "\n".join(errors[:5])
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Collection imported: {collection.name}"
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    "Failed to import collection:\n" + "\n".join(errors)
                )

        except Exception as e:
            logger.error(f"✗ Error importing collection: {e}")
            QMessageBox.critical(self, "Error", str(e))


class FileListWidget(QListWidget):
    """
    Custom list widget that accepts file drops.
    """

    files_dropped = pyqtSignal(list)  # List of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop."""
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())

            if file_paths:
                self.files_dropped.emit(file_paths)

            event.acceptProposedAction()
