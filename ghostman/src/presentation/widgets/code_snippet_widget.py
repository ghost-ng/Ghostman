"""
Code Snippet Widget for Ghostman.

Provides a syntax-highlighted code display widget with copy functionality,
designed for integration with the REPL and markdown rendering system.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QApplication, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QTextCursor, QPalette, QIcon

logger = logging.getLogger("ghostman.code_snippet_widget")

# Theme system imports
try:
    from ...ui.themes.theme_manager import get_theme_manager
    from ...ui.themes.style_templates import StyleTemplates, ButtonStyleManager
    from ...ui.themes.color_system import ColorSystem
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    # Create a basic ColorSystem substitute
    class ColorSystem:
        def __init__(self):
            self.primary = "#007ACC"
            self.secondary = "#E1E1E1"
            self.background_primary = "#FFFFFF"
            self.background_secondary = "#F5F5F5"
            self.background_tertiary = "#FAFAFA"
            self.text_primary = "#000000"
            self.text_secondary = "#666666"
            self.text_disabled = "#CCCCCC"
            self.border_primary = "#CCCCCC"
            self.border_secondary = "#E1E1E1"
            self.border_focus = "#007ACC"
            self.interactive_normal = "#FFFFFF"
            self.interactive_hover = "#F0F0F0"
            self.interactive_active = "#E1E1E1"
            self.interactive_disabled = "#F5F5F5"
            
    logger.warning("Theme system not available - using basic styling")

class CodeSnippetHeader(QWidget):
    """Header widget for code snippets with title, language tag, and copy button."""
    
    copy_requested = pyqtSignal(str)  # Emitted when copy button is clicked
    
    def __init__(self, title: str = "Code", language: str = "text", parent=None):
        super().__init__(parent)
        self.title = title
        self.language = language
        self.theme_colors: Optional[ColorSystem] = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize the header UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title label
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("code-snippet-title")
        layout.addWidget(self.title_label)
        
        # Language tag
        self.language_tag = QLabel(self.language.upper())
        self.language_tag.setObjectName("code-snippet-language-tag")
        layout.addWidget(self.language_tag)
        
        # Spacer
        layout.addStretch()
        
        # Copy button
        self.copy_button = QPushButton("Copy")
        self.copy_button.setObjectName("code-snippet-copy-button")
        self.copy_button.setFixedSize(QSize(60, 28))
        self.copy_button.clicked.connect(self._on_copy_clicked)
        layout.addWidget(self.copy_button)
        
    def _on_copy_clicked(self):
        """Handle copy button click."""
        self.copy_requested.emit("copy")
        
    def show_copy_feedback(self):
        """Show visual feedback for successful copy operation."""
        original_text = self.copy_button.text()
        self.copy_button.setText("Copied!")
        self.copy_button.setEnabled(False)
        
        # Reset after 1.5 seconds
        def reset_button():
            self.copy_button.setText(original_text)
            self.copy_button.setEnabled(True)
            
        QTimer.singleShot(1500, reset_button)
        
    def apply_theme(self, colors: ColorSystem):
        """Apply theme colors to the header."""
        self.theme_colors = colors
        
        # Apply button styling if available
        if THEME_SYSTEM_AVAILABLE:
            try:
                ButtonStyleManager.apply_unified_button_style(
                    button=self.copy_button,
                    colors=colors,
                    button_type="push",
                    size="small",
                    state="normal"
                )
            except Exception as e:
                logger.warning(f"Failed to apply button theme: {e}")


class CodeSnippetWidget(QFrame):
    """
    Code snippet display widget with syntax highlighting and copy functionality.
    
    Features:
    - Header with title and language tag
    - Copy button with visual feedback
    - Syntax-highlighted code display
    - Theme integration
    - Scrollable content for long code
    """
    
    code_copied = pyqtSignal(str)  # Emitted when code is copied
    
    def __init__(self, code: str, language: str = "text", title: str = None, parent=None):
        super().__init__(parent)
        self.code = code
        self.language = language or "text"
        self.title = title or self._generate_title()
        self.theme_colors: Optional[ColorSystem] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _generate_title(self) -> str:
        """Generate a title based on the language."""
        if self.language and self.language != "text":
            return f"{self.language.title()} Snippet"
        return "Code Snippet"
        
    def _setup_ui(self):
        """Initialize the widget UI components."""
        self.setObjectName("code-snippet-container")
        self.setFrameStyle(QFrame.Shape.Box)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = CodeSnippetHeader(
            title=self.title, 
            language=self.language, 
            parent=self
        )
        self.header.setObjectName("code-snippet-header")
        layout.addWidget(self.header)
        
        # Code display
        self.code_display = QTextEdit()
        self.code_display.setObjectName("code-snippet-code-display")
        self.code_display.setReadOnly(True)
        self.code_display.setPlainText(self.code)
        
        # Set monospace font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.code_display.setFont(font)
        
        # Configure text edit behavior
        self.code_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.code_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Set minimum height for readability
        self.code_display.setMinimumHeight(60)
        
        layout.addWidget(self.code_display)
        
    def _setup_connections(self):
        """Setup signal connections."""
        self.header.copy_requested.connect(self._handle_copy)
        
    def _handle_copy(self):
        """Handle copy operation."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.code)
            
            # Show feedback
            self.header.show_copy_feedback()
            
            # Emit signal
            self.code_copied.emit(self.code)
            
            logger.debug(f"Copied {len(self.code)} characters to clipboard")
            
        except Exception as e:
            logger.error(f"Failed to copy code to clipboard: {e}")
            
    def set_code(self, code: str, language: str = None):
        """Update the code content and optionally the language."""
        self.code = code
        if language:
            self.language = language
            self.header.language_tag.setText(language.upper())
            
        self.code_display.setPlainText(self.code)
        
    def apply_theme(self, colors: ColorSystem):
        """Apply theme colors to the widget."""
        self.theme_colors = colors
        
        # Apply theme to header
        self.header.apply_theme(colors)
        
        # Get styling from StyleTemplates if available
        if THEME_SYSTEM_AVAILABLE:
            try:
                from ...ui.themes.style_templates import StyleTemplates
                style_css = StyleTemplates.get_code_snippet_widget_style(colors)
                self.setStyleSheet(style_css)
            except Exception as e:
                logger.warning(f"Failed to apply theme styling: {e}")
                self._apply_basic_styling(colors)
        else:
            self._apply_basic_styling(colors)
            
    def _apply_basic_styling(self, colors: ColorSystem):
        """Apply basic styling when StyleTemplates is not available."""
        basic_style = f"""
        QFrame#code-snippet-container {{
            border: 1px solid {colors.border_primary};
            border-radius: 8px;
            background-color: {colors.background_tertiary};
            margin: 4px 0px;
        }}
        
        QWidget#code-snippet-header {{
            background-color: {colors.background_secondary};
            border-bottom: 1px solid {colors.border_secondary};
            border-radius: 7px 7px 0px 0px;
        }}
        
        QLabel#code-snippet-title {{
            color: {colors.text_primary};
            font-weight: 600;
            font-size: 13px;
        }}
        
        QLabel#code-snippet-language-tag {{
            background-color: {colors.primary}20;
            color: {colors.primary};
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
        }}
        
        QTextEdit#code-snippet-code-display {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: none;
            border-radius: 0px 0px 7px 7px;
            padding: 8px;
        }}
        """
        self.setStyleSheet(basic_style)
        

def create_code_snippet_widget(code: str, language: str = "text", 
                             title: str = None, theme_colors: ColorSystem = None,
                             parent=None) -> CodeSnippetWidget:
    """
    Factory function to create a themed code snippet widget.
    
    Args:
        code: The code content to display
        language: Programming language for syntax highlighting
        title: Custom title for the snippet (auto-generated if None)
        theme_colors: ColorSystem for theming (auto-detected if None)
        parent: Parent widget
        
    Returns:
        Configured CodeSnippetWidget instance
    """
    widget = CodeSnippetWidget(code, language, title, parent)
    
    # Apply theme if provided or available
    if theme_colors:
        widget.apply_theme(theme_colors)
    elif THEME_SYSTEM_AVAILABLE:
        try:
            theme_manager = get_theme_manager()
            if theme_manager and theme_manager.current_theme:
                widget.apply_theme(theme_manager.current_theme)
        except Exception as e:
            logger.warning(f"Failed to auto-apply theme: {e}")
            
    return widget


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Test code
    test_code = '''def fibonacci(n):
    """Generate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    return fib

# Example usage
result = fibonacci(10)
print(f"First 10 Fibonacci numbers: {result}")'''
    
    # Create test window
    window = QWidget()
    window.setWindowTitle("Code Snippet Widget Test")
    window.resize(600, 400)
    
    layout = QVBoxLayout(window)
    
    # Create code snippet widget
    widget = create_code_snippet_widget(
        code=test_code,
        language="python",
        title="Fibonacci Function"
    )
    
    layout.addWidget(widget)
    
    window.show()
    sys.exit(app.exec())