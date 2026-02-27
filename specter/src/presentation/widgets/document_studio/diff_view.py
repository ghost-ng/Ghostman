"""
DiffView — side-by-side before/after comparison view for documents.

Displays the original and formatted versions of a DOCX document with
highlighted diffs (insertions, deletions, replacements) using
``difflib.SequenceMatcher``.

Layout:
┌─────────────────────────────────────────────────┐
│  [← Back]            [Reject]  [Accept]         │
├────────────────────┬────────────────────────────┤
│  "Original"        │  "Formatted"               │
├────────────────────┼────────────────────────────┤
│  QTextBrowser      │  QTextBrowser              │
│  (left pane)       │  (right pane)              │
│                    │                            │
│  deletions/        │  insertions/               │
│  replacements      │  replacements              │
│  highlighted       │  highlighted               │
└────────────────────┴────────────────────────────┘
"""

import difflib
import html
import logging
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# Theme imports — graceful fallback when running outside the full app.
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.document_studio.diff_view")

# ---------------------------------------------------------------------------
# Default diff highlight colours (designed for dark themes)
# ---------------------------------------------------------------------------
_DEFAULT_ADD_COLOR = "#2d6b2d"
_DEFAULT_REMOVE_COLOR = "#6b2d2d"
_DEFAULT_ADD_BG = "rgba(45,107,45,0.25)"
_DEFAULT_REMOVE_BG = "rgba(107,45,45,0.25)"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_text_lines(file_path: str) -> List[str]:
    """
    Extract plain text lines from a DOCX file using python-docx.

    Each paragraph becomes one string in the returned list.
    Returns an empty list if the file cannot be read.

    Parameters
    ----------
    file_path : str
        Absolute path to a ``.docx`` file.

    Returns
    -------
    list[str]
        List of paragraph text strings.
    """
    try:
        from docx import Document as DocxDocument
    except ImportError:
        logger.warning("python-docx not available — cannot extract text from %s", file_path)
        return []

    try:
        doc = DocxDocument(file_path)
        return [para.text for para in doc.paragraphs]
    except Exception as exc:
        logger.error("Failed to extract text from %s: %s", file_path, exc)
        return []


def _build_diff_html(
    original_lines: List[str],
    formatted_lines: List[str],
    add_color: str = _DEFAULT_ADD_COLOR,
    remove_color: str = _DEFAULT_REMOVE_COLOR,
    add_bg: str = _DEFAULT_ADD_BG,
    remove_bg: str = _DEFAULT_REMOVE_BG,
) -> Tuple[str, str]:
    """
    Compute a side-by-side diff and return highlighted HTML for both panes.

    Uses ``difflib.SequenceMatcher`` to identify equal, replace, delete,
    and insert blocks. All text content is HTML-escaped before insertion.

    Parameters
    ----------
    original_lines : list[str]
        Lines from the original document.
    formatted_lines : list[str]
        Lines from the formatted document.
    add_color : str
        CSS colour for added-text left border.
    remove_color : str
        CSS colour for removed-text left border.
    add_bg : str
        CSS background colour for added blocks (right pane).
    remove_bg : str
        CSS background colour for removed blocks (left pane).

    Returns
    -------
    tuple[str, str]
        ``(original_html, formatted_html)`` with highlighted changes.
    """
    matcher = difflib.SequenceMatcher(None, original_lines, formatted_lines)

    left_parts: List[str] = []
    right_parts: List[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in original_lines[i1:i2]:
                escaped = html.escape(line) if line else "&nbsp;"
                left_parts.append(f"<p style='margin:2px 0;'>{escaped}</p>")
                right_parts.append(f"<p style='margin:2px 0;'>{escaped}</p>")

        elif tag == "replace":
            # Left pane: show removed lines with remove background
            for line in original_lines[i1:i2]:
                escaped = html.escape(line) if line else "&nbsp;"
                left_parts.append(
                    f"<p style='margin:2px 0; background:{remove_bg}; "
                    f"border-left:3px solid {remove_color}; "
                    f"padding-left:6px;'>{escaped}</p>"
                )
            # Right pane: show added lines with add background
            for line in formatted_lines[j1:j2]:
                escaped = html.escape(line) if line else "&nbsp;"
                right_parts.append(
                    f"<p style='margin:2px 0; background:{add_bg}; "
                    f"border-left:3px solid {add_color}; "
                    f"padding-left:6px;'>{escaped}</p>"
                )
            # Pad the shorter side so both panes stay visually aligned
            diff_count = (i2 - i1) - (j2 - j1)
            if diff_count > 0:
                # More removed than added — pad right
                for _ in range(diff_count):
                    right_parts.append("<p style='margin:2px 0;'>&nbsp;</p>")
            elif diff_count < 0:
                # More added than removed — pad left
                for _ in range(-diff_count):
                    left_parts.append("<p style='margin:2px 0;'>&nbsp;</p>")

        elif tag == "delete":
            for line in original_lines[i1:i2]:
                escaped = html.escape(line) if line else "&nbsp;"
                left_parts.append(
                    f"<p style='margin:2px 0; background:{remove_bg}; "
                    f"border-left:3px solid {remove_color}; "
                    f"padding-left:6px;'>{escaped}</p>"
                )
                # Blank placeholder on the right to keep alignment
                right_parts.append("<p style='margin:2px 0;'>&nbsp;</p>")

        elif tag == "insert":
            for line in formatted_lines[j1:j2]:
                escaped = html.escape(line) if line else "&nbsp;"
                right_parts.append(
                    f"<p style='margin:2px 0; background:{add_bg}; "
                    f"border-left:3px solid {add_color}; "
                    f"padding-left:6px;'>{escaped}</p>"
                )
                # Blank placeholder on the left to keep alignment
                left_parts.append("<p style='margin:2px 0;'>&nbsp;</p>")

    original_html = "\n".join(left_parts)
    formatted_html = "\n".join(right_parts)
    return original_html, formatted_html


# ---------------------------------------------------------------------------
# DiffView widget
# ---------------------------------------------------------------------------

class DiffView(QWidget):
    """
    Side-by-side before/after comparison view for documents.

    Displays the original and formatted versions of a document with
    highlighted diffs in two QTextBrowser panes separated by a QSplitter.

    Signals
    -------
    back_requested()
        Emitted when the Back button is clicked to navigate back.
    accept_requested(str)
        Emitted when the Accept button is clicked. Payload is the
        formatted file path.
    reject_requested(str)
        Emitted when the Reject button is clicked. Payload is the
        original file path.
    """

    back_requested = pyqtSignal()
    accept_requested = pyqtSignal(str)
    reject_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DiffView")

        self._original_path: str = ""
        self._formatted_path: str = ""
        self._current_colors = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the widget tree."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Toolbar row ---------------------------------------------------
        toolbar = QFrame()
        toolbar.setObjectName("DiffViewToolbar")
        toolbar.setFixedHeight(40)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(8)

        self._back_btn = QPushButton("\u25c0 Back")
        self._back_btn.setObjectName("DiffViewBackBtn")
        self._back_btn.setToolTip("Return to document list")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested.emit)
        tb_layout.addWidget(self._back_btn)

        tb_layout.addStretch()

        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setObjectName("DiffViewRejectBtn")
        self._reject_btn.setToolTip("Reject changes and keep the original")
        self._reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reject_btn.clicked.connect(self._on_reject_clicked)
        tb_layout.addWidget(self._reject_btn)

        self._accept_btn = QPushButton("Accept")
        self._accept_btn.setObjectName("DiffViewAcceptBtn")
        self._accept_btn.setToolTip("Accept the formatted version")
        self._accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accept_btn.clicked.connect(self._on_accept_clicked)
        tb_layout.addWidget(self._accept_btn)

        root.addWidget(toolbar)

        # --- Labels row ----------------------------------------------------
        labels_row = QHBoxLayout()
        labels_row.setContentsMargins(8, 4, 8, 4)
        labels_row.setSpacing(0)

        self._original_label = QLabel("Original")
        self._original_label.setObjectName("DiffViewOriginalLabel")
        self._original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        labels_row.addWidget(self._original_label)

        self._formatted_label = QLabel("Formatted")
        self._formatted_label.setObjectName("DiffViewFormattedLabel")
        self._formatted_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._formatted_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        labels_row.addWidget(self._formatted_label)

        root.addLayout(labels_row)

        # --- QSplitter with two QTextBrowser panes -------------------------
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setObjectName("DiffViewSplitter")
        self._splitter.setChildrenCollapsible(False)

        self._left_browser = QTextBrowser()
        self._left_browser.setObjectName("DiffViewLeftBrowser")
        self._left_browser.setOpenExternalLinks(False)
        self._left_browser.setReadOnly(True)

        self._right_browser = QTextBrowser()
        self._right_browser.setObjectName("DiffViewRightBrowser")
        self._right_browser.setOpenExternalLinks(False)
        self._right_browser.setReadOnly(True)

        self._splitter.addWidget(self._left_browser)
        self._splitter.addWidget(self._right_browser)

        # Equal sizes for both panes
        self._splitter.setSizes([1, 1])

        root.addWidget(self._splitter, 1)  # stretch factor 1

        # Synchronise scrolling between the two panes (with guard flag
        # to prevent infinite signal recursion)
        self._syncing_scroll = False
        left_sb = self._left_browser.verticalScrollBar()
        right_sb = self._right_browser.verticalScrollBar()
        left_sb.valueChanged.connect(self._sync_scroll_right)
        right_sb.valueChanged.connect(self._sync_scroll_left)

    # ------------------------------------------------------------------
    # Scroll synchronisation helpers
    # ------------------------------------------------------------------

    def _sync_scroll_right(self, value: int) -> None:
        """Propagate left pane scroll to right, guarded against recursion."""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self._right_browser.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _sync_scroll_left(self, value: int) -> None:
        """Propagate right pane scroll to left, guarded against recursion."""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self._left_browser.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_diff(self, original_path: str, formatted_path: str) -> None:
        """
        Load two DOCX files and display a side-by-side diff.

        Parameters
        ----------
        original_path : str
            Path to the original document.
        formatted_path : str
            Path to the formatted (post-processing) document.
        """
        self._original_path = original_path
        self._formatted_path = formatted_path

        original_lines = _extract_text_lines(original_path)
        formatted_lines = _extract_text_lines(formatted_path)

        if not original_lines and not formatted_lines:
            self._left_browser.setHtml(
                "<p style='color:#888; font-style:italic;'>"
                "Could not extract text from the document.</p>"
            )
            self._right_browser.setHtml(
                "<p style='color:#888; font-style:italic;'>"
                "Could not extract text from the document.</p>"
            )
            logger.warning(
                "Both documents returned empty text: %s, %s",
                original_path, formatted_path,
            )
            return

        original_html, formatted_html = _build_diff_html(
            original_lines, formatted_lines
        )
        self._left_browser.setHtml(original_html)
        self._right_browser.setHtml(formatted_html)

        logger.debug(
            "Diff loaded: %d original lines, %d formatted lines",
            len(original_lines), len(formatted_lines),
        )

    # ------------------------------------------------------------------
    # Theme support
    # ------------------------------------------------------------------

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the diff view and all child widgets.

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
        interactive_hover = getattr(colors, "interactive_hover", "#5a5a5a")

        # Container
        self.setStyleSheet(f"""
            QWidget#DiffView {{
                background-color: {bg_primary};
            }}
        """)

        # Toolbar
        toolbar = self.findChild(QFrame, "DiffViewToolbar")
        if toolbar:
            toolbar.setStyleSheet(f"""
                QFrame#DiffViewToolbar {{
                    background-color: {bg_secondary};
                    border: none;
                    border-bottom: 1px solid {border_secondary};
                }}
            """)

        # Back button — normal style
        if THEME_AVAILABLE:
            ButtonStyleManager.apply_unified_button_style(
                self._back_btn, colors, "push", "small", "normal"
            )
        else:
            self._back_btn.setStyleSheet(f"""
                QPushButton#DiffViewBackBtn {{
                    background-color: {bg_tertiary};
                    color: {text_primary};
                    border: 1px solid {border_secondary};
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-size: 12px;
                }}
                QPushButton#DiffViewBackBtn:hover {{
                    background-color: {interactive_hover};
                }}
            """)

        # Accept button — success state
        if THEME_AVAILABLE:
            ButtonStyleManager.apply_unified_button_style(
                self._accept_btn, colors, "push", "small", "success"
            )
        else:
            status_success = getattr(colors, "status_success", "#4CAF50")
            self._accept_btn.setStyleSheet(f"""
                QPushButton#DiffViewAcceptBtn {{
                    background-color: {status_success};
                    color: {text_primary};
                    border: 1px solid {status_success};
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton#DiffViewAcceptBtn:hover {{
                    background-color: {interactive_hover};
                }}
                QPushButton#DiffViewAcceptBtn:disabled {{
                    color: {text_disabled};
                    background-color: {bg_tertiary};
                    border-color: {border_secondary};
                }}
            """)

        # Reject button — danger state
        if THEME_AVAILABLE:
            ButtonStyleManager.apply_unified_button_style(
                self._reject_btn, colors, "push", "small", "danger"
            )
        else:
            status_error = getattr(colors, "status_error", "#F44336")
            self._reject_btn.setStyleSheet(f"""
                QPushButton#DiffViewRejectBtn {{
                    background-color: {status_error};
                    color: {text_primary};
                    border: 1px solid {status_error};
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton#DiffViewRejectBtn:hover {{
                    background-color: {interactive_hover};
                }}
                QPushButton#DiffViewRejectBtn:disabled {{
                    color: {text_disabled};
                    background-color: {bg_tertiary};
                    border-color: {border_secondary};
                }}
            """)

        # Labels
        label_style = (
            f"color: {text_secondary}; font-size: 12px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        self._original_label.setStyleSheet(label_style)
        self._formatted_label.setStyleSheet(label_style)

        # Splitter styling
        self._splitter.setStyleSheet(f"""
            QSplitter#DiffViewSplitter {{
                background-color: {bg_primary};
            }}
            QSplitter#DiffViewSplitter::handle {{
                background-color: {border_primary};
                width: 2px;
            }}
        """)

        # Text browser panes
        browser_style = f"""
            QTextBrowser {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                selection-background-color: {border_primary};
            }}
        """
        self._left_browser.setStyleSheet(browser_style)
        self._right_browser.setStyleSheet(browser_style)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_accept_clicked(self) -> None:
        """Emit ``accept_requested`` with the formatted file path."""
        if self._formatted_path:
            self.accept_requested.emit(self._formatted_path)

    def _on_reject_clicked(self) -> None:
        """Emit ``reject_requested`` with the original file path."""
        if self._original_path:
            self.reject_requested.emit(self._original_path)
