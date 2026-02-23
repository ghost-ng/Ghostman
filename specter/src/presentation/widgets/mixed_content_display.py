"""
Mixed content display widget for REPL.

Uses a single QTextBrowser for all content, enabling seamless cross-message
text selection (copy-paste).  URLs are rendered as clickable hyperlinks with
a confirmation dialog before opening in the browser.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox,
    QApplication, QTextBrowser,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor
import re
import html as html_module
import logging
from typing import Optional, List, Tuple, Dict, Any

logger = logging.getLogger('specter.mixed_content_display')

# URL regex — matches http/https URLs not already inside an href attribute
_URL_RE = re.compile(
    r'(?<!["\'=>/])'           # not preceded by quote, =, >, /
    r'(https?://[^\s<>"\')\]]+)',
    re.IGNORECASE,
)


class MixedContentDisplay(QWidget):
    """
    Scrollable widget that displays HTML text in a single QTextBrowser.

    All messages are appended as styled HTML blocks, enabling native
    cross-message text selection.  Code blocks are rendered as styled
    ``<pre>`` elements.
    """

    link_clicked = pyqtSignal(str)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, parent=None):
        super().__init__(parent)

        self.theme_colors: Optional[Dict[str, str]] = None
        self.content_history: List[tuple] = []  # (content, style, type)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Single QTextBrowser for all content ---
        self.text_browser = QTextBrowser()
        self.text_browser.setAcceptDrops(False)  # Let parent REPL handle file drops
        self.text_browser.setOpenLinks(False)
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setReadOnly(True)
        self.text_browser.anchorClicked.connect(self._handle_anchor_clicked)
        self.text_browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.text_browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        layout.addWidget(self.text_browser)

        # Track tool-status insertion points for removal
        self._tool_status_positions: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Backward-compatible properties used by repl_widget.py
    # ------------------------------------------------------------------

    @property
    def content_widgets(self) -> list:
        """Compat shim — returns a non-empty list when there is content."""
        if self.text_browser.document().characterCount() > 1:
            return [True]  # non-empty sentinel
        return []

    # ------------------------------------------------------------------
    # Public API — content
    # ------------------------------------------------------------------

    def add_html_content(self, html_text: str, message_style: str = "normal"):
        """Append HTML content to the display."""
        self.content_history.append((html_text, message_style, "html"))
        self._render_html(html_text, message_style)

    def add_code_snippet(self, code: str, language: str = ""):
        """Append a code block as a styled ``<pre>`` element."""
        if not code.strip():
            return
        self.content_history.append(((code, language), None, "code"))
        self._render_code(code, language)

    def add_plain_text(self, text: str, message_style: str = "normal"):
        """Append plain text (HTML-escaped, newlines → ``<br>``)."""
        escaped = html_module.escape(text).replace("\n", "<br>")
        self.add_html_content(escaped, message_style)

    def add_separator(self):
        """Append a thin horizontal rule."""
        border = "#666"
        if self.theme_colors:
            border = self.theme_colors.get(
                "border", self.theme_colors.get("text_secondary", "#666")
            )
        self._append_raw_html(
            f'<hr style="border:none; border-top:1px solid {border}; margin:6px 0;">'
        )

    def clear(self):
        """Clear all content and history."""
        self.text_browser.clear()
        self.content_history.clear()
        self._tool_status_positions.clear()
        logger.debug("REPL display cleared")

    # ------------------------------------------------------------------
    # Tool-status temporary indicators
    # ------------------------------------------------------------------

    def add_tool_status(self, skill_id: str, text: str):
        """Insert a temporary tool-running status line."""
        # Store the visible text so we can search for it during removal
        search_text = text.strip()
        self._tool_status_positions[skill_id] = search_text
        self._append_raw_html(
            f'<div style="color:#aaa; font-style:italic; padding:4px 8px;">'
            f'{html_module.escape(text)}</div>'
        )

    def remove_tool_status(self, skill_id: str):
        """Remove a previously-inserted tool status line (best-effort)."""
        search_text = self._tool_status_positions.pop(skill_id, None)
        if not search_text:
            return
        doc = self.text_browser.document()
        # Search for the actual visible text (not HTML attributes)
        cursor = doc.find(search_text)
        if not cursor.isNull():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.removeSelectedText()
            cursor.deleteChar()  # remove trailing newline

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def scroll_to_bottom(self):
        """Auto-scroll the text browser to the bottom."""
        vsb = self.text_browser.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def verticalScrollBar(self):
        """Backward-compat — delegate to the text browser."""
        return self.text_browser.verticalScrollBar()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def set_theme_colors(self, colors: Dict[str, str]):
        """Apply new theme colors and re-render all content."""
        self.theme_colors = colors
        self._apply_browser_stylesheet()
        self._rerender_all()

    def _apply_browser_stylesheet(self):
        bg = self._tc("background_secondary", self._tc("bg_primary", "#0d0d1a"))
        text = self._tc("text_primary", "#ffffff")
        accent = self._tc("accent", "#00d4ff")
        border = self._tc("border", "#333")
        bg_hex = self._rgba_to_hex(bg)
        border_hex = self._rgba_to_hex(border)
        text_hex = self._rgba_to_hex(text)
        accent_hex = self._rgba_to_hex(accent)

        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_hex};
                color: {text_hex};
                border: 1px solid {border_hex};
                selection-background-color: {accent_hex};
                selection-color: {bg_hex};
                padding: 8px;
            }}
        """)

    def _rerender_all(self):
        """Re-render all content with current theme colors."""
        self.text_browser.clear()
        for content, style, ctype in self.content_history:
            if ctype == "html":
                self._render_html(content, style)
            elif ctype == "code":
                self._render_code(content[0], content[1])

    # ------------------------------------------------------------------
    # Content size management
    # ------------------------------------------------------------------

    def manage_content_size(self, max_widgets: int = 500):
        """Trim oldest entries if history exceeds *max_widgets*."""
        if len(self.content_history) <= max_widgets:
            return
        self.content_history = self.content_history[-(max_widgets - 100):]
        self._rerender_all()

    def get_content_height(self) -> int:
        return int(self.text_browser.document().size().height())

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _render_html(self, html_text: str, message_style: str = "normal"):
        """Render an HTML block into the text browser."""
        color = self._style_color(message_style)
        color_hex = self._rgba_to_hex(color)

        # Linkify bare URLs
        html_text = self._linkify(html_text)

        # Extract code blocks and insert styled <pre>
        processed, code_blocks = self._extract_code_blocks(html_text)

        for code, _lang in code_blocks:
            pre_html = self._code_to_pre(code)
            processed = processed.replace("[CODE_BLOCK_PLACEHOLDER]", pre_html, 1)

        wrapped = (
            f'<div style="color:{color_hex}; margin:2px 0; padding:1px 0;">'
            f'{processed}</div>'
        )
        self._append_raw_html(wrapped)

    def _render_code(self, code: str, language: str = ""):
        """Render a standalone code block."""
        self._append_raw_html(self._code_to_pre(code))

    def _code_to_pre(self, code: str) -> str:
        """Build a themed ``<pre>`` block for *code*."""
        bg = self._rgba_to_hex(self._tc("background_tertiary", "#1e1e2e"))
        border = self._rgba_to_hex(self._tc("border", "#444"))
        text = self._rgba_to_hex(self._tc("text_primary", "#ddd"))
        escaped = html_module.escape(code)
        return (
            f'<pre style="background-color:{bg}; border:1px solid {border}; '
            f'padding:10px; margin:6px 0; border-radius:5px; '
            f'font-family:Consolas,Monaco,\'Courier New\',monospace; font-size:13px; '
            f'color:{text}; white-space:pre-wrap; word-wrap:break-word;">'
            f'{escaped}</pre>'
        )

    def _append_raw_html(self, html: str):
        """Append raw HTML at the end of the document and auto-scroll."""
        cursor = self.text_browser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_browser.setTextCursor(cursor)
        self.text_browser.insertHtml(html)
        # Small delay for layout to settle before scrolling
        QTimer.singleShot(10, self.scroll_to_bottom)

    # ------------------------------------------------------------------
    # URL linkification
    # ------------------------------------------------------------------

    def _linkify(self, html_text: str) -> str:
        """Convert bare URLs to clickable ``<a>`` tags."""
        accent = self._rgba_to_hex(self._tc("accent", "#00d4ff"))
        # Split around existing <a> tags so we don't double-linkify
        parts = re.split(r'(<a\b[^>]*>.*?</a>)', html_text, flags=re.DOTALL | re.IGNORECASE)
        out: list[str] = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                out.append(part)  # already inside <a>
            else:
                out.append(_URL_RE.sub(
                    rf'<a href="\1" style="color:{accent}; text-decoration:underline;">\1</a>',
                    part,
                ))
        return "".join(out)

    # ------------------------------------------------------------------
    # Anchor / link handling
    # ------------------------------------------------------------------

    def _handle_anchor_clicked(self, url: QUrl):
        """Show themed confirmation dialog, then open in browser."""
        url_str = url.toString()
        if not url_str:
            return
        self.link_clicked.emit(url_str)

        msg = QMessageBox(self)
        msg.setWindowTitle("Open Link")
        msg.setText(f"Do you want to visit:\n\n{url_str}")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        # Apply theme styling
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            tm = get_theme_manager()
            if tm and tm.current_theme:
                c = tm.current_theme
                msg.setStyleSheet(f"""
                    QMessageBox {{
                        background-color: {c.background_primary};
                        color: {c.text_primary};
                    }}
                    QMessageBox QLabel {{
                        color: {c.text_primary};
                        font-size: 11pt;
                    }}
                    QPushButton {{
                        background-color: {c.interactive_normal};
                        color: {c.text_primary};
                        border: 1px solid {c.border_primary};
                        border-radius: 4px;
                        padding: 6px 20px;
                        min-width: 70px;
                        font-size: 10pt;
                    }}
                    QPushButton:hover {{
                        background-color: {c.interactive_hover};
                        border-color: {c.primary};
                    }}
                    QPushButton:pressed {{
                        background-color: {c.interactive_active};
                    }}
                    QPushButton:default {{
                        border: 2px solid {c.primary};
                    }}
                """)
        except Exception:
            pass

        if msg.exec() == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(url)

    # ------------------------------------------------------------------
    # Code-block extraction (preserved from original)
    # ------------------------------------------------------------------

    def _extract_code_blocks(self, html_text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Extract code blocks from HTML, returning (processed_html, [(code, lang)])."""
        code_blocks: List[Tuple[str, str]] = []
        pattern = (
            r'<div[^>]*style="[^"]*background-color:[^"]*"[^>]*>'
            r'.*?<pre[^>]*>(.*?)</pre>.*?</div>\s*</div>'
        )

        def _replace(match):
            try:
                raw = match.group(1)
                clean = re.sub(r'<[^>]+>', '', raw)
                clean = html_module.unescape(clean)
                clean = re.sub(r'style="[^"]*"', '', clean)
                clean = re.sub(r'class="[^"]*"', '', clean)
                clean = re.sub(r'\n\s*\n', '\n', clean).rstrip()
                lang = self._detect_language(match.group(0))
                code_blocks.append((clean, lang))
                return "[CODE_BLOCK_PLACEHOLDER]"
            except Exception as e:
                logger.warning(f"Code block parse error: {e}")
                code_blocks.append(("# parse error", "text"))
                return "[CODE_BLOCK_PLACEHOLDER]"

        try:
            processed = re.sub(pattern, _replace, html_text, flags=re.DOTALL)
            # Cleanup artifacts
            for p in [
                r'</div>\s*</div>\s*<br>\s*',
                r'<div[^>]*>\s*</div>',
                r'<br>\s*</div>',
                r'\s*</div>\s*$',
                r'^\s*<br>\s*',
            ]:
                processed = re.sub(p, '', processed, flags=re.MULTILINE | re.DOTALL)
            return processed.strip(), code_blocks
        except Exception as e:
            logger.error(f"HTML processing failed: {e}")
            return html_text, []

    def _detect_language(self, html_block: str) -> str:
        """Detect programming language from code block HTML."""
        clean = re.sub(r'<[^>]+>', '', html_block)
        clean = html_module.unescape(clean).strip()
        if not clean:
            return "text"
        try:
            from pygments.lexers import guess_lexer
            lexer = guess_lexer(clean)
            return lexer.aliases[0] if lexer.aliases else lexer.name.lower()
        except Exception:
            if clean.strip().startswith('{') and clean.strip().endswith('}'):
                try:
                    import json
                    json.loads(clean)
                    return "json"
                except Exception:
                    pass
            return "text"

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------

    def _tc(self, key: str, fallback: str = "#ffffff") -> str:
        """Get a theme color by key with fallback."""
        if self.theme_colors:
            # Try both naming conventions
            return self.theme_colors.get(
                key, self.theme_colors.get(f"bg_{key}", fallback)
            )
        return fallback

    def _style_color(self, style: str) -> str:
        """Map a message style name to a theme color."""
        if not self.theme_colors:
            return "#ffffff"
        tp = self._tc("text_primary", "#ffffff")
        mapping = {
            "normal": tp,
            "input": self._tc("primary", tp),
            "response": tp,
            "system": self._tc("text_secondary", tp),
            "info": self._tc("info", tp),
            "warning": self._tc("warning", tp),
            "error": self._tc("error", tp),
            "divider": self._tc("text_secondary", tp),
        }
        return mapping.get(style, tp)

    @staticmethod
    def _rgba_to_hex(color: str) -> str:
        """Convert rgba()/rgb() to #RRGGBB."""
        if color.startswith("#"):
            return color
        m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color)
        if m:
            return f"#{int(m.group(1)):02x}{int(m.group(2)):02x}{int(m.group(3)):02x}"
        return color
