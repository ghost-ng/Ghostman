"""
File browser bar widget following existing PyQt6 UI patterns.

Displays uploaded files with processing status, progress tracking, and management controls.
Integrates seamlessly with the existing theme system and UI architecture.
"""

import logging, os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QProgressBar, QToolButton, QSizePolicy,
    QMenu, QWidgetAction, QCheckBox, QSpacerItem, QLayout, QLayoutItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QCursor

# Import ColorUtils and theme system for advanced color manipulation
try:
    from ...ui.themes.color_system import ColorUtils
    from ...ui.themes.theme_manager import get_theme_manager, get_theme_primary_color, get_theme_color
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    # Fallback simple color utility
    class ColorUtils:
        @staticmethod
        def lighten(color: str, factor: float = 0.1) -> str:
            return color
        @staticmethod 
        def darken(color: str, factor: float = 0.1) -> str:
            return color
    
    # Fallback helper functions when theme system not available
    def get_theme_primary_color(theme_manager_instance=None):
        return "#ecf0f1"
    
    def get_theme_color(color_name, theme_manager_instance=None, fallback=None):
        fallbacks = {
            'text_primary': '#ecf0f1',
            'text_secondary': '#95a5a6',
            'background_secondary': '#2c3e50',
            'background_primary': '#34495e',
            'border_secondary': '#34495e',
            'primary': '#3498db'
        }
        return fallbacks.get(color_name, fallback or '#ecf0f1')

logger = logging.getLogger("specter.file_browser_bar")


class FlowLayout(QLayout):
    """
    Custom flow layout that automatically wraps widgets to new lines.

    Features:
    - Automatic horizontal flow with wrapping
    - Dynamic reflow on window resize
    - Maintains widget natural sizes
    - Efficient layout calculations
    """

    def __init__(self, parent=None, margin=0, h_spacing=-1, v_spacing=-1):
        super().__init__(parent)

        self._item_list = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

        # Set layout margins
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        """Clean up layout items."""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        """Add item to the layout."""
        self._item_list.append(item)

    def horizontalSpacing(self) -> int:
        """Get horizontal spacing between items."""
        if self._h_spacing >= 0:
            return self._h_spacing
        else:
            return self._smart_spacing(Qt.Orientation.Horizontal)

    def verticalSpacing(self) -> int:
        """Get vertical spacing between items."""
        if self._v_spacing >= 0:
            return self._v_spacing
        else:
            return self._smart_spacing(Qt.Orientation.Vertical)

    def count(self) -> int:
        """Return number of items in layout."""
        return len(self._item_list)

    def itemAt(self, index: int) -> QLayoutItem:
        """Get item at specific index."""
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem:
        """Remove and return item at index."""
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        """Return which directions this layout can expand."""
        return Qt.Orientation(0)  # Don't expand

    def hasHeightForWidth(self) -> bool:
        """Layout height depends on width (for wrapping)."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Calculate required height for given width."""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        """Set layout geometry and position all items."""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        """Calculate preferred size."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Calculate minimum size needed."""
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                     margins.top() + margins.bottom())

        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """
        Perform the actual layout calculation and positioning.

        Args:
            rect: Available rectangle for layout
            test_only: If True, only calculate height without positioning

        Returns:
            Required height for the layout
        """
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        h_spacing = self.horizontalSpacing()
        v_spacing = self.verticalSpacing()

        for item in self._item_list:
            widget = item.widget()

            # Skip invisible widgets
            if widget and not widget.isVisible():
                continue

            space_x = h_spacing
            space_y = v_spacing

            next_x = x + item.sizeHint().width() + space_x

            # Check if we need to wrap to next line
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom

    def _smart_spacing(self, orientation: Qt.Orientation) -> int:
        """Get smart spacing from parent widget style."""
        parent = self.parent()
        if not parent:
            return -1

        if parent.isWidgetType():
            if orientation == Qt.Orientation.Horizontal:
                return parent.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal
                )
            else:
                return parent.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Vertical
                )
        return -1


class FileStatusIndicator(QWidget):
    """Modern status indicator widget for file processing states."""

    def __init__(self, status: str = "pending", theme_manager=None):
        super().__init__()
        self.status = status
        self.theme_manager = theme_manager
        self._animation = None
        self._rotation = 0
        self.setFixedSize(12, 12)  # Smaller for modern pills
        
        # Start animation for processing status
        if status == "processing":
            self._start_animation()
    
    def _start_animation(self):
        """Start rotation animation for processing indicator."""
        # DISABLED: QPropertyAnimation was causing segmentation faults
        # Keep the method but disable animation to prevent crashes
        pass
    
    def _on_rotation_changed(self, value):
        """Handle rotation animation updates."""
        self._rotation = value
        self.update()
    
    def set_status(self, status: str):
        """Update status and animation."""
        if self._animation:
            self._animation.stop()
            self._animation = None
        
        self.status = status
        self._rotation = 0
        
        if status == "processing":
            self._start_animation()
        else:
            self.update()
    
    def _get_theme_color(self, attr_name: str, fallback: str) -> str:
        """Get a color from the current theme with a fallback value."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            return getattr(colors, attr_name, fallback)
        return fallback

    def paintEvent(self, event):
        """Modern status indicators with clean design using theme colors."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = 4  # Smaller radius for modern look

        if self.status == "processing":
            # Modern spinning indicator - minimalist dots
            painter.translate(center)
            painter.rotate(self._rotation)

            processing_color = self._get_theme_color('status_info', '#007bff')
            # Draw 6 dots in a circle
            for i in range(6):
                alpha = 255 - (i * 35)
                color = QColor(processing_color)
                color.setAlpha(max(80, alpha))
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)

                painter.drawEllipse(-1, -radius + 1, 2, 2)
                painter.rotate(60)

        elif self.status == "completed":
            # Modern checkmark - clean and minimal
            success_color = self._get_theme_color('status_success', '#28a745')
            check_text_color = self._get_theme_color('text_primary', '#ffffff')
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(success_color))
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

            # Thicker, cleaner checkmark
            pen = QPainter(self).pen()
            pen.setColor(QColor(check_text_color))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(center.x() - 2, center.y(), center.x() - 1, center.y() + 1)
            painter.drawLine(center.x() - 1, center.y() + 1, center.x() + 2, center.y() - 2)

        elif self.status == "failed":
            # Modern X - clean and minimal
            error_color = self._get_theme_color('status_error', '#dc3545')
            x_text_color = self._get_theme_color('text_primary', '#ffffff')
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(error_color))
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

            # Thicker, cleaner X
            pen = QPainter(self).pen()
            pen.setColor(QColor(x_text_color))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(center.x() - 2, center.y() - 2, center.x() + 2, center.y() + 2)
            painter.drawLine(center.x() - 2, center.y() + 2, center.x() + 2, center.y() - 2)

        elif self.status == "queued":
            # Modern waiting indicator - clean dot
            queued_color = self._get_theme_color('text_disabled', '#6c757d')
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(queued_color))
            painter.drawEllipse(center.x() - 2, center.y() - 2, 4, 4)
    
    def __del__(self):
        """Cleanup animation on destruction."""
        if self._animation:
            self._animation.stop()


class FileContextItem(QFrame):
    """Pill-style file context item widget (Bootstrap pill inspired)."""

    remove_requested = pyqtSignal(str)  # file_id
    view_requested = pyqtSignal(str)    # file_id
    toggle_requested = pyqtSignal(str, bool)  # file_id, enabled
    processing_completed = pyqtSignal(str, str)  # file_id, status (completed/failed)

    def __init__(self, file_id: str, filename: str, file_size: int = 0, file_type: str = "", theme_manager=None, conversation_id: str = None, tab_id: str = None):
        super().__init__()

        # DEBUG: Log constructor parameters
        logger.info(f"🔍 FileContextItem.__init__: file_id={file_id}, conversation_id={conversation_id}, tab_id={tab_id}")
        print(f"🔍 FileContextItem.__init__: file_id={file_id}, conversation_id={conversation_id}, tab_id={tab_id}")

        self.file_id = file_id
        self.filename = filename
        self.file_size = file_size
        self.file_type = file_type
        self.theme_manager = theme_manager
        self.processing_status = "queued"
        self.progress = 0.0
        self.tokens_used = 0
        self.relevance_score = 0.0
        self.is_enabled = True  # Whether file is included in context

        # Error handling attributes
        self.has_error = False
        self.error_message = ""
        self._toggle_disabled = False

        # CRITICAL FIX: Add conversation and tab association
        self.conversation_id = conversation_id
        self.tab_id = tab_id

        # DEBUG: Verify attributes were set
        logger.info(f"🔍 FileContextItem: Set conversation_id={self.conversation_id}, tab_id={self.tab_id}")
        print(f"🔍 FileContextItem: Set conversation_id={self.conversation_id}, tab_id={self.tab_id}")

        self._init_ui()
        self._apply_styling()
        self._setup_toggle_functionality()
        self._setup_tooltips()
    
    def _init_ui(self):
        """Initialize pill-style UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 0, 1, 0)  # Tighter horizontal padding
        layout.setSpacing(1)  # Tighter spacing between elements

        # Status indicator - very compact size
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)  # Smaller size
        self.status_indicator.setText("○")  # Default circle
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: #ff6b35;  /* Orange color for visibility */
                font-size: 12px;  /* Smaller font size */
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignVCenter)

        # File type icon (smaller)
        self.type_label = QLabel()
        self.type_label.setFixedSize(12, 12)
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_type_icon()
        layout.addWidget(self.type_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Filename (main content)
        self.filename_label = QLabel(self._get_pill_name())
        font = self.filename_label.font()
        font.setPointSize(8)  # Increased by 1 for better readability
        font.setBold(False)
        self.filename_label.setFont(font)
        # Remove maximum width constraint - let it size naturally within badge constraints
        # Use Expanding policy to fill available space and prevent clipping
        self.filename_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filename_label.setTextFormat(Qt.TextFormat.PlainText)
        # Note: QLabel doesn't support native eliding, but we handle truncation in _get_pill_name()
        # Add with vertical center alignment for perfect centering
        layout.addWidget(self.filename_label, 1, Qt.AlignmentFlag.AlignVCenter)  # Stretch factor allows it to use available space

        # Remove button (×) - very compact with no border
        self.remove_btn = QToolButton()
        self.remove_btn.setText("×")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.file_id))
        self.remove_btn.setFixedSize(6, 6)  # Very compact size
        # Center the X text within the button
        self.remove_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Use inline stylesheet to force perfect centering with line-height
        self.remove_btn.setStyleSheet("""
            QToolButton {
                padding: 0px;
                margin: -3px 0px 0px 0px;  /* Negative top margin to raise X button higher */
                border: none;
                background-color: transparent;
                color: #ff6b6b;
                font-weight: bold;
                font-size: 12px;
                line-height: 4px;  /* Match button height for vertical centering */
                qproperty-alignment: AlignCenter;
            }
            QToolButton:hover {
                background-color: rgba(255, 107, 107, 0.2);
                color: #ff4444;
                padding: 0px;
                margin: -3px 0px 0px 0px;  /* Keep same margin on hover */
                border-radius: 3px;  /* Smaller radius for tighter hover area */
            }
        """)
        # Add button with vertical center alignment
        layout.addWidget(self.remove_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Set size policy for grid pill layout
        # Use Preferred policy to allow natural sizing within min/max constraints
        # This allows the badge to grow to fit content up to max width
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(20)  # Thinner badge height
        self.setMinimumWidth(150)  # Increased minimum to 150px for better readability
        self.setMaximumWidth(220)  # Increased maximum to prevent clipping

        # No widget margins - spacing handled by CSS margin property
        self.setContentsMargins(0, 0, 0, 0)
        
        
        # Initialize spinner animation
        self._spinner_timer = QTimer()
        self._spinner_timer.timeout.connect(self._update_spinner)
        self._spinner_frame = 0
    
    def _update_type_icon(self):
        """Update the file type icon for pill style."""
        # Simple text-based file type indicators (smaller for pills)
        icon_map = {
            'python': '🐍',
            'javascript': '⚡',
            'typescript': 'TS',
            'java': '☕',
            'cpp': 'C++',
            'html': '🌐',
            'css': '🎨',
            'json': '📋',
            'xml': '📄',
            'csv': '📊',
            'md': '📝',
            'txt': '📄',
            'log': '📜',
            'config': '⚙️'
        }
        
        icon = icon_map.get(self.file_type.lower(), '📄')
        self.type_label.setText(icon)
        
        # Style the icon (smaller for pill)
        font = self.type_label.font()
        font.setPointSize(8)
        self.type_label.setFont(font)
    
    def _get_pill_name(self) -> str:
        """Get pill-style display name with extension."""
        name = self.filename  # Use full filename with extension
        max_length = 18  # Slightly increased to accommodate extensions

        if len(name) <= max_length:
            return name
        else:
            # Truncate from middle to preserve extension
            path = Path(name)
            stem = path.stem
            ext = path.suffix

            # Calculate available space for stem
            available = max_length - len(ext) - 3  # 3 for "..."

            if available > 0:
                return f"{stem[:available]}...{ext}"
            else:
                return f"{name[:max_length-3]}..."
    
    def _get_status_styling(self) -> Dict[str, str]:
        """Get theme-aware badge colors for pill styling, with Bootstrap fallbacks."""
        # Retrieve theme colors if available, otherwise use Bootstrap defaults
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            queued_bg = getattr(colors, 'text_disabled', '#6c757d')
            processing_bg = getattr(colors, 'primary', '#0d6efd')
            success_bg = getattr(colors, 'status_success', '#198754')
            error_bg = getattr(colors, 'status_error', '#dc3545')
            text_color = "#fff"
        else:
            queued_bg = "#6c757d"
            processing_bg = "#0d6efd"
            success_bg = "#198754"
            error_bg = "#dc3545"
            text_color = "#fff"

        status_styles = {
            "queued": {
                "bg_color": queued_bg,
                "hover_bg": ColorUtils.darken(queued_bg, 0.1),
                "text_color": text_color,
                "hover_text": text_color
            },
            "processing": {
                "bg_color": processing_bg,
                "hover_bg": ColorUtils.darken(processing_bg, 0.1),
                "text_color": text_color,
                "hover_text": text_color
            },
            "completed": {
                "bg_color": success_bg,
                "hover_bg": ColorUtils.darken(success_bg, 0.1),
                "text_color": text_color,
                "hover_text": text_color
            },
            "failed": {
                "bg_color": error_bg,
                "hover_bg": ColorUtils.darken(error_bg, 0.1),
                "text_color": text_color,
                "hover_text": text_color
            }
        }

        base_style = status_styles.get(self.processing_status, status_styles["queued"])

        # Modify styling if disabled
        if not self.is_enabled:
            if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                colors = self.theme_manager.current_theme
                disabled_bg = getattr(colors, 'interactive_disabled', '#e9ecef')
                disabled_text = getattr(colors, 'text_disabled', '#6c757d')
            else:
                disabled_bg = "#e9ecef"
                disabled_text = "#6c757d"
            base_style = {
                "bg_color": disabled_bg,
                "hover_bg": ColorUtils.darken(disabled_bg, 0.05),
                "text_color": disabled_text,
                "hover_text": disabled_text
            }

        return base_style
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _calculate_badge_colors(self) -> Dict[str, str]:
        """Calculate theme-aware badge colors with proper contrast."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            
            # Extract theme colors
            bg_primary = colors.background_primary
            bg_secondary = colors.background_secondary
            text_primary = colors.text_primary
            text_secondary = colors.text_secondary
            accent_color = colors.primary
            success_color = getattr(colors, 'success', '#28a745')
            error_color = getattr(colors, 'error', '#dc3545')
            warning_color = getattr(colors, 'warning', '#ffc107')
            
            # Determine if theme is dark
            is_dark = self._is_dark_color(bg_primary)
            
            # Calculate badge colors based on status and theme
            if self.is_enabled:
                if self.processing_status == "completed":
                    base_color = success_color
                    text_color = '#ffffff' if self._is_dark_color(success_color) else '#000000'
                elif self.processing_status == "processing":
                    base_color = accent_color
                    text_color = '#ffffff' if self._is_dark_color(accent_color) else '#000000'
                elif self.processing_status == "failed":
                    base_color = error_color
                    text_color = '#ffffff'
                else:  # queued
                    base_color = ColorUtils.lighten(bg_secondary, 0.1) if is_dark else ColorUtils.darken(bg_secondary, 0.1)
                    text_color = text_primary
                
                opacity = "1.0" if self.processing_status in ["completed", "failed"] else "0.95"
            else:
                # Disabled state
                base_color = ColorUtils.lighten(bg_secondary, 0.2) if is_dark else ColorUtils.darken(bg_secondary, 0.2)
                text_color = text_secondary
                opacity = "0.6"
            
            # Calculate hover states - SUBTLE change to prevent visual expansion
            hover_bg = ColorUtils.lighten(base_color, 0.03)  # Much more subtle - only 3% lighter
            hover_border = ColorUtils.lighten(base_color, 0.08)  # Subtle border highlight
            
            return {
                'background': base_color,
                'text': text_color,
                'border': ColorUtils.darken(base_color, 0.1),
                'hover_bg': hover_bg,
                'hover_border': hover_border,
                'opacity': opacity
            }
        else:
            # Fallback colors
            return self._get_fallback_badge_colors()
    
    def _get_fallback_badge_colors(self) -> Dict[str, str]:
        """Get fallback badge colors when theme manager is not available."""
        status_colors = {
            "completed": ("#28a745", "#ffffff"),
            "processing": ("#007bff", "#ffffff"),
            "failed": ("#dc3545", "#ffffff"),
            "queued": ("#6c757d", "#ffffff")
        }
        
        if self.is_enabled:
            base_color, text_color = status_colors.get(self.processing_status, ("#6c757d", "#ffffff"))
            opacity = "1.0"
        else:
            base_color, text_color = ("#e9ecef", "#6c757d")
            opacity = "0.6"
        
        return {
            'background': base_color,
            'text': text_color,
            'border': ColorUtils.darken(base_color, 0.1),
            'hover_bg': ColorUtils.lighten(base_color, 0.1),
            'hover_border': ColorUtils.lighten(base_color, 0.15),
            'opacity': opacity
        }
    
    def _is_dark_color(self, color_str: str) -> bool:
        """Check if a color is dark based on luminance."""
        try:
            # Remove # if present
            color = color_str.lstrip('#')
            # Convert to RGB
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            # Calculate relative luminance
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except:
            return True  # Default to dark
    
    def _apply_styling(self):
        """Apply modern rounded pill-style theme-aware styling with improved design."""
        # Get badge colors with theme awareness
        badge_colors = self._calculate_badge_colors()
        
        pill_bg = badge_colors['background']
        pill_text = badge_colors['text']
        pill_border = badge_colors['border']
        hover_bg = badge_colors['hover_bg']
        hover_border = badge_colors['hover_border']
        opacity = badge_colors['opacity']
        
        # Modern smooth design with interface designer recommendations
        self.setStyleSheet(f"""
            /* === FILE BADGE STYLING === */
            FileContextItem {{
                /* Badge background - subtle gradient from top to bottom */
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {pill_bg},  /* Top color */
                    stop: 1 {ColorUtils.darken(pill_bg, 0.05)});  /* Bottom slightly darker */

                /* Badge text color */
                color: {pill_text};

                /* Badge border - thin outline around badge */
                border: 1px solid {pill_border};

                /* Badge corner rounding - 10px for smooth pill shape */
                border-radius: 10px;

                /* Badge internal padding - ZERO vertical, asymmetric horizontal */
                /* Less padding on right to bring X button very close to edge */
                padding: 0px 1px 0px 3px;  /* top right bottom left */

                /* Badge external margin - minimal spacing */
                margin: 0px 1px;

                /* Badge transparency - 1.0 = fully opaque, lower = more transparent */
                opacity: {opacity};

                /* Badge text size in pixels */
                font-size: 14px;

                /* Badge text thickness - 500 is medium weight */
                font-weight: 500;

                /* Badge minimum height - matches setFixedHeight(20) */
                min-height: 20px;

                /* Badge maximum height - matches setFixedHeight(20) */
                max-height: 20px;
            }}

            /* === FILE BADGE HOVER STATE === */
            FileContextItem:hover {{
                /* Simple border highlight only - no color or size changes */
                border: 1px solid {hover_border};
            }}

            /* === TEXT LABELS INSIDE BADGE === */
            QLabel {{
                /* Label text color */
                color: {pill_text};

                /* Label background - transparent to show badge background */
                background: transparent;

                /* Label border - no border */
                border: none;

                /* Label inherits font weight from parent badge */
                font-weight: inherit;

                /* Label inherits font size from parent badge */
                font-size: inherit;

                /* Label has no margin */
                margin: 0;

                /* Label has no padding */
                padding: 0;
            }}

            /* === REMOVE BUTTON (X) INSIDE BADGE === */
            /* NOTE: QToolButton styling is handled by inline stylesheet in _init_ui */
            /* Inline stylesheet takes precedence and prevents conflicts */
        """)

        # Force inline stylesheets on labels to override any parent cascade
        self.filename_label.setStyleSheet(
            f"QLabel {{ color: {pill_text}; background: transparent; border: none; "
            f"margin: 0; padding: 0; }}"
        )
        self.type_label.setStyleSheet(
            f"QLabel {{ color: {pill_text}; background: transparent; border: none; "
            f"margin: 0; padding: 0; }}"
        )
    
    def update_status(self, status: str, progress: float = 0.0, already_processed: bool = False):
        """Update processing status and progress."""
        old_status = self.processing_status
        self.processing_status = status
        self.progress = progress
        self._already_processed = already_processed
        
        # Update status indicator with spinner
        self._update_status_indicator(status)
        
        # Reapply styling if status changed
        if old_status != status:
            self._apply_styling()
            
        
        # Animate status change
        if old_status != status:
            self._animate_status_change()
    
    def _update_status_indicator(self, status: str):
        """Update status indicator with spinner animation."""
        if status == "processing":
            # Start spinner animation
            self._spinner_timer.start(80)  # Update every 80ms for smoother animation
            self.status_indicator.setVisible(True)
        elif status in ["completed", "failed"]:
            # Stop spinner and hide indicator
            self._spinner_timer.stop()
            self.status_indicator.setVisible(False)
            # Emit processing completed signal
            self.processing_completed.emit(self.file_id, status)
            logger.info(f"🔄 File processing completed: {self.file_id} - {status}")
        else:
            # Show static indicator for other states (queued, etc.)
            self._spinner_timer.stop()
            self.status_indicator.setText("○")
            self.status_indicator.setVisible(True)
    
    def _update_spinner(self):
        """Update spinner animation frame."""
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]  # Same as repl widget
        self.status_indicator.setText(spinner_chars[self._spinner_frame % len(spinner_chars)])
        self._spinner_frame += 1
    
    def set_usage_info(self, tokens_used: int, relevance_score: float):
        """Update usage information."""
        self.tokens_used = tokens_used
        self.relevance_score = relevance_score
    
    
    def _animate_status_change(self):
        """Animate status change with a subtle effect."""
        # DISABLED: QPropertyAnimation on geometry was causing segmentation faults
        # The animation creates Qt C++ objects that can cause crashes during cleanup
        # Keep method for future non-geometry animations if needed
        pass
    
    def _setup_toggle_functionality(self):
        """Setup click-to-toggle functionality."""
        # Make the pill clickable (except for the remove button)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_tooltips(self):
        """Setup tooltips to show full filename when truncated."""
        # Show full filename if it's truncated
        if len(self.filename) > 18:  # Same max_length as _get_pill_name
            self.setToolTip(self.filename)
        else:
            self.setToolTip("")

    def _update_error_tooltip(self):
        """Update tooltip to show error message when file has error."""
        if self.has_error and self.error_message:
            # Extract meaningful lines from error message (skip generic headers)
            error_lines = self.error_message.split('\n')
            meaningful_lines = []

            # Skip generic headers and collect meaningful content
            for line in error_lines:
                line = line.strip()
                # Skip empty lines and generic headers
                if not line:
                    continue
                if line.startswith('Failed to upload'):
                    continue
                if line.startswith('Error:') and len(line) < 20:  # Generic "Error: X" lines
                    continue
                if line.startswith('If this persists'):
                    break  # Stop at the "If this persists" section

                # Add meaningful lines
                if line:
                    meaningful_lines.append(line)

            # Build error summary (first 2-3 meaningful lines)
            if meaningful_lines:
                error_summary = '\n'.join(meaningful_lines[:3])
            else:
                error_summary = "File processing failed"

            # Build tooltip
            if len(self.filename) > 18:
                # Truncated filename + error
                error_tooltip = f"📄 {self.filename}\n\n❌ {error_summary}"
            else:
                # Just error (filename visible in badge)
                error_tooltip = f"❌ {error_summary}"

            self.setToolTip(error_tooltip)
        elif len(self.filename) > 18:
            self.setToolTip(self.filename)
        else:
            self.setToolTip("")

    def _disable_toggle(self):
        """Disable toggle functionality when file has error."""
        self._toggle_disabled = True
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def set_error(self, error_message: str):
        """Set error state for this file and disable toggling."""
        self.has_error = True
        self.error_message = error_message
        self.processing_status = "failed"
        self._disable_toggle()
        self._update_error_tooltip()
        self._apply_styling()
        logger.info(f"File {self.file_id} set to error state: {error_message}")

    def clear_error(self):
        """Clear error state for this file."""
        self.has_error = False
        self.error_message = ""
        self._toggle_disabled = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._setup_tooltips()
        self._apply_styling()
        logger.info(f"File {self.file_id} error state cleared")

    def toggle_enabled(self):
        """Toggle the enabled state of this file."""
        # Don't allow toggling if disabled due to error
        if self._toggle_disabled:
            return
        self.is_enabled = not self.is_enabled
        self._apply_styling()
        self.toggle_requested.emit(self.file_id, self.is_enabled)
    
    def set_enabled(self, enabled: bool):
        """Set the enabled state of this file."""
        if self.is_enabled != enabled:
            self.is_enabled = enabled
            self._apply_styling()
    
    def mousePressEvent(self, event):
        """Handle mouse press events for toggling."""
        # Only toggle on left click and not on the remove button
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click was on the remove button area
            remove_btn_rect = self.remove_btn.geometry()

            # Only toggle if not clicking on remove button
            if not remove_btn_rect.contains(event.position().toPoint()):
                self.toggle_enabled()
        super().mousePressEvent(event)


class FileBrowserBar(QFrame):
    """
    File browser bar showing uploaded files with processing status and controls.
    
    Features:
    - Displays file contexts with status indicators
    - Processing progress tracking
    - File management controls
    - Theme-aware styling
    - Context menus and bulk operations
    - Smooth animations and transitions
    """
    
    # Signals
    file_removed = pyqtSignal(str)  # file_id
    file_viewed = pyqtSignal(str)   # file_id
    file_toggled = pyqtSignal(str, bool)  # file_id, enabled
    clear_all_requested = pyqtSignal()
    files_reordered = pyqtSignal(list)  # list of file_ids in new order
    upload_files_requested = pyqtSignal()  # Request file upload dialog
    hide_requested = pyqtSignal()  # Request to hide the file browser toolbar
    processing_completed = pyqtSignal(str, str)  # file_id, status (completed/failed) - propagated from FileContextItem
    
    def __init__(self, theme_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.file_items: Dict[str, FileContextItem] = {}
        self.max_visible_files = 20  # More files in grid
        self._animation = None

        self.setVisible(False)  # Initially hidden

        # Set flexible size constraints for file badges
        self.setMinimumHeight(60)  # Minimum to show header + 1 row of compact badges
        self.setMaximumHeight(300)  # Maximum height before scroll (allows ~6 rows of badges)
        self.setMinimumWidth(300)  # Ensure enough width to display badges without clipping
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self._init_ui()
        self._apply_styling()
        self._connect_signals()
        
        # Force refresh of label colors after all initialization
        self._refresh_label_colors()
        
        # Load button icons after UI is fully initialized
        self._load_upload_icon_for_button()
        self._load_clear_icon()
        
        logger.debug("FileBrowserBar initialized")
    
    def _init_ui(self):
        """Initialize the UI components."""
        logger.info("🔧 FB_INIT: Initializing FileBrowserBar UI...")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 2, 8, 4)  # Minimal top margin, compact bottom
        main_layout.setSpacing(0)  # No spacing between header and badges

        # Header section
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 0, 4, 0)  # No top or bottom margin
        header_layout.setSpacing(6)  # Reduced spacing for better alignment
        
        # Status summary (compact, inline with title)
        self.status_label = QLabel("No files loaded")
        self.status_label.setObjectName("status_label")
        status_color = get_theme_primary_color(self.theme_manager)
        from PyQt6.QtGui import QPalette, QColor
        palette = self.status_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(status_color))
        self.status_label.setPalette(palette)
        status_font = self.status_label.font()
        status_font.setPointSize(8)
        self.status_label.setFont(status_font)
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()
        
        # Upload files button with icon (QToolButton for consistency)
        logger.info("🔧 FB_INIT: Creating upload button...")
        self.upload_files_btn = QToolButton()
        logger.info(f"🔧 FB_INIT: Upload button created: {self.upload_files_btn}")

        # Load icon using the theme-aware method (avoid duplicate loading)
        logger.info("🔧 FB_INIT: Setting up icon loading...")
        # The icon will be loaded by _load_upload_icon_for_button() after UI init

        self.upload_files_btn.setToolTip("Open file dialog to select files for context")
        self.upload_files_btn.clicked.connect(self._on_upload_files_clicked)
        self.upload_files_btn.setFixedSize(32, 32)  # Initial size, updated by update_button_sizes()
        header_layout.addWidget(self.upload_files_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        logger.info("🔧 FB_INIT: Upload button added to layout")

        # Clear all button with icon
        self.clear_all_btn = QToolButton()
        self.clear_all_btn.setToolTip("Clear all files")
        self.clear_all_btn.clicked.connect(self.clear_all_requested.emit)
        self.clear_all_btn.setFixedSize(32, 32)  # Initial size, updated by update_button_sizes()
        # Icon will be loaded in _load_clear_icon() after UI init
        header_layout.addWidget(self.clear_all_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Minimize button — hides the file browser toolbar (same as toggle)
        self.minimize_btn = QToolButton()
        self.minimize_btn.setText("▁")
        self.minimize_btn.setToolTip("Minimize file browser")
        self.minimize_btn.clicked.connect(self._hide_toolbar)
        self.minimize_btn.setFixedSize(32, 32)  # Initial size, updated by update_button_sizes()
        header_layout.addWidget(self.minimize_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Track header buttons for uniform sizing
        self._header_buttons = [self.upload_files_btn, self.clear_all_btn, self.minimize_btn]
        
        main_layout.addWidget(header_frame)
        
        # Files section (grid layout pills)
        self.files_frame = QFrame()
        files_layout = QVBoxLayout(self.files_frame)
        files_layout.setContentsMargins(8, 0, 8, 4)  # No top margin, bottom margin to prevent badge cutoff
        files_layout.setSpacing(0)  # No spacing between elements
        
        # Container for Bootstrap-style pills with FlowLayout
        self.pills_container = QWidget()
        self.pills_container.setObjectName("pills_container")

        # Use FlowLayout for automatic wrapping
        self.pills_flow = FlowLayout(self.pills_container, margin=0, h_spacing=4, v_spacing=4)

        # Wrap pills container in scroll area for overflow handling
        pills_scroll = QScrollArea()
        pills_scroll.setWidget(self.pills_container)
        pills_scroll.setWidgetResizable(True)
        # Enable horizontal scrollbar to prevent forced compression when parent is narrow
        pills_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        pills_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        pills_scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Set transparent background for scroll area and container
        pills_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        self.pills_container.setStyleSheet("QWidget#pills_container { background-color: transparent; }")

        files_layout.addWidget(pills_scroll)
        main_layout.addWidget(self.files_frame)
    
    def _apply_styling(self):
        """Apply theme-aware styling using optimized helper functions."""
        logger.info(f"🎨 FileBrowserBar _apply_styling called")
        
        # Use optimized helper functions for consistent color retrieval
        bg_color = get_theme_color('background_secondary', self.theme_manager)
        bg_primary = get_theme_color('background_primary', self.theme_manager)
        text_color = get_theme_color('text_primary', self.theme_manager)
        text_secondary = get_theme_color('text_secondary', self.theme_manager)
        border_color = get_theme_color('border_secondary', self.theme_manager)
        accent_color = get_theme_color('primary', self.theme_manager)
        
        logger.info(f"🎨 Retrieved colors - text_primary: {text_color}, bg: {bg_color}, accent: {accent_color}")
        
        self.setStyleSheet(f"""
            /* === MAIN FILE BROWSER CONTAINER === */
            FileBrowserBar {{
                /* Container background - subtle gradient from top to bottom */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_color}, stop:1 {ColorUtils.darken(bg_color, 0.1)});

                /* Container border - thin outline around entire browser */
                border: 1px solid {ColorUtils.lighten(border_color, 0.2)};

                /* Container corner rounding */
                border-radius: 4px;

                /* Container external margin - space outside file browser */
                margin: 0px;

                /* Container internal padding - space inside container walls */
                padding: 12px;  /* General padding */
                padding-top: 8px;  /* Top padding (above "Attachments" title) */
                padding-bottom: 16px;  /* Bottom padding (below status line) */

                /* Container minimum height */
                min-height: 60px;

                /* Container maximum height */
                max-height: 120px;
            }}

            /* === FRAME ELEMENTS (internal containers) === */
            QFrame {{
                /* All internal frames are transparent */
                background-color: transparent;

                /* All internal frames have no border */
                border: none;
            }}

            /* === DIRECT CHILD TEXT LABELS ONLY (scoped to avoid badge override) === */
            FileBrowserBar > QFrame > QLabel, FileBrowserBar > QLabel {{
                /* Default label text color */
                color: {text_color};

                /* Default label background - transparent */
                background: transparent;

                /* Default label border - none */
                border: none;

                /* Default label text weight */
                font-weight: 500;
            }}

            /* === STATUS LINE TEXT ("1 file" or "No files loaded") === */
            QLabel#status_label {{
                /* Status text color */
                color: {text_color};
            }}

            /* title_label removed — status_label is now in header */
            /* === PUSH BUTTONS (generic fallback, not used) === */
            QPushButton {{
                /* Button background gradient */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {accent_color}, stop:1 {ColorUtils.darken(accent_color, 0.15)});

                /* Button text color */
                color: white;

                /* Button border - none */
                border: none;

                /* Button corner rounding */
                border-radius: 8px;

                /* Button internal padding */
                padding: 6px 12px;

                /* Button text size */
                font-size: 10px;

                /* Button text weight */
                font-weight: 600;
            }}

            /* === PUSH BUTTON HOVER STATE === */
            QPushButton:hover {{
                /* Hover background - lighter gradient */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {ColorUtils.lighten(accent_color, 0.1)},
                    stop:1 {ColorUtils.darken(accent_color, 0.05)});
            }}

            /* === PUSH BUTTON PRESSED STATE === */
            QPushButton:pressed {{
                /* Pressed background - darker */
                background: {ColorUtils.darken(accent_color, 0.2)};
            }}

            /* === UPLOAD & CLEAR BUTTONS (QToolButton in header) === */
            QToolButton {{
                /* Button background - subtle transparent white */
                background-color: rgba(255,255,255,0.1);

                /* Button border - very subtle outline */
                border: 1px solid rgba(255,255,255,0.15);

                /* Button corner rounding */
                border-radius: 4px;

                /* Button icon/text color */
                color: {text_color};

                /* Button icon size */
                font-size: 12px;

                /* Button minimum width */
                min-width: 28px;

                /* Button minimum height */
                min-height: 28px;

                /* Button maximum width */
                max-width: 32px;

                /* Button maximum height */
                max-height: 32px;

                /* Button internal padding */
                padding: 2px;
            }}

            /* === UPLOAD & CLEAR BUTTONS HOVER STATE === */
            QToolButton:hover {{
                /* Hover background - accent color highlight */
                background-color: {accent_color};

                /* Hover border - accent color */
                border-color: {accent_color};

                /* Hover text/icon - white for contrast */
                color: white;
            }}

            /* === UPLOAD & CLEAR BUTTONS PRESSED STATE === */
            QToolButton:pressed {{
                /* Pressed background - darker accent */
                background-color: {ColorUtils.darken(accent_color, 0.2)};

                /* Pressed border - darker accent */
                border-color: {ColorUtils.darken(accent_color, 0.2)};
            }}
            /* === SCROLL AREA (for file badges overflow) === */
            QScrollArea {{
                /* Scroll area background - transparent */
                background-color: transparent;

                /* Scroll area border - very subtle outline */
                border: 1px solid rgba(255,255,255,0.1);

                /* Scroll area corner rounding */
                border-radius: 8px;
            }}

            /* === HORIZONTAL SCROLLBAR TRACK === */
            QScrollBar:horizontal {{
                /* Scrollbar track background */
                background-color: rgba(255,255,255,0.05);

                /* Scrollbar track height */
                height: 8px;

                /* Scrollbar track corner rounding */
                border-radius: 4px;

                /* Scrollbar track margin */
                margin: 0;
            }}

            /* === HORIZONTAL SCROLLBAR HANDLE (draggable part) === */
            QScrollBar::handle:horizontal {{
                /* Scrollbar handle color */
                background-color: {accent_color};

                /* Scrollbar handle corner rounding */
                border-radius: 4px;

                /* Scrollbar handle minimum width */
                min-width: 20px;
            }}

            /* === HORIZONTAL SCROLLBAR HANDLE HOVER STATE === */
            QScrollBar::handle:horizontal:hover {{
                /* Hover handle color - lighter */
                background-color: {ColorUtils.lighten(accent_color, 0.2)};
            }}

            /* === HORIZONTAL SCROLLBAR ARROWS (hidden) === */
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                /* Hide scrollbar arrows */
                border: none;
                background: none;
                width: 0px;
            }}
        """)
        
        # Apply theme colors to labels using helper functions for consistency
        if hasattr(self, 'status_label'):
            self.status_label.setObjectName("status_label")
            self.status_label.setStyleSheet(f"color: {text_color};")  # Use primary text color
            logger.info(f"🎨 Applied status_label stylesheet: color: {text_color};")
    def _connect_signals(self):
        """Connect internal signals."""
        if self.theme_manager:
            # Connect to theme changes
            if hasattr(self.theme_manager, 'theme_changed'):
                self.theme_manager.theme_changed.connect(self._on_theme_changed)
    
    def _refresh_label_colors(self):
        """Force refresh label colors using QPalette approach."""
        try:
            logger.info("🎨 Force refreshing label colors...")
            
            # Get the primary text color using helper function
            text_color = get_theme_primary_color(self.theme_manager)
            logger.info(f"🎨 Retrieved primary text color: {text_color}")
            
            from PyQt6.QtGui import QPalette, QColor
            
            # Apply to status label using QPalette
            if hasattr(self, 'status_label') and self.status_label:
                palette = self.status_label.palette()
                palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))
                self.status_label.setPalette(palette)
                logger.info(f"🎨 Applied theme color to status_label via QPalette: {text_color}")
                
        except Exception as e:
            logger.error(f"Error refreshing label colors: {e}")
    
    def _get_icon_variant(self) -> str:
        """Determine which icon variant to use based on theme - EXACT COPY from REPL widget."""
        try:
            if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                colors = self.theme_manager.current_theme
                # Check if background is dark or light
                bg_color = colors.background_primary
                # Simple heuristic: if background starts with #0-#7, it's dark
                if bg_color.startswith('#') and len(bg_color) >= 2:
                    first_hex_digit = int(bg_color[1], 16)
                    return "lite" if first_hex_digit <= 7 else "dark"
            
            # Default fallback
            return "lite"
            
        except Exception as e:
            logger.error(f"Failed to determine icon variant: {e}")
            return "lite"
    
    def _is_theme_dark(self) -> bool:
        """Determine if current theme is dark."""
        try:
            if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                colors = self.theme_manager.current_theme
                bg_color = colors.background_primary
                
                # Parse hex color to determine brightness
                bg_color = bg_color.lstrip('#')
                r = int(bg_color[0:2], 16)
                g = int(bg_color[2:4], 16)
                b = int(bg_color[4:6], 16)
                
                # Calculate perceived brightness
                brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                
                # Return True if dark (low brightness)
                return brightness < 0.5
            else:
                # Default to dark theme
                return True
        except Exception as e:
            logger.debug(f"Failed to determine theme darkness: {e}")
            return True  # Default fallback
    
    def _load_upload_icon_for_button(self):
        """Load theme-appropriate upload icon - EXACT COPY of REPL icon loading pattern."""
        logger.info("🎨 FB_ICON: Loading upload icon for file browser button...")
        try:
            # Check button exists
            if not hasattr(self, 'upload_files_btn'):
                logger.error("❌ FB_ICON: upload_files_btn doesn't exist yet!")
                return
                
            from ...utils.resource_resolver import resolve_icon
            variant = self._get_icon_variant()

            upload_icon_path = resolve_icon("upload", variant)

            if upload_icon_path and upload_icon_path.exists():
                upload_icon = QIcon(str(upload_icon_path))
                if not upload_icon.isNull():
                    self.upload_files_btn.setIcon(upload_icon)
                    from PyQt6.QtCore import QSize
                    self.upload_files_btn.setIconSize(QSize(16, 16))
                    logger.debug(f"Loaded upload icon: upload_{variant}.png")
            else:
                logger.warning(f"Upload icon not found for variant: {variant}")
                
        except Exception as e:
            logger.error(f"❌ FB_ICON: Exception loading upload icon: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_clear_icon(self):
        """Load theme-appropriate clear icon for the clear button."""
        logger.info("🎨 FB_ICON: Loading clear icon for clear button...")
        try:
            # Check button exists
            if not hasattr(self, 'clear_all_btn'):
                logger.error("❌ FB_ICON: clear_all_btn doesn't exist yet!")
                return
                
            from ...utils.resource_resolver import resolve_icon
            variant = self._get_icon_variant()

            clear_icon_path = resolve_icon("clear", variant)

            if clear_icon_path and clear_icon_path.exists():
                clear_icon = QIcon(str(clear_icon_path))
                if not clear_icon.isNull():
                    self.clear_all_btn.setIcon(clear_icon)
                    from PyQt6.QtCore import QSize
                    self.clear_all_btn.setIconSize(QSize(16, 16))
                    logger.debug(f"Loaded clear icon: clear_{variant}.png")
                else:
                    self.clear_all_btn.setText("Clear")
            else:
                self.clear_all_btn.setText("Clear")
                logger.warning(f"Clear icon not found for variant: {variant}")

        except Exception as e:
            logger.error(f"Failed to load clear icon: {e}")
            self.clear_all_btn.setText("Clear")
    
    def _hide_toolbar(self):
        """Request the parent to hide the file browser stack. Files remain tracked."""
        self.hide_requested.emit()

    def update_button_sizes(self):
        """Update header button sizes to match the toolbar's dynamic sizing.

        Uses the same formula as REPLWidget._auto_size_button_row():
          scale = 0.6 + (slider-1) * 0.8/9
          icon_size = slider * 3 + 1
        """
        try:
            from ...infrastructure.storage.settings_manager import settings
            from PyQt6.QtCore import QSize

            user_slider = settings.get('interface.icon_size', 5)
            user_slider = max(1, min(10, int(user_slider)))

            scale = 0.6 + (user_slider - 1) * (0.8 / 9)
            ideal = 28  # same ideal as toolbar
            btn_size = max(16, int(ideal * scale))
            icon_size = user_slider * 3 + 1

            for btn in getattr(self, '_header_buttons', []):
                btn.setFixedSize(btn_size, btn_size)
                btn.setIconSize(QSize(icon_size, icon_size))

            logger.debug(f"File browser buttons sized to {btn_size}px (icon {icon_size}px, slider {user_slider})")
        except Exception as e:
            logger.debug(f"update_button_sizes error: {e}")

    def _on_theme_changed(self, new_theme=None):
        """Handle theme changes."""
        self._apply_styling()
        self._refresh_label_colors()
        # Update upload button icon for new theme
        if hasattr(self, 'upload_files_btn'):
            self._load_upload_icon_for_button()
        # Update clear button icon for new theme
        if hasattr(self, 'clear_all_btn'):
            self._load_clear_icon()
        # Update all file items
        for item in self.file_items.values():
            item._apply_styling()
    
    # _toggle_expansion method removed as expand/collapse button was removed
    def _show_settings_menu(self):
        """Show settings context menu."""
        menu = QMenu(self)
        
        # Auto-remove options
        auto_remove_action = QAction("Auto-remove inactive files", self)
        auto_remove_action.setCheckable(True)
        # TODO: Connect to settings
        menu.addAction(auto_remove_action)
        
        menu.addSeparator()
        
        # View options
        compact_view_action = QAction("Compact view", self)
        compact_view_action.setCheckable(True)
        menu.addAction(compact_view_action)
        
        show_details_action = QAction("Show file details", self)
        show_details_action.setCheckable(True)
        show_details_action.setChecked(True)
        menu.addAction(show_details_action)
        
        menu.addSeparator()
        
        # Export options
        export_action = QAction("Export file list...", self)
        menu.addAction(export_action)
        
        menu.exec(QCursor.pos())
    
    def _on_upload_files_clicked(self):
        """Handle upload files button click - emit signal for parent to handle."""
        try:
            logger.debug("Upload Files button clicked in FileBrowserBar")
            self.upload_files_requested.emit()
        except Exception as e:
            logger.error(f"Failed to handle upload files button click: {e}")
    
    def add_file(self, file_id: str, filename: str, file_size: int = 0, file_type: str = "", status: str = "queued", conversation_id: str = None, tab_id: str = None):
        """Add a file to the browser bar with conversation and tab association."""
        logger.info(f"🔍 ADD_FILE DEBUG: file_id={file_id}, conversation_id={conversation_id}, tab_id={tab_id}")
        print(f"🔍 ADD_FILE DEBUG: file_id={file_id}, conversation_id={conversation_id}, tab_id={tab_id}")
        
        if file_id in self.file_items:
            # Update existing item
            item = self.file_items[file_id]
            item.update_status(status)
            # Update conversation/tab association if provided
            if conversation_id:
                item.conversation_id = conversation_id
                logger.info(f"🔍 ADD_FILE: Updated existing file {file_id} conversation_id to {conversation_id}")
            if tab_id:
                item.tab_id = tab_id
                logger.info(f"🔍 ADD_FILE: Updated existing file {file_id} tab_id to {tab_id}")
            return
        
        # Create new file item with conversation and tab association
        logger.info(f"🔍 ADD_FILE: Creating NEW FileContextItem with tab_id={tab_id}")
        print(f"🔍 ADD_FILE: Creating NEW FileContextItem with tab_id={tab_id}")
        
        item = FileContextItem(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            theme_manager=self.theme_manager,
            conversation_id=conversation_id,
            tab_id=tab_id
        )
        
        # Verify the tab_id was set correctly
        logger.info(f"🔍 ADD_FILE: Created file item - actual tab_id: {getattr(item, 'tab_id', 'NOT SET')}")
        print(f"🔍 ADD_FILE: Created file item - actual tab_id: {getattr(item, 'tab_id', 'NOT SET')}")
        
        # Connect signals
        item.remove_requested.connect(self._on_file_remove_requested)
        item.view_requested.connect(self.file_viewed.emit)
        item.toggle_requested.connect(self.file_toggled.emit)
        item.processing_completed.connect(self._on_file_processing_completed)

        # Add to flow layout - simple one-line addition
        self.pills_flow.addWidget(item)
        self.file_items[file_id] = item
        
        # Update status
        item.update_status(status)
        
        # Show the bar if it was hidden
        if not self.isVisible():
            self.setVisible(True)
        
        self._update_status_display()
        logger.debug(f"Added file item: {file_id} ({filename})")
    
    def _on_file_remove_requested(self, file_id: str):
        """Handle file removal request."""
        self.remove_file(file_id)
        self.file_removed.emit(file_id)

    def _on_file_processing_completed(self, file_id: str, status: str):
        """Handle file processing completion - hide spinner and propagate signal."""
        logger.info(f"🔄 _on_file_processing_completed called: {file_id} - {status}")
        if file_id in self.file_items:
            item = self.file_items[file_id]
            item.status_indicator.setVisible(False)
            logger.info(f"✅ Successfully hid spinner for file: {file_id}")
        else:
            logger.warning(f"❌ File item not found for processing completion: {file_id}")
            logger.info(f"Available file IDs: {list(self.file_items.keys())}")

        # Propagate signal to parent widgets (e.g., REPLWidget for RAG refresh)
        logger.info(f"📡 Propagating processing_completed signal for {file_id[:8]} - {status}")
        self.processing_completed.emit(file_id, status)
    
    def remove_file(self, file_id: str):
        """Remove a file from the browser."""
        if file_id in self.file_items:
            item = self.file_items[file_id]

            # Remove from parent layout
            parent = item.parent()
            if parent:
                parent.layout().removeWidget(item)
            item.deleteLater()
            del self.file_items[file_id]

            # Rebuild grid layout to fix spacing
            self._rebuild_grid_layout()

            # Don't hide the entire widget - keep header and buttons visible
            # so users can still upload new files
            # The files section will just show "No files loaded" status

            self._update_status_display()
            logger.debug(f"Removed file item: {file_id}")
    
    def update_file_status(self, file_id: str, status: str, progress: float = 0.0) -> str:
        """
        Update file processing status.

        Returns:
            The actual file_id used (may differ from input if filename match was used)
        """
        logger.info(f"🔍 DEBUG: update_file_status called - file_id: {file_id}, status: {status}")
        logger.info(f"🔍 DEBUG: Available file IDs: {list(self.file_items.keys())}")
        try:
            if file_id in self.file_items:
                logger.info(f"🔍 DEBUG: Found file item for {file_id}")
                self.file_items[file_id].update_status(status, progress)
                logger.info(f"🔍 DEBUG: Updated status for {file_id}")
                self._update_status_display()
                logger.info(f"🔍 DEBUG: Updated status display for {file_id}")
                return file_id
            else:
                logger.warning(f"🔍 DEBUG: File item not found for {file_id}")
                logger.info(f"🔍 DEBUG: Trying to find by filename match...")
                # Try to find by filename if file_id doesn't match
                for item_id, item in self.file_items.items():
                    if item.filename == file_id or file_id.endswith(item.filename):
                        logger.info(f"🔍 DEBUG: Found match by filename: {item_id} -> {item.filename}")
                        item.update_status(status, progress)
                        self._update_status_display()
                        return item_id  # Return the actual file_id
                logger.warning(f"🔍 DEBUG: No filename match found either")
                return file_id  # Return original if not found
        except Exception as e:
            logger.error(f"🔍 DEBUG: Exception in update_file_status: {e}")
            raise
    
    def update_file_usage(self, file_id: str, tokens_used: int, relevance_score: float):
        """Update file usage information."""
        logger.info(f"🔍 DEBUG: update_file_usage called - file_id: {file_id}, tokens: {tokens_used}")
        try:
            if file_id in self.file_items:
                logger.info(f"🔍 DEBUG: Found file item for usage update {file_id}")
                self.file_items[file_id].set_usage_info(tokens_used, relevance_score)
                logger.info(f"🔍 DEBUG: Set usage info for {file_id}")
            else:
                logger.info(f"🔍 DEBUG: File item not found for usage update {file_id}")
        except Exception as e:
            logger.error(f"🔍 DEBUG: Exception in update_file_usage: {e}")
            raise
    
    def clear_all_files(self):
        """Clear all files from the browser."""
        for file_id in list(self.file_items.keys()):
            self.remove_file(file_id)
        # Don't hide the entire widget - remove_file() will handle visibility
        # when the last file is removed
        logger.debug("Cleared all file items")
    
    def hide_files_for_conversation(self, conversation_id: str):
        """Hide files that belong to a specific conversation."""
        visible_count = 0
        for item in self.file_items.values():
            if item.conversation_id == conversation_id:
                item.setVisible(False)
            else:
                if item.isVisible():
                    visible_count += 1
        
        # Hide the entire bar if no files are visible
        if visible_count == 0:
            self.setVisible(False)
        
        logger.debug(f"Hidden files for conversation {conversation_id[:8]}...")
    
    def show_files_for_conversation(self, conversation_id: str):
        """Show only files that belong to a specific conversation."""
        logger.debug(f"🔍 DEBUG: show_files_for_conversation called for {conversation_id[:8]}...")
        logger.debug(f"🔍 DEBUG: Total file_items: {len(self.file_items)}")
        
        visible_count = 0
        for file_id, item in self.file_items.items():
            logger.debug(f"🔍 DEBUG: File {file_id} has conversation_id: {getattr(item, 'conversation_id', 'NO ATTRIBUTE')}")
            
            if item.conversation_id == conversation_id:
                item.setVisible(True)
                visible_count += 1
                logger.debug(f"🔍 DEBUG: Showing file {file_id} (matches conversation)")
            else:
                item.setVisible(False)
                logger.debug(f"🔍 DEBUG: Hiding file {file_id} (different conversation: {getattr(item, 'conversation_id', 'None')})")
        
        # Show the entire bar if any files are visible
        if visible_count > 0:
            self.setVisible(True)
            logger.debug(f"Showing {visible_count} files for conversation {conversation_id[:8]}...")
        else:
            self.setVisible(False)
            logger.debug(f"No files found for conversation {conversation_id[:8]}...")
    
    def hide_all_files(self):
        """Hide all files without removing them."""
        for item in self.file_items.values():
            item.setVisible(False)
        self.setVisible(False)
        logger.debug("Hidden all file items")
    
    def get_files_for_conversation(self, conversation_id: str) -> list:
        """Get list of file IDs for a specific conversation."""
        files = [file_id for file_id, item in self.file_items.items() 
                if item.conversation_id == conversation_id]
        logger.debug(f"🔍 get_files_for_conversation({conversation_id[:8] if conversation_id else 'None'}): Found {len(files)} files")
        return files
    
    def get_files_for_tab(self, tab_id: str) -> list:
        """Get list of file IDs for a specific tab."""
        files = [file_id for file_id, item in self.file_items.items() 
                if getattr(item, 'tab_id', None) == tab_id]
        logger.debug(f"🔍 get_files_for_tab({tab_id}): Found {len(files)} files")
        return files
    
    def show_files_for_tab(self, tab_id: str):
        """Show only files that belong to a specific tab."""
        logger.info(f"🔍 show_files_for_tab called for tab {tab_id}")
        
        visible_count = 0
        for file_id, item in self.file_items.items():
            if getattr(item, 'tab_id', None) == tab_id:
                item.setVisible(True)
                visible_count += 1
                logger.debug(f"✅ Showing file {file_id} for tab {tab_id}")
            else:
                item.setVisible(False)
        
        # Show the entire bar if any files are visible
        if visible_count > 0:
            self.setVisible(True)
            logger.info(f"📁 Showing {visible_count} files for tab {tab_id}")
        else:
            self.setVisible(False)
            logger.info(f"📁 No files found for tab {tab_id}")
    
    def count_files_for_tab(self, tab_id: str) -> int:
        """Count files associated with a specific tab."""
        count = len([item for item in self.file_items.values() 
                    if getattr(item, 'tab_id', None) == tab_id])
        logger.debug(f"🔢 Tab {tab_id} has {count} files")
        return count
    
    def set_file_enabled(self, file_id: str, enabled: bool):
        """Set the enabled state of a specific file."""
        try:
            if file_id in self.file_items:
                file_item = self.file_items[file_id]
                file_item.is_enabled = enabled
                file_item._apply_styling()
                logger.debug(f"Updated file {file_id} enabled state to {enabled}")
                return True
            else:
                logger.warning(f"File {file_id} not found in browser bar for enabled state update")
                return False
            
        except Exception as e:
            logger.error(f"Failed to set file enabled state: {e}")
            return False
    
    def get_file_count(self) -> int:
        """Get the number of files currently displayed."""
        return len(self.file_items)
    
    def append_file(self, file_path: str, filename: str, **kwargs):
        """Add a file to the existing files (append mode)."""
        return self.add_file(file_path, filename, **kwargs)
    
    def _update_status_display(self):
        """Update the status display."""
        logger.info("🔍 DEBUG: _update_status_display called")
        total_files = len(self.file_items)
        
        if total_files == 0:
            status_text = "No files loaded"
        else:
            # Count by status
            status_counts = {}
            total_tokens = 0
            
            for item in self.file_items.values():
                status = item.processing_status
                status_counts[status] = status_counts.get(status, 0) + 1
                total_tokens += item.tokens_used
            
            status_parts = []
            if total_files == 1:
                status_parts.append("1 file")
            else:
                status_parts.append(f"{total_files} files")
            
            if total_tokens > 0:
                status_parts.append(f"{total_tokens} tokens")
            
            # Add processing info
            processing_count = status_counts.get("processing", 0)
            if processing_count > 0:
                status_parts.append(f"{processing_count} processing")
            
            status_text = " • ".join(status_parts)
        
        # Status label now lives in header row — prefix with icon
        if total_files > 0:
            self.status_label.setText(f"📁 {status_text}")
        else:
            self.status_label.setText("📁 No files")
    
    def has_files(self) -> bool:
        """Check if any files are present."""
        return len(self.file_items) > 0
    
    def get_file_count(self) -> int:
        """Get number of files."""
        return len(self.file_items)
    
    def get_file_ids(self) -> List[str]:
        """Get list of file IDs in current order."""
        return list(self.file_items.keys())
    
    def set_max_visible_files(self, max_files: int):
        """Set maximum number of visible files."""
        self.max_visible_files = max_files
        # TODO: Implement pagination or scrolling if needed
    
    def get_processing_files(self) -> List[str]:
        """Get list of files currently being processed."""
        return [
            file_id for file_id, item in self.file_items.items()
            if item.processing_status == "processing"
        ]
    
    def get_completed_files(self) -> List[str]:
        """Get list of successfully processed files."""
        return [
            file_id for file_id, item in self.file_items.items()
            if item.processing_status == "completed"
        ]
    
    def get_all_files_info(self) -> List[Dict[str, any]]:
        """Get detailed information about all files in the browser."""
        file_info_list = []
        for file_id, item in self.file_items.items():
            file_info_list.append({
                'file_id': file_id,
                'filename': item.filename,
                'file_size': item.file_size,
                'file_type': item.file_type,
                'processing_status': item.processing_status,
                'is_enabled': item.is_enabled,
                'tokens_used': item.tokens_used,
                'relevance_score': item.relevance_score
            })
        return file_info_list
    
    def get_enabled_files_info(self) -> List[Dict[str, any]]:
        """Get detailed information about only enabled files in the browser."""
        return [
            {
                'file_id': file_id,
                'filename': item.filename,
                'file_size': item.file_size,
                'file_type': item.file_type,
                'processing_status': item.processing_status,
                'is_enabled': item.is_enabled,
                'tokens_used': item.tokens_used,
                'relevance_score': item.relevance_score
            }
            for file_id, item in self.file_items.items()
            if item.is_enabled
        ]
    
    def _rebuild_grid_layout(self):
        """Rebuild the flow layout after item removal."""
        # Clear current layout
        while self.pills_flow.count() > 0:
            item = self.pills_flow.takeAt(0)
            if item and item.widget():
                # Don't delete the widget, just remove from layout
                pass

        # Re-add all items to flow layout
        for file_id, item in self.file_items.items():
            self.pills_flow.addWidget(item)

    def resizeEvent(self, event):
        """Handle resize events to trigger layout reflow and update tooltips."""
        super().resizeEvent(event)
        # FlowLayout automatically handles reflow, but we update tooltips
        # in case filename truncation needs adjustment
        for item in self.file_items.values():
            # Use _update_error_tooltip if file has error, otherwise _setup_tooltips
            if hasattr(item, '_update_error_tooltip') and item.has_error:
                item._update_error_tooltip()
            elif hasattr(item, '_setup_tooltips'):
                item._setup_tooltips()