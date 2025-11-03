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
        self._last_error_message = ""
        self._provider_name = ""
        self._is_visible = False  # Track if banner is currently shown

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
        main_layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Error message label (single line, centered vertically)
        self.message_label = QLabel()
        self.message_label.setWordWrap(False)  # Single line
        message_font = QFont()
        message_font.setBold(True)
        message_font.setPointSize(10)
        self.message_label.setFont(message_font)
        main_layout.addWidget(self.message_label, 1, Qt.AlignmentFlag.AlignVCenter)

        # Action hints (hidden by default, can be shown later if needed)
        self.hints_label = QLabel()
        self.hints_label.setWordWrap(True)
        self.hints_label.setVisible(False)  # Hide hints to keep banner single-line
        hints_font = QFont()
        hints_font.setPointSize(9)
        self.hints_label.setFont(hints_font)
        # Don't add hints_label to layout since it's hidden

        # Open Settings button
        self.settings_button = QPushButton("Open Settings")
        self.settings_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_button.setFixedHeight(28)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        main_layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignVCenter)

        # Retry Now button
        self.retry_button = QPushButton("Retry Now")
        self.retry_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.retry_button.setFixedHeight(28)
        self.retry_button.clicked.connect(self._on_retry_clicked)
        main_layout.addWidget(self.retry_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def _apply_theme_styling(self):
        """Apply theme-aware styling to banner."""
        try:
            if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                colors = self.theme_manager.current_theme

                # Get error color
                error_color = colors.status_error if hasattr(colors, 'status_error') else '#e74c3c'
                text_color = colors.text_primary if hasattr(colors, 'text_primary') else '#ffffff'

                # Ensure text has good contrast
                # For error backgrounds, white text usually works best
                text_color = '#ffffff'

            else:
                # Fallback colors
                error_color = '#e74c3c'
                text_color = '#ffffff'
                colors = None

            # Apply banner frame styling (no border)
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {error_color};
                    border: none;
                    border-radius: 6px;
                }}
            """)

            # Apply label styling
            self.message_label.setStyleSheet(f"color: {text_color};")
            self.hints_label.setStyleSheet(f"color: {text_color}; opacity: 0.9;")

            # Use EXACT same styling as conversation tab buttons
            if colors:
                try:
                    from ...ui.themes.style_templates import StyleTemplates
                    # Use the same style as active conversation tabs
                    tab_button_style = StyleTemplates.get_conversation_tab_button_style(colors, active=True)

                    # Apply to both buttons
                    self.settings_button.setStyleSheet(tab_button_style)
                    self.retry_button.setStyleSheet(tab_button_style)
                    logger.debug("Applied conversation tab button styling to banner buttons")
                except ImportError:
                    # Fall through to fallback styling below
                    pass

            if not colors or not hasattr(self.settings_button, 'styleSheet') or not self.settings_button.styleSheet():
                # Fallback styling if colors is None or import failed
                # Fallback to legacy styling if ButtonStyleManager not available
                primary_color = colors.primary if colors and hasattr(colors, 'primary') else '#3498db'
                button_text_color = colors.text_primary if colors and hasattr(colors, 'text_primary') else '#00ff41'
                button_style = f"""
                    QPushButton {{
                        background-color: {primary_color};
                        color: {button_text_color};
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-weight: bold;
                        font-size: 12px;
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

            logger.debug("Theme styling applied to API error banner")

        except Exception as e:
            logger.error(f"Failed to apply theme styling: {e}")

    def show_error(self, error_message: str, provider_name: str = "API", custom_message: str = None):
        """
        Show error banner with specified message.

        Args:
            error_message: Error message to display (for logging/hints)
            provider_name: Name of the API provider (e.g., "OpenAI API")
            custom_message: Optional custom message to display in banner (overrides default)
        """
        logger.info(f"🔔 show_error() called - provider: {provider_name}")

        # Update message
        self._last_error_message = error_message
        self._provider_name = provider_name
        self._is_visible = True  # Set flag when showing

        # Set message text (use custom message if provided, otherwise default)
        display_message = custom_message if custom_message else "Check your network settings"
        self.message_label.setText(display_message)
        logger.debug(f"Banner message set: {display_message} - {provider_name}")

        # Generate hints based on error message
        #hints = self._generate_hints(error_message)
        #self.hints_label.setText(hints)

        # Show banner with animation
        self._show_with_animation()

        logger.info(f"✓ API error banner shown: {provider_name} - flag set to True")

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
            hints.append("• Check your network configuration")
            hints.append("• Verify internet connectivity")

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
        self._is_visible = False  # Clear flag when hiding
        self._hide_with_animation()
        logger.info("✓ API error banner hidden - flag set to False")

    def is_banner_visible(self):
        """Check if banner is currently visible."""
        return self._is_visible


    def _show_with_animation(self):
        """Show banner with slide-down animation."""
        if self.isVisible():
            return  # Already visible

        # Target height (reduced to 74% of original 80px = 59px)
        target_height = 59

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


    def _on_retry_clicked(self):
        """Handle retry button click."""
        logger.info("API retry requested from banner")
        self.retry_requested.emit()

    def _on_settings_clicked(self):
        """Handle settings button click."""
        logger.info("Settings requested from banner")
        self.settings_requested.emit()
