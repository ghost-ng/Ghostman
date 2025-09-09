"""
File browser bar widget following existing PyQt6 UI patterns.

Displays uploaded files with processing status, progress tracking, and management controls.
Integrates seamlessly with the existing theme system and UI architecture.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, 
    QWidget, QPushButton, QProgressBar, QToolButton, QSizePolicy,
    QMenu, QWidgetAction, QCheckBox, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QCursor

# Import ColorUtils for advanced color manipulation
try:
    from ...ui.themes.color_system import ColorUtils
except ImportError:
    # Fallback simple color utility
    class ColorUtils:
        @staticmethod
        def lighten(color: str, factor: float = 0.1) -> str:
            return color
        @staticmethod 
        def darken(color: str, factor: float = 0.1) -> str:
            return color

logger = logging.getLogger("ghostman.file_browser_bar")


class FileStatusIndicator(QWidget):
    """Modern status indicator widget for file processing states."""
    
    def __init__(self, status: str = "pending"):
        super().__init__()
        self.status = status
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
    
    def paintEvent(self, event):
        """Modern status indicators with clean design."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = 4  # Smaller radius for modern look
        
        if self.status == "processing":
            # Modern spinning indicator - minimalist dots
            painter.translate(center)
            painter.rotate(self._rotation)
            
            # Draw 6 dots in a circle
            for i in range(6):
                alpha = 255 - (i * 35)
                color = QColor("#007bff")
                color.setAlpha(max(80, alpha))
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                
                painter.drawEllipse(-1, -radius + 1, 2, 2)
                painter.rotate(60)
                
        elif self.status == "completed":
            # Modern checkmark - clean and minimal
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#28a745"))
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # Thicker, cleaner checkmark
            pen = QPainter(self).pen()
            pen.setColor(QColor("white"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(center.x() - 2, center.y(), center.x() - 1, center.y() + 1)
            painter.drawLine(center.x() - 1, center.y() + 1, center.x() + 2, center.y() - 2)
            
        elif self.status == "failed":
            # Modern X - clean and minimal
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#dc3545"))
            painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            
            # Thicker, cleaner X
            pen = QPainter(self).pen()
            pen.setColor(QColor("white"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(center.x() - 2, center.y() - 2, center.x() + 2, center.y() + 2)
            painter.drawLine(center.x() - 2, center.y() + 2, center.x() + 2, center.y() - 2)
            
        elif self.status == "queued":
            # Modern waiting indicator - clean dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#6c757d"))
            painter.drawEllipse(center.x() - 2, center.y() - 2, 4, 4)
    
    def __del__(self):
        """Cleanup animation on destruction."""
        if self._animation:
            self._animation.stop()


class FileContextItem(QFrame):
    """Pill-style file context item widget (Bootstrap pill inspired)."""
    
    remove_requested = pyqtSignal(str)  # file_id
    view_requested = pyqtSignal(str)    # file_id
    
    def __init__(self, file_id: str, filename: str, file_size: int = 0, file_type: str = "", theme_manager=None):
        super().__init__()
        self.file_id = file_id
        self.filename = filename
        self.file_size = file_size
        self.file_type = file_type
        self.theme_manager = theme_manager
        self.processing_status = "queued"
        self.progress = 0.0
        self.tokens_used = 0
        self.relevance_score = 0.0
        
        self._init_ui()
        self._apply_styling()
        self._setup_context_menu()
    
    def _init_ui(self):
        """Initialize pill-style UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)
        
        # Status indicator (small dot)
        self.status_indicator = FileStatusIndicator("queued")
        self.status_indicator.setFixedSize(12, 12)  # Smaller for pill
        layout.addWidget(self.status_indicator)
        
        # File type icon (smaller)
        self.type_label = QLabel()
        self.type_label.setFixedSize(14, 14)
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_type_icon()
        layout.addWidget(self.type_label)
        
        # Filename (main content)
        self.filename_label = QLabel(self._get_pill_name())
        self.filename_label.setToolTip(f"{self.filename} ({self._format_file_size(self.file_size)})")
        font = self.filename_label.font()
        font.setPointSize(8)
        font.setBold(False)
        self.filename_label.setFont(font)
        layout.addWidget(self.filename_label)
        
        # Remove button (×)
        self.remove_btn = QToolButton()
        self.remove_btn.setText("×")
        self.remove_btn.setToolTip("Remove file")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.file_id))
        self.remove_btn.setFixedSize(16, 16)
        layout.addWidget(self.remove_btn)
        
        # Set size policy for grid pill layout
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(32)  # Bootstrap pill height
        self.setMinimumWidth(120)  # Minimum pill width
        self.setMaximumWidth(200)  # Maximum pill width
        
        # Add tooltip with full info
        self._update_tooltip()
    
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
        """Get pill-style display name (just filename, no extension for brevity)."""
        name = Path(self.filename).stem
        max_length = 15  # Shorter for pill style
        
        if len(name) <= max_length:
            return name
        else:
            return f"{name[:max_length-3]}..."
    
    def _get_status_styling(self) -> Dict[str, str]:
        """Get Bootstrap CSS badge colors for pill styling."""
        # Official Bootstrap 5.3 badge colors
        status_styles = {
            "queued": {
                "bg_color": "#6c757d",  # Bootstrap secondary
                "hover_bg": "#5c636a",  # Bootstrap secondary hover
                "text_color": "#fff",
                "hover_text": "#fff"
            },
            "processing": {
                "bg_color": "#0d6efd",  # Bootstrap primary (blue)
                "hover_bg": "#0b5ed7",  # Bootstrap primary hover
                "text_color": "#fff",
                "hover_text": "#fff"
            },
            "completed": {
                "bg_color": "#198754",  # Bootstrap success (green)  
                "hover_bg": "#157347",  # Bootstrap success hover
                "text_color": "#fff",
                "hover_text": "#fff"
            },
            "failed": {
                "bg_color": "#dc3545",  # Bootstrap danger (red)
                "hover_bg": "#bb2d3b",  # Bootstrap danger hover
                "text_color": "#fff", 
                "hover_text": "#fff"
            }
        }
        return status_styles.get(self.processing_status, status_styles["queued"])
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _apply_styling(self):
        """Apply modern pill-style theme-aware styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            base_bg = colors.background_primary
            text_color = colors.text_primary
            accent_color = colors.primary
        else:
            # Fallback colors
            base_bg = "#1a1a1a"
            text_color = "#ffffff"
            accent_color = "#4CAF50"
        
        # Get status-based styling
        status_style = self._get_status_styling()
        
        # True Bootstrap CSS pill badge styling
        self.setStyleSheet(f"""
            FileContextItem {{
                background-color: {status_style['bg_color']};
                color: {status_style['text_color']};
                border: none;
                border-radius: 50rem;  /* Bootstrap's pill rounding */
                padding: 0.25rem 0.5rem;  /* Bootstrap badge padding */
                font-size: 0.75rem;  /* Bootstrap badge font size */
                font-weight: 700;  /* Bootstrap badge font weight */
                line-height: 1;
                text-align: center;
                white-space: nowrap;
                vertical-align: baseline;
                margin: 0.125rem;
            }}
            FileContextItem:hover {{
                background-color: {status_style['hover_bg']};
                color: {status_style['hover_text']};
                opacity: 0.85;  /* Bootstrap hover effect */
            }}
            QLabel {{
                color: inherit;
                background: transparent;
                border: none;
                font-weight: inherit;
                font-size: inherit;
                margin: 0;
                padding: 0;
            }}
            QToolButton {{
                background-color: rgba(255,255,255,0.2);
                border: none;
                color: inherit;
                font-size: 0.6rem;
                font-weight: bold;
                border-radius: 50%;
                width: 14px;
                height: 14px;
                margin-left: 0.25rem;
            }}
            QToolButton:hover {{
                background-color: rgba(255,255,255,0.35);
            }}
        """)
    
    def _setup_context_menu(self):
        """Setup context menu for the file item."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu."""
        menu = QMenu(self)
        
        # View action
        view_action = QAction("View Content", self)
        view_action.triggered.connect(lambda: self.view_requested.emit(self.file_id))
        menu.addAction(view_action)
        
        menu.addSeparator()
        
        # Copy actions
        copy_name_action = QAction("Copy Filename", self)
        copy_name_action.triggered.connect(self._copy_filename)
        menu.addAction(copy_name_action)
        
        copy_path_action = QAction("Copy Path", self)
        copy_path_action.triggered.connect(self._copy_path)
        menu.addAction(copy_path_action)
        
        menu.addSeparator()
        
        # Remove action
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_requested.emit(self.file_id))
        menu.addAction(remove_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _copy_filename(self):
        """Copy filename to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.filename)
    
    def _copy_path(self):
        """Copy full path to clipboard."""
        from PyQt6.QtWidgets import QApplication
        # This would need the full path from the file context data
        QApplication.clipboard().setText(self.filename)  # Placeholder
    
    def update_status(self, status: str, progress: float = 0.0, already_processed: bool = False):
        """Update processing status and progress."""
        old_status = self.processing_status
        self.processing_status = status
        self.progress = progress
        self._already_processed = already_processed
        
        # Update status indicator
        self.status_indicator.set_status(status)
        
        # Reapply styling if status changed
        if old_status != status:
            self._apply_styling()
            
        # Update tooltip
        self._update_tooltip()
        
        # Animate status change
        if old_status != status:
            self._animate_status_change()
    
    def set_usage_info(self, tokens_used: int, relevance_score: float):
        """Update usage information."""
        self.tokens_used = tokens_used
        self.relevance_score = relevance_score
        self._update_tooltip()
    
    def _update_tooltip(self):
        """Update tooltip with comprehensive file info."""
        status_text = {
            "queued": "⏳ Queued for processing",
            "processing": "🔄 Processing...",
            "completed": "✅ Processed successfully", 
            "failed": "❌ Processing failed"
        }.get(self.processing_status, "❓ Unknown status")
        
        # Check if this was already processed
        if hasattr(self, '_already_processed') and self._already_processed:
            status_text = "📋 Already processed (using existing embeddings)"
        
        size_text = self._format_file_size(self.file_size)
        tooltip_parts = [
            f"📄 {self.filename}",
            f"📊 {size_text}",
            f"🔧 {self.file_type.upper() if self.file_type else 'Unknown'}",
            status_text
        ]
        
        if self.tokens_used > 0:
            tooltip_parts.append(f"🔤 {self.tokens_used} tokens")
            
        if self.relevance_score > 0:
            tooltip_parts.append(f"🎯 {self.relevance_score:.1%} relevance")
            
        self.setToolTip("\n".join(tooltip_parts))
    
    def _animate_status_change(self):
        """Animate status change with a subtle effect."""
        # DISABLED: QPropertyAnimation on geometry was causing segmentation faults
        # The animation creates Qt C++ objects that can cause crashes during cleanup
        # Keep method for future non-geometry animations if needed
        pass


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
    clear_all_requested = pyqtSignal()
    files_reordered = pyqtSignal(list)  # list of file_ids in new order
    
    def __init__(self, theme_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.file_items: Dict[str, FileContextItem] = {}
        self.max_visible_files = 20  # More files in grid
        self._is_expanded = True
        self._animation = None
        
        # Grid layout tracking
        self.current_row_layout = None
        self.pills_in_current_row = 0
        self.max_pills_per_row = 4
        
        self.setVisible(False)  # Initially hidden
        self._init_ui()
        self._apply_styling()
        self._connect_signals()
        
        logger.debug("FileBrowserBar initialized")
    
    def _init_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)
        
        # Header section
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(8)
        
        # Title with file count
        self.title_label = QLabel("📁 File Contexts")
        font = self.title_label.font()
        font.setBold(True)
        font.setPointSize(10)
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Toggle collapse/expand button
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("▼")
        self.toggle_btn.setToolTip("Collapse/Expand")
        self.toggle_btn.clicked.connect(self._toggle_expansion)
        self.toggle_btn.setFixedSize(20, 20)
        header_layout.addWidget(self.toggle_btn)
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙️")
        self.settings_btn.setToolTip("File context settings")
        self.settings_btn.clicked.connect(self._show_settings_menu)
        self.settings_btn.setFixedSize(20, 20)
        header_layout.addWidget(self.settings_btn)
        
        # Clear all button
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_requested.emit)
        self.clear_all_btn.setMaximumWidth(80)
        header_layout.addWidget(self.clear_all_btn)
        
        main_layout.addWidget(header_frame)
        
        # Files section (grid layout pills)
        self.files_frame = QFrame()
        files_layout = QVBoxLayout(self.files_frame)
        files_layout.setContentsMargins(8, 8, 8, 8)
        files_layout.setSpacing(6)
        
        # Grid container for Bootstrap-style pills
        self.pills_container = QWidget()
        self.pills_container.setObjectName("pills_container")
        
        # Use a flow layout-like approach with QHBoxLayout and wrapping
        self.pills_grid = QVBoxLayout(self.pills_container)  # Vertical for rows
        self.pills_grid.setContentsMargins(0, 0, 0, 0)
        self.pills_grid.setSpacing(8)
        
        self.current_row_layout = None
        self.pills_in_current_row = 0
        self.max_pills_per_row = 4  # Grid layout
        
        files_layout.addWidget(self.pills_container)
        
        # Status section (summary info)
        self.status_frame = QFrame()
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(4, 2, 4, 2)
        status_layout.setSpacing(8)
        
        self.status_label = QLabel("No files loaded")
        font = self.status_label.font()
        font.setPointSize(8)
        self.status_label.setFont(font)
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        files_layout.addWidget(self.status_frame)
        main_layout.addWidget(self.files_frame)
    
    def _apply_styling(self):
        """Apply theme-aware styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.background_secondary
            bg_primary = colors.background_primary
            text_color = colors.text_primary
            text_secondary = colors.text_secondary
            border_color = colors.border_secondary
            accent_color = colors.primary
        else:
            # Fallback colors
            bg_color = "#2c3e50"
            bg_primary = "#34495e"
            text_color = "#ecf0f1"
            text_secondary = "#95a5a6"
            border_color = "#34495e"
            accent_color = "#3498db"
        
        self.setStyleSheet(f"""
            FileBrowserBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {bg_color}, stop:1 {ColorUtils.darken(bg_color, 0.1)});
                border: 1px solid {ColorUtils.lighten(border_color, 0.2)};
                border-radius: 12px;
                margin: 4px;
                padding: 6px;
            }}
            QFrame {{
                background-color: transparent;
                border: none;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                border: none;
                font-weight: 500;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {accent_color}, stop:1 {ColorUtils.darken(accent_color, 0.15)});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {ColorUtils.lighten(accent_color, 0.1)}, 
                    stop:1 {ColorUtils.darken(accent_color, 0.05)});
            }}
            QPushButton:pressed {{
                background: {ColorUtils.darken(accent_color, 0.2)};
            }}
            QToolButton {{
                background-color: rgba(255,255,255,0.1);
                border: none;
                border-radius: 10px;
                color: {text_color};
                font-size: 12px;
                min-width: 20px;
                min-height: 20px;
            }}
            QToolButton:hover {{
                background-color: {accent_color};
                color: white;
            }}
            QScrollArea {{
                background-color: transparent;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
            }}
            QScrollBar:horizontal {{
                background-color: rgba(255,255,255,0.05);
                height: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {accent_color};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {ColorUtils.lighten(accent_color, 0.2)};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
        """)
        
        # Update status label color
        self.status_label.setStyleSheet(f"color: {text_secondary};")
    
    def _connect_signals(self):
        """Connect internal signals."""
        if self.theme_manager:
            # Connect to theme changes
            if hasattr(self.theme_manager, 'theme_changed'):
                self.theme_manager.theme_changed.connect(self._on_theme_changed)
    
    def _on_theme_changed(self, new_theme):
        """Handle theme changes."""
        self._apply_styling()
        # Update all file items
        for item in self.file_items.values():
            item._apply_styling()
    
    def _toggle_expansion(self):
        """Toggle collapsed/expanded state."""
        # DISABLED: QPropertyAnimation was causing segmentation faults
        # Use instant expand/collapse instead of animation
        
        self._is_expanded = not self._is_expanded
        
        # Update toggle button
        self.toggle_btn.setText("▲" if self._is_expanded else "▼")
        
        # Instant expand/collapse without animation
        if self._is_expanded:
            self.files_frame.setVisible(True)
            self.files_frame.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX equivalent
        else:
            self.files_frame.setVisible(False)
            self.files_frame.setMaximumHeight(0)
    
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
    
    def add_file(self, file_id: str, filename: str, file_size: int = 0, file_type: str = "", status: str = "queued"):
        """Add a file to the browser bar."""
        if file_id in self.file_items:
            # Update existing item
            item = self.file_items[file_id]
            item.update_status(status)
            return
        
        # Create new file item
        item = FileContextItem(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            theme_manager=self.theme_manager
        )
        
        # Connect signals
        item.remove_requested.connect(self._on_file_remove_requested)
        item.view_requested.connect(self.file_viewed.emit)
        
        # Add to grid layout
        if not self.current_row_layout or self.pills_in_current_row >= self.max_pills_per_row:
            # Create new row
            self.current_row_layout = QHBoxLayout()
            self.current_row_layout.setSpacing(8)
            self.current_row_layout.setContentsMargins(0, 0, 0, 0)
            
            row_widget = QWidget()
            row_widget.setLayout(self.current_row_layout)
            self.pills_grid.addWidget(row_widget)
            
            self.pills_in_current_row = 0
        
        # Add item to current row
        self.current_row_layout.addWidget(item)
        self.pills_in_current_row += 1
        
        # Add stretch to fill remaining space in row
        if self.pills_in_current_row < self.max_pills_per_row:
            self.current_row_layout.addStretch()
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
            
            # Hide if no files left
            if not self.file_items:
                self.setVisible(False)
            
            self._update_status_display()
            logger.debug(f"Removed file item: {file_id}")
    
    def update_file_status(self, file_id: str, status: str, progress: float = 0.0):
        """Update file processing status."""
        logger.info(f"🔍 DEBUG: update_file_status called - file_id: {file_id}, status: {status}")
        try:
            if file_id in self.file_items:
                logger.info(f"🔍 DEBUG: Found file item for {file_id}")
                self.file_items[file_id].update_status(status, progress)
                logger.info(f"🔍 DEBUG: Updated status for {file_id}")
                self._update_status_display()
                logger.info(f"🔍 DEBUG: Updated status display for {file_id}")
            else:
                logger.info(f"🔍 DEBUG: File item not found for {file_id}")
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
        self.setVisible(False)
        logger.debug("Cleared all file items")
    
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
        
        self.status_label.setText(status_text)
        
        # Update title with count
        if total_files > 0:
            self.title_label.setText(f"📁 File Contexts ({total_files})")
        else:
            self.title_label.setText("📁 File Contexts")
    
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
    
    def _rebuild_grid_layout(self):
        """Rebuild the grid layout after item removal."""
        # Clear current layout
        for i in reversed(range(self.pills_grid.count())):
            child = self.pills_grid.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Reset grid tracking
        self.current_row_layout = None
        self.pills_in_current_row = 0
        
        # Re-add all items
        for file_id, item in self.file_items.items():
            if not self.current_row_layout or self.pills_in_current_row >= self.max_pills_per_row:
                # Create new row
                self.current_row_layout = QHBoxLayout()
                self.current_row_layout.setSpacing(8)
                self.current_row_layout.setContentsMargins(0, 0, 0, 0)
                
                row_widget = QWidget()
                row_widget.setLayout(self.current_row_layout)
                self.pills_grid.addWidget(row_widget)
                
                self.pills_in_current_row = 0
            
            # Add item to current row
            self.current_row_layout.addWidget(item)
            self.pills_in_current_row += 1
            
            # Add stretch to fill remaining space in row
            if self.pills_in_current_row < self.max_pills_per_row:
                self.current_row_layout.addStretch()