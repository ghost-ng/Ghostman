"""
Collection Attach Widget for quickly attaching collections to conversations.

Provides a dropdown widget with checkboxes that allows users to attach/detach
file collections to the current conversation with a single click.
"""

import asyncio
import logging
from typing import List, Optional, Set

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QMenu, QWidgetAction,
    QVBoxLayout, QLabel, QCheckBox, QScrollArea, QPushButton,
    QMessageBox
)

from ...application.services.collection_service import CollectionService
from ...domain.models.collection import FileCollection
from ...infrastructure.conversation_management.repositories.database import DatabaseManager
from ...ui.themes.improved_preset_themes import ColorSystem

logger = logging.getLogger("ghostman.presentation.collection_attach")


class CollectionAttachWidget(QWidget):
    """
    Quick-attach widget for collections.

    Displays a dropdown button with a list of available collections.
    Each collection has a checkbox to attach/detach it from the current conversation.
    Shows count of attached collections in the button text.
    """

    # Signals
    collection_attached = pyqtSignal(str, str)  # conversation_id, collection_id
    collection_detached = pyqtSignal(str, str)  # conversation_id, collection_id
    collections_changed = pyqtSignal()  # Emitted when attachments change

    def __init__(
        self,
        parent=None,
        db_manager: Optional[DatabaseManager] = None,
        colors: Optional[ColorSystem] = None
    ):
        """
        Initialize the Collection Attach Widget.

        Args:
            parent: Parent widget
            db_manager: Optional database manager
            colors: Optional color system for theming
        """
        super().__init__(parent)
        self.service = CollectionService(db_manager)
        self.colors = colors
        self.current_conversation_id: Optional[str] = None
        self.attached_collection_ids: Set[str] = set()
        self.available_collections: List[FileCollection] = []

        self._init_ui()
        if self.colors:
            self._apply_theme()

        logger.info("✓ CollectionAttachWidget initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Dropdown button
        self.attach_button = QToolButton()
        self.attach_button.setText("Collections (0)")
        self.attach_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.attach_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # Create dropdown menu
        self.menu = QMenu(self.attach_button)
        self.attach_button.setMenu(self.menu)

        # Menu will be populated dynamically
        self.menu.aboutToShow.connect(self._on_menu_about_to_show)

        layout.addWidget(self.attach_button)

    def _apply_theme(self):
        """Apply theme colors to the widget."""
        if not self.colors:
            return

        self.attach_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.colors.primary};
                color: {self.colors.text_primary};
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: {self.colors.primary_hover};
            }}
            QToolButton:pressed {{
                background-color: {self.colors.primary_active};
            }}
            QToolButton::menu-indicator {{
                image: none;  /* Hide default arrow */
                width: 0px;
            }}
        """)

        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colors.background_secondary};
                color: {self.colors.text_primary};
                border: 1px solid {self.colors.border};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 4px 20px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {self.colors.primary};
            }}
        """)

    def set_colors(self, colors: ColorSystem):
        """
        Update theme colors.

        Args:
            colors: New color system
        """
        self.colors = colors
        self._apply_theme()

    def set_conversation(self, conversation_id: Optional[str]):
        """
        Set the current conversation.

        Args:
            conversation_id: Conversation UUID or None
        """
        self.current_conversation_id = conversation_id

        if conversation_id:
            self._load_attached_collections()
        else:
            self.attached_collection_ids.clear()
            self._update_button_text()

        logger.info(f"✓ Set conversation: {conversation_id}")

    def _load_attached_collections(self):
        """Load collections attached to the current conversation."""
        if not self.current_conversation_id:
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collections = loop.run_until_complete(
                self.service.get_conversation_collections(
                    self.current_conversation_id
                )
            )
            loop.close()

            self.attached_collection_ids = {c.id for c in collections}
            self._update_button_text()

            logger.info(
                f"✓ Loaded {len(self.attached_collection_ids)} attached collections"
            )

        except Exception as e:
            logger.error(f"✗ Error loading attached collections: {e}")

    def _update_button_text(self):
        """Update the button text with count of attached collections."""
        count = len(self.attached_collection_ids)
        self.attach_button.setText(f"Collections ({count})")

    def _on_menu_about_to_show(self):
        """Populate menu when it's about to be shown."""
        self._populate_menu()

    def _populate_menu(self):
        """Populate the menu with available collections."""
        self.menu.clear()

        # Load available collections
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.available_collections = loop.run_until_complete(
                self.service.list_collections(include_templates=False)
            )
            loop.close()

        except Exception as e:
            logger.error(f"✗ Error loading collections: {e}")
            error_action = QAction("Error loading collections", self)
            error_action.setEnabled(False)
            self.menu.addAction(error_action)
            return

        # Add header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)

        header_label = QLabel("Attach Collections:")
        header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_label)

        if self.current_conversation_id:
            info_label = QLabel(
                f"{len(self.attached_collection_ids)} attached"
            )
            info_label.setStyleSheet("font-size: 10pt; opacity: 0.7;")
            header_layout.addWidget(info_label)

        header_action = QWidgetAction(self)
        header_action.setDefaultWidget(header_widget)
        self.menu.addAction(header_action)

        self.menu.addSeparator()

        # Add collection checkboxes
        if not self.available_collections:
            no_collections = QAction("No collections available", self)
            no_collections.setEnabled(False)
            self.menu.addAction(no_collections)

            self.menu.addSeparator()

            # Add "Create New" action
            create_action = QAction("Create New Collection...", self)
            create_action.triggered.connect(self._on_create_collection)
            self.menu.addAction(create_action)

        else:
            # Create scrollable area for collections
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setContentsMargins(4, 0, 4, 0)
            scroll_layout.setSpacing(2)

            for collection in self.available_collections:
                checkbox = QCheckBox(
                    f"{collection.name} ({collection.file_count} files)"
                )
                checkbox.setChecked(collection.id in self.attached_collection_ids)
                checkbox.setEnabled(self.current_conversation_id is not None)

                # Connect checkbox to attach/detach handler
                checkbox.stateChanged.connect(
                    lambda state, coll_id=collection.id:
                    self._on_collection_toggled(coll_id, state == Qt.CheckState.Checked.value)
                )

                scroll_layout.addWidget(checkbox)

            scroll_layout.addStretch()

            # Create scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidget(scroll_widget)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(300)
            scroll_area.setMinimumWidth(250)
            scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

            if self.colors:
                scroll_area.setStyleSheet(f"""
                    QScrollArea {{
                        background-color: {self.colors.background_secondary};
                        border: none;
                    }}
                    QCheckBox {{
                        color: {self.colors.text_primary};
                        padding: 4px;
                    }}
                    QCheckBox:hover {{
                        background-color: {self.colors.background_tertiary};
                        border-radius: 2px;
                    }}
                    QCheckBox:disabled {{
                        color: {self.colors.text_secondary};
                    }}
                """)

            scroll_action = QWidgetAction(self)
            scroll_action.setDefaultWidget(scroll_area)
            self.menu.addAction(scroll_action)

            self.menu.addSeparator()

            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)

            create_btn = QPushButton("New")
            create_btn.clicked.connect(self._on_create_collection)

            manage_btn = QPushButton("Manage")
            manage_btn.clicked.connect(self._on_manage_collections)

            if self.colors:
                button_style = f"""
                    QPushButton {{
                        background-color: {self.colors.primary};
                        color: {self.colors.text_primary};
                        border: none;
                        border-radius: 3px;
                        padding: 6px 12px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors.primary_hover};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors.primary_active};
                    }}
                """
                create_btn.setStyleSheet(button_style)
                manage_btn.setStyleSheet(button_style)

            actions_layout.addWidget(create_btn)
            actions_layout.addWidget(manage_btn)

            actions_action = QWidgetAction(self)
            actions_action.setDefaultWidget(actions_widget)
            self.menu.addAction(actions_action)

        # Show warning if no conversation selected
        if not self.current_conversation_id:
            self.menu.addSeparator()
            warning_action = QAction("⚠ Select a conversation to attach", self)
            warning_action.setEnabled(False)
            self.menu.addAction(warning_action)

    def _on_collection_toggled(self, collection_id: str, is_checked: bool):
        """
        Handle collection checkbox toggle.

        Args:
            collection_id: Collection UUID
            is_checked: Whether checkbox is now checked
        """
        if not self.current_conversation_id:
            logger.warning("⚠ Cannot toggle collection without conversation")
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if is_checked:
                # Attach collection
                success = loop.run_until_complete(
                    self.service.attach_collection_to_conversation(
                        self.current_conversation_id,
                        collection_id
                    )
                )

                if success:
                    self.attached_collection_ids.add(collection_id)
                    self.collection_attached.emit(
                        self.current_conversation_id,
                        collection_id
                    )
                    logger.info(f"✓ Attached collection {collection_id}")
                else:
                    logger.warning(f"⚠ Failed to attach collection {collection_id}")

            else:
                # Detach collection
                success = loop.run_until_complete(
                    self.service.detach_collection_from_conversation(
                        self.current_conversation_id,
                        collection_id
                    )
                )

                if success:
                    self.attached_collection_ids.discard(collection_id)
                    self.collection_detached.emit(
                        self.current_conversation_id,
                        collection_id
                    )
                    logger.info(f"✓ Detached collection {collection_id}")
                else:
                    logger.warning(f"⚠ Failed to detach collection {collection_id}")

            loop.close()

            self._update_button_text()
            self.collections_changed.emit()

        except Exception as e:
            logger.error(f"✗ Error toggling collection: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to {'attach' if is_checked else 'detach'} collection: {e}"
            )

    def _on_create_collection(self):
        """Handle create new collection button click."""
        self.menu.close()

        # Import here to avoid circular dependency
        from ..dialogs.collections_manager_dialog import CollectionsManagerDialog

        dialog = CollectionsManagerDialog(
            parent=self.window(),
            theme_name=self.colors.name if self.colors else "Matrix"
        )

        # Connect signals to refresh on changes
        dialog.collection_created.connect(lambda c: self._populate_menu())
        dialog.collection_updated.connect(lambda c: self._populate_menu())
        dialog.collection_deleted.connect(lambda c: self._populate_menu())

        dialog.exec()

    def _on_manage_collections(self):
        """Handle manage collections button click."""
        self.menu.close()

        # Import here to avoid circular dependency
        from ..dialogs.collections_manager_dialog import CollectionsManagerDialog

        dialog = CollectionsManagerDialog(
            parent=self.window(),
            theme_name=self.colors.name if self.colors else "Matrix"
        )

        # Connect signals to refresh on changes
        dialog.collection_created.connect(lambda c: self._populate_menu())
        dialog.collection_updated.connect(lambda c: self._populate_menu())
        dialog.collection_deleted.connect(lambda c: self._populate_menu())

        dialog.exec()

    def get_attached_collections(self) -> List[FileCollection]:
        """
        Get all collections attached to the current conversation.

        Returns:
            List of FileCollection objects
        """
        if not self.current_conversation_id:
            return []

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            collections = loop.run_until_complete(
                self.service.get_conversation_collections(
                    self.current_conversation_id
                )
            )
            loop.close()

            return collections

        except Exception as e:
            logger.error(f"✗ Error getting attached collections: {e}")
            return []

    def refresh(self):
        """Refresh the widget state (reload attached collections)."""
        if self.current_conversation_id:
            self._load_attached_collections()

    def has_attached_collections(self) -> bool:
        """
        Check if current conversation has any attached collections.

        Returns:
            True if collections are attached, False otherwise
        """
        return len(self.attached_collection_ids) > 0
