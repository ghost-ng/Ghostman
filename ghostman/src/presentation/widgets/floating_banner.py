"""
Floating Banner Window for Ghostman.

A frameless window that floats above the REPL and moves with it.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint
from .api_error_banner import APIErrorBanner

logger = logging.getLogger("ghostman.floating_banner")


class FloatingBannerWindow(QWidget):
    """
    Floating banner window that stays attached to the REPL window.

    This window:
    - Has no frame or decorations
    - Stays on top of other windows
    - Moves automatically when the REPL window moves
    - Shows/hides based on API validation state
    """

    def __init__(self, parent_window, theme_manager):
        """
        Initialize the floating banner window.

        Args:
            parent_window: The REPL window this banner is attached to
            theme_manager: Theme manager for styling
        """
        super().__init__()

        self.parent_window = parent_window
        self.theme_manager = theme_manager

        # Setup window flags for frameless, always-on-top behavior
        self.setWindowFlags(
            Qt.WindowType.Tool |  # Tool window (no taskbar entry)
            Qt.WindowType.FramelessWindowHint |  # No frame
            Qt.WindowType.WindowStaysOnTopHint  # Always on top
        )

        # Make window background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Initialize UI
        self._init_ui()

        # Start hidden
        self.hide()

        logger.debug("FloatingBannerWindow initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create banner widget
        self.banner = APIErrorBanner(self.theme_manager, self)
        layout.addWidget(self.banner)

        # Set fixed height based on banner height
        self.setFixedHeight(59)  # 74% of original 80px

        logger.debug("FloatingBanner UI initialized")

    def show_error(self, error_message: str, provider_name: str = "API", custom_message: str = None):
        """
        Show the banner with an error message.

        Args:
            error_message: The error message to display
            provider_name: Name of the API provider
            custom_message: Optional custom message to override default banner text
        """
        logger.info(f"🔔 FloatingBanner.show_error() called with provider={provider_name}, error={error_message}, custom={custom_message}")
        logger.debug(f"📍 Banner current state: isVisible={self.isVisible()}, parent_window exists={self.parent_window is not None}")

        # Update banner content
        self.banner.show_error(error_message, provider_name, custom_message=custom_message)
        logger.debug("✅ Banner content updated")

        # Position above parent window
        self.update_position()
        logger.debug("✅ Banner position updated")

        # Show the floating window
        self.show()
        self.raise_()
        logger.info(f"✅ FloatingBanner window shown, now visible={self.isVisible()}")

    def hide_banner(self):
        """Hide the banner."""
        logger.debug("FloatingBanner hiding")
        self.banner.hide_banner()
        self.hide()


    def update_position(self):
        """Update the position to stay above the parent window."""
        if not self.parent_window or not self.parent_window.isVisible():
            logger.debug(f"❌ Cannot update position: parent_window exists={self.parent_window is not None}, parent_visible={self.parent_window.isVisible() if self.parent_window else False}")
            return

        # Get parent window geometry
        parent_pos = self.parent_window.pos()
        parent_width = self.parent_window.width()

        # Position banner directly above parent window
        banner_x = parent_pos.x()
        banner_y = parent_pos.y() - self.height()

        # Set width to match parent
        self.setFixedWidth(parent_width)

        # Move to position
        self.move(banner_x, banner_y)

        logger.debug(f"📍 FloatingBanner positioned at ({banner_x}, {banner_y}) width={parent_width}, height={self.height()}")

    def track_parent_movement(self):
        """
        Track parent window movement and update position accordingly.

        This should be called when the parent window moves or resizes.
        """
        if self.isVisible():
            self.update_position()
