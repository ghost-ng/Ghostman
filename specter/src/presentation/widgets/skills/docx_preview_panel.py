"""
DOCX Preview Panel - Live document preview with chat-based editing.

A floating panel that shows a styled HTML preview of a DOCX file. The user
opens a document, sees a faithful preview, then chats with the AI to request
formatting changes. After each AI modification the preview auto-refreshes.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QPushButton, QLabel, QFileDialog, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

# Theme imports
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.theme_manager import get_theme_manager, get_theme_color
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.skills.docx_preview")


def _docx_to_html(file_path: str) -> str:
    """Convert a DOCX file to styled HTML for preview.

    Uses mammoth for high-fidelity conversion if available, falls back to
    python-docx paragraph-level extraction.
    """
    try:
        import mammoth

        with open(file_path, "rb") as f:
            result = mammoth.convert_to_html(f)

        html_body = result.value
        if result.messages:
            for msg in result.messages[:5]:
                logger.debug(f"mammoth: {msg}")

        return html_body

    except ImportError:
        logger.info("mammoth not installed, falling back to python-docx extraction")

    # Fallback: python-docx paragraph extraction
    try:
        from docx import Document
        from docx.shared import Pt

        doc = Document(file_path)
        parts = []

        for para in doc.paragraphs:
            text = para.text
            if not text.strip():
                parts.append("<p>&nbsp;</p>")
                continue

            style_name = para.style.name if para.style else ""

            # Determine tag
            if style_name.startswith("Heading 1"):
                parts.append(f"<h1>{text}</h1>")
            elif style_name.startswith("Heading 2"):
                parts.append(f"<h2>{text}</h2>")
            elif style_name.startswith("Heading 3"):
                parts.append(f"<h3>{text}</h3>")
            elif "List" in style_name:
                parts.append(f"<li>{text}</li>")
            else:
                # Check for bold/italic in runs
                styled_parts = []
                for run in para.runs:
                    t = run.text
                    if not t:
                        continue
                    if run.bold:
                        t = f"<b>{t}</b>"
                    if run.italic:
                        t = f"<i>{t}</i>"
                    if run.underline:
                        t = f"<u>{t}</u>"
                    styled_parts.append(t)
                parts.append(f"<p>{''.join(styled_parts)}</p>")

        return "\n".join(parts)

    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return f"<p style='color:red;'>Failed to load document: {e}</p>"


class DocxPreviewPanel(QWidget):
    """Floating panel showing a live HTML preview of a DOCX document.

    Signals:
        file_opened(str): Emitted when a document is opened (path).
        preview_refreshed(): Emitted after the preview is updated.
        close_requested(): Emitted when the user clicks Close.
    """

    file_opened = pyqtSignal(str)
    preview_refreshed = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None, colors: Optional["ColorSystem"] = None):
        super().__init__(parent)
        self._file_path: Optional[str] = None
        self._colors = colors
        self._last_modified: float = 0.0

        self.setWindowTitle("Document Preview")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(500, 400)
        self.resize(620, 700)

        self._init_ui()
        self._apply_theme()

        # File watcher timer — polls for changes every 1.5s
        self._watch_timer = QTimer(self)
        self._watch_timer.timeout.connect(self._check_file_changed)

    # ── UI construction ───────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(6)

        self._open_btn = QPushButton("Open")
        self._open_btn.setToolTip("Open a .docx file to preview")
        self._open_btn.clicked.connect(self._on_open_clicked)
        toolbar_layout.addWidget(self._open_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setToolTip("Re-render the document preview")
        self._refresh_btn.clicked.connect(self.refresh_preview)
        self._refresh_btn.setEnabled(False)
        toolbar_layout.addWidget(self._refresh_btn)

        toolbar_layout.addStretch()

        self._file_label = QLabel("No document loaded")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        toolbar_layout.addWidget(self._file_label)

        self._close_btn = QPushButton("X")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setToolTip("Close preview")
        self._close_btn.clicked.connect(self._on_close)
        toolbar_layout.addWidget(self._close_btn)

        layout.addWidget(toolbar)

        # Browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setReadOnly(True)
        layout.addWidget(self._browser)

    # ── Public API ────────────────────────────────────────────────────

    def open_document(self, file_path: str) -> bool:
        """Open and preview a DOCX file.

        Args:
            file_path: Absolute path to a .docx file.

        Returns:
            True if the document was loaded successfully.
        """
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"File not found: {file_path}")
            return False
        if p.suffix.lower() != ".docx":
            logger.warning(f"Not a .docx file: {file_path}")
            return False

        self._file_path = str(p)
        self._file_label.setText(p.name)
        self._refresh_btn.setEnabled(True)

        self.refresh_preview()
        self.file_opened.emit(self._file_path)

        # Start watching for changes
        try:
            self._last_modified = os.path.getmtime(self._file_path)
        except OSError:
            self._last_modified = 0.0
        self._watch_timer.start(1500)

        # Show the panel
        self.show()
        self.raise_()
        return True

    @property
    def current_file(self) -> Optional[str]:
        """Return the currently loaded file path, or None."""
        return self._file_path

    def refresh_preview(self):
        """Re-render the current document to HTML and display it."""
        if not self._file_path:
            return

        html_body = _docx_to_html(self._file_path)
        full_html = self._wrap_html(html_body)
        self._browser.setHtml(full_html)

        # Update last-modified timestamp
        try:
            self._last_modified = os.path.getmtime(self._file_path)
        except OSError:
            pass

        self.preview_refreshed.emit()
        logger.debug(f"Preview refreshed: {self._file_path}")

    def set_colors(self, colors: "ColorSystem"):
        """Update the color scheme and re-apply theme."""
        self._colors = colors
        self._apply_theme()
        if self._file_path:
            self.refresh_preview()

    # ── Private helpers ───────────────────────────────────────────────

    def _wrap_html(self, body_html: str) -> str:
        """Wrap the converted body HTML in a full styled document."""
        bg = "#FFFFFF"
        fg = "#1A1A1A"
        h_color = "#2C3E50"
        link_color = "#2980B9"
        border_color = "#DEE2E6"

        if self._colors:
            bg = self._colors.background_primary
            fg = self._colors.text_primary
            h_color = self._colors.primary
            link_color = self._colors.primary
            border_color = self._colors.border

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: 'Calibri', 'Segoe UI', sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: {fg};
    background: {bg};
    padding: 24px 32px;
    margin: 0;
    max-width: 100%;
}}
h1 {{ font-size: 18pt; color: {h_color}; margin: 18px 0 8px 0; font-weight: 700; }}
h2 {{ font-size: 15pt; color: {h_color}; margin: 14px 0 6px 0; font-weight: 600; }}
h3 {{ font-size: 13pt; color: {h_color}; margin: 12px 0 4px 0; font-weight: 600; }}
p  {{ margin: 4px 0; }}
ul, ol {{ margin: 4px 0 4px 20px; }}
li {{ margin: 2px 0; }}
a  {{ color: {link_color}; }}
table {{
    border-collapse: collapse;
    margin: 12px 0;
    width: 100%;
}}
th, td {{
    border: 1px solid {border_color};
    padding: 6px 10px;
    text-align: left;
}}
th {{ background: {h_color}22; font-weight: 600; }}
blockquote {{
    border-left: 3px solid {border_color};
    margin: 8px 0;
    padding: 4px 12px;
    color: {fg}99;
}}
img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

    def _apply_theme(self):
        """Apply the current color scheme to the panel widgets."""
        if not self._colors:
            return

        c = self._colors
        self.setStyleSheet(f"""
            QWidget {{
                background: {c.background_primary};
                color: {c.text_primary};
            }}
            QFrame {{
                background: {c.background_secondary};
                border-bottom: 1px solid {c.border};
            }}
            QPushButton {{
                background: {c.background_secondary};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {c.primary}33;
                border-color: {c.primary};
            }}
            QPushButton:disabled {{
                color: {c.text_secondary};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {c.text_secondary};
                font-size: 11px;
            }}
            QTextBrowser {{
                background: {c.background_primary};
                border: none;
            }}
        """)

    def _check_file_changed(self):
        """Poll the file's mtime and refresh if it was modified."""
        if not self._file_path:
            return
        try:
            mtime = os.path.getmtime(self._file_path)
            if mtime > self._last_modified:
                self._last_modified = mtime
                self.refresh_preview()
                logger.debug("Auto-refresh: file modified on disk")
        except OSError:
            pass

    def _on_open_clicked(self):
        """Show a file dialog to pick a DOCX file."""
        start_dir = str(Path.home() / "Documents")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Word Document", start_dir,
            "Word Documents (*.docx);;All Files (*)"
        )
        if path:
            self.open_document(path)

    def _on_close(self):
        """Close the preview panel."""
        self._watch_timer.stop()
        self.close_requested.emit()
        self.hide()

    def closeEvent(self, event):
        """Handle window close."""
        self._watch_timer.stop()
        self.close_requested.emit()
        super().closeEvent(event)
