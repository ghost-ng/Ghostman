"""
StudioHeaderBar — title bar for the Document Studio panel.

Shows "Document Studio" title with a collapse/close button.
"""

import logging
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QSizePolicy

logger = logging.getLogger("specter.document_studio.header")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


class StudioHeaderBar(QFrame):
    """Header bar with title and collapse button."""

    collapse_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("studio_header_bar")
        self.setFixedHeight(40)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        self._title = QLabel("\U0001f4da Document Studio")
        self._title.setObjectName("studio_title")
        self._title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._title)

        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("\u25c0")  # left-pointing triangle
        self._collapse_btn.setToolTip("Collapse panel")
        self._collapse_btn.setFixedSize(26, 26)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        layout.addWidget(self._collapse_btn)

    def apply_theme(self, colors):
        """Apply theme to header bar."""
        if not THEME_AVAILABLE or not colors:
            return
        primary = getattr(colors, "primary", "#4CAF50")
        bg_tertiary = getattr(colors, "background_tertiary", "#3a3a3a")
        border_sec = getattr(colors, "border_secondary", "#333333")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        interactive_hover = getattr(colors, "interactive_hover", "#5a5a5a")

        self.setStyleSheet(f"""
            QFrame#studio_header_bar {{
                background: {bg_tertiary};
                border: none;
                border-bottom: 2px solid {primary};
            }}
        """)
        self._title.setStyleSheet(
            f"color: {text_primary}; font-weight: bold; font-size: 13px; "
            f"background: transparent; border: none; letter-spacing: 0.5px;"
        )
        self._collapse_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: {text_secondary};
                font-size: 12px;
            }}
            QToolButton:hover {{
                background-color: {interactive_hover};
                border-color: {border_sec};
                color: {text_primary};
            }}
        """)
