"""
Floating REPL Window for Ghostman.

A separate window that appears next to the avatar without moving it.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QWidget, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QCloseEvent, QMouseEvent, QShortcut, QKeySequence

from .repl_widget import REPLWidget
# Import window state management
from ...application.window_state import save_window_state, load_window_state

try:
    from ..ui.resize import REPLResizableMixin, HitZone
    from ..ui.resize.simple_arrow_mixin import SimpleREPLArrowMixin
    SIMPLE_ARROW_RESIZE_AVAILABLE = True
    ARROW_RESIZE_AVAILABLE = False  # Disable complex system
except ImportError:
    # Fallback if resize system is not available
    class REPLResizableMixin:
        def __init_repl_resize__(self, *args, **kwargs): pass
        def enable_resize(self): pass
        def disable_resize(self): pass
        def cleanup_resize(self): pass
    
    class SimpleREPLArrowMixin:
        def __init_simple_repl_arrows__(self, *args, **kwargs): pass
        def enable_simple_arrow_resize(self): pass
        def disable_simple_arrow_resize(self): pass
        def cleanup_simple_arrow_resize(self): pass
        def show_resize_arrows(self, auto_hide=None): pass
    
    HitZone = None
    SIMPLE_ARROW_RESIZE_AVAILABLE = False
    ARROW_RESIZE_AVAILABLE = False
try:
    from ...infrastructure.storage.settings_manager import settings as _global_settings
except Exception:  # pragma: no cover
    _global_settings = None

logger = logging.getLogger("ghostman.floating_repl")



class FloatingREPLWindow(SimpleREPLArrowMixin, REPLResizableMixin, QMainWindow):
    """
    Floating REPL window that appears next to the avatar.
    
    This is a separate window that positions itself relative to the avatar
    without affecting the avatar's position at all.
    """
    
    # Signals
    closed = pyqtSignal()
    command_entered = pyqtSignal(str)
    window_moved = pyqtSignal(QPoint)
    
    # Resize signals (from mixin)
    resize_started = pyqtSignal(object)  # HitZone
    resize_updated = pyqtSignal(object, int, int)  # HitZone, width, height
    resize_finished = pyqtSignal(object, int, int)  # HitZone, width, height
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.repl_widget = None
        
        # Initialize resize functionality - use simple arrow system
        self._use_simple_arrows = True
        try:
            if SIMPLE_ARROW_RESIZE_AVAILABLE and self._use_simple_arrows:
                self.__init_simple_repl_arrows__()
                logger.debug("Initialized simple arrow resize for REPL")
            else:
                self.__init_repl_resize__()
                logger.debug("Initialized traditional resize for REPL")
        except Exception as e:
            logger.warning(f"Failed to initialize resize functionality: {e}")
            # Fallback to traditional resize
            try:
                self.__init_repl_resize__()
                self._use_simple_arrows = False
                logger.debug("Falling back to traditional resize")
            except Exception as e2:
                logger.error(f"Failed to initialize any resize system: {e2}")
        
        self._init_ui()
        self._setup_window()

        # Direct arrow resize implementation (bypassing mixin complexity)
        self._setup_direct_arrows()

        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # Create floating banner window (initially hidden)
        self._init_floating_banner()

        logger.info("FloatingREPLWindow initialized")
    
    def _setup_direct_arrows(self):
        """Setup direct arrow resize functionality (bypassing mixin complexity)."""
        try:
            from ..ui.resize.grip_resize import GripResizeManager
            from ..ui.resize.constraints import SizeConstraints
            
            # Create REPL constraints (minimum 360x320, no maximum)
            constraints = SizeConstraints(
                min_width=360, min_height=320,
                max_width=None, max_height=None
            )
            
            # Create edge grip manager (no full overlay, just small grips)
            self._direct_arrow_manager = GripResizeManager(self, constraints)
            self._direct_arrows_enabled = False
            
            logger.debug("Direct arrow resize setup complete for REPL")
            
        except Exception as e:
            logger.warning(f"Failed to setup direct arrows for REPL: {e}")
            self._direct_arrow_manager = None
            self._direct_arrows_enabled = False
    
    def show_resize_arrows(self, auto_hide: bool = True):
        """Show resize arrows directly."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrow_manager.show_arrows(auto_hide=auto_hide)
            logger.debug(f"REPL direct arrows shown (auto_hide={auto_hide})")
        else:
            logger.warning("Direct arrow manager not available for REPL")
    
    def hide_resize_arrows(self):
        """Hide resize arrows directly."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrow_manager.hide_arrows()
            logger.debug("REPL direct arrows hidden")
    
    def enable_direct_arrows(self, enabled: bool = True):
        """Enable/disable direct arrow functionality."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrows_enabled = enabled
            if enabled:
                # For REPL, make arrows always visible
                self._direct_arrow_manager.set_always_visible(True)
                logger.debug("REPL direct arrows enabled (always visible)")
            else:
                self.hide_resize_arrows()
                logger.debug("REPL direct arrows disabled")
        else:
            logger.warning("Direct arrow manager not available for REPL")

    def enable_repl_resize(self, enabled: bool = True):
        """Enable or disable resize functionality for the REPL window."""
        try:
            # Use direct arrow approach that works
            self.enable_direct_arrows(enabled)
        except Exception as e:
            logger.warning(f"Failed to toggle REPL resize: {e}")
    
    def toggle_resize_system(self, use_simple_arrows: Optional[bool] = None):
        """Toggle between simple arrow and traditional resize systems."""
        if use_simple_arrows is None:
            use_simple_arrows = not self._use_simple_arrows
        
        if use_simple_arrows == self._use_simple_arrows:
            return  # Already using the requested system
        
        try:
            # Disable current system
            if self._use_simple_arrows:
                self.disable_simple_arrow_resize()
                self.cleanup_simple_arrow_resize()
            else:
                self.disable_resize()
                self.cleanup_resize()
            
            # Enable new system
            self._use_simple_arrows = use_simple_arrows
            if use_simple_arrows and SIMPLE_ARROW_RESIZE_AVAILABLE:
                self.__init_simple_repl_arrows__()
                self.enable_simple_arrow_resize()
                logger.info("Switched REPL to simple arrow resize")
            else:
                self.__init_repl_resize__()
                self.enable_resize()
                self._use_simple_arrows = False
                logger.info("Switched REPL to traditional resize")
                
        except Exception as e:
            logger.error(f"Failed to toggle resize system: {e}")
    
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create REPL widget as central widget
        self.repl_widget = REPLWidget()
        self.setCentralWidget(self.repl_widget)

        # REPL widget already loads its own opacity from settings in its constructor
        # No need to override it here since REPLWidget._load_opacity_from_settings() handles this

        # Connect REPL signals
        self.repl_widget.minimize_requested.connect(self.close)
        self.repl_widget.command_entered.connect(self.command_entered.emit)

        # API error banner will be managed by REPLWidget
        # Access it via self.repl_widget.api_error_banner if needed

        logger.debug("FloatingREPL UI initialized")
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("")  # No window title
        self.resize(520, 450)  # Default size: 500px + padding for REPL content
        self.setMinimumSize(300, 250)  # Set minimum size instead of fixed size
        
        # Get always on top setting from settings
        always_on_top = True  # Default value
        try:
            from ...infrastructure.storage.settings_manager import settings as _settings
            always_on_top = _settings.get('interface.always_on_top', True)
        except Exception:
            pass
        
        # Make window frameless and conditionally always on top
        base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool  # Prevents taskbar
        if always_on_top:
            base_flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(base_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set transparent background for the main window to allow child transparency
        self.setStyleSheet("FloatingREPLWindow { background-color: transparent; }")

        # Enable mouse tracking for cursor changes without button press
        self.setMouseTracking(True)

        # Window opacity is now controlled by REPLWidget.set_panel_opacity()
        # via settings (opacity slider) - don't hardcode it here
    
        
        
        logger.debug("FloatingREPL window properties configured")
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for the REPL window."""
        # Ctrl+H to hide/close the REPL window
        hide_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        hide_shortcut.activated.connect(self._hide_repl)
        
        logger.debug("REPL keyboard shortcuts configured: Ctrl+H to hide")
    
    def _hide_repl(self):
        """Hide/close the REPL window."""
        logger.info("REPL hide shortcut activated (Ctrl+H)")
        self.close()
    
    def save_current_window_state(self):
        """Save current REPL window position and size."""
        try:
            pos = self.pos()
            size = self.size()
            save_window_state('repl', pos.x(), pos.y(), size.width(), size.height())
        except Exception as e:
            logger.error(f"Failed to save REPL window state: {e}")
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Save window state when mouse is released (after move/resize)."""
        super().mouseReleaseEvent(event)
        # Save state after any mouse operation that could have moved/resized the window
        self.save_current_window_state()
    
    def resizeEvent(self, event):
        """Save window state when resized."""
        super().resizeEvent(event)
        # Save state after resize
        self.save_current_window_state()
    
    def moveEvent(self, event):
        """Save window state when moved."""
        super().moveEvent(event)
        # Save state after move
        self.save_current_window_state()
        try:
            self.window_moved.emit(self.pos())
        except Exception:
            pass
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Save current conversation before closing
        if self.repl_widget and hasattr(self.repl_widget, 'save_current_conversation'):
            try:
                self.repl_widget.save_current_conversation()
                logger.debug("Current conversation saved before window close")
            except Exception as e:
                logger.error(f"Failed to save conversation on close: {e}")
        
        # Cleanup resize functionality
        try:
            if self._use_simple_arrows:
                self.cleanup_simple_arrow_resize()
            else:
                self.cleanup_resize()
        except Exception as e:
            logger.debug(f"Error during resize cleanup: {e}")
        
        self.closed.emit()
        event.accept()
        logger.debug("FloatingREPL window closed")
    
    # Old eventFilter removed - no longer needed with ResizeGrip widgets
    
    # Resize functionality now handled by ResizeGrip widgets
    
    def position_relative_to_avatar(self, avatar_pos: QPoint, avatar_size: tuple, screen_geometry):
        """
        Position the REPL window using saved position or relative to avatar.
        
        Args:
            avatar_pos: Current position of the avatar window
            avatar_size: Size of the avatar window (width, height)
            screen_geometry: Available screen geometry
        """
        try:
            # Load saved window state
            window_state = load_window_state('repl')
            saved_position = window_state['position']
            saved_size = window_state['size']
            
            # Apply saved size
            self.resize(saved_size['width'], saved_size['height'])
            
            # Use saved position if available and valid, otherwise position relative to avatar
            if saved_position and 'x' in saved_position and 'y' in saved_position:
                repl_x, repl_y = saved_position['x'], saved_position['y']
                
                # Validate saved position is still on screen
                if (repl_x >= screen_geometry.left() and 
                    repl_x + self.width() <= screen_geometry.right() and
                    repl_y >= screen_geometry.top() and 
                    repl_y + self.height() <= screen_geometry.bottom()):
                    
                    logger.debug(f'Using saved REPL position: ({repl_x}, {repl_y}), size: {saved_size}')
                    final_pos = QPoint(repl_x, repl_y)
                    self.move(final_pos)
                    return
                else:
                    logger.info("Saved REPL position is off-screen, positioning relative to avatar")
            
        except Exception as e:
            logger.error(f"Failed to load REPL position, using relative positioning: {e}")
        
        # Fall back to relative positioning
        avatar_width, avatar_height = avatar_size
        repl_width = self.width()
        repl_height = self.height()
        
        # Default position: to the right of avatar
        repl_x = avatar_pos.x() + avatar_width + 10  # 10px gap
        repl_y = avatar_pos.y()
        
        logger.debug(f'Positioning REPL relative to avatar: avatar at {avatar_pos}, size {avatar_size}')
        logger.debug(f'Initial REPL position: ({repl_x}, {repl_y}), screen: {screen_geometry}')
        
        # Check if REPL would go off the right edge of screen
        if repl_x + repl_width > screen_geometry.right():
            logger.debug('REPL would go off-screen right, positioning on left')
            # Position to the left of avatar
            repl_x = avatar_pos.x() - repl_width - 10  # 10px gap on left
            
            # If it would still go off the left edge, clamp to screen edge
            if repl_x < screen_geometry.left():
                repl_x = screen_geometry.left() + 10
                logger.debug(f'Clamped to left edge: {repl_x}')
        
        # Check if REPL would go off the bottom edge
        if repl_y + repl_height > screen_geometry.bottom():
            logger.debug('REPL would go off-screen bottom, adjusting Y position')
            repl_y = screen_geometry.bottom() - repl_height - 10
            
            # If it would go off the top, clamp to top
            if repl_y < screen_geometry.top():
                repl_y = screen_geometry.top() + 10
                logger.debug(f'Clamped to top edge: {repl_y}')
        
        final_pos = QPoint(repl_x, repl_y)
        self.move(final_pos)
        
        logger.debug(f'FloatingREPL positioned at: {final_pos}')

    def move_attached(self, avatar_pos: QPoint, offset: QPoint, screen_geometry):
        """Move REPL based on avatar position plus offset, clamped to screen."""
        try:
            target = avatar_pos + offset
            x = max(screen_geometry.left() + 5, min(target.x(), screen_geometry.right() - self.width() - 5))
            y = max(screen_geometry.top() + 5, min(target.y(), screen_geometry.bottom() - self.height() - 5))
            final = QPoint(x, y)
            self.move(final)
            logger.debug(f"REPL moved (attached) to: {final} (offset {offset})")
        except Exception as e:
            logger.error(f"Failed move_attached: {e}")
    
    def show_and_activate(self):
        """Show the window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Focus on the command input
        if self.repl_widget and self.repl_widget.command_input:
            self.repl_widget.command_input.setFocus()
        
        logger.debug("FloatingREPL shown and activated")

    # Public API -----------------------------------------------------
    def set_panel_opacity(self, opacity: float):
        """Set only the panel (frame) opacity (content/text remains fully opaque)."""
        if self.repl_widget:
            self.repl_widget.set_panel_opacity(opacity)

    # Floating Banner Management -----------------------------------------
    def _init_floating_banner(self):
        """Initialize the floating banner window."""
        try:
            from .floating_banner import FloatingBannerWindow
            from ...ui.themes.theme_manager import get_theme_manager

            theme_manager = get_theme_manager()
            self.floating_banner = FloatingBannerWindow(self, theme_manager)

            # Connect banner signals
            self.floating_banner.banner.retry_requested.connect(self._on_banner_retry)
            self.floating_banner.banner.settings_requested.connect(self._on_banner_settings)

            # Connect to validator (deferred)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._connect_banner_to_validator)

            logger.info("Floating banner window created")

        except Exception as e:
            logger.error(f"Failed to create floating banner: {e}")
            self.floating_banner = None

    def _connect_banner_to_validator(self):
        """Connect banner to validator (called after initialization)."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and hasattr(app, 'coordinator'):
                coordinator = app.coordinator
                if coordinator and hasattr(coordinator, '_api_validator') and coordinator._api_validator:
                    # Connect validator signals directly to our handlers
                    coordinator._api_validator.validation_failed.connect(self._on_api_validation_failed)
                    coordinator._api_validator.validation_succeeded.connect(self._on_api_validation_succeeded)
                    logger.info("✓ FloatingREPL banner connected to validator")
                else:
                    logger.warning("Coordinator or validator not available")
            else:
                logger.warning("QApplication or coordinator not available for banner connection")
        except Exception as e:
            logger.error(f"Failed to connect banner to validator: {e}")

    def _on_api_validation_failed(self, result):
        """Handle API validation failure (show banner)."""
        try:
            logger.info(f"📨 FloatingREPL._on_api_validation_failed() called")
            logger.debug(f"📊 Signal data: provider={result.provider_name}, error={result.error_message}")
            logger.debug(f"📊 Banner state: floating_banner exists={self.floating_banner is not None}")
            logger.debug(f"📊 REPL window visible: {self.isVisible()}")

            # Only show banner if REPL window is visible (not in system tray)
            if not self.isVisible():
                logger.info("⊗ REPL window hidden (in system tray) - not showing banner")
                return

            if self.floating_banner:
                error_message = result.error_message or "Unknown error"
                provider_name = result.provider_name or "API"
                logger.debug(f"✅ Calling floating_banner.show_error() with provider={provider_name}")
                self.floating_banner.show_error(error_message, provider_name)
                logger.info(f"✓ Banner show_error() completed for: {provider_name}")
            else:
                logger.error("❌ Banner not available to show error")
        except Exception as e:
            logger.error(f"Failed to show API error banner: {e}", exc_info=True)

    def _on_api_validation_succeeded(self):
        """Handle API validation success (hide banner if visible)."""
        try:
            if self.floating_banner and hasattr(self.floating_banner, 'banner'):
                banner = self.floating_banner.banner
                # Only hide if banner is actually visible
                if hasattr(banner, 'is_banner_visible') and banner.is_banner_visible():
                    banner.hide_banner()
                    logger.info("✓ Banner was visible - hiding it now (API connection restored)")
                else:
                    logger.debug("Banner not visible - nothing to hide")
        except Exception as e:
            logger.error(f"Failed to hide API error banner: {e}")

    def _on_banner_retry(self):
        """Handle retry button click from banner."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and hasattr(app, 'coordinator'):
                coordinator = app.coordinator
                if coordinator and hasattr(coordinator, '_api_validator') and coordinator._api_validator:
                    coordinator._api_validator.validate_now()
                    logger.info("Manual API validation triggered from banner")
        except Exception as e:
            logger.error(f"Failed to trigger API retry: {e}")

    def _on_banner_settings(self):
        """Handle settings button click from banner."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and hasattr(app, 'coordinator'):
                coordinator = app.coordinator
                if coordinator:
                    coordinator._show_settings()
                    logger.info("Settings dialog requested from banner")
        except Exception as e:
            logger.error(f"Failed to open settings from banner: {e}")


    # Window Event Handlers -----------------------------------------------
    def moveEvent(self, event):
        """Handle window move events to update banner position."""
        super().moveEvent(event)
        if hasattr(self, 'floating_banner') and self.floating_banner:
            self.floating_banner.track_parent_movement()

    def resizeEvent(self, event):
        """Handle window resize events to update banner width."""
        super().resizeEvent(event)
        if hasattr(self, 'floating_banner') and self.floating_banner:
            self.floating_banner.track_parent_movement()

    def showEvent(self, event):
        """Handle window show events to position banner."""
        super().showEvent(event)
        if hasattr(self, 'floating_banner') and self.floating_banner and self.floating_banner.isVisible():
            from PyQt6.QtCore import QTimer
            # Delay slightly to ensure window is fully positioned
            QTimer.singleShot(10, self.floating_banner.track_parent_movement)

    def hideEvent(self, event):
        """Handle window hide events to hide banner."""
        super().hideEvent(event)
        if hasattr(self, 'floating_banner') and self.floating_banner:
            self.floating_banner.hide()

    def __del__(self):
        """Cleanup when widget is destroyed."""
        try:
            if hasattr(self, '_use_simple_arrows') and self._use_simple_arrows:
                if hasattr(self, 'cleanup_simple_arrow_resize'):
                    self.cleanup_simple_arrow_resize()
            elif hasattr(self, 'cleanup_resize'):
                self.cleanup_resize()
        except Exception:
            pass  # Ignore errors during destruction