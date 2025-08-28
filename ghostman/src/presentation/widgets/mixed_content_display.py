"""
Mixed content display widget for REPL.
Supports both HTML text and embedded custom widgets with full formatting control.
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QLabel, 
    QSizePolicy, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
import re
from typing import Optional, List, Tuple, Dict, Any
import logging
import html

# Import our custom code widget
try:
    from .embedded_code_widget import EmbeddedCodeSnippetWidget
    CODE_WIDGET_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import code widget: {e}")
    CODE_WIDGET_AVAILABLE = False
    # Create a minimal fallback
    class EmbeddedCodeSnippetWidget:
        def __init__(self, code, language, colors):
            self.code = code

logger = logging.getLogger('ghostman.mixed_content_display')

# Theme system imports
try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False


class MixedContentDisplay(QScrollArea):
    """
    Scrollable widget that can contain both HTML text and custom widgets.
    Replaces QTextEdit to provide full control over embedded content.
    """
    
    link_clicked = pyqtSignal(str)  # Emitted when a link is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store references to widgets for cleanup
        self.content_widgets = []
        self.theme_colors = None
        
        # Store original content for re-rendering on theme change
        self.content_history = []  # List of (content, message_style, widget_type) tuples
        
        # Register with theme manager for automatic updates
        self._init_theme_system()
        
        # Container widget for the scrollable content
        self.content_widget = QWidget()
        self.content_widget.setObjectName("MixedContentContainer")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setSpacing(4)  # Tighter spacing
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Configure scroll area
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Set frame style to match QTextEdit appearance
        self.setFrameStyle(QFrame.Shape.StyledPanel)
    
    def _init_theme_system(self):
        """Initialize theme system connection."""
        if THEME_SYSTEM_AVAILABLE:
            try:
                theme_manager = get_theme_manager()
                # Register with theme manager using set_theme_colors method
                theme_manager.register_widget(self, "set_theme_colors")
                logger.debug("MixedContentDisplay registered with theme system")
            except Exception as e:
                logger.warning(f"Failed to initialize theme system: {e}")
        else:
            logger.debug("Theme system not available for MixedContentDisplay")
        
    def set_theme_colors(self, colors: Dict[str, str]):
        """Update theme colors and re-render all content with new theme."""
        self.theme_colors = colors
        self._update_stylesheet()
        
        # Re-render all content with new theme colors
        self._rerender_all_content()
        
    def _update_stylesheet(self):
        """Update the stylesheet based on theme colors."""
        if not self.theme_colors:
            return
            
        bg_color = self.theme_colors.get('bg_primary', self.theme_colors.get('background_primary', '#1a1a1a'))
        text_color = self.theme_colors.get('text_primary', '#ffffff')
        border_color = self.theme_colors.get('border', self.theme_colors.get('border_subtle', '#3a3a3a'))
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: 1px solid {border_color};
            }}
            QWidget#MixedContentContainer {{
                background-color: {bg_color};
            }}
        """)
        
    def _rerender_all_content(self):
        """Re-render all content with new theme colors."""
        # Clear existing widgets
        for widget in self.content_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.content_widgets.clear()
        
        # Re-add all content with new theme
        for content, message_style, widget_type in self.content_history:
            if widget_type == 'html':
                self._add_html_content_internal(content, message_style, store_history=False)
            elif widget_type == 'code':
                self._add_code_snippet_internal(content[0], content[1], store_history=False)
    
    def add_html_content(self, html_text: str, message_style: str = "normal"):
        """
        Add HTML content as a label.
        Preserves HTML formatting while maintaining theme consistency.
        """
        # Store in history for re-rendering
        self.content_history.append((html_text, message_style, 'html'))
        self._add_html_content_internal(html_text, message_style, store_history=False)
    
    def _add_html_content_internal(self, html_text: str, message_style: str = "normal", store_history: bool = True):
        """Internal method to add HTML content without storing history."""
        label = QLabel()
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        label.setOpenExternalLinks(False)  # We'll handle links manually
        label.setAutoFillBackground(False)  # Prevent Qt from filling background
        label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # Make widget transparent
        
        # Process the HTML to extract and handle code blocks
        processed_html, code_blocks = self._extract_code_blocks(html_text)
        
        # Force no backgrounds by adding inline styles to all HTML elements
        import re
        
        # Add inline style to all HTML opening tags to remove backgrounds
        def add_background_removal(match):
            full_match = match.group(0)
            tag_name = match.group(1)
            
            # If already has style attribute, append to it
            if 'style=' in full_match:
                # Replace existing style attribute
                full_match = re.sub(r'style="([^"]*)"', r'style="\1; background: none !important; background-color: transparent !important;"', full_match)
            else:
                # Add new style attribute before closing >
                full_match = full_match[:-1] + ' style="background: none !important; background-color: transparent !important;">'
            
            return full_match
        
        # Apply to all HTML tags except code-related tags (to preserve code widget backgrounds)
        processed_html = re.sub(r'<(p|div|span|h[1-6]|ul|ol|li|blockquote|a)(?:\s[^>]*)?>(?!</)', add_background_removal, processed_html)
        
        if code_blocks:
            # If we have code blocks, add the text before the first code block
            parts = processed_html.split("[CODE_BLOCK_PLACEHOLDER]")
            
            for i, part in enumerate(parts):
                if part.strip():
                    # Add text part
                    text_label = QLabel()
                    text_label.setWordWrap(True)
                    text_label.setTextInteractionFlags(
                        Qt.TextInteractionFlag.TextSelectableByMouse | 
                        Qt.TextInteractionFlag.LinksAccessibleByMouse
                    )
                    text_label.setAutoFillBackground(False)  # Prevent Qt from filling background
                    text_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # Make widget transparent
                    text_label.setText(part)
                    self._apply_label_styling(text_label, message_style)
                    self.content_layout.addWidget(text_label)
                    self.content_widgets.append(text_label)
                    
                    # Connect link handling
                    text_label.linkActivated.connect(self._handle_link_click)
                
                # Add code block if there's one corresponding to this position
                if i < len(code_blocks):
                    code, language = code_blocks[i]
                    self.add_code_snippet(code, language)
        else:
            # No code blocks, just add the HTML as is
            label.setText(processed_html)
            self._apply_label_styling(label, message_style)
            self.content_layout.addWidget(label)
            self.content_widgets.append(label)
            
            # Connect link handling
            label.linkActivated.connect(self._handle_link_click)
        
        # Auto-scroll to bottom
        QTimer.singleShot(10, self.scroll_to_bottom)
        
    def _extract_code_blocks(self, html_text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Extract code blocks from HTML content using robust parsing.
        Returns processed HTML with placeholders and list of (code, language) tuples.
        """
        code_blocks = []
        
        # Enhanced pattern to match the complete PygmentsRenderer structure
        # This pattern handles nested divs and captures the entire code block
        code_pattern = r'<div[^>]*style="[^"]*background-color:[^"]*"[^>]*>.*?<pre[^>]*>(.*?)</pre>.*?</div>\s*</div>'
        
        def replace_code_block(match):
            try:
                # Extract the code content from the <pre> tag
                code_content = match.group(1)
                logger.debug(f"Raw extracted content: {repr(code_content[:100])}{'...' if len(code_content) > 100 else ''}")
                
                # COMPREHENSIVE HTML tag removal for Pygments content
                # First, remove all HTML tags systematically 
                code_content = re.sub(r'<[^>]+>', '', code_content)
                
                # Unescape HTML entities
                code_content = html.unescape(code_content)
                
                # Additional cleanup for Pygments artifacts
                # Remove any remaining CSS-related artifacts
                code_content = re.sub(r'style="[^"]*"', '', code_content)
                code_content = re.sub(r'class="[^"]*"', '', code_content)
                
                # Clean up whitespace artifacts from HTML stripping
                code_content = re.sub(r'\n\s*\n', '\n', code_content)  # Remove extra blank lines
                code_content = re.sub(r'^\s+', '', code_content, flags=re.MULTILINE)  # Remove leading spaces on each line
                
                logger.debug(f"Cleaned code content: {len(code_content)} chars, first 50: {repr(code_content[:50])}")
                
                # Clean up extra whitespace but preserve code structure
                code_content = code_content.strip()
                
                # Try to detect language from the full match context
                language = self._detect_language_from_html(match.group(0))
                
                # Check if this code is already syntax-highlighted
                is_already_highlighted = self._is_code_already_highlighted(match.group(1))
                if is_already_highlighted:
                    logger.debug(f"🔄 Code block already highlighted by first system - using plain display")
                    # For already-highlighted content, we'll use a special flag
                    language = f"pre-highlighted-{language}"
                
                code_blocks.append((code_content, language))
                logger.debug(f"Extracted code block: {len(code_content)} chars, language: {language}, pre-highlighted: {is_already_highlighted}")
                
                return "[CODE_BLOCK_PLACEHOLDER]"
                
            except Exception as e:
                logger.warning(f"Failed to parse code block: {e}")
                # Return placeholder to avoid HTML artifacts
                code_blocks.append(("# Code parsing error", "text"))
                return "[CODE_BLOCK_PLACEHOLDER]"
        
        # Apply the pattern matching with error handling
        try:
            processed_html = re.sub(code_pattern, replace_code_block, html_text, flags=re.DOTALL)
            
            # Additional cleanup for any remaining code block artifacts
            processed_html = self._cleanup_remaining_artifacts(processed_html)
            
            # Specific cleanup for the HTML artifacts you mentioned
            cleanup_patterns = [
                r'</div>\s*</div>\s*<br>\s*',    # The exact artifact pattern
                r'<div[^>]*>\s*</div>',          # Empty divs
                r'<br>\s*</div>',                # BR before closing div
                r'\s*</div>\s*$',                # Trailing closing divs
                r'^\s*<br>\s*',                  # Leading br tags
            ]
            
            for cleanup_pattern in cleanup_patterns:
                processed_html = re.sub(cleanup_pattern, '', processed_html, flags=re.MULTILINE | re.DOTALL)
            
            # Final trim
            processed_html = processed_html.strip()
            
            logger.debug(f"Processed HTML: found {len(code_blocks)} code blocks")
            
        except Exception as e:
            logger.error(f"HTML processing failed: {e}")
            # Fallback: return original content without code extraction
            return html_text, []
        
        return processed_html, code_blocks
        
    def _detect_language_from_html(self, html_block: str) -> str:
        """
        Extract code from HTML and use Pygments for detection.
        """
        # First strip HTML tags to get clean code
        import html as html_module
        
        # Remove HTML tags
        clean_code = re.sub(r'<[^>]+>', '', html_block)
        clean_code = html_module.unescape(clean_code)
        clean_code = clean_code.strip()
        
        if not clean_code:
            return 'text'
            
        # Use Pygments to detect the language from the clean code
        return self._detect_language_from_content(clean_code)
        
    def _is_code_already_highlighted(self, raw_html_content: str) -> bool:
        """
        Detect if code content has already been syntax-highlighted by Pygments.
        
        Args:
            raw_html_content: The raw HTML content from the <pre> tag
            
        Returns:
            True if the content appears to be already highlighted
        """
        # Look for Pygments-style HTML elements
        pygments_indicators = [
            r'<span[^>]*color[^>]*>',  # Inline color styling
            r'<span[^>]*class="[^"]*"[^>]*>',  # CSS classes
            r'style="[^"]*color[^"]*"',  # Inline CSS with colors
            r'<span[^>]*style="[^"]*font-weight[^"]*"[^>]*>',  # Font styling
        ]
        
        for pattern in pygments_indicators:
            if re.search(pattern, raw_html_content, re.IGNORECASE):
                return True
        
        return False

    def _detect_language_from_content(self, content: str) -> str:
        """
        Use Pygments' built-in language detection instead of hardcoded patterns.
        """
        try:
            # Import Pygments lexer guessing function
            from pygments.lexers import guess_lexer
            from pygments.util import ClassNotFound
            
            # Let Pygments analyze the code and guess the language
            lexer = guess_lexer(content)
            
            # Get the primary alias or name from the lexer
            if lexer.aliases:
                detected_lang = lexer.aliases[0]  # Use first alias as it's usually the most common
            else:
                detected_lang = lexer.name.lower()
            
            logger.debug(f"🎯 Pygments detected language: {detected_lang} (lexer: {lexer.name})")
            return detected_lang
            
        except (ImportError, ClassNotFound, Exception) as e:
            logger.warning(f"⚠️ Pygments language detection failed: {e}")
            # Absolute minimal fallback - just check for JSON
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    import json
                    json.loads(content)
                    return 'json'
                except:
                    pass
            return 'text'  # Default fallback
    
    def _verify_language_with_patterns(self, content: str, suspected_lang: str) -> bool:
        """
        Verify if content matches expected patterns for a suspected language.
        """
        content_lower = content.lower()
        
        # Quick verification patterns for common languages
        verification_patterns = {
            'python': ['def ', 'import ', 'class ', 'print(', '__name__'],
            'javascript': ['function', 'var ', 'const ', 'let ', 'console.'],
            'java': ['public class', 'system.out', 'public static'],
            'cpp': ['#include', 'cout <<', 'std::'],
            'go': ['package ', 'func ', 'fmt.'],
            'rust': ['fn ', 'println!', 'struct '],
            'sql': ['select ', 'from ', 'where '],
            'yaml': [': ', '\\n- ', '\\n  '],
            'html': ['<html', '<div', '<body'],
        }
        
        if suspected_lang in verification_patterns:
            patterns = verification_patterns[suspected_lang]
            matches = sum(1 for pattern in patterns if pattern in content_lower)
            # If we find multiple matching patterns, it's likely the correct language
            return matches >= 2
            
        return False
            
    def _cleanup_remaining_artifacts(self, html_content: str) -> str:
        """
        Clean up any remaining HTML artifacts that might cause display issues.
        """
        # Remove orphaned closing div tags that might be left behind
        html_content = re.sub(r'\s*</div>\s*</div>\s*<br>\s*', ' ', html_content)
        html_content = re.sub(r'\s*</div>\s*</div>\s*', ' ', html_content)
        html_content = re.sub(r'\s*</div>\s*<br>\s*', ' ', html_content)
        
        # Clean up multiple consecutive whitespace/newlines
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = re.sub(r'<br>\s*<br>', '<br>', html_content)
        
        # Remove empty paragraphs or divs
        html_content = re.sub(r'<p>\s*</p>', '', html_content)
        html_content = re.sub(r'<div>\s*</div>', '', html_content)
        
        return html_content.strip()
        
    def _apply_label_styling(self, label: QLabel, message_style: str):
        """Apply theme-based styling to a label."""
        if not self.theme_colors:
            return
            
        # Get color based on message style
        style_colors = {
            'normal': self.theme_colors.get('text_primary', '#ffffff'),
            'input': self.theme_colors.get('text_secondary', '#a0a0a0'),
            'response': self.theme_colors.get('info', '#4A9EFF'),
            'system': self.theme_colors.get('text_secondary', '#808080'),
            'info': self.theme_colors.get('info', '#4A9EFF'),
            'warning': self.theme_colors.get('warning', '#FFB84D'),
            'error': self.theme_colors.get('error', '#FF4D4D'),
        }
        
        color = style_colors.get(message_style, self.theme_colors.get('text_primary', '#ffffff'))
        
        label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: transparent !important;
                background: none !important;
                padding: 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }}
            QLabel a {{
                color: {self.theme_colors.get('info', '#4A9EFF')};
                text-decoration: none;
                background: none !important;
            }}
            QLabel a:hover {{
                text-decoration: underline;
                background: none !important;
            }}
            QLabel p {{
                background: none !important;
                background-color: transparent !important;
            }}
            QLabel div {{
                background: none !important;
                background-color: transparent !important;
            }}
            QLabel span {{
                background: none !important;
                background-color: transparent !important;
            }}
        """)
        
    def add_code_snippet(self, code: str, language: str = ""):
        """
        Add an embedded code snippet widget with full formatting control and theme support.
        """
        # Store in history for re-rendering
        self.content_history.append(((code, language), None, 'code'))
        self._add_code_snippet_internal(code, language, store_history=False)
    
    def _add_code_snippet_internal(self, code: str, language: str = "", store_history: bool = True):
        """Internal method to add code snippet without storing history."""
        if not code.strip():
            logger.warning("Attempted to add empty code snippet")
            return
            
        # Use theme colors if available, with comprehensive defaults
        colors = self.theme_colors or {
            'bg_primary': '#1a1a1a',
            'bg_secondary': '#2a2a2a',
            'bg_tertiary': '#3a3a3a',  # This will be the solid background
            'text_primary': '#ffffff',
            'text_secondary': '#a0a0a0',
            'border': '#4a4a4a',
            'interactive': '#3a3a3a',
            'interactive_hover': '#4a4a4a',
            'background_primary': '#1a1a1a',
            'background_secondary': '#2a2a2a',
            'background_tertiary': '#3a3a3a',
        }
        
        try:
            # Create the embedded code widget with enhanced error handling
            code_widget = EmbeddedCodeSnippetWidget(code, language, colors)
            
            # Add to layout
            self.content_layout.addWidget(code_widget)
            self.content_widgets.append(code_widget)
            
            # Connect copy signal if needed
            code_widget.copy_requested.connect(self._handle_code_copy)
            
            # Auto-scroll to bottom
            QTimer.singleShot(10, self.scroll_to_bottom)
            
            logger.debug(f"Added code snippet: {len(code)} chars, language: {language}")
            
        except Exception as e:
            logger.error(f"Failed to add code snippet: {e}")
            # Fallback: add as plain text
            self.add_plain_text(f"```{language}\n{code}\n```", "normal")
        
    def add_plain_text(self, text: str, message_style: str = "normal"):
        """Add plain text content."""
        escaped_text = html.escape(text)
        # Convert newlines to <br> for proper display
        html_text = escaped_text.replace('\n', '<br>')
        self.add_html_content(html_text, message_style)
        
    def add_separator(self):
        """Add a horizontal separator."""
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)
        if self.theme_colors:
            separator.setStyleSheet(f"background-color: {self.theme_colors.get('border', '#3a3a3a')};")
        self.content_layout.addWidget(separator)
        self.content_widgets.append(separator)
        
    def clear(self):
        """Clear all content."""
        # Remove all widgets
        for widget in self.content_widgets:
            widget.deleteLater()
        self.content_widgets.clear()
        
        # Clear history
        self.content_history.clear()
        
        # Clear the layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def scroll_to_bottom(self):
        """Auto-scroll to the bottom."""
        v_scrollbar = self.verticalScrollBar()
        v_scrollbar.setValue(v_scrollbar.maximum())
        
    def _handle_link_click(self, url: str):
        """Handle link clicks."""
        self.link_clicked.emit(url)
        
    def _handle_code_copy(self, code: str):
        """Handle code copy feedback with enhanced logging."""
        try:
            logger.info(f"Code copied to clipboard: {len(code)} characters")
            logger.debug(f"Copied code preview: {code[:50]}{'...' if len(code) > 50 else ''}")
        except Exception as e:
            logger.warning(f"Error in copy feedback: {e}")
        
    def get_content_height(self) -> int:
        """Get the total height of all content."""
        return self.content_widget.sizeHint().height()
        
    def manage_content_size(self, max_widgets: int = 500):
        """
        Manage content size by removing old widgets if too many.
        Similar to document size management in QTextEdit.
        """
        if len(self.content_widgets) > max_widgets:
            # Remove oldest widgets
            widgets_to_remove = len(self.content_widgets) - max_widgets + 100  # Remove 100 extra
            
            for i in range(widgets_to_remove):
                if i < len(self.content_widgets):
                    widget = self.content_widgets[i]
                    self.content_layout.removeWidget(widget)
                    widget.deleteLater()
                    
            # Update the list
            self.content_widgets = self.content_widgets[widgets_to_remove:]
            
            # Add truncation notice
            notice = QLabel("[Previous messages truncated for performance]")
            if self.theme_colors:
                notice.setStyleSheet(f"""
                    color: {self.theme_colors.get('text_secondary', '#808080')};
                    font-style: italic;
                    padding: 4px;
                """)
            self.content_layout.insertWidget(0, notice)