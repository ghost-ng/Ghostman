"""
Avatar Widget for Ghostman.

Displays the animated avatar as the main interface.
"""

import logging
import os
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QMenu
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPaintEvent, QMouseEvent, QAction, QIcon

try:
    from ..ui.resize import AvatarResizableMixin, HitZone
    from ..ui.resize.simple_arrow_mixin import SimpleAvatarArrowMixin
    SIMPLE_ARROW_RESIZE_AVAILABLE = True
    ARROW_RESIZE_AVAILABLE = False  # Disable complex system
except ImportError:
    # Fallback if resize system is not available
    class AvatarResizableMixin:
        def __init_avatar_resize__(self, *args, **kwargs): pass
        def enable_resize(self): pass
        def disable_resize(self): pass
        def cleanup_resize(self): pass
    
    class SimpleAvatarArrowMixin:
        def __init_simple_avatar_arrows__(self, *args, **kwargs): pass
        def enable_simple_arrow_resize(self): pass
        def disable_simple_arrow_resize(self): pass
        def cleanup_simple_arrow_resize(self): pass
        def show_resize_arrows(self, auto_hide=None): pass
    
    HitZone = None
    SIMPLE_ARROW_RESIZE_AVAILABLE = False
    ARROW_RESIZE_AVAILABLE = False

logger = logging.getLogger("ghostman.avatar_widget")


class AvatarWidget(SimpleAvatarArrowMixin, AvatarResizableMixin, QWidget):
    """
    Widget that displays the avatar as the main interface.
    
    Features:
    - Displays the avatar image
    - Floating animation effect
    - Click interaction
    - Draggable around the screen
    """
    
    # Signals
    avatar_clicked = pyqtSignal()
    minimize_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    conversations_requested = pyqtSignal()
    help_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    # Resize signals (from mixin)
    resize_started = pyqtSignal(object)  # HitZone
    resize_updated = pyqtSignal(object, int, int)  # HitZone, width, height
    resize_finished = pyqtSignal(object, int, int)  # HitZone, width, height
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.avatar_pixmap: Optional[QPixmap] = None
        self.scaled_pixmap: Optional[QPixmap] = None
        self.animation: Optional[QPropertyAnimation] = None
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.mouse_press_pos = QPoint()
        self.window_moved_during_drag = False
        
        # Initialize resize functionality - use simple arrow system
        self._use_simple_arrows = True
        try:
            if SIMPLE_ARROW_RESIZE_AVAILABLE and self._use_simple_arrows:
                self.__init_simple_avatar_arrows__()
                logger.debug("Initialized simple arrow resize for avatar")
            else:
                self.__init_avatar_resize__()
                logger.debug("Initialized traditional resize for avatar")
        except Exception as e:
            logger.warning(f"Failed to initialize resize functionality: {e}")
            # Fallback to traditional resize
            try:
                self.__init_avatar_resize__()
                self._use_simple_arrows = False
                logger.debug("Falling back to traditional resize")
            except Exception as e2:
                logger.error(f"Failed to initialize any resize system: {e2}")
        
        self._init_ui()
        self._load_avatar()
        self._setup_animation()
        
        # Direct arrow resize implementation (bypassing mixin complexity)
        self._setup_direct_arrows()
        
        logger.info("AvatarWidget initialized")
    
    def _setup_direct_arrows(self):
        """Setup direct arrow resize functionality (bypassing mixin complexity)."""
        try:
            from ..ui.resize.grip_resize import GripResizeManager
            from ..ui.resize.constraints import SizeConstraints
            
            # Create avatar constraints (80x80 to 200x200, square aspect ratio)
            constraints = SizeConstraints(
                min_width=80, min_height=80,
                max_width=200, max_height=200,
                maintain_aspect_ratio=True
            )
            
            # Create edge grip manager (no full overlay, just small grips)
            self._direct_arrow_manager = GripResizeManager(self, constraints)
            self._direct_arrows_enabled = False
            
            logger.debug("Direct arrow resize setup complete for avatar")
            
        except Exception as e:
            logger.warning(f"Failed to setup direct arrows for avatar: {e}")
            self._direct_arrow_manager = None
            self._direct_arrows_enabled = False
    
    def show_resize_arrows(self, auto_hide: bool = True):
        """Show resize arrows directly."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrow_manager.show_arrows(auto_hide=auto_hide)
            logger.debug(f"Avatar direct arrows shown (auto_hide={auto_hide})")
        else:
            logger.warning("Direct arrow manager not available for avatar")
    
    def hide_resize_arrows(self):
        """Hide resize arrows directly."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrow_manager.hide_arrows()
            logger.debug("Avatar direct arrows hidden")
    
    def enable_direct_arrows(self, enabled: bool = True):
        """Enable/disable direct arrow functionality."""
        if hasattr(self, '_direct_arrow_manager') and self._direct_arrow_manager:
            self._direct_arrows_enabled = enabled
            if enabled:
                logger.debug("Avatar direct arrows enabled")
            else:
                self.hide_resize_arrows()
                logger.debug("Avatar direct arrows disabled")
        else:
            logger.warning("Direct arrow manager not available for avatar")

    def enable_avatar_resize(self, enabled: bool = True):
        """Enable or disable resize functionality for the avatar."""
        try:
            # Use direct arrow approach that works
            self.enable_direct_arrows(enabled)
        except Exception as e:
            logger.warning(f"Failed to toggle avatar resize: {e}")
    
    def toggle_resize_system(self, use_simple_arrows: bool = None):
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
                self.init_avatar_simple_arrows()
                self.enable_simple_arrow_resize()
                logger.info("Switched avatar to simple arrow resize")
            else:
                self.__init_avatar_resize__()
                self.enable_resize()
                self._use_simple_arrows = False
                logger.info("Switched avatar to traditional resize")
                
        except Exception as e:
            logger.error(f"Failed to toggle resize system: {e}")
    
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set widget properties
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(120, 120)  # Match the window size
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        logger.debug(f"Avatar UI initialized with size: {self.size()}")
    
    def _load_avatar(self):
        """Load the avatar image."""
        avatar_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "assets", "avatar.png"
        )
        
        if os.path.exists(avatar_path):
            self.avatar_pixmap = QPixmap(avatar_path)
            if not self.avatar_pixmap.isNull():
                logger.info(f"Avatar loaded from: {avatar_path}")
                self._update_scaled_pixmap()
            else:
                logger.error(f"Failed to load avatar from: {avatar_path}")
                self._create_fallback_avatar()
        else:
            logger.warning(f"Avatar not found at: {avatar_path}")
            self._create_fallback_avatar()
    
    def _create_fallback_avatar(self):
        """Create a fallback avatar if the image can't be loaded."""
        # Create a simple colored circle as fallback
        size = 200
        self.avatar_pixmap = QPixmap(size, size)
        self.avatar_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(self.avatar_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.lightGray)
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawEllipse(10, 10, size-20, size-20)
        
        # Draw a simple face
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawEllipse(60, 70, 20, 20)  # Left eye
        painter.drawEllipse(120, 70, 20, 20)  # Right eye
        painter.drawArc(60, 100, 80, 40, 0, -180 * 16)  # Smile
        
        painter.end()
        logger.info("Fallback avatar created")
        self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        """Update the scaled pixmap based on widget size."""
        if self.avatar_pixmap and not self.avatar_pixmap.isNull():
            # Scale to fit widget while maintaining aspect ratio
            # Leave some padding
            padding = 10
            size = min(self.width(), self.height()) - padding
            if size > 0:
                self.scaled_pixmap = self.avatar_pixmap.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logger.debug(f"Scaled pixmap to size: {size}x{size}, widget size: {self.width()}x{self.height()}")
    
    def _setup_animation(self):
        """Setup animation (disabled for now)."""
        # Animation removed per request
        pass
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the avatar."""
        if not self.scaled_pixmap:
            logger.warning("No scaled pixmap available for painting")
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Get the actual widget rect
        widget_rect = self.rect()
        logger.debug(f"Painting avatar in rect: {widget_rect}, scaled pixmap size: {self.scaled_pixmap.size()}")
        
        # Calculate position to center the avatar
        x = (widget_rect.width() - self.scaled_pixmap.width()) // 2
        y = (widget_rect.height() - self.scaled_pixmap.height()) // 2
        
        # Ensure we're not drawing outside the widget
        x = max(0, x)
        y = max(0, y)
        
        # Skip shadow for now to avoid clipping issues
        # Draw the avatar
        painter.setOpacity(1.0)
        painter.drawPixmap(x, y, self.scaled_pixmap)
        
        painter.end()
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        logger.debug(f"Avatar widget resized from {event.oldSize()} to {event.size()}")
        self._update_scaled_pixmap()
        self.update()  # Force repaint
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we're in a resize zone
            is_in_resize_zone = False
            
            if self._use_simple_arrows:
                # For simple arrow system, check if currently resizing (arrows handle their own events)
                try:
                    if hasattr(self, 'is_simple_arrow_resize_enabled'):
                        # Simple arrows handle their own mouse events, so no conflict with dragging
                        is_in_resize_zone = False  # Let normal drag behavior work
                except Exception as e:
                    logger.debug(f"Error checking simple arrow resize state: {e}")
            else:
                # For traditional system, check hit zones
                try:
                    if hasattr(self, 'get_resize_status'):
                        status = self.get_resize_status()
                        # Check if we're hovering over a resize zone
                        if hasattr(self, '_resize_manager') and self._resize_manager:
                            zone = self._resize_manager.get_hit_zone(event.position().toPoint())
                            is_in_resize_zone = (zone and hasattr(zone, 'value') and zone.value != 'none')
                except Exception as e:
                    logger.debug(f"Error checking resize zone: {e}")
            
            if not is_in_resize_zone:
                # Normal drag behavior
                self.is_dragging = True
                self.window_moved_during_drag = False
                self.drag_start_pos = event.globalPosition().toPoint() - self.window().pos()
                self.mouse_press_pos = event.position()
                logger.debug(f"Mouse pressed for drag at {event.position()}, window pos: {self.window().pos()}")
            else:
                # Let resize handle this
                self.is_dragging = False
                self.window_moved_during_drag = False
                logger.debug(f"Mouse pressed in resize zone at {event.position()}")
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for dragging."""
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # Move the parent window
            if self.window():
                new_pos = event.globalPosition().toPoint() - self.drag_start_pos
                self.window().move(new_pos)
                self.window_moved_during_drag = True
                logger.debug(f"Dragging window to position: {new_pos}")
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self.is_dragging
            window_moved = self.window_moved_during_drag
            self.is_dragging = False
            self.window_moved_during_drag = False
            
            # Only emit avatar_clicked if no actual window movement occurred
            # Check both mouse movement distance AND whether window actually moved
            distance = (event.position() - self.mouse_press_pos).manhattanLength()
            logger.debug(f"Mouse released, distance moved: {distance}px, window moved during drag: {window_moved}")
            
            if not window_moved and distance < 10:  # No window movement AND minimal mouse movement = click
                logger.debug('Detected click (not drag) - emitting avatar_clicked')
                self.avatar_clicked.emit()
            else:
                logger.debug('Detected drag (not click) - no REPL toggle')
            
            logger.debug(f"Mouse released, final window position: {self.window().pos()}")
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Double-click now just triggers avatar click
            self.avatar_clicked.emit()
            logger.debug("Avatar double-clicked")
    
    def _get_theme_icon(self, icon_name: str) -> QIcon:
        """Get dark icon for avatar menu (menus are always lite background)."""
        try:
            from ...utils.resource_resolver import resolve_icon
            icon_path = resolve_icon(icon_name, "_dark")
            if icon_path:
                return QIcon(str(icon_path))
        except Exception as e:
            logger.debug(f"Failed to load icon {icon_name}_dark.png: {e}")
        
        return QIcon()  # Empty icon as fallback
    
    def _show_context_menu(self, pos: QPoint):
        """Show context menu on right-click."""
        logger.debug(f"Avatar right-click detected at position: {pos}")
        context_menu = QMenu(self)
        
        # Conversations action - primary feature
        conversations_action = QAction(self._get_theme_icon("chat"), "Conversations", self)
        conversations_action.triggered.connect(self._on_conversations_clicked)
        context_menu.addAction(conversations_action)
        logger.debug("Added 'Conversations' option to context menu")
        
        context_menu.addSeparator()
        
        # Settings action
        settings_action = QAction(self._get_theme_icon("gear"), "Settings...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        context_menu.addAction(settings_action)
        
        # Help documentation action
        help_action = QAction("Help Documentation", self)
        help_action.triggered.connect(self._on_help_clicked)
        context_menu.addAction(help_action)
        
        context_menu.addSeparator()
        
        # Add actions
        minimize_action = QAction(self._get_theme_icon("minimize"), "Minimize to Tray", self)
        minimize_action.triggered.connect(self.minimize_requested.emit)
        context_menu.addAction(minimize_action)
        
        context_menu.addSeparator()
        
        # Quit action
        quit_action = QAction(self._get_theme_icon("exit"), "Quit Ghostman", self)
        quit_action.triggered.connect(self._on_quit_clicked)
        context_menu.addAction(quit_action)
        
        # Apply theme-aware menu styling
        self._style_menu(context_menu)
        
        # Show the menu
        logger.debug("Showing avatar context menu...")
        context_menu.exec(pos)
        logger.debug("Context menu closed")
    
    def _style_menu(self, menu):
        """Apply theme-aware styling to QMenu widgets."""
        try:
            # Try to get theme manager from parent or globally
            theme_manager = None
            
            # Try to get from parent first
            parent = self.parent()
            while parent and not theme_manager:
                theme_manager = getattr(parent, 'theme_manager', None)
                parent = parent.parent()
            
            # Try to get from the global theme manager
            if not theme_manager:
                try:
                    from ghostman.src.ui.themes.theme_manager import get_theme_manager
                    theme_manager = get_theme_manager()
                except (ImportError, AttributeError):
                    return
            
            if not theme_manager:
                return
                
            try:
                from ghostman.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                if not THEME_SYSTEM_AVAILABLE:
                    return
            except ImportError:
                return
            
            colors = theme_manager.current_theme
            if colors:
                from ghostman.src.ui.themes.style_templates import StyleTemplates
                menu_style = StyleTemplates.get_menu_style(colors)
                menu.setStyleSheet(menu_style)
                
        except Exception as e:
            # Silently handle errors to avoid breaking functionality
            pass
    
    def _on_conversations_clicked(self):
        """Handle conversations menu item clicked."""
        logger.info("🗨️ Conversations menu item clicked by user")
        logger.debug("Emitting conversations_requested signal...")
        self.conversations_requested.emit()
        logger.debug("conversations_requested signal emitted")
    
    def _on_help_clicked(self):
        """Handle help documentation menu item clicked."""
        import os
        import webbrowser
        try:
            logger.info("📖 Help documentation menu item clicked by user")
            # Get the help file path
            current_dir = os.path.dirname(__file__)
            # Go up from widgets to presentation, then to src, then stay in ghostman, then to assets
            ghostman_src_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            help_file = os.path.join(ghostman_src_root, 'assets', 'help', 'index.html')
            help_url = f'file:///{help_file.replace(os.sep, "/")}'
            webbrowser.open(help_url)
            logger.info(f"📖 Opened help documentation: {help_url}")
        except Exception as e:
            logger.error(f"Failed to open help documentation: {e}")
    
    def _on_quit_clicked(self):
        """Handle quit menu item clicked."""
        logger.info("🚪 Quit Ghostman clicked by user")
        logger.debug("Emitting quit_requested signal...")
        self.quit_requested.emit()
        logger.debug("quit_requested signal emitted")
    
    def closeEvent(self, event):
        """Handle widget close event."""
        try:
            if self._use_simple_arrows:
                self.cleanup_simple_arrow_resize()
            else:
                self.cleanup_resize()
        except Exception as e:
            logger.debug(f"Error during resize cleanup: {e}")
        super().closeEvent(event)
    
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