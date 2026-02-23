"""
Code Snippet Widget for Specter.

Provides a syntax-highlighted code display widget with copy functionality,
designed for integration with the REPL and markdown rendering system.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QApplication, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRegularExpression
from PyQt6.QtGui import QFont, QTextCursor, QPalette, QIcon, QSyntaxHighlighter, QTextCharFormat, QColor

logger = logging.getLogger("specter.code_snippet_widget")

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


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """
    Python syntax highlighter matching the target design colors.
    
    Colors based on the target screenshot:
    - Purple: keywords (def, if, return, etc.)
    - Green: strings
    - Blue: numbers
    - Gray: comments
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_highlighting_rules()
        
    def _setup_highlighting_rules(self):
        """Setup the highlighting rules with target design colors."""
        
        # Keywords (purple color like in target)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#d73a49"))  # Red-purple like GitHub
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "exec", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "not", "or", "pass", "print", "raise", "return", "try",
            "while", "with", "yield", "None", "True", "False"
        ]
        
        self.highlighting_rules = []
        for keyword in keywords:
            pattern = QRegularExpression(f"\\b{keyword}\\b")
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Strings (green color like in target)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#032f62"))  # Dark blue for strings
        
        # Single and double quoted strings
        self.highlighting_rules.append((QRegularExpression('"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), string_format))
        self.highlighting_rules.append((QRegularExpression("'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), string_format))
        
        # Triple quoted strings
        self.highlighting_rules.append((QRegularExpression('"""[^"]*"""'), string_format))
        self.highlighting_rules.append((QRegularExpression("'''[^']*'''"), string_format))
        
        # Numbers (blue color)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#005cc5"))  # Blue
        self.highlighting_rules.append((QRegularExpression("\\b\\d+\\.?\\d*\\b"), number_format))
        
        # Comments (gray color)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a737d"))  # Gray
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegularExpression("#[^\\n]*"), comment_format))
        
        # Function names (after def)
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#6f42c1"))  # Purple
        function_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression("\\bdef\\s+(\\w+)"), function_format))
        
        # Class names (after class)
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#6f42c1"))  # Purple
        class_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression("\\bclass\\s+(\\w+)"), class_format))

    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        for pattern, format in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, format)


class CodeSnippetHeader(QWidget):
    """Header widget removed - functionality moved to overlay buttons in main widget."""
    pass  # This class is deprecated in the new design


class CodeSnippetWidget(QFrame):
    """
    Code snippet display widget with syntax highlighting and overlay button functionality.
    
    New Design Features:
    - No header banner - clean code-focused layout
    - Small language button overlay on top-left
    - Copy button overlay on top-right
    - Syntax-highlighted code display with full area usage
    - Theme integration across 39 themes
    - WCAG accessibility compliance
    - Responsive button positioning
    """
    
    code_copied = pyqtSignal(str)  # Emitted when code is copied
    language_clicked = pyqtSignal(str)  # Emitted when language button is clicked
    
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
        """Initialize the widget UI components with new overlay button design."""
        self.setObjectName("code-snippet-container")
        self.setFrameStyle(QFrame.Shape.Box)
        
        # Main layout - single code display area
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Code display (now takes full area)
        self.code_display = QTextEdit()
        self.code_display.setObjectName("code-snippet-code-display")
        self.code_display.setReadOnly(True)
        self.code_display.setPlainText(self.code)
        
        # Set proper monospace font matching target design
        font = QFont("SF Mono", 14)
        if not font.exactMatch():
            font = QFont("Monaco", 14)
            if not font.exactMatch():
                font = QFont("Consolas", 14)
                if not font.exactMatch():
                    font = QFont("Courier New", 14)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.code_display.setFont(font)
        
        # Apply syntax highlighting if it's Python code
        if self.language.lower() == "python":
            self.syntax_highlighter = PythonSyntaxHighlighter(self.code_display.document())
        else:
            self.syntax_highlighter = None
        
        # Configure text edit behavior
        self.code_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.code_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Set minimum height for readability
        self.code_display.setMinimumHeight(100)  # Slightly taller since no header
        
        layout.addWidget(self.code_display)
        
        # Create overlay buttons (positioned absolutely)
        self._setup_overlay_buttons()
        
    def _setup_overlay_buttons(self):
        """Create and position the language and copy buttons as overlays."""
        
        # Language button (top-left overlay)
        self.language_button = QPushButton(self._format_language_display(self.language))
        self.language_button.setObjectName("code-snippet-language-button")
        self.language_button.setParent(self)
        self.language_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Copy button (top-right overlay)
        self.copy_button = QPushButton("Copy")
        self.copy_button.setObjectName("code-snippet-copy-button")
        self.copy_button.setParent(self)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set up button sizes and constraints
        self._configure_button_sizes()
        
    def _configure_button_sizes(self):
        """Configure button sizing following design specifications."""
        
        # Copy button - primary reference size
        self.copy_button.setMinimumSize(QSize(60, 28))
        self.copy_button.setMaximumSize(QSize(80, 32))
        
        # Language button - 70% of copy button height, more compact
        lang_height = 20  # 70% of 28px
        lang_width = 45   # Compact but readable
        self.language_button.setMinimumSize(QSize(lang_width, lang_height))
        self.language_button.setMaximumSize(QSize(70, 24))  # Allow some growth
        
    def _format_language_display(self, language: str) -> str:
        """Format language name for compact button display."""
        # Handle common language name mappings
        lang_map = {
            'python': 'PY',
            'javascript': 'JS',
            'typescript': 'TS',
            'json': 'JSON',
            'html': 'HTML',
            'css': 'CSS',
            'sql': 'SQL',
            'bash': 'SH',
            'shell': 'SH',
            'yaml': 'YAML',
            'xml': 'XML',
            'markdown': 'MD',
            'text': 'TXT'
        }
        
        lang_lower = language.lower()
        if lang_lower in lang_map:
            return lang_map[lang_lower]
        
        # For unknown languages, use first 3-4 characters
        if len(language) <= 4:
            return language.upper()
        else:
            return language[:4].upper()
            
    def resizeEvent(self, event):
        """Handle widget resize to reposition overlay buttons."""
        super().resizeEvent(event)
        self._position_overlay_buttons()
        
    def _position_overlay_buttons(self):
        """Position overlay buttons with responsive layout."""
        if not hasattr(self, 'language_button') or not hasattr(self, 'copy_button'):
            return
            
        # Get container dimensions
        container_width = self.width()
        container_height = self.height()
        
        # Language button positioning (top-left)
        lang_x = 8  # 8px from left edge
        lang_y = 8  # 8px from top edge
        self.language_button.move(lang_x, lang_y)
        
        # Copy button positioning (top-right)
        copy_width = self.copy_button.width()
        copy_x = container_width - copy_width - 8  # 8px from right edge
        copy_y = 8  # 8px from top edge
        self.copy_button.move(copy_x, copy_y)
        
        # Ensure buttons stay above content
        self.language_button.raise_()
        self.copy_button.raise_()
        
    def _setup_connections(self):
        """Setup signal connections for overlay buttons."""
        self.copy_button.clicked.connect(self._handle_copy)
        self.language_button.clicked.connect(self._handle_language_click)
        
    def _handle_language_click(self):
        """Handle language button click - emit signal for potential functionality."""
        self.language_clicked.emit(self.language)
        # Could be used for language switching, info display, etc.
        
    def _handle_copy(self):
        """Handle copy operation with overlay button feedback."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.code)
            
            # Show feedback on copy button
            self.show_copy_feedback()
            
            # Emit signal
            self.code_copied.emit(self.code)
            
            logger.debug(f"Copied {len(self.code)} characters to clipboard")
            
        except Exception as e:
            logger.error(f"Failed to copy code to clipboard: {e}")
            
    def show_copy_feedback(self):
        """Show visual feedback for successful copy operation."""
        original_text = self.copy_button.text()
        self.copy_button.setText("✓ Copied")
        self.copy_button.setEnabled(False)
        
        # Reset after 1.5 seconds
        def reset_button():
            self.copy_button.setText(original_text)
            self.copy_button.setEnabled(True)
            
        QTimer.singleShot(1500, reset_button)
            
    def set_code(self, code: str, language: str = None):
        """Update the code content and optionally the language."""
        self.code = code
        if language:
            self.language = language
            if hasattr(self, 'language_button'):
                self.language_button.setText(self._format_language_display(language))
            
        self.code_display.setPlainText(self.code)
        
        # Re-apply syntax highlighting if language changed
        if language and language.lower() == "python":
            if not hasattr(self, 'syntax_highlighter') or self.syntax_highlighter is None:
                self.syntax_highlighter = PythonSyntaxHighlighter(self.code_display.document())
        elif language and language.lower() != "python":
            # Remove syntax highlighting for non-Python code
            if hasattr(self, 'syntax_highlighter') and self.syntax_highlighter is not None:
                self.syntax_highlighter.setDocument(None)
                self.syntax_highlighter = None
        
    def apply_theme(self, colors: ColorSystem):
        """Apply theme colors to the widget with new overlay button design."""
        self.theme_colors = colors
        
        # Apply overlay button styling
        self._apply_overlay_button_styling(colors)
        
        # Get styling from StyleTemplates if available
        if THEME_SYSTEM_AVAILABLE:
            try:
                from ...ui.themes.style_templates import StyleTemplates
                style_css = StyleTemplates.get_code_snippet_widget_overlay_style(colors)
                self.setStyleSheet(style_css)
            except Exception as e:
                logger.warning(f"Failed to apply theme styling: {e}")
                self._apply_basic_styling(colors)
        else:
            self._apply_basic_styling(colors)
            
    def _apply_overlay_button_styling(self, colors: ColorSystem):
        """Apply theme-aware styling to overlay buttons with accessibility compliance."""
        if not hasattr(self, 'language_button') or not hasattr(self, 'copy_button'):
            return
            
        # Import color utilities for accessibility
        if THEME_SYSTEM_AVAILABLE:
            try:
                from ...ui.themes.color_system import ColorUtils
                
                # Language button styling - subtle and compact
                lang_bg_color = self._adjust_color_opacity(colors.background_tertiary, 0.4)
                lang_text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(
                    colors.background_tertiary, colors, min_ratio=4.5
                )
                lang_hover_color = self._adjust_color_opacity(colors.background_secondary, 0.6)
                lang_border_color = colors.border_secondary
                
                lang_style = f"""
                QPushButton#code-snippet-language-button {{
                    background-color: {lang_bg_color};
                    color: {lang_text_color};
                    border: 1px solid {lang_border_color};
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-size: 10px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
                }}
                QPushButton#code-snippet-language-button:hover {{
                    background-color: {lang_hover_color};
                    border-color: {colors.border_primary};
                }}
                QPushButton#code-snippet-language-button:pressed {{
                    background-color: {colors.interactive_active};
                }}
                """
                
                # Copy button styling - more prominent
                copy_text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(
                    colors.interactive_normal, colors, min_ratio=4.5
                )
                
                copy_style = f"""
                QPushButton#code-snippet-copy-button {{
                    background-color: {colors.interactive_normal};
                    color: {copy_text_color};
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
                    opacity: 1.0;
                }}
                QPushButton#code-snippet-copy-button:hover {{
                    background-color: {colors.interactive_hover};
                    border-color: {colors.border_focus};
                    opacity: 1.0;
                }}
                QPushButton#code-snippet-copy-button:pressed {{
                    background-color: {colors.interactive_active};
                    opacity: 1.0;
                }}
                QPushButton#code-snippet-copy-button:disabled {{
                    background-color: {colors.interactive_disabled};
                    color: {colors.text_disabled};
                    opacity: 1.0;
                }}
                """
                
                # Apply styles to buttons
                self.language_button.setStyleSheet(lang_style)
                self.copy_button.setStyleSheet(copy_style)
                
            except Exception as e:
                logger.warning(f"Failed to apply advanced button styling: {e}")
                self._apply_basic_button_styling(colors)
        else:
            self._apply_basic_button_styling(colors)
            
    def _apply_basic_button_styling(self, colors: ColorSystem):
        """Apply basic button styling when advanced theme system is unavailable."""
        if not hasattr(self, 'language_button') or not hasattr(self, 'copy_button'):
            return
            
        # Basic fallback styling
        lang_style = f"""
        QPushButton#code-snippet-language-button {{
            background-color: rgba(100, 100, 100, 0.3);
            color: {colors.text_secondary if hasattr(colors, 'text_secondary') else '#666666'};
            border: 1px solid rgba(150, 150, 150, 0.5);
            border-radius: 3px;
            padding: 2px 4px;
            font-size: 10px;
            font-weight: 500;
        }}
        """
        
        copy_style = f"""
        QPushButton#code-snippet-copy-button {{
            background-color: #E0E0E0;
            color: {colors.text_primary if hasattr(colors, 'text_primary') else '#333333'};
            border: 1px solid #A0A0A0;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: 500;
            opacity: 1.0;
        }}
        QPushButton#code-snippet-copy-button:hover {{
            background-color: #D0D0D0;
            opacity: 1.0;
        }}
        QPushButton#code-snippet-copy-button:pressed {{
            background-color: #C0C0C0;
            opacity: 1.0;
        }}
        """
        
        self.language_button.setStyleSheet(lang_style)
        self.copy_button.setStyleSheet(copy_style)
        
    def _adjust_color_opacity(self, hex_color: str, opacity: float) -> str:
        """Convert hex color to rgba with specified opacity."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {opacity})"
        except:
            return f"rgba(100, 100, 100, {opacity})"  # Fallback
            
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