"""
RecipeLibrary -- list widget showing saved recipes with management actions.

Displays a compact list of recipes from ``DocumentStudioState`` with
buttons to create, edit, delete, and apply recipes.  Auto-refreshes
when recipes are added or removed via state signals.

Layout:
+------------------------------------------+
|  Recipes                           [+]   |
+------------------------------------------+
|  QListWidget (max 120px)                 |
|    - Corporate Memo                      |
|    - APA Format                          |
|    - Quick Clean                         |
+------------------------------------------+
|  [Edit]  [Delete]  [Apply]              |
+------------------------------------------+
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .studio_state import DocumentStudioState

# Theme imports -- graceful fallback when running outside the full app.
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.document_studio.recipe_library")


class RecipeLibrary(QFrame):
    """
    A list widget showing saved recipes with management actions.

    Signals
    -------
    recipe_selected(str)
        Emitted when a recipe is clicked.  Payload is ``recipe_id``.
    create_requested()
        Emitted when the "+" button is clicked.
    edit_requested(str)
        Emitted when *Edit* is clicked.  Payload is ``recipe_id``.
    delete_requested(str)
        Emitted when *Delete* is clicked.  Payload is ``recipe_id``.
    apply_requested(str)
        Emitted when *Apply* is clicked.  Payload is ``recipe_id``.
    """

    recipe_selected = pyqtSignal(str)
    create_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    apply_requested = pyqtSignal(str)

    def __init__(
        self,
        state: DocumentStudioState,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self.setObjectName("RecipeLibrary")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._build_ui()
        self._connect_state_signals()
        self._refresh_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the library widget tree."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Header row: title + "+" button -------------------------------
        header = QFrame()
        header.setObjectName("RecipeLibraryHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 6, 6)
        header_layout.setSpacing(6)

        title = QLabel("Recipes")
        title.setObjectName("RecipeLibraryTitle")
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header_layout.addWidget(title)

        self._new_btn = QToolButton()
        self._new_btn.setObjectName("RecipeLibraryNewBtn")
        self._new_btn.setText("+")
        self._new_btn.setToolTip("Create new recipe")
        self._new_btn.setFixedSize(24, 24)
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self.create_requested.emit)
        header_layout.addWidget(self._new_btn)

        root.addWidget(header)

        # --- Recipe list --------------------------------------------------
        self._list_widget = QListWidget()
        self._list_widget.setObjectName("RecipeLibraryList")
        self._list_widget.setMaximumHeight(120)
        self._list_widget.setAlternatingRowColors(False)
        self._list_widget.currentItemChanged.connect(self._on_item_changed)
        root.addWidget(self._list_widget)

        # --- Action buttons -----------------------------------------------
        btn_bar = QFrame()
        btn_bar.setObjectName("RecipeLibraryBtnBar")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(10, 4, 10, 6)
        btn_layout.setSpacing(6)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setObjectName("RecipeLibraryEditBtn")
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("RecipeLibraryDeleteBtn")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self._delete_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setObjectName("RecipeLibraryApplyBtn")
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply_clicked)
        btn_layout.addWidget(self._apply_btn)

        btn_layout.addStretch()

        root.addWidget(btn_bar)

    # ------------------------------------------------------------------
    # State signal connections
    # ------------------------------------------------------------------

    def _connect_state_signals(self) -> None:
        """Wire up state signals for auto-refresh."""
        self._state.recipe_saved.connect(self._on_recipe_changed)
        self._state.recipe_removed.connect(self._on_recipe_changed)

    def _on_recipe_changed(self, _recipe_id: str) -> None:
        """Refresh the list when a recipe is added, updated, or removed."""
        self._refresh_list()

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        """Rebuild the list widget from current state recipes."""
        # Remember the currently selected recipe_id so we can re-select it.
        previous_id = self._selected_recipe_id()

        self._list_widget.blockSignals(True)
        self._list_widget.clear()

        for recipe_id, recipe in self._state.recipes.items():
            item = QListWidgetItem(recipe.name)
            item.setData(Qt.ItemDataRole.UserRole, recipe_id)
            self._list_widget.addItem(item)

        # Try to re-select the previously selected recipe.
        restored = False
        if previous_id:
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == previous_id:
                    self._list_widget.setCurrentItem(item)
                    restored = True
                    break

        self._list_widget.blockSignals(False)

        # Update button states
        if not restored:
            self._update_action_buttons(None)

    def _selected_recipe_id(self) -> Optional[str]:
        """Return the recipe_id of the currently selected item, or None."""
        item = self._list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_item_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        """Handle list selection change."""
        recipe_id: Optional[str] = None
        if current is not None:
            recipe_id = current.data(Qt.ItemDataRole.UserRole)

        self._update_action_buttons(recipe_id)

        # Update state active_recipe_id
        self._state.active_recipe_id = recipe_id

        if recipe_id:
            self.recipe_selected.emit(recipe_id)

    def _on_edit_clicked(self) -> None:
        """Emit ``edit_requested`` for the selected recipe."""
        recipe_id = self._selected_recipe_id()
        if recipe_id:
            self.edit_requested.emit(recipe_id)

    def _on_delete_clicked(self) -> None:
        """Emit ``delete_requested`` for the selected recipe."""
        recipe_id = self._selected_recipe_id()
        if recipe_id:
            self.delete_requested.emit(recipe_id)

    def _on_apply_clicked(self) -> None:
        """Emit ``apply_requested`` for the selected recipe."""
        recipe_id = self._selected_recipe_id()
        if recipe_id:
            self.apply_requested.emit(recipe_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_action_buttons(self, recipe_id: Optional[str]) -> None:
        """Enable or disable action buttons based on selection."""
        has_selection = recipe_id is not None
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)
        self._apply_btn.setEnabled(has_selection)

    # ------------------------------------------------------------------
    # Theme support
    # ------------------------------------------------------------------

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the library widget.

        Parameters
        ----------
        colors : ColorSystem (or compatible object)
            Provides semantic colour attributes used for styling.
        """
        if not THEME_AVAILABLE or not colors:
            return

        bg_primary = getattr(colors, "background_primary", "#2b2b2b")
        bg_secondary = getattr(colors, "background_secondary", "#333333")
        bg_tertiary = getattr(colors, "background_tertiary", "#3a3a3a")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        text_disabled = getattr(colors, "text_disabled", "#888888")
        border_secondary = getattr(colors, "border_secondary", "#333333")
        primary = getattr(colors, "primary", "#4CAF50")
        interactive_hover = getattr(colors, "interactive_hover", "#5a5a5a")

        # Library frame
        self.setStyleSheet(f"""
            QFrame#RecipeLibrary {{
                background-color: {bg_primary};
                border: none;
            }}
        """)

        # Header
        header = self.findChild(QFrame, "RecipeLibraryHeader")
        if header:
            header.setStyleSheet(f"""
                QFrame#RecipeLibraryHeader {{
                    background-color: {bg_secondary};
                    border: none;
                    border-bottom: 1px solid {border_secondary};
                }}
            """)

        # Title label
        title = self.findChild(QLabel, "RecipeLibraryTitle")
        if title:
            title.setStyleSheet(
                f"color: {text_primary}; font-weight: bold; font-size: 13px; "
                f"background: transparent; border: none;"
            )

        # "+" button
        if THEME_AVAILABLE and colors:
            ButtonStyleManager.apply_unified_button_style(
                self._new_btn, colors, "tool", "icon", "normal"
            )

        # List widget
        self._list_widget.setStyleSheet(f"""
            QListWidget#RecipeLibraryList {{
                background-color: {bg_primary};
                color: {text_primary};
                border: none;
                border-bottom: 1px solid {border_secondary};
                font-size: 12px;
                outline: none;
            }}
            QListWidget#RecipeLibraryList::item {{
                padding: 4px 10px;
                border: none;
            }}
            QListWidget#RecipeLibraryList::item:selected {{
                background-color: {primary};
                color: {text_primary};
            }}
            QListWidget#RecipeLibraryList::item:hover {{
                background-color: {interactive_hover};
            }}
        """)

        # Action button bar
        btn_bar = self.findChild(QFrame, "RecipeLibraryBtnBar")
        if btn_bar:
            btn_bar.setStyleSheet(f"""
                QFrame#RecipeLibraryBtnBar {{
                    background-color: {bg_secondary};
                    border: none;
                }}
            """)

        # Action buttons (Edit, Delete, Apply)
        btn_style = f"""
            QPushButton {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {interactive_hover};
            }}
            QPushButton:disabled {{
                color: {text_disabled};
            }}
        """
        self._edit_btn.setStyleSheet(btn_style)
        self._delete_btn.setStyleSheet(btn_style)

        # Apply button -- use primary colour to emphasize
        self._apply_btn.setStyleSheet(f"""
            QPushButton#RecipeLibraryApplyBtn {{
                background-color: {primary};
                color: {text_primary};
                border: 1px solid {primary};
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#RecipeLibraryApplyBtn:hover {{
                background-color: {interactive_hover};
            }}
            QPushButton#RecipeLibraryApplyBtn:disabled {{
                color: {text_disabled};
                background-color: {bg_tertiary};
                border-color: {border_secondary};
            }}
        """)
