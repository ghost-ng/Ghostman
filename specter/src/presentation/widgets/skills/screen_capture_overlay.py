"""
Screen Capture Overlay - Full-screen overlay for selecting capture regions.

Provides a full-screen overlay showing the captured screen with a control panel
for selecting shapes, configuring borders, and drawing markup annotations.
"""

import logging
from typing import Optional, List, Tuple
from io import BytesIO

from PyQt6.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QFrame, QColorDialog
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal, QBuffer, QIODevice, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QCursor, QPixmap, QImage,
    QPainterPath, QPolygon
)

from ....infrastructure.skills.interfaces.screen_capture_skill import (
    CaptureShape, CaptureResult
)

logger = logging.getLogger("specter.ui.screen_capture_overlay")


class ScreenCaptureOverlay(QWidget):
    """
    Full-screen overlay for screen capture with control panel.

    Shows the captured screen with semi-transparent dimming. User can select
    shape, configure border, draw markup annotations, and drag to select region.

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
        super().__init__(parent)

        # Load border color from settings
        from ....infrastructure.storage.settings_manager import settings
        saved_border_color = settings.get('screen_capture.border_color', border_color)

        self.shape = shape
        self.border_width = border_width
        self.border_color = QColor(saved_border_color)
        self.show_border = border_width > 0

        # Selection state
        self.start_point: Optional[QPoint] = None
        self.current_point: Optional[QPoint] = None
        self.freeform_points: List[QPoint] = []
        self.is_selecting = False
        self.selection_complete = False
        self.captured_image: Optional[QPixmap] = None

        # Markup state
        self._markup_mode = False
        self._markup_strokes: List[Tuple[QColor, int, List[QPoint]]] = []  # (color, width, points)
        self._current_stroke: List[QPoint] = []
        self._markup_color = QColor("#FF0000")
        self._markup_width = 3

        # Capture screen BEFORE showing overlay
        self._capture_screen()

        # Setup UI
        self._setup_ui()
        self._create_control_panel()

    def _setup_ui(self):
        """Setup overlay UI properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.virtualGeometry()
            self.setGeometry(geometry)
        else:
            self.setWindowState(Qt.WindowState.WindowFullScreen)

        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _capture_screen(self):
        """Capture full screen (all monitors) before showing overlay."""
        screen = QApplication.primaryScreen()
        if screen:
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

    # ------------------------------------------------------------------
    #  Compact QSS used by control panel
    # ------------------------------------------------------------------
    _PANEL_QSS = """
        QFrame#capturePanel {
            background-color: rgba(22, 22, 30, 245);
            border: 1px solid rgba(80, 80, 80, 180);
            border-radius: 6px;
            padding: 4px;
        }
        QLabel { color: #FFFFFF; font-size: 11px; }
        QPushButton {
            background-color: rgba(50, 50, 58, 255);
            color: #CCCCCC;
            border: 1px solid rgba(70, 70, 78, 150);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 10px;
        }
        QPushButton:hover {
            background-color: rgba(70, 70, 78, 255);
            color: #FFFFFF;
            border-color: rgba(100, 100, 110, 200);
        }
        QPushButton:pressed {
            background-color: rgba(35, 35, 42, 255);
        }
        QPushButton:checked {
            background-color: rgba(0, 110, 200, 255);
            color: #FFFFFF;
            border-color: rgba(0, 140, 240, 255);
            font-weight: bold;
        }
        QPushButton:checked:hover {
            background-color: rgba(0, 130, 220, 255);
        }
        QPushButton#cancelBtn {
            background-color: rgba(140, 30, 30, 200);
            color: #FFFFFF;
            border: 1px solid rgba(180, 40, 40, 200);
        }
        QPushButton#cancelBtn:hover {
            background-color: rgba(180, 40, 40, 255);
        }
        QPushButton#markupBtn:checked {
            background-color: rgba(200, 80, 0, 255);
            border-color: rgba(240, 100, 0, 255);
        }
        QCheckBox { color: #FFFFFF; font-size: 10px; spacing: 4px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid rgba(100, 100, 100, 200);
            border-radius: 3px;
            background-color: rgba(50, 50, 58, 255);
        }
        QCheckBox::indicator:checked {
            background-color: rgba(0, 110, 200, 255);
            border-color: rgba(0, 140, 240, 255);
        }
    """

    def _create_control_panel(self):
        """Create compact floating control panel."""
        self.control_panel = QFrame(self)
        self.control_panel.setObjectName("capturePanel")
        self.control_panel.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.control_panel.setStyleSheet(self._PANEL_QSS)

        layout = QVBoxLayout(self.control_panel)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 6, 8, 6)

        # ── Row 1: Title + Cancel ──
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        title = QLabel("Screen Capture")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        top_row.addWidget(title)

        top_row.addStretch()

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self._cancel_capture)
        cancel_btn.setToolTip("Cancel capture (ESC)")
        top_row.addWidget(cancel_btn)

        layout.addLayout(top_row)

        # ── Row 2: Shape buttons + Markup toggle ──
        shape_row = QHBoxLayout()
        shape_row.setSpacing(4)

        self.shape_buttons = {}
        shapes = [
            ("Rectangle", CaptureShape.RECTANGLE, "▭"),
            ("Square", CaptureShape.RECTANGLE, "□"),
            ("Circle", CaptureShape.CIRCLE, "○"),
            ("Freeform", CaptureShape.FREEFORM, "✎")
        ]

        for name, shape_type, icon in shapes:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setChecked(shape_type == self.shape and name == "Rectangle")
            btn.clicked.connect(lambda checked, n=name, s=shape_type: self._on_shape_changed(n, s))
            self.shape_buttons[name] = btn
            shape_row.addWidget(btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(80, 80, 80, 150);")
        shape_row.addWidget(sep)

        # Markup toggle
        self._markup_btn = QPushButton("🖊 Markup")
        self._markup_btn.setObjectName("markupBtn")
        self._markup_btn.setCheckable(True)
        self._markup_btn.setChecked(False)
        self._markup_btn.clicked.connect(self._toggle_markup_mode)
        self._markup_btn.setToolTip("Draw annotations on the screenshot")
        shape_row.addWidget(self._markup_btn)

        layout.addLayout(shape_row)

        # ── Row 3: Border options + Markup color/size (shared row) ──
        options_row = QHBoxLayout()
        options_row.setSpacing(4)

        self.border_checkbox = QCheckBox("Border")
        self.border_checkbox.setChecked(self.show_border)
        self.border_checkbox.stateChanged.connect(self._on_border_toggle)
        options_row.addWidget(self.border_checkbox)

        # Color picker button (shared for border & markup)
        self.color_picker_btn = QPushButton()
        self.color_picker_btn.setFixedWidth(50)
        self.color_picker_btn.setText(self.border_color.name().upper())
        self._update_color_btn_style()
        self.color_picker_btn.clicked.connect(self._pick_border_color)
        self.color_picker_btn.setToolTip("Pick custom color")
        options_row.addWidget(self.color_picker_btn)

        # Color presets (compact)
        preset_colors = [
            ("#FF0000", "Red"), ("#0000FF", "Blue"),
            ("#00FF00", "Green"), ("#FFFF00", "Yellow"),
            ("#FFFFFF", "White"), ("#000000", "Black")
        ]

        for color_hex, color_name in preset_colors:
            preset_btn = QPushButton()
            preset_btn.setFixedSize(20, 20)
            preset_btn.setStyleSheet(
                f"background-color: {color_hex}; border: 1px solid #888; "
                f"border-radius: 2px; padding: 0px;"
            )
            preset_btn.setToolTip(color_name)
            preset_btn.clicked.connect(lambda checked, c=color_hex: self._set_border_color(c))
            options_row.addWidget(preset_btn)

        options_row.addStretch()

        # Markup pen width buttons (visible when markup mode on)
        self._pen_thin_btn = QPushButton("╌")
        self._pen_thin_btn.setFixedWidth(24)
        self._pen_thin_btn.setToolTip("Thin pen (2px)")
        self._pen_thin_btn.clicked.connect(lambda: self._set_markup_width(2))

        self._pen_med_btn = QPushButton("━")
        self._pen_med_btn.setFixedWidth(24)
        self._pen_med_btn.setToolTip("Medium pen (4px)")
        self._pen_med_btn.clicked.connect(lambda: self._set_markup_width(4))

        self._pen_thick_btn = QPushButton("▬")
        self._pen_thick_btn.setFixedWidth(24)
        self._pen_thick_btn.setToolTip("Thick pen (8px)")
        self._pen_thick_btn.clicked.connect(lambda: self._set_markup_width(8))

        self._undo_btn = QPushButton("↩")
        self._undo_btn.setFixedWidth(24)
        self._undo_btn.setToolTip("Undo last stroke")
        self._undo_btn.clicked.connect(self._undo_markup_stroke)

        for btn in (self._pen_thin_btn, self._pen_med_btn, self._pen_thick_btn, self._undo_btn):
            btn.setVisible(False)
            options_row.addWidget(btn)

        layout.addLayout(options_row)

        # ── Row 4: Action buttons (initially hidden) ──
        action_layout = QHBoxLayout()
        action_layout.setSpacing(4)

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
        self.instructions = QLabel("Drag to select region • ESC to cancel")
        self.instructions.setStyleSheet("font-size: 9px; color: #999; padding-top: 2px;")
        layout.addWidget(self.instructions)

        # Position control panel at top center
        self.control_panel.adjustSize()
        screen_width = self.screen().geometry().width()
        panel_width = self.control_panel.width()
        self.control_panel.move((screen_width - panel_width) // 2, 10)

    def _update_color_btn_style(self):
        """Update the color picker button appearance."""
        text_color = '#000000' if self.border_color.lightness() > 128 else '#FFFFFF'
        self.color_picker_btn.setText(self.border_color.name().upper())
        self.color_picker_btn.setStyleSheet(
            f"background-color: {self.border_color.name()}; "
            f"color: {text_color}; "
            f"border: 2px solid #888; font-size: 8px; font-weight: bold;"
        )

    # ------------------------------------------------------------------
    #  Markup mode
    # ------------------------------------------------------------------

    def _toggle_markup_mode(self, checked: bool):
        """Toggle markup drawing mode."""
        self._markup_mode = checked

        # Show/hide pen width buttons
        for btn in (self._pen_thin_btn, self._pen_med_btn, self._pen_thick_btn, self._undo_btn):
            btn.setVisible(checked)

        # Update cursor
        if checked:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.instructions.setText("Draw on screen • Click Markup again to return to selection")
        elif self.selection_complete:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.instructions.setText("✓ Copied to clipboard! • Save or Done to finish")
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            self.instructions.setText("Drag to select region • ESC to cancel")

        # Resize panel
        self.control_panel.adjustSize()
        screen_width = self.screen().geometry().width()
        panel_width = self.control_panel.width()
        self.control_panel.move((screen_width - panel_width) // 2, 10)

    def _set_markup_width(self, width: int):
        """Set markup pen width."""
        self._markup_width = width

    def _undo_markup_stroke(self):
        """Remove last markup stroke."""
        if self._markup_strokes:
            self._markup_strokes.pop()
            self.update()

    # ------------------------------------------------------------------
    #  Shape / border callbacks
    # ------------------------------------------------------------------

    def _on_shape_changed(self, name: str, shape: CaptureShape):
        """Handle shape button click."""
        # Turn off markup mode when selecting a shape
        if self._markup_mode:
            self._markup_btn.setChecked(False)
            self._toggle_markup_mode(False)

        self.shape = shape
        self.force_square = (name == "Square")

        for btn_name, btn in self.shape_buttons.items():
            btn.setChecked(btn_name == name)
        self.update()

    def _on_border_toggle(self, state):
        """Handle border checkbox toggle."""
        self.show_border = (state == Qt.CheckState.Checked.value)
        self.update()

    def _pick_border_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self.border_color, self, "Select Color")
        if color.isValid():
            self._set_border_color(color.name())

    def _set_border_color(self, color_hex: str):
        """Set border/markup color and save to settings."""
        from ....infrastructure.storage.settings_manager import settings

        self.border_color = QColor(color_hex)
        self._markup_color = QColor(color_hex)
        self._update_color_btn_style()

        settings.set('screen_capture.border_color', color_hex)
        self.update()

    # ------------------------------------------------------------------
    #  Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        """Paint the overlay with captured screen, selection, and markup."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill with black background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 255))

        # Draw captured screen on top
        if self.screen_pixmap:
            painter.drawPixmap(0, 0, self.screen_pixmap)
            # Semi-transparent dimming
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw selection region
        if self.start_point and self.current_point:
            self._draw_selection(painter)

        # Draw all markup strokes
        self._draw_markup_strokes(painter)

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

        if hasattr(self, 'force_square') and self.force_square:
            size = min(rect.width(), rect.height())
            rect.setWidth(size)
            rect.setHeight(size)

        if self.screen_pixmap:
            painter.drawPixmap(rect, self.screen_pixmap, rect)

        if self.show_border:
            pen = QPen(self.border_color, self.border_width)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        self._draw_size_label(painter, rect)

    def _draw_circle_selection(self, painter: QPainter):
        """Draw circle/oval selection."""
        rect = QRect(self.start_point, self.current_point).normalized()

        if self.screen_pixmap:
            painter.save()
            path = QPainterPath()
            path.addEllipse(QRectF(rect))
            painter.setClipPath(path)
            painter.drawPixmap(rect, self.screen_pixmap, rect)
            painter.restore()

        if self.show_border:
            pen = QPen(self.border_color, self.border_width)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)

        self._draw_size_label(painter, rect)

    def _draw_freeform_selection(self, painter: QPainter):
        """Draw freeform selection."""
        if len(self.freeform_points) < 2:
            return

        path = QPainterPath()
        path.moveTo(QPointF(self.freeform_points[0]))
        for point in self.freeform_points[1:]:
            path.lineTo(QPointF(point))

        if self.is_selecting and self.current_point:
            path.lineTo(QPointF(self.current_point))
        else:
            path.closeSubpath()

        if self.screen_pixmap:
            painter.save()
            painter.setClipPath(path)
            bounds = path.boundingRect().toRect()
            painter.drawPixmap(bounds, self.screen_pixmap, bounds)
            painter.restore()

        if self.show_border:
            pen = QPen(self.border_color, self.border_width)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def _draw_size_label(self, painter: QPainter, rect: QRect):
        """Draw size label for selection."""
        label = f"{rect.width()} x {rect.height()}"
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))

        label_rect = painter.fontMetrics().boundingRect(label)
        label_rect.adjust(-5, -2, 5, 2)
        label_rect.moveTopLeft(QPoint(rect.left(), rect.top() - label_rect.height() - 5))

        painter.drawRect(label_rect)
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_markup_strokes(self, painter: QPainter):
        """Draw all saved markup strokes and current in-progress stroke."""
        for color, width, points in self._markup_strokes:
            if len(points) < 2:
                continue
            pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            for i in range(1, len(points)):
                painter.drawLine(points[i - 1], points[i])

        # Draw current stroke in progress
        if self._markup_mode and self._current_stroke and len(self._current_stroke) >= 2:
            pen = QPen(self._markup_color, self._markup_width,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            for i in range(1, len(self._current_stroke)):
                painter.drawLine(self._current_stroke[i - 1], self._current_stroke[i])

    # ------------------------------------------------------------------
    #  Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._markup_mode:
            # Start a new markup stroke
            self._current_stroke = [event.pos()]
            return

        if not self.selection_complete:
            self.start_point = event.pos()
            self.current_point = event.pos()
            self.is_selecting = True

            if self.shape == CaptureShape.FREEFORM:
                self.freeform_points = [event.pos()]

            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        if self._markup_mode and self._current_stroke:
            self._current_stroke.append(event.pos())
            self.update()
            return

        if self.is_selecting:
            self.current_point = event.pos()

            if self.shape == CaptureShape.FREEFORM:
                self.freeform_points.append(event.pos())

            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._markup_mode:
            # Finish current markup stroke
            if self._current_stroke and len(self._current_stroke) >= 2:
                self._markup_strokes.append(
                    (QColor(self._markup_color), self._markup_width, list(self._current_stroke))
                )
            self._current_stroke = []
            self.update()
            return

        if self.selection_complete:
            return

        self.is_selecting = False
        self.current_point = event.pos()
        self.selection_complete = True

        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # Capture the selected region
        self._capture_selection()

        # Auto-copy to clipboard
        if self.captured_image:
            self._copy_to_clipboard(self.captured_image)
            self.instructions.setText("✓ Copied to clipboard! • Save or Done to finish")
            self.instructions.setStyleSheet("font-size: 9px; color: #00FF00; padding-top: 2px;")

        # Show action buttons
        self.save_button.setVisible(True)
        self.copy_button.setVisible(True)
        self.done_button.setVisible(True)

        # Reposition control panel
        self.control_panel.adjustSize()
        screen_width = self.screen().geometry().width()
        panel_width = self.control_panel.width()
        self.control_panel.move((screen_width - panel_width) // 2, 10)

        self.update()

    def keyPressEvent(self, event):
        """Handle key press - confirm or cancel."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.selection_complete:
                self._on_done_clicked()
            else:
                self._confirm_capture()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel_capture()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._undo_markup_stroke()

    # ------------------------------------------------------------------
    #  Capture helpers
    # ------------------------------------------------------------------

    def _capture_selection(self):
        """Capture the selected region to pixmap (includes markup)."""
        if not self.start_point or not self.current_point:
            return

        try:
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()

                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

            if rect.width() < 5 or rect.height() < 5:
                logger.warning("Selection too small")
                return

            if self.screen_pixmap:
                self.captured_image = self._render_capture(rect)
                logger.debug(f"Captured selection: {rect.width()}x{rect.height()}")

        except Exception as e:
            logger.error(f"Failed to capture selection: {e}", exc_info=True)

    def _render_capture(self, rect: QRect) -> QPixmap:
        """Render the captured region with markup strokes baked in."""
        # Start from the raw screen region
        pixmap = self.screen_pixmap.copy(rect)

        # Paint markup strokes onto the captured pixmap
        if self._markup_strokes:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for color, width, points in self._markup_strokes:
                # Offset points relative to capture rect
                pen = QPen(color, width, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                for i in range(1, len(points)):
                    p1 = points[i - 1] - rect.topLeft()
                    p2 = points[i] - rect.topLeft()
                    painter.drawLine(p1, p2)
            painter.end()

        return pixmap

    def _copy_to_clipboard(self, pixmap: QPixmap):
        """Copy pixmap to system clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            logger.info("Image copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}", exc_info=True)

    def _on_save_clicked(self):
        """Handle Save button click."""
        if not self.captured_image:
            return

        # Re-render to include any new markup since last capture
        self._recapture_with_markup()

        try:
            from pathlib import Path
            from datetime import datetime
            import os
            from ....infrastructure.storage.settings_manager import settings

            custom_save_path = settings.get('screen_capture.default_save_path', '')

            if custom_save_path and Path(custom_save_path).exists():
                captures_dir = Path(custom_save_path)
            else:
                appdata = os.environ.get('APPDATA', '')
                if not appdata:
                    logger.error("APPDATA environment variable not found")
                    return
                captures_dir = Path(appdata) / "Specter" / "captures"
                captures_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
            file_path = captures_dir / filename

            self.captured_image.save(str(file_path), "PNG")

            logger.info(f"Image saved: {file_path}")
            self.instructions.setText(f"✓ Saved to {filename}")
            self.instructions.setStyleSheet("font-size: 9px; color: #00FF00; padding-top: 2px;")

        except Exception as e:
            logger.error(f"Failed to save image: {e}", exc_info=True)
            self.instructions.setText(f"✗ Save failed: {str(e)}")
            self.instructions.setStyleSheet("font-size: 9px; color: #FF0000; padding-top: 2px;")

    def _on_copy_clicked(self):
        """Handle Copy button click."""
        if self.captured_image:
            self._recapture_with_markup()
            self._copy_to_clipboard(self.captured_image)
            self.instructions.setText("✓ Copied to clipboard!")
            self.instructions.setStyleSheet("font-size: 9px; color: #00FF00; padding-top: 2px;")

    def _recapture_with_markup(self):
        """Re-render captured image to include latest markup."""
        if not self.start_point or not self.current_point:
            return

        if self.shape == CaptureShape.FREEFORM:
            rect = self._get_freeform_bounding_rect()
        else:
            rect = QRect(self.start_point, self.current_point).normalized()
            if hasattr(self, 'force_square') and self.force_square:
                size = min(rect.width(), rect.height())
                rect.setWidth(size)
                rect.setHeight(size)

        if self.screen_pixmap:
            self.captured_image = self._render_capture(rect)

    def _on_done_clicked(self):
        """Handle Done button click - emit result and close."""
        if not self.captured_image:
            self._cancel_capture()
            return

        # Re-render to include any markup drawn after initial capture
        self._recapture_with_markup()

        try:
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()
                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            self.captured_image.save(buffer, "PNG")
            image_data = BytesIO(buffer.data().data())

            result = CaptureResult(
                shape=self.shape,
                x=rect.x(),
                y=rect.y(),
                width=rect.width(),
                height=rect.height(),
                image_data=image_data
            )

            logger.info(f"Screen capture completed: {rect.width()}x{rect.height()}")
            self.capture_completed.emit(result)
            self.close()

        except Exception as e:
            logger.error(f"Failed to complete capture: {e}", exc_info=True)
            self._cancel_capture()

    def _confirm_capture(self):
        """Confirm capture and emit result (legacy ENTER-to-confirm)."""
        if not self.start_point or not self.current_point:
            self._cancel_capture()
            return

        try:
            if self.shape == CaptureShape.FREEFORM:
                rect = self._get_freeform_bounding_rect()
            else:
                rect = QRect(self.start_point, self.current_point).normalized()
                if hasattr(self, 'force_square') and self.force_square:
                    size = min(rect.width(), rect.height())
                    rect.setWidth(size)
                    rect.setHeight(size)

            if rect.width() < 5 or rect.height() < 5:
                self._cancel_capture()
                return

            if self.screen_pixmap:
                captured_pixmap = self._render_capture(rect)

                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                captured_pixmap.save(buffer, "PNG")
                image_data = BytesIO(buffer.data().data())

                result = CaptureResult(
                    shape=self.shape,
                    x=rect.x(),
                    y=rect.y(),
                    width=rect.width(),
                    height=rect.height(),
                    image_data=image_data
                )

                logger.info(f"Screen capture completed: {rect.width()}x{rect.height()}")
                self.capture_completed.emit(result)
                self.close()
            else:
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
