"""
Branded splash/loading screen for Specter.

Displays a frameless animated splash screen with progress bar
during application startup.
"""

import logging
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QRectF, QPropertyAnimation,
    QEasingCurve, pyqtProperty,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap,
    QLinearGradient, QRadialGradient, QPainterPath,
)

logger = logging.getLogger("specter.splash_screen")

# Two-pi constant for glow phase wrapping
_TWO_PI = 2.0 * math.pi


class SplashScreen(QWidget):
    """
    Custom branded splash screen shown during Specter startup.

    Features a dark rounded-rect background, app icon, title/subtitle,
    an animated gradient progress bar with a pulsing glow at the
    leading edge, and a step-label describing the current operation.
    """

    # ---- Static colors (avoid per-frame allocation) ----------------------
    _BG_COLOR = QColor("#0a0a1a")
    _BORDER_GLOW_COLOR = QColor(0, 212, 255, 40)
    _PRIMARY = QColor("#00d4ff")
    _TEXT_SUBTITLE = QColor(160, 160, 175)
    _TEXT_VERSION = QColor(100, 100, 120)
    _TEXT_LABEL = QColor(140, 140, 160)
    _TRACK_COLOR = QColor(30, 30, 50)
    _GRAD_START = QColor(30, 90, 255)
    _GRAD_END = QColor(0, 212, 255)
    _GLOW_TRANSPARENT = QColor(0, 212, 255, 0)

    # ------------------------------------------------------------------ #
    #  Construction
    # ------------------------------------------------------------------ #

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window setup — frameless splash that stays on top
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 320)

        # Center on the primary screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
            y = screen_geo.y() + (screen_geo.height() - self.height()) // 2
            self.move(x, y)

        # Progress state
        self._progress: int = 0
        self._step_label: str = "Initializing..."

        # Glow animation phase (wraps at 2*pi)
        self._glow_phase: float = 0.0

        # Opacity used for fade-out
        self._splash_opacity: float = 1.0

        # Load the app icon once
        self._icon_pixmap: QPixmap | None = self._load_icon()

        # Cache version string (avoids per-frame QApplication lookup)
        app = QApplication.instance()
        ver = app.applicationVersion() if app and app.applicationVersion() else ""
        self._version_text: str = f"v{ver}" if ver else ""

        # Pre-create fonts (avoid per-frame allocation in paintEvent)
        self._title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        self._title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        self._subtitle_font = QFont("Segoe UI", 9)
        self._version_font = QFont("Segoe UI", 8)
        self._label_font = QFont("Segoe UI", 8)

        # Pre-create static pen / paths
        self._border_pen = QPen(self._BORDER_GLOW_COLOR, 2)
        self._bg_path = QPainterPath()
        self._bg_path.addRoundedRect(QRectF(1, 1, 418, 318), 16, 16)

        # Static progress bar track path
        bar_margin = 50
        bar_h = 6
        bar_y = 320 - 50
        bar_w = 420 - 2 * bar_margin
        self._bar_x = bar_margin
        self._bar_y = bar_y
        self._bar_w = bar_w
        self._bar_h = bar_h
        self._track_path = QPainterPath()
        self._track_path.addRoundedRect(
            QRectF(bar_margin, bar_y, bar_w, bar_h), bar_h / 2, bar_h / 2
        )

        # ~33 fps timer to animate the progress-bar glow
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(30)
        self._glow_timer.timeout.connect(self._advance_glow)
        self._glow_timer.start()

    # ------------------------------------------------------------------ #
    #  Icon loading
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_icon() -> "QPixmap | None":
        try:
            from specter.src.utils.resource_resolver import resolve_asset
            icon_path = resolve_asset("app_icon.png")
            if icon_path and icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    return pixmap.scaled(
                        128, 128,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        except Exception as exc:
            logger.warning("Failed to load splash icon: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    #  pyqtProperty for opacity animation
    # ------------------------------------------------------------------ #

    def _get_splash_opacity(self) -> float:
        return self._splash_opacity

    def _set_splash_opacity(self, value: float) -> None:
        self._splash_opacity = value
        self.setWindowOpacity(value)

    splash_opacity = pyqtProperty(
        float, fget=_get_splash_opacity, fset=_set_splash_opacity
    )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def update_progress(self, percent: int, label: str) -> None:
        """Update the progress bar position and step text."""
        self._progress = max(0, min(percent, 100))
        self._step_label = label
        self.update()

    def finish(self) -> None:
        """Fade out and close the splash screen."""
        self._glow_timer.stop()

        anim = QPropertyAnimation(self, b"splash_opacity", self)
        anim.setDuration(400)
        anim.setStartValue(self._splash_opacity)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        anim.finished.connect(self.close)
        anim.finished.connect(self.deleteLater)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        # Keep a reference so it isn't garbage-collected before it finishes
        self._fade_anim = anim

    # ------------------------------------------------------------------ #
    #  Glow timer slot
    # ------------------------------------------------------------------ #

    def _advance_glow(self) -> None:
        self._glow_phase = (self._glow_phase + 0.12) % _TWO_PI
        self.update()

    # ------------------------------------------------------------------ #
    #  Painting
    # ------------------------------------------------------------------ #

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()

        # ---- Background ------------------------------------------------
        painter.setPen(self._border_pen)
        painter.setBrush(self._BG_COLOR)
        painter.drawPath(self._bg_path)

        # ---- App icon ---------------------------------------------------
        icon_y = 30
        if self._icon_pixmap and not self._icon_pixmap.isNull():
            icon_x = (w - self._icon_pixmap.width()) // 2
            painter.drawPixmap(icon_x, icon_y, self._icon_pixmap)

        # ---- Title: "SPECTER" -------------------------------------------
        title_y = icon_y + 128 + 18
        painter.setFont(self._title_font)
        painter.setPen(self._PRIMARY)
        painter.drawText(QRect(0, title_y, w, 30), Qt.AlignmentFlag.AlignCenter, "SPECTER")

        # ---- Subtitle ---------------------------------------------------
        subtitle_y = title_y + 28
        painter.setFont(self._subtitle_font)
        painter.setPen(self._TEXT_SUBTITLE)
        painter.drawText(
            QRect(0, subtitle_y, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "AI Desktop Assistant",
        )

        # ---- Version ----------------------------------------------------
        if self._version_text:
            version_y = subtitle_y + 18
            painter.setFont(self._version_font)
            painter.setPen(self._TEXT_VERSION)
            painter.drawText(
                QRect(0, version_y, w, 16),
                Qt.AlignmentFlag.AlignCenter,
                self._version_text,
            )

        # ---- Progress bar -----------------------------------------------
        bar_x = self._bar_x
        bar_y = self._bar_y
        bar_w = self._bar_w
        bar_h = self._bar_h

        # Track (dark)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._TRACK_COLOR)
        painter.drawPath(self._track_path)

        # Filled portion (gradient: blue → cyan)
        fill_w = bar_w * (self._progress / 100.0)
        if fill_w > 0:
            fill_path = QPainterPath()
            fill_path.addRoundedRect(
                QRectF(bar_x, bar_y, fill_w, bar_h), bar_h / 2, bar_h / 2
            )

            grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            grad.setColorAt(0.0, self._GRAD_START)
            grad.setColorAt(1.0, self._GRAD_END)
            painter.setBrush(QBrush(grad))
            painter.drawPath(fill_path)

            # Glow / pulse at the leading edge
            pulse = 0.5 + 0.5 * math.sin(self._glow_phase)
            glow_radius = 14.0 + 6.0 * pulse
            glow_alpha = int(120 + 80 * pulse)
            glow_cx = bar_x + fill_w
            glow_cy = bar_y + bar_h / 2

            radial = QRadialGradient(glow_cx, glow_cy, glow_radius)
            radial.setColorAt(0.0, QColor(0, 212, 255, glow_alpha))
            radial.setColorAt(1.0, self._GLOW_TRANSPARENT)
            painter.setBrush(QBrush(radial))
            painter.drawEllipse(
                QRectF(
                    glow_cx - glow_radius,
                    glow_cy - glow_radius,
                    glow_radius * 2,
                    glow_radius * 2,
                )
            )

        # ---- Step label -------------------------------------------------
        label_y = bar_y + bar_h + 8
        painter.setFont(self._label_font)
        painter.setPen(self._TEXT_LABEL)
        painter.drawText(
            QRect(bar_x, label_y, bar_w, 18),
            Qt.AlignmentFlag.AlignCenter,
            self._step_label,
        )

        painter.end()
