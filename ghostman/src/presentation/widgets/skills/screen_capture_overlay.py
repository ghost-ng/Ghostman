"""
Screen Capture Overlay - Full-screen overlay for selecting capture regions.

Provides a translucent full-screen overlay with mouse interaction for selecting
regions to capture using different shapes (rectangle, circle, freeform).
"""

import logging
from typing import Optional, List
from io import BytesIO

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QCursor, QPixmap, QImage,
    QPainterPath, QPolygon
)

from ....infrastructure.skills.interfaces.screen_capture_skill import (
    CaptureShape, CaptureResult
)

logger = logging.getLogger("ghostman.ui.screen_capture_overlay")


class ScreenCaptureOverlay(QWidget):
    """
    Full-screen translucent overlay for screen capture region selection.

    Displays a semi-transparent overlay that allows users to select a region
    using mouse drag. Supports different shapes (rectangle, circle, freeform)
    and renders selection borders in real-time.

    Signals:
        capture_completed: Emitted when user confirms capture (CaptureResult)
        capture_cancelled: Emitted when user cancels (ESC key)
    """

    capture_completed = pyqtSignal(CaptureResult)
    capture_cancelled = pyqtSignal()

    def __init__(
        self,
        shape: CaptureShape = CaptureShape.RECTANGLE,
        border_width: int = 2,
        border_color: str = "#FF0000",
        parent: Optional[QWidget] = None
    ):
        """
        Initialize screen capture overlay.

        Args:
            shape: Capture shape type
            border_width: Selection border width in pixels
            border_color: Selection border color (hex format)
            parent: Parent widget (usually None for full-screen)
        """
        super().__init__(parent)

        self.shape = shape
        self.border_width = border_width
        self.border_color = QColor(border_color)

        # Selection state
        self.start_point: Optional[QPoint] = None
        self.current_point: Optional[QPoint] = None
        self.freeform_points: List[QPoint] = []
        self.is_selecting = False

        # Setup widget
        self._setup_ui()

        # Capture full screen before showing overlay
        self._capture_screen()

    def _setup_ui(self):
        """Setup overlay UI properties."""
        # Make window frameless and stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Set window to full screen
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        # Set semi-transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Enable mouse tracking for freeform mode
        self.setMouseTracking(True)

        # Set crosshair cursor
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _capture_screen(self):
        """Capture full screen before showing overlay."""
        screen = QApplication.primaryScreen()
        if screen:
            self.screen_pixmap = screen.grabWindow(0)
        else:
            self.screen_pixmap = None

    def paintEvent(self, event):
        """Paint the overlay with selection region."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill with semi-transparent black
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw selection region if active
        if self.start_point and self.current_point:
            self._draw_selection(painter)

        # Draw instructions
        self._draw_instructions(painter)

    def _draw_selection(self, painter: QPainter):
        """Draw the current selection region."""
        if self.shape == CaptureShape.RECTANGLE:
            self._draw_rectangle_selection(painter)
        elif self.shape == CaptureShape.CIRCLE:
            self._draw_circle_selection(painter)
        elif self.shape == CaptureShape.FREEFORM:
            self._draw_freeform_selection(painter)

    def _draw_rectangle_selection(self, painter: QPainter):
        """Draw rectangle selection."""
        rect = QRect(self.start_point, self.current_point).normalized()

        # Clear selection area (show captured screen)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(rect, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Draw border
        pen = QPen(self.border_color, self.border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        # Draw size label
        self._draw_size_label(painter, rect)

    def _draw_circle_selection(self, painter: QPainter):
        """Draw circle selection."""
        rect = QRect(self.start_point, self.current_point).normalized()

        # Clear selection area (show captured screen)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(rect, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Draw border
        pen = QPen(self.border_color, self.border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        # Draw size label
        self._draw_size_label(painter, rect)

    def _draw_freeform_selection(self, painter: QPainter):
        """Draw freeform selection."""
        if len(self.freeform_points) < 2:
            return

        # Create path from points
        path = QPainterPath()
        path.moveTo(self.freeform_points[0])
        for point in self.freeform_points[1:]:
            path.lineTo(point)

        # If selecting, add current point
        if self.is_selecting and self.current_point:
            path.lineTo(self.current_point)
        else:
            # Close path when done
            path.closeSubpath()

        # Clear selection area
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillPath(path, QBrush(Qt.GlobalColor.transparent))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Draw border
        pen = QPen(self.border_color, self.border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _draw_size_label(self, painter: QPainter, rect: QRect):
        """Draw size label for selection."""
        label = f"{rect.width()} x {rect.height()}"

        # Draw label background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))

        label_rect = painter.fontMetrics().boundingRect(label)
        label_rect.adjust(-5, -2, 5, 2)
        label_rect.moveTopLeft(QPoint(rect.left(), rect.top() - label_rect.height() - 5))

        painter.drawRect(label_rect)

        # Draw label text
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_instructions(self, painter: QPainter):
        """Draw instruction text."""
        instructions = "Drag to select region • ENTER to confirm • ESC to cancel"

        # Position at top center
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))

        text_rect = painter.fontMetrics().boundingRect(instructions)
        text_rect.adjust(-10, -5, 10, 5)
        text_rect.moveCenter(QPoint(self.width() // 2, 30))

        painter.drawRect(text_rect)

        # Draw text
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, instructions)

    def mousePressEvent(self, event):
        """Handle mouse press - start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.current_point = event.pos()
            self.is_selecting = True

            if self.shape == CaptureShape.FREEFORM:
                self.freeform_points = [event.pos()]

            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move - update selection."""
        if self.is_selecting:
            self.current_point = event.pos()

            if self.shape == CaptureShape.FREEFORM:
                self.freeform_points.append(event.pos())

            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - end selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
            self.current_point = event.pos()
            self.update()

    def keyPressEvent(self, event):
        """Handle key press - confirm or cancel."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._confirm_capture()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel_capture()

    def _confirm_capture(self):
        """Confirm capture and emit result."""
        if not self.start_point or not self.current_point:
            self._cancel_capture()
            return

        try:
            # Calculate capture region
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()

            if rect.width() < 5 or rect.height() < 5:
                logger.warning("Selection too small")
                self._cancel_capture()
                return

            # Capture region from screen pixmap
            if self.screen_pixmap:
                captured_pixmap = self.screen_pixmap.copy(rect)

                # Convert to bytes
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                captured_pixmap.save(buffer, "PNG")
                image_data = BytesIO(buffer.data().data())

                # Create result
                result = CaptureResult(
                    shape=self.shape,
                    x=rect.x(),
                    y=rect.y(),
                    width=rect.width(),
                    height=rect.height(),
                    image_data=image_data
                )

                logger.info(f"✓ Screen capture completed: {rect.width()}x{rect.height()}")
                self.capture_completed.emit(result)
                self.close()
            else:
                logger.error("No screen pixmap available")
                self._cancel_capture()

        except Exception as e:
            logger.error(f"Failed to capture screen region: {e}", exc_info=True)
            self._cancel_capture()

    def _get_freeform_bounding_rect(self) -> QRect:
        """Get bounding rectangle for freeform selection."""
        if not self.freeform_points:
            return QRect()

        min_x = min(p.x() for p in self.freeform_points)
        max_x = max(p.x() for p in self.freeform_points)
        min_y = min(p.y() for p in self.freeform_points)
        max_y = max(p.y() for p in self.freeform_points)

        return QRect(QPoint(min_x, min_y), QPoint(max_x, max_y))

    def _cancel_capture(self):
        """Cancel capture and emit signal."""
        logger.info("Screen capture cancelled")
        self.capture_cancelled.emit()
        self.close()
