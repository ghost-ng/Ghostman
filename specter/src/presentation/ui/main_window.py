"""
Main Window for Specter Avatar Mode.

Provides the avatar interface when in Avatar mode.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QCloseEvent, QMouseEvent, QShortcut, QKeySequence

# Import window state management
from ...application.window_state import save_window_state, load_window_state
from ...infrastructure.storage.settings_manager import settings

logger = logging.getLogger("specter.main_window")


class MainWindow(QMainWindow):
    """
    Main application window for Avatar mode.
    
    Contains only the avatar widget - REPL is now a separate floating window.
    """
    
    # Signals
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    help_requested = pyqtSignal()
    conversations_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, app_coordinator):
        super().__init__()
        self.app_coordinator = app_coordinator
        self.floating_repl = None
        self.conversation_browser = None  # Simple conversation browser
        # Attach state (REPL snapped to avatar)
        self._repl_attached: bool = bool(settings.get('interface.repl_attached', False))
        off = settings.get('interface.repl_attach_offset', None)
        if isinstance(off, dict) and 'x' in off and 'y' in off:
            self._repl_attach_offset = QPoint(int(off['x']), int(off['y']))
        else:
            self._repl_attach_offset = QPoint(140, 0)  # sensible default; will be recalculated when attaching
        
        self._init_ui()
        self._setup_window()
        self._setup_keyboard_shortcuts()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Initialize the user interface with only the avatar widget."""
        # Import widgets
        from ..widgets.avatar_widget import AvatarWidget
        from ..widgets.floating_repl import FloatingREPLWindow
        
        # Create the avatar widget as central widget
        self.avatar_widget = AvatarWidget()
        self.avatar_widget.minimize_requested.connect(self.minimize_requested.emit)
        self.avatar_widget.avatar_clicked.connect(self._toggle_repl)
        self.avatar_widget.screen_capture_requested.connect(self._on_screen_capture_requested)
        self.avatar_widget.settings_requested.connect(self.settings_requested.emit)
        self.avatar_widget.conversations_requested.connect(self._show_conversations)
        self.avatar_widget.help_requested.connect(self.help_requested.emit)
        self.avatar_widget.quit_requested.connect(self.quit_requested.emit)
        self.setCentralWidget(self.avatar_widget)
        
        # Create floating REPL window (initially hidden)
        self.floating_repl = FloatingREPLWindow()
        self.floating_repl.closed.connect(self._on_repl_closed)
        self.floating_repl.command_entered.connect(self._on_command_entered)
        # Connect REPL widget signals through floating REPL
        self.floating_repl.repl_widget.settings_requested.connect(self.settings_requested.emit)
        self.floating_repl.repl_widget.help_requested.connect(self.help_requested.emit)
        self.floating_repl.repl_widget.browse_requested.connect(self._show_conversations)
        self.floating_repl.repl_widget.pin_toggle_requested.connect(self._on_pin_toggle)
        # Wire attach toggle from REPL title bar
        if hasattr(self.floating_repl.repl_widget, 'attach_toggle_requested'):
            self.floating_repl.repl_widget.attach_toggle_requested.connect(self._on_attach_toggle)
            # Sync initial visual state
            if hasattr(self.floating_repl.repl_widget, 'set_attach_state'):
                self.floating_repl.repl_widget.set_attach_state(self._repl_attached)
        # Update offset when user manually moves REPL while attached
        if hasattr(self.floating_repl, 'window_moved'):
            self.floating_repl.window_moved.connect(self._on_repl_moved)
        
        # Set window background
        self._set_window_style()
        
        logger.debug("UI components initialized - avatar only, REPL is floating")
    
    def _setup_window(self):
        """Setup window properties."""
        # Dynamic window title based on selected avatar persona
        try:
            from ...infrastructure.storage.settings_manager import settings
            from ...domain.models.avatar_personas import get_avatar, DEFAULT_AVATAR_ID
            avatar_id = settings.get('avatar.selected', DEFAULT_AVATAR_ID)
            avatar = get_avatar(avatar_id)
            self.setWindowTitle(f"{avatar.name if avatar else 'Specter'} - AI Assistant")
        except Exception:
            self.setWindowTitle("Specter - AI Assistant")

        # Set taskbar icon
        try:
            from ...utils.resource_resolver import resolve_asset
            from PyQt6.QtGui import QIcon
            icon_path = resolve_asset("app_icon.png")
            if icon_path:
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass

        self.setMinimumSize(60, 60)

        # Apply saved avatar scale
        base_size = 120
        try:
            from ...infrastructure.storage.settings_manager import settings as _s
            scale = _s.get('avatar.scale', 1.0)
            scaled_size = max(72, min(int(base_size * scale), 600))
        except Exception:
            scaled_size = base_size
        self.resize(scaled_size, scaled_size)
        
        # Get always on top setting from settings
        always_on_top = True  # Default value
        try:
            from ..infrastructure.storage.settings_manager import settings as _settings
            always_on_top = _settings.get('interface.always_on_top', True)
        except Exception:
            pass
        
        # Make window frameless and conditionally always on top
        base_flags = Qt.WindowType.FramelessWindowHint
        if always_on_top:
            base_flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(base_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Center the window
        self._center_window()
        
        logger.debug("Window properties configured")
    
    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts for the main window."""
        # Ctrl+M to minimize to taskbar/tray
        minimize_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        minimize_shortcut.activated.connect(self._minimize_to_taskbar)
        
        logger.debug("MainWindow keyboard shortcuts configured: Ctrl+M to minimize")
    
    def _minimize_to_taskbar(self):
        """Minimize the entire application to taskbar/tray."""
        logger.info("Minimize shortcut activated (Ctrl+M)")
        # Emit minimize signal which will be handled by the app coordinator
        self.minimize_requested.emit()
    
    def _set_window_style(self):
        """Set the window style and background."""
        # Set a gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2
                );
                border-radius: 20px;
            }
        """)
    
    def _center_window(self):
        """Position the window using saved position or default to bottom right corner."""
        try:
            # Load saved window state
            window_state = load_window_state('avatar')
            saved_position = window_state['position']
            saved_size = window_state['size']
            
            # Apply saved size
            self.resize(saved_size['width'], saved_size['height'])
            
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                
                # If no saved position, use bottom-right default
                if saved_position is None:
                    logger.info("No saved avatar position - using bottom-right default")
                    window_geometry = self.frameGeometry()
                    padding = 50
                    x = screen_geometry.right() - window_geometry.width() - padding
                    y = screen_geometry.bottom() - window_geometry.height() - padding
                else:
                    # Use saved position if valid
                    x, y = saved_position['x'], saved_position['y']
                    
                    # Validate position is on screen
                    if (x < screen_geometry.left() or x > screen_geometry.right() - 100 or
                        y < screen_geometry.top() or y > screen_geometry.bottom() - 100):
                        
                        logger.info("Saved avatar position is off-screen, using bottom-right default")
                        # Fall back to bottom-right default
                        window_geometry = self.frameGeometry()
                        padding = 50
                        x = screen_geometry.right() - window_geometry.width() - padding
                        y = screen_geometry.bottom() - window_geometry.height() - padding
                
                logger.debug(f'Positioning avatar window at: ({x}, {y}), size: {saved_size}')
                self.move(x, y)
                
        except Exception as e:
            logger.error(f"Failed to load avatar window position, using bottom-right default: {e}")
            # Fall back to bottom-right positioning
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.frameGeometry()
                
                padding = 50
                x = screen_geometry.right() - window_geometry.width() - padding
                y = screen_geometry.bottom() - window_geometry.height() - padding
                
                logger.debug(f'Using bottom-right default positioning: ({x}, {y})')
                self.move(x, y)
    
    def save_current_window_state(self):
        """Save current window position and size."""
        try:
            pos = self.pos()
            size = self.size()
            save_window_state('avatar', pos.x(), pos.y(), size.width(), size.height())
        except Exception as e:
            logger.error(f"Failed to save avatar window state: {e}")
    
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
        # If REPL is attached, move it along with the avatar using stored offset
        try:
            if self._repl_attached and self.floating_repl and self.floating_repl.isVisible():
                logger.debug(f"🔗 Avatar moved - moving attached REPL. Avatar at: {self.pos()}")
                self._move_attached_repl()
            elif self._repl_attached:
                logger.debug(f"🔗 Avatar moved but REPL not visible (attached={self._repl_attached})")
        except Exception as e:
            logger.debug(f"Failed to move attached REPL: {e}")
        # Save state after move
        self.save_current_window_state()
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Save REPL visibility state before hiding
        repl_was_visible = self.floating_repl and self.floating_repl.isVisible()
        settings.set('interface.repl_was_visible', repl_was_visible)
        logger.debug(f"Saved REPL visibility state on close: {repl_was_visible}")
        
        # Hide floating REPL if it's visible
        if repl_was_visible:
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to window close")
        
        # Save current conversation state before closing
        try:
            if (hasattr(self.app_coordinator, '_cleanup_on_shutdown') and 
                hasattr(self, 'floating_repl') and 
                self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget')):
                
                repl_widget = self.floating_repl.repl_widget
                if hasattr(repl_widget, '_has_unsaved_messages') and repl_widget._has_unsaved_messages():
                    logger.info("💾 Saving unsaved messages before window close...")
                    # Let app coordinator handle the cleanup
                    
        except Exception as e:
            logger.error(f"Failed to check/save unsaved messages: {e}")
        
        # Don't actually close, just minimize to tray
        event.ignore()
        self.hide()
        self.close_requested.emit()
        logger.debug("Window close event - minimizing to tray")
    
    def show_and_activate(self):
        """Show the window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Restore REPL visibility if it was previously visible
        try:
            repl_was_visible = settings.get('interface.repl_was_visible', False)
            if repl_was_visible and self.floating_repl:
                logger.debug(f"Restoring REPL visibility: {repl_was_visible}")
                self._show_repl()
        except Exception as e:
            logger.error(f"Failed to restore REPL visibility: {e}")
        
        logger.debug("Window shown and activated")
    
    def minimize_to_tray(self):
        """Minimize the window to system tray."""
        # Save REPL visibility state before hiding
        repl_was_visible = self.floating_repl and self.floating_repl.isVisible()
        settings.set('interface.repl_was_visible', repl_was_visible)
        logger.debug(f"Saved REPL visibility state: {repl_was_visible}")
        
        # Hide floating REPL if it's visible
        if repl_was_visible:
            self.floating_repl.hide()
            logger.debug("Floating REPL hidden due to minimize to tray")
        
        self.hide()
        self.minimize_requested.emit()
        logger.debug("Window minimized to tray")
    
    def _toggle_repl(self):
        """Toggle floating REPL visibility."""
        if self.floating_repl.isVisible():
            self._hide_repl()
        else:
            self._show_repl()

    def _on_screen_capture_requested(self):
        """Handle screen capture request from avatar menu."""
        logger.info("Screen capture requested from avatar")
        # Delegate to app_coordinator's handler
        if self.app_coordinator:
            self.app_coordinator._trigger_screen_capture()

    def _show_repl(self):
        """Show the floating REPL positioned relative to avatar - avatar never moves."""
        # Get current avatar position and screen info
        avatar_pos = self.pos()
        avatar_size = (self.width(), self.height())
        screen = self.screen()
        
        logger.debug(f'Showing floating REPL: avatar at {avatar_pos}, size {avatar_size}')
        
        if screen:
            screen_geometry = screen.availableGeometry()
            
            if self._repl_attached:
                # When attached, try to use saved positions first if they exist
                repl_positioned_by_saved = False
                try:
                    from ..application.window_state import load_window_state
                    repl_state = load_window_state('repl')
                    
                    if (repl_state['position'] and 
                        'x' in repl_state['position'] and 
                        'y' in repl_state['position']):
                        
                        repl_x, repl_y = repl_state['position']['x'], repl_state['position']['y']
                        repl_size = repl_state['size']
                        
                        # Enhanced validation for attached windows - more lenient for left-side positioning
                        validation_result = self._validate_attached_repl_position(
                            repl_x, repl_y, repl_size, screen_geometry, avatar_pos
                        )
                        
                        if validation_result['valid']:
                            # Use saved position and update offset based on current avatar position
                            self.floating_repl.resize(repl_size['width'], repl_size['height'])
                            self.floating_repl.move(repl_x, repl_y)
                            self._repl_attach_offset = QPoint(repl_x, repl_y) - avatar_pos
                            repl_positioned_by_saved = True
                            self.floating_repl._window_state_ready = True
                            logger.debug(f'✓ Used saved REPL position: ({repl_x}, {repl_y}), offset: {self._repl_attach_offset}')
                        else:
                            logger.debug(f'✗ Saved REPL position validation failed: {validation_result["reason"]}')
                            # Auto-debug when validation fails
                            if logger.isEnabledFor(logging.DEBUG):
                                self.debug_attachment_state()
                            
                except Exception as e:
                    logger.debug(f"Could not use saved REPL position: {e}")
                
                if not repl_positioned_by_saved:
                    # Fall back to current attachment logic
                    self._ensure_attach_offset_default()
                    self.floating_repl.move_attached(avatar_pos, self._repl_attach_offset, screen_geometry)
                    self.floating_repl._window_state_ready = True
                    logger.debug("Used attachment offset for REPL positioning")
            else:
                # Position REPL relative to avatar (avatar position unchanged)
                self.floating_repl.position_relative_to_avatar(
                    avatar_pos, avatar_size, screen_geometry
                )
            
            # Show and activate the REPL
            self.floating_repl.show_and_activate()
            
            logger.debug(f'Floating REPL shown, avatar remains at: {self.pos()}')
    
    def _hide_repl(self):
        """Hide the floating REPL - avatar position completely unaffected."""
        logger.debug(f'Hiding floating REPL, avatar at: {self.pos()}')
        self.floating_repl.hide()
        logger.debug(f'Floating REPL hidden, avatar still at: {self.pos()}')
    
    def _on_repl_closed(self):
        """Handle floating REPL window being closed."""
        logger.debug(f'Floating REPL closed by user, avatar remains at: {self.pos()}')

    def _on_attach_toggle(self, attached: bool):
        """Handle attach toggle from REPL title bar."""
        logger.info(f"🔗 MainWindow received attach toggle signal: {attached}")
        self._repl_attached = bool(attached)
        try:
            # Persist state
            settings.set('interface.repl_attached', self._repl_attached)
            logger.info(f"🔗 Saved attach state to settings: {self._repl_attached}")
            
            # Compute and persist offset when attaching
            if self._repl_attached and self.floating_repl:
                # If REPL not visible yet, compute a sensible default to the right of avatar
                if not self.floating_repl.isVisible():
                    logger.info("🔗 REPL not visible, using default offset")
                    self._ensure_attach_offset_default()
                else:
                    logger.info("🔗 REPL visible, computing offset from current positions")
                    self._repl_attach_offset = self.floating_repl.pos() - self.pos()
                    logger.info(f"🔗 Computed offset: {self._repl_attach_offset}")
                    
                # Save the computed offset
                self._save_attach_offset()
                
                # If visible, snap immediately
                if self.floating_repl.isVisible():
                    screen = self.screen()
                    if screen:
                        logger.info(f"🔗 Snapping REPL to attached position immediately")
                        self.floating_repl.move_attached(self.pos(), self._repl_attach_offset, screen.availableGeometry())
            else:
                logger.info(f"🔗 Detached or REPL not available")
                
            # Update button visual if needed
            if hasattr(self.floating_repl.repl_widget, 'set_attach_state'):
                self.floating_repl.repl_widget.set_attach_state(self._repl_attached)
        except Exception as e:
            logger.error(f"Failed to handle attach toggle: {e}")

    def _validate_attached_repl_position(self, repl_x, repl_y, repl_size, screen_geometry, avatar_pos):
        """
        Enhanced validation for attached REPL positions with detailed debugging.
        
        Args:
            repl_x, repl_y: Proposed REPL position
            repl_size: Dictionary with 'width' and 'height' keys
            screen_geometry: QRect of available screen area
            avatar_pos: QPoint of current avatar position
            
        Returns:
            Dictionary with 'valid' boolean and 'reason' string for debugging
        """
        try:
            # Calculate the offset this position would create
            proposed_offset = QPoint(repl_x, repl_y) - avatar_pos
            
            # More lenient visibility requirements for attached windows
            # Only require 80px width and 40px height to be visible (title bar + some content)
            min_visible_width = min(80, repl_size['width'] // 3)
            min_visible_height = min(40, repl_size['height'] // 6)
            
            # Check visibility constraints
            left_visible = repl_x + min_visible_width >= screen_geometry.left()
            right_visible = repl_x + repl_size['width'] - min_visible_width <= screen_geometry.right()
            top_visible = repl_y + min_visible_height >= screen_geometry.top()
            bottom_visible = repl_y + repl_size['height'] - min_visible_height <= screen_geometry.bottom()
            
            # Special handling for left-side positioning (negative offset.x)
            if proposed_offset.x() < 0:
                logger.debug(f"🔍 Left-side REPL detected: offset.x = {proposed_offset.x()}")
                # For left-side, be more lenient about the right edge
                # Just ensure the REPL isn't completely off-screen
                right_visible = repl_x + min_visible_width <= screen_geometry.right()
            
            # Detailed debugging information
            debug_info = {
                'repl_pos': f'({repl_x}, {repl_y})',
                'repl_size': f"{repl_size['width']}x{repl_size['height']}",
                'avatar_pos': f'({avatar_pos.x()}, {avatar_pos.y()})',
                'offset': f'({proposed_offset.x()}, {proposed_offset.y()})',
                'screen': f'{screen_geometry.left()},{screen_geometry.top()} to {screen_geometry.right()},{screen_geometry.bottom()}',
                'min_visible': f'{min_visible_width}x{min_visible_height}',
                'checks': f'L={left_visible}, R={right_visible}, T={top_visible}, B={bottom_visible}'
            }
            
            is_valid = left_visible and right_visible and top_visible and bottom_visible
            
            if is_valid:
                logger.debug(f"🔍 REPL position validation SUCCESS: {debug_info}")
                return {'valid': True, 'reason': 'Position is sufficiently visible'}
            else:
                failed_checks = []
                if not left_visible: failed_checks.append('left_edge')
                if not right_visible: failed_checks.append('right_edge')
                if not top_visible: failed_checks.append('top_edge')
                if not bottom_visible: failed_checks.append('bottom_edge')
                
                reason = f"Failed visibility checks: {', '.join(failed_checks)}. Debug: {debug_info}"
                logger.debug(f"🔍 REPL position validation FAILED: {reason}")
                return {'valid': False, 'reason': reason}
                
        except Exception as e:
            error_reason = f"Validation error: {e}"
            logger.error(f"🔍 REPL position validation ERROR: {error_reason}")
            return {'valid': False, 'reason': error_reason}

    def _ensure_attach_offset_default(self):
        """
        Ensure we have a reasonable default offset when attaching.
        
        Tries to preserve existing offset orientation (left vs right) if available,
        otherwise defaults to right-side positioning.
        """
        try:
            # Check if we have a saved offset that we should respect
            saved_offset = settings.get('interface.repl_attach_offset', None)
            if isinstance(saved_offset, dict) and 'x' in saved_offset and 'y' in saved_offset:
                saved_x, saved_y = int(saved_offset['x']), int(saved_offset['y'])
                
                # If the saved offset indicates left-side positioning (negative x), preserve that
                if saved_x < 0:
                    logger.debug(f"🔗 Preserving left-side positioning from saved offset: ({saved_x}, {saved_y})")
                    # Calculate appropriate left-side offset based on current avatar width
                    gap = 10
                    default_x = -(self.floating_repl.width() if self.floating_repl else 520) - gap
                    default_y = saved_y  # Preserve Y offset
                    self._repl_attach_offset = QPoint(default_x, default_y)
                    logger.debug(f"🔗 Adjusted left-side offset: {self._repl_attach_offset}")
                    return
                else:
                    logger.debug(f"🔗 Using saved right-side offset: ({saved_x}, {saved_y})")
                    self._repl_attach_offset = QPoint(saved_x, saved_y)
                    return
            
            # Default: place REPL to the right of avatar with 10px gap
            gap = 10
            default_x = self.width() + gap
            default_y = 0
            self._repl_attach_offset = QPoint(default_x, default_y)
            logger.debug(f"🔗 Set default right-side offset: {self._repl_attach_offset} (avatar size: {self.width()}x{self.height()})")
            
        except Exception as e:
            logger.warning(f"Error calculating attach offset: {e}")
            self._repl_attach_offset = QPoint(140, 0)
            logger.debug(f"🔗 Fallback attach offset: {self._repl_attach_offset}")

    def _save_attach_offset(self):
        """Save the current attachment offset to settings."""
        try:
            settings.set('interface.repl_attach_offset', {
                'x': int(self._repl_attach_offset.x()),
                'y': int(self._repl_attach_offset.y()),
            })
            logger.debug(f"🔗 Saved attach offset: {self._repl_attach_offset}")
        except Exception as e:
            logger.error(f"Failed to save attach offset: {e}")

    def debug_attachment_state(self):
        """
        Comprehensive debugging method for attachment positioning issues.
        
        Call this method when debugging positioning problems to get detailed
        information about the current state.
        """
        try:
            logger.info("🔍 ===== ATTACHMENT DEBUG REPORT =====")
            
            # Basic state
            logger.info(f"🔍 Attached: {self._repl_attached}")
            logger.info(f"🔍 Current attach offset: {self._repl_attach_offset}")
            
            # Avatar state
            avatar_pos = self.pos()
            avatar_size = self.size()
            logger.info(f"🔍 Avatar position: {avatar_pos}")
            logger.info(f"🔍 Avatar size: {avatar_size}")
            
            # REPL state
            if self.floating_repl:
                repl_pos = self.floating_repl.pos()
                repl_size = self.floating_repl.size()
                repl_visible = self.floating_repl.isVisible()
                logger.info(f"🔍 REPL position: {repl_pos}")
                logger.info(f"🔍 REPL size: {repl_size}")
                logger.info(f"🔍 REPL visible: {repl_visible}")
                
                if repl_visible:
                    # Calculate current offset
                    current_offset = repl_pos - avatar_pos
                    logger.info(f"🔍 Current calculated offset: {current_offset}")
                    logger.info(f"🔍 Offset mismatch: {current_offset != self._repl_attach_offset}")
            
            # Screen info
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                logger.info(f"🔍 Screen geometry: {screen_geometry}")
            
            # Settings state
            saved_attach_state = settings.get('interface.repl_attached', None)
            saved_offset = settings.get('interface.repl_attach_offset', None)
            logger.info(f"🔍 Saved attach state: {saved_attach_state}")
            logger.info(f"🔍 Saved offset: {saved_offset}")
            
            # Window states
            try:
                from ..application.window_state import load_window_state
                avatar_state = load_window_state('avatar')
                repl_state = load_window_state('repl')
                logger.info(f"🔍 Avatar window state: {avatar_state}")
                logger.info(f"🔍 REPL window state: {repl_state}")
            except Exception as e:
                logger.warning(f"🔍 Could not load window states: {e}")
            
            logger.info("🔍 ===== END DEBUG REPORT =====")
            
        except Exception as e:
            logger.error(f"🔍 Error in debug_attachment_state: {e}")

    def _move_attached_repl(self):
        """Move REPL based on avatar position and stored offset, clamped to screen."""
        screen = self.screen()
        if not screen or not self.floating_repl:
            return
        geom = screen.availableGeometry()
        self.floating_repl.move_attached(self.pos(), self._repl_attach_offset, geom)

    def _on_repl_moved(self, repl_pos: QPoint):
        """When attached and user drags REPL, move avatar to maintain offset."""
        try:
            if self._repl_attached:
                # Calculate where avatar should be based on REPL position and offset
                new_avatar_pos = repl_pos - self._repl_attach_offset
                logger.debug(f"🔗 REPL moved to {repl_pos}, moving avatar to {new_avatar_pos}")
                self.move(new_avatar_pos)
                # Update the offset for consistency
                self._repl_attach_offset = repl_pos - new_avatar_pos
                settings.set('interface.repl_attach_offset', {
                    'x': int(self._repl_attach_offset.x()),
                    'y': int(self._repl_attach_offset.y()),
                })
        except Exception as e:
            logger.debug(f"Failed to move avatar on REPL move: {e}")
    
    def _validate_attached_repl_position(self, repl_x, repl_y, repl_size, screen_geometry, avatar_pos):
        """Enhanced validation for attached REPL positioning with left-side support."""
        try:
            # More lenient requirements - only need 80px width and 40px height visible
            min_visible_width = min(80, repl_size['width'] // 3)
            min_visible_height = min(40, repl_size['height'] // 5)
            
            # Calculate if enough of the window would be visible
            right_edge = repl_x + repl_size['width']
            bottom_edge = repl_y + repl_size['height']
            
            # Check visibility from each edge
            left_visible = right_edge >= screen_geometry.left() + min_visible_width
            right_visible = repl_x <= screen_geometry.right() - min_visible_width
            top_visible = bottom_edge >= screen_geometry.top() + min_visible_height
            bottom_visible = repl_y <= screen_geometry.bottom() - min_visible_height
            
            # Calculate the offset to understand positioning relative to avatar
            offset = QPoint(repl_x, repl_y) - avatar_pos
            is_left_side = offset.x() < 0
            
            # Log detailed validation info
            logger.debug(f"Validation for REPL at ({repl_x}, {repl_y}):")
            logger.debug(f"  Screen: {screen_geometry}")
            logger.debug(f"  Size: {repl_size['width']}x{repl_size['height']}")
            logger.debug(f"  Avatar: {avatar_pos}, Offset: {offset}, Left side: {is_left_side}")
            logger.debug(f"  Visibility: left={left_visible}, right={right_visible}, top={top_visible}, bottom={bottom_visible}")
            
            if left_visible and right_visible and top_visible and bottom_visible:
                return {'valid': True, 'reason': 'Position validated successfully'}
            else:
                failed_checks = []
                if not left_visible: failed_checks.append('left')
                if not right_visible: failed_checks.append('right')
                if not top_visible: failed_checks.append('top')
                if not bottom_visible: failed_checks.append('bottom')
                return {'valid': False, 'reason': f'Failed visibility checks: {", ".join(failed_checks)}'}
                
        except Exception as e:
            return {'valid': False, 'reason': f'Validation error: {e}'}
    
    def debug_attachment_state(self):
        """Comprehensive debugging of attachment state."""
        try:
            logger.debug("=== ATTACHMENT STATE DEBUG ===")
            logger.debug(f"Avatar position: {self.pos()}")
            logger.debug(f"Avatar size: {self.size()}")
            logger.debug(f"Attached: {self._repl_attached}")
            logger.debug(f"Current offset: {self._repl_attach_offset}")
            
            if self.floating_repl:
                logger.debug(f"REPL position: {self.floating_repl.pos()}")
                logger.debug(f"REPL size: {self.floating_repl.size()}")
                logger.debug(f"REPL visible: {self.floating_repl.isVisible()}")
            
            screen = self.screen()
            if screen:
                geom = screen.availableGeometry()
                logger.debug(f"Screen geometry: {geom}")
            
            # Check saved states
            try:
                from ..application.window_state import load_window_state
                avatar_state = load_window_state('avatar')
                repl_state = load_window_state('repl')
                logger.debug(f"Saved avatar state: {avatar_state}")
                logger.debug(f"Saved REPL state: {repl_state}")
            except Exception as e:
                logger.debug(f"Could not load saved states: {e}")
                
            # Check settings
            try:
                attached_setting = settings.get('interface.repl_attached', False)
                offset_setting = settings.get('interface.repl_attach_offset', None)
                logger.debug(f"Settings - attached: {attached_setting}, offset: {offset_setting}")
            except Exception as e:
                logger.debug(f"Could not load settings: {e}")
                
            logger.debug("=== END ATTACHMENT DEBUG ===")
        except Exception as e:
            logger.error(f"Debug failed: {e}")
    
    def _on_pin_toggle(self, always_on_top: bool):
        """Handle pin toggle from REPL - apply always on top setting."""
        try:
            logger.info(f"📌 Pin toggle received: always_on_top = {always_on_top}")
            
            # Save to settings (already done by REPL widget, but ensure consistency)
            settings.set('interface.always_on_top', always_on_top)
            
            # Apply the window flags immediately via app coordinator
            if hasattr(self.app_coordinator, '_update_window_flags'):
                self.app_coordinator._update_window_flags(always_on_top)
                logger.info(f"✓ Applied always on top setting: {always_on_top}")
            else:
                logger.warning("App coordinator doesn't have _update_window_flags method")
                
        except Exception as e:
            logger.error(f"Failed to handle pin toggle: {e}")
    
    def _get_themed_messagebox_style(self, button_color: str = None) -> str:
        """
        Build a QMessageBox stylesheet using current theme colors.

        Falls back to hardcoded dark-theme defaults when the theme manager
        is unavailable.

        Args:
            button_color: Semantic purpose of the primary button.
                          One of 'warning', 'success', 'error', or a raw
                          hex color string.  When *None*, ``status_warning``
                          is used.
        """
        # --- resolve theme colors (with safe fallbacks) ---
        bg = "#2b2b2b"
        fg = "#ffffff"
        border = "#555555"
        btn_bg = "#ff9800"
        btn_hover = "#f57c00"
        btn_pressed = None  # only emitted when a value exists

        try:
            from ...ui.themes.theme_manager import get_theme_manager
            tm = get_theme_manager()
            colors = tm.current_theme
            if colors is not None:
                from ...ui.themes.color_system import ColorSystem
                bg = colors.background_secondary
                fg = colors.text_primary
                border = colors.border_primary

                # Determine button background from semantic name or raw hex
                if button_color == "warning":
                    btn_bg = colors.status_warning
                elif button_color == "success":
                    btn_bg = colors.status_success
                elif button_color == "error":
                    btn_bg = colors.status_error
                elif button_color is not None:
                    btn_bg = button_color  # raw hex string passed in
                else:
                    btn_bg = colors.status_warning  # default

                # Derive hover / pressed shades
                btn_hover = ColorSystem.darken(btn_bg, 0.15)
                btn_pressed = ColorSystem.darken(btn_bg, 0.25)
        except Exception:
            pass  # fall through to hardcoded defaults

        # --- build stylesheet ---
        pressed_rule = ""
        if btn_pressed:
            pressed_rule = f"""
                    QMessageBox QPushButton:pressed {{
                        background-color: {btn_pressed};
                    }}"""

        return f"""
                    QMessageBox {{
                        background-color: {bg};
                        color: {fg};
                        border: 1px solid {border};
                    }}
                    QMessageBox QLabel {{
                        color: {fg};
                    }}
                    QMessageBox QPushButton {{
                        background-color: {btn_bg};
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        min-width: 80px;
                    }}
                    QMessageBox QPushButton:hover {{
                        background-color: {btn_hover};
                    }}{pressed_rule}
                """

    def _on_command_entered(self, command: str):
        """Handle command from REPL."""
        logger.info(f"REPL command: {command}")
        # This would be connected to AI service
    
    def _show_conversations(self):
        """Show the simple conversation management window."""
        try:
            from ..dialogs.simple_conversation_browser import SimpleConversationBrowser
            from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
            
            # Get conversation manager from REPL widget if available (to share same instance)
            conversation_manager = None
            current_conversation_id = None
            
            if (self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget') and
                self.floating_repl.repl_widget):
                # Get conversation manager from REPL widget
                if hasattr(self.floating_repl.repl_widget, 'conversation_manager'):
                    conversation_manager = self.floating_repl.repl_widget.conversation_manager
                    logger.info("Using shared conversation manager from REPL widget")
                # Get current conversation ID
                current_conversation_id = self.floating_repl.repl_widget.get_current_conversation_id()
            
            # If no conversation manager from REPL, create one
            if not conversation_manager:
                logger.info("Creating new conversation manager for browser")
                if not hasattr(self, '_conversation_manager') or not self._conversation_manager:
                    self._conversation_manager = ConversationManager()
                    if not self._conversation_manager.initialize():
                        logger.error("Failed to initialize conversation manager")
                        from PyQt6.QtWidgets import QMessageBox
                        
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Conversations Unavailable")
                        msg_box.setText("Conversation management system could not be initialized.")
                        msg_box.setIcon(QMessageBox.Icon.Warning)
                        msg_box.setStyleSheet(self._get_themed_messagebox_style("warning"))
                        msg_box.exec()
                        return
                conversation_manager = self._conversation_manager
            
            # Create or show conversation browser with shared conversation manager
            if not self.conversation_browser:
                # Get theme manager if available
                try:
                    from ...ui.themes.theme_manager import get_theme_manager
                    theme_manager = get_theme_manager()
                except ImportError:
                    theme_manager = None
                    
                self.conversation_browser = SimpleConversationBrowser(
                    parent=self, 
                    conversation_manager=conversation_manager,
                    theme_manager=theme_manager
                )
                self.conversation_browser.conversation_restore_requested.connect(
                    self._restore_conversation_to_repl
                )
            else:
                # Update current conversation and refresh the list
                self.conversation_browser.set_current_conversation(current_conversation_id)
                # Reload conversations to show any new ones
                self.conversation_browser._load_conversations()
            
            # Show the browser
            self.conversation_browser.show()
            self.conversation_browser.raise_()
            self.conversation_browser.activateWindow()
            
            logger.info("Simple conversation browser opened")
            
        except ImportError as e:
            logger.error(f"Conversation management not available: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Feature Unavailable")
            msg_box.setText("Conversation management is not yet available.")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStyleSheet(self._get_themed_messagebox_style("warning"))
            msg_box.exec()
        except Exception as e:
            logger.error(f"Failed to show conversations: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open conversations:\n{str(e)}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setStyleSheet(self._get_themed_messagebox_style("error"))
            msg_box.exec()
    
    
    def _restore_conversation_to_repl(self, conversation_id: str):
        """Restore a conversation to the REPL."""
        logger.info(f"Restoring conversation to REPL: {conversation_id}")
        
        try:
            # Show REPL if not visible
            if not self.floating_repl.isVisible():
                self._show_repl()
            
            # Load conversation in REPL widget
            if (self.floating_repl and 
                hasattr(self.floating_repl, 'repl_widget') and 
                self.floating_repl.repl_widget):
                
                # Restore the conversation in the REPL widget
                if hasattr(self.floating_repl.repl_widget, 'restore_conversation'):
                    self.floating_repl.repl_widget.restore_conversation(conversation_id)
                    logger.info(f"✓ Conversation {conversation_id} restoration initiated in REPL")
                else:
                    logger.error("✗ REPL widget doesn't have restore_conversation method")
                
                # Update conversation browser to reflect the change
                if self.conversation_browser:
                    self.conversation_browser.set_current_conversation(conversation_id)
                    # The browser will handle its own status update and refresh
                
                # Show success message with conversation details
                from PyQt6.QtWidgets import QMessageBox
                
                # Get conversation details for better message
                try:
                    conversation_manager = getattr(self.floating_repl.repl_widget, 'conversation_manager', None)
                    if conversation_manager:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            conversation = loop.run_until_complete(
                                conversation_manager.get_conversation(conversation_id, include_messages=False)
                            )
                            if conversation:
                                title = conversation.title or "Untitled Conversation"
                                message = f"Conversation '{title}' has been loaded into the REPL."
                            else:
                                message = "Conversation has been loaded into the REPL."
                        finally:
                            loop.close()
                    else:
                        message = "Conversation has been loaded into the REPL."
                except Exception as e:
                    logger.warning(f"Could not get conversation details for message: {e}")
                    message = "Conversation has been loaded into the REPL."
                
                # Create themed message box
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Conversation Restored")
                msg_box.setText(message)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStyleSheet(self._get_themed_messagebox_style("success"))
                msg_box.exec()
            else:
                logger.error("REPL widget not available for conversation restore")
                
        except Exception as e:
            logger.error(f"Failed to restore conversation: {e}")
            from PyQt6.QtWidgets import QMessageBox
            
            # Create themed error message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Restore Failed")
            msg_box.setText(f"Failed to restore conversation:\n{str(e)}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setStyleSheet(self._get_themed_messagebox_style("error"))
            msg_box.exec()