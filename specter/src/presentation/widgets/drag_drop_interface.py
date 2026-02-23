"""
Drag and Drop Interface for File Context Feature.

Provides visual feedback and handling for file drag and drop operations
throughout the Specter application.
"""

import logging
from typing import List, Optional, Callable
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent, QDragLeaveEvent, QPainter, QColor, QPen

logger = logging.getLogger("specter.drag_drop")

class DragDropOverlay(QFrame):
    """
    Overlay widget that appears when files are dragged over the application.
    
    Provides clear visual feedback about drop zones and accepted file types.
    """
    
    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animation for smooth show/hide
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.setVisible(False)
        self._init_ui()
        self._apply_styling()

        # Re-apply styling when the theme changes
        if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
            self.theme_manager.theme_changed.connect(lambda _: self._apply_styling())

    def _init_ui(self):
        """Initialize the overlay UI."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Main drop icon
        self.drop_icon = QLabel("📁")
        self.drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_icon.setStyleSheet("font-size: 64px;")
        layout.addWidget(self.drop_icon)
        
        # Main message
        self.main_message = QLabel("Drop Files Here")
        self.main_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_message.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(self.main_message)
        
        # Subtitle with supported formats
        self.subtitle = QLabel("Supported formats: TXT, PY, JS, JSON, MD, CSV")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("font-size: 14px; font-weight: 400;")
        layout.addWidget(self.subtitle)
        
        layout.addStretch()
    
    def _apply_styling(self):
        """Apply theme-aware styling with semi-transparent background."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.background_overlay  # Should have alpha
            text_color = colors.text_primary
            border_color = colors.primary
        else:
            bg_color = "rgba(0, 0, 0, 0.8)"
            text_color = "#ffffff"
            border_color = "#4CAF50"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 3px dashed {border_color};
                border-radius: 12px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
        """)
    
    def show_overlay(self, valid_drop: bool = True):
        """Show overlay with animation."""
        if valid_drop:
            self.main_message.setText("Drop Files Here")
            self.drop_icon.setText("📁")
        else:
            self.main_message.setText("Unsupported File Type")
            self.drop_icon.setText("❌")
        
        self.setVisible(True)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def hide_overlay(self):
        """Hide overlay with animation."""
        self.fade_animation.finished.connect(lambda: self.setVisible(False))
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()


class DragDropMixin:
    """
    Mixin class to add drag and drop functionality to any widget.
    
    This mixin provides standardized drag and drop handling that can be
    added to the main REPL widget or other components.
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.txt', '.py', '.js', '.json', '.md', '.csv', '.html', '.css', '.yaml', '.yml', '.xml'}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drag_drop_callback: Optional[Callable[[List[str]], None]] = None
        self.drag_drop_overlay: Optional[DragDropOverlay] = None
        self._drag_timer = QTimer()
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._hide_drag_overlay)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def set_drag_drop_callback(self, callback: Callable[[List[str]], None]):
        """Set callback function for handling dropped files."""
        self.drag_drop_callback = callback
    
    def setup_drag_drop_overlay(self, theme_manager=None):
        """Set up the drag drop overlay widget."""
        self.drag_drop_overlay = DragDropOverlay(theme_manager, self)
        # Position overlay to cover the entire widget
        self.drag_drop_overlay.setGeometry(self.rect())
    
    def resizeEvent(self, event):
        """Handle resize events to reposition overlay."""
        super().resizeEvent(event)
        if self.drag_drop_overlay:
            self.drag_drop_overlay.setGeometry(self.rect())
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if self._has_valid_files(event.mimeData()):
            event.acceptProposedAction()
            self._show_drag_overlay(True)
            logger.debug("Drag enter: valid files detected")
        else:
            event.ignore()
            self._show_drag_overlay(False)
            logger.debug("Drag enter: no valid files detected")
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move events."""
        if self._has_valid_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """Handle drag leave events."""
        # Use timer to avoid flickering when moving between child widgets
        self._drag_timer.start(100)
        logger.debug("Drag leave detected")
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        self._hide_drag_overlay()
        
        if not self._has_valid_files(event.mimeData()):
            event.ignore()
            return
        
        # Get file paths
        file_paths = self._extract_file_paths(event.mimeData())
        if not file_paths:
            event.ignore()
            return
        
        # Filter valid files
        valid_files = [path for path in file_paths if self._is_supported_file(path)]
        
        if not valid_files:
            logger.warning(f"No supported files in drop: {file_paths}")
            event.ignore()
            return
        
        event.acceptProposedAction()
        
        # Call the callback if set
        if self.drag_drop_callback:
            self.drag_drop_callback(valid_files)
            logger.info(f"Dropped {len(valid_files)} files: {[Path(f).name for f in valid_files]}")
        else:
            logger.warning("No drag drop callback set")
    
    def _has_valid_files(self, mime_data: QMimeData) -> bool:
        """Check if mime data contains valid files."""
        if not mime_data.hasUrls():
            return False
        
        for url in mime_data.urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if self._is_supported_file(file_path):
                    return True
        
        return False
    
    def _extract_file_paths(self, mime_data: QMimeData) -> List[str]:
        """Extract file paths from mime data."""
        file_paths = []
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
        
        return file_paths
    
    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported based on extension."""
        try:
            path = Path(file_path)
            return path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        except Exception as e:
            logger.error(f"Error checking file support for {file_path}: {e}")
            return False
    
    def _show_drag_overlay(self, valid_drop: bool):
        """Show the drag overlay."""
        if self.drag_drop_overlay:
            self.drag_drop_overlay.show_overlay(valid_drop)
            self.drag_drop_overlay.raise_()  # Bring to front
    
    def _hide_drag_overlay(self):
        """Hide the drag overlay."""
        if self.drag_drop_overlay:
            self.drag_drop_overlay.hide_overlay()


class FileStatusIndicator(QFrame):
    """
    File status indicator widget that shows processing states.
    
    Can be used standalone or embedded in other widgets to show
    file processing status with appropriate visual feedback.
    """
    
    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.current_status = "idle"  # idle, processing, success, error
        self.message = ""
        
        self._init_ui()
        self._apply_styling()

        # Re-apply styling when the theme changes
        if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
            self.theme_manager.theme_changed.connect(lambda _: self._apply_styling())

    def _init_ui(self):
        """Initialize the status indicator UI."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # Status icon and text
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Initially hidden
        self.setVisible(False)
    
    def _apply_styling(self):
        """Apply theme-aware styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.background_secondary
            text_color = colors.text_primary
            border_color = colors.border_secondary
        else:
            bg_color = "#2a2a2a"
            text_color = "#ffffff"
            border_color = "#444444"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
        """)
    
    def set_status(self, status: str, message: str = ""):
        """
        Set the status indicator state.
        
        Args:
            status: One of "idle", "processing", "success", "error"
            message: Optional status message
        """
        self.current_status = status
        self.message = message
        
        if status == "idle":
            self.setVisible(False)
            return
        
        # Status icons and messages
        status_config = {
            "processing": ("⏳", "Processing files..."),
            "success": ("✅", "Files processed successfully"),
            "error": ("❌", "Error processing files")
        }
        
        icon, default_msg = status_config.get(status, ("❓", "Unknown status"))
        display_message = message or default_msg
        
        self.status_label.setText(f"{icon} {display_message}")
        
        # Show with appropriate styling
        if status == "success":
            self._apply_success_styling()
        elif status == "error":
            self._apply_error_styling()
        else:
            self._apply_styling()
        
        self.setVisible(True)
        
        # Auto-hide success/error messages after delay
        if status in ["success", "error"]:
            QTimer.singleShot(3000, self._auto_hide)
    
    def _apply_success_styling(self):
        """Apply success state styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.status_success
            border_color = colors.status_success
        else:
            bg_color = "#4CAF50"
            border_color = "#4CAF50"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QLabel {{
                color: #ffffff;
                background: transparent;
                border: none;
                font-weight: 500;
            }}
        """)
    
    def _apply_error_styling(self):
        """Apply error state styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.status_error
            border_color = colors.status_error
        else:
            bg_color = "#F44336"
            border_color = "#F44336"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QLabel {{
                color: #ffffff;
                background: transparent;
                border: none;
                font-weight: 500;
            }}
        """)
    
    def _auto_hide(self):
        """Auto-hide the status indicator."""
        self.set_status("idle")
    
    def clear_status(self):
        """Clear the status indicator."""
        self.set_status("idle")


class ContextIndicator(QLabel):
    """
    Small indicator that shows when file contexts are being used in conversations.
    
    This appears near the input area or in the toolbar to indicate that
    file contexts are active and being included in the conversation.
    """
    
    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.active_contexts = 0
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(24, 24)
        self.setStyleSheet("font-size: 12px;")
        self.setVisible(False)

        self._apply_styling()

        # Re-apply styling when the theme changes
        if self.theme_manager and hasattr(self.theme_manager, 'theme_changed'):
            self.theme_manager.theme_changed.connect(lambda _: self._apply_styling())

    def set_context_count(self, count: int):
        """Set the number of active contexts."""
        self.active_contexts = count
        
        if count > 0:
            self.setText(f"📎{count}" if count > 1 else "📎")
            self.setToolTip(f"{count} file context{'s' if count != 1 else ''} active")
            self.setVisible(True)
        else:
            self.setVisible(False)
    
    def _apply_styling(self):
        """Apply theme-aware styling."""
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            bg_color = colors.primary
            text_color = "#ffffff"
        else:
            bg_color = "#4CAF50"
            text_color = "#ffffff"
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px;
            }}
        """)