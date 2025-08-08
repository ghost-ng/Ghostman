"""Base overlay window class with common functionality."""

from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QMouseEvent
from typing import Tuple, Optional
import logging

class OverlayBaseWindow(QMainWindow):
    """Base class for overlay windows with common functionality."""
    
    # Signals
    position_changed = pyqtSignal(QPoint)
    focus_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Drag functionality
        self.dragging = False
        self.drag_position = QPoint()
        self.drag_start_time = 0
        self.click_threshold = 300  # ms to distinguish click from drag
        
        # Window refresh for Windows always-on-top workaround
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_always_on_top)
        
        self.setup_overlay_behavior()
        self.setup_drag_functionality()
        
        # Start refresh timer on Windows - less frequent to avoid layered window issues
        import sys
        if sys.platform == "win32":
            self.refresh_timer.start(30000)  # Every 30 seconds
    
    def setup_overlay_behavior(self):
        """Configure window for overlay behavior - ALWAYS ON TOP."""
        # CRITICAL FIX: Use simplified flags for maximum Windows compatibility
        flags = (
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool  # Tool window type for better overlay behavior
        )
        
        self.setWindowFlags(flags)
        
        # CRITICAL FIX: Do NOT use WA_TranslucentBackground - it makes windows invisible
        # Only enable if specifically needed by subclass
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Ensure window can be activated and shown
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)  # Prevent premature deletion
        
        # Full opacity for maximum visibility - set BEFORE any show() calls
        self.setWindowOpacity(1.0)
        
        # Normal window state for visibility
        self.setWindowState(Qt.WindowState.WindowNoState)
        
        # WINDOWS SPECIFIC: Force window to be painted
        import sys
        if sys.platform == "win32":
            self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, True)
            self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        
        self.logger.info("Overlay behavior configured - always on top, no translucent background")
    
    def setup_drag_functionality(self):
        """Enable window dragging."""
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            self.drag_start_time = event.timestamp()
            event.accept()
            self.logger.debug("Drag started")
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.position_changed.emit(new_pos)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self.dragging
            drag_duration = event.timestamp() - self.drag_start_time if hasattr(self, 'drag_start_time') else 0
            
            self.dragging = False
            event.accept()
            
            # Determine if this was a click or drag
            if not was_dragging or drag_duration < self.click_threshold:
                # This might be a click - let subclasses handle it
                pass
            
            self.logger.debug("Drag ended")
        super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effects."""
        self.setWindowOpacity(1.0)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effects."""
        self.setWindowOpacity(1.0)  # Keep full opacity for visibility
        super().leaveEvent(event)
    
    def refresh_always_on_top(self):
        """Refresh always-on-top status (Windows workaround)."""
        try:
            if self.isVisible() and not self.dragging:
                # Very conservative approach - just raise without activating
                self.raise_()
                self.logger.debug("Refreshed always-on-top status")
        except Exception as e:
            self.logger.warning(f"Error refreshing always-on-top: {e}")
    
    def ensure_on_screen(self):
        """Ensure window is visible on screen."""
        from PyQt6.QtWidgets import QApplication
        
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        
        # Check if window is off-screen
        if not screen_geometry.intersects(window_geometry):
            # Move to center of screen
            center_x = (screen_geometry.width() - window_geometry.width()) // 2
            center_y = (screen_geometry.height() - window_geometry.height()) // 2
            self.move(center_x, center_y)
            self.logger.info("Window moved back to screen")
    
    def set_opacity(self, opacity: float):
        """Set window opacity with validation."""
        opacity = max(0.1, min(1.0, opacity))
        self.setWindowOpacity(opacity)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop refresh timer
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        self.logger.debug("Overlay window closing")
        super().closeEvent(event)