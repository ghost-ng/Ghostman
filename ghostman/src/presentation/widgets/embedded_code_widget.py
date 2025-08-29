"""
Embedded code snippet widget for REPL integration.
Provides full control over formatting without CSS inheritance issues.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QApplication, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QFontMetrics, QPalette, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, QIcon
import re
from typing import Optional, Dict
import logging

# Import the universal color system
try:
    from .universal_syntax_colors import get_universal_syntax_colors, SyntaxColorScheme
    UNIVERSAL_COLORS_AVAILABLE = True
except ImportError:
    UNIVERSAL_COLORS_AVAILABLE = False

logger = logging.getLogger('ghostman.embedded_code_widget')

# Theme system imports
try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False


class CodeContentWidget(QTextEdit):
    """Custom text widget for code display with solid background."""
    
    def __init__(self, code: str, language: str = "", theme_colors: dict = None):
        super().__init__()
        self.setReadOnly(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.code = code
        self.language = language
        self.theme_colors = theme_colors or self._get_default_colors()
        
        self._setup_widget()
        self._apply_syntax_highlighting()
        
    def _get_default_colors(self):
        """Default color scheme - adaptive fallback."""
        return {
            'bg_primary': '#002b36',      # Solarized Dark base03
            'bg_secondary': '#073642',    # Solarized Dark base02
            'bg_tertiary': '#094352',     # Slightly lighter for code background 
            'text_primary': '#839496',    # Solarized Dark base0
            'text_secondary': '#586e75',  # Solarized Dark base01
            'border': '#073642',          # Solarized Dark base02
            'background_primary': '#002b36',
            'background_secondary': '#073642', 
            'background_tertiary': '#094352',
            # Let universal colors handle syntax highlighting
        }
    
    def _setup_widget(self):
        """Configure the widget appearance."""
        # CRITICAL: Preserve indentation by setting code with proper whitespace handling
        # Use setPlainText but ensure tab/space preservation
        self.setPlainText(self.code)
        
        # Configure monospace font with proper tab width
        font = QFont('Consolas')
        if not font.exactMatch():
            font = QFont('SF Mono')
        if not font.exactMatch():
            font = QFont('Monaco')
        if not font.exactMatch():
            font = QFont('Courier New')
            
        font.setPixelSize(14)
        font.setFixedPitch(True)  # Ensure monospace
        self.setFont(font)
        
        # Set proper tab width (4 spaces equivalent)
        metrics = QFontMetrics(font)
        tab_width = metrics.horizontalAdvance(' ') * 4
        self.setTabStopDistance(tab_width)
        
        # CRITICAL: Set solid background color that fills ALL space
        selection_bg = self.theme_colors.get('selection', '#073642')  # Darker selection for dark themes
        
        # Map color keys to handle both old and new theme formats
        bg_color = self.theme_colors.get('bg_tertiary', self.theme_colors.get('background_tertiary', '#094352'))
        text_color = self.theme_colors.get('text_primary', '#839496')
        border_color = self.theme_colors.get('border', self.theme_colors.get('border_subtle', '#073642'))
        
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                padding: 16px;
                border: 1px solid {border_color};
                border-radius: 6px;
                selection-background-color: {selection_bg};
                font-family: 'Consolas', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
                white-space: pre-wrap;
                tab-size: 4;
            }}
            QTextEdit::viewport {{
                background-color: {bg_color};
            }}
        """)
        
        # Set line height and preserve whitespace
        self.document().setDefaultStyleSheet(f"""
            * {{
                line-height: 150%;
                background-color: {bg_color};
                white-space: pre;
                tab-size: 4;
            }}
        """)
        
        # Calculate and set appropriate height
        metrics = QFontMetrics(font)
        line_count = self.code.count('\n') + 1
        line_height = metrics.lineSpacing()
        padding = 32  # 16px top + 16px bottom
        min_height = max(60, line_count * line_height + padding)
        self.setMinimumHeight(min_height)
        self.setMaximumHeight(min_height + 20)  # Small buffer for scrollbar
        
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting using Pygments for any language."""
        # Check if content is already highlighted by the first system
        if self.language and self.language.startswith('pre-highlighted-'):
            logger.info(f"🔄 Skipping second highlighting - content already processed by first system")
            return
        
        # FORCE Pygments usage - no fallbacks to keyword-based highlighting
        try:
            from .pygments_syntax_highlighter import PygmentsSyntaxHighlighter
            logger.debug(f"🎨 Attempting Pygments highlighting for language: {self.language}")
            
            # Use Pygments for universal language support (500+ languages)
            self.highlighter = PygmentsSyntaxHighlighter(
                self.document(), 
                language=self.language,
                code=self.code,
                theme_colors=self.theme_colors
            )
            logger.info(f"✅ PYGMENTS ACTIVE: Applied token-based highlighting for {self.language} (lexer: {self.highlighter.lexer.name})")
            
        except ImportError as e:
            logger.error(f"❌ CRITICAL: Pygments highlighter import failed: {e}")
            logger.error(f"❌ NO FALLBACK - Code will have no syntax highlighting")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Pygments highlighting failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            logger.error(f"❌ NO FALLBACK - Code will have no syntax highlighting")


# Removed UniversalPythonHighlighter - using only Pygments for token-based highlighting


class LanguageButton(QPushButton):
    """Small language indicator button positioned on the left side."""
    
    # Signal emitted when language button is clicked
    language_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None, language=""):
        # Format language display name
        display_name = self._get_language_display_name(language)
        super().__init__(display_name, parent)
        
        self.language = language
        self.setObjectName("language-button")
        self._setup_style()
        
        # Emit signal when clicked
        self.clicked.connect(lambda: self.language_clicked.emit(self.language))
        
    def _get_language_display_name(self, language: str) -> str:
        """Get short display name for language - dynamic based on actual language."""
        if not language or language == 'text':
            return "TXT"
            
        # Handle pre-highlighted languages
        if language.startswith('pre-highlighted-'):
            base_lang = language.replace('pre-highlighted-', '')
            language = base_lang
            
        # Common short mappings for readability
        common_short_names = {
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
            'dockerfile': 'DOCK',
            'makefile': 'MAKE',
        }
        
        # Check if we have a common short name
        lang_lower = language.lower()
        if lang_lower in common_short_names:
            return common_short_names[lang_lower]
            
        # For other languages, use first 4 characters uppercase for button
        # This scales to any language Pygments detects without hardcoding
        display_name = language.upper()[:4]
        
        # Handle some special cases that might look weird
        if display_name == 'CSHA':
            return 'C#'
        elif display_name == 'CPLU':
            return 'C++'
        elif display_name == 'OBJE':
            return 'OBJC'
            
        return display_name
        
    def _setup_style(self):
        """Setup basic styling that will be enhanced by theme."""
        # Smaller than copy button (20px vs 28px height)
        self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def apply_theme_style(self, theme_colors: Dict[str, str]):
        """Apply theme-aware styling with different color from copy button."""
        # Determine if theme is dark or light
        bg_color = theme_colors.get('bg_tertiary', theme_colors.get('background_tertiary', '#1a1a1a'))
        is_dark = self._calculate_luminance(bg_color) < 0.5
        
        if is_dark:
            # Dark theme - use tertiary background for differentiation
            normal_bg = theme_colors.get('background_tertiary', 'rgba(255, 255, 255, 0.08)')
            hover_bg = "rgba(255, 255, 255, 0.15)"
            active_bg = "rgba(255, 255, 255, 0.2)"
            text_color = theme_colors.get('text_secondary', '#a0a0a0')
            border_color = "rgba(255, 255, 255, 0.2)"
        else:
            # Light theme - use tertiary background for differentiation  
            normal_bg = theme_colors.get('background_tertiary', 'rgba(0, 0, 0, 0.03)')
            hover_bg = "rgba(0, 0, 0, 0.08)"
            active_bg = "rgba(0, 0, 0, 0.12)"
            text_color = theme_colors.get('text_secondary', '#666666')
            border_color = "rgba(0, 0, 0, 0.15)"
            
        self.setStyleSheet(f"""
        QPushButton#language-button {{
            background-color: {normal_bg};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
            padding: 2px 4px;
        }}
        QPushButton#language-button:hover {{
            background-color: {hover_bg};
        }}
        QPushButton#language-button:pressed {{
            background-color: {active_bg};
        }}
        QPushButton#language-button:disabled {{
            opacity: 0.5;
        }}
        """)
        
    def _calculate_luminance(self, color: str) -> float:
        """Calculate relative luminance of a color."""
        try:
            # Handle rgba colors
            if 'rgba' in color:
                return 0.5  # Default middle luminance for rgba
                
            color = color.lstrip('#')
            if len(color) < 6:
                return 0.5  # Default for invalid colors
                
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            r, g, b = r/255.0, g/255.0, b/255.0
            
            # Apply gamma correction
            r = r/12.92 if r <= 0.03928 else pow((r + 0.055)/1.055, 2.4)
            g = g/12.92 if g <= 0.03928 else pow((g + 0.055)/1.055, 2.4)
            b = b/12.92 if b <= 0.03928 else pow((b + 0.055)/1.055, 2.4)
            
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        except:
            return 0.5  # Safe fallback


class CopyButton(QPushButton):
    """Floating copy button with smooth animations and theme awareness."""
    
    def __init__(self, parent=None):
        super().__init__("Copy", parent)
        self.setObjectName("copy-button")
        self._setup_animations()
        self._setup_style()
        
    def _setup_animations(self):
        """Setup smooth fade in/out animations."""
        self.opacity_effect = None
        self.fade_in_animation = None
        self.fade_out_animation = None
        
    def _setup_style(self):
        """Setup basic styling that will be enhanced by theme."""
        self.setFixedSize(60, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def apply_theme_style(self, theme_colors: Dict[str, str]):
        """Apply theme-aware styling to the copy button."""
        # Determine if theme is dark or light
        bg_color = theme_colors.get('bg_tertiary', theme_colors.get('background_tertiary', '#1a1a1a'))
        is_dark = self._calculate_luminance(bg_color) < 0.5
        
        if is_dark:
            # Dark theme styling
            normal_bg = "rgba(255, 255, 255, 0.1)"
            hover_bg = "rgba(255, 255, 255, 0.2)"
            active_bg = "rgba(255, 255, 255, 0.3)"
            text_color = theme_colors.get('text_primary', '#ffffff')
            border_color = "rgba(255, 255, 255, 0.3)"
        else:
            # Light theme styling  
            normal_bg = "rgba(0, 0, 0, 0.05)"
            hover_bg = "rgba(0, 0, 0, 0.1)"
            active_bg = "rgba(0, 0, 0, 0.15)"
            text_color = theme_colors.get('text_primary', '#000000')
            border_color = "rgba(0, 0, 0, 0.2)"
            
        self.setStyleSheet(f"""
        QPushButton#copy-button {{
            background-color: {normal_bg};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            padding: 4px 8px;
        }}
        QPushButton#copy-button:hover {{
            background-color: {hover_bg};
        }}
        QPushButton#copy-button:pressed {{
            background-color: {active_bg};
        }}
        QPushButton#copy-button:disabled {{
            opacity: 0.5;
        }}
        """)
        
    def _calculate_luminance(self, color: str) -> float:
        """Calculate relative luminance of a color."""
        try:
            color = color.lstrip('#')
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            r, g, b = r/255.0, g/255.0, b/255.0
            
            # Apply gamma correction
            def gamma_correct(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
                
            r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        except:
            return 0.0
            
    def show_success_feedback(self):
        """Show visual feedback for successful copy."""
        original_text = self.text()
        self.setText("Copied!")
        self.setEnabled(False)
        
        # Reset after 1.5 seconds
        QTimer.singleShot(1500, lambda: (
            self.setText(original_text),
            self.setEnabled(True)
        ))


class EmbeddedCodeSnippetWidget(QWidget):
    """
    Complete code snippet widget with floating copy button and universal theme support.
    Designed to be embedded in REPL without CSS inheritance issues.
    """
    
    copy_requested = pyqtSignal(str)
    
    def __init__(self, code: str, language: str = "", theme_colors: dict = None, parent=None):
        super().__init__(parent)
        self.code = code
        self.language = language or self._detect_language(code)
        self.theme_colors = theme_colors or self._get_default_colors()
        self.copy_button = None
        
        # Register with theme manager for automatic theme updates
        self._init_theme_system()
        
        self._setup_ui()
        
    def _get_default_colors(self):
        """Default color scheme - Solarized Dark compatible."""
        return {
            'bg_primary': '#002b36',      # Solarized Dark base03
            'bg_secondary': '#073642',    # Solarized Dark base02 
            'bg_tertiary': '#094352',     # Slightly lighter for code background
            'text_primary': '#839496',    # Solarized Dark base0
            'text_secondary': '#586e75',  # Solarized Dark base01
            'border': '#073642',          # Solarized Dark base02
            'interactive': '#073642',     # Match secondary background
            'interactive_hover': '#094352', # Match tertiary background
            'keyword': '#859900',         # Solarized Dark green
            'string': '#2aa198',          # Solarized Dark cyan
            'comment': '#586e75',         # Solarized Dark base01
            'function': '#b58900',        # Solarized Dark yellow
            'number': '#d33682',          # Solarized Dark magenta
            'builtin': '#cb4b16',         # Solarized Dark orange
        }
    
    def _detect_language(self, code: str) -> str:
        """Use Pygments for professional language detection with enhanced patterns."""
        try:
            # Import Pygments functions
            from pygments.lexers import guess_lexer, get_lexer_by_name
            from pygments.util import ClassNotFound
            import re
            
            # Clean code for analysis
            clean_code = code.strip()
            
            # High-confidence pattern checks for languages Pygments might miss
            patterns = {
                'go': [
                    r'package\s+\w+',
                    r'func\s+\w+\s*\(',
                    r'import\s+\(\s*["\']',
                    r'fmt\.Print'
                ],
                'rust': [
                    r'fn\s+\w+\s*\(',
                    r'let\s+\w+:\s*\w+',
                    r'println!\s*\(',
                    r'use\s+std::'
                ],
                'perl': [
                    r'use\s+(strict|warnings)',
                    r'my\s+\$\w+',
                    r'print\s+".*\\n"',
                    r'#!/usr/bin/perl'
                ],
                'python': [
                    r'def\s+\w+\s*\(',
                    r'if\s+__name__\s*==\s*["\']__main__["\']',
                    r'import\s+\w+',
                    r'from\s+\w+\s+import'
                ],
                'javascript': [
                    r'function\s+\w+\s*\(',
                    r'console\.log\s*\(',
                    r'const\s+\w+\s*=',
                    r'let\s+\w+\s*='
                ]
            }
            
            # Check patterns for specific languages
            for lang, lang_patterns in patterns.items():
                matches = sum(1 for pattern in lang_patterns if re.search(pattern, clean_code))
                if matches >= 2:  # Require at least 2 pattern matches
                    logger.debug(f"🎯 Code widget: Pattern-based detection found '{lang}' ({matches} matches)")
                    return lang
            
            # JSON detection
            if clean_code.startswith('{') and clean_code.endswith('}'):
                try:
                    import json
                    json.loads(clean_code)
                    return 'json'
                except:
                    pass
            
            # Shebang detection
            if clean_code.startswith('#!/'):
                first_line = clean_code.split('\n')[0]
                if 'python' in first_line:
                    return 'python'
                elif 'perl' in first_line:
                    return 'perl'
                elif 'bash' in first_line or '/bin/sh' in first_line:
                    return 'bash'
                elif 'node' in first_line:
                    return 'javascript'
            
            # Use Pygments for detection
            lexer = guess_lexer(clean_code)
            
            # Get the primary alias or name
            if lexer.aliases:
                detected_lang = lexer.aliases[0]
            else:
                detected_lang = lexer.name.lower()
            
            # Handle common Pygments misdetections
            if detected_lang in ['python', 'css+lasso', 'scdoc'] and any(re.search(p, clean_code) for p in patterns.get('rust', [])):
                detected_lang = 'rust'
            elif detected_lang in ['python', 'text', 'scdoc'] and any(re.search(p, clean_code) for p in patterns.get('go', [])):
                detected_lang = 'go'
            elif detected_lang in ['scdoc', 'text'] and any(re.search(p, clean_code) for p in patterns.get('python', [])):
                detected_lang = 'python'
            elif detected_lang in ['text', 'css'] and any(re.search(p, clean_code) for p in patterns.get('javascript', [])):
                detected_lang = 'javascript'
            
            logger.debug(f"🎯 Code widget: Pygments detected '{detected_lang}' (lexer: {lexer.name})")
            return detected_lang
            
        except (ImportError, ClassNotFound, Exception) as e:
            logger.warning(f"⚠️ Code widget language detection failed: {e}")
            return 'text'
    
    def _init_theme_system(self):
        """Initialize theme system connection."""
        if THEME_SYSTEM_AVAILABLE:
            try:
                theme_manager = get_theme_manager()
                # Register with theme manager using set_theme_colors method
                theme_manager.register_widget(self, "set_theme_colors")
                logger.debug("EmbeddedCodeSnippetWidget registered with theme system")
            except Exception as e:
                logger.warning(f"Failed to initialize theme system: {e}")
        else:
            logger.debug("Theme system not available for EmbeddedCodeSnippetWidget")
    
    def _setup_ui(self):
        """Setup the widget UI with overlay language and copy buttons."""
        # Main layout with no margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create container for positioning elements
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Code content with solid background (full area - no banner)
        self.code_content = CodeContentWidget(self.code, self.language, self.theme_colors)
        container_layout.addWidget(self.code_content)
        
        # Create floating language button (left side)
        if self.language and not self.language.startswith('pre-highlighted-'):
            self.language_button = LanguageButton(container, self.language)
            self.language_button.apply_theme_style(self.theme_colors)
        else:
            self.language_button = None
        
        # Create floating copy button (right side)
        self.copy_button = CopyButton(container)
        self.copy_button.apply_theme_style(self.theme_colors)
        self.copy_button.clicked.connect(self._handle_copy)
        
        # Position buttons initially (will be repositioned in resizeEvent)
        self._position_buttons()
        
        # Hide buttons by default
        if self.language_button:
            self.language_button.hide()
        self.copy_button.hide()
        
        layout.addWidget(container)
        
        # Set up hover events for button visibility
        container.enterEvent = self._on_enter
        container.leaveEvent = self._on_leave
        
        # Set size policy
        self.setMinimumHeight(60)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().Policy.Minimum
        )
        
    def _on_enter(self, event):
        """Show buttons on hover."""
        if self.language_button:
            self.language_button.show()
        if self.copy_button:
            self.copy_button.show()
            
    def _on_leave(self, event):
        """Hide buttons when not hovering."""
        if self.language_button:
            self.language_button.hide()
        if self.copy_button:
            self.copy_button.hide()
    
    def _position_buttons(self):
        """Position overlay buttons."""
        container_width = self.width() if self.width() > 0 else 400  # Fallback width
        
        # Position language button (left side)
        if self.language_button:
            self.language_button.move(8, 8)
        
        # Position copy button (right side)
        if self.copy_button:
            copy_width = self.copy_button.sizeHint().width()
            self.copy_button.move(container_width - copy_width - 8, 8)
    
    def resizeEvent(self, event):
        """Reposition buttons when widget is resized."""
        super().resizeEvent(event)
        self._position_buttons()
        if self.copy_button:
            self.copy_button.hide()
            
    def resizeEvent(self, event):
        """Reposition copy button when widget is resized."""
        super().resizeEvent(event)
        if self.copy_button:
            self.copy_button.move(self.width() - 70, 10)
        
    def _create_header(self) -> QWidget:
        """Create the header widget."""
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors['bg_secondary']};
                border-bottom: 1px solid {self.theme_colors['border']};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Left side: title and language tag
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)
        
        # Title
        title = QLabel(f"{self.language.title() if self.language else 'Code'} Snippet")
        title.setStyleSheet(f"""
            color: {self.theme_colors['text_primary']};
            font-weight: 600;
            font-size: 13px;
        """)
        left_layout.addWidget(title)
        
        # Language tag
        if self.language:
            lang_tag = QLabel(self.language.upper())
            lang_tag.setStyleSheet(f"""
                background-color: #f1f8ff;
                color: #0366d6;
                padding: 3px 8px;
                border-radius: 3px;
                border: 1px solid #c8e1ff;
                font-size: 11px;
                font-weight: 500;
            """)
            left_layout.addWidget(lang_tag)
        
        left_layout.addStretch()
        layout.addLayout(left_layout)
        
        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme_colors['text_primary']};
                font-size: 12px;
                padding: 6px 12px;
                background-color: {self.theme_colors['interactive']};
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.theme_colors['interactive_hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme_colors['border']};
            }}
        """)
        copy_btn.clicked.connect(self._handle_copy)
        layout.addWidget(copy_btn)
        
        return header
    
    def _handle_copy(self):
        """Handle copy button click with enhanced feedback."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.code)
            self.copy_requested.emit(self.code)
            
            # Visual feedback
            if self.copy_button:
                self.copy_button.show_success_feedback()
                
            logger.debug(f"Copied {len(self.code)} characters to clipboard")
            
        except Exception as e:
            logger.error(f"Failed to copy code: {e}")
    
    def set_theme_colors(self, colors: dict):
        """Update theme colors for all components."""
        self.theme_colors = colors
        
        # Update code content colors
        if hasattr(self, 'code_content'):
            self.code_content.theme_colors = colors
            self.code_content._setup_widget()
            self.code_content._apply_syntax_highlighting()
            
        # Update copy button colors
        if self.copy_button:
            self.copy_button.apply_theme_style(colors)
            
        logger.debug(f"Updated theme colors for code snippet widget")