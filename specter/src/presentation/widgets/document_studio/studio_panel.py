"""
DocumentStudioPanel — main panel widget for the Document Studio.

Orchestrates the header bar, stacked views (list, preview, diff, recipe
editor), batch controls, document cards, and a status bar.  Connects to
``DocumentStudioState`` signals to keep the UI in sync with the data model.

Layout:
┌─────────────────────────────────────────┐
│  StudioHeaderBar (title + collapse)     │
├─────────────────────────────────────────┤
│  QStackedWidget                         │
│  ┌─ View 0: List ─────────────────────┐ │
│  │  Batch controls toolbar            │ │
│  │  ┌────────────────────────────────┐ │ │
│  │  │ QScrollArea                    │ │ │
│  │  │   DocumentCard                 │ │ │
│  │  │   DocumentCard                 │ │ │
│  │  │   ...                          │ │ │
│  │  │   (or empty-hint label)        │ │ │
│  │  └────────────────────────────────┘ │ │
│  │  QProgressBar (batch, hidden)      │ │
│  └────────────────────────────────────┘ │
│  View 1: Preview  (placeholder)         │
│  View 2: Diff     (placeholder)         │
│  View 3: Recipe   (placeholder)         │
├─────────────────────────────────────────┤
│  Status bar (file count · errors)       │
└─────────────────────────────────────────┘
"""

import logging
import os
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .document_card import DocumentCard
from .studio_header_bar import StudioHeaderBar
from .studio_state import DocumentEntry, DocumentStatus, DocumentStudioState

# Theme imports — graceful fallback when running outside the full app.
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager, StyleTemplates
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.document_studio.panel")

# ---------------------------------------------------------------------------
# View indices for the QStackedWidget
# ---------------------------------------------------------------------------
VIEW_LIST = 0
VIEW_PREVIEW = 1
VIEW_DIFF = 2
VIEW_RECIPE_EDITOR = 3


class DocumentStudioPanel(QFrame):
    """
    Main panel widget for the Document Studio.

    Owns the header bar, a QStackedWidget with four view pages, and a
    status bar.  The list view (view 0) contains batch controls, a
    scrollable list of ``DocumentCard`` widgets, and a batch progress bar.

    Signals
    -------
    collapse_requested()
        Forwarded from the header bar's collapse button.
    apply_recipe_requested(str, list)
        Emitted when "Apply Recipe" is clicked.  Payload is
        ``(recipe_id, selected_file_paths)``.
    files_dropped(list)
        Emitted when ``.docx`` files are dropped onto the panel.
    """

    collapse_requested = pyqtSignal()
    apply_recipe_requested = pyqtSignal(str, list)
    files_dropped = pyqtSignal(list)

    # Minimum / preferred width for the panel.
    _MIN_WIDTH = 280
    _PREFERRED_WIDTH = 340

    def __init__(
        self,
        state: DocumentStudioState,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._cards: Dict[str, DocumentCard] = {}
        self._current_colors = None

        self.setObjectName("DocumentStudioPanel")
        self.setMinimumWidth(self._MIN_WIDTH)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self._build_ui()
        self._connect_state_signals()
        self._refresh_status_bar()
        self._apply_default_theme()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the entire panel widget tree."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Header bar ---------------------------------------------------
        self._header = StudioHeaderBar(self)
        self._header.collapse_requested.connect(self.collapse_requested.emit)
        root.addWidget(self._header)

        # --- Stacked widget (4 views) -------------------------------------
        self._stack = QStackedWidget(self)
        root.addWidget(self._stack, 1)  # stretch factor 1

        # View 0 — list view
        self._stack.addWidget(self._build_list_view())

        # Views 1-3 — placeholders
        for label_text in ("Preview", "Diff", "Recipe Editor"):
            placeholder = QLabel(f"{label_text} — coming soon")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setObjectName("StudioPlaceholder")
            self._stack.addWidget(placeholder)

        self._stack.setCurrentIndex(VIEW_LIST)

        # --- Status bar ---------------------------------------------------
        self._status_bar = QFrame(self)
        self._status_bar.setObjectName("StudioStatusBar")
        self._status_bar.setFixedHeight(26)
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(10, 2, 10, 2)
        status_layout.setSpacing(8)

        self._file_count_label = QLabel("0 files")
        self._file_count_label.setObjectName("StudioStatusText")
        status_layout.addWidget(self._file_count_label)

        self._error_count_label = QLabel("")
        self._error_count_label.setObjectName("StudioStatusError")
        status_layout.addWidget(self._error_count_label)

        status_layout.addStretch()

        self._batch_status_label = QLabel("")
        self._batch_status_label.setObjectName("StudioStatusBatch")
        status_layout.addWidget(self._batch_status_label)

        root.addWidget(self._status_bar)

    def _build_list_view(self) -> QWidget:
        """Build view 0 — the document list with batch controls."""
        container = QWidget()
        container.setObjectName("StudioListView")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Batch controls toolbar --------------------------------------
        toolbar = QFrame()
        toolbar.setObjectName("StudioBatchToolbar")
        toolbar.setFixedHeight(36)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.setObjectName("StudioSelectAllBtn")
        self._select_all_btn.setToolTip("Select all documents")
        self._select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_btn.clicked.connect(self._on_select_all)
        tb_layout.addWidget(self._select_all_btn)

        self._select_none_btn = QPushButton("None")
        self._select_none_btn.setObjectName("StudioSelectNoneBtn")
        self._select_none_btn.setToolTip("Deselect all documents")
        self._select_none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_none_btn.clicked.connect(self._on_select_none)
        tb_layout.addWidget(self._select_none_btn)

        tb_layout.addStretch()

        self._recipe_combo = QComboBox()
        self._recipe_combo.setObjectName("StudioRecipeCombo")
        self._recipe_combo.setToolTip("Choose a recipe to apply")
        self._recipe_combo.setMinimumWidth(100)
        self._recipe_combo.addItem("(no recipe)", "")
        tb_layout.addWidget(self._recipe_combo)

        self._apply_recipe_btn = QPushButton("Apply Recipe")
        self._apply_recipe_btn.setObjectName("StudioApplyRecipeBtn")
        self._apply_recipe_btn.setToolTip("Apply selected recipe to checked documents")
        self._apply_recipe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_recipe_btn.clicked.connect(self._on_apply_recipe)
        tb_layout.addWidget(self._apply_recipe_btn)

        layout.addWidget(toolbar)

        # --- Scroll area with card list -----------------------------------
        self._scroll_area = QScrollArea()
        self._scroll_area.setObjectName("StudioScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._card_container = QWidget()
        self._card_container.setObjectName("StudioCardContainer")
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(8, 8, 8, 8)
        self._card_layout.setSpacing(6)
        self._card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty-state hint
        self._empty_hint = QLabel("Drop DOCX files here\u2026")
        self._empty_hint.setObjectName("StudioEmptyHint")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setMinimumHeight(80)
        self._card_layout.addWidget(self._empty_hint)

        self._scroll_area.setWidget(self._card_container)
        layout.addWidget(self._scroll_area, 1)  # stretch

        # --- Batch progress bar (hidden by default) -----------------------
        self._batch_progress = QProgressBar()
        self._batch_progress.setObjectName("StudioBatchProgress")
        self._batch_progress.setRange(0, 100)
        self._batch_progress.setTextVisible(True)
        self._batch_progress.setFixedHeight(18)
        self._batch_progress.setVisible(False)
        layout.addWidget(self._batch_progress)

        return container

    # ------------------------------------------------------------------
    # State signal connections
    # ------------------------------------------------------------------

    def _connect_state_signals(self) -> None:
        """Wire up DocumentStudioState signals to local handlers."""
        self._state.document_added.connect(self._on_document_added)
        self._state.document_removed.connect(self._on_document_removed)
        self._state.document_status_changed.connect(self._on_status_changed)
        self._state.document_progress_changed.connect(self._on_progress_changed)
        self._state.selection_changed.connect(self._on_selection_changed)
        self._state.batch_started.connect(self._on_batch_started)
        self._state.batch_progress.connect(self._on_batch_progress)
        self._state.batch_completed.connect(self._on_batch_completed)
        self._state.recipe_saved.connect(self._on_recipe_saved)
        self._state.recipe_removed.connect(self._on_recipe_removed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> DocumentStudioState:
        """The backing state object."""
        return self._state

    def set_view(self, index: int) -> None:
        """Switch the stacked widget to the given view index."""
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)

    def current_view(self) -> int:
        """Return the current view index."""
        return self._stack.currentIndex()

    def get_card(self, file_path: str) -> Optional[DocumentCard]:
        """Return the card for *file_path*, or ``None``."""
        return self._cards.get(file_path)

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept drag if it contains file URLs."""
        mime = event.mimeData()
        if mime and mime.hasUrls():
            # Accept if at least one URL is a .docx file
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".docx"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        """Keep accepting during drag movement."""
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Handle dropped files — emit ``files_dropped`` for .docx files."""
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            event.ignore()
            return

        docx_paths: List[str] = []
        for url in mime.urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith(".docx"):
                    docx_paths.append(path)

        if docx_paths:
            event.acceptProposedAction()
            self.files_dropped.emit(docx_paths)
            logger.info("Dropped %d DOCX file(s) onto studio panel", len(docx_paths))
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # State event handlers
    # ------------------------------------------------------------------

    def _on_document_added(self, file_path: str) -> None:
        """Create a card for the newly added document."""
        entry = self._state.documents.get(file_path)
        if not entry:
            return
        if file_path in self._cards:
            # Already have a card — just refresh
            self._cards[file_path].update_entry(entry)
            return

        card = DocumentCard(entry, parent=self._card_container)
        card.remove_requested.connect(self._on_card_remove_requested)
        card.selection_toggled.connect(self._on_card_selection_toggled)
        card.preview_requested.connect(self._on_card_preview_requested)

        # Apply current theme to the new card
        if self._current_colors is not None:
            card.apply_theme(self._current_colors)

        self._cards[file_path] = card
        self._card_layout.addWidget(card)

        # Hide empty hint when we have cards
        self._empty_hint.setVisible(False)
        self._refresh_status_bar()

    def _on_document_removed(self, file_path: str) -> None:
        """Remove the card for the given file path."""
        card = self._cards.pop(file_path, None)
        if card:
            self._card_layout.removeWidget(card)
            card.deleteLater()

        # Show empty hint if no cards remain
        if not self._cards:
            self._empty_hint.setVisible(True)
        self._refresh_status_bar()

    def _on_status_changed(self, file_path: str, status_value: str) -> None:
        """Update the card's status display."""
        card = self._cards.get(file_path)
        if not card:
            return
        try:
            status = DocumentStatus(status_value)
        except ValueError:
            logger.warning("Unknown status value: %s", status_value)
            return
        entry = self._state.documents.get(file_path)
        error = entry.error_message if entry else ""
        card.set_status(status, error)

        # Re-apply theme so border colour updates
        if self._current_colors is not None:
            card.apply_theme(self._current_colors)

        self._refresh_status_bar()

    def _on_progress_changed(self, file_path: str, progress: float) -> None:
        """Update the card's progress bar."""
        card = self._cards.get(file_path)
        if card:
            card.set_progress(progress)

    def _on_selection_changed(self) -> None:
        """Sync card checkboxes with state after bulk select/deselect."""
        for file_path, card in self._cards.items():
            entry = self._state.documents.get(file_path)
            if entry:
                card.set_selected(entry.selected)

    def _on_batch_started(self, recipe_id: str) -> None:
        """Show the batch progress bar and disable controls."""
        self._batch_progress.setValue(0)
        self._batch_progress.setVisible(True)
        self._apply_recipe_btn.setEnabled(False)
        self._batch_status_label.setText("Batch running\u2026")

    def _on_batch_progress(self, completed: int, total: int) -> None:
        """Update the batch progress bar."""
        if total > 0:
            pct = int((completed / total) * 100)
            self._batch_progress.setValue(pct)
            self._batch_progress.setFormat(f"{completed}/{total}")
            self._batch_status_label.setText(f"{completed}/{total}")

    def _on_batch_completed(self, all_success: bool, summary: str) -> None:
        """Hide batch progress and re-enable controls."""
        self._batch_progress.setVisible(False)
        self._apply_recipe_btn.setEnabled(True)
        status = "Batch complete" if all_success else "Batch finished with errors"
        self._batch_status_label.setText(status)
        logger.info("Batch completed: success=%s, summary=%s", all_success, summary)

    def _on_recipe_saved(self, recipe_id: str) -> None:
        """Add or update the recipe in the combo box."""
        recipe = self._state.get_recipe(recipe_id)
        if not recipe:
            return
        # Check if already in combo
        idx = self._recipe_combo.findData(recipe_id)
        if idx >= 0:
            self._recipe_combo.setItemText(idx, recipe.name)
        else:
            self._recipe_combo.addItem(recipe.name, recipe_id)

    def _on_recipe_removed(self, recipe_id: str) -> None:
        """Remove the recipe from the combo box."""
        idx = self._recipe_combo.findData(recipe_id)
        if idx >= 0:
            self._recipe_combo.removeItem(idx)

    # ------------------------------------------------------------------
    # Card signal handlers
    # ------------------------------------------------------------------

    def _on_card_remove_requested(self, file_path: str) -> None:
        """Forward card removal to the state object."""
        self._state.remove_document(file_path)

    def _on_card_selection_toggled(self, file_path: str, selected: bool) -> None:
        """Forward card selection toggle to the state object."""
        entry = self._state.documents.get(file_path)
        if entry:
            entry.selected = selected
            self._state.selection_changed.emit()

    def _on_card_preview_requested(self, file_path: str) -> None:
        """Switch to the preview view (placeholder for now)."""
        logger.debug("Preview requested for: %s", file_path)
        self.set_view(VIEW_PREVIEW)

    # ------------------------------------------------------------------
    # Toolbar button handlers
    # ------------------------------------------------------------------

    def _on_select_all(self) -> None:
        """Select all documents via state."""
        self._state.select_all()

    def _on_select_none(self) -> None:
        """Deselect all documents via state."""
        self._state.deselect_all()

    def _on_apply_recipe(self) -> None:
        """Emit ``apply_recipe_requested`` with the chosen recipe and selected files."""
        recipe_id = self._recipe_combo.currentData()
        if not recipe_id:
            logger.debug("No recipe selected — ignoring apply")
            return
        selected = self._state.get_selected_paths()
        if not selected:
            logger.debug("No files selected — ignoring apply")
            return
        self.apply_recipe_requested.emit(recipe_id, selected)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _refresh_status_bar(self) -> None:
        """Update the file-count and error-count labels."""
        total = len(self._state.documents)
        suffix = "file" if total == 1 else "files"
        self._file_count_label.setText(f"{total} {suffix}")

        errors = sum(
            1
            for e in self._state.documents.values()
            if e.status == DocumentStatus.FAILED
        )
        if errors > 0:
            err_suffix = "error" if errors == 1 else "errors"
            self._error_count_label.setText(f"\u00b7 {errors} {err_suffix}")
            self._error_count_label.setVisible(True)
        else:
            self._error_count_label.setText("")
            self._error_count_label.setVisible(False)

    # ------------------------------------------------------------------
    # Theme support
    # ------------------------------------------------------------------

    def _apply_default_theme(self) -> None:
        """Try to apply the current theme at construction time."""
        if not THEME_AVAILABLE:
            return
        try:
            tm = get_theme_manager()
            if tm:
                colors = tm.get_colors()
                if colors:
                    self.apply_theme(colors)
        except Exception:
            logger.debug("Theme manager not available at panel construction")

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the panel and all children.

        Parameters
        ----------
        colors : ColorSystem (or compatible object)
            Provides semantic colour attributes used for styling.
        """
        self._current_colors = colors

        bg_primary = getattr(colors, "background_primary", "#2b2b2b")
        bg_secondary = getattr(colors, "background_secondary", "#333333")
        bg_tertiary = getattr(colors, "background_tertiary", "#3a3a3a")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        text_disabled = getattr(colors, "text_disabled", "#888888")
        border_primary = getattr(colors, "border_primary", "#444444")
        border_secondary = getattr(colors, "border_secondary", "#333333")
        primary = getattr(colors, "primary", "#4CAF50")
        status_error = getattr(colors, "status_error", "#F44336")
        interactive_hover = getattr(colors, "interactive_hover", "#5a5a5a")

        # Panel frame
        self.setStyleSheet(f"""
            QFrame#DocumentStudioPanel {{
                background-color: {bg_primary};
                border-left: 1px solid {border_primary};
            }}
        """)

        # Header bar
        self._header.apply_theme(colors)

        # Batch toolbar
        toolbar_style = f"""
            QFrame#StudioBatchToolbar {{
                background-color: {bg_secondary};
                border: none;
                border-bottom: 1px solid {border_secondary};
            }}
        """
        # Find the toolbar widget and apply
        toolbar = self.findChild(QFrame, "StudioBatchToolbar")
        if toolbar:
            toolbar.setStyleSheet(toolbar_style)

        # Toolbar buttons
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
        for btn in (self._select_all_btn, self._select_none_btn):
            btn.setStyleSheet(btn_style)

        # Apply recipe button — use primary colour
        self._apply_recipe_btn.setStyleSheet(f"""
            QPushButton#StudioApplyRecipeBtn {{
                background-color: {primary};
                color: {text_primary};
                border: 1px solid {primary};
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#StudioApplyRecipeBtn:hover {{
                background-color: {interactive_hover};
            }}
            QPushButton#StudioApplyRecipeBtn:disabled {{
                color: {text_disabled};
                background-color: {bg_tertiary};
                border-color: {border_secondary};
            }}
        """)

        # Recipe combo box
        self._recipe_combo.setStyleSheet(f"""
            QComboBox#StudioRecipeCombo {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 12px;
            }}
            QComboBox#StudioRecipeCombo::drop-down {{
                border: none;
            }}
            QComboBox#StudioRecipeCombo QAbstractItemView {{
                background-color: {bg_secondary};
                color: {text_primary};
                selection-background-color: {primary};
                border: 1px solid {border_secondary};
            }}
        """)

        # Scroll area and card container
        self._scroll_area.setStyleSheet(f"""
            QScrollArea#StudioScrollArea {{
                background-color: {bg_primary};
                border: none;
            }}
        """)
        self._card_container.setStyleSheet(f"""
            QWidget#StudioCardContainer {{
                background-color: {bg_primary};
            }}
        """)

        # Empty hint
        self._empty_hint.setStyleSheet(f"""
            QLabel#StudioEmptyHint {{
                color: {text_disabled};
                font-size: 13px;
                font-style: italic;
                background: transparent;
                border: none;
                padding: 20px;
            }}
        """)

        # Placeholder labels in stacked widget
        for i in range(VIEW_PREVIEW, self._stack.count()):
            widget = self._stack.widget(i)
            if isinstance(widget, QLabel):
                widget.setStyleSheet(f"""
                    QLabel#StudioPlaceholder {{
                        color: {text_disabled};
                        font-size: 14px;
                        font-style: italic;
                        background-color: {bg_primary};
                        border: none;
                    }}
                """)

        # Batch progress bar
        self._batch_progress.setStyleSheet(f"""
            QProgressBar#StudioBatchProgress {{
                background-color: {bg_tertiary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                text-align: center;
                font-size: 11px;
                color: {text_primary};
                margin: 4px 8px;
            }}
            QProgressBar#StudioBatchProgress::chunk {{
                background-color: {primary};
                border-radius: 2px;
            }}
        """)

        # Status bar
        self._status_bar.setStyleSheet(f"""
            QFrame#StudioStatusBar {{
                background-color: {bg_secondary};
                border: none;
                border-top: 1px solid {border_secondary};
            }}
        """)
        self._file_count_label.setStyleSheet(
            f"color: {text_secondary}; font-size: 11px; background: transparent;"
        )
        self._error_count_label.setStyleSheet(
            f"color: {status_error}; font-size: 11px; background: transparent;"
        )
        self._batch_status_label.setStyleSheet(
            f"color: {text_secondary}; font-size: 11px; background: transparent;"
        )

        # Apply theme to all existing cards
        for card in self._cards.values():
            card.apply_theme(colors)
