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
        self.setFixedHeight(36)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)

        self._title = QLabel("\U0001f4da Document Studio")
        self._title.setObjectName("studio_title")
        self._title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._title)

        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("\u25c0")  # left-pointing triangle
        self._collapse_btn.setToolTip("Collapse panel")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        layout.addWidget(self._collapse_btn)

    def apply_theme(self, colors):
        """Apply theme to header bar."""
        if not THEME_AVAILABLE or not colors:
            return
        self.setStyleSheet(f"""
            QFrame#studio_header_bar {{
                background: {colors.background_tertiary};
                border: none;
                border-bottom: 1px solid {colors.border_secondary};
            }}
        """)
        self._title.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; font-size: 13px; background: transparent;"
        )
        if colors:
            ButtonStyleManager.apply_unified_button_style(
                self._collapse_btn, colors, "tool", "icon", "normal"
            )
