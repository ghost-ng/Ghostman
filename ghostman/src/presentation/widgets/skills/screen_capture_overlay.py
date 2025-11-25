"""
Screen Capture Overlay - Full-screen overlay for selecting capture regions.

Provides a full-screen overlay showing the captured screen with a control panel
for selecting shapes and configuring borders.
"""

import logging
from typing import Optional, List
from io import BytesIO

from PyQt6.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QRect, QPoint, QPointF, pyqtSignal, QBuffer, QIODevice, QSize
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
    Full-screen overlay for screen capture with control panel.

    Shows the captured screen with semi-transparent dimming. User can select
    shape, configure border, and drag to select region.

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
            shape: Initial capture shape type
            border_width: Selection border width in pixels
            border_color: Selection border color (hex format)
            parent: Parent widget (usually None for full-screen)
        """
        super().__init__(parent)

        self.shape = shape
        self.border_width = border_width
        self.border_color = QColor(border_color)
        self.show_border = border_width > 0

        # Selection state
        self.start_point: Optional[QPoint] = None
        self.current_point: Optional[QPoint] = None
        self.freeform_points: List[QPoint] = []
        self.is_selecting = False
        self.selection_complete = False
        self.captured_image: Optional[QPixmap] = None

        # Capture screen BEFORE showing overlay
        self._capture_screen()

        # Setup UI
        self._setup_ui()
        self._create_control_panel()

    def _setup_ui(self):
        """Setup overlay UI properties."""
        # Make window frameless and stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Get screen geometry to cover ALL monitors
        screen = QApplication.primaryScreen()
        if screen:
            # Use virtual geometry to span all screens
            geometry = screen.virtualGeometry()
            self.setGeometry(geometry)
        else:
            # Fallback to full screen state
            self.setWindowState(Qt.WindowState.WindowFullScreen)

        # Enable mouse tracking for freeform mode
        self.setMouseTracking(True)

        # Set crosshair cursor
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _capture_screen(self):
        """Capture full screen (all monitors) before showing overlay."""
        screen = QApplication.primaryScreen()
        if screen:
            # Capture virtual screen (all monitors)
            virtual_geometry = screen.virtualGeometry()
            self.screen_pixmap = screen.grabWindow(
                0,
                virtual_geometry.x(),
                virtual_geometry.y(),
                virtual_geometry.width(),
                virtual_geometry.height()
            )
            logger.debug(f"Captured screen: {self.screen_pixmap.width()}x{self.screen_pixmap.height()}")
        else:
            self.screen_pixmap = None
            logger.error("Failed to capture screen")

    def _create_control_panel(self):
        """Create floating control panel for shape and border selection."""
        # Control panel frame
        self.control_panel = QFrame(self)
        self.control_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 230);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: rgba(70, 70, 70, 255);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(90, 90, 90, 255);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 50, 255);
            }
            QPushButton#selected {
                background-color: rgba(0, 120, 215, 255);
            }
            QComboBox {
                background-color: rgba(70, 70, 70, 255);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid white;
            }
            QCheckBox {
                color: white;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self.control_panel)
        layout.setSpacing(8)

        # Title
        title = QLabel("Screen Capture")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Shape selection
        shape_layout = QHBoxLayout()
        shape_label = QLabel("Shape:")
        shape_layout.addWidget(shape_label)

        self.shape_buttons = {}
        shapes = [
            ("Rectangle", CaptureShape.RECTANGLE, "▭"),
            ("Square", CaptureShape.RECTANGLE, "□"),  # Will force 1:1 ratio
            ("Circle", CaptureShape.CIRCLE, "○"),
            ("Freeform", CaptureShape.FREEFORM, "✎")
        ]

        for name, shape_type, icon in shapes:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setChecked(shape_type == self.shape and name == "Rectangle")
            btn.clicked.connect(lambda checked, n=name, s=shape_type: self._on_shape_changed(n, s))
            self.shape_buttons[name] = btn
            shape_layout.addWidget(btn)

        layout.addLayout(shape_layout)

        # Border options
        border_layout = QHBoxLayout()

        self.border_checkbox = QCheckBox("Show Border")
        self.border_checkbox.setChecked(self.show_border)
        self.border_checkbox.stateChanged.connect(self._on_border_toggle)
        border_layout.addWidget(self.border_checkbox)

        border_layout.addWidget(QLabel("Color:"))
        self.border_color_combo = QComboBox()
        self.border_color_combo.addItems(["Red", "Blue", "Green", "Yellow", "White", "Black"])
        self.border_color_combo.currentTextChanged.connect(self._on_border_color_changed)
        border_layout.addWidget(self.border_color_combo)

        layout.addLayout(border_layout)

        # Action buttons (Save and Copy) - initially hidden
        action_layout = QHBoxLayout()

        self.save_button = QPushButton("💾 Save")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setVisible(False)
        action_layout.addWidget(self.save_button)

        self.copy_button = QPushButton("📋 Copy")
        self.copy_button.clicked.connect(self._on_copy_clicked)
        self.copy_button.setVisible(False)
        action_layout.addWidget(self.copy_button)

        self.done_button = QPushButton("✓ Done")
        self.done_button.clicked.connect(self._on_done_clicked)
        self.done_button.setVisible(False)
        action_layout.addWidget(self.done_button)

        layout.addLayout(action_layout)

        # Instructions
        self.instructions = QLabel("Drag to select region • ENTER to confirm • ESC to cancel")
        self.instructions.setStyleSheet("font-size: 10px; color: #CCCCCC; padding-top: 5px;")
        layout.addWidget(self.instructions)

        # Position control panel at top center
        self.control_panel.adjustSize()
        screen_width = self.screen().geometry().width()
        panel_width = self.control_panel.width()
        self.control_panel.move((screen_width - panel_width) // 2, 20)

    def _on_shape_changed(self, name: str, shape: CaptureShape):
        """Handle shape button click."""
        self.shape = shape
        self.force_square = (name == "Square")

        # Update button styles
        for btn_name, btn in self.shape_buttons.items():
            btn.setChecked(btn_name == name)
            if btn_name == name:
                btn.setObjectName("selected")
            else:
                btn.setObjectName("")
            btn.setStyleSheet(btn.styleSheet())  # Force refresh

        self.update()
        logger.debug(f"Shape changed to: {name}")

    def _on_border_toggle(self, state):
        """Handle border checkbox toggle."""
        self.show_border = (state == Qt.CheckState.Checked.value)
        self.update()

    def _on_border_color_changed(self, color_name: str):
        """Handle border color change."""
        color_map = {
            "Red": "#FF0000",
            "Blue": "#0000FF",
            "Green": "#00FF00",
            "Yellow": "#FFFF00",
            "White": "#FFFFFF",
            "Black": "#000000"
        }
        self.border_color = QColor(color_map.get(color_name, "#FF0000"))
        self.update()

    def paintEvent(self, event):
        """Paint the overlay with captured screen and selection."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill with black background first
        painter.fillRect(self.rect(), QColor(0, 0, 0, 255))

        # Draw captured screen on top
        if self.screen_pixmap:
            painter.drawPixmap(0, 0, self.screen_pixmap)

            # Apply semi-transparent black overlay for dimming
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw selection region (will clear dimming in selected area)
        if self.start_point and self.current_point:
            self._draw_selection(painter)

    def _draw_selection(self, painter: QPainter):
        """Draw the current selection region."""
        if self.shape == CaptureShape.RECTANGLE:
            self._draw_rectangle_selection(painter)
        elif self.shape == CaptureShape.CIRCLE:
            self._draw_circle_selection(painter)
        elif self.shape == CaptureShape.FREEFORM:
            self._draw_freeform_selection(painter)

    def _draw_rectangle_selection(self, painter: QPainter):
        """Draw rectangle/square selection."""
        rect = QRect(self.start_point, self.current_point).normalized()

        # Force square if needed
        if hasattr(self, 'force_square') and self.force_square:
            size = min(rect.width(), rect.height())
            rect.setWidth(size)
            rect.setHeight(size)

        # Show captured screen clearly in selection area (no dimming)
        if self.screen_pixmap:
            # Draw the selected region from screen pixmap without dimming
            painter.drawPixmap(rect, self.screen_pixmap, rect)

        # Draw border if enabled
        if self.show_border:
            pen = QPen(self.border_color, self.border_width)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        # Draw size label
        self._draw_size_label(painter, rect)

    def _draw_circle_selection(self, painter: QPainter):
        """Draw circle/oval selection."""
        rect = QRect(self.start_point, self.current_point).normalized()

        # Show captured screen clearly in selection area (no dimming)
        if self.screen_pixmap:
            # Create a circular clip path
            painter.save()
            path = QPainterPath()
            path.addEllipse(rect)
            painter.setClipPath(path)
            painter.drawPixmap(rect, self.screen_pixmap, rect)
            painter.restore()

        # Draw border if enabled
        if self.show_border:
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

        # Create path from points (convert QPoint to QPointF)
        path = QPainterPath()
        path.moveTo(QPointF(self.freeform_points[0]))
        for point in self.freeform_points[1:]:
            path.lineTo(QPointF(point))

        # If still selecting, add current point
        if self.is_selecting and self.current_point:
            path.lineTo(QPointF(self.current_point))
        else:
            path.closeSubpath()

        # Show captured screen clearly in freeform path (no dimming)
        if self.screen_pixmap:
            painter.save()
            painter.setClipPath(path)
            # Get bounding rect of freeform path
            bounds = path.boundingRect().toRect()
            painter.drawPixmap(bounds, self.screen_pixmap, bounds)
            painter.restore()

        # Draw border if enabled
        if self.show_border:
            pen = QPen(self.border_color, self.border_width)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def _draw_size_label(self, painter: QPainter, rect: QRect):
        """Draw size label for selection."""
        label = f"{rect.width()} x {rect.height()}"

        # Position label at top-left of selection
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))

        label_rect = painter.fontMetrics().boundingRect(label)
        label_rect.adjust(-5, -2, 5, 2)
        label_rect.moveTopLeft(QPoint(rect.left(), rect.top() - label_rect.height() - 5))

        painter.drawRect(label_rect)

        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event):
        """Handle mouse press - start selection."""
        if event.button() == Qt.MouseButton.LeftButton and not self.selection_complete:
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
        """Handle mouse release - end selection and auto-copy to clipboard."""
        if event.button() == Qt.MouseButton.LeftButton and not self.selection_complete:
            self.is_selecting = False
            self.current_point = event.pos()

            # Mark selection as complete
            self.selection_complete = True

            # Remove crosshair cursor
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

            # Capture the selected region
            self._capture_selection()

            # Auto-copy to clipboard
            if self.captured_image:
                self._copy_to_clipboard(self.captured_image)
                self.instructions.setText("✓ Copied to clipboard! • Save or Done to finish")
                self.instructions.setStyleSheet("font-size: 10px; color: #00FF00; padding-top: 5px;")

            # Show action buttons
            self.save_button.setVisible(True)
            self.copy_button.setVisible(True)
            self.done_button.setVisible(True)

            # Reposition control panel to accommodate new buttons
            self.control_panel.adjustSize()
            screen_width = self.screen().geometry().width()
            panel_width = self.control_panel.width()
            self.control_panel.move((screen_width - panel_width) // 2, 20)

            self.update()

    def keyPressEvent(self, event):
        """Handle key press - confirm or cancel."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # If selection complete, treat as Done
            if self.selection_complete:
                self._on_done_clicked()
            else:
                self._confirm_capture()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel_capture()

    def _capture_selection(self):
        """Capture the selected region to pixmap."""
        if not self.start_point or not self.current_point:
            return

        try:
            # Calculate capture region
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()

                # Force square if needed
                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

            if rect.width() < 5 or rect.height() < 5:
                logger.warning("Selection too small")
                return

            # Capture region from screen pixmap
            if self.screen_pixmap:
                self.captured_image = self.screen_pixmap.copy(rect)
                logger.debug(f"Captured selection: {rect.width()}x{rect.height()}")

        except Exception as e:
            logger.error(f"Failed to capture selection: {e}", exc_info=True)

    def _copy_to_clipboard(self, pixmap: QPixmap):
        """Copy pixmap to system clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            logger.info("✓ Image copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}", exc_info=True)

    def _on_save_clicked(self):
        """Handle Save button click."""
        if not self.captured_image:
            return

        try:
            from pathlib import Path
            from datetime import datetime
            import os

            # Create captures directory
            appdata = os.environ.get('APPDATA', '')
            if not appdata:
                logger.error("APPDATA environment variable not found")
                return

            captures_dir = Path(appdata) / "Ghostman" / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
            file_path = captures_dir / filename

            # Save image
            self.captured_image.save(str(file_path), "PNG")

            logger.info(f"✓ Image saved: {file_path}")
            self.instructions.setText(f"✓ Saved to {filename}")
            self.instructions.setStyleSheet("font-size: 10px; color: #00FF00; padding-top: 5px;")

        except Exception as e:
            logger.error(f"Failed to save image: {e}", exc_info=True)
            self.instructions.setText(f"✗ Save failed: {str(e)}")
            self.instructions.setStyleSheet("font-size: 10px; color: #FF0000; padding-top: 5px;")

    def _on_copy_clicked(self):
        """Handle Copy button click."""
        if self.captured_image:
            self._copy_to_clipboard(self.captured_image)
            self.instructions.setText("✓ Copied to clipboard!")
            self.instructions.setStyleSheet("font-size: 10px; color: #00FF00; padding-top: 5px;")

    def _on_done_clicked(self):
        """Handle Done button click - emit result and close."""
        if not self.captured_image:
            self._cancel_capture()
            return

        try:
            # Calculate capture region for result
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()

                # Force square if needed
                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

            # Convert pixmap to bytes
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            self.captured_image.save(buffer, "PNG")
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

        except Exception as e:
            logger.error(f"Failed to complete capture: {e}", exc_info=True)
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

                # Force square if needed
                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

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
