"""
DocumentCard — visual card widget for a single document in the Document Studio.

Displays filename, metadata (page count, file size), a progress bar for
processing, and status text with color coding.  Emits signals for click,
selection toggle, remove, and preview actions.

Layout:
┌─────────────────────────────────────┐
│ [☑] 📄 quarterly-report.docx   [✕] │
│     12 pages · 245 KB               │
│     [████████░░] 80%                 │
│     Status: Processing...            │
└─────────────────────────────────────┘
"""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .studio_state import DocumentEntry, DocumentStatus

# Theme imports — graceful fallback when running outside the full app.
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.document_studio.card")

# ---------------------------------------------------------------------------
# File-type emoji mapping
# ---------------------------------------------------------------------------
_FILE_TYPE_ICONS = {
    ".docx": "\U0001F4C4",   # 📄
    ".doc": "\U0001F4C4",
    ".pdf": "\U0001F4D5",    # 📕
    ".txt": "\U0001F4DD",    # 📝
    ".rtf": "\U0001F4DD",
    ".odt": "\U0001F4C4",
    ".xlsx": "\U0001F4CA",   # 📊
    ".xls": "\U0001F4CA",
    ".csv": "\U0001F4CA",
    ".pptx": "\U0001F4CA",
    ".ppt": "\U0001F4CA",
    ".md": "\U0001F4DD",
    ".html": "\U0001F310",   # 🌐
    ".htm": "\U0001F310",
    ".json": "\U0001F4CB",   # 📋
    ".xml": "\U0001F4CB",
    ".yaml": "\U0001F4CB",
    ".yml": "\U0001F4CB",
}
_DEFAULT_FILE_ICON = "\U0001F4C4"  # 📄


def _file_type_icon(filename: str) -> str:
    """Return an emoji for *filename* based on its extension."""
    _, ext = os.path.splitext(filename)
    return _FILE_TYPE_ICONS.get(ext.lower(), _DEFAULT_FILE_ICON)


def _format_file_size(size_bytes: int) -> str:
    """Return a human-readable file-size string (e.g. '245 KB')."""
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ---------------------------------------------------------------------------
# Status → display text
# ---------------------------------------------------------------------------
_STATUS_LABELS = {
    DocumentStatus.PENDING: "Pending",
    DocumentStatus.QUEUED: "Queued",
    DocumentStatus.PROCESSING: "Processing\u2026",
    DocumentStatus.COMPLETED: "Completed",
    DocumentStatus.FAILED: "Failed",
}


class DocumentCard(QFrame):
    """
    A card-style QFrame representing a single document in the studio.

    Signals
    -------
    clicked(str)
        Emitted when the card body is clicked.  Payload is ``file_path``.
    selection_toggled(str, bool)
        Emitted when the checkbox state changes.
    remove_requested(str)
        Emitted when the remove (✕) button is clicked.
    preview_requested(str)
        Emitted on double-click.  Payload is ``file_path``.
    """

    clicked = pyqtSignal(str)
    selection_toggled = pyqtSignal(str, bool)
    remove_requested = pyqtSignal(str)
    preview_requested = pyqtSignal(str)

    # Maximum characters for the filename before it gets elided.
    _MAX_FILENAME_CHARS = 35

    def __init__(
        self,
        entry: DocumentEntry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._entry = entry
        self._file_path = entry.file_path

        self.setObjectName("DocumentCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(80)

        self._build_ui()
        self._refresh_from_entry()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the card's widget tree."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(4)

        # --- Row 1: checkbox, icon+filename, remove button ----------------
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._checkbox = QCheckBox()
        self._checkbox.setToolTip("Select for batch processing")
        self._checkbox.stateChanged.connect(self._on_checkbox_toggled)
        row1.addWidget(self._checkbox)

        self._icon_label = QLabel()
        self._icon_label.setFixedWidth(22)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self._icon_label)

        self._filename_label = QLabel()
        self._filename_label.setObjectName("DocumentCardFilename")
        self._filename_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        row1.addWidget(self._filename_label)

        self._remove_btn = QPushButton("\u2715")  # ✕
        self._remove_btn.setObjectName("DocumentCardRemoveBtn")
        self._remove_btn.setFixedSize(22, 22)
        self._remove_btn.setToolTip("Remove document from studio")
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        row1.addWidget(self._remove_btn)

        root_layout.addLayout(row1)

        # --- Row 2: metadata (page count, file size) ----------------------
        self._meta_label = QLabel()
        self._meta_label.setObjectName("DocumentCardMeta")
        self._meta_label.setContentsMargins(28, 0, 0, 0)  # indent under filename
        root_layout.addWidget(self._meta_label)

        # --- Row 3: progress bar ------------------------------------------
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("DocumentCardProgress")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setContentsMargins(28, 0, 0, 0)
        self._progress_bar.setVisible(False)  # hidden until processing starts
        root_layout.addWidget(self._progress_bar)

        # --- Row 4: status label ------------------------------------------
        self._status_label = QLabel()
        self._status_label.setObjectName("DocumentCardStatus")
        self._status_label.setContentsMargins(28, 0, 0, 0)
        root_layout.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def file_path(self) -> str:
        """The file path this card represents."""
        return self._file_path

    @property
    def entry(self) -> DocumentEntry:
        """Current document entry data."""
        return self._entry

    def update_entry(self, entry: DocumentEntry) -> None:
        """Replace the backing entry and refresh the UI."""
        self._entry = entry
        self._refresh_from_entry()

    def set_status(self, status: DocumentStatus, error: str = "") -> None:
        """Update the displayed status (and optionally the error)."""
        self._entry.status = status
        if error:
            self._entry.error_message = error
        self._refresh_status()

    def set_progress(self, progress: float) -> None:
        """Update the progress bar (0.0 - 1.0)."""
        self._entry.progress = max(0.0, min(1.0, progress))
        self._refresh_progress()

    def set_selected(self, selected: bool) -> None:
        """Programmatically set the checkbox without emitting our own signal."""
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(selected)
        self._checkbox.blockSignals(False)
        self._entry.selected = selected

    def is_selected(self) -> bool:
        """Whether the card's checkbox is checked."""
        return self._checkbox.isChecked()

    # ------------------------------------------------------------------
    # Theme support
    # ------------------------------------------------------------------

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the card.

        Parameters
        ----------
        colors : ColorSystem (or compatible object)
            Provides semantic colour attributes used for styling.
        """
        border_color = self._border_color_for_status(colors, self._entry.status)
        bg = getattr(colors, "background_tertiary", "#3a3a3a")
        bg_hover = getattr(colors, "interactive_hover", "#5a5a5a")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        text_tertiary = getattr(colors, "text_tertiary", "#888888")
        primary = getattr(colors, "primary", "#4CAF50")
        border_sec = getattr(colors, "border_secondary", "#333333")
        status_error = getattr(colors, "status_error", "#F44336")

        # Card frame
        self.setStyleSheet(f"""
            QFrame#DocumentCard {{
                background-color: {bg};
                border: 2px solid {border_color};
                border-radius: 6px;
            }}
            QFrame#DocumentCard:hover {{
                background-color: {bg_hover};
            }}
        """)

        # Filename label
        self._filename_label.setStyleSheet(f"""
            QLabel#DocumentCardFilename {{
                color: {text_primary};
                font-weight: bold;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
        """)

        # Meta label
        self._meta_label.setStyleSheet(f"""
            QLabel#DocumentCardMeta {{
                color: {text_secondary};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
        """)

        # Status label — colour depends on status
        status_color = self._status_text_color(colors, self._entry.status)
        self._status_label.setStyleSheet(f"""
            QLabel#DocumentCardStatus {{
                color: {status_color};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
        """)

        # Progress bar
        progress_bg = getattr(colors, "interactive_normal", "#4a4a4a")
        self._progress_bar.setStyleSheet(f"""
            QProgressBar#DocumentCardProgress {{
                background-color: {progress_bg};
                border: 1px solid {border_sec};
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
                color: {text_primary};
            }}
            QProgressBar#DocumentCardProgress::chunk {{
                background-color: {primary};
                border-radius: 2px;
            }}
        """)

        # Remove button
        self._remove_btn.setStyleSheet(f"""
            QPushButton#DocumentCardRemoveBtn {{
                background: transparent;
                border: none;
                color: {text_tertiary};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton#DocumentCardRemoveBtn:hover {{
                color: {status_error};
            }}
        """)

        # Checkbox styling
        self._checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 4px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {border_sec};
                border-radius: 3px;
                background-color: {bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {primary};
                border-color: {primary};
            }}
        """)

        # Icon label
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: none;
                font-size: 16px;
            }}
        """)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Emit ``clicked`` on left-button press (unless on a child control)."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only emit when the click lands on the card body itself, not on
            # child widgets that already handle their own events.
            child = self.childAt(event.pos())
            if child in (None, self._filename_label, self._meta_label,
                         self._status_label, self._icon_label):
                self.clicked.emit(self._file_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        """Emit ``preview_requested`` on double-click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.preview_requested.emit(self._file_path)
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_from_entry(self) -> None:
        """Synchronise all visual elements with ``self._entry``."""
        entry = self._entry

        # Icon
        self._icon_label.setText(_file_type_icon(entry.filename))

        # Filename — elide if too long
        name = entry.filename
        if len(name) > self._MAX_FILENAME_CHARS:
            name = name[: self._MAX_FILENAME_CHARS - 1] + "\u2026"
        self._filename_label.setText(name)
        self._filename_label.setToolTip(entry.filename)

        # Meta line
        self._refresh_meta()

        # Checkbox
        self.set_selected(entry.selected)

        # Progress & status
        self._refresh_progress()
        self._refresh_status()

    def _refresh_meta(self) -> None:
        """Update the metadata label text."""
        parts = []
        if self._entry.page_count > 0:
            pages = self._entry.page_count
            parts.append(f"{pages} page{'s' if pages != 1 else ''}")
        if self._entry.file_size > 0:
            parts.append(_format_file_size(self._entry.file_size))
        self._meta_label.setText(" \u00b7 ".join(parts) if parts else "")

    def _refresh_progress(self) -> None:
        """Show/hide the progress bar and set its value."""
        is_processing = self._entry.status == DocumentStatus.PROCESSING
        self._progress_bar.setVisible(is_processing)
        if is_processing:
            pct = int(self._entry.progress * 100)
            self._progress_bar.setValue(pct)
            self._progress_bar.setFormat(f"{pct}%")

    def _refresh_status(self) -> None:
        """Update the status label text and visibility."""
        status = self._entry.status
        label = _STATUS_LABELS.get(status, status.value.title())

        if status == DocumentStatus.FAILED and self._entry.error_message:
            label = f"Failed: {self._entry.error_message}"
            self._status_label.setToolTip(self._entry.error_message)
        else:
            self._status_label.setToolTip("")

        self._status_label.setText(f"Status: {label}")

        # Hide status for pending (default state) — cleaner look
        show_status = status != DocumentStatus.PENDING
        self._status_label.setVisible(show_status)

    # ------------------------------------------------------------------
    # Colour helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _border_color_for_status(colors, status: DocumentStatus) -> str:
        """Return the card border colour for the given *status*."""
        if status in (DocumentStatus.PENDING, DocumentStatus.QUEUED):
            return getattr(colors, "text_disabled", "#555555")
        if status == DocumentStatus.PROCESSING:
            return getattr(colors, "primary", "#4CAF50")
        if status == DocumentStatus.COMPLETED:
            return getattr(colors, "status_success", "#4CAF50")
        if status == DocumentStatus.FAILED:
            return getattr(colors, "status_error", "#F44336")
        return getattr(colors, "border_primary", "#444444")

    @staticmethod
    def _status_text_color(colors, status: DocumentStatus) -> str:
        """Return the status label text colour for the given *status*."""
        if status == DocumentStatus.PROCESSING:
            return getattr(colors, "primary", "#4CAF50")
        if status == DocumentStatus.COMPLETED:
            return getattr(colors, "status_success", "#4CAF50")
        if status == DocumentStatus.FAILED:
            return getattr(colors, "status_error", "#F44336")
        # PENDING, QUEUED, or anything else
        return getattr(colors, "text_secondary", "#cccccc")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_checkbox_toggled(self, state: int) -> None:
        """Handle checkbox state change."""
        checked = state == Qt.CheckState.Checked.value
        self._entry.selected = checked
        self.selection_toggled.emit(self._file_path, checked)

    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        self.remove_requested.emit(self._file_path)
