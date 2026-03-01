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


class SplashScreen(QWidget):
    """
    Custom branded splash screen shown during Specter startup.

    Features a dark rounded-rect background, app icon, title/subtitle,
    an animated gradient progress bar with a pulsing glow at the
    leading edge, and a step-label describing the current operation.
    """

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

        # Glow animation phase (0 → ∞, wraps via sin())
        self._glow_phase: float = 0.0

        # Opacity used for fade-out
        self._splash_opacity: float = 1.0

        # Load the app icon once
        self._icon_pixmap: QPixmap | None = self._load_icon()

        # Cache version string (avoids per-frame QApplication lookup)
        app = QApplication.instance()
        ver = app.applicationVersion() if app and app.applicationVersion() else ""
        self._version_text: str = f"v{ver}" if ver else ""

        # ~30 fps timer to animate the progress-bar glow
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(30)  # ~33 fps
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
        self._glow_phase += 0.12
        self.update()

    # ------------------------------------------------------------------ #
    #  Painting
    # ------------------------------------------------------------------ #

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # ---- Background ------------------------------------------------
        bg_rect = QRectF(1, 1, w - 2, h - 2)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(bg_rect, 16, 16)

        # Subtle cyan border glow
        glow_pen = QPen(QColor(0, 212, 255, 40), 2)
        painter.setPen(glow_pen)
        painter.setBrush(QBrush(QColor("#0a0a1a")))
        painter.drawPath(bg_path)

        # ---- App icon ---------------------------------------------------
        icon_y = 30
        if self._icon_pixmap and not self._icon_pixmap.isNull():
            icon_x = (w - self._icon_pixmap.width()) // 2
            painter.drawPixmap(icon_x, icon_y, self._icon_pixmap)

        # ---- Title: "SPECTER" -------------------------------------------
        title_y = icon_y + 128 + 18
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        painter.setFont(title_font)
        painter.setPen(QColor("#00d4ff"))
        painter.drawText(QRect(0, title_y, w, 30), Qt.AlignmentFlag.AlignCenter, "SPECTER")

        # ---- Subtitle ---------------------------------------------------
        subtitle_y = title_y + 28
        subtitle_font = QFont("Segoe UI", 9)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(160, 160, 175))
        painter.drawText(
            QRect(0, subtitle_y, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "AI Desktop Assistant",
        )

        # ---- Version ----------------------------------------------------
        version_y = subtitle_y + 18
        if self._version_text:
            version_font = QFont("Segoe UI", 8)
            painter.setFont(version_font)
            painter.setPen(QColor(100, 100, 120))
            painter.drawText(
                QRect(0, version_y, w, 16),
                Qt.AlignmentFlag.AlignCenter,
                self._version_text,
            )

        # ---- Progress bar -----------------------------------------------
        bar_margin = 50
        bar_h = 6
        bar_y = h - 50
        bar_x = bar_margin
        bar_w = w - 2 * bar_margin

        # Track (dark)
        track_path = QPainterPath()
        track_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
        track_path.addRoundedRect(track_rect, bar_h / 2, bar_h / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 30, 50))
        painter.drawPath(track_path)

        # Filled portion (gradient: blue → cyan)
        fill_w = bar_w * (self._progress / 100.0)
        if fill_w > 0:
            fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, bar_h / 2, bar_h / 2)

            grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            grad.setColorAt(0.0, QColor(30, 90, 255))
            grad.setColorAt(1.0, QColor(0, 212, 255))
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
            radial.setColorAt(1.0, QColor(0, 212, 255, 0))
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
        label_font = QFont("Segoe UI", 8)
        painter.setFont(label_font)
        painter.setPen(QColor(140, 140, 160))
        painter.drawText(
            QRect(bar_margin, label_y, bar_w, 18),
            Qt.AlignmentFlag.AlignCenter,
            self._step_label,
        )

        painter.end()
