"""
Help Dialog for Specter.
Displays comprehensive help documentation in a web browser or embedded web view.
"""

import os
import sys
import logging
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPixmap

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

logger = logging.getLogger("specter.help_dialog")


class HelpDialog(QDialog):
    """Dialog for displaying help documentation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Specter Help")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)
        
        self.help_path = self._get_help_path()
        self.web_view = None
        
        self._setup_ui()
        self._apply_styling()

        # Connect to theme changes for live updates
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            if theme_manager:
                theme_manager.theme_changed.connect(lambda _: self._apply_styling())
        except ImportError:
            pass

        logger.info("Help dialog initialized")
    
    def _get_help_path(self) -> Path:
        """Get the path to the help documentation."""
        from ...utils.resource_resolver import resolve_help_file
        
        help_path = resolve_help_file()
        if help_path:
            logger.info(f"Found help documentation at: {help_path}")
        else:
            logger.warning("Help documentation not found in any expected location")
        
        return help_path
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)
        
        # Content area
        if self.help_path and self.help_path.exists():
            if WEB_ENGINE_AVAILABLE:
                self._create_web_view(layout)
            else:
                self._create_fallback_view(layout)
        else:
            self._create_error_view(layout)
        
        # Footer with buttons
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)
    
    def _create_header(self) -> QHBoxLayout:
        """Create the header section."""
        header_layout = QHBoxLayout()
        
        # Title and icon
        title_label = QLabel("👻 Specter Help Documentation")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Version info
        try:
            from .....__version__ import __version__
            version_label = QLabel(f"Version {__version__}")
            version_label.setStyleSheet("color: #64748b; font-size: 12px;")
            header_layout.addWidget(version_label)
        except ImportError:
            pass
        
        return header_layout
    
    def _create_web_view(self, layout: QVBoxLayout):
        """Create web view for displaying help content."""
        try:
            self.web_view = QWebEngineView()
            
            # Load the help page
            file_url = QUrl.fromLocalFile(str(self.help_path.absolute()))
            self.web_view.load(file_url)
            
            layout.addWidget(self.web_view)
            logger.info("Web view created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create web view: {e}")
            self._create_fallback_view(layout)
    
    def _create_fallback_view(self, layout: QVBoxLayout):
        """Create fallback view when web engine is not available."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout(frame)
        
        # Icon
        icon_label = QLabel("📚")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px; margin: 20px;")
        frame_layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(
            "<h2>Help Documentation Available</h2>"
            "<p>The comprehensive help documentation is available but requires "
            "a web browser to display properly.</p>"
            "<p>Click 'Open in Browser' below to view the full documentation "
            "with interactive features, search, and navigation.</p>"
        )
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("margin: 20px; line-height: 1.5;")
        frame_layout.addWidget(message_label)
        
        # Quick info
        info_label = QLabel(
            "<b>Quick Help:</b><br>"
            "• <b>Enter:</b> Send message<br>"
            "• <b>Up/Down arrows:</b> Navigate message history<br>"
            "• <b>Ctrl+F:</b> Search conversations<br>"
            "• <b>Ctrl+H:</b> Hide chat window<br>"
            "• Configure your API key in Settings → AI Model<br>"
            "• Works with OpenAI and compatible services"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_label.setStyleSheet(
            "background: #f8fafc; padding: 15px; border-radius: 8px; "
            "border-left: 4px solid #8b5cf6; margin: 10px;"
        )
        frame_layout.addWidget(info_label)
        
        frame_layout.addStretch()
        layout.addWidget(frame)
    
    def _create_error_view(self, layout: QVBoxLayout):
        """Create error view when help files are not found."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout(frame)
        
        # Error icon
        error_label = QLabel("⚠")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("font-size: 48px; margin: 20px;")
        frame_layout.addWidget(error_label)
        
        # Error message
        message_label = QLabel(
            "<h2>Help Documentation Not Found</h2>"
            "<p>The help documentation files could not be located.</p>"
            "<p>Please check the installation or try reinstalling the application.</p>"
        )
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("margin: 20px; line-height: 1.5;")
        frame_layout.addWidget(message_label)
        
        frame_layout.addStretch()
        layout.addWidget(frame)
    
    def _create_footer(self) -> QHBoxLayout:
        """Create the footer with action buttons."""
        footer_layout = QHBoxLayout()
        
        footer_layout.addStretch()
        
        # Open in browser button (if local help exists)
        if self.help_path and self.help_path.exists():
            browser_btn = QPushButton("🌐 Open in Browser")
            browser_btn.clicked.connect(self._open_in_browser)
            footer_layout.addWidget(browser_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        footer_layout.addWidget(close_btn)
        
        return footer_layout
    
    def _apply_styling(self):
        """Apply consistent styling to the dialog."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...ui.themes.style_templates import StyleTemplates
            
            theme_manager = get_theme_manager()
            if theme_manager and hasattr(theme_manager, 'current_theme'):
                colors = theme_manager.current_theme
                
                # Apply dialog styling
                dialog_style = StyleTemplates.get_dialog_style(colors)
                self.setStyleSheet(dialog_style)
                
                logger.debug("Applied theme styling to help dialog")
        except Exception as e:
            logger.warning(f"Could not apply theme styling: {e}")
    
    def _open_in_browser(self):
        """Open help documentation in the default web browser."""
        try:
            if self.help_path and self.help_path.exists():
                webbrowser.open(f"file://{self.help_path.absolute()}")
                logger.info("Opened help documentation in browser")
            else:
                logger.warning("Help documentation not found locally")
        except Exception as e:
            logger.error(f"Failed to open help in browser: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open help documentation in browser:\\n{e}"
            )
    
    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        
        # Center the dialog on the parent
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        
        logger.debug("Help dialog shown")


def show_help(parent=None):
    """Convenience function to show the help dialog."""
    dialog = HelpDialog(parent)
    dialog.exec()


if __name__ == "__main__":
    # Test the help dialog
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = HelpDialog()
    dialog.show()
    sys.exit(app.exec())