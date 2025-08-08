"""Avatar widget for minimized application state."""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve, QTimer, QSequentialAnimationGroup, QParallelAnimationGroup
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QContextMenuEvent, QMouseEvent, QFont, QColor
from ui.components.overlay_base import OverlayBaseWindow
import time
import logging
import sys
from pathlib import Path

class AvatarWidget(OverlayBaseWindow):
    """Minimized avatar widget for the AI assistant."""
    
    # Signals
    left_clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    right_clicked = pyqtSignal(QPoint)
    avatar_hovered = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Animation properties
        self.hover_animation = None
        self.pulse_animation = None
        self.fade_in_animation = None
        self.glow_animation = None
        
        # Interaction tracking
        self.click_position = QPoint()
        self.idle_time = 0
        
        # Initialize activity timer
        self.activity_timer = QTimer()
        self.activity_timer.timeout.connect(self.check_activity)
        self.activity_timer.start(1000)  # Check every second
        
        self.setup_ui()
        self.setup_animations()
        # Force visibility timer
        self.visibility_timer = QTimer()
        self.visibility_timer.timeout.connect(self.force_visibility)
        self.visibility_timer.start(2000)  # Check every 2 seconds
        
        self.resize(120, 120)  # LARGE avatar size for visibility
    
    def setup_ui(self):
        """CRITICAL FIX: Setup the avatar UI with proper widget configuration."""
        central_widget = QWidget()
        # CRITICAL: Set a solid background color on central widget too
        central_widget.setStyleSheet("""
            QWidget {
                background-color: rgb(0, 0, 0, 0);  /* Transparent background */
            }
        """)
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)  # No spacing for tight layout
        
        # Avatar image/icon
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add glow/shadow effect
        self.setup_glow_effect()
        
        # CRITICAL FIX: Ultra-high contrast styling with HUGE size for maximum visibility
        self.avatar_label.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 0, 0);  /* Bright red background */
                border: 10px solid rgb(0, 255, 0);  /* Bright green border */
                border-radius: 50px;
                font-size: 24px;
                font-weight: bold;
                color: white;
                min-width: 100px;
                min-height: 100px;
                max-width: 100px;
                max-height: 100px;
            }
        """)
        
        # Load avatar image - with fallback
        self.load_avatar_image()
        self.avatar_label.setFixedSize(100, 100)  # HUGE size for visibility
        
        # Ensure there's always visible text as fallback
        if self.avatar_label.text() == "" and self.avatar_label.pixmap() is None:
            self.avatar_label.setText("G")
        
        layout.addWidget(self.avatar_label)
        
        # Set initial size explicitly
        self.setFixedSize(80, 80)
        
        # Position in bottom-right corner by default
        self.position_in_corner()
        
        self.logger.info("Avatar widget UI setup complete")
    
    def load_avatar_image(self):
        """Load the avatar image from assets folder."""
        try:
            # Get the path to the assets folder
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                application_path = Path(sys.executable).parent
                assets_path = application_path / "assets"
            else:
                # Running as script
                # From src/ui/components/avatar_widget.py, go up 3 levels to ghostman/, then to assets
                current_file = Path(__file__)
                src_dir = current_file.parent.parent.parent  # Go up to src/
                ghostman_root = src_dir.parent  # Go up to ghostman/
                assets_path = ghostman_root / "assets"
            
            avatar_image_path = assets_path / "avatar.png"
            
            if avatar_image_path.exists():
                # Load and scale the image
                pixmap = QPixmap(str(avatar_image_path))
                if not pixmap.isNull():
                    # Scale to fit the label while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        56, 56,  # Slightly smaller than label size for padding
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.avatar_label.setPixmap(scaled_pixmap)
                    self.logger.info(f"Avatar image loaded from: {avatar_image_path}")
                else:
                    self.logger.error(f"Failed to load avatar image: {avatar_image_path}")
                    self.set_fallback_avatar()
            else:
                self.logger.warning(f"Avatar image not found: {avatar_image_path}")
                self.set_fallback_avatar()
                
        except Exception as e:
            self.logger.error(f"Error loading avatar image: {e}")
            self.set_fallback_avatar()
    
    def set_fallback_avatar(self):
        """Set fallback text avatar if image loading fails."""
        font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        self.avatar_label.setFont(font)
        self.avatar_label.setText("👻")  # Ghost emoji as fallback
        self.avatar_label.setStyleSheet("""
            QLabel {
                background-color: rgba(70, 130, 180, 220);
                border-radius: 30px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
    
    def position_in_corner(self):
        """Position avatar in bottom-right corner of screen."""
        from PyQt6.QtWidgets import QApplication
        
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60  # Account for taskbar
        self.move(x, y)
        
        self.logger.debug(f"Avatar positioned at ({x}, {y})")
    
    def setup_glow_effect(self):
        """Setup the glow/shadow effect for the avatar."""
        try:
            # Create drop shadow effect with enhanced glow
            self.shadow_effect = QGraphicsDropShadowEffect()
            self.shadow_effect.setBlurRadius(25)  # Increased blur for softer glow
            self.shadow_effect.setXOffset(0)
            self.shadow_effect.setYOffset(0)
            self.shadow_effect.setColor(QColor(135, 206, 235, 180))  # Enhanced sky blue glow
            
            # Apply effect to avatar label
            self.avatar_label.setGraphicsEffect(self.shadow_effect)
            
            self.logger.debug("Glow effect setup complete")
        except Exception as e:
            self.logger.error(f"Error setting up glow effect: {e}")
    
    def setup_animations(self):
        """Setup hover and interaction animations."""
        # Hover scale animation
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity effect for pulse and fade-in (separate from glow effect)
        self.opacity_effect = QGraphicsOpacityEffect()
        # Note: We can't apply multiple graphics effects, so we'll use window opacity
        
        # Fade-in animation for initial appearance
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)  # Shorter duration
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in_animation.setStartValue(0.8)  # Start from visible
        self.fade_in_animation.setEndValue(1.0)    # End at full opacity
        
        # Pulse animation disabled to remove strobe effect
        self.pulse_animation = None
        
        # Glow animation disabled to remove strobe effect - keep static glow
        self.glow_animation = None
        
        self.logger.debug("Avatar animations setup complete")
    
    def force_visibility(self):
        """Force the avatar to remain visible."""
        if not self.isVisible():
            self.show()
            self.raise_()
            self.logger.warning("Avatar was hidden - forcing visibility")
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle right-click context menu - ONLY functionality."""
        self.right_clicked.emit(event.globalPos())
        event.accept()
        self.logger.info("Avatar right-clicked")
    
    def enterEvent(self, event):
        """Handle mouse enter with animation."""
        self.avatar_hovered.emit(True)
        self.start_hover_animation()
        self.update_activity_time()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave with animation."""
        self.avatar_hovered.emit(False)
        self.end_hover_animation()
        super().leaveEvent(event)
    
    def show(self):
        """CRITICAL FIX: Override show to ensure maximum visibility with simplified approach."""
        # STEP 1: Set full opacity BEFORE any show operations
        self.setWindowOpacity(1.0)
        
        # STEP 2: Ensure proper size is set
        if self.width() <= 0 or self.height() <= 0:
            self.resize(80, 80)
            self.logger.info("Avatar resized to 80x80 during show()")
        
        # STEP 3: Position before showing (critical for visibility)
        self.position_in_corner()
        
        # STEP 4: Show the window using parent method
        super().show()
        
        # STEP 5: Force visibility with minimal operations
        self.setVisible(True)  # Explicitly set visible
        self.raise_()  # Bring to front
        
        # STEP 6: NO FADE-IN ANIMATION - keep it simple and visible
        self.setWindowOpacity(1.0)  # Ensure full opacity always
        
        # STEP 7: Force repaint to ensure it's drawn
        self.repaint()
        self.update()
        
        # STEP 8: Log visibility status
        self.logger.info(f"AVATAR SHOW COMPLETE - Visible: {self.isVisible()}, Opacity: {self.windowOpacity()}")
        self.logger.info(f"Avatar position: ({self.x()}, {self.y()}), Size: {self.width()}x{self.height()}")
        self.logger.info(f"Avatar window flags: {self.windowFlags()}")
        self.logger.info(f"Avatar window state: {self.windowState()}")
    
    def start_hover_animation(self):
        """Start hover animation (slight scale up)."""
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
        
        current_geometry = self.geometry()
        enlarged_geometry = current_geometry.adjusted(-5, -5, 5, 5)
        
        self.hover_animation.setStartValue(current_geometry)
        self.hover_animation.setEndValue(enlarged_geometry)
        self.hover_animation.start()
        
        # Maintain full opacity for visibility
        self.setWindowOpacity(1.0)
        
        # Glow animation should already be running by default
        # On hover, we could intensify the glow but let's keep it consistent
    
    def end_hover_animation(self):
        """End hover animation (scale back to normal)."""
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
        
        current_geometry = self.geometry()
        normal_geometry = current_geometry.adjusted(5, 5, -5, -5)
        
        self.hover_animation.setStartValue(current_geometry)
        self.hover_animation.setEndValue(normal_geometry)
        self.hover_animation.start()
        
        # Keep static glow effect - no pulsing animations
    
    def start_pulse_animation(self):
        """Start idle pulse animation - DISABLED to remove strobe effect."""
        # Animation disabled to prevent strobing
        pass
    
    def stop_pulse_animation(self):
        """Stop pulse animation - DISABLED to remove strobe effect."""
        # Animation disabled, maintain static opacity
        self.setWindowOpacity(0.95)
    
    def update_activity_time(self):
        """Update last activity time."""
        self.idle_time = 0
        # Maintain full opacity for visibility
        self.setWindowOpacity(1.0)
    
    def check_activity(self):
        """Monitor user activity for idle detection."""
        try:
            # Only count idle time if not hovering
            if not self.underMouse():
                self.idle_time += 1
                
                # Pulse animation disabled - no idle pulsing
            else:
                self.idle_time = 0
        except Exception as e:
            self.logger.error(f"Error in activity check: {e}")
    
    def set_avatar_text(self, text: str):
        """Set the avatar display text."""
        self.avatar_label.setText(text)
    
    def set_avatar_style(self, style_sheet: str):
        """Set custom avatar styling."""
        self.avatar_label.setStyleSheet(style_sheet)
    
    def show_notification_indicator(self, show: bool = True):
        """Show/hide notification indicator on avatar."""
        if show:
            # Change background color for notifications (with border)
            self.avatar_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(40, 35, 20, 180);
                    border: 2px solid #FFD700;
                    border-radius: 30px;
                }
            """)
            # Change glow color to gold
            if hasattr(self, 'shadow_effect'):
                self.shadow_effect.setColor(QColor(255, 215, 0, 180))
        else:
            # Normal styling
            self.avatar_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(20, 20, 40, 180);
                    border: 2px solid #4A90E2;
                    border-radius: 30px;
                }
            """)
            # Reset glow color to blue
            if hasattr(self, 'shadow_effect'):
                self.shadow_effect.setColor(QColor(135, 206, 235, 150))
    
    def closeEvent(self, event):
        """Handle close event."""
        # Stop timers
        self.activity_timer.stop()
        
        # Stop animations
        if self.hover_animation and self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
        
        # Pulse animation disabled
        
        if hasattr(self, 'fade_in_animation') and self.fade_in_animation and self.fade_in_animation.state() == QPropertyAnimation.State.Running:
            self.fade_in_animation.stop()
        
        # Glow animation disabled
        
        self.logger.info("Avatar widget closing")
        super().closeEvent(event)
    
    def apply_theme_colors(self, colors, spacing):
        """Apply theme colors to the avatar widget."""
        try:
            # Update avatar label styling with theme colors (with border)
            self.avatar_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors.background_dark};
                    border: 2px solid {colors.avatar_border};
                    border-radius: {spacing.border_radius * 2}px;
                }}
            """)
            
            # Update glow effect color if it exists
            if hasattr(self, 'shadow_effect') and self.shadow_effect:
                glow_color = QColor()
                glow_color.setNamedColor(colors.avatar_glow)
                self.shadow_effect.setColor(glow_color)
            
            self.logger.debug("Avatar theme colors applied successfully")
            
        except Exception as e:
            self.logger.error(f"Error applying theme colors to avatar: {e}")
    
    def update_notification_indicator_colors(self, colors):
        """Update notification indicator colors based on theme."""
        try:
            if hasattr(self, '_showing_notification') and self._showing_notification:
                # Update notification styling with theme colors (darker background, with border)
                notification_bg = colors.background_dark.replace(')', ', 0.7)').replace('rgb(', 'rgba(')
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {notification_bg};
                        border: 2px solid {colors.avatar_border};
                        border-radius: 30px;
                    }}
                """)
                
                # Update glow color for notification
                if hasattr(self, 'shadow_effect') and self.shadow_effect:
                    notif_color = QColor()
                    notif_color.setNamedColor(colors.avatar_notification)
                    self.shadow_effect.setColor(notif_color)
                    
        except Exception as e:
            self.logger.error(f"Error updating notification indicator colors: {e}")
    
    def show_notification_indicator(self, show: bool = True, colors=None):
        """Show/hide notification indicator on avatar with optional theme colors."""
        try:
            self._showing_notification = show
            
            if show:
                # Use theme colors if provided, otherwise fallback to default
                if colors:
                    bg_color = colors.background_dark
                    glow_color = colors.avatar_notification
                else:
                    bg_color = "rgba(20, 20, 40, 180)"
                    glow_color = "rgba(255, 215, 0, 180)"
                
                # Change background for notifications (with border)
                notification_bg = bg_color.replace('180)', '200)').replace('40,', '35,') if 'rgba' in bg_color else bg_color
                border_color = colors.avatar_border if colors else "#FFD700"  # Use gold for notification border if no colors
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {notification_bg};
                        border: 2px solid {border_color};
                        border-radius: 30px;
                    }}
                """)
                
                # Change glow color
                if hasattr(self, 'shadow_effect') and self.shadow_effect:
                    notif_color = QColor()
                    notif_color.setNamedColor(glow_color)
                    self.shadow_effect.setColor(notif_color)
            else:
                # Reset to normal styling - this should be called with current theme colors
                if colors:
                    bg_color = colors.background_dark
                    glow_color = colors.avatar_glow
                else:
                    bg_color = "rgba(20, 20, 40, 180)"
                    glow_color = "rgba(135, 206, 235, 150)"
                
                # Normal styling (with border)
                border_color = colors.avatar_border if colors else "#4A90E2"  # Default blue border if no colors
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {bg_color};
                        border: 2px solid {border_color};
                        border-radius: 30px;
                    }}
                """)
                
                # Reset glow color
                if hasattr(self, 'shadow_effect') and self.shadow_effect:
                    normal_color = QColor()
                    normal_color.setNamedColor(glow_color)
                    self.shadow_effect.setColor(normal_color)
                    
        except Exception as e:
            self.logger.error(f"Error updating notification indicator: {e}")