"""
Avatar Widget for Ghostman.

Displays the animated avatar as the main interface.
"""

import logging
import os
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QMenu
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPaintEvent, QMouseEvent, QAction

logger = logging.getLogger("ghostman.avatar_widget")


class AvatarWidget(QWidget):
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.avatar_pixmap: Optional[QPixmap] = None
        self.scaled_pixmap: Optional[QPixmap] = None
        self.animation: Optional[QPropertyAnimation] = None
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.mouse_press_pos = QPoint()
        
        self._init_ui()
        self._load_avatar()
        self._setup_animation()
        
        logger.info("AvatarWidget initialized")
    
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
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.window().pos()
            self.mouse_press_pos = event.position()
            # Don't emit click immediately - wait for release to distinguish click from drag
            logger.debug(f"Mouse pressed at {event.position()}, window pos: {self.window().pos()}")
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for dragging."""
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # Move the parent window
            if self.window():
                new_pos = event.globalPosition().toPoint() - self.drag_start_pos
                self.window().move(new_pos)
                logger.debug(f"Dragging window to position: {new_pos}")
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            
            # Check if this was a click (minimal movement) rather than a drag
            distance = (event.position() - self.mouse_press_pos).manhattanLength()
            logger.debug(f"Mouse released, distance moved: {distance}px")
            
            if distance < 5:  # Less than 5 pixels = click
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
    
    def _show_context_menu(self, pos: QPoint):
        """Show context menu on right-click."""
        context_menu = QMenu(self)
        
        # Add actions
        minimize_action = QAction("Minimize to Tray", self)
        minimize_action.triggered.connect(self.minimize_requested.emit)
        context_menu.addAction(minimize_action)
        
        context_menu.addSeparator()
        
        about_action = QAction("About Spector", self)
        about_action.triggered.connect(lambda: logger.info("About Spector clicked"))
        context_menu.addAction(about_action)
        
        # Show the menu
        context_menu.exec(pos)
        logger.debug("Context menu shown")