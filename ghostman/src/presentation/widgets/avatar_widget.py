"""
Avatar Widget for Ghostman.

Displays the animated avatar as the main interface.
"""

import logging
import os
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPaintEvent, QMouseEvent

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
        self.hover_offset = 0
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        
        self._init_ui()
        self._load_avatar()
        self._setup_animation()
        
        logger.info("AvatarWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set widget properties
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        logger.debug("Avatar UI initialized")
    
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
            size = min(self.width(), self.height())
            if size > 0:
                self.scaled_pixmap = self.avatar_pixmap.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
    
    def _setup_animation(self):
        """Setup floating animation for the avatar."""
        # Create animation for floating effect
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(3000)  # 3 seconds
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1)  # Infinite loop
        
        # Setup animation timer for subtle movement
        self.float_timer = QTimer()
        self.float_timer.timeout.connect(self._update_float_animation)
        self.float_timer.start(50)  # Update every 50ms
        
        self.float_phase = 0
    
    def _update_float_animation(self):
        """Update the floating animation position."""
        import math
        self.float_phase += 0.05
        self.hover_offset = int(math.sin(self.float_phase) * 5)  # Float up and down by 5 pixels
        self.update()  # Trigger repaint
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the avatar."""
        if not self.scaled_pixmap:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate position to center the avatar
        x = (self.width() - self.scaled_pixmap.width()) // 2
        y = (self.height() - self.scaled_pixmap.height()) // 2 + self.hover_offset
        
        # Draw shadow effect
        shadow_offset = 10
        painter.setOpacity(0.3)
        painter.drawPixmap(x + shadow_offset, y + shadow_offset, self.scaled_pixmap)
        
        # Draw the avatar
        painter.setOpacity(1.0)
        painter.drawPixmap(x, y, self.scaled_pixmap)
        
        painter.end()
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.window().pos()
            self.avatar_clicked.emit()
            logger.debug("Avatar clicked")
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for dragging."""
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # Move the parent window
            if self.window():
                self.window().move(event.globalPosition().toPoint() - self.drag_start_pos)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.minimize_requested.emit()
            logger.debug("Avatar double-clicked - minimize requested")