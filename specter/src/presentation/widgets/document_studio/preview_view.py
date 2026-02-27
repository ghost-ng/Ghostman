"""
DocumentPreviewView — in-app document preview for the Document Studio.

Renders DOCX files as styled HTML inside a QTextBrowser.  Provides toolbar
controls for navigating back to the document list and opening the file in
the system default application.

Layout:
┌─────────────────────────────────────────┐
│  [← Back]  quarterly-report.docx  [↗]  │  toolbar
├─────────────────────────────────────────┤
│                                         │
│  QTextBrowser (rendered HTML)           │
│                                         │
└─────────────────────────────────────────┘
"""

import html
import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
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

logger = logging.getLogger("specter.document_studio.preview_view")

# ---------------------------------------------------------------------------
# Paragraph style name → HTML tag mapping
# ---------------------------------------------------------------------------
_STYLE_TAG_MAP = {
    "heading 1": "h1",
    "heading 2": "h2",
    "heading 3": "h3",
    "heading 4": "h4",
    "heading 5": "h5",
    "heading 6": "h6",
    "list": "li",
    "list bullet": "li",
    "list number": "li",
    "list paragraph": "li",
}


def _run_to_html(run) -> str:
    """Convert a single python-docx Run to an HTML span with inline styles."""
    text = html.escape(run.text)
    if not text:
        return ""

    styles: list[str] = []

    if run.bold:
        styles.append("font-weight:bold")
    if run.italic:
        styles.append("font-style:italic")
    if run.underline:
        styles.append("text-decoration:underline")

    # Font size — python-docx stores as half-points (Pt * 2) in an Emu-like
    # wrapper; the .pt property gives the float value in points.
    font = run.font
    if font.size is not None:
        try:
            pt = font.size.pt
            styles.append(f"font-size:{pt:.1f}pt")
        except Exception:
            pass

    if font.name:
        styles.append(f"font-family:'{html.escape(font.name)}'")

    # Font colour — RGBColor has a string representation like "FF0000".
    if font.color and font.color.rgb is not None:
        try:
            styles.append(f"color:#{font.color.rgb}")
        except Exception:
            pass

    if styles:
        return f'<span style="{";".join(styles)}">{text}</span>'
    return text


def docx_to_html(file_path: str) -> str:
    """
    Convert a DOCX file to styled HTML suitable for QTextBrowser rendering.

    Parameters
    ----------
    file_path : str
        Absolute path to the ``.docx`` file.

    Returns
    -------
    str
        An HTML string wrapped in a ``<div>`` with a default font family.
        On error, returns an HTML snippet describing the problem.
    """
    # --- Guard: file existence -------------------------------------------
    if not os.path.isfile(file_path):
        return (
            '<div style="color:#F44336;padding:16px;">'
            f"<b>File not found:</b> {html.escape(file_path)}"
            "</div>"
        )

    # --- Lazy import of python-docx --------------------------------------
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError:
        return (
            '<div style="color:#F44336;padding:16px;">'
            "<b>python-docx is not installed.</b><br>"
            "Run <code>pip install python-docx</code> to enable DOCX preview."
            "</div>"
        )

    # --- Parse the document ----------------------------------------------
    try:
        doc = Document(file_path)
    except Exception as exc:
        logger.warning("Failed to open DOCX '%s': %s", file_path, exc)
        return (
            '<div style="color:#F44336;padding:16px;">'
            f"<b>Cannot open document:</b> {html.escape(str(exc))}"
            "</div>"
        )

    # --- Build HTML body -------------------------------------------------
    parts: list[str] = []
    in_list = False

    for para in doc.paragraphs:
        style_name = (para.style.name or "").lower().strip()
        tag = _STYLE_TAG_MAP.get(style_name, "p")

        # Build inline content from runs
        inner = "".join(_run_to_html(run) for run in para.runs)

        # If the paragraph has no runs (e.g. images-only), fall back to
        # the plain text property.
        if not inner and para.text:
            inner = html.escape(para.text)

        # Manage list wrapping — open/close <ul> around consecutive <li>.
        if tag == "li":
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{inner}</li>")
        else:
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<{tag}>{inner}</{tag}>")

    # Close any open list
    if in_list:
        parts.append("</ul>")

    body = "\n".join(parts)

    return (
        '<div style="font-family:Calibri,Segoe UI,Arial,sans-serif;'
        'line-height:1.5;padding:12px;">'
        f"{body}"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class DocumentPreviewView(QWidget):
    """
    In-app document preview widget.

    Renders a DOCX file as HTML in a ``QTextBrowser`` and provides toolbar
    buttons for navigating back and opening the file externally.

    Signals
    -------
    back_requested()
        Emitted when the user clicks the Back button.
    open_external_requested(str)
        Emitted when the user clicks "Open External".  Payload is the
        absolute file path.
    """

    back_requested = pyqtSignal()
    open_external_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DocumentPreviewView")
        self._current_file_path: str = ""
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the widget tree: toolbar + browser."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Toolbar row --------------------------------------------------
        toolbar = QWidget(self)
        toolbar.setObjectName("PreviewToolbar")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(8)

        self._back_btn = QPushButton("\u2190 Back")  # ← Back
        self._back_btn.setObjectName("PreviewBackBtn")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setToolTip("Return to document list")
        self._back_btn.clicked.connect(self.back_requested.emit)
        tb_layout.addWidget(self._back_btn)

        self._filename_label = QLabel()
        self._filename_label.setObjectName("PreviewFilenameLabel")
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        tb_layout.addWidget(self._filename_label)

        self._open_external_btn = QPushButton("\u2197")  # ↗
        self._open_external_btn.setObjectName("PreviewOpenExternalBtn")
        self._open_external_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_external_btn.setToolTip("Open in system default application")
        self._open_external_btn.clicked.connect(self._on_open_external)
        tb_layout.addWidget(self._open_external_btn)

        root.addWidget(toolbar)

        # --- QTextBrowser for rendered content ----------------------------
        self._browser = QTextBrowser(self)
        self._browser.setObjectName("PreviewBrowser")
        self._browser.setOpenExternalLinks(False)
        self._browser.setReadOnly(True)
        root.addWidget(self._browser, 1)  # stretch factor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_document(self, file_path: str) -> None:
        """
        Load and render a DOCX file in the preview browser.

        Parameters
        ----------
        file_path : str
            Absolute path to the ``.docx`` file.
        """
        self._current_file_path = file_path

        # Update the filename label
        filename = os.path.basename(file_path)
        self._filename_label.setText(filename)
        self._filename_label.setToolTip(file_path)

        # Convert and display
        logger.debug("Loading document preview: %s", file_path)
        html_content = docx_to_html(file_path)
        self._browser.setHtml(html_content)

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the preview view.

        Parameters
        ----------
        colors : ColorSystem (or compatible object)
            Provides semantic colour attributes used for styling.
        """
        bg_primary = getattr(colors, "background_primary", "#2b2b2b")
        bg_secondary = getattr(colors, "background_secondary", "#1e1e1e")
        bg_tertiary = getattr(colors, "background_tertiary", "#3a3a3a")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        border_secondary = getattr(colors, "border_secondary", "#333333")
        primary = getattr(colors, "primary", "#4CAF50")

        # Toolbar
        toolbar = self.findChild(QWidget, "PreviewToolbar")
        if toolbar:
            toolbar.setStyleSheet(f"""
                QWidget#PreviewToolbar {{
                    background-color: {bg_tertiary};
                    border-bottom: 1px solid {border_secondary};
                }}
            """)

        # Filename label
        self._filename_label.setStyleSheet(f"""
            QLabel#PreviewFilenameLabel {{
                color: {text_primary};
                font-weight: bold;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
        """)

        # Browser
        self._browser.setStyleSheet(f"""
            QTextBrowser#PreviewBrowser {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: none;
                padding: 8px;
                selection-background-color: {primary};
                selection-color: {bg_primary};
            }}
        """)

        # Buttons — use ButtonStyleManager if available
        if THEME_AVAILABLE and colors:
            ButtonStyleManager.apply_unified_button_style(
                self._back_btn, colors, "push", "small", "normal"
            )
            ButtonStyleManager.apply_unified_button_style(
                self._open_external_btn, colors, "tool", "icon", "normal"
            )
        else:
            # Minimal fallback styling
            for btn in (self._back_btn, self._open_external_btn):
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_tertiary};
                        color: {text_secondary};
                        border: 1px solid {border_secondary};
                        border-radius: 4px;
                        padding: 4px 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {primary};
                        color: {bg_primary};
                    }}
                """)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_open_external(self) -> None:
        """Emit ``open_external_requested`` with the current file path."""
        if self._current_file_path:
            self.open_external_requested.emit(self._current_file_path)
