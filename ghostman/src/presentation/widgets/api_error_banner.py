"""
API Error Banner Widget for Ghostman.

Displays theme-aware error banner above REPL input when API connectivity fails.
Shows only on first failure, dismissible by user, auto-hides when connection restored.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QWidget, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QCursor

# Import theme system
try:
    from ...ui.themes.color_system import ColorUtils
    from ...ui.themes.theme_manager import get_theme_manager, get_theme_color
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    class ColorUtils:
        @staticmethod
        def lighten(color: str, factor: float = 0.1) -> str:
            return color
        @staticmethod
        def darken(color: str, factor: float = 0.1) -> str:
            return color
    def get_theme_color(color_name, theme_manager_instance=None, fallback=None):
        return fallback or '#e74c3c'

logger = logging.getLogger("ghostman.api_error_banner")


class APIErrorBanner(QFrame):
    """
    Theme-aware error banner for API connectivity issues.

    Features:
    - Appears above REPL input area
    - Theme-aware colors with WCAG contrast
    - Slide-in/out animations
    - Action buttons: Open Settings, Retry Now
    - Dismissible with X button
    - Auto-hides when connection restored
    """

    # Signals
    dismissed = pyqtSignal()  # User manually dismissed the banner
    retry_requested = pyqtSignal()  # User clicked "Retry Now"
    settings_requested = pyqtSignal()  # User clicked "Open Settings"

    def __init__(self, theme_manager=None, parent=None):
        """
        Initialize API error banner.

        Args:
            theme_manager: ThemeManager instance for theme integration
            parent: Parent widget
        """
        super().__init__(parent)

        self.theme_manager = theme_manager
        self._is_dismissed_by_user = False
        self._last_error_message = ""
        self._provider_name = ""

        # Banner is initially hidden
        self.setVisible(False)
        self.setFixedHeight(0)  # Start with height 0 for animation

        # Setup UI
        self._setup_ui()

        # Apply initial styling
        self._apply_theme_styling()

        # Connect to theme changes
        if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
            self.theme_manager.theme_changed.connect(self._apply_theme_styling)

        logger.debug("API error banner initialized")

    def _setup_ui(self):
        """Setup banner UI components."""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)

        # Warning icon
        self.icon_label = QLabel("⚠️")
        icon_font = QFont()
        icon_font.setPointSize(16)
        self.icon_label.setFont(icon_font)
        main_layout.addWidget(self.icon_label)

        # Content area (message + actions)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        # Error message label
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        message_font = QFont()
        message_font.setBold(True)
        message_font.setPointSize(10)
        self.message_label.setFont(message_font)
        content_layout.addWidget(self.message_label)

        # Action hints (bullet points)
        self.hints_label = QLabel()
        self.hints_label.setWordWrap(True)
        hints_font = QFont()
        hints_font.setPointSize(9)
        self.hints_label.setFont(hints_font)
        content_layout.addWidget(self.hints_label)

        main_layout.addLayout(content_layout, stretch=1)

        # Action buttons container
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Open Settings button
        self.settings_button = QPushButton("Open Settings")
        self.settings_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_button.setFixedHeight(28)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        buttons_layout.addWidget(self.settings_button)

        # Retry Now button
        self.retry_button = QPushButton("Retry Now")
        self.retry_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.retry_button.setFixedHeight(28)
        self.retry_button.clicked.connect(self._on_retry_clicked)
        buttons_layout.addWidget(self.retry_button)

        # Spacer
        buttons_layout.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        ))

        # Dismiss button (X)
        self.dismiss_button = QPushButton("×")
        self.dismiss_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dismiss_button.setFixedSize(28, 28)
        dismiss_font = QFont()
        dismiss_font.setPointSize(14)
        dismiss_font.setBold(True)
        self.dismiss_button.setFont(dismiss_font)
        self.dismiss_button.clicked.connect(self._on_dismiss_clicked)
        buttons_layout.addWidget(self.dismiss_button)

        main_layout.addLayout(buttons_layout)

    def _apply_theme_styling(self):
        """Apply theme-aware styling to banner."""
        try:
            if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                colors = self.theme_manager.current_theme

                # Get error color
                error_color = colors.status_error if hasattr(colors, 'status_error') else '#e74c3c'
                text_color = colors.text_primary if hasattr(colors, 'text_primary') else '#ffffff'
                primary_color = colors.primary if hasattr(colors, 'primary') else '#3498db'

                # Calculate background with transparency
                bg_color = error_color
                border_color = ColorUtils.darken(error_color, 0.2)

                # Ensure text has good contrast
                # For error backgrounds, white text usually works best
                text_color = '#ffffff'

            else:
                # Fallback colors
                bg_color = '#e74c3c'
                border_color = '#c0392b'
                text_color = '#ffffff'
                primary_color = '#3498db'

            # Apply banner frame styling
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                }}
            """)

            # Apply label styling
            self.message_label.setStyleSheet(f"color: {text_color};")
            self.hints_label.setStyleSheet(f"color: {text_color}; opacity: 0.9;")

            # Apply button styling
            button_style = f"""
                QPushButton {{
                    background-color: {primary_color};
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {ColorUtils.lighten(primary_color, 0.1)};
                }}
                QPushButton:pressed {{
                    background-color: {ColorUtils.darken(primary_color, 0.1)};
                }}
            """
            self.settings_button.setStyleSheet(button_style)
            self.retry_button.setStyleSheet(button_style)

            # Dismiss button (transparent background)
            dismiss_style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_color};
                    border: 1px solid {text_color};
                    border-radius: 14px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.2);
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.3);
                }}
            """
            self.dismiss_button.setStyleSheet(dismiss_style)

            logger.debug("Theme styling applied to API error banner")

        except Exception as e:
            logger.error(f"Failed to apply theme styling: {e}")

    def show_error(self, error_message: str, provider_name: str = "API"):
        """
        Show error banner with specified message.

        Args:
            error_message: Error message to display
            provider_name: Name of the API provider (e.g., "OpenAI API")
        """
        logger.info(f"🔔 show_error() called - provider: {provider_name}, dismissed: {self._is_dismissed_by_user}")

        # Don't show if user dismissed it
        if self._is_dismissed_by_user:
            logger.debug("Banner dismissed by user, not showing again")
            return

        # Update message
        self._last_error_message = error_message
        self._provider_name = provider_name

        # Set message text
        self.message_label.setText(f"API Connection Lost - {provider_name}")
        logger.debug(f"Banner message set: API Connection Lost - {provider_name}")

        # Generate hints based on error message
        hints = self._generate_hints(error_message)
        self.hints_label.setText(hints)

        # Show banner with animation
        self._show_with_animation()

        logger.info(f"API error banner shown: {provider_name} - {error_message}")

    def _generate_hints(self, error_message: str) -> str:
        """
        Generate helpful hints based on error message.

        Args:
            error_message: The error message

        Returns:
            Formatted hints text with bullet points
        """
        error_lower = error_message.lower()
        hints = []

        # Authentication errors
        if any(term in error_lower for term in ['auth', 'api key', '401', '403', 'unauthorized']):
            hints.append("• Check your API key in Settings")
            hints.append("• Verify API key is valid and active")

        # Network errors
        elif any(term in error_lower for term in ['connection', 'network', 'timeout', 'unreachable']):
            hints.append("• Check your internet connection")
            hints.append("• API endpoint may be temporarily unavailable")

        # Rate limiting
        elif any(term in error_lower for term in ['rate limit', '429', 'too many']):
            hints.append("• Rate limit exceeded - wait before sending more messages")
            hints.append("• Consider upgrading your API plan")

        # Server errors
        elif any(term in error_lower for term in ['500', '502', '503', '504', 'server error']):
            hints.append("• API service is experiencing issues")
            hints.append("• This is temporary - will retry automatically")

        # SSL/Certificate errors
        elif any(term in error_lower for term in ['ssl', 'certificate', 'tls']):
            hints.append("• SSL certificate verification failed")
            hints.append("• Check SSL settings or disable verification")

        # Generic fallback
        else:
            hints.append("• Check your internet connection")
            hints.append("• Verify API settings in Settings")
            hints.append("• API endpoint may be temporarily unavailable")

        return "\n".join(hints)

    def hide_banner(self):
        """Hide banner with animation."""
        self._hide_with_animation()
        logger.debug("API error banner hidden")

    def reset_dismissal(self):
        """
        Reset dismissal state to allow banner to show again.
        Call this when settings change or connection restored.
        """
        self._is_dismissed_by_user = False
        logger.debug("Banner dismissal state reset")

    def _show_with_animation(self):
        """Show banner with slide-down animation."""
        if self.isVisible():
            return  # Already visible

        # Target height (will be calculated based on content)
        target_height = 80

        # Make visible but keep height at 0
        self.setVisible(True)
        self.setFixedHeight(0)

        # Animate height
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(250)  # 250ms animation
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_height)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(lambda: self.setFixedHeight(target_height))
        self.animation.start()

    def _hide_with_animation(self):
        """Hide banner with slide-up animation."""
        if not self.isVisible():
            return  # Already hidden

        current_height = self.height()

        # Animate height to 0
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(250)  # 250ms animation
        self.animation.setStartValue(current_height)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(lambda: self.setVisible(False))
        self.animation.start()

    def _on_dismiss_clicked(self):
        """Handle dismiss button click."""
        self._is_dismissed_by_user = True
        self._hide_with_animation()
        self.dismissed.emit()
        logger.info("API error banner dismissed by user")

    def _on_retry_clicked(self):
        """Handle retry button click."""
        logger.info("API retry requested from banner")
        self.retry_requested.emit()

    def _on_settings_clicked(self):
        """Handle settings button click."""
        logger.info("Settings requested from banner")
        self.settings_requested.emit()
