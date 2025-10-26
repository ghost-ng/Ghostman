"""
REPL Widget for Ghostman.

Provides a Read-Eval-Print-Loop interface for interacting with the AI.
"""

import logging
import asyncio
import html
import os
import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("ghostman.repl_widget")
# Markdown rendering imports - migrated to mistune v3 for better performance
try:
    import mistune
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("Mistune library not available - falling back to plain text rendering")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QTextBrowser,
    QLineEdit, QPushButton, QLabel, QFrame, QComboBox, QPlainTextEdit,
    QToolButton, QMenu, QProgressBar, QListWidget, QSizePolicy,
    QListWidgetItem, QApplication, QMessageBox, QDialog, QCheckBox
)

# Import our custom mixed content display
from .mixed_content_display import MixedContentDisplay
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QSize, pyqtSlot, QPropertyAnimation, QEasingCurve, QUrl, QPoint
import weakref
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QTextCharFormat, QColor, QPalette, QIcon, QAction, QTextOption, QFontMetrics

# Import startup service for preamble
from ...application.startup_service import startup_service

# Tab system imports - conditional availability
try:
    from .tab_conversation_manager import TabConversationManager
    TAB_SYSTEM_AVAILABLE = True
except ImportError:
    TAB_SYSTEM_AVAILABLE = False
    logger.warning("Tab system not available - falling back to single conversation mode")

class ReplLinkHandler:
    """Robust link detection and handling system for REPL widgets."""
    
    def __init__(self, text_edit, parent_repl=None):
        self.text_edit = weakref.ref(text_edit)
        self.parent_repl = weakref.ref(parent_repl) if parent_repl else None
        
        # Link registry for reliable detection
        self.link_registry = {}  # block_num: [(start, end, href), ...]
        
        # Performance optimization
        self.last_position = QPoint(-1, -1)
        self.last_cursor_state = None
        self.position_cache = {}
        
        # Debounced updates for better performance
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_cursor_update)
        self._pending_position = None
        
        # Initialize
        self._rebuild_link_registry()
        
        # Connect to document changes
        if text_edit.document():
            text_edit.document().contentsChanged.connect(self._on_document_changed)
    
    def handle_mouse_move(self, event_pos):
        """Handle mouse move events for cursor changes."""
        if event_pos == self.last_position:
            return False
        
        self.last_position = event_pos
        
        # Check cache first
        cache_key = (event_pos.x(), event_pos.y())
        if cache_key in self.position_cache:
            is_link, href = self.position_cache[cache_key]
            self._update_cursor_state(is_link, href)
            return True
        
        # Queue update for performance
        self._pending_position = event_pos
        if not self._update_timer.isActive():
            self._update_timer.start(10)  # 10ms debounce
        
        return True
    
    def handle_mouse_click(self, event_pos):
        """Handle mouse click events for link activation."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        try:
            is_link, href = self._detect_link_at_position(event_pos)
            if is_link and href:
                self._handle_link_activation(href)
                return True
        except Exception as e:
            logger.error(f"Error handling mouse click: {e}")
        
        return False
    
    def _perform_cursor_update(self):
        """Perform the actual cursor update with caching."""
        if not self._pending_position:
            return
        
        position = self._pending_position
        self._pending_position = None
        
        # Detect link at position
        is_link, href = self._detect_link_at_position(position)
        
        # Cache result
        cache_key = (position.x(), position.y())
        self.position_cache[cache_key] = (is_link, href)
        
        # Limit cache size for memory management
        if len(self.position_cache) > 1000:
            keys_to_remove = list(self.position_cache.keys())[:500]
            for key in keys_to_remove:
                del self.position_cache[key]
        
        # Update cursor
        self._update_cursor_state(is_link, href)
    
    def _detect_link_at_position(self, position):
        """Detect if there's a link at the given position using multiple methods."""
        text_edit = self.text_edit()
        if not text_edit:
            return False, None
        
        # Method 1: Registry-based detection (most reliable)
        registry_result = self._detect_via_registry(position)
        if registry_result[0]:
            return registry_result
        
        # Method 2: Character format detection
        format_result = self._detect_via_char_format(position)
        if format_result[0]:
            return format_result
        
        # Method 3: anchorAt method (fallback)
        anchor_result = self._detect_via_anchor_at(position)
        if anchor_result[0]:
            return anchor_result
        
        return False, None
    
    def _detect_via_registry(self, position):
        """Detect links using the internal registry."""
        text_edit = self.text_edit()
        if not text_edit:
            return False, None
        
        try:
            cursor = text_edit.cursorForPosition(position)
            block = cursor.block()
            
            if not block.isValid():
                return False, None
            
            block_num = block.blockNumber()
            position_in_block = cursor.position() - block.position()
            
            # Check registry for this block
            if block_num in self.link_registry:
                for start_pos, end_pos, href in self.link_registry[block_num]:
                    if start_pos <= position_in_block < end_pos:
                        return True, href
        
        except Exception as e:
            logger.debug(f"Registry detection failed: {e}")
        
        return False, None
    
    def _detect_via_char_format(self, position):
        """Detect links using character format analysis."""
        text_edit = self.text_edit()
        if not text_edit:
            return False, None
        
        try:
            cursor = text_edit.cursorForPosition(position)
            char_format = cursor.charFormat()
            
            if char_format.isAnchor():
                href = char_format.anchorHref()
                if href:
                    return True, href
        
        except Exception as e:
            logger.debug(f"Character format detection failed: {e}")
        
        return False, None
    
    def _detect_via_anchor_at(self, position):
        """Detect links using the anchorAt method."""
        text_edit = self.text_edit()
        if not text_edit:
            return False, None
        
        try:
            anchor = text_edit.anchorAt(position)
            if anchor and anchor.strip():
                return True, anchor
        
        except Exception as e:
            logger.debug(f"AnchorAt detection failed: {e}")
        
        return False, None
    
    def _update_cursor_state(self, is_link, href):
        """Update the cursor state."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        new_state = "link" if is_link else "text"
        
        # Only update if state changed
        if self.last_cursor_state != new_state:
            if is_link:
                text_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                text_edit.setCursor(Qt.CursorShape.IBeamCursor)
            
            self.last_cursor_state = new_state
    
    def _handle_link_activation(self, href):
        """Handle link activation (clicks)."""
        try:
            # Handle internal resend message links
            if href.startswith('resend_message'):
                parent_repl = self.parent_repl() if self.parent_repl else None
                if parent_repl and hasattr(parent_repl, '_handle_resend_click'):
                    parent_repl._handle_resend_click(QUrl(href))
            
            # Handle external URLs
            elif href.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
                import webbrowser
                webbrowser.open(href)
            
        except Exception as e:
            logger.error(f"Error handling link activation '{href}': {e}")
    
    def _rebuild_link_registry(self):
        """Rebuild the link registry by scanning the document."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        self.link_registry.clear()
        self.position_cache.clear()
        
        document = text_edit.document()
        
        try:
            for block_num in range(document.blockCount()):
                block = document.findBlockByNumber(block_num)
                if not block.isValid():
                    continue
                
                self._scan_block_for_links(block_num, block)
        
        except Exception as e:
            logger.error(f"Error rebuilding link registry: {e}")
    
    def _scan_block_for_links(self, block_num, block):
        """Scan a single block for links and add them to the registry."""
        block_it = block.begin()
        block_position = block.position()
        
        while not block_it.atEnd():
            fragment = block_it.fragment()
            if fragment.isValid():
                char_format = fragment.charFormat()
                
                if char_format.isAnchor():
                    href = char_format.anchorHref()
                    if href:
                        start_pos = fragment.position() - block_position
                        end_pos = start_pos + fragment.length()
                        
                        if block_num not in self.link_registry:
                            self.link_registry[block_num] = []
                        
                        self.link_registry[block_num].append((start_pos, end_pos, href))
            
            block_it += 1
    
    def _on_document_changed(self):
        """Handle document content changes."""
        self._rebuild_link_registry()
# Import font service for font configuration
from ...application.font_service import font_service

# Theme system imports
try:
    from ...ui.themes.theme_manager import get_theme_manager
    from ...ui.themes.style_templates import StyleTemplates, ButtonStyleManager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    logger.warning("Theme system not available - using legacy styling")

# Settings import (percent-based opacity)
try:
    from ...infrastructure.storage.settings_manager import settings as _global_settings
except Exception:  # pragma: no cover
    _global_settings = None

# Conversation management imports
try:
    from ...infrastructure.conversation_management.integration.conversation_manager import ConversationManager
    from ...infrastructure.conversation_management.models.conversation import Conversation, Message
    from ...infrastructure.conversation_management.models.enums import ConversationStatus, MessageRole
except Exception:  # pragma: no cover
    ConversationManager = None
    Conversation = None
    Message = None
    ConversationStatus = None
    MessageRole = None

logger = logging.getLogger("ghostman.repl_widget")


class MarkdownRenderer:
    """
    Advanced markdown renderer for REPL output with color-coded message types.
    
    Features:
    - Full markdown support (headers, emphasis, code blocks, lists, links, tables)
    - Preserves existing color scheme for different message types
    - Optimized for conversational AI interfaces
    - Graceful fallback to plain text when markdown unavailable
    - Performance-optimized for long conversations
    """
    
    def __init__(self, theme_manager=None):
        """Initialize the markdown renderer with optimized configuration."""
        self.markdown_available = MARKDOWN_AVAILABLE
        self.theme_manager = theme_manager
        
        if self.markdown_available:
            # Configure mistune v3 renderer with AI-friendly plugins and Pygments syntax highlighting
            # mistune v3 provides better performance and more robust parsing
            self.md_processor = mistune.create_markdown(
                renderer=self._create_enhanced_renderer(),
                plugins=[
                    'table',        # Table support (replaces 'tables')
                    'strikethrough', # ~~strikethrough~~ support
                    'mark',         # ==highlight== support
                    'insert',       # ++insert++ support
                    'task_lists',   # [x] and [ ] checkbox support
                ],
                # mistune v3 has built-in support for:
                # - Fenced code blocks (```code```)
                # - Newline to <br> conversion (via hard_wrap=True)
                # - Basic markdown features (bold, italic, links, etc.)
                hard_wrap=True,  # Convert single newlines to <br> (replaces nl2br)
                escape=False,    # Allow HTML tags for Qt rendering
            )
        
        # Update color scheme based on theme or use defaults
        self._update_color_scheme()
        
        # Performance cache for repeated renders (small cache to avoid memory issues)
        self._render_cache = {}
        self._cache_max_size = 100
    
    def _create_enhanced_renderer(self):
        """Create a custom mistune renderer with Pygments syntax highlighting."""
        try:
            # Try to import Pygments for syntax highlighting
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import html
            from pygments.util import ClassNotFound
            
            class PygmentsRenderer(mistune.HTMLRenderer):
                """Custom mistune renderer with Pygments syntax highlighting."""
                
                def __init__(self, theme_manager=None):
                    super().__init__()
                    self.theme_manager = theme_manager
                    self._get_pygments_style()
                
                def _get_pygments_style(self):
                    """Get Pygments style based on current theme with improved detection."""
                    if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                        try:
                            theme = self.theme_manager.current_theme
                            # Use the same theme detection logic as StyleTemplates
                            if hasattr(theme, 'background_primary'):
                                bg = theme.background_primary
                                if bg.startswith('#'):
                                    # Enhanced luminance calculation for better theme detection
                                    r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
                                    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                                    # Use vs (light) and vs2015 (dark) for better code highlighting
                                    self.pygments_style = 'vs' if luminance > 0.5 else 'vs2015'
                                    self.is_dark_theme = luminance <= 0.5
                                else:
                                    self.pygments_style = 'vs2015'
                                    self.is_dark_theme = True
                            else:
                                self.pygments_style = 'vs2015'
                                self.is_dark_theme = True
                        except Exception:
                            self.pygments_style = 'vs2015'
                            self.is_dark_theme = True
                    else:
                        self.pygments_style = 'vs2015'
                        self.is_dark_theme = True
                
                def block_code(self, code, info=None):
                    """Render code blocks with enhanced widget-style appearance and syntax highlighting."""
                    language = info.strip() if info else ""
                    language_display = language.upper() if language else ""
                    
                    # Get theme colors for styling
                    colors = self._get_theme_colors()
                    
                    # Generate the header HTML
                    header_html = self._generate_code_header(language_display, colors)
                    
                    # Generate syntax-highlighted code content
                    code_content_html = self._generate_highlighted_code(code, language, colors)
                    
                    # Combine into widget-style structure with modern styling
                    container_bg = colors['bg_tertiary'] if hasattr(self, 'is_dark_theme') and self.is_dark_theme else colors['bg_primary']
                    border_color = colors['border']
                    
                    return f"""
                    <div style="
                        background-color: {container_bg};
                        border: 1px solid {border_color};
                        border-radius: 8px;
                        margin: 6px 0;
                        overflow: hidden;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    ">
                        {header_html}
                        {code_content_html}
                    </div>
                    """
                
                def _get_theme_colors(self):
                    """Get theme-appropriate colors for the code widget."""
                    # Try to get colors from theme manager
                    if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
                        theme = self.theme_manager.current_theme
                        
                        # Get theme-specific colors first - PRESERVE UNIQUE THEME COLORS
                        text_primary = getattr(theme, 'text_primary', None)
                        text_secondary = getattr(theme, 'text_secondary', None)
                        
                        # Only use fallbacks if theme colors are actually missing
                        if text_primary is None:
                            # Use theme detection to provide appropriate text fallbacks
                            if hasattr(self, 'is_dark_theme') and not self.is_dark_theme:
                                text_primary = '#2d2d2d'  # Light theme fallback
                            else:
                                text_primary = '#ffffff'  # Dark theme fallback
                        
                        if text_secondary is None:
                            # Use theme detection to provide appropriate secondary fallbacks
                            if hasattr(self, 'is_dark_theme') and not self.is_dark_theme:
                                text_secondary = '#666666'  # Light theme fallback
                            else:
                                text_secondary = '#cccccc'  # Dark theme fallback
                        
                        return {
                            'bg_primary': getattr(theme, 'background_primary', '#1a1a1a'),
                            'bg_secondary': getattr(theme, 'background_secondary', '#2a2a2a'),
                            'bg_tertiary': getattr(theme, 'background_tertiary', '#3a3a3a'),
                            'text_primary': text_primary,  # PRESERVE unique theme colors
                            'text_secondary': text_secondary,  # PRESERVE unique theme colors
                            'border': getattr(theme, 'border_primary', '#4a4a4a'),
                            'interactive': getattr(theme, 'interactive_normal', '#4a4a4a'),
                            'interactive_hover': getattr(theme, 'interactive_hover', '#5a5a5a'),
                        }
                    
                    # Fallback dark theme colors
                    return {
                        'bg_primary': '#1a1a1a',
                        'bg_secondary': '#2a2a2a', 
                        'bg_tertiary': '#3a3a3a',
                        'text_primary': '#ffffff',
                        'text_secondary': '#cccccc',
                        'border': '#4a4a4a',
                        'interactive': '#4a4a4a',
                        'interactive_hover': '#5a5a5a',
                    }
                
                def _generate_code_header(self, language_display, colors):
                    """Generate the header HTML for the code widget."""
                    # Language tag (only if language is specified)
                    language_tag = ""
                    if language_display:
                        # Enhanced language tag with primary color accent and opacity
                        primary_color = getattr(self.theme_manager.current_theme, 'primary', '#4CAF50') if self.theme_manager and hasattr(self.theme_manager, 'current_theme') else '#4CAF50'
                        tag_bg = f"{primary_color}20"  # 20% opacity
                        
                        language_tag = f"""
                        <span style="
                            background-color: {tag_bg};
                            color: {primary_color};
                            padding: 3px 8px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 500;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        ">{language_display}</span>
                        """
                    
                    # Modern header styling to match CodeSnippetWidget
                    header_bg = colors['bg_secondary']
                    title = f"{language_display} Snippet" if language_display else "Code Snippet"
                    
                    return f"""
                    <div style="
                        background-color: {header_bg};
                        padding: 12px 16px;
                        border-bottom: 1px solid {colors['border']};
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        border-radius: 7px 7px 0 0;
                    ">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="
                                color: {colors['text_primary']};
                                font-weight: 600;
                                font-size: 13px;
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            ">{title}</span>
                            {language_tag}
                        </div>
                        <span style="
                            color: {colors['text_primary']};
                            font-size: 12px;
                            padding: 6px 12px;
                            background-color: {colors['interactive']};
                            border: 1px solid {colors['border']};
                            border-radius: 4px;
                            cursor: pointer;
                            font-weight: 500;
                            transition: all 0.2s ease;
                        " title="Click to copy" 
                           onmouseover="this.style.backgroundColor='{colors['interactive_hover']}'" 
                           onmouseout="this.style.backgroundColor='{colors['interactive']}'">
                            Copy
                        </span>
                    </div>
                    """
                
                def _generate_highlighted_code(self, code, language, colors):
                    """Generate syntax-highlighted code content."""
                    # Get code font from font service
                    try:
                        from ...application.font_service import font_service
                        code_font_css = font_service.get_css_font_style('code_snippets')
                    except Exception:
                        # Fallback to default monospace fonts
                        code_font_css = "font-family: 'Consolas', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace; font-size: 14px"
                    
                    if language:
                        try:
                            # Get lexer for the specified language
                            lexer = get_lexer_by_name(language, stripall=True)
                            logger.debug(f"🎨 First highlighting system: Got lexer '{lexer.name}' for language '{language}'")
                            
                            # Create formatter with theme-appropriate styling
                            formatter = html.HtmlFormatter(
                                style=self.pygments_style,
                                noclasses=True,
                                nobackground=True,
                                nowrap=True,  # Don't include <pre><code> wrapper
                            )
                            
                            # Generate highlighted HTML
                            highlighted_code = highlight(code, lexer, formatter)
                            logger.debug(f"🎨 First highlighting system: Generated {len(highlighted_code)} chars of highlighted HTML")
                            
                            return f"""
                            <div style="
                                background-color: {colors['bg_tertiary']};
                                padding: 16px;
                                overflow-x: auto;
                                {code_font_css};
                                line-height: 1.5;
                                color: {colors['text_primary']};
                                border-radius: 0 0 7px 7px;
                                min-height: 60px;
                            ">
                                <pre style="
                                    margin: 0; 
                                    white-space: pre-wrap; 
                                    font-family: inherit;
                                    background-color: {colors['bg_tertiary']} !important;
                                    width: 100%;
                                    display: block;
                                    padding: 0;
                                ">{highlighted_code}</pre>
                            </div>
                            """
                            
                        except ClassNotFound:
                            logger.debug(f"🚫 First highlighting system: Language '{language}' not supported by Pygments")
                        except Exception as e:
                            logger.debug(f"🚫 First highlighting system: Pygments highlighting failed for '{language}': {e}")
                    
                    # Fallback to plain code with HTML escaping and modern styling
                    escaped_code = mistune.escape(code)
                    return f"""
                    <div style="
                        background-color: {colors['bg_tertiary']};
                        padding: 16px;
                        overflow-x: auto;
                        font-family: 'Consolas', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
                        font-size: 14px;
                        line-height: 1.5;
                        color: {colors['text_primary']};
                        border-radius: 0 0 7px 7px;
                        min-height: 60px;
                    ">
                        <pre style="
                            margin: 0; 
                            white-space: pre-wrap; 
                            font-family: inherit;
                            background-color: {colors['bg_tertiary']} !important;
                            width: 100%;
                            display: block;
                            padding: 0;
                        ">{escaped_code}</pre>
                    </div>
                    """
            
            # Return the custom renderer instance
            return PygmentsRenderer(self.theme_manager)
            
        except ImportError:
            # Pygments not available, fall back to standard HTML renderer
            logger.warning("Pygments not available - using standard code block rendering")
            return 'html'
        except Exception as e:
            # Any other error, fall back to standard renderer
            logger.warning(f"Failed to create enhanced renderer: {e} - using standard HTML renderer")
            return 'html'
    
    def _update_color_scheme(self):
        """Update color scheme based on current theme or use defaults."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            try:
                colors = self.theme_manager.current_theme
                # Use theme colors for message types with enhanced contrast for markdown
                self.color_scheme = {
                    "normal": colors.text_primary,
                    "input": colors.primary,  # User input in primary color
                    "response": colors.text_primary,  # AI response in text color  
                    "system": colors.text_tertiary,  # System messages in muted text
                    "info": colors.status_info,
                    "warning": colors.status_warning,
                    "error": colors.status_error,
                    "divider": colors.separator
                }
                
                # Ensure all colors have sufficient contrast for readability
                self._validate_and_enhance_contrast()
                
            except Exception as e:
                logger.warning(f"Failed to get theme colors: {e}, using defaults")
                self._set_default_colors()
        else:
            self._set_default_colors()
    
    def _set_default_colors(self):
        """Set default color scheme when theme system is not available."""
        self.color_scheme = {
            "normal": "#f0f0f0",
            "input": "#4CAF50", 
            "response": "#2196F3",
            "system": "#9E9E9E",
            "info": "#FF9800",
            "warning": "#FF5722",
            "error": "#F44336",
            "divider": "#616161"
        }
    
    def _validate_and_enhance_contrast(self):
        """Validate and enhance color contrast for better markdown readability."""
        try:
            # Get background color for contrast calculation
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                colors = self.theme_manager.current_theme
                bg_color = colors.background_primary
                
                # Check and enhance contrast for each color type
                for style_type, color in self.color_scheme.items():
                    enhanced_color = self._ensure_minimum_contrast(color, bg_color)
                    if enhanced_color != color:
                        self.color_scheme[style_type] = enhanced_color
                        logger.debug(f"Enhanced contrast for {style_type}: {color} -> {enhanced_color}")
                        
        except Exception as e:
            logger.warning(f"Failed to validate color contrast: {e}")
    
    def _get_smart_text_fallback(self, bg_color: str) -> str:
        """
        Get smart text color fallback based on background brightness.
        Returns dark text for light backgrounds and light text for dark backgrounds.
        """
        try:
            # Remove # if present
            hex_color = bg_color.lstrip('#')
            
            # Convert hex to RGB
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16) 
                b = int(hex_color[4:6], 16)
            elif len(hex_color) == 3:
                r = int(hex_color[0], 16) * 17
                g = int(hex_color[1], 16) * 17
                b = int(hex_color[2], 16) * 17
            else:
                # Invalid color, use dark fallback
                return '#2d2d2d'
            
            # Calculate luminance (0.299*R + 0.587*G + 0.114*B)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            # Return dark text for light backgrounds, light text for dark backgrounds
            if luminance > 0.5:
                return '#2d2d2d'  # Dark text for light background
            else:
                return '#f0f0f0'  # Light text for dark background
                
        except (ValueError, TypeError):
            # Fallback if color parsing fails
            return '#2d2d2d'
    
    def _ensure_minimum_contrast(self, text_color: str, background_color: str, min_ratio: float = 4.5) -> str:
        """Ensure minimum contrast ratio between text and background colors."""
        try:
            # Simple color adjustment for better contrast
            # This is a basic implementation - could be enhanced with proper contrast calculation
            
            # Convert hex to RGB for basic analysis
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            def rgb_to_hex(rgb):
                return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
            
            # Get RGB values
            text_rgb = hex_to_rgb(text_color)
            bg_rgb = hex_to_rgb(background_color)
            
            # Calculate relative luminance (simplified)
            def get_luminance(rgb):
                r, g, b = [x / 255.0 for x in rgb]
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            text_lum = get_luminance(text_rgb)
            bg_lum = get_luminance(bg_rgb)
            
            # Calculate contrast ratio
            contrast = (max(text_lum, bg_lum) + 0.05) / (min(text_lum, bg_lum) + 0.05)
            
            # If contrast is sufficient, return original color
            if contrast >= min_ratio:
                return text_color
            
            # Enhance contrast by adjusting brightness
            # Make text lighter or darker depending on background
            if bg_lum > 0.5:  # Light background
                # Make text darker
                factor = 0.7
                enhanced_rgb = tuple(int(c * factor) for c in text_rgb)
            else:  # Dark background
                # Make text lighter
                factor = 1.3
                enhanced_rgb = tuple(min(255, int(c * factor)) for c in text_rgb)
            
            return rgb_to_hex(enhanced_rgb)
            
        except Exception as e:
            logger.warning(f"Failed to calculate contrast for {text_color}: {e}")
            return text_color
    
    def render(self, text: str, style: str = "normal", force_plain: bool = False) -> str:
        """
        Render text with markdown formatting and message type styling.
        
        Args:
            text: Input text (markdown or plain text)
            style: Message type for color coding (normal, input, response, etc.)
            force_plain: If True, bypass markdown processing
            
        Returns:
            HTML string ready for QTextEdit insertion
        """
        # Handle empty or None text
        if not text or not text.strip():
            # For spacing purposes, return an empty line without any text
            return '<br>'
        
        # Cache key for performance optimization
        cache_key = f"{hash(text)}{style}{force_plain}"
        if cache_key in self._render_cache:
            return self._render_cache[cache_key]
        
        base_color = self.color_scheme.get(style, self.color_scheme.get("normal", "#f0f0f0"))
        
        # Determine if we should process as markdown
        should_process_markdown = (
            not force_plain and 
            self.markdown_available and 
            self._detect_markdown_content(text)
        )
        
        if should_process_markdown:
            html_content = self._render_markdown_to_html(text, base_color, style)
        else:
            # Plain text rendering with basic HTML escaping
            html_content = self._render_plain_text(text, base_color)
        
        # Cache the result (with size management)
        self._manage_cache(cache_key, html_content)
        
        return html_content
    
    def _detect_markdown_content(self, text: str) -> bool:
        """
        Detect if text contains markdown formatting to optimize processing.
        
        Args:
            text: Input text to analyze
            
        Returns:
            True if markdown formatting detected, False otherwise
        """
        # Quick regex patterns for common markdown elements
        markdown_patterns = [
            r'\*\*[^\*]+\*\*',       # **bold**
            r'\*[^\*]+\*',           # *italic*
            r'__[^_]+__',            # __bold__
            r'_[^_]+_',              # _italic_
            r'`[^`]+`',              # `code`
            r'^```',                 # ```code block
            r'^#{1,6}\s',           # # Headers
            r'^\s*[-\*\+]\s',       # - * + lists
            r'^\s*\d+\.\s',         # 1. numbered lists
            r'\[([^\]]+)\]\(([^\)]+)\)',  # [link](url)
            r'^\s*\|.*\|\s*$',      # | table | cells |
            r'>\s+',                 # > blockquotes
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
    
    def _render_markdown_to_html(self, text: str, base_color: str, style: str) -> str:
        """
        Convert markdown to HTML with integrated color styling.
        
        Args:
            text: Markdown text to convert
            base_color: Base color for the message type
            style: Message style type
            
        Returns:
            Styled HTML content
        """
        try:
            # Process markdown to HTML using mistune v3
            # mistune v3 uses direct function call instead of .convert()
            html_content = self.md_processor(text)
            
            # Convert HTML input checkboxes to Unicode symbols for QTextEdit compatibility
            html_content = self._convert_checkboxes_to_unicode(html_content)
            
            # Apply message-type styling to the HTML
            styled_html = self._apply_color_styling(html_content, base_color, style)
            
            # Clean up and optimize for Qt rendering
            styled_html = self._optimize_qt_html(styled_html)
            
            # Note: mistune v3 doesn't require reset() - it's stateless
            
            return styled_html + '<br>'
            
        except Exception as e:
            logger.warning(f"Markdown rendering failed: {e}, falling back to plain text")
            return self._render_plain_text(text, base_color)
    
    def _apply_color_styling(self, html_content: str, base_color: str, style: str) -> str:
        """
        Apply consistent color styling to HTML content based on message type.
        
        Args:
            html_content: HTML content from markdown conversion
            base_color: Base color for the message type
            style: Message style type for special handling
            
        Returns:
            HTML with integrated color styling
        """
        # Define style-specific color variations
        style_colors = {
            'code': self._adjust_color_brightness(base_color, 0.8),
            'em': self._adjust_color_brightness(base_color, 1.1),
            'strong': self._adjust_color_brightness(base_color, 1.2),
            'h1': self._adjust_color_brightness(base_color, 1.3),
            'h2': self._adjust_color_brightness(base_color, 1.25),
            'h3': self._adjust_color_brightness(base_color, 1.2),
            'blockquote': self._adjust_color_brightness(base_color, 0.7),
            'a': self.color_scheme.get('info', '#4A9EFF')  # Link color from theme
        }
        
        # Get appropriate font based on message style
        font_type = 'user_input' if style == 'input' else 'ai_response'
        font_css = font_service.get_css_font_style(font_type)
        
        # Get code font from font service
        code_font_css = font_service.get_css_font_style('code_snippets')
        
        # Wrap entire content with base color and font configuration - explicitly remove backgrounds
        styled_html = f'<div style="color: {base_color}; line-height: {{\'1.4\'}}; {font_css}; background: none !important;">{html_content}</div>'
        
        # Apply specific styling to elements - remove backgrounds to prevent line coloring
        replacements = {
            '<code>': f'<code style="padding: {{\'2px\'}} {{\'4px\'}}; border-radius: {{\'3px\'}}; color: {style_colors["code"]}; {code_font_css}; background: none !important;">',
            # Skip pre tag replacement to avoid overriding code snippet solid backgrounds
            '<em>': f'<em style="color: {style_colors["em"]}; font-style: italic; background: none !important;">',
            '<strong>': f'<strong style="color: {style_colors["strong"]}; font-weight: bold; background: none !important;">',
            '<h1>': f'<h1 style="color: {style_colors["h1"]}; font-size: {{\'1.4em\'}}; margin: {{\'8px\'}} {{\'0\'}} {{\'4px\'}} {{\'0\'}}; border-bottom: {{\'2px\'}} solid {base_color}; background: none !important;">',
            '<h2>': f'<h2 style="color: {style_colors["h2"]}; font-size: {{\'1.3em\'}}; margin: {{\'6px\'}} {{\'0\'}} {{\'3px\'}} {{\'0\'}}; border-bottom: {{\'1px\'}} solid {base_color}; background: none !important;">',
            '<h3>': f'<h3 style="color: {style_colors["h3"]}; font-size: {{\'1.2em\'}}; margin: {{\'4px\'}} {{\'0\'}} {{\'2px\'}} {{\'0\'}}; background: none !important;">',
            '<blockquote>': f'<blockquote style="color: {style_colors["blockquote"]}; border-left: {{\'3px\'}} solid {base_color}; padding-left: {{\'12px\'}}; margin: {{\'4px\'}} {{\'0\'}}; font-style: italic; background: none !important;">',
            '<ul>': '<ul style="margin: 4px 0; padding-left: 20px; background: none !important;">',
            '<ol>': '<ol style="margin: 4px 0; padding-left: 20px; background: none !important;">',
            '<li>': f'<li style="margin: {{\'2px\'}} {{\'0\'}}; background: none !important;">',
            '<table>': f'<table style="border-collapse: collapse; margin: 8px 0; border: 1px solid {base_color}; background: none !important;">',
            '<th>': f'<th style="padding: 4px 8px; border: 1px solid {base_color}; font-weight: bold; background: none !important;">',
            '<td>': f'<td style="padding: 4px 8px; border: 1px solid {base_color}; background: none !important;">',
            '<p>': '<p style="background: none !important;">',
            '<div>': '<div style="background: none !important;">',
        }
        
        for old, new in replacements.items():
            styled_html = styled_html.replace(old, new)
        
        # Handle links with special care - ensure proper anchor formatting for Qt
        styled_html = re.sub(
            r'<a href="([^"]+)"([^>]*)>',
            f'<a href="\\1" style="color: {style_colors["a"]}; text-decoration: underline;"\\2>',
            styled_html
        )
        
        return styled_html
    
    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """
        Adjust the brightness of a hex color by a given factor.
        
        Args:
            hex_color: Hex color string (e.g., "#ff0000")
            factor: Brightness factor (1.0 = no change, >1.0 = brighter, <1.0 = darker)
            
        Returns:
            Adjusted hex color string
        """
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Apply brightness factor
            adjusted_rgb = tuple(min(255, int(c * factor)) for c in rgb)
            
            # Convert back to hex
            return f"#{adjusted_rgb[0]:02x}{adjusted_rgb[1]:02x}{adjusted_rgb[2]:02x}"
        except (ValueError, IndexError):
            # Return original color if adjustment fails
            return hex_color
    
    def _convert_checkboxes_to_unicode(self, html_content: str) -> str:
        """
        Convert HTML input checkboxes to Unicode symbols for QTextEdit compatibility.
        
        QTextEdit cannot render HTML <input> elements, but mistune's task_lists plugin
        generates them. This method converts them to Unicode checkbox symbols that
        display properly in QTextEdit.
        
        Args:
            html_content: HTML content with potential checkbox inputs
            
        Returns:
            HTML content with checkboxes converted to Unicode symbols
        """
        # Flexible pattern to match checkbox inputs with any attribute order
        checkbox_pattern = r'<input[^>]*?(?=.*class="task-list-item-checkbox")(?=.*type="checkbox")[^>]*?/?>'
        
        def replace_checkbox(match):
            checkbox_html = match.group(0)
            # Check if checkbox is checked
            if 'checked' in checkbox_html:
                return '☑ '  # Checked box with space
            else:
                return '☐ '  # Unchecked box with space
        
        # Replace checkbox inputs with Unicode symbols
        result = re.sub(checkbox_pattern, replace_checkbox, html_content)
        
        # Clean up the task-list-item class since it's no longer needed for styling
        result = re.sub(r'<li class="task-list-item">', '<li>', result)
        
        return result
    
    def _optimize_qt_html(self, html_content: str) -> str:
        """
        Optimize HTML for Qt's text rendering engine.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Optimized HTML for Qt rendering
        """
        # Remove problematic HTML elements/attributes that Qt doesn't handle well
        optimizations = [
            # Remove unsupported CSS properties
            (r'\s*white-space:\s*pre-wrap;', ''),
            (r'\s*word-wrap:\s*break-word;', ''),
            # Simplify complex selectors
            (r'<p>\s*</p>', ''),  # Remove empty paragraphs
            # Ensure proper line spacing
            (r'</p>\s*<p>', '</p><br><p>'),
        ]
        
        optimized_html = html_content
        for pattern, replacement in optimizations:
            optimized_html = re.sub(pattern, replacement, optimized_html, flags=re.IGNORECASE)
        
        return optimized_html
    
    def _render_plain_text(self, text: str, base_color: str) -> str:
        """
        Render plain text with HTML escaping and color styling.
        
        Args:
            text: Plain text to render
            base_color: Color for the text
            
        Returns:
            HTML-formatted plain text
        """
        # HTML escape the text to prevent injection
        escaped_text = html.escape(text)
        
        # Convert newlines to <br> tags
        escaped_text = escaped_text.replace('\n', '<br>')
        
        # Preserve spaces and tabs
        escaped_text = escaped_text.replace('  ', '&nbsp;&nbsp;')
        escaped_text = escaped_text.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        
        return f'<span style="color: {base_color};">{escaped_text}</span><br>'
    
    def _manage_cache(self, key: str, content: str):
        """
        Manage render cache size to prevent memory bloat.
        
        Args:
            key: Cache key
            content: Content to cache
        """
        # Remove oldest entries if cache is full
        if len(self._render_cache) >= self._cache_max_size:
            # Remove roughly 20% of entries (oldest first)
            keys_to_remove = list(self._render_cache.keys())[:self._cache_max_size // 5]
            for old_key in keys_to_remove:
                del self._render_cache[old_key]
        
        self._render_cache[key] = content
    
    def clear_cache(self):
        """Clear the render cache to free memory."""
        self._render_cache.clear()
    
    def update_theme(self):
        """Update color scheme when theme changes."""
        self._update_color_scheme()
        self.clear_cache()  # Clear cache to force re-render with new colors
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for debugging/monitoring."""
        return {
            'cache_size': len(self._render_cache),
            'cache_max_size': self._cache_max_size,
            'markdown_available': self.markdown_available
        }


class ConversationCard(QWidget):
    """
    Visual card widget for displaying conversation metadata in dropdown.
    """
    def __init__(self, conversation: 'Conversation', parent=None):
        super().__init__(parent)
        self.conversation = conversation
        self._init_ui()
    
    def _init_ui(self):
        """Initialize conversation card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Title and status row
        title_row = QHBoxLayout()
        
        # Status indicator
        status_label = QLabel(self._get_status_icon())
        status_label.setToolTip(f"Status: {self.conversation.status.value.title()}")
        title_row.addWidget(status_label)
        
        # Title
        title_label = QLabel(self.conversation.title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)
        
        # Summary indicator
        if self.conversation.summary:
            summary_label = QLabel("💡")
            summary_label.setToolTip("Has AI summary")
            title_row.addWidget(summary_label)
        
        layout.addLayout(title_row)
        
        # Metadata row
        meta_row = QHBoxLayout()
        
        # Message count
        msg_count = QLabel(f"📝 {len(self.conversation.messages)} msgs")
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            text_color = self.theme_manager.current_theme.text_tertiary
        else:
            text_color = "#888"
        msg_count.setStyleSheet(f"color: {text_color}; font-size: 9px;")
        meta_row.addWidget(msg_count)
        
        # Last updated
        time_diff = datetime.now() - self.conversation.updated_at
        if time_diff.days > 0:
            time_text = f"{time_diff.days}d ago"
        elif time_diff.seconds > 3600:
            time_text = f"{time_diff.seconds // 3600}h ago"
        else:
            time_text = f"{time_diff.seconds // 60}m ago"
        
        time_label = QLabel(f"🕒 {time_text}")
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            text_color = self.theme_manager.current_theme.text_tertiary
        else:
            text_color = "#888"
        time_label.setStyleSheet(f"color: {text_color}; font-size: 9px;")
        meta_row.addWidget(time_label)
        
        meta_row.addStretch()
        layout.addLayout(meta_row)
        
        # Tags if any
        if self.conversation.metadata.tags:
            tags_text = " ".join([f"#{tag}" for tag in list(self.conversation.metadata.tags)[:3]])
            if len(self.conversation.metadata.tags) > 3:
                tags_text += "💬"
            tags_label = QLabel(tags_text)
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                text_color = self.theme_manager.current_theme.text_tertiary
            else:
                text_color = "#666"
            tags_label.setStyleSheet(f"color: {text_color}; font-size: 8px; font-style: italic;")
            layout.addWidget(tags_label)
    
    def _get_status_icon(self) -> str:
        """Get status icon based on conversation status."""
        status_icons = {
            ConversationStatus.ACTIVE: "🔥",
            ConversationStatus.PINNED: "⭐", 
            ConversationStatus.ARCHIVED: "📦",
            ConversationStatus.DELETED: "🗑️"
        }
        return status_icons.get(self.conversation.status, "💬")


class IdleDetector(QObject):
    """
    Detects user inactivity for background summarization.
    """
    idle_detected = pyqtSignal(str)  # conversation_id
    
    def __init__(self, idle_threshold_minutes: int = 5):
        super().__init__()
        self.idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self.last_activity = datetime.now()
        self.current_conversation_id: Optional[str] = None
        
        # Timer to check for idle state
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_idle_state)
        self.check_timer.start(60000)  # Check every minute
    
    def reset_activity(self, conversation_id: Optional[str] = None):
        """Reset activity timer."""
        self.last_activity = datetime.now()
        if conversation_id:
            self.current_conversation_id = conversation_id
    
    def _check_idle_state(self):
        """Check if user has been idle."""
        if not self.current_conversation_id:
            return
            
        time_since_activity = datetime.now() - self.last_activity
        if time_since_activity >= self.idle_threshold:
            self.idle_detected.emit(self.current_conversation_id)
            self.current_conversation_id = None  # Prevent repeated signals


class REPLWidget(QWidget):
    """
    Enhanced REPL interface with visual conversation management.
    
    Features:
    - Visual conversation management toolbar
    - Conversation selector dropdown with rich cards
    - Status indicators and action buttons
    - Message type icons
    - Background AI summarization
    - Command input with history
    - Scrollable output display
    """
    
    # Signals
    command_entered = pyqtSignal(str)
    minimize_requested = pyqtSignal()
    conversation_changed = pyqtSignal(str)  # conversation_id
    export_requested = pyqtSignal(str)  # conversation_id
    browse_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    help_requested = pyqtSignal()
    attach_toggle_requested = pyqtSignal(bool)
    pin_toggle_requested = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_history = []
        self.history_index = -1
        self.current_input = ""
        
        # Thread management for file processing
        self._processing_threads = []  # Track active processing threads
        
        # Panel (frame) opacity (only background, not text/content). 0.0 - 1.0
        # Initialize with default 90% opacity
        self._panel_opacity = 0.90
        
        # Conversation management
        self.conversation_manager: Optional[ConversationManager] = None
        self.current_conversation: Optional[Conversation] = None
        self.conversations_list: List[Conversation] = []
        
        # Error handling and resend functionality
        self.last_failed_message = None
        
        # AI processing thread management
        self.current_ai_thread = None
        self.current_ai_worker = None
        
        # Idle detection for background summarization
        self.idle_detector = IdleDetector(idle_threshold_minutes=5)
        self.idle_detector.idle_detected.connect(self._on_idle_detected)
        
        # Background summarization state
        self.summarization_queue: List[str] = []  # conversation IDs
        self.is_summarizing = False
        
        # Unified RAG session
        self.rag_session = None
        self._rag_session_initializing = False
        self._rag_session_ready = False
        self._pending_files_queue = []  # Queue for files waiting for RAG initialization
        self._init_rag_session()
        
        # Startup task control
        self._startup_tasks_completed = False
        
        # Autosave functionality
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._autosave_current_conversation)
        self.autosave_interval = 60000  # 1 minute in milliseconds
        self.last_autosave_time = None
        self.autosave_enabled = True
        
        # Load from settings if available
        self._load_opacity_from_settings()
        
        # Initialize theme system
        self._init_theme_system()
        
        # Assign object name so selective stylesheet rules don't leak globally
        self.setObjectName("repl-root")
        
        # Enable transparency support for the widget
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set transparent background like in working minimal test
        self.setStyleSheet("REPLWidget { background-color: transparent; }")

        # Enable drag and drop
        self.setAcceptDrops(True)

        self._init_ui()
        self._apply_styles()
        self._update_component_themes()  # Apply theme to all components after UI init
        
        # CRITICAL: Apply opacity immediately after initialization
        # This ensures opacity takes effect on startup
        self._apply_startup_opacity()
        
        self._init_conversation_manager()
        
        # Load conversations after UI is fully initialized
        QTimer.singleShot(100, self._load_conversations_deferred)
        
        # Load dimensions after UI is fully initialized
        QTimer.singleShot(200, self._load_window_dimensions)
        
        logger.info("Enhanced REPLWidget initialized with conversation management")

    @property
    def output_display(self):
        """
        Get the active tab's output display widget.
        This property provides backward compatibility - code can still use self.output_display,
        but it now points to the active tab's widget instead of a shared widget.
        """
        # Check if tab manager exists and has an active tab
        if hasattr(self, 'tab_manager') and self.tab_manager and self.tab_manager.active_tab_id:
            active_tab = self.tab_manager.get_active_tab()
            if active_tab and active_tab.output_display:
                return active_tab.output_display

        # Return None during initialization or when no tabs exist
        # This is normal during app startup before tabs are created
        return None

    @property
    def file_browser_bar(self):
        """
        Get the active tab's file browser widget.
        This property provides backward compatibility - code can still use self.file_browser_bar,
        but it now points to the active tab's widget instead of a shared widget.
        """
        # Check if tab manager exists and has an active tab
        if hasattr(self, 'tab_manager') and self.tab_manager and self.tab_manager.active_tab_id:
            active_tab = self.tab_manager.get_active_tab()
            if active_tab and hasattr(active_tab, 'file_browser'):
                return active_tab.file_browser

        # Return None during initialization or when no tabs exist
        return None

    def _init_dynamic_input_height(self):
        """Initialize dynamic input height system."""
        # Initialize variables for dynamic height management
        self.max_input_lines = 5
        self.min_input_lines = 1
        self.line_height = 0  # Will be calculated based on font
        self.current_line_count = 1
        self.current_visual_lines = 1  # Includes wrapped lines
        
        # Create height animation
        self.height_animation = QPropertyAnimation(self.command_input, b"maximumHeight")
        self.height_animation.setDuration(150)  # 150ms smooth transition
        self.height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Calculate initial line height
        self._calculate_line_height()
        
        # Connect text changes to height updates
        self.command_input.textChanged.connect(self._on_input_text_changed)
        
        # Override resize event to recalculate height when width changes (affects wrapping)
        original_resize = self.command_input.resizeEvent
        def on_input_resize(event):
            original_resize(event)
            QTimer.singleShot(50, self._update_input_height)  # Delay to let Qt finish resizing
        self.command_input.resizeEvent = on_input_resize
        
        # Set initial height
        self._update_input_height()
    
    def _calculate_line_height(self):
        """Calculate the height of a single line based on font metrics."""
        if hasattr(self, 'command_input') and self.command_input:
            font_metrics = QFontMetrics(self.command_input.font())
            # Use lineSpacing() instead of height() for more accurate line height calculation
            # lineSpacing() includes the natural spacing between lines as intended by the font designer
            self.line_height = font_metrics.lineSpacing()
            
            # Ensure minimum line height for readability - this prevents overly compressed text
            # even with very small fonts
            MIN_LINE_HEIGHT = 16  # Minimum reasonable line height for readability
            self.line_height = max(self.line_height, MIN_LINE_HEIGHT)
    
    def _on_input_text_changed(self):
        """Handle input text changes to update height dynamically."""
        if not hasattr(self, 'command_input') or not self.command_input:
            return
        
        # Always update height when text changes (handles both wrapping and manual breaks)
        # Use a short delay to let Qt finish updating the document layout
        QTimer.singleShot(10, self._check_visual_lines_change)
        
        # Also update block count for other purposes
        document = self.command_input.document()
        self.current_line_count = document.blockCount()
    
    def _check_visual_lines_change(self):
        """Check if visual lines have changed and update height accordingly."""
        if not hasattr(self, 'command_input') or not self.command_input:
            return
            
        # Calculate visual lines (includes both manual breaks and wrapped text)
        new_visual_lines = self._calculate_visual_lines()
        
        # Initialize if not set
        if not hasattr(self, 'current_visual_lines'):
            self.current_visual_lines = 1
            
        # Always update height (even if line count is same, text content may affect wrapping)
        logger.debug(f"📏 Checking visual lines: current={getattr(self, 'current_visual_lines', 1)} -> new={new_visual_lines}")
        if new_visual_lines != self.current_visual_lines:
            logger.debug(f"📏 Visual lines changed: {self.current_visual_lines} -> {new_visual_lines}")
            self.current_visual_lines = new_visual_lines
            self._update_input_height()
        else:
            # Even if line count is same, force height recalculation in case wrapping changed
            self._update_input_height()
    
    def _update_input_height(self):
        """Update the input field height based on current line count including wrapped lines."""
        if not self.line_height:
            self._calculate_line_height()  # Ensure line height is calculated
            if not self.line_height:
                return
        
        # Use the current visual lines count (already calculated in text changed handler)
        total_visual_lines = getattr(self, 'current_visual_lines', 1)
        
        # Constrain line count to min/max limits
        effective_lines = max(self.min_input_lines, min(self.max_input_lines, total_visual_lines))
        
        # Calculate new height based on content, but account for QPlainTextEdit's internal margins
        # QPlainTextEdit has internal document margins that need to be accounted for
        content_height = effective_lines * self.line_height
        
        # Get the QPlainTextEdit's content margins and frame width
        margins = self.command_input.contentsMargins()
        frame_width = self.command_input.frameWidth() if hasattr(self.command_input, 'frameWidth') else 1
        
        # Calculate total internal padding (margins + frame + document margins)
        vertical_padding = margins.top() + margins.bottom() + (frame_width * 2) + 4  # 4px for document margins
        
        # CRITICAL: For single line, force exactly 32px to match button height
        # For multiple lines, calculate based on content
        BUTTON_HEIGHT = 32  # This matches the button height from ButtonStyleManager "small" size
        
        if effective_lines == 1:
            # Single line: force exact button height for perfect alignment
            new_height = BUTTON_HEIGHT
        else:
            # Multiple lines: calculate based on content but ensure minimum
            proposed_height = content_height + vertical_padding
            new_height = max(proposed_height, BUTTON_HEIGHT)
        
        # Enable/disable scrollbar based on line count
        if total_visual_lines > self.max_input_lines:
            self.command_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.command_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Update height (no animation needed, just set directly)
        current_height = self.command_input.maximumHeight()
        if current_height != new_height:
            # Set both minimum and maximum height to the calculated value
            self.command_input.setMinimumHeight(new_height)
            self.command_input.setMaximumHeight(new_height)
            
            # Force a repaint to ensure the height change is visible
            self.command_input.updateGeometry()
    
    def _calculate_visual_lines(self):
        """Calculate the total number of visual lines including wrapped text."""
        try:
            document = self.command_input.document()
            text = self.command_input.toPlainText()
            
            # Debug logging for troubleshooting
            logger.debug(f"🔍 Visual lines calculation - text length: {len(text)}")
            logger.debug(f"🔍 Visual lines calculation - document blocks: {document.blockCount()}")
            logger.debug(f"🔍 Visual lines calculation - line_height: {self.line_height}")
            
            # Get viewport width for wrapping calculations
            viewport_width = self.command_input.viewport().width()
            logger.debug(f"🔍 Visual lines calculation - viewport width: {viewport_width}")
            
            if viewport_width <= 20:
                logger.debug("🔍 Visual lines calculation - invalid viewport width, using block count")
                return max(1, document.blockCount())
                
            # Set document width for proper wrapping calculation
            old_width = document.textWidth()
            document.setTextWidth(viewport_width - 10)  # Account for margins/padding
            
            # Force layout creation and ensure it's processed
            layout_engine = document.documentLayout()
            
            # Force the widget to process all pending layout updates
            self.command_input.updateGeometry()
            self.command_input.update()
            
            # Give Qt a moment to process the layout changes
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Use block-by-block line counting method (Qt recommended approach)
            total_lines = 0
            block = document.begin()
            
            while block.isValid():
                # Force layout creation for this specific block
                layout = block.layout()
                if layout and layout.lineCount() > 0:
                    line_count = layout.lineCount()
                    logger.debug(f"🔍 Block line count: {line_count}")
                    total_lines += line_count
                else:
                    # For blocks without layout or empty layout, count as 1 line minimum
                    # This handles manual line breaks (Shift+Enter) which create new blocks
                    total_lines += 1
                    logger.debug("🔍 No valid layout for block, using 1 line")
                block = block.next()
            
            # Restore original width
            document.setTextWidth(old_width)
            
            visual_lines = max(1, total_lines)
            logger.debug(f"🔍 Visual lines calculation - calculated visual lines: {visual_lines}")
            return visual_lines
            
        except Exception as e:
            logger.debug(f"🔍 Visual lines calculation exception: {e}")
            # Ultimate fallback
            return max(1, self.command_input.document().blockCount())
    
    def _on_input_font_changed(self):
        """Handle font changes by recalculating line height and updating input height."""
        self._calculate_line_height()
        self._update_input_height()
    
    def _init_theme_system(self):
        """Initialize theme system connection."""
        if THEME_SYSTEM_AVAILABLE:
            try:
                self.theme_manager = get_theme_manager()
                # Register with theme manager for automatic theme updates (prefer this over signal)
                self.theme_manager.register_widget(self, "_on_theme_changed")
                # Note: Removed redundant signal connection to prevent double theme updates
                logger.debug("Theme system initialized for REPL widget")
            except Exception as e:
                logger.warning(f"Failed to initialize theme system: {e}")
                self.theme_manager = None
        else:
            self.theme_manager = None
            logger.debug("Theme system not available - using legacy styling")
    
    def _on_theme_changed(self, color_system):
        """Handle theme changes by updating widget styles."""
        try:
            # Update all styling when theme changes
            self._apply_styles()
            self._update_component_themes()
            
            # CRITICAL: Update output display theme colors - this was missing!
            self._style_output_display()
            
            # Update conversation selector styling
            if hasattr(self, 'conversation_selector'):
                self._style_conversation_selector()
            
            # Update send button styling
            if hasattr(self, 'send_button'):
                self._style_send_button()
            
            # Update dynamic input height system for potential font changes
            if hasattr(self, 'command_input') and hasattr(self, 'line_height'):
                self._on_input_font_changed()
            
            # Update stop button styling
            if hasattr(self, 'stop_button'):
                self._style_stop_button()
            
            # Update save button icon for theme changes
            if hasattr(self, 'title_save_btn'):
                self._load_save_icon(self.title_save_btn)
                logger.debug("Save button icon updated for theme change")
            
            # Update search elements if they exist - use high-contrast styling
            if hasattr(self, 'search_status_label'):
                from ...ui.themes.style_templates import StyleTemplates
                self.search_status_label.setStyleSheet(StyleTemplates.get_high_contrast_search_status_style(self.theme_manager.current_theme))
            
            # Update summary notification styling
            if hasattr(self, 'summary_notification'):
                summary_color = self.theme_manager.current_theme.status_success
                self.summary_notification.setStyleSheet(f"color: {summary_color}; font-size: 9px; font-style: italic;")
            
            # Update markdown renderer to use new theme colors
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.update_theme()
                logger.debug("Markdown renderer updated with new theme colors")
            
            # Re-render existing conversation with new colors
            self._refresh_existing_output()
            logger.debug("Existing conversation re-rendered with new theme colors")
            
            # CRITICAL: Force style refresh for all components to ensure immediate theme updates
            self._force_comprehensive_style_refresh()
            
            # CRITICAL: Ensure tab frame transparency after theme changes
            # Schedule this to run after theme styles have been fully applied
            self._schedule_tab_transparency_enforcement()
            
            # Update tab button styles with new theme
            if hasattr(self, 'tab_manager') and self.tab_manager:
                self.tab_manager.refresh_tab_styles()
                logger.debug("Tab button styles refreshed with new theme")
            
            logger.debug("REPL widget styles updated for new theme")
        except Exception as e:
            logger.error(f"Failed to update REPL widget theme: {e}")
    
    def _force_comprehensive_style_refresh(self):
        """Force a comprehensive style refresh for all UI elements."""
        try:
            # Re-style all menus with new theme
            self._refresh_menu_styling()
            
            # Force Qt to re-evaluate all stylesheets and polish all widgets
            QApplication.processEvents()
            
            # Update all children recursively
            self._force_widget_polish_recursive(self)
            
            # Force a repaint
            self.update()
            
            logger.debug("Comprehensive style refresh completed")
            
        except Exception as e:
            logger.warning(f"Failed to force comprehensive style refresh: {e}")
    
    def _force_widget_polish_recursive(self, widget):
        """Recursively force polish all widgets to apply new styles."""
        try:
            # Force style refresh for this widget
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
            
            # Recursively apply to all children
            for child in widget.findChildren(QWidget):
                try:
                    child.style().unpolish(child)
                    child.style().polish(child)
                    child.update()
                except Exception:
                    # Skip widgets that can't be polished
                    pass
                    
        except Exception as e:
            logger.warning(f"Failed to force polish widget {widget}: {e}")
    
    def _style_command_input(self):
        """Apply theme-aware styling to the command input field."""
        if not (self.theme_manager and THEME_SYSTEM_AVAILABLE):
            return
        
        try:
            colors = self.theme_manager.current_theme
            self.command_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_primary};
                    border: 2px solid {colors.border_secondary};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 13px;
                    selection-background-color: {colors.primary};
                    selection-color: {colors.background_primary};
                }}
                QLineEdit:focus {{
                    border-color: {colors.border_focus};
                }}
                QLineEdit:hover {{
                    border-color: {colors.primary};
                }}
            """)
        except Exception as e:
            logger.warning(f"Failed to style command input: {e}")
    
    def _style_output_display(self):
        """Apply theme-aware styling to the output display with TRUE transparency support."""
        if not (self.theme_manager and THEME_SYSTEM_AVAILABLE):
            return
        
        try:
            colors = self.theme_manager.current_theme
            
            # Apply TRUE transparency to background
            alpha = max(0.0, min(1.0, self._panel_opacity))
            if alpha >= 0.99:
                # Nearly/fully opaque - use original hex color
                bg_color = colors.background_primary
            else:
                # TRUE TRANSPARENCY - use rgba with actual transparency
                if colors.background_primary.startswith('#'):
                    r = int(colors.background_primary[1:3], 16)
                    g = int(colors.background_primary[3:5], 16)
                    b = int(colors.background_primary[5:7], 16)
                    bg_color = f"rgba({r}, {g}, {b}, {alpha:.3f})"
                else:
                    # Fallback for non-hex colors
                    bg_color = f"rgba(30, 30, 30, {alpha:.3f})"
            
            # Create theme color dictionary for MixedContentDisplay
            # Use theme-specific colors directly from ColorSystem - NO generic fallbacks
            theme_colors = {
                'bg_primary': bg_color,
                'bg_secondary': colors.background_secondary,
                'bg_tertiary': colors.background_tertiary,
                'text_primary': colors.text_primary,
                'text_secondary': colors.text_secondary,
                'border': colors.border_primary,
                'info': colors.status_info,  # Use theme's unique status colors
                'warning': colors.status_warning,
                'error': colors.status_error,
                'keyword': colors.primary,  # Use theme's primary color for keywords
                'string': colors.secondary,  # Use theme's secondary color for strings
                'comment': colors.text_tertiary,  # Use theme's tertiary text for comments
                'function': colors.primary,  # Use theme's primary color for functions
                'number': colors.secondary,  # Use theme's secondary color for numbers
                'interactive': colors.interactive_normal,  # Use proper ColorSystem properties
                'interactive_hover': colors.interactive_hover,
                'selection': colors.primary
            }
            
            # Apply theme colors to ALL tab widgets, not just the active one
            # Since we now have per-tab widgets, we need to update all of them
            if hasattr(self, 'tab_manager') and self.tab_manager:
                tabs_updated = 0
                for tab in self.tab_manager.tabs.values():
                    if tab.output_display:
                        tab.output_display.set_theme_colors(theme_colors)
                        tabs_updated += 1
                logger.debug(f"Applied theme colors to {tabs_updated} tab widgets with opacity: {alpha:.3f}")
            elif hasattr(self, 'output_display') and self.output_display:
                # Fallback for old code or if tab_manager doesn't exist yet
                self.output_display.set_theme_colors(theme_colors)
                logger.debug(f"Applied MixedContentDisplay theme colors with opacity: {alpha:.3f}")
        except Exception as e:
            logger.warning(f"Theme update handled automatically by theme manager: {e}")
    
    def _update_layout_component_themes(self):
        """Update theme styling for layout components like frames and separators."""
        if not (self.theme_manager and THEME_SYSTEM_AVAILABLE):
            return
        
        try:
            colors = self.theme_manager.current_theme
            
            # Update all QFrame widgets with theme-aware styling
            for frame in self.findChildren(QFrame):
                if frame.frameStyle() != QFrame.Shape.NoFrame:
                    frame.setStyleSheet(f"""
                        QFrame {{
                            background-color: {colors.background_secondary};
                            border: none;
                        }}
                    """)
            
            # Update any separator lines
            for label in self.findChildren(QLabel):
                if hasattr(label, 'objectName') and 'separator' in label.objectName():
                    label.setStyleSheet(f"background-color: {colors.separator};")
                    
        except Exception as e:
            logger.warning(f"Failed to update layout component themes: {e}")
    
    def _update_component_themes(self):
        """Update individual component styles based on current theme."""
        if not (self.theme_manager and THEME_SYSTEM_AVAILABLE):
            return
        
        try:
            colors = self.theme_manager.current_theme
            
            # Update title frame if it exists
            if hasattr(self, 'title_frame'):
                self.title_frame.setStyleSheet(StyleTemplates.get_title_frame_style(colors))
            
            # Update various buttons if they exist
            if hasattr(self, 'send_button'):
                self._style_send_button()
            
            if hasattr(self, 'stop_button'):
                self._style_stop_button()
            
            # Update conversation selector if it exists
            if hasattr(self, 'conversation_selector'):
                self.conversation_selector.setStyleSheet(StyleTemplates.get_combo_box_style(colors))
            
            # Update search frame if it exists
            if hasattr(self, 'search_frame'):
                self.search_frame.setStyleSheet(StyleTemplates.get_search_frame_style(colors))
                
            # Update search input if it exists
            if hasattr(self, 'search_input'):
                input_style = self._get_search_input_style()
                self.search_input.setStyleSheet(input_style)
                # Ensure frame is always disabled after theme changes
                self.search_input.setFrame(False)
                
            # Update search icon label if it exists
            if hasattr(self, 'search_icon_label'):
                self.search_icon_label.setStyleSheet(f"""
                    QLabel {{
                        color: {colors.text_primary};
                        background: transparent;
                        border: none !important;
                        border-width: 0px !important;
                        border-style: none !important;
                        border-color: transparent !important;
                        outline: none !important;
                        padding: 0px;
                        font-size: 14px;
                    }}
                """)
            
            # Update status labels to use theme colors
            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(StyleTemplates.get_label_style(colors, "secondary"))
            
            if hasattr(self, 'search_status_label'):
                # Use high-contrast styling instead of generic tertiary text
                self.search_status_label.setStyleSheet(StyleTemplates.get_high_contrast_search_status_style(colors))
            
            if hasattr(self, 'summary_notification'):
                self.summary_notification.setStyleSheet(StyleTemplates.get_label_style(colors, "success"))
            
            # Update main output display styling with current opacity
            if hasattr(self, 'output_display'):
                self._style_output_display()
            
            # Update main input field styling
            if hasattr(self, 'command_input'):
                self._style_command_input()
            
            # Update all QToolButton widgets with new theme
            self._update_all_tool_buttons()
            
            # Re-apply search button size constraints after theme styling
            self._reapply_search_button_sizing()
            
            # Update all icon buttons to match new theme variant (dark/lite)
            if hasattr(self, 'title_help_btn'):
                self._load_help_icon(self.title_help_btn)
            
            if hasattr(self, 'help_command_btn'):
                self._load_help_command_icon(self.help_command_btn)
            
            if hasattr(self, 'title_settings_btn'):
                self._load_gear_icon(self.title_settings_btn)
            
            if hasattr(self, 'title_new_btn'):
                self._load_plus_icon(self.title_new_btn)
            
            if hasattr(self, 'chat_btn'):
                self._load_chat_icon()
            
            if hasattr(self, 'attach_btn'):
                self._load_chain_icon()
            
            if hasattr(self, 'upload_btn'):
                self._load_filebar_icon()
            
            if hasattr(self, 'move_btn'):
                self._load_move_icon(self.move_btn)
            
            # Update main input field styling
            if hasattr(self, 'command_input'):
                self._style_command_input()
            
            # Update main output display styling
            if hasattr(self, 'output_display'):
                self._style_output_display()
            
            # Ensure all layout components get theme updates
            self._update_layout_component_themes()
            
            if hasattr(self, 'search_btn'):
                self._load_search_icon()
            
            if hasattr(self, 'pin_btn'):
                self._load_pin_icon()
            
            # Update button visual states
            if hasattr(self, 'search_btn'):
                self._update_search_button_state()
            if hasattr(self, 'upload_btn'):
                self._update_upload_button_state()
            if hasattr(self, 'attach_btn'):
                self._update_attach_button_state()
            if hasattr(self, 'pin_btn'):
                self._update_pin_button_state()
            
            # Reload theme-specific icons
            if hasattr(self, 'search_btn'):
                self._load_search_icon()
            self._load_chain_icon()
            if hasattr(self, 'upload_btn'):
                self._load_filebar_icon()
            if hasattr(self, 'chat_btn'):
                self._load_chat_icon()
            if hasattr(self, 'title_settings_btn'):
                self._load_gear_icon(self.title_settings_btn)
            if hasattr(self, 'settings_btn'):
                self._load_gear_icon(self.settings_btn)
            if hasattr(self, 'title_new_conv_btn'):
                self._load_plus_icon(self.title_new_conv_btn)
            if hasattr(self, 'move_btn'):
                self._load_move_icon(self.move_btn)
            if hasattr(self, 'pin_btn'):
                self._load_pin_icon()
            
            # Note: help_btn is a local variable, so it's handled during initialization
            
            # Update prompt label with new theme
            if hasattr(self, 'prompt_label'):
                # Check if we're currently in processing mode
                current_text = self.prompt_label.text()
                is_processing = current_text != ">>>"
                self._style_prompt_label(normal=not is_processing, processing=is_processing)
            
            # Refresh toolbar button icons to prevent ellipses
            self._refresh_toolbar_icons()
            
        except Exception as e:
            logger.error(f"Failed to update component themes: {e}")
    
    def _update_all_tool_buttons(self):
        """Update all QToolButton and QPushButton widgets in the widget hierarchy with current theme."""
        try:
            # Find all QToolButton and QPushButton widgets recursively
            from PyQt6.QtWidgets import QPushButton, QToolButton
            tool_buttons = self.findChildren(QToolButton)
            push_buttons = self.findChildren(QPushButton)
            all_buttons = tool_buttons + push_buttons
            
            for button in all_buttons:
                # Special handling for send button
                if button == getattr(self, 'send_button', None):
                    self._style_send_button()
                    continue
                
                # Special handling for stop button
                if button == getattr(self, 'stop_button', None):
                    self._style_stop_button()
                    continue
                    
                # Determine if this is a title button or toolbar button based on size/properties
                if hasattr(button, 'parent') and button.parent():
                    # Check if it's in the title area (approximate check)
                    size = button.size()
                    if size.height() <= 25 and size.width() <= 32:
                        # This looks like a title button (including minimize button)
                        self._style_title_button(button, button.width() > 30)
                    else:
                        # This looks like a toolbar button
                        if isinstance(button, QToolButton):
                            self._style_tool_button(button)
                        else:
                            # For QPushButton, use title button styling if it's small
                            self._style_title_button(button)
                        
                    # Ensure emoji text is preserved during theme updates
                    current_text = button.text()
                    if current_text and len(current_text) <= 2:  # Likely an emoji
                        # Refresh emoji with proper font context
                        button_name = getattr(button, 'objectName', lambda: 'unknown')()
                        self._restore_button_emoji(button, current_text, button_name)
                        
            logger.debug(f"Updated {len(all_buttons)} buttons ({len(tool_buttons)} QToolButton, {len(push_buttons)} QPushButton) with current theme")
            
        except Exception as e:
            logger.error(f"Failed to update tool buttons: {e}")
    
    def _style_prompt_label(self, normal=True, processing=False):
        """Style the prompt label with theme-aware colors."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme

            # Base background tiers with graceful fallback
            bg_secondary = getattr(colors, 'background_secondary', getattr(colors, 'background_primary', '#222'))
            bg_tertiary = getattr(colors, 'background_tertiary', bg_secondary)

            if processing:
                # Emphasize processing with theme-aware accent color (primary or info status)
                text_color = getattr(colors, 'primary', getattr(colors, 'status_info', getattr(colors, 'text_primary', '#4CAF50')))
                bg_color = bg_tertiary
                border_color = getattr(colors, 'border_focus', getattr(colors, 'border_secondary', '#777'))
            else:
                # Normal prompt: primary color text on secondary background
                text_color = getattr(colors, 'primary', getattr(colors, 'text_primary', '#4CAF50'))
                bg_color = bg_secondary
                border_color = getattr(colors, 'border_secondary', '#555')

            # Avoid identical bg/text
            if text_color.lower() == bg_color.lower():
                # Use smart fallback based on background brightness
                fallback_text = self._get_smart_text_fallback(bg_color)
                text_color = getattr(colors, 'text_primary', fallback_text)

            # Compose stylesheet (force solid background independent of panel opacity)
            self.prompt_label.setStyleSheet(
                "QLabel { "
                f"color: {text_color}; "
                f"background-color: {bg_color}; "
                f"border: 1px solid {border_color}; "
                "border-radius: 4px; "
                "font-family: Segoe UI Emoji, Consolas, monospace; "
                "font-size: 11px; "
                "padding: 5px 8px; "  # Consistent padding to prevent size changes
                "margin-right: 6px; "
                "}"
            )
        else:
            # Fallback to improved colors without background - keep transparent 
            if processing:
                color = "#FF9800"  # Material orange
            else:
                color = "#4CAF50"  # Material green
                
            # Use string formatting to avoid CSS syntax issues
            self.prompt_label.setStyleSheet(
                f"color: {color}; "
                f"font-family: Segoe UI Emoji, Consolas, monospace; "
                f"font-size: 11px; "
                f"padding: 5px 8px; "
                f"margin-right: 5px; "
                f"background-color: transparent; "
                f"opacity: 1.0;"
            )
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB values for rgba()."""
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    
    def _get_uniform_button_style(self, size="medium", button_type="push"):
        """
        DEPRECATED: Use ButtonStyleManager.get_unified_button_style() instead.
        Legacy wrapper for backward compatibility.
        """
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            return ButtonStyleManager.get_unified_button_style(colors, button_type, size)
        else:
            # Fallback for systems without theme support
            return ButtonStyleManager.get_unified_button_style(None, button_type, size)
    
    def _get_themed_button_style(self, variant="secondary"):
        """Get themed button style string (legacy method for backward compatibility)."""
        return self._get_uniform_button_style("medium", "tool")
    
    def _get_search_checkbox_style(self):
        """Get theme-aware styling for search checkbox."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            return f"""
                QCheckBox {{
                    color: {colors.text_primary};
                    spacing: {{'2px'}};
                    font-size: {{'10px'}};
                    font-weight: bold;
                }}
                QCheckBox::indicator {{
                    width: {{'14px'}};
                    height: {{'14px'}};
                    border: {{'1px'}} solid {colors.border_secondary};
                    background-color: {colors.interactive_normal};
                    border-radius: {{'2px'}};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {colors.primary};
                    border-color: {colors.primary};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {colors.border_focus};
                }}
            """
        else:
            return """
                QCheckBox {
                    color: white;
                    spacing: 2px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QCheckBox::indicator {
                    width: 14px;
                    height: 14px;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #FFA500;
                    border-color: #FFA500;
                }
                QCheckBox::indicator:hover {
                    border-color: rgba(255, 255, 255, 0.5);
                }
            """
    
    def _get_search_input_style(self):
        """
        Get theme-aware styling for search input with expert PyQt6 border removal.
        
        This method combines CSS styling with the native Qt border removal techniques
        applied in the widget creation for maximum effectiveness.
        
        The CSS here works in conjunction with:
        1. setFrame(False) - Primary Qt-native border removal
        2. setAutoFillBackground(False) - Prevents styling conflicts  
        3. Proper focus policy - Removes focus ring artifacts
        4. Parent frame border removal - Prevents hierarchy inheritance
        """
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            return f"""
                QLineEdit {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_primary};
                    border: none !important;
                    border-width: 0px !important;
                    border-style: none !important;
                    border-color: transparent !important;
                    outline: none !important;
                    padding: 4px 6px;
                    border-radius: 3px;
                    font-size: 11px;
                    selection-background-color: {colors.primary};
                    selection-color: {colors.background_primary};
                }}
                QLineEdit:focus {{
                    border: none !important;
                    outline: none !important;
                    background-color: {colors.background_secondary};
                }}
                QLineEdit:hover {{
                    border: none !important;
                    outline: none !important;
                }}
                QLineEdit:selected {{
                    border: none !important;
                    outline: none !important;
                }}
            """
        else:
            # Fallback styles - ALWAYS fully opaque with comprehensive border removal
            return f"""
                QLineEdit {{
                    background-color: rgba(30, 30, 30, 1.0);
                    color: #ffffff;
                    border: none !important;
                    border-width: 0px !important;
                    border-style: none !important;
                    border-color: transparent !important;
                    outline: none !important;
                    padding: 4px 6px;
                    border-radius: 3px;
                    font-size: 11px;
                    selection-background-color: #4CAF50;
                    selection-color: rgba(30, 30, 30, 1.0);
                }}
                QLineEdit:focus {{
                    border: none !important;
                    outline: none !important;
                    background-color: rgba(30, 30, 30, 1.0);
                }}
                QLineEdit:hover {{
                    border: none !important;
                    outline: none !important;
                }}
                QLineEdit:selected {{
                    border: none !important;
                    outline: none !important;
                }}
            """
    
    def _init_conversation_manager(self):
        """Initialize conversation management system."""
        if not ConversationManager:
            logger.warning("Conversation management not available - running in basic mode")
            return
        
        try:
            self.conversation_manager = ConversationManager()
            if self.conversation_manager.initialize():
                logger.info("✓ Conversation manager initialized successfully")

                # OPTIMIZATION: Set file browser reference in AI service for RAG query optimization
                self._set_file_browser_reference_in_ai_service()
            else:
                logger.error("✗ Failed to initialize conversation manager")
                self.conversation_manager = None
        except Exception as e:
            logger.error(f"✗ Conversation manager initialization failed: {e}")
            self.conversation_manager = None
    
    def _perform_startup_tasks(self):
        """Perform application startup tasks and display preamble."""
        # Prevent multiple executions during theme switching or re-initialization
        if self._startup_tasks_completed:
            logger.debug("Startup tasks already completed - skipping duplicate execution")
            return
            
        try:
            logger.info("Performing startup tasks...")
            
            # Perform startup tasks
            startup_result = startup_service.perform_startup_tasks()
            
            # Only show preamble if there's an issue (API failure, errors, etc)
            api_status = startup_result.get('api_status', True)
            errors = startup_result.get('errors', [])
            
            if not api_status or errors:
                # Show error message if API failed or there are errors
                if not api_status:
                    self.append_output("⚠️ API connection failed - check settings", "warning")
                for error in errors:
                    self.append_output(f"❌ {error}", "error")
                self.append_output("-" * 50, "system")
            # Otherwise show nothing - clean start
            
            logger.info(f"Startup tasks completed - first_run: {startup_result.get('first_run')}, api_status: {api_status}")
            
            # Don't auto-create conversations on startup - wait for user to actually send a message
            
            # Mark startup tasks as completed to prevent re-execution during theme switching
            self._startup_tasks_completed = True
            
        except Exception as e:
            logger.error(f"✗ Failed to perform startup tasks: {e}")
            # Show error only
            self.append_output(f"❌ Startup failed: {e}", "error")
            
            # Mark startup tasks as completed even on failure to prevent retry loops
            self._startup_tasks_completed = True
    
    def _auto_create_startup_conversation(self):
        """Automatically create a new conversation on startup."""
        try:
            logger.info("🆕 Auto-creating new conversation on startup...")
            
            # Check if we already have a current conversation
            if hasattr(self, 'current_conversation') and self.current_conversation:
                logger.info("Current conversation already exists - skipping auto-creation")
                return
            
            # Verify we have conversation management available
            if not self.conversation_manager:
                logger.debug("No conversation manager available - skipping auto-creation")
                return
            
            # Get AI service for conversation integration
            ai_service = None
            if self.conversation_manager:
                ai_service = self.conversation_manager.get_ai_service()
            
            if not ai_service or not hasattr(ai_service, 'conversation_service'):
                logger.debug("AI service doesn't support conversation management - skipping auto-creation")
                return
            
            # Use the working _start_new_conversation approach but without saving current
            # Since this is startup, there should be no current conversation to save
            self._start_new_conversation(save_current=False)
            logger.info("✓ Auto-creation initiated using _start_new_conversation")
            
        except Exception as e:
            logger.error(f"Failed to auto-create startup conversation: {e}")
            # Don't show error to user - this is a nice-to-have feature
    
    def _load_conversations_deferred(self):
        """Load conversations after UI is fully initialized."""
        # Perform startup tasks first
        self._perform_startup_tasks()
        
        if not self.conversation_manager:
            logger.debug("No conversation manager available for deferred loading")
            return
        
        try:
            logger.debug("Starting deferred conversation loading...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.debug("Event loop is running, creating task for deferred loading...")
                asyncio.create_task(self._load_conversations())
            else:
                logger.debug("Event loop not running, using run_until_complete for deferred loading...")
                loop.run_until_complete(self._load_conversations())
            logger.debug("Deferred conversation loading initiated successfully")
        except Exception as e:
            logger.error(f"✗ Failed deferred conversation loading: {e}", exc_info=True)
            # Ensure state is valid
            self.conversations_list = []
            self.current_conversation = None
    
    async def _load_conversations(self):
        """Load recent conversations into selector."""
        if not self.conversation_manager:
            logger.warning("No conversation manager available for loading conversations")
            return
        
        try:
            logger.debug("Loading conversations from conversation manager...")
            # Fix any issues with multiple active conversations before loading
            if hasattr(self.conversation_manager, 'fix_multiple_active_conversations'):
                fixed = self.conversation_manager.fix_multiple_active_conversations()
                if fixed:
                    logger.debug("✓ Verified conversation uniqueness")
            
            # Get recent conversations (all statuses) for the conversation UI
            conversations = await self.conversation_manager.list_conversations(limit=20)
            logger.debug(f"Loaded {len(conversations)} conversations")
            self.conversations_list = conversations
            
            # Set current conversation to the active one (if any), otherwise most recent
            self.current_conversation = None
            if conversations:
                # Find the active conversation
                active_conversations = [c for c in conversations if c.status == ConversationStatus.ACTIVE]
                if len(active_conversations) > 1:
                    logger.warning(f"⚠  Found {len(active_conversations)} active conversations after cleanup - this should not happen")
                    # Use the first one but log the issue
                    active_conversations = active_conversations[:1]
                if active_conversations:
                    self.current_conversation = active_conversations[0]
                    logger.debug(f"Set current conversation to active: {self.current_conversation.title}")
                else:
                    # If no active conversation, set the most recent as current
                    self.current_conversation = conversations[0] 
                    logger.debug(f"No active conversation found, set current to most recent: {conversations[0].title}")
            else:
                logger.debug("No conversations found - no current conversation set")
            
            logger.info(f"📋 Loaded {len(conversations)} conversations")

            # Create initial tab if tab manager exists and no tabs created yet
            if hasattr(self, 'tab_manager') and self.tab_manager and len(self.tab_manager.tabs) == 0:
                logger.info("Creating initial tab for current conversation...")
                # Determine tab title from current conversation
                if self.current_conversation and self.current_conversation.title:
                    tab_title = self.current_conversation.title[:23] + "..." if len(self.current_conversation.title) > 25 else self.current_conversation.title
                else:
                    tab_title = "New Conversation"

                # Create and activate the first tab
                first_tab_id = self.tab_manager.create_tab(title=tab_title, activate=True)
                logger.info(f"✅ Created initial tab: {first_tab_id}")

            # Simple UI refresh
            if hasattr(self, '_refresh_conversation_selector'):
                QTimer.singleShot(50, self._refresh_conversation_selector)

        except Exception as e:
            logger.error(f"✗ Failed to load conversations: {e}", exc_info=True)
            # Ensure state is valid even if conversation loading fails
            self.conversations_list = []
            self.current_conversation = None
    
    def _get_status_icon(self, conversation: Optional[Conversation]) -> str:
        """Get status icon for conversation."""
        if not conversation:
            return "🆕"
        
        if not ConversationStatus:
            return "💬"
        
        status_icons = {
            ConversationStatus.ACTIVE: "🔥",
            ConversationStatus.PINNED: "⭐", 
            ConversationStatus.ARCHIVED: "📦",
            ConversationStatus.DELETED: "🗑️"
        }
        return status_icons.get(conversation.status, "💬")
    
    def _update_status_label(self, conversation: Optional[Conversation]):
        """Update status label based on conversation."""
        # Only update if status_label exists (it may not in simplified UI)
        if not hasattr(self, 'status_label'):
            return
            
        if not conversation:
            self.status_label.setText("🆕 New")
            new_color = self.theme_manager.current_theme.status_info if (self.theme_manager and THEME_SYSTEM_AVAILABLE) else "#FFA500"
            self.status_label.setStyleSheet(f"color: {new_color}; font-weight: bold; font-size: 10px;")
            return
        
        status_text = conversation.status.value.title()
        icon = self._get_status_icon(conversation)
        self.status_label.setText(f"{icon} {status_text}")
        
        # Color coding based on status with theme support
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = {
                "Active": self.theme_manager.current_theme.status_success,
                "Pinned": self.theme_manager.current_theme.status_warning, 
                "Archived": self.theme_manager.current_theme.text_disabled,
                "Deleted": self.theme_manager.current_theme.status_error
            }
        else:
            colors = {
                "Active": "#4CAF50",
                "Pinned": "#FFD700", 
                "Archived": "#888888",
                "Deleted": "#FF5555"
            }
        color = colors.get(status_text, colors.get("Active", "#4CAF50"))
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
        
        # Show summary indicator if available
        if conversation.summary:
            tooltip = f"Status: {status_text}\nSummary available: {conversation.summary.summary[:100]}..."
        else:
            tooltip = f"Status: {status_text}"
        
        self.status_label.setToolTip(tooltip)
    
    def _init_tab_bar(self, parent_layout):
        """Initialize simple tab bar above the title bar with clear background."""
        # Create a frame for the tab bar - give it a unique class to avoid inheritance
        self.tab_frame = QFrame()
        self.tab_frame.setObjectName("tab_frame")
        
        # Set the frame to have no parent background inheritance
        self.tab_frame.setAutoFillBackground(False)
        
        # Apply initial transparent styling (will be reinforced by _ensure_tab_frame_transparency)
        self.tab_frame.setStyleSheet("""
            QFrame[objectName="tab_frame"] {
                background-color: rgba(0,0,0,0) !important;
                background: none !important;
                border: none !important;
                margin: 0px;
                padding: 0px;
                min-height: 30px;
                max-height: 30px;
            }
        """)
        
        # Create horizontal layout for tabs
        self.tab_layout = QHBoxLayout(self.tab_frame)
        self.tab_layout.setContentsMargins(8, 4, 8, 4)
        self.tab_layout.setSpacing(4)
        
        # Initialize tab manager if available
        self.tab_manager = None
        if TAB_SYSTEM_AVAILABLE:
            # Add stretch to push tabs to the left
            self.tab_layout.addStretch()
            
            # Initialize tab manager but don't create initial tab yet
            # We'll create tabs on demand when user clicks "New Tab"
            # Pass parent_layout so tab manager can add its QStackedWidget to hold tab output widgets
            self.tab_manager = TabConversationManager(
                self,
                self.tab_frame,
                self.tab_layout,
                output_container_layout=parent_layout,
                create_initial_tab=False
            )
            
            # Connect tab manager signals
            self.tab_manager.tab_switched.connect(self._on_tab_switched)
            self.tab_manager.conversation_context_switched.connect(self._on_conversation_context_switched)
            self.tab_manager.tab_created.connect(self._on_tab_created)
            self.tab_manager.tab_closed.connect(self._on_tab_closed)
        else:
            # Create placeholder tabs only for non-tab systems
            self._create_placeholder_tabs()
            # Add stretch to push tabs to the left
            self.tab_layout.addStretch()
        
        # Add the tab frame to parent layout
        parent_layout.addWidget(self.tab_frame)
        
        # Schedule tab frame transparency enforcement after theme styles are applied
        self._schedule_tab_transparency_enforcement()
    
    def _ensure_tab_frame_transparency(self):
        """Force tab frame transparency using maximum CSS specificity."""
        if not hasattr(self, 'tab_frame'):
            return
            
        # Maximum specificity override with comprehensive background property coverage
        transparency_css = """
            QFrame[objectName="tab_frame"],
            #repl-root QFrame#tab_frame,
            #repl-root QFrame[objectName="tab_frame"] {
                background: transparent !important;
                background-color: transparent !important;
                background-image: none !important;
            }
        """
        
        try:
            self.tab_frame.setStyleSheet(transparency_css)
            # Force immediate style update
            self.tab_frame.style().polish(self.tab_frame)
        except Exception as e:
            logger.warning(f"Failed to enforce tab transparency: {e}")
    
    def _schedule_tab_transparency_enforcement(self):
        """Schedule tab transparency enforcement with multiple timing intervals."""
        try:
            # Immediate application
            self._ensure_tab_frame_transparency()
            
            # Schedule at multiple intervals to handle theme system timing
            QTimer.singleShot(10, self._ensure_tab_frame_transparency)
            QTimer.singleShot(50, self._ensure_tab_frame_transparency)
            QTimer.singleShot(100, self._ensure_tab_frame_transparency)
            
        except Exception as e:
            logger.warning(f"Failed to schedule tab transparency: {e}")
            
            # Also ensure autoFillBackground is disabled
            self.tab_frame.setAutoFillBackground(False)
            
            # Force immediate style update
            self.tab_frame.style().polish(self.tab_frame)
            
        except Exception as e:
            from ...utils.logger import logger
            logger.warning(f"Failed to enforce tab frame transparency: {e}")
    
    def _schedule_tab_transparency_enforcement(self):
        """Schedule tab frame transparency enforcement using QTimer for proper timing.
        
        This ensures the transparency override is applied after the theme system
        has finished applying its styles, preventing inheritance conflicts.
        """
        try:
            from PyQt6.QtCore import QTimer
            
            # Schedule multiple enforcement attempts to handle different timing scenarios
            # Immediate attempt (0ms) - for cases where theme hasn't been applied yet
            QTimer.singleShot(0, self._ensure_tab_frame_transparency)
            
            # Short delay (10ms) - for most theme application scenarios
            QTimer.singleShot(10, self._ensure_tab_frame_transparency)
            
            # Medium delay (50ms) - for complex theme loading scenarios
            QTimer.singleShot(50, self._ensure_tab_frame_transparency)
            
            # Longer delay (100ms) - safety net for slow systems
            QTimer.singleShot(100, self._ensure_tab_frame_transparency)
            
        except Exception as e:
            from ...utils.logger import logger
            logger.warning(f"Failed to schedule tab frame transparency enforcement: {e}")
            # Fallback to immediate application if QTimer fails
            self._ensure_tab_frame_transparency()
        
    def _create_placeholder_tabs(self):
        """Create placeholder tabs for UI consistency."""
        # Placeholder tab buttons (for UI consistency)
        self.tab_buttons = []
        
        # Add first placeholder tab (active)
        tab1 = QPushButton("Tab 1")
        tab1.setStyleSheet("""
            QPushButton {
                background-color: rgba(147, 112, 219, 0.9);
                color: white;
                border: 1px solid rgba(147, 112, 219, 1.0);
                border-radius: 3px;
                padding: 4px 12px;
                min-width: 60px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: rgba(147, 112, 219, 1.0);
            }
        """)
        self.tab_buttons.append(tab1)
        self.tab_layout.addWidget(tab1)
        
        # Add second placeholder tab (inactive)
        tab2 = QPushButton("Tab 2")
        tab2.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 60, 0.8);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                padding: 4px 12px;
                min-width: 60px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 0.9);
            }
        """)
        self.tab_buttons.append(tab2)
        self.tab_layout.addWidget(tab2)
        
        logger.debug("Created placeholder tabs for UI consistency")
    
    def _init_title_bar(self, parent_layout):
        """Initialize title bar with new conversation and help buttons."""
        # Create a frame for the title bar to make it more visible and draggable
        self.title_frame = QFrame()
        # Apply theme-aware styling - ALWAYS fully opaque
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            self.title_frame.setStyleSheet(StyleTemplates.get_title_frame_style(self.theme_manager.current_theme))
        else:
            # Fallback styles - ALWAYS fully opaque
            self.title_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(40, 40, 40, 1.0);
                    border: none;
                    border-radius: 5px;
                    margin: 0px;
                }}
            """)
        
        # Enable drag functionality for the title frame
        self.title_frame.mousePressEvent = self._title_mouse_press
        self.title_frame.mouseMoveEvent = self._title_mouse_move
        self.title_frame.mouseReleaseEvent = self._title_mouse_release
        self._dragging = False
        self._drag_pos = None
        
        title_layout = QHBoxLayout(self.title_frame)
        # Compensate for main layout's 10px top margin by reducing title layout top margin
        # This makes top (10px main + 0px title = 10px) equal to bottom (10px title)
        title_layout.setContentsMargins(8, 0, 8, 20) # left, top, right, bottom
        title_layout.setSpacing(8)  # space in between icon buttons
        
        # New conversation button with menu (with extra padding)
        self.title_new_conv_btn = QToolButton()
        # Load plus icon (theme-specific)
        self._load_plus_icon(self.title_new_conv_btn)
        # Icon size is now handled by ButtonStyleManager
        self.title_new_conv_btn.setToolTip("Start new conversation")
        # Don't set popup mode - we'll handle the menu manually
        self.title_new_conv_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.title_new_conv_btn.clicked.connect(self._show_new_conv_menu)
        #self.title_new_conv_btn.setFixedSize(40, 40)  
        
        # Create menu for new conversation options
        new_conv_menu = QMenu(self.title_new_conv_btn)
        
        # Add New Tab option if tab system is available
        if TAB_SYSTEM_AVAILABLE and hasattr(self, 'tab_manager') and self.tab_manager:
            new_tab_action = QAction("New Tab", self.title_new_conv_btn)
            new_tab_action.setIcon(self._load_themed_icon("new_tab"))
            new_tab_action.triggered.connect(self._create_new_tab)
            new_conv_menu.addAction(new_tab_action)
        
        # New conversation action
        new_action = QAction("New Conversation", self.title_new_conv_btn)
        new_action.setIcon(self._load_themed_icon("new"))
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Store menu reference but don't set it on the button (avoids arrow)
        self.title_new_conv_menu = new_conv_menu
        
        # Apply menu styling
        self._style_menu(new_conv_menu)
        
        # Apply styling without menu attached
        self._style_title_button(self.title_new_conv_btn, add_right_padding=True)
        
        title_layout.addWidget(self.title_new_conv_btn)
        
        # Save conversation button
        self.title_save_btn = QToolButton()
        # Load save icon (theme-specific)
        self._load_save_icon(self.title_save_btn)
        self.title_save_btn.setToolTip("Save current conversation")
        self.title_save_btn.clicked.connect(self._save_current_conversation)
        self._style_title_button(self.title_save_btn)
        title_layout.addWidget(self.title_save_btn)
        
        # Help documentation button (with help-docs icon)
        self.title_help_btn = QToolButton()
        # Load help icon (theme-specific)
        self._load_help_icon(self.title_help_btn)
        # Icon size is now handled by ButtonStyleManager
        self.title_help_btn.setToolTip("Open help documentation")
        self.title_help_btn.clicked.connect(self._on_help_clicked)
        self._style_title_button(self.title_help_btn)
        title_layout.addWidget(self.title_help_btn)
        
        # Help command button (with help icon)
        self.help_command_btn = QToolButton()
        self._load_help_command_icon(self.help_command_btn)
        self.help_command_btn.setToolTip("Send 'help' command to chat")
        self.help_command_btn.clicked.connect(self._on_help_command_clicked)
        self._style_title_button(self.help_command_btn)
        title_layout.addWidget(self.help_command_btn)
        
        # Settings button
        self.title_settings_btn = QToolButton()
        # Load gear icon (theme-specific)
        self._load_gear_icon(self.title_settings_btn)
        # Icon size is now handled by ButtonStyleManager
        self.title_settings_btn.setToolTip("Open settings")
        self.title_settings_btn.clicked.connect(self._on_settings_clicked)
        #self.title_settings_btn.setFixedSize(40, 40)
        self._style_title_button(self.title_settings_btn)
        title_layout.addWidget(self.title_settings_btn)
        
        # Chat/Browse button
        self.chat_btn = QToolButton()
        # Load chat icon (theme-specific)
        self._load_chat_icon()
        # Icon size is now handled by ButtonStyleManager
        self.chat_btn.setToolTip("Browse conversations")
        self.chat_btn.clicked.connect(self._on_chat_clicked)
        # Apply uniform button styling with proper padding
        logger.info("Applying uniform styling to chat button")
        self._style_title_button(self.chat_btn)
        title_layout.addWidget(self.chat_btn)
        
        # Attach (snap to avatar) toggle button
        self.attach_btn = QToolButton()
        # Load chain icon (theme-specific)
        self._load_chain_icon()
        # Icon size is now handled by ButtonStyleManager
        self.attach_btn.setToolTip("Attach REPL to avatar (toggle)")
        self.attach_btn.setCheckable(True)
        self._style_title_button(self.attach_btn)
        # Initialize from settings if available
        try:
            from ...infrastructure.storage.settings_manager import settings as _settings
            initial_attached = bool(_settings.get('interface.repl_attached', False))
            self.attach_btn.setChecked(initial_attached)
        except Exception:
            initial_attached = False
        # Style: theme-aware styling
        self._update_attach_button_state()
        self.attach_btn.clicked.connect(self._on_attach_toggle_clicked)
        title_layout.addWidget(self.attach_btn)
        
        # Upload/File context button (now toggles file browser bar)
        self.upload_btn = QToolButton()
        self.upload_btn.setToolTip("Toggle file browser (Ctrl+U)\nClick 'Upload Files' button inside to add files")
        
        # SET ICON DIRECTLY HERE - NO SEPARATE METHOD CALL
        try:
            icon_variant = self._get_icon_variant()
            filebar_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"filebar_{icon_variant}.png"
            )
            
            if os.path.exists(filebar_icon_path):
                filebar_icon = QIcon(filebar_icon_path)
                if not filebar_icon.isNull():
                    self.upload_btn.setIcon(filebar_icon)
                    from PyQt6.QtCore import QSize
                    self.upload_btn.setIconSize(QSize(16, 16))
                    logger.debug(f"Set filebar icon: filebar_{icon_variant}.png")
                else:
                    self.upload_btn.setText("📁")
            else:
                self.upload_btn.setText("📁")
        except Exception as e:
            logger.error(f"Failed to set filebar icon: {e}")
            self.upload_btn.setText("📁")
        
        self.upload_btn.clicked.connect(self._toggle_file_browser)
        # Apply uniform styling first
        self._style_title_button(self.upload_btn)
        # Style: theme-aware styling
        self._update_upload_button_state()
        title_layout.addWidget(self.upload_btn)
        
        # Search button
        self.search_btn = QToolButton()
        # Load search icon (theme-specific)
        self._load_search_icon()
        # Icon size is now handled by ButtonStyleManager
        self.search_btn.setToolTip("Search conversations (Ctrl+F)")
        self.search_btn.clicked.connect(self._toggle_search)
        # Apply uniform styling first
        self._style_title_button(self.search_btn)
        # Style: theme-aware styling
        self._update_search_button_state()
        title_layout.addWidget(self.search_btn)

        # Move/Resize arrow toggle button
        self.move_btn = QToolButton()
        self._load_move_icon(self.move_btn)
        self.move_btn.setToolTip("Toggle resize arrows")
        self.move_btn.setCheckable(True)  # Make it a toggle button
        self.move_btn.clicked.connect(self._on_move_toggle_clicked)
        self._style_title_button(self.move_btn)
        # Size constraints are now handled by _style_title_button CSS
        title_layout.addWidget(self.move_btn)
        
        # Always on top (pin) toggle button - FORCE ICON ONLY, NO EMOJI
        self.pin_btn = QToolButton()
        self.pin_btn.setToolTip("Toggle always stay on top")
        self.pin_btn.setCheckable(True)  # Make it a toggle button
        
        # IMMEDIATELY load icon BEFORE any other operations
        self._load_pin_icon_immediate()
        
        # Force icon-only mode (no text) AFTER icon is loaded
        self.pin_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        
        # ABSOLUTE PROTECTION: Never allow text content
        self.pin_btn.setText("")
        
        # Set initial state from settings
        try:
            always_on_top = settings.get('interface.always_on_top', True)
            self.pin_btn.setChecked(always_on_top)
        except Exception:
            self.pin_btn.setChecked(True)
        
        self.pin_btn.clicked.connect(self._on_pin_toggle_clicked)
        
        # Apply initial styling based on current state
        if self.pin_btn.isChecked():
            self._apply_pin_button_toggle_style(self.pin_btn)
            logger.debug("Applied initial pin button toggle styling")
        else:
            self._style_title_button(self.pin_btn)
            logger.debug("Applied initial normal pin button styling")
        
        # Final icon reload to ensure it sticks
        self._load_pin_icon_immediate()
        
        # FINAL PROTECTION: Clear any text that might have been set
        self.pin_btn.setText("")
        
        # OVERRIDE setText method to prevent emoji injection (no recursion)
        original_setText = self.pin_btn.setText
        self.pin_btn._original_setText = original_setText  # Store reference
        def protected_setText(text):
            if text:  # Only log if someone is trying to set actual text
                logger.debug(f"Pin button setText blocked: '{text}'")
            # Always ignore any text setting attempts - no icon reload to prevent recursion
            original_setText("")
        self.pin_btn.setText = protected_setText
        
        title_layout.addWidget(self.pin_btn)
        
        title_layout.addStretch()
        
        # Minimize button (uniform styling)
        minimize_btn = QPushButton("__")
        minimize_btn.clicked.connect(self.minimize_requested.emit)
        self._style_title_button(minimize_btn)
        title_layout.addWidget(minimize_btn)
        
        parent_layout.addWidget(self.title_frame)

    def _init_search_bar(self, parent_layout):
        """Initialize in-conversation search bar."""
        # Search bar frame (initially hidden) - ALWAYS fully opaque
        self.search_frame = QFrame()
        self.search_frame.setVisible(False)
        # Use theme-based styling or opaque fallback
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            from ...ui.themes.style_templates import StyleTemplates
            self.search_frame.setStyleSheet(StyleTemplates.get_search_frame_style(self.theme_manager.current_theme))
        else:
            self.search_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(40, 40, 40, 1.0);
                    border: none !important;
                    border-width: 0px !important;
                    border-style: none !important;
                    border-color: transparent !important;
                    outline: none !important;
                    border-radius: 4px;
                    margin: 2px;
                }}
                QFrame:focus {{
                    border: none !important;
                    outline: none !important;
                }}
            """)
        
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(6)
        
        # Search icon/label - apply theme colors and remove border comprehensively
        self.search_icon_label = QLabel("🔍")
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            self.search_icon_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors.text_primary};
                    background: transparent;
                    border: none !important;
                    border-width: 0px !important;
                    border-style: none !important;
                    border-color: transparent !important;
                    outline: none !important;
                    padding: 0px;
                    font-size: 14px;
                }}
            """)
        else:
            # Fallback styling with comprehensive border removal
            self.search_icon_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    background: transparent;
                    border: none !important;
                    border-width: 0px !important;
                    border-style: none !important;
                    border-color: transparent !important;
                    outline: none !important;
                    padding: 0px;
                    font-size: 14px;
                }
            """)
        search_layout.addWidget(self.search_icon_label)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in conversation...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._search_next)
        
        # COMPREHENSIVE BORDER REMOVAL - PyQt6 Expert Approach
        from PyQt6.QtCore import Qt
        
        # 1. PRIMARY: Disable Qt's native frame (most important)
        self.search_input.setFrame(False)
        
        # 2. Set focus policy to avoid focus ring artifacts
        self.search_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        # 3. Disable auto-fill background to prevent styling conflicts
        self.search_input.setAutoFillBackground(False)
        
        # 4. Ensure parent frame doesn't contribute borders
        if hasattr(self, 'search_frame'):
            self.search_frame.setFrameStyle(QFrame.Shape.NoFrame)
            self.search_frame.setLineWidth(0)
        
        search_layout.addWidget(self.search_input)
        
        # Regex checkbox
        self.regex_checkbox = QCheckBox(".*")
        self.regex_checkbox.setToolTip("Use regular expressions")
        self.regex_checkbox.setMinimumSize(35, 25)
        self.regex_checkbox.stateChanged.connect(self._on_regex_toggled)
        search_layout.addWidget(self.regex_checkbox)
        
        # Search navigation buttons (uniform styling)
        self.search_prev_btn = QPushButton("↑")
        self.search_prev_btn.setToolTip("Previous match")
        self.search_prev_btn.clicked.connect(self._search_previous)
        search_layout.addWidget(self.search_prev_btn)
        
        self.search_next_btn = QPushButton("↓")
        self.search_next_btn.setToolTip("Next match")
        self.search_next_btn.clicked.connect(self._search_next)
        search_layout.addWidget(self.search_next_btn)
        
        # Search results label with high-contrast styling
        self.search_status_label = QLabel("0/0")
        self.search_status_label.setMinimumWidth(40)
        # Use high-contrast styling for better visibility
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            from ...ui.themes.style_templates import StyleTemplates
            self.search_status_label.setStyleSheet(StyleTemplates.get_high_contrast_search_status_style(self.theme_manager.current_theme))
        else:
            # Fallback styling
            self.search_status_label.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: bold;")
        search_layout.addWidget(self.search_status_label)
        
        # Close search button (uniform styling)
        close_search_btn = QPushButton("✕")
        close_search_btn.setToolTip("Close search")
        close_search_btn.clicked.connect(self._close_search)
        search_layout.addWidget(close_search_btn)
        
        # Style search buttons using "icon" size for compactness
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        ButtonStyleManager.apply_unified_button_style(self.search_prev_btn, colors, "push", "icon")
        ButtonStyleManager.apply_unified_button_style(self.search_next_btn, colors, "push", "icon")
        ButtonStyleManager.apply_unified_button_style(close_search_btn, colors, "push", "icon")
        
        # Override with compact size constraints to ensure all buttons fit on one row  
        compact_size = QSize(24, 24)
        for btn in [self.search_prev_btn, self.search_next_btn, close_search_btn]:
            btn.setMinimumSize(compact_size)
            btn.setMaximumSize(compact_size)
            btn.resize(compact_size)
        
        # Apply additional CSS size constraints to ensure truly compact appearance
        compact_override = """
            QPushButton {
                min-width: 24px !important;
                max-width: 24px !important;
                min-height: 24px !important;
                max-height: 24px !important;
                width: 24px !important;
                height: 24px !important;
                margin: 0px;
                padding: 2px;
                font-size: 11px;
            }
        """
        # Apply the override after the main styling
        self.search_prev_btn.setStyleSheet(self.search_prev_btn.styleSheet() + compact_override)
        self.search_next_btn.setStyleSheet(self.search_next_btn.styleSheet() + compact_override)
        close_search_btn.setStyleSheet(close_search_btn.styleSheet() + compact_override)
        
        # Store close button reference for theme changes
        self._search_close_btn = close_search_btn
        
        # Style regex checkbox
        self.regex_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 2px;
                font-size: 10px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 2px;
                background-color: rgba(30, 30, 30, 0.8);
            }
        """)
        checkbox_style = self._get_search_checkbox_style()
        self.regex_checkbox.setStyleSheet(checkbox_style)
        
        # Search input styling with theme colors
        input_style = self._get_search_input_style()
        self.search_input.setStyleSheet(input_style)
        
        # Initialize search state
        self.current_search_matches = []
        self.current_search_index = -1
        self.current_search_query = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_conversation_search)
        self.search_debounce_ms = 300  # Faster debounce for in-conversation search
        
        parent_layout.addWidget(self.search_frame)
    
    def _reapply_search_button_sizing(self):
        """Re-apply compact size constraints to search buttons after theme changes."""
        try:
            if (hasattr(self, 'search_prev_btn') and hasattr(self, 'search_next_btn')):
                
                # Re-apply compact size constraints
                compact_size = QSize(24, 24)
                buttons_to_resize = [self.search_prev_btn, self.search_next_btn]
                if hasattr(self, '_search_close_btn') and self._search_close_btn:
                    buttons_to_resize.append(self._search_close_btn)
                
                for btn in buttons_to_resize:
                    btn.setMinimumSize(compact_size)
                    btn.setMaximumSize(compact_size)
                    btn.resize(compact_size)
                    
                    # Re-apply CSS override
                    compact_override = """
                        QPushButton {
                            min-width: 24px !important;
                            max-width: 24px !important;
                            min-height: 24px !important;
                            max-height: 24px !important;
                            width: 24px !important;
                            height: 24px !important;
                            margin: 0px;
                            padding: 2px;
                            font-size: 11px;
                        }
                    """
                    btn.setStyleSheet(btn.styleSheet() + compact_override)
                
                logger.debug("✓ Re-applied search button size constraints after theme change")
        except Exception as e:
            logger.warning(f"Failed to re-apply search button sizing: {e}")
    
    def _init_file_browser_bar(self, parent_layout):
        """Initialize file browser bar for file context management."""
        try:
            # Debug: Check Python path and file existence
            import sys
            import os
            logger.debug(f"Python path: {sys.path[:3]}...")  # Show first 3 paths
            
            # Try to import FileBrowserBar
            try:
                from ghostman.src.presentation.widgets.file_browser_bar import FileBrowserBar
                logger.debug("✅ FileBrowserBar imported successfully")
            except ImportError as e:
                logger.error(f"❌ FileBrowserBar import failed: {e}")
                
                # Check if file exists
                widget_dir = os.path.dirname(__file__)
                bar_path = os.path.join(widget_dir, "file_browser_bar.py")
                logger.debug(f"Looking for FileBrowserBar at: {bar_path}")
                logger.debug(f"File exists: {os.path.exists(bar_path)}")
                
                # Try alternative import approaches
                if os.path.exists(bar_path):
                    try:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("file_browser_bar", bar_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        FileBrowserBar = module.FileBrowserBar
                        logger.info("✅ FileBrowserBar loaded via importlib")
                    except Exception as load_e:
                        logger.error(f"❌ importlib load failed: {load_e}")
                        raise ImportError("Could not load FileBrowserBar") from e
                else:
                    raise ImportError("FileBrowserBar file not found") from e
            
            # Create FileBrowserBar with segfault prevention
            self.file_browser_bar = FileBrowserBar(theme_manager=getattr(self, 'theme_manager', None))
            self.file_browser_bar.setVisible(False)  # Initially hidden
            
            # Connect signals with error handling to prevent segfaults
            try:
                self.file_browser_bar.file_removed.connect(self._on_file_removed_safe)
                self.file_browser_bar.processing_completed.connect(self._on_file_processing_completed)
                self.file_browser_bar.clear_all_requested.connect(self._on_clear_all_files_safe)
                self.file_browser_bar.file_viewed.connect(self._on_file_viewed)
                self.file_browser_bar.file_toggled.connect(self._on_file_toggled)
                self.file_browser_bar.upload_files_requested.connect(self._on_upload_files_from_browser)
                logger.info("✅ FileBrowserBar signals connected safely")
            except Exception as signal_error:
                logger.error(f"⚠️ Failed to connect FileBrowserBar signals: {signal_error}")
            
            # Add to layout
            parent_layout.addWidget(self.file_browser_bar)
            logger.info("✅ File browser bar enabled with segfault prevention")

            # NOTE: File browser reference will be set in AI service after conversation_manager initializes
            # See _initialize_conversation_manager() which calls _set_file_browser_reference_in_ai_service()

        except Exception as e:
            logger.error(f"❌ Failed to initialize file browser bar: {e}")
            self.file_browser_bar = None
    
    def _connect_file_browser_signals(self, file_browser):
        """Connect signals for a file browser widget (used for per-tab file browsers)."""
        try:
            file_browser.file_removed.connect(self._on_file_removed_safe)
            file_browser.processing_completed.connect(self._on_file_processing_completed)
            file_browser.clear_all_requested.connect(self._on_clear_all_files_safe)
            file_browser.file_viewed.connect(self._on_file_viewed)
            file_browser.file_toggled.connect(self._on_file_toggled)
            file_browser.upload_files_requested.connect(self._on_upload_files_from_browser)
            logger.debug("Connected file browser signals")
        except Exception as e:
            logger.error(f"Failed to connect file browser signals: {e}")

    def _set_file_browser_reference_in_ai_service(self):
        """Set file browser reference in AI service for RAG query optimization."""
        logger.info("🔧 ATTEMPTING to set file browser reference in AI service...")
        try:
            if hasattr(self, 'conversation_manager') and self.conversation_manager:
                logger.info("  - conversation_manager: ✅ FOUND")
                ai_service = self.conversation_manager.get_ai_service()
                logger.info(f"  - ai_service: {'✅ FOUND' if ai_service else '❌ NONE'}")
                if ai_service and hasattr(ai_service, 'set_file_browser_reference'):
                    logger.info("  - set_file_browser_reference method: ✅ EXISTS")
                    if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                        logger.info("  - file_browser_bar: ✅ FOUND")
                        ai_service.set_file_browser_reference(self.file_browser_bar)
                        logger.info("✅✅✅ SUCCESSFULLY set file browser reference in AI service for RAG optimization ✅✅✅")
                    else:
                        logger.warning("  - file_browser_bar: ❌ NOT FOUND - cannot set reference")
                else:
                    logger.warning("  - set_file_browser_reference method: ❌ DOES NOT EXIST - AI service version mismatch")
            else:
                logger.warning("  - conversation_manager: ❌ NOT FOUND")
        except Exception as e:
            logger.error(f"❌ Failed to set file browser reference in AI service: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")

    def _on_file_removed_safe(self, file_id):
        """Safely handle file removal from browser bar with RAG cleanup."""
        try:
            logger.info(f"📄 File removed from browser: {file_id}")
            
            # Remove from RAG session if available
            removal_success = False
            if hasattr(self, 'rag_session') and self.rag_session:
                try:
                    # Check if using unified session (coordinator-based)
                    if self.rag_session == "unified_session":
                        # Get RAG coordinator and try to find integration service
                        try:
                            from ...infrastructure.rag_coordinator import get_rag_coordinator
                            rag_coordinator = get_rag_coordinator()
                            
                            if rag_coordinator and hasattr(rag_coordinator, 'enhanced_widgets'):
                                # Find the integration service for this widget
                                widget_id = f"repl_{id(self)}"
                                if widget_id in rag_coordinator.enhanced_widgets:
                                    enhancer = rag_coordinator.enhanced_widgets[widget_id]
                                    if hasattr(enhancer, 'integration_service'):
                                        integration_service = enhancer.integration_service
                                        removal_success = integration_service.remove_document(
                                            file_id, 
                                            conversation_id=getattr(self, '_current_conversation_id', None)
                                        )
                                        logger.info(f"🗑️ Removed {file_id} via coordinator: {removal_success}")
                        except Exception as coord_error:
                            logger.warning(f"Coordinator removal failed: {coord_error}")
                    
                    # Fallback: Try direct removal if RAG session has remove method
                    if not removal_success and hasattr(self.rag_session, 'remove_document'):
                        removal_success = self.rag_session.remove_document(file_id)
                        logger.info(f"🗑️ Removed {file_id} via direct session: {removal_success}")
                    
                    # Last resort: Try metadata-based removal
                    if not removal_success and hasattr(self.rag_session, 'remove_documents_by_metadata'):
                        removed_ids = self.rag_session.remove_documents_by_metadata({"file_id": file_id})
                        removal_success = bool(removed_ids)
                        logger.info(f"🗑️ Removed {file_id} via metadata: {removal_success}")
                        
                except Exception as rag_error:
                    logger.error(f"Failed to remove {file_id} from RAG: {rag_error}")
            
            # Update file tracking
            if hasattr(self, '_uploaded_files'):
                self._uploaded_files.discard(file_id)
            
            # Remove from database
            if hasattr(self, 'conversation_manager'):
                try:
                    conv_service = self.conversation_manager.conversation_service
                    if conv_service:
                        # Use thread-safe async pattern
                        from ...infrastructure.async_manager import run_async_task_safe
                        
                        def on_removal_complete(result, error):
                            if error:
                                logger.error(f"Failed to remove file from database: {error}")
                            else:
                                logger.info(f"✅ File removed from database: {file_id}")
                        
                        run_async_task_safe(
                            conv_service.remove_file_from_conversation(file_id),
                            callback=on_removal_complete,
                            timeout=10.0
                        )
                    else:
                        logger.warning("No conversation service available for file removal")
                        
                except Exception as db_error:
                    logger.error(f"Failed to remove file from database: {db_error}")
                    
            # Continue with UI removal regardless of database result
            
            # Remove from enabled files tracking
            if hasattr(self, '_enabled_files'):
                self._enabled_files.discard(file_id)
            
            # Remove from file path mapping
            if hasattr(self, '_file_id_to_path_map'):
                self._file_id_to_path_map.pop(file_id, None)
            
            # Log removal result
            if removal_success:
                logger.info(f"✅ Successfully removed {file_id} from RAG pipeline and tracking")
            else:
                logger.warning(f"⚠️ File {file_id} removed from UI but may still exist in RAG pipeline")
                
        except Exception as e:
            logger.error(f"Failed to handle file removal: {e}")

    def _on_clear_all_files_safe(self):
        """Safely handle clear all files request with RAG cleanup."""
        try:
            logger.info("📄 Clearing all files from context")
            
            # Clear from RAG session if available
            clear_success = False
            if hasattr(self, 'rag_session') and self.rag_session:
                try:
                    # Check if using unified session (coordinator-based)
                    if self.rag_session == "unified_session":
                        # Get RAG coordinator and try to clear via integration service
                        try:
                            from ...infrastructure.rag_coordinator import get_rag_coordinator
                            rag_coordinator = get_rag_coordinator()
                            
                            if rag_coordinator and hasattr(rag_coordinator, 'enhanced_widgets'):
                                # Find the integration service for this widget
                                widget_id = f"repl_{id(self)}"
                                if widget_id in rag_coordinator.enhanced_widgets:
                                    enhancer = rag_coordinator.enhanced_widgets[widget_id]
                                    if hasattr(enhancer, 'integration_service'):
                                        integration_service = enhancer.integration_service
                                        conv_id = getattr(self, '_current_conversation_id', None)
                                        if conv_id:
                                            integration_service.clear_conversation_context(conv_id)
                                            clear_success = True
                                            logger.info(f"🗑️ Cleared conversation context via coordinator")
                        except Exception as coord_error:
                            logger.warning(f"Coordinator clear failed: {coord_error}")
                    
                    # Fallback: Try direct clear if RAG session has clear method  
                    if not clear_success and hasattr(self.rag_session, 'clear_all_documents'):
                        self.rag_session.clear_all_documents()
                        clear_success = True
                        logger.info("🗑️ Cleared via direct session clear_all_documents")
                    
                    # Alternative: Clear by conversation if available
                    if not clear_success and hasattr(self.rag_session, 'clear_conversation_context'):
                        conv_id = getattr(self, '_current_conversation_id', None)
                        if conv_id:
                            self.rag_session.clear_conversation_context(conv_id)
                            clear_success = True
                            logger.info(f"🗑️ Cleared conversation {conv_id} via session")
                        
                except Exception as rag_error:
                    logger.error(f"Failed to clear RAG pipeline: {rag_error}")
            
            # Clear file tracking
            if hasattr(self, '_uploaded_files'):
                self._uploaded_files.clear()
                
            # Clear enabled files tracking
            if hasattr(self, '_enabled_files'):
                self._enabled_files.clear()

            # Clear files from browser bar UI (keeps header visible)
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                self.file_browser_bar.clear_all_files()

            # Log clear result
            if clear_success:
                logger.info("✅ Successfully cleared all files from RAG pipeline and tracking")
            else:
                logger.warning("⚠️ Files cleared from UI but may still exist in RAG pipeline")
                
        except Exception as e:
            logger.error(f"Failed to clear all files: {e}")
    
    def _on_file_viewed(self, file_id):
        """Handle file view request."""
        try:
            logger.info(f"📄 View requested for file: {file_id}")
            # TODO: Implement file content viewing
        except Exception as e:
            logger.error(f"Failed to handle file view: {e}")
    
    def _on_file_toggled(self, file_id, enabled):
        """Handle file context toggle (enable/disable for context inclusion)."""
        try:
            logger.info(f"📄 File {'enabled' if enabled else 'disabled'} for context: {file_id}")
            
            # Track enabled files for context retrieval immediately
            if not hasattr(self, '_enabled_files'):
                self._enabled_files = set()
            
            if enabled:
                self._enabled_files.add(file_id)
            else:
                self._enabled_files.discard(file_id)
                
            logger.info(f"📊 Total enabled files: {len(self._enabled_files)}")
            
            # Update database enabled state using async manager
            if hasattr(self, 'conversation_manager'):
                try:
                    conv_service = self.conversation_manager.conversation_service
                    if conv_service:
                        from ...infrastructure.async_manager import run_async_task_safe
                        
                        def on_toggle_complete(result, error):
                            if error:
                                logger.error(f"Failed to update file enabled state in database: {error}")
                                # Revert the local change if database update failed
                                if enabled:
                                    self._enabled_files.discard(file_id)
                                else:
                                    self._enabled_files.add(file_id)
                            elif result:
                                logger.info(f"✅ Updated file {file_id} enabled state in database")
                            else:
                                logger.warning(f"⚠️ Failed to update file {file_id} enabled state in database")
                                # Revert the local change if database update failed
                                if enabled:
                                    self._enabled_files.discard(file_id)
                                else:
                                    self._enabled_files.add(file_id)
                        
                        # Run the async operation safely
                        run_async_task_safe(
                            conv_service.toggle_file_enabled_status(file_id, enabled),
                            callback=on_toggle_complete,
                            timeout=10.0  # 10 second timeout
                        )
                        
                except Exception as db_error:
                    logger.error(f"Failed to schedule file enabled state update: {db_error}")
                    # Revert the local change
                    if enabled:
                        self._enabled_files.discard(file_id)
                    else:
                        self._enabled_files.add(file_id)
            
        except Exception as e:
            logger.error(f"Failed to handle file toggle: {e}")
    
    def _load_conversation_files(self, conversation_id: str):
        """Load and display files associated with a conversation."""
        try:
            logger.info(f"📁 Loading files for conversation: {conversation_id}")
            
            # First try to show existing files for this conversation
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                existing_files = self.file_browser_bar.get_files_for_conversation(conversation_id)
                if existing_files:
                    logger.info(f"📁 Found {len(existing_files)} existing files for conversation, showing them")
                    self.file_browser_bar.show_files_for_conversation(conversation_id)
                    return  # Files already exist, just show them
                else:
                    logger.info(f"📁 No existing files found for conversation, loading from database")
            
            # Update current conversation ID for file operations
            self._current_conversation_id = conversation_id
            
            # Update enabled files tracking
            if not hasattr(self, '_enabled_files'):
                self._enabled_files = set()
            self._enabled_files.clear()
            
            # Get conversation service
            if not hasattr(self, 'conversation_manager') or not self.conversation_manager:
                logger.warning("No conversation manager available for file loading")
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.setVisible(False)
                return
            
            conv_service = self.conversation_manager.conversation_service
            if not conv_service:
                logger.warning("No conversation service available for file loading")
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.setVisible(False)
                return
            
            # Load files from database using async manager
            from ...infrastructure.async_manager import run_async_task_safe
            
            def on_files_loaded(files, error):
                logger.info(f"🔍 DEBUG: on_files_loaded called - files={files}, error={error}")
                try:
                    if error:
                        logger.error(f"Failed to load conversation files: {error}")
                        if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                            self.file_browser_bar.setVisible(False)
                        return
                    
                    if files is None:
                        logger.warning("🔍 DEBUG: files is None")
                        files = []
                    
                    logger.info(f"🔍 DEBUG: Processing {len(files)} loaded files")
                    logger.info(f"🔍 DEBUG: Files data: {files}")
                    
                    # Use QTimer to ensure UI updates happen on main thread
                    from PyQt6.QtCore import QTimer
                    
                    def process_on_main_thread():
                        logger.info(f"🔍 DEBUG: Processing files on main thread")
                        self._process_loaded_files(files)
                    
                    # Schedule on main thread with single shot timer
                    QTimer.singleShot(0, process_on_main_thread)
                    
                except Exception as callback_error:
                    logger.error(f"🔍 DEBUG: Exception in on_files_loaded callback: {callback_error}")
                    import traceback
                    traceback.print_exc()
            
            # Run the async operation safely
            run_async_task_safe(
                conv_service.get_conversation_files(conversation_id),
                callback=on_files_loaded,
                timeout=15.0  # 15 second timeout
            )
            
            # Also schedule a fallback check in case async callback fails
            from PyQt6.QtCore import QTimer
            
            def fallback_check():
                logger.info(f"🔍 DEBUG: Fallback check - loading files directly for {conversation_id}")
                try:
                    # Try to get files synchronously as backup
                    import asyncio
                    if hasattr(asyncio, 'run'):
                        files = asyncio.run(conv_service.get_conversation_files(conversation_id))
                        logger.info(f"🔍 DEBUG: Fallback got {len(files) if files else 0} files")
                        if files:
                            self._process_loaded_files(files)
                    else:
                        logger.info(f"🔍 DEBUG: asyncio.run not available, skipping fallback")
                except Exception as fallback_error:
                    logger.error(f"🔍 DEBUG: Fallback loading failed: {fallback_error}")
            
            # Schedule fallback check after 2 seconds
            QTimer.singleShot(2000, fallback_check)
                
        except Exception as e:
            logger.error(f"Failed to load conversation files: {e}")
    
    def _process_loaded_files(self, files):
        """Process the loaded files and update the UI."""
        try:
            logger.info(f"🔍 DEBUG: _process_loaded_files called with {len(files) if files else 0} files")
            
            # Check if file browser bar exists
            if not hasattr(self, 'file_browser_bar'):
                logger.error("🔍 DEBUG: No file_browser_bar attribute!")
                return
            
            if not self.file_browser_bar:
                logger.error("🔍 DEBUG: file_browser_bar is None!")
                return
                
            logger.info(f"🔍 DEBUG: file_browser_bar exists and is valid")
            
            # RAG integration is now handled by FAISS-only system
            # No additional setup needed as FAISS uses conversation metadata directly
            
            # Add files to browser bar
            if files:
                logger.info(f"📄 Found {len(files)} files for conversation")
                
                for i, file_info in enumerate(files):
                    logger.info(f"🔍 DEBUG: Processing file {i+1}: {file_info}")
                    
                    try:
                        # Add file to browser bar with current status and conversation association
                        current_tab_id = None
                        if hasattr(self, 'tab_manager') and self.tab_manager:
                            active_tab = self.tab_manager.get_active_tab()
                            if active_tab:
                                current_tab_id = active_tab.tab_id
                        
                        self.file_browser_bar.add_file(
                            file_id=file_info['file_id'],
                            filename=file_info['filename'],
                            file_size=file_info.get('file_size', 0),
                            file_type=file_info.get('file_type', ''),
                            status=file_info['processing_status'],
                            conversation_id=conversation_id,
                            tab_id=current_tab_id
                        )
                        logger.info(f"🔍 DEBUG: Successfully added file {file_info['filename']} to browser bar (conversation: {conversation_id[:8] if conversation_id else 'None'}, tab: {current_tab_id})")
                        # Update enabled state
                        if file_info.get('is_enabled', True):
                            self._enabled_files.add(file_info['file_id'])
                        
                        # Update pill enabled state in browser bar
                        try:
                            self.file_browser_bar.set_file_enabled(
                                file_info['file_id'], 
                                file_info.get('is_enabled', True)
                            )
                        except AttributeError:
                            # Method doesn't exist yet, will be added
                            pass
                            
                    except Exception as add_error:
                        logger.error(f"🔍 DEBUG: Failed to add file to browser bar: {add_error}")
                        import traceback
                        traceback.print_exc()
                
                # Show browser bar if files exist
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.setVisible(True)
                logger.info(f"✅ Loaded {len(files)} files into browser bar")
            else:
                # Hide browser bar if no files
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.setVisible(False)
                logger.info("📁 No files found for conversation")
                
        except Exception as e:
            logger.error(f"Failed to process loaded files: {e}")
    
    def _init_rag_session(self):
        """Initialize the unified RAG session using SafeRAGSession (no segfaults)."""
        logger.info("🚀 Starting unified RAG session initialization")
        
        if self._rag_session_initializing:
            return
            
        try:
            # Check if already initialized
            if self.rag_session:
                logger.debug("RAG session already exists, skipping initialization")
                self._rag_session_ready = True
                return
                
            self.rag_session = None
            self._rag_session_ready = False
            self._rag_session_initializing = True
            
            # Get API configuration from settings ONLY (no environment variables)
            from ...infrastructure.storage.settings_manager import settings
            api_key = settings.get('ai_model.api_key')
            
            if not api_key:
                logger.warning("No API key configured in settings - RAG functionality will be limited")
            
            # Check if RAG coordinator is available and enabled
            try:
                from ...infrastructure.rag_coordinator import get_rag_coordinator
                rag_coordinator = get_rag_coordinator()
                
                if rag_coordinator and rag_coordinator.is_enabled():
                    # Use unified session through coordinator
                    self.rag_session = "unified_session"  # Placeholder indicating unified session
                    self._rag_session_ready = True
                    self._rag_session_initializing = False
                    logger.info("✅ Unified RAG session initialized through coordinator")
                    return
            except ImportError:
                logger.debug("RAG coordinator not available, using direct session")
            
            # Fallback: Create direct SafeRAGSession for this widget
            try:
                from ...infrastructure.rag_pipeline.threading.safe_rag_session import create_safe_rag_session
                
                logger.info("🔄 Creating direct SafeRAGSession (fallback)")
                self.rag_session = create_safe_rag_session()
                
                if self.rag_session and self.rag_session.is_ready:
                    self._rag_session_ready = True
                    logger.info("✅ Direct SafeRAGSession initialized successfully")
                else:
                    logger.error("SafeRAGSession not ready")
                    self.rag_session = None
                    self._rag_session_ready = False
                    
            except ImportError as import_error:
                logger.error(f"Could not import SafeRAGSession: {import_error}")
                self.rag_session = None
                self._rag_session_ready = False
            
            self._rag_session_initializing = False
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG session: {e}")
            self.rag_session = None
            self._rag_session_initializing = False
            self._rag_session_ready = False
    
    
    def _on_file_processing_started(self, file_id, filename):
        """Handle file processing started signal."""
        logger.info(f"📄 File processing started: {filename}")
        
        # Update conversation file association with processing status
        self._update_file_processing_status_async(file_id, 'processing', 0, {'filename': filename})
    
    def _on_file_processing_completed(self, file_id, status):
        """Handle file processing completed signal from FileBrowserBar.

        Args:
            file_id: The file ID
            status: Status string ("completed" or "failed")
        """
        logger.info(f"📁 File processing completed signal: {file_id[:8]} - {status}")

        if status == "completed":
            # File was successfully processed and added to FAISS
            # Refresh the RAG session so next query sees the new file
            logger.info("🔄 Refreshing RAG session to include newly processed file")

            if hasattr(self, 'rag_session') and self.rag_session:
                try:
                    # Get fresh stats to verify file was added
                    stats = self.rag_session.get_stats(timeout=2.0)
                    doc_count = stats.get('rag_pipeline', {}).get('documents_processed', 0)
                    logger.info(f"✅ RAG session refreshed - now has {doc_count} documents")
                except Exception as stats_err:
                    logger.debug(f"Could not get RAG stats: {stats_err}")
            else:
                logger.debug("No RAG session to refresh")

        elif status == "failed":
            logger.warning(f"⚠️ File processing failed for {file_id[:8]}")
    
    def _on_file_processing_failed(self, file_id, error_message):
        """Handle file processing failed signal."""
        logger.error(f"❌ File processing failed: {error_message}")
        
        # Update conversation file association with failed status
        self._update_file_processing_status_async(file_id, 'failed', 0, {'error': error_message})
    
    def _associate_file_with_current_tab_and_conversation(self, file_id: str, filename: str, result_data: dict = None):
        """Immediately associate file with current tab and conversation when processing completes."""
        try:
            # Get current tab and conversation
            current_tab_id = None
            current_conversation_id = None
            
            if hasattr(self, 'tab_manager') and self.tab_manager:
                active_tab = self.tab_manager.get_active_tab()
                if active_tab:
                    current_tab_id = active_tab.tab_id
                    current_conversation_id = getattr(active_tab, 'conversation_id', None)
            
            # Fallback to internal conversation tracking
            if not current_conversation_id:
                current_conversation_id = self._get_safe_conversation_id()
            
            logger.info(f"🔗 IMMEDIATE ASSOCIATION: {filename} → tab {current_tab_id}, conversation {current_conversation_id[:8] if current_conversation_id else 'None'}")

            # Add file to browser bar immediately with conversation association (tab is optional for avatar mode)
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar and current_conversation_id:
                try:
                    # Get file path from result data if available
                    file_path = result_data.get('file_path') if result_data else None
                    file_size = result_data.get('file_size', 0) if result_data else 0

                    # Add to browser bar with immediate association (tab_id can be None for avatar mode)
                    self.file_browser_bar.add_file(
                        file_id=file_id,
                        filename=filename,
                        file_path=file_path,
                        file_size=file_size,
                        conversation_id=current_conversation_id,
                        tab_id=current_tab_id  # Can be None for avatar window mode
                    )

                    # Make file browser visible immediately
                    self.file_browser_bar.setVisible(True)

                    tab_info = f"tab: {current_tab_id}" if current_tab_id else "avatar mode (no tab)"
                    logger.info(f"📄 IMMEDIATE: Added {filename} to browser bar ({tab_info}, conv: {current_conversation_id[:8]})")

                    # Force show files for current conversation
                    self.file_browser_bar.show_files_for_conversation(current_conversation_id)

                except Exception as browser_error:
                    logger.error(f"Failed to add file to browser bar immediately: {browser_error}")
            else:
                logger.warning(f"Cannot associate file immediately - missing conversation ({current_conversation_id}) or browser bar")
                
        except Exception as e:
            logger.error(f"Failed to associate file with tab and conversation: {e}")
    
    def _get_file_id_for_path_or_name(self, filename_or_path: str, fallback_id: str = None) -> str:
        """Get the correct file_id for a filename or path from our mapping."""
        import os
        # First try direct mapping lookup (path -> file_id)
        if hasattr(self, '_file_id_to_path_map'):
            for file_id, mapped_path in self._file_id_to_path_map.items():
                # Check if path matches exactly or basename matches
                if (mapped_path == filename_or_path or 
                    os.path.basename(mapped_path) == filename_or_path or
                    os.path.basename(mapped_path) == os.path.basename(filename_or_path)):
                    logger.info(f"🔍 Found file_id mapping: {filename_or_path} -> {file_id}")
                    return file_id
        
        # Fallback to provided file_id if available
        if fallback_id:
            logger.info(f"🔍 Using fallback file_id: {fallback_id}")
            return fallback_id
        
        # Final fallback to the filename/path itself
        logger.warning(f"🔍 No file_id mapping found, using filename: {filename_or_path}")
        return filename_or_path
    
    def _update_file_processing_status_async(self, file_id: str, status: str, chunk_count: int = 0, metadata: dict = None):
        """Update file processing status in conversation database asynchronously."""
        try:
            if not hasattr(self, 'conversation_manager') or not self.conversation_manager:
                logger.debug(f"No conversation manager available to update file {file_id} status")
                return
            
            conv_service = self.conversation_manager.conversation_service
            if not conv_service:
                logger.debug(f"No conversation service available to update file {file_id} status")
                return
            
            # Update status asynchronously using safe threading approach
            def update_status():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success = loop.run_until_complete(
                            conv_service.update_file_processing_status(
                                file_id=file_id,
                                status=status,
                                chunk_count=chunk_count,
                                metadata=metadata
                            )
                        )
                        if success:
                            logger.info(f"✅ Updated file {file_id} status to {status}")
                        else:
                            logger.warning(f"⚠ Failed to update file {file_id} status to {status}")
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"❌ Error updating file {file_id} status: {e}")
            
            # Run in background thread to avoid blocking UI
            import threading
            thread = threading.Thread(target=update_status, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"❌ Failed to start file status update for {file_id}: {e}")
    
    def _on_attach_toggle_clicked(self):
        """Emit attach toggle request with current state and update tooltip/icon."""
        attached = self.attach_btn.isChecked()
        logger.info(f"🔗 Attach button clicked - new state: {'attached' if attached else 'detached'}")
        
        # Update visual feedback
        if not self.attach_btn.icon().isNull():
            # Using icon - visual feedback is handled by styling
            pass
        else:
            # Using text fallback
            self.attach_btn.setText("⚲" if attached else "⚮")
        self.attach_btn.setToolTip("Attached to avatar" if attached else "Detached from avatar")
        
        # Update visual state
        self._update_attach_button_state()
        
        # Emit to parent window to handle positioning/persistence
        logger.info(f"🔗 Emitting attach_toggle_requested signal: {attached}")
        self.attach_toggle_requested.emit(attached)

    def set_attach_state(self, attached: bool):
        """Externally update the attach button state and visuals."""
        if hasattr(self, 'attach_btn'):
            self.attach_btn.setChecked(bool(attached))
            if self.attach_btn.icon().isNull():
                # Using text fallback
                self.attach_btn.setText("⚲" if attached else "⚮")
            self.attach_btn.setToolTip("Attached to avatar" if attached else "Detached from avatar")
            
            # Update visual state
            self._update_attach_button_state()
    
    def _on_upload_clicked(self):
        """Handle upload button click - open file dialog or show file browser."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            logger.info("📁 Upload button clicked")
            
            # Show file dialog
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select files to upload for context",
                "",
                "All supported files (*.txt *.py *.js *.json *.md *.csv *.html *.css *.xml *.yaml *.yml);;All files (*.*)"
            )
            
            if file_paths:
                logger.info(f"📁 Selected {len(file_paths)} files for upload")
                self._process_uploaded_files(file_paths)
            else:
                logger.debug("📁 No files selected")
                
        except Exception as e:
            logger.error(f"Failed to handle upload click: {e}")
    
    def _on_upload_files_from_browser(self):
        """Handle upload files request from file browser bar."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            logger.info("📁 Upload files requested from browser bar")
            
            # Show file dialog
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select files to upload for context",
                "",
                "All supported files (*.txt *.py *.js *.json *.md *.csv *.html *.css *.xml *.yaml *.yml);;All files (*.*)"
            )
            
            if file_paths:
                logger.info(f"📁 Selected {len(file_paths)} files for upload")
                self._process_uploaded_files(file_paths)
                # Keep file browser open after uploading files
                if hasattr(self, 'file_browser_bar') and not self.file_browser_bar.isVisible():
                    self.file_browser_bar.setVisible(True)
                    self._update_upload_button_state()
            else:
                logger.debug("📁 No files selected")
                
        except Exception as e:
            logger.error(f"Failed to handle upload files from browser: {e}")
    
    def _process_uploaded_files(self, file_paths):
        """Process the uploaded files for context with immediate embeddings processing."""
        try:
            # CRITICAL FIX: Always ensure we have a conversation before uploading files
            current_conversation_id = self._get_safe_conversation_id()
            if not current_conversation_id:
                logger.warning("⚠️ No current conversation found - creating conversation for file upload")
                # Create a conversation immediately to ensure files have proper association
                current_conversation_id = self._ensure_conversation_for_files()
                if not current_conversation_id:
                    logger.error("😱 Failed to create conversation for files - this will break file isolation!")
                    return  # Don't upload files without conversation
                
                # CRITICAL: Associate this conversation with the current tab immediately
                if hasattr(self, 'tab_manager') and self.tab_manager:
                    active_tab = self.tab_manager.get_active_tab()
                    if active_tab and not active_tab.conversation_id:
                        # Create conversation title from first uploaded file
                        import os
                        first_file = file_paths[0] if file_paths else "Untitled"
                        conversation_title = f"Files: {os.path.basename(first_file)}"
                        
                        # Associate tab with conversation
                        self.tab_manager.associate_conversation_with_tab(
                            active_tab.tab_id,
                            current_conversation_id,
                            conversation_title
                        )
                        logger.info(f"✅ Associated conversation {current_conversation_id[:8]} with tab {active_tab.tab_id}")
                
                # Set this as the current conversation and load it properly
                self._current_conversation_id = current_conversation_id
                
                # Load the actual conversation object if possible
                if hasattr(self, 'conversation_manager') and self.conversation_manager:
                    try:
                        import asyncio
                        
                        def get_conversation_sync():
                            try:
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    return new_loop.run_until_complete(
                                        self.conversation_manager.get_conversation(current_conversation_id)
                                    )
                                finally:
                                    new_loop.close()
                            except Exception as e:
                                logger.error(f"Error loading conversation object: {e}")
                                return None
                        
                        conversation_obj = get_conversation_sync()
                        if conversation_obj:
                            self.current_conversation = conversation_obj
                            logger.info(f"✅ Loaded conversation object for {current_conversation_id[:8]}")
                        
                    except Exception as e:
                        logger.warning(f"Could not load conversation object: {e}")
                
                logger.info(f"✅ Created and set conversation {current_conversation_id[:8]} for file upload")
            
            logger.info(f"📎 Linking files to conversation: {current_conversation_id[:8] if current_conversation_id else 'None'}...")

            # CRITICAL: Get active tab ID BEFORE processing files
            current_tab_id = None
            if hasattr(self, 'tab_manager') and self.tab_manager:
                active_tab = self.tab_manager.get_active_tab()
                if active_tab:
                    current_tab_id = active_tab.tab_id
                    logger.info(f"📁 Processing files for tab: {current_tab_id}")
                else:
                    logger.info("📁 No active tab - using avatar window mode (files will be conversation-scoped)")
            else:
                logger.debug("📁 No tab manager - using avatar window mode")

            # Show file browser bar immediately when files are selected
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                self.file_browser_bar.setVisible(True)
                logger.info("📄 File browser bar shown")
            else:
                logger.warning("📄 File browser bar not available")

            # Process each file and link to conversation
            for file_path in file_paths:
                import os
                from pathlib import Path
                from datetime import datetime
                
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                # Detect file type
                file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
                
                # Generate unique file_id for RAG pipeline
                path_obj = Path(file_path)
                timestamp = datetime.now().timestamp()
                file_id = f"file_{path_obj.stem}_{int(timestamp)}"
                
                # Save file association to database if we have a conversation
                if current_conversation_id and hasattr(self, 'conversation_manager'):
                    try:
                        conv_service = self.conversation_manager.conversation_service
                        if conv_service:
                            # Add file to conversation in database
                            import asyncio
                            
                            async def save_with_fallback():
                                # Check if conversation exists first
                                conversation = await conv_service.get_conversation(current_conversation_id)
                                active_conversation_id = current_conversation_id
                                
                                if not conversation:
                                    # EDGE CASE FIX: Handle conversation not found during file upload
                                    logger.warning(f"Conversation {current_conversation_id} not found during file upload")
                                    
                                    # Check if user deleted all conversations - create one if needed
                                    conversations = await conv_service.repository.list_conversations(
                                        limit=1,
                                        include_deleted=False
                                    )
                                    
                                    if len(conversations) == 0:
                                        logger.warning(f"⚠️ EDGE CASE: User has 0 conversations during file upload - creating new conversation")
                                        new_conversation_id = await conv_service.create_conversation("File Upload Chat")
                                        if new_conversation_id:
                                            active_conversation_id = new_conversation_id
                                            logger.info(f"✅ Created new conversation {active_conversation_id} for file upload (0 conversations case)")
                                            # Update current conversation reference
                                            if hasattr(self, 'conversation_manager') and self.conversation_manager.has_ai_service():
                                                ai_service = self.conversation_manager.get_ai_service()
                                                if ai_service:
                                                    ai_service.set_current_conversation(active_conversation_id)
                                            # Update our internal reference
                                            self._current_conversation_id = active_conversation_id
                                        else:
                                            logger.error("Failed to create new conversation for file upload (0 conversations case)")
                                            return False
                                    else:
                                        # TIMING FIX: Wait for startup conversation to be created (up to 2 seconds)
                                        logger.info(f"Found {len(conversations)} conversations, waiting for startup conversation")
                                        for attempt in range(20):  # Wait up to 2 seconds (20 * 0.1s)
                                            await asyncio.sleep(0.1)
                                            conversation = await conv_service.get_conversation(current_conversation_id)
                                            if conversation:
                                                logger.info(f"✅ Found startup conversation {current_conversation_id} on attempt {attempt + 1}")
                                                break
                                        
                                        if not conversation:
                                            logger.warning(f"Startup conversation still not ready after 2s, creating new one for file upload")
                                            # Create a new conversation for the file as fallback
                                            new_conversation_id = await conv_service.create_conversation("File Upload Chat")
                                            if new_conversation_id:
                                                active_conversation_id = new_conversation_id
                                                logger.info(f"Created fallback conversation {active_conversation_id} for file upload")
                                            # Update current conversation reference
                                            if hasattr(self, 'conversation_manager') and self.conversation_manager.has_ai_service():
                                                ai_service = self.conversation_manager.get_ai_service()
                                                if ai_service:
                                                    ai_service.set_current_conversation(active_conversation_id)
                                            # Update our internal reference
                                            self._current_conversation_id = active_conversation_id
                                        else:
                                            logger.error("Failed to create new conversation for file upload")
                                            return False
                                
                                # Now add the file to the conversation
                                return await conv_service.add_file_to_conversation(
                                    conversation_id=active_conversation_id,
                                    file_id=file_id,
                                    filename=filename,
                                    file_path=file_path,
                                    file_size=file_size,
                                    file_type=file_ext,
                                    metadata={'upload_timestamp': datetime.now().isoformat()}
                                )
                            
                            def save_file_sync():
                                try:
                                    # Check if we're in an event loop already (PyQt environment)
                                    try:
                                        loop = asyncio.get_running_loop()
                                        # We're in a running loop, so we need to use a thread
                                        import concurrent.futures
                                        import threading
                                        
                                        result_container = {'result': None, 'exception': None}
                                        event = threading.Event()
                                        
                                        def run_in_new_loop():
                                            try:
                                                new_loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(new_loop)
                                                try:
                                                    result = new_loop.run_until_complete(save_with_fallback())
                                                    result_container['result'] = result
                                                finally:
                                                    new_loop.close()
                                            except Exception as e:
                                                result_container['exception'] = e
                                            finally:
                                                event.set()
                                        
                                        thread = threading.Thread(target=run_in_new_loop, daemon=True)
                                        thread.start()
                                        # Wait for completion with timeout
                                        if event.wait(timeout=30.0):
                                            if result_container['exception']:
                                                raise result_container['exception']
                                            return result_container['result']
                                        else:
                                            logger.error("File save operation timed out")
                                            return False
                                            
                                    except RuntimeError:
                                        # No running loop, we can create one
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            return loop.run_until_complete(save_with_fallback())
                                        finally:
                                            loop.close()
                                
                                except Exception as e:
                                    logger.error(f"Error in save_file_sync: {e}")
                                    return False
                            
                            success = save_file_sync()
                            if success:
                                logger.info(f"✅ Saved file {filename} to conversation database")
                            else:
                                logger.warning(f"⚠️ Failed to save file {filename} to database")
                                
                    except Exception as db_error:
                        logger.error(f"Failed to save file to database: {db_error}")
                
                # Add to UI with generated file_id and conversation association
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    # Use the tab_id retrieved at the start of the method
                    # No need to retrieve again - already got it before the loop

                    self.file_browser_bar.add_file(
                        file_id=file_id,  # Use generated file_id as first parameter
                        filename=filename,
                        file_size=file_size,
                        file_type=file_ext,
                        status="queued",
                        conversation_id=current_conversation_id,
                        tab_id=current_tab_id  # ✅ ALWAYS PASSED - retrieved before loop
                    )
                    logger.info(f"📄 Added file to browser: {filename} (ID: {file_id}, conversation: {current_conversation_id[:8] if current_conversation_id else 'None'}, tab: {current_tab_id})")
                
                # Track uploaded files with file_id
                if not hasattr(self, '_uploaded_files'):
                    self._uploaded_files = set()
                self._uploaded_files.add(file_id)
                
                # Track enabled files (all files are enabled by default)
                if not hasattr(self, '_enabled_files'):
                    self._enabled_files = set()
                self._enabled_files.add(file_id)
                
                # Track file ID to path mapping for save functionality
                if not hasattr(self, '_file_id_to_path_map'):
                    self._file_id_to_path_map = {}
                self._file_id_to_path_map[file_id] = file_path
                
                # Start embeddings processing with file_id
                self._start_immediate_embeddings_processing(file_path, filename, file_id)
            
            logger.info(f"🚀 Started immediate processing for {len(file_paths)} files")
                    
        except Exception as e:
            logger.error(f"Failed to process uploaded files: {e}")
    
    def _ensure_conversation_for_files(self) -> Optional[str]:
        """Ensure there's a conversation for file uploads, creating one if needed."""
        try:
            # First try to get any existing conversation
            if hasattr(self, 'conversation_manager') and self.conversation_manager:
                if self.conversation_manager.has_ai_service():
                    ai_service = self.conversation_manager.get_ai_service()
                    if ai_service:
                        existing_id = ai_service.get_current_conversation_id()
                        if existing_id:
                            logger.info(f"🔗 Using existing conversation for files: {existing_id[:8]}...")
                            return existing_id
            
            # No existing conversation - create a pending one that will be "adopted" 
            # when user sends their first message
            if not hasattr(self, '_pending_conversation_id'):
                import uuid
                self._pending_conversation_id = str(uuid.uuid4())
                logger.info(f"🆕 Created new pending conversation for files: {self._pending_conversation_id[:8]}...")
            
            return self._pending_conversation_id
            
        except Exception as e:
            logger.error(f"Failed to ensure conversation for files: {e}")
            return None
    
    def _get_safe_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID - ALWAYS prefer tab-specific conversation."""
        # Method 1: Get from active tab (TAB-SPECIFIC - HIGHEST PRIORITY)
        if hasattr(self, 'tab_manager') and self.tab_manager:
            tab_conversation_id = self.tab_manager.get_active_conversation_id()
            if tab_conversation_id:
                logger.debug(f"🎯 Using tab-specific conversation: {tab_conversation_id[:8]}")
                return tab_conversation_id

        # Method 2: Direct reference (fallback for non-tab mode like avatar window)
        if hasattr(self, '_current_conversation_id') and self._current_conversation_id:
            logger.debug(f"📌 Using direct conversation reference: {self._current_conversation_id[:8]}")
            return self._current_conversation_id

        # Method 3: Current conversation object (legacy fallback)
        if hasattr(self, 'current_conversation') and self.current_conversation:
            logger.debug(f"📋 Using current_conversation object: {self.current_conversation.id[:8]}")
            self._current_conversation_id = self.current_conversation.id
            return self.current_conversation.id

        # Method 4: Create pending session ID for file isolation
        # This prevents context bleeding when files are uploaded before any conversation exists
        if not hasattr(self, '_pending_conversation_id'):
            # Create a temporary conversation ID that will be used for file uploads
            # This ID will be replaced when the user sends their first message and a real conversation is created
            import uuid
            self._pending_conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 Created pending conversation ID for file isolation: {self._pending_conversation_id[:8]}...")

        logger.debug(f"⏳ Using pending conversation: {self._pending_conversation_id[:8]}")
        return self._pending_conversation_id
    
    def _ensure_active_conversation_for_files(self) -> Optional[str]:
        """Ensure there's an active conversation for file uploads, creating one if needed."""
        try:
            if not hasattr(self, 'conversation_manager') or not self.conversation_manager:
                logger.error("No conversation manager available to create conversation")
                return None
            
            # Create a new conversation specifically for file uploads
            import asyncio
            loop = asyncio.new_event_loop() 
            asyncio.set_event_loop(loop)
            try:
                conv_service = self.conversation_manager.conversation_service
                new_conv_id = loop.run_until_complete(
                    conv_service.create_conversation(
                        title="New Conversation",
                        initial_message="Files uploaded to conversation."
                    )
                )
                
                if new_conv_id:
                    # Set as active conversation
                    success = self.conversation_manager.set_conversation_active_simple(new_conv_id)
                    if success:
                        # Update AI service context
                        if self.conversation_manager.has_ai_service():
                            ai_service = self.conversation_manager.get_ai_service()
                            if ai_service:
                                ai_service.set_current_conversation(new_conv_id)
                        
                        # Update our internal references
                        self._current_conversation_id = new_conv_id
                        
                        logger.info(f"✅ Created new conversation for file upload: {new_conv_id[:8]}...")
                        return new_conv_id
                    
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Failed to ensure active conversation for files: {e}")
        
        return None
    
    def _start_immediate_embeddings_processing(self, file_path: str, filename: str, file_id: str = None):
        """Start immediate embeddings processing for a single file."""
        try:
            logger.info(f"🔍 DEBUG: _start_immediate_embeddings_processing called for: {filename}")
            
            # Debug RAG session state
            logger.info(f"🔍 DEBUG: hasattr rag_session: {hasattr(self, 'rag_session')}")
            if hasattr(self, 'rag_session'):
                logger.info(f"🔍 DEBUG: rag_session is not None: {self.rag_session is not None}")
            logger.info(f"🔍 DEBUG: _rag_session_ready: {getattr(self, '_rag_session_ready', 'NOT_SET')}")
            logger.info(f"🔍 DEBUG: _rag_session_initializing: {getattr(self, '_rag_session_initializing', 'NOT_SET')}")
            
            # Ensure we have a valid and ready RAG session
            if not hasattr(self, 'rag_session') or not self.rag_session or not getattr(self, '_rag_session_ready', False):
                # Check if RAG session is currently initializing
                if hasattr(self, '_rag_session_initializing') and self._rag_session_initializing:
                    logger.info(f"⏳ RAG session is initializing - queuing {filename} for processing")
                    # Add to queue for processing after initialization
                    if hasattr(self, '_pending_files_queue'):
                        self._pending_files_queue.append((file_path, filename))
                        logger.info(f"📋 Added {filename} to queue (total queued: {len(self._pending_files_queue)})")
                    return
                
                logger.warning(f"❌ No RAG session - attempting to initialize for {filename}")
                # Try to reinitialize the session
                if hasattr(self, '_init_rag_session'):
                    logger.info(f"Attempting to reinitialize RAG session for {filename}")
                    self._init_rag_session()
                    # Add to queue since initialization is async
                    if hasattr(self, '_pending_files_queue'):
                        self._pending_files_queue.append((file_path, filename))
                        logger.info(f"📋 Added {filename} to queue after reinit attempt")
                    return
                
                logger.error(f"❌ Failed to initialize RAG session for {filename}")
                return
            # Ensure file is associated with current conversation before processing
            current_conv_id = self._get_safe_conversation_id()
            if not current_conv_id:
                logger.warning(f"No conversation found for file {filename} - creating isolated conversation")
                current_conv_id = self._ensure_conversation_for_files()
                if not current_conv_id:
                    logger.error(f"Failed to create conversation - file may be globally accessible")

            logger.debug(f"Processing file {filename} for conversation: {current_conv_id[:8] if current_conv_id else 'None'}...")

            # Store the file_id for later use in status updates
            self._current_processing_file_id = file_id
            self._display_processing_started_in_chat(filename)
            
            # Use thread-safe RAG processing (NO MORE SEGFAULTS!)
            from PyQt6.QtCore import QThread, QObject, pyqtSignal
            
            class SafeEmbeddingsProcessor(QObject):
                """Thread-safe embeddings processor using the ChromaDB worker thread."""
                finished = pyqtSignal(str, str, bool, dict)  # file_path, filename, success, result

                def __init__(self, rag_session, file_path, filename, conversation_id=None, parent_repl=None):
                    super().__init__()
                    self.rag_session = rag_session
                    self.file_path = file_path
                    self.filename = filename
                    self.conversation_id = conversation_id
                    self.parent_repl = parent_repl
                
                def process(self):
                    """Process file using thread-safe RAG session (no asyncio/threading issues)."""
                    try:
                        logger.debug(f"Processing embeddings for {self.filename}")

                        # Check if RAG session is available
                        if not self.rag_session:
                            logger.error(f"No RAG session available for {self.filename}")
                            self.finished.emit(self.file_path, self.filename, False, {
                                'tokens': 0,
                                'chunks': 0,
                                'file_id': self.filename,
                                'already_processed': False,
                                'error': 'No RAG session'
                            })
                            return

                        # Use the existing RAG session passed to the processor
                        try:
                            safe_rag = self.rag_session

                            if not safe_rag.is_ready:
                                logger.error(f"RAG session not ready for {self.filename}")
                                self.finished.emit(self.file_path, self.filename, False, {
                                    'tokens': 0,
                                    'chunks': 0,
                                    'file_id': self.filename,
                                    'already_processed': False,
                                    'error': 'Existing RAG session not ready'
                                })
                                return
                            
                            # Process document through thread-safe interface (NO ASYNCIO IN QT THREAD!)
                            logger.debug(f"Processing document: {self.filename}")

                            # Use conversation ID passed from parent during initialization
                            conversation_id = self.conversation_id
                            if conversation_id:
                                logger.debug(f"Using conversation ID: {conversation_id[:8]}...")
                            
                            # Prepare metadata with conversation association
                            metadata_override = {}

                            if conversation_id:
                                logger.debug(f"Associating document with conversation: {conversation_id[:8]}...")

                                # Store conversation ID for document association
                                metadata_override['pending_conversation_id'] = conversation_id

                                # Validate conversation exists in database
                                if hasattr(self.parent_repl, 'conversation_manager') and self.parent_repl.conversation_manager:
                                    conv_service = self.parent_repl.conversation_manager.conversation_service
                                    if conv_service:
                                        try:
                                            import asyncio
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            conversation = loop.run_until_complete(conv_service.get_conversation(conversation_id))
                                            if conversation:
                                                metadata_override['conversation_id'] = conversation_id
                                                logger.debug(f"Document associated with verified conversation: {conversation_id[:8]}...")
                                            else:
                                                logger.debug(f"Conversation {conversation_id[:8]}... pending - using pending association")
                                        except Exception as conv_check_error:
                                            logger.debug(f"Failed to verify conversation: {conv_check_error}")
                            else:
                                logger.warning("No conversation ID - document will be global")
                                metadata_override['storage_type'] = 'global_no_conversation'
                            
                            document_id = safe_rag.ingest_document(
                                file_path=self.file_path,
                                metadata_override=metadata_override,
                                timeout=120.0  # 2 minute timeout
                            )
                            
                            if document_id:
                                # Get stats safely
                                stats = safe_rag.get_stats(timeout=10.0) or {}
                                rag_stats = stats.get('rag_pipeline', {})
                                
                                # Estimate tokens from file content
                                try:
                                    with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        token_count = len(content.split())
                                except Exception as token_error:
                                    logger.debug(f"Token counting failed for {self.filename}: {token_error}")
                                    token_count = 100  # Default estimate

                                success_result = {
                                    'tokens': token_count,
                                    'chunks': rag_stats.get('chunks_created', 1),
                                    'file_id': self.filename,
                                    'already_processed': False,
                                    'document_id': document_id
                                }

                                if document_id.startswith("skipped_"):
                                    logger.warning(f"Document processing skipped: {document_id}")
                                    success_result['skipped'] = True
                                    success_result['skip_reason'] = 'API key issue'
                                else:
                                    logger.info(f"Successfully processed {self.filename} - {token_count} tokens")

                                self.finished.emit(self.file_path, self.filename, True, success_result)
                            else:
                                logger.error(f"Document ingestion failed for {self.filename}")
                                self.finished.emit(self.file_path, self.filename, False, {
                                    'tokens': 0,
                                    'chunks': 0,
                                    'file_id': self.filename,
                                    'already_processed': False,
                                    'error': 'Document ingestion returned None'
                                })
                            
                            # Don't close the shared session - it's managed by the parent widget
                            logger.info(f"✅ Document ingestion complete for {self.filename}, keeping shared session alive")
                            
                        except ImportError as import_error:
                            logger.error(f"❌ Failed to import safe RAG session: {import_error}")
                            self.finished.emit(self.file_path, self.filename, False, {
                                'tokens': 0,
                                'chunks': 0,
                                'file_id': self.filename,
                                'already_processed': False,
                                'error': f'Safe RAG import failed: {import_error}'
                            })
                        
                    except Exception as e:
                        logger.error(f"Embeddings processing error for {self.filename}: {e}")
                        import traceback
                        logger.debug(f"Full traceback: {traceback.format_exc()}")

                        # Report the failure properly
                        self.finished.emit(self.file_path, self.filename, False, {
                            'tokens': 0,
                            'chunks': 0,
                            'file_id': self.filename,
                            'already_processed': False,
                            'error': str(e)
                        })
            
            # Create and start SAFE thread (ChromaDB worker prevents segfaults)
            thread = QThread()
            processor = SafeEmbeddingsProcessor(
                self.rag_session,
                file_path,
                filename,
                conversation_id=current_conv_id,
                parent_repl=self
            )
            processor.moveToThread(thread)
            
            # Store thread reference to prevent early deletion
            if not hasattr(self, '_processing_threads'):
                self._processing_threads = []
            self._processing_threads.append((thread, processor))
            
            # Set up timeout mechanism (30 seconds max per file)
            from PyQt6.QtCore import QTimer
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda: self._handle_processing_timeout(file_path, filename, thread, processor))
            
            # Connect signals with proper cleanup
            thread.started.connect(processor.process)
            thread.started.connect(lambda: timeout_timer.start(30000))  # 30 second timeout
            processor.finished.connect(self._on_embeddings_complete)
            processor.finished.connect(timeout_timer.stop)
            processor.finished.connect(thread.quit)
            processor.finished.connect(processor.deleteLater)
            
            # Clean up thread reference when finished
            def cleanup_thread_ref():
                try:
                    timeout_timer.stop()
                    timeout_timer.deleteLater()
                    self._processing_threads = [(t, p) for t, p in self._processing_threads 
                                              if t != thread]
                    # Give thread time to finish naturally
                    if thread.isRunning():
                        thread.wait(2000)  # Wait up to 2 seconds
                    thread.deleteLater()
                except Exception as e:
                    logger.error(f"Error cleaning up thread reference: {e}")
            
            thread.finished.connect(cleanup_thread_ref)
            
            # Start the processing thread (re-enabled after fixing QPropertyAnimation issue)
            thread.start()
            logger.info(f"🧵 Started embeddings processing thread for {filename}")
            
        except Exception as e:
            logger.error(f"Failed to start embeddings processing for {filename}: {e}")
            # Update UI to failed status
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                file_id = self._get_file_id_for_path_or_name(file_path)
                self.file_browser_bar.update_file_status(file_id, "failed")
    
    def _on_embeddings_complete(self, file_path: str, filename: str, success: bool, result: dict):
        """Handle completion of embeddings processing."""
        try:
            if success:
                already_processed = result.get('already_processed', False)
                
                if already_processed:
                    logger.info(f"📋 File {filename} already processed - using existing embeddings")
                    status_message = f"📊 File {filename} already processed: {result.get('chunks', 0)} chunks, {result.get('tokens', 0)} tokens (existing)"
                else:
                    logger.info(f"🎉 Embeddings complete for {filename}")
                    status_message = f"📊 File {filename} processed: {result.get('chunks', 0)} chunks, {result.get('tokens', 0)} tokens (new)"
                
                # Display file processing status in chat instead of separate widget
                self._display_file_status_in_chat(filename, result, "completed")
                
                # IMMEDIATE ASSOCIATION: Associate file with current tab and conversation
                file_id = self._get_file_id_for_path_or_name(filename, result.get('file_id'))
                result_data = {
                    'file_path': file_path,
                    'file_size': result.get('file_size', 0),
                    'chunks': result.get('chunks', 0),
                    'tokens': result.get('tokens', 0)
                }
                self._associate_file_with_current_tab_and_conversation(file_id, filename, result_data)
                
                # Update file browser bar status to "completed"
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    try:
                        tokens_used = result.get('tokens', 0)
                        chunks = result.get('chunks', 0)
                        logger.info(f"🔍 Using file_id: {file_id} for filename: {filename}")
                        self.file_browser_bar.update_file_status(file_id, "completed")
                        self.file_browser_bar.update_file_usage(file_id, tokens_used, 1.0)  # Default relevance
                        logger.info(f"📄 Updated browser bar status to 'completed' for: {filename} (ID: {file_id})")
                    except Exception as bar_error:
                        logger.error(f"Failed to update browser bar status: {bar_error}")
                
                # Update conversation database with file processing completion
                self._update_file_processing_status_async(
                    file_id or filename, 
                    "completed",
                    result.get('chunks', 0),
                    {'tokens': result.get('tokens', 0), 'processed_at': datetime.now().isoformat()}
                )
                
                logger.info(status_message)
                logger.info("🔍 DEBUG: About to finish processing completion handler")
                
            else:
                # Import enhanced error handler
                try:
                    from ghostman.src.infrastructure.error_handling.enhanced_file_error_handler import get_enhanced_error_message
                    from pathlib import Path
                    file_path = Path(result.get('file_path', filename)) if result.get('file_path') else None
                    enhanced_error = get_enhanced_error_message(result, file_path)
                    logger.error(f"💥 Embeddings failed for {filename}: {enhanced_error}")
                except ImportError:
                    logger.error(f"💥 Embeddings failed for {filename}: {result.get('error', 'Unknown error')}")
                # Display file processing failure in chat instead of separate widget
                self._display_file_status_in_chat(filename, result, "failed")
                
                # Update file browser bar status to "failed"
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    try:
                        file_id = result.get('file_id', filename)
                        self.file_browser_bar.update_file_status(file_id, "failed")
                        logger.info(f"📄 Updated browser bar status to 'failed' for: {filename}")
                    except Exception as bar_error:
                        logger.error(f"Failed to update browser bar status: {bar_error}")
                
                # Update conversation database with file processing failure
                self._update_file_processing_status_async(
                    result.get('file_id', filename),
                    "failed",
                    0,
                    {'error': result.get('error', 'Unknown error'), 'failed_at': datetime.now().isoformat()}
                )
                
                logger.info("🔍 DEBUG: Finished handling failed processing")
                    
        except Exception as e:
            logger.error(f"Error handling embeddings completion: {e}")
            logger.error(f"🔍 DEBUG: Exception in embeddings completion handler: {e}")
        finally:
            logger.info("🔍 DEBUG: Exiting _on_embeddings_complete method")
    
    def _update_file_processing_status_async(self, file_id: str, status: str, chunk_count: int = 0, metadata: dict = None):
        """Update file processing status in conversation database using thread-safe async pattern."""
        try:
            if not hasattr(self, 'conversation_manager') or not self.conversation_manager:
                logger.debug(f"No conversation manager available for file status update: {file_id}")
                return
            
            conv_service = self.conversation_manager.conversation_service
            if not conv_service:
                logger.debug(f"No conversation service available for file status update: {file_id}")
                return
            
            # Use thread-safe async pattern like other database operations
            from ...infrastructure.async_manager import get_async_manager
            
            async_manager = get_async_manager()
            if async_manager:
                def on_update_complete(result, error):
                    if error:
                        logger.error(f"Failed to update file processing status for {file_id}: {error}")
                    else:
                        logger.info(f"✅ Updated file processing status: {file_id} -> {status}")
                
                # Update file processing status in database  
                from ...infrastructure.async_manager import run_async_task_safe
                run_async_task_safe(
                    conv_service.update_file_processing_status(file_id, status, chunk_count, metadata),
                    callback=on_update_complete,
                    timeout=10.0
                )
            else:
                logger.warning(f"No async manager available for file status update: {file_id}")
                
        except Exception as e:
            logger.error(f"Failed to schedule file processing status update for {file_id}: {e}")
    
    def _schedule_ui_update(self, file_path: str, result: dict, status: str):
        """Schedule UI updates to run in the main thread using QTimer."""
        try:
            from PyQt6.QtCore import QTimer
            
            logger.info("🔍 DEBUG: Creating QTimer for UI update")
            
            def perform_ui_update():
                """Perform the actual UI update in the main thread."""
                try:
                    logger.info("🔍 DEBUG: Executing deferred UI update")
                    
                    # Check if file browser bar is still available
                    if (hasattr(self, 'file_browser_bar') and 
                        self.file_browser_bar and 
                        not hasattr(self.file_browser_bar, '__deleted__')):
                        
                        logger.info(f"🔍 DEBUG: Updating file browser bar status to {status}")
                        
                        # Update status
                        if hasattr(self.file_browser_bar, 'update_file_status'):
                            file_id = self._get_file_id_for_path_or_name(file_path)
                            self.file_browser_bar.update_file_status(file_id, status)
                            logger.info("🔍 DEBUG: Status updated successfully")
                        
                        # Update usage info if successful and tokens available
                        if (status == "completed" and 'tokens' in result and 
                            hasattr(self.file_browser_bar, 'update_file_usage')):
                            self.file_browser_bar.update_file_usage(
                                file_path, 
                                result['tokens'], 
                                1.0  # Full relevance since it's processed/available
                            )
                            logger.info("🔍 DEBUG: Usage info updated successfully")
                    else:
                        logger.info("🔍 DEBUG: File browser bar not available for deferred update")
                        
                    logger.info("🔍 DEBUG: Deferred UI update completed")
                    
                except Exception as ui_error:
                    logger.error(f"🔍 DEBUG: Error in deferred UI update: {ui_error}")
                    import traceback
                    traceback.print_exc()
            
            # Schedule the update to run in the next event loop cycle
            QTimer.singleShot(0, perform_ui_update)
            logger.info("🔍 DEBUG: UI update scheduled successfully")
            
        except Exception as e:
            logger.error(f"🔍 DEBUG: Error scheduling UI update: {e}")
            import traceback
            traceback.print_exc()
    
    def _display_file_status_in_chat(self, filename: str, result: dict, status: str):
        """Display file processing status directly in the chat conversation using stable MixedContentDisplay."""
        try:
            logger.info(f"🔍 DEBUG: _display_file_status_in_chat called for: {filename}, status: {status}")
            logger.info(f"🔍 DEBUG: Result data: {result}")
            
            # Create appropriate status message based on result
            if status == "completed":
                # Check if processing was successful - either explicit success flag or presence of processing data
                has_success_flag = result.get('success', False)
                has_processing_data = 'tokens' in result and 'chunks' in result
                is_successful = has_success_flag or has_processing_data
                
                if is_successful:
                    chunks = result.get('chunks', 0)
                    tokens = result.get('tokens', 0)
                    already_processed = result.get('already_processed', False)
                    
                    if already_processed:
                        status_icon = "📋"
                        status_text = f"File <strong>{filename}</strong> was already processed"
                        detail_text = f"Using existing: {chunks} chunks, {tokens} tokens"
                        style = "info"
                    else:
                        status_icon = "✅"
                        status_text = f"File <strong>{filename}</strong> processed successfully"
                        detail_text = f"Created: {chunks} chunks, {tokens} tokens"
                        style = "info"

                    # Only show success messages in debug mode
                    if self._is_debug_mode_enabled():
                        # Create HTML message with consistent styling
                        message_html = f"""
                        <div style="background-color: rgba(34, 139, 34, 0.1); border-left: 3px solid #228B22; padding: 8px; margin: 4px 0; border-radius: 4px;">
                            <div style="font-weight: bold; color: #228B22;">{status_icon} {status_text}</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{detail_text}</div>
                        </div>
                        """
                else:
                    # Handle the case where success is False but status is completed
                    # Use enhanced error handler for better error messages
                    try:
                        from ghostman.src.infrastructure.error_handling.enhanced_file_error_handler import get_enhanced_error_message
                        from pathlib import Path
                        file_path = Path(result.get('file_path', filename)) if result.get('file_path') else None
                        error_msg = get_enhanced_error_message(result, file_path)
                    except ImportError:
                        error_msg = result.get('error', 'Unknown error')
                    message_html = f"""
                    <div style="background-color: rgba(220, 20, 60, 0.1); border-left: 3px solid #DC143C; padding: 8px; margin: 4px 0; border-radius: 4px;">
                        <div style="font-weight: bold; color: #DC143C;">❌ File <strong>{filename}</strong> processing failed</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">Error: {error_msg}</div>
                    </div>
                    """
                    style = "error"
            
            elif status == "failed":
                # Use enhanced error handler for better error messages
                try:
                    from ghostman.src.infrastructure.error_handling.enhanced_file_error_handler import get_enhanced_error_message
                    from pathlib import Path
                    file_path = Path(result.get('file_path', filename)) if result.get('file_path') else None
                    error_msg = get_enhanced_error_message(result, file_path)
                except ImportError:
                    error_msg = result.get('error', 'Unknown error')
                message_html = f"""
                <div style="background-color: rgba(220, 20, 60, 0.1); border-left: 3px solid #DC143C; padding: 8px; margin: 4px 0; border-radius: 4px;">
                    <div style="font-weight: bold; color: #DC143C;">❌ File <strong>{filename}</strong> processing failed</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 2px;">Error: {error_msg}</div>
                </div>
                """
                style = "error"
            
            else:
                # Fallback for unknown status
                message_html = f"""
                <div style="background-color: rgba(255, 165, 0, 0.1); border-left: 3px solid #FFA500; padding: 8px; margin: 4px 0; border-radius: 4px;">
                    <div style="font-weight: bold; color: #FFA500;">ℹ️ File <strong>{filename}</strong> status: {status}</div>
                </div>
                """
                style = "info"
            
            logger.info(f"🔍 DEBUG: Created message HTML for {filename}, about to check output_display")
            logger.info(f"🔍 DEBUG: hasattr output_display: {hasattr(self, 'output_display')}")

            # Only display file processing status in debug mode
            if self._is_debug_mode_enabled():
                # Add the message to chat using the proven stable MixedContentDisplay
                if hasattr(self, 'output_display') and self.output_display:
                    logger.info(f"🔍 DEBUG: About to add HTML content to chat for file status: {filename} - {status}")
                    self.output_display.add_html_content(message_html, style)
                    logger.info(f"📢 File status displayed in chat: {filename} - {status}")
                else:
                    logger.warning(f"❌ MixedContentDisplay not available for file status - hasattr: {hasattr(self, 'output_display')}")
                    if hasattr(self, 'output_display'):
                        logger.warning(f"❌ output_display is None: {self.output_display is None}")
                
        except Exception as e:
            logger.error(f"Error displaying file status in chat: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Fallback: at least log the status
            logger.info(f"File {filename} {status}: {result}")
    
    def _display_processing_started_in_chat(self, filename: str):
        """Display file processing started message in chat."""
        try:
            logger.info(f"🔍 DEBUG: _display_processing_started_in_chat called for: {filename}")
            
            # Check if MixedContentDisplay is available
            logger.info(f"🔍 DEBUG: hasattr output_display: {hasattr(self, 'output_display')}")
            if hasattr(self, 'mixed_content_display'):
                logger.info(f"🔍 DEBUG: output_display is not None: {self.output_display is not None}")
            
            # Only show processing messages in debug mode
            if self._is_debug_mode_enabled():
                message_html = f"""
                <div style="background-color: rgba(30, 144, 255, 0.1); border-left: 3px solid #1E90FF; padding: 8px; margin: 4px 0; border-radius: 4px;">
                    <div style="font-weight: bold; color: #1E90FF;">🔄 Processing file <strong>{filename}</strong>...</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 2px;">Creating embeddings for file context</div>
                </div>
                """

                if hasattr(self, 'output_display') and self.output_display:
                    logger.info(f"🔍 DEBUG: About to add HTML content to chat for: {filename}")
                    self.output_display.add_html_content(message_html, "info")
                    logger.info(f"📢 Processing started message displayed in chat: {filename}")
            else:
                logger.warning(f"❌ MixedContentDisplay not available for processing status - hasattr: {hasattr(self, 'output_display')}")
                if hasattr(self, 'output_display'):
                    logger.warning(f"❌ output_display is None: {self.output_display is None}")
            
            # Update file browser bar status to "processing"
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                try:
                    # Use the file_id passed from the calling function
                    file_id = getattr(self, '_current_processing_file_id', filename)
                    self.file_browser_bar.update_file_status(file_id, "processing")
                    logger.info(f"📄 Updated browser bar status to 'processing' for: {filename} (ID: {file_id})")
                except Exception as bar_error:
                    logger.error(f"Failed to update browser bar status: {bar_error}")
                
        except Exception as e:
            logger.error(f"Error displaying processing start in chat: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def _schedule_safe_ui_update(self, file_path: str, result: dict, status: str):
        """Schedule SAFE UI updates that skip the problematic update_file_usage method."""
        try:
            from PyQt6.QtCore import QTimer
            
            logger.info("🔍 DEBUG: Creating QTimer for SAFE UI update")
            
            def perform_safe_ui_update():
                """Perform only SAFE UI updates (status only, no usage)."""
                try:
                    logger.info("🔍 DEBUG: Executing SAFE deferred UI update")
                    
                    # Check if file browser bar is still available
                    if (hasattr(self, 'file_browser_bar') and 
                        self.file_browser_bar and 
                        not hasattr(self.file_browser_bar, '__deleted__')):
                        
                        logger.info(f"🔍 DEBUG: Updating file browser bar status to {status}")
                        
                        # SAFE: Update status only (this method works correctly)
                        if hasattr(self.file_browser_bar, 'update_file_status'):
                            file_id = self._get_file_id_for_path_or_name(file_path)
                            self.file_browser_bar.update_file_status(file_id, status)
                            logger.info("🔍 DEBUG: Status updated successfully")
                        
                        # SKIP: update_file_usage is the method causing segmentation faults
                        # Do not call self.file_browser_bar.update_file_usage() - it causes crashes
                        logger.info("🔍 DEBUG: Skipping usage update (causes segfaults)")
                    else:
                        logger.info("🔍 DEBUG: File browser bar not available for safe deferred update")
                        
                    logger.info("🔍 DEBUG: Safe deferred UI update completed")
                    
                except Exception as ui_error:
                    logger.error(f"🔍 DEBUG: Error in safe deferred UI update: {ui_error}")
                    import traceback
                    traceback.print_exc()
            
            # Schedule the safe update to run in the next event loop cycle
            QTimer.singleShot(0, perform_safe_ui_update)
            logger.info("🔍 DEBUG: Safe UI update scheduled successfully")
            
        except Exception as e:
            logger.error(f"🔍 DEBUG: Error scheduling safe UI update: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_processing_timeout(self, file_path: str, filename: str, thread, processor):
        """Handle processing timeout for a file."""
        try:
            logger.warning(f"⏰ Processing timeout for {filename} (30s)")
            
            # Force stop the thread
            if thread.isRunning():
                thread.quit()
                if not thread.wait(2000):  # Wait 2 more seconds
                    thread.terminate()
                    logger.warning(f"🚫 Force terminated thread for {filename}")
            
            # Update UI to failed status
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                file_id = self._get_file_id_for_path_or_name(file_path)
                self.file_browser_bar.update_file_status(file_id, "failed")
                
            logger.error(f"💥 Processing timeout for {filename} after 30 seconds")
            
        except Exception as e:
            logger.error(f"Error handling processing timeout: {e}")
    
    def _start_async_processing(self, file_paths):
        """Start async processing using QThread."""
        try:
            from PyQt6.QtCore import QThread, QObject, pyqtSignal
            
            class FileProcessor(QObject):
                finished = pyqtSignal()
                progress = pyqtSignal(str, str, str)  # file_path, filename, status
                
                def __init__(self, service, file_paths):
                    super().__init__()
                    self.service = service  
                    self.file_paths = file_paths
                
                def process(self):
                    import asyncio
                    asyncio.run(self._process_files())
                
                async def _process_files(self):
                    try:
                        if hasattr(self.service, 'initialize'):
                            await self.service.initialize()
                        
                        for file_path in self.file_paths:
                            try:
                                import os
                                filename = os.path.basename(file_path)
                                
                                self.progress.emit(file_path, filename, "processing")
                                result = await self.service.process_file(file_path)
                                
                                if result.success:
                                    self.progress.emit(file_path, filename, "completed")
                                else:
                                    self.progress.emit(file_path, filename, "failed")
                                    
                            except Exception as e:
                                logger.error(f"Error processing {file_path}: {e}")
                                self.progress.emit(file_path, filename, "failed")
                        
                        self.finished.emit()
                    except Exception as e:
                        logger.error(f"Error in async processing: {e}")
                        self.finished.emit()
            
            # Create and start processing thread
            self.processing_thread = QThread()
            self.file_processor = FileProcessor(self.rag_session, file_paths)
            self.file_processor.moveToThread(self.processing_thread)
            
            # Connect signals
            self.processing_thread.started.connect(self.file_processor.process)
            self.file_processor.progress.connect(self._on_file_progress)
            self.file_processor.finished.connect(self.processing_thread.quit)
            self.file_processor.finished.connect(self.file_processor.deleteLater)
            self.processing_thread.finished.connect(self.processing_thread.deleteLater)
            
            # Start processing
            self.processing_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start async processing: {e}")
            # Fallback
            self._process_files_sync(file_paths)
    
    def _on_file_progress(self, file_path, filename, status):
        """Handle file processing progress updates."""
        try:
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                # Use correct file_id instead of file_path
                file_id = self._get_file_id_for_path_or_name(file_path)
                self.file_browser_bar.update_file_status(file_id, status)
                logger.info(f"📄 Updated {filename} status: {status} (ID: {file_id})")
        except Exception as e:
            logger.error(f"Failed to update file progress: {e}")
    
    async def _process_files_async(self, file_paths):
        """Asynchronously process files using file context service."""
        try:
            if not self.rag_session:
                logger.warning("RAG session not available")
                return
            
            # Initialize service if not already done
            if hasattr(self.rag_session, 'initialize'):
                await self.rag_session.initialize()
            
            # Process each file
            for file_path in file_paths:
                try:
                    import os
                    filename = os.path.basename(file_path)

                    # Get current conversation ID for document association FIRST
                    conversation_id = None
                    if hasattr(self, 'current_conversation') and self.current_conversation:
                        conversation_id = self.current_conversation.id
                    elif hasattr(self, 'conversation_manager') and self.conversation_manager:
                        if self.conversation_manager.has_ai_service():
                            ai_service = self.conversation_manager.get_ai_service()
                            if ai_service:
                                conversation_id = ai_service.get_current_conversation_id()
                    
                    # CRITICAL FIX: Use _get_safe_conversation_id as fallback for drag/drop files too
                    print(f"🔍 DRAG DEBUG: conversation_id before fallback: {conversation_id}")
                    logger.info(f"🔍 DRAG DEBUG: conversation_id before fallback: {conversation_id}")
                    if not conversation_id:
                        conversation_id = self._get_safe_conversation_id()
                        print(f"🔍 DRAG DEBUG: conversation_id after fallback: {conversation_id}")
                        logger.info(f"🔍 DRAG DEBUG: conversation_id after fallback: {conversation_id}")
                        if conversation_id:
                            logger.info(f"🔄 Using fallback conversation ID for drag/drop from _get_safe_conversation_id: {conversation_id[:8]}...")

                    # Add to browser bar with processing status and PROPER TAB ASSOCIATION
                    # Now that we have conversation_id, we can add the file
                    if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                        # CRITICAL: Get current tab ID for association
                        current_tab_id = None
                        if hasattr(self, 'tab_manager') and self.tab_manager:
                            active_tab = self.tab_manager.get_active_tab()
                            if active_tab:
                                current_tab_id = active_tab.tab_id
                                logger.info(f"🔍 ASYNC PROCESSING: Using tab {current_tab_id} for {filename}")
                            else:
                                logger.error(f"❌ ASYNC PROCESSING: No active tab for {filename} - will break file association!")

                        self.file_browser_bar.add_file(
                            file_id=file_path,  # Using file_path as file_id for now
                            filename=filename,
                            status="processing",
                            conversation_id=conversation_id,
                            tab_id=current_tab_id
                        )
                        logger.info(f"📄 Added to browser: {filename} (conversation: {conversation_id[:8] if conversation_id else 'None'}, tab: {current_tab_id})")

                    logger.info(f"📄 Processing file with embeddings: {filename}")

                    # Prepare metadata with conversation association
                    metadata_override = {}
                    
                    # FIXED: Enhanced conversation association logic with better fallbacks (drag/drop version)
                    if conversation_id:
                        logger.info(f"🔗 Attempting to associate drag/drop document with conversation: {conversation_id[:8]}...")
                        
                        # Always store pending_conversation_id as primary association method
                        metadata_override['pending_conversation_id'] = conversation_id
                        logger.info(f"🔗 Drag/drop document stored with pending_conversation_id: {conversation_id[:8]}...")
                        
                        # Validate conversation exists in database and add formal association if found
                        if hasattr(self, 'conversation_manager') and self.conversation_manager:
                            conv_service = self.conversation_manager.conversation_service
                            if conv_service:
                                try:
                                    import asyncio
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    conversation = loop.run_until_complete(conv_service.get_conversation(conversation_id))
                                    if conversation:
                                        metadata_override['conversation_id'] = conversation_id
                                        logger.info(f"✅ Drag/drop document also associated with verified conversation: {conversation_id[:8]}...")
                                    else:
                                        logger.info(f"🕰️ Conversation {conversation_id[:8]}... not yet in database - using pending association")
                                except Exception as conv_check_error:
                                    logger.warning(f"⚠️ Failed to verify conversation {conversation_id[:8]}...: {conv_check_error}")
                            else:
                                logger.info("🕰️ No conversation service - using pending association")
                        else:
                            logger.info("🕰️ No conversation manager - using pending association")
                    else:
                        logger.warning("⚠️ No current conversation ID found - drag/drop document will be truly global")
                        # Add a marker to help identify truly global vs pending files
                        metadata_override['storage_type'] = 'global_no_conversation'
                    
                    # Process file with RAG pipeline
                    success = await self.rag_session.ingest_document(file_path, metadata_override)
                    
                    # Update browser bar based on result
                    if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                        file_id = self._get_file_id_for_path_or_name(file_path)
                        if success:
                            self.file_browser_bar.update_file_status(file_id, "completed")
                            logger.info(f"✅ Successfully processed: {filename}")
                        else:
                            self.file_browser_bar.update_file_status(file_id, "failed")
                            logger.error(f"❌ Failed to process: {filename} - {result.error_message}")
                            
                except Exception as file_error:
                    logger.error(f"Error processing file {file_path}: {file_error}")
                    if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                        self.file_browser_bar.update_file_status(file_path, "failed")
        
        except Exception as e:
            logger.error(f"Error in async file processing: {e}")
    
    def _process_files_sync(self, file_paths):
        """Synchronously process files (fallback)."""
        try:
            for file_path in file_paths:
                import os
                filename = os.path.basename(file_path)
                
                # Add to browser bar with PROPER TAB ASSOCIATION
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    # CRITICAL: Get current tab ID for association
                    current_tab_id = None
                    current_conversation_id = getattr(self, '_current_conversation_id', None)
                    
                    if hasattr(self, 'tab_manager') and self.tab_manager:
                        active_tab = self.tab_manager.get_active_tab()
                        if active_tab:
                            current_tab_id = active_tab.tab_id
                            logger.info(f"🔍 SYNC PROCESSING: Using tab {current_tab_id} for {filename}")
                            print(f"🔍 SYNC PROCESSING: Using tab {current_tab_id} for {filename}")
                        else:
                            logger.error(f"❌ SYNC PROCESSING: No active tab for {filename} - will break file association!")
                            print(f"❌ SYNC PROCESSING: No active tab for {filename} - will break file association!")
                    
                    self.file_browser_bar.add_file(
                        file_id=file_path,  # Using file_path as file_id for now 
                        filename=filename, 
                        status="pending",
                        conversation_id=current_conversation_id,
                        tab_id=current_tab_id
                    )
                    logger.info(f"📄 Added to context (sync): {filename} with tab {current_tab_id}")
                    
        except Exception as e:
            logger.error(f"Error in sync file processing: {e}")
    
    def _init_conversation_toolbar(self, parent_layout):
        """Initialize conversation management toolbar."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # New conversation button with menu
        self.toolbar_new_conv_btn = QToolButton()
        # Load plus icon (theme-specific)
        self._load_plus_icon(self.toolbar_new_conv_btn)
        # Icon size is now handled by ButtonStyleManager
        self.toolbar_new_conv_btn.setToolTip("Start new conversation")
        # Don't set popup mode - we'll handle the menu manually
        self.toolbar_new_conv_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toolbar_new_conv_btn.clicked.connect(self._show_toolbar_new_conv_menu)
        
        # Create menu for new conversation options FIRST
        new_conv_menu = QMenu(self.toolbar_new_conv_btn)
        
        # Add New Tab option if tab system is available
        if TAB_SYSTEM_AVAILABLE and hasattr(self, 'tab_manager') and self.tab_manager:
            new_tab_action = QAction("New Tab", self.toolbar_new_conv_btn)
            new_tab_action.setIcon(self._load_themed_icon("new_tab"))
            new_tab_action.triggered.connect(self._create_new_tab)
            new_conv_menu.addAction(new_tab_action)
        
        # New conversation action
        new_action = QAction("New Conversation", self.toolbar_new_conv_btn)
        new_action.setIcon(self._load_themed_icon("new"))
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Store menu reference but don't set it on the button (avoids arrow)
        self.toolbar_new_conv_menu = new_conv_menu
        
        # Apply menu styling
        self._style_menu(new_conv_menu)
        
        # Apply styling without menu attached
        self._style_tool_button(self.toolbar_new_conv_btn)
        
        toolbar_layout.addWidget(self.toolbar_new_conv_btn)
        
        # Browse conversations button
        self.browse_btn = QToolButton()
        self.browse_btn.setText("≡")
        self.browse_btn.setToolTip("Browse conversations")
        self.browse_btn.clicked.connect(self.browse_requested.emit)
        self._style_tool_button(self.browse_btn)
        toolbar_layout.addWidget(self.browse_btn)
        
        # Export button
        self.export_btn = QToolButton()
        self.export_btn.setText("↗")
        self.export_btn.setToolTip("Export current conversation")
        self.export_btn.clicked.connect(self._on_export_requested)
        self._style_tool_button(self.export_btn)
        toolbar_layout.addWidget(self.export_btn)
        
        # Settings button
        self.settings_btn = QToolButton()
        # Load gear icon (theme-specific)
        self._load_gear_icon(self.settings_btn)
        # Icon size is now handled by ButtonStyleManager
        self.settings_btn.setToolTip("Conversation settings")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self._style_tool_button(self.settings_btn)
        toolbar_layout.addWidget(self.settings_btn)
        
        toolbar_layout.addStretch()
        
        # Background summarization progress
        self.summary_progress = QProgressBar()
        self.summary_progress.setMaximum(0)  # Indeterminate
        self.summary_progress.setVisible(False)
        self.summary_progress.setMaximumHeight(3)
        self.summary_progress.setTextVisible(False)
        toolbar_layout.addWidget(self.summary_progress)
        
        # Summary notification label
        self.summary_notification = QLabel()
        self.summary_notification.setVisible(False)
        summary_color = self.theme_manager.current_theme.status_success if (self.theme_manager and THEME_SYSTEM_AVAILABLE) else "#4CAF50"
        self.summary_notification.setStyleSheet(f"color: {summary_color}; font-size: 9px; font-style: italic;")
        toolbar_layout.addWidget(self.summary_notification)
        
        parent_layout.addLayout(toolbar_layout)
    
    def _style_conversation_selector(self):
        """Apply custom styling to conversation selector - ALWAYS fully opaque."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            # Use theme colors for conversation selector
            bg_color = colors.background_secondary
            text_color = colors.text_primary
            border_color = colors.border_secondary
            focus_color = colors.border_focus
            
            style = f"QComboBox {{background-color: {bg_color}; color: {text_color}; border: none; border-radius: 5px; padding: 5px 10px; font-size: 11px;}} QComboBox:hover {{border: none;}} QComboBox::drop-down {{border: none; width: 20px;}} QComboBox::down-arrow {{image: none; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 5px solid {text_color}; margin-top: 2px;}} QComboBox QAbstractItemView {{background-color: {colors.background_primary}; color: {text_color}; selection-background-color: {colors.primary}; border: none; outline: none;}}"
        else:
            # Fallback styles - ALWAYS fully opaque
            style = f"QComboBox {{background-color: rgba(40, 40, 40, 1.0); color: white; border: none; border-radius: 5px; padding: 5px 10px; font-size: 11px;}} QComboBox:hover {{border: none;}} QComboBox::drop-down {{border: none; width: 20px;}} QComboBox::down-arrow {{image: none; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 5px solid white; margin-top: 2px;}} QComboBox QAbstractItemView {{background-color: rgba(30, 30, 30, 1.0); color: white; selection-background-color: #4CAF50; border: none; outline: none;}}"
        
        self.conversation_selector.setStyleSheet(style)
    
    def _style_tool_button(self, button: QToolButton):
        """Apply consistent styling to toolbar buttons using unified ButtonStyleManager."""
        # Remove old size constraints to let CSS take control
        button.setMaximumSize(16777215, 16777215)
        
        # Get theme colors and emoji font
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        emoji_font_stack = self._get_emoji_font_stack()
        
        # Apply theme-aware styling for better visibility (all themes)
        special_colors = {}
        if colors:
            # Use high-contrast background calculation to ensure button visibility
            special_colors = {
                "text": colors.text_primary,  # Use primary text color
                "background": self._get_high_contrast_button_background(colors),  # Use calculated high-contrast background
                "hover": colors.interactive_hover,  # Use theme's hover color
                "active": colors.interactive_active  # Use theme's active color
            }
        
        # Use unified button styling system with special colors if needed
        ButtonStyleManager.apply_unified_button_style(
            button, colors, "tool", "icon", "normal", special_colors, emoji_font_stack
        )
    
    def _apply_move_button_toggle_style(self, button: QToolButton):
        """
        Apply unified toggle styling to move button.
        Uses the new ButtonStyleManager with special warning colors.
        """
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        emoji_font_stack = self._get_emoji_font_stack()
        
        # Special colors for move button toggle state (warning/amber)
        special_colors = {
            "background": "rgba(255, 215, 0, 0.8)",
            "text": "black",
            "hover": "rgba(255, 215, 0, 0.9)",
            "active": "rgba(255, 215, 0, 1.0)"
        }
        
        ButtonStyleManager.apply_unified_button_style(
            button, colors, "tool", "icon", "normal", special_colors, emoji_font_stack
        )
    
    def _apply_pin_button_toggle_style(self, button: QToolButton):
        """
        Apply unified toggle styling to pin button.
        Uses the same colors as move button for consistency.
        """
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        emoji_font_stack = self._get_emoji_font_stack()
        
        # Special colors for pin button toggle state (same as move button)
        special_colors = {
            "background": "rgba(255, 215, 0, 0.8)",
            "text": "black",
            "hover": "rgba(255, 215, 0, 0.9)",
            "active": "rgba(255, 215, 0, 1.0)"
        }
        
        ButtonStyleManager.apply_unified_button_style(
            button, colors, "tool", "icon", "normal", special_colors, emoji_font_stack
        )

    def _get_high_contrast_button_background(self, colors):
        """
        Calculate the best high-contrast background color for buttons against the titlebar.
        
        This ensures buttons are always visible regardless of theme or opacity settings.
        Returns the best background color string (hex or rgba).
        """
        if not colors:
            return "#555555"  # Fallback if no theme colors available
        
        def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
            """Calculate WCAG contrast ratio between two hex colors."""
            try:
                from PyQt6.QtGui import QColor
                qcolor1 = QColor(color1_hex)
                qcolor2 = QColor(color2_hex)
                
                def get_luminance(qcolor):
                    r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                    r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                    g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                    b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                    return 0.2126 * r + 0.7152 * g + 0.0722 * b
                
                lum1 = get_luminance(qcolor1)
                lum2 = get_luminance(qcolor2)
                
                if lum1 < lum2:
                    lum1, lum2 = lum2, lum1
                
                return (lum1 + 0.05) / (lum2 + 0.05)
            except:
                return 1.0
        
        # Test against actual titlebar background (background_tertiary)
        titlebar_bg = colors.background_tertiary
        candidates = [
            colors.interactive_normal,    # Standard interactive background
            colors.border_primary,        # Border color (often good contrast)
            colors.background_primary,    # Primary background (darkest/lightest)
            "rgba(255, 255, 255, 0.15)", # Light semi-transparent for dark themes
            "rgba(0, 0, 0, 0.2)",        # Dark semi-transparent for light themes
        ]
        
        best_bg = colors.interactive_normal
        best_contrast = 0
        
        for candidate in candidates:
            try:
                # For RGBA colors, extract RGB values for contrast calculation
                test_color = candidate
                if "rgba" in candidate.lower():
                    # Extract RGB values from rgba(r,g,b,a) format
                    rgba_parts = candidate.lower().replace("rgba(", "").replace(")", "").split(",")
                    if len(rgba_parts) >= 3:
                        r, g, b = int(rgba_parts[0].strip()), int(rgba_parts[1].strip()), int(rgba_parts[2].strip())
                        test_color = f"#{r:02x}{g:02x}{b:02x}"
                contrast = calculate_contrast_ratio(test_color, titlebar_bg)
                if contrast > best_contrast:
                    best_contrast = contrast
                    best_bg = candidate
            except:
                continue
        
        # If still poor contrast (< 3.0), force a high-contrast solution
        if best_contrast < 3.0:
            try:
                from PyQt6.QtGui import QColor
                bg_color = QColor(colors.background_tertiary)
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
                
                if luminance < 0.5:  # Dark theme
                    best_bg = "rgba(255, 255, 255, 0.2)"  # Light semi-transparent
                else:  # Light theme
                    best_bg = "rgba(0, 0, 0, 0.15)"       # Dark semi-transparent
            except:
                best_bg = colors.interactive_normal
        
        return best_bg

    def _style_title_button(self, button, add_right_padding: bool = False):
        """
        Apply unified styling to title bar buttons.
        Uses the new ButtonStyleManager for consistency.
        Handles both QToolButton (with icons) and QPushButton (minimize) properly.
        """
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        emoji_font_stack = self._get_emoji_font_stack()
        
        # Detect button type automatically
        from PyQt6.QtWidgets import QPushButton, QToolButton
        if isinstance(button, QPushButton):
            button_type = "push"
        else:
            button_type = "tool"
        
        # Handle special padding for plus button
        if add_right_padding:
            # Apply the same improved contrast calculation for plus button
            if isinstance(button, QToolButton) and colors:
                # Calculate improved colors (same logic as above)
                def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
                    """Calculate WCAG contrast ratio between two hex colors."""
                    try:
                        from PyQt6.QtGui import QColor
                        qcolor1 = QColor(color1_hex)
                        qcolor2 = QColor(color2_hex)
                        
                        def get_luminance(qcolor):
                            r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                            r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                            g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                            b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                            return 0.2126 * r + 0.7152 * g + 0.0722 * b
                        
                        lum1 = get_luminance(qcolor1)
                        lum2 = get_luminance(qcolor2)
                        
                        if lum1 < lum2:
                            lum1, lum2 = lum2, lum1
                        
                        return (lum1 + 0.05) / (lum2 + 0.05)
                    except:
                        return 1.0  # Fallback for any errors
                
                # Apply improved contrast calculation for plus button
                titlebar_bg = colors.background_tertiary
                candidates = [
                    colors.interactive_normal,
                    colors.border_primary,
                    colors.background_primary,
                    "rgba(255, 255, 255, 0.15)",
                    "rgba(0, 0, 0, 0.2)",
                ]
                
                best_bg = colors.interactive_normal
                best_contrast = 0
                
                for candidate in candidates:
                    try:
                        # For RGBA colors, extract RGB values for contrast calculation
                        test_color = candidate
                        if "rgba" in candidate.lower():
                            # Extract RGB values from rgba(r,g,b,a) format
                            rgba_parts = candidate.lower().replace("rgba(", "").replace(")", "").split(",")
                            if len(rgba_parts) >= 3:
                                r, g, b = int(rgba_parts[0].strip()), int(rgba_parts[1].strip()), int(rgba_parts[2].strip())
                                test_color = f"#{r:02x}{g:02x}{b:02x}"
                        contrast = calculate_contrast_ratio(test_color, titlebar_bg)
                        if contrast > best_contrast:
                            best_contrast = contrast
                            best_bg = candidate
                    except:
                        continue
                
                # Force high-contrast if needed
                if best_contrast < 3.0:
                    try:
                        from PyQt6.QtGui import QColor
                        bg_color = QColor(colors.background_tertiary)
                        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
                        
                        if luminance < 0.5:  # Dark theme
                            best_bg = "rgba(255, 255, 255, 0.2)"
                        else:  # Light theme  
                            best_bg = "rgba(0, 0, 0, 0.1)"
                    except:
                        best_bg = colors.interactive_normal
                
                # Create improved colors ColorSystem for plus button
                from types import SimpleNamespace
                improved_colors = SimpleNamespace()
                for attr in dir(colors):
                    if not attr.startswith('_'):
                        setattr(improved_colors, attr, getattr(colors, attr))
                
                # Override with improved background
                improved_colors.interactive_normal = best_bg
                improved_colors.interactive_hover = "rgba(255, 255, 255, 0.3)" if best_bg.startswith("rgba(255") else colors.interactive_hover
                improved_colors.interactive_active = "rgba(255, 255, 255, 0.4)" if best_bg.startswith("rgba(255") else colors.interactive_active
                
                ButtonStyleManager.apply_plus_button_style(button, improved_colors, emoji_font_stack)
            else:
                # Fallback to original method
                ButtonStyleManager.apply_plus_button_style(button, colors, emoji_font_stack)
        else:
            # Apply theme-aware styling for better visibility
            # Only apply special colors to QToolButtons (icon buttons), NOT QPushButtons (minimize)
            special_colors = {}
            if isinstance(button, QToolButton) and colors:
                # IMPROVED: Calculate the best background color for maximum contrast
                # against the titlebar background (background_secondary)
                
                def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
                    """Calculate WCAG contrast ratio between two hex colors."""
                    try:
                        from PyQt6.QtGui import QColor
                        qcolor1 = QColor(color1_hex)
                        qcolor2 = QColor(color2_hex)
                        
                        def get_luminance(qcolor):
                            r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                            r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                            g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                            b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                            return 0.2126 * r + 0.7152 * g + 0.0722 * b
                        
                        lum1 = get_luminance(qcolor1)
                        lum2 = get_luminance(qcolor2)
                        
                        if lum1 < lum2:
                            lum1, lum2 = lum2, lum1
                        
                        return (lum1 + 0.05) / (lum2 + 0.05)
                    except:
                        return 1.0  # Fallback for any errors
                
                # Try different background options and pick the one with best contrast
                titlebar_bg = colors.background_tertiary
                candidates = [
                    colors.interactive_normal,    # Standard interactive background
                    colors.border_primary,        # Border color (often good contrast)
                    colors.background_primary,    # Primary background (darkest/lightest)
                    colors.primary + "40",        # Primary with 25% opacity
                    colors.secondary + "40",      # Secondary with 25% opacity
                    "rgba(255, 255, 255, 0.15)", # Light semi-transparent for dark themes
                    "rgba(0, 0, 0, 0.2)",        # Dark semi-transparent for light themes
                ]
                
                best_bg = colors.interactive_normal  # fallback
                best_contrast = 0
                
                for candidate in candidates:
                    try:
                        # For RGBA colors, extract RGB values for contrast calculation
                        test_color = candidate
                        if "rgba" in candidate.lower():
                            # Extract RGB values from rgba(r,g,b,a) format
                            rgba_parts = candidate.lower().replace("rgba(", "").replace(")", "").split(",")
                            if len(rgba_parts) >= 3:
                                r, g, b = int(rgba_parts[0].strip()), int(rgba_parts[1].strip()), int(rgba_parts[2].strip())
                                test_color = f"#{r:02x}{g:02x}{b:02x}"
                        contrast = calculate_contrast_ratio(test_color, titlebar_bg)
                        if contrast > best_contrast:
                            best_contrast = contrast
                            best_bg = candidate
                    except:
                        continue
                
                # If still poor contrast (< 3.0), force a high-contrast solution
                if best_contrast < 3.0:
                    # Determine if theme is dark or light based on background luminance
                    try:
                        from PyQt6.QtGui import QColor
                        bg_color = QColor(colors.background_tertiary)
                        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
                        
                        if luminance < 0.5:  # Dark theme
                            best_bg = "rgba(255, 255, 255, 0.2)"  # Light semi-transparent
                            hover_bg = "rgba(255, 255, 255, 0.3)"
                            active_bg = "rgba(255, 255, 255, 0.4)"
                        else:  # Light theme
                            best_bg = "rgba(0, 0, 0, 0.1)"       # Dark semi-transparent
                            hover_bg = "rgba(0, 0, 0, 0.15)"
                            active_bg = "rgba(0, 0, 0, 0.2)"
                    except:
                        # Ultimate fallback
                        best_bg = colors.interactive_normal
                        hover_bg = colors.interactive_hover
                        active_bg = colors.interactive_active
                else:
                    # Good contrast found, create proportional hover/active colors
                    hover_bg = colors.interactive_hover
                    active_bg = colors.interactive_active
                
                special_colors = {
                    "text": colors.text_primary,  # Use primary text color
                    "background": best_bg,        # Use calculated high-contrast background
                    "hover": hover_bg,           # Use theme's hover color or calculated
                    "active": active_bg,         # Use theme's active color or calculated
                    "border": colors.border_primary  # Add subtle border for extra definition
                }
            
            # Use standard unified styling with special colors if needed
            logger.info(f"Applying unified icon styling to {button_type} button")
            ButtonStyleManager.apply_unified_button_style(
                button, colors, button_type, "icon", "normal", special_colors, emoji_font_stack
            )
        
        # Force style refresh for theme switching to ensure immediate updates
        if colors:
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
            
        logger.debug(f"Applied title button styling to {button_type} button with theme-aware colors")
    
    def _style_send_button(self):
        """Style the Send button with unified primary styling."""
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        
        # If no theme is available yet, apply a basic style to avoid unstyled button
        if not colors:
            # Apply a basic green send button style as fallback
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QPushButton:pressed {
                    background-color: #047857;
                }
            """)
            return
        
        # Use primary state for send button with theme colors
        ButtonStyleManager.apply_unified_button_style(
            self.send_button, colors, "push", "small", "toggle"
        )
    
    def _style_stop_button(self):
        """Style the Stop button with unified danger styling."""
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        
        # If no theme is available yet, apply a basic style to avoid unstyled button
        if not colors:
            # Apply a basic red stop button style as fallback
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
                QPushButton:pressed {
                    background-color: #b91c1c;
                }
            """)
            return
        
        # Use danger state for stop button with theme colors
        ButtonStyleManager.apply_unified_button_style(
            self.stop_button, colors, "push", "small", "danger"
        )
    
    def _style_menu(self, menu):
        """Apply theme-based styling to a QMenu."""
        if not self.theme_manager or not THEME_SYSTEM_AVAILABLE:
            return
        
        colors = self.theme_manager.current_theme
        if colors:
            from ...ui.themes.style_templates import StyleTemplates
            menu.setStyleSheet(StyleTemplates.get_menu_style(colors))
    
    def _refresh_menu_styling(self):
        """Refresh styling for all menus in the widget."""
        # Re-style title bar new conversation menu if it exists
        if hasattr(self, 'title_new_conv_menu') and self.title_new_conv_menu:
            self._style_menu(self.title_new_conv_menu)
        
        # Re-style toolbar new conversation menu if it exists
        if hasattr(self, 'toolbar_new_conv_menu') and self.toolbar_new_conv_menu:
            self._style_menu(self.toolbar_new_conv_menu)
        
        # Re-style any other menus that might exist
        for attr_name in dir(self):
            if 'menu' in attr_name.lower():
                attr = getattr(self, attr_name, None)
                if attr and hasattr(attr, 'setStyleSheet'):
                    try:
                        self._style_menu(attr)
                    except:
                        pass  # Skip if not a QMenu
    
    def _update_search_button_state(self):
        """Update search button visual state using unified styling system."""
        try:
            if not hasattr(self, 'search_btn'):
                return
                
            # Check if search is active
            search_active = hasattr(self, 'search_frame') and self.search_frame and self.search_frame.isVisible()
            colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
            
            if search_active:
                # Use warning state for active search (matching theme)
                state = "warning"
                special_colors = {
                    "background": colors.primary if colors else "#ff9800",
                    "text": colors.background_primary if colors else "#000000",
                    "hover": colors.primary_hover if colors else "#f57c00",
                    "active": colors.primary if colors else "#e6940b"
                }
            else:
                # Apply theme-aware darker styling for better visibility (all themes)
                state = "normal"
                special_colors = {}
                if colors:
                    # Use high-contrast background calculation to ensure button visibility
                    special_colors = {
                        "text": colors.text_primary,  # Use primary text color
                        "background": self._get_high_contrast_button_background(colors),  # Use calculated high-contrast background
                        "hover": colors.interactive_hover,  # Use theme's hover color
                        "active": colors.interactive_active  # Use theme's active color
                    }
            
            # Apply unified styling
            ButtonStyleManager.apply_unified_button_style(
                self.search_btn, colors, "tool", "icon", state, special_colors
            )
            
            logger.debug(f"Updated search button state: active={search_active}")
            
        except Exception as e:
            logger.error(f"Failed to update search button state: {e}")
    
    def _update_upload_button_state(self):
        """Update upload button visual state using unified styling system."""
        try:
            if not hasattr(self, 'upload_btn'):
                return
                
            # Check if file browser is active
            file_browser_active = hasattr(self, 'file_browser_bar') and self.file_browser_bar and self.file_browser_bar.isVisible()
            colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
            
            if file_browser_active:
                # Use primary state for active file browser (matching theme)
                state = "warning"
                special_colors = {
                    "background": colors.primary if colors else "#007bff",
                    "text": colors.background_primary if colors else "#ffffff",
                    "hover": colors.primary_hover if colors else "#0056b3",
                    "active": colors.primary if colors else "#004085"
                }
            else:
                # Apply theme-aware darker styling for better visibility (all themes)
                state = "normal"
                special_colors = {}
                if colors:
                    # Use high-contrast background calculation to ensure button visibility
                    special_colors = {
                        "text": colors.text_primary,  # Use primary text color
                        "background": self._get_high_contrast_button_background(colors),  # Use calculated high-contrast background
                        "hover": colors.interactive_hover,  # Use theme's hover color
                        "active": colors.interactive_active  # Use theme's active color
                    }
            
            # Apply unified styling
            ButtonStyleManager.apply_unified_button_style(
                self.upload_btn, colors, "tool", "icon", state, special_colors
            )
            
            logger.debug(f"Updated upload button state: active={file_browser_active}")
            
        except Exception as e:
            logger.error(f"Failed to update upload button state: {e}")
    
    def _update_attach_button_state(self):
        """Update attach button visual state using unified styling system."""
        try:
            if not hasattr(self, 'attach_btn'):
                return
                
            # Check if attached
            is_attached = self.attach_btn.isChecked()
            colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
            
            if is_attached:
                # Use success state for attached state
                state = "success"
                special_colors = {
                    "background": colors.status_success if colors else "#4CAF50",
                    "text": colors.background_primary if colors else "#ffffff",
                    "hover": colors.primary_hover if colors else "#66bb6a",
                    "active": colors.status_success if colors else "#45a049"
                }
            else:
                # Apply theme-aware darker styling for better visibility (all themes)
                state = "normal"
                special_colors = {}
                if colors:
                    # Use high-contrast background calculation to ensure button visibility
                    special_colors = {
                        "text": colors.text_primary,  # Use primary text color
                        "background": self._get_high_contrast_button_background(colors),  # Use calculated high-contrast background
                        "hover": colors.interactive_hover,  # Use theme's hover color
                        "active": colors.interactive_active  # Use theme's active color
                    }
            
            # Apply unified styling
            ButtonStyleManager.apply_unified_button_style(
                self.attach_btn, colors, "tool", "icon", state, special_colors
            )
            
            logger.debug(f"Updated attach button state: attached={is_attached}")
            
        except Exception as e:
            logger.error(f"Failed to update attach button state: {e}")
    
    def _apply_pin_button_toggle_style(self, button: QToolButton):
        """
        Apply unified toggle styling to pin button.
        Uses the new ButtonStyleManager with special warning colors - SAME AS MOVE BUTTON.
        """
        colors = self.theme_manager.current_theme if self.theme_manager and THEME_SYSTEM_AVAILABLE else None
        emoji_font_stack = self._get_emoji_font_stack()
        
        # Special colors for pin button toggle state (warning/amber) - IDENTICAL to move button
        special_colors = {
            "background": "rgba(255, 215, 0, 0.8)",
            "text": "black",
            "hover": "rgba(255, 215, 0, 0.9)",
            "active": "rgba(255, 215, 0, 1.0)"
        }
        
        ButtonStyleManager.apply_unified_button_style(
            button, colors, "tool", "icon", "normal", special_colors, emoji_font_stack
        )

    def _update_pin_button_state(self):
        """Update pin button visual state using unified styling system."""
        try:
            if not hasattr(self, 'pin_btn'):
                return
                
            # Check if pin is active (always on top enabled)
            pin_active = self.pin_btn.isChecked()
            
            # Note: Icon will be reloaded after styling
            
            if pin_active:
                # Apply toggle styling with amber feedback - SAME AS MOVE BUTTON
                self._apply_pin_button_toggle_style(self.pin_btn)
                logger.debug("Applied pin button toggle styling (amber)")
            else:
                # Reset to normal styling - SAME AS MOVE BUTTON
                self._style_title_button(self.pin_btn)
                logger.debug("Applied normal pin button styling")
            
            # CRITICAL: Reload icon after styling to ensure it's preserved
            self._load_pin_icon_immediate()
            
            # Ensure text is always cleared
            if hasattr(self.pin_btn, '_original_setText'):
                self.pin_btn._original_setText("")
            else:
                self.pin_btn.setText("")
            
            # Apply the same styling as other buttons but with special toggle colors if active
            if pin_active:
                self._apply_pin_button_toggle_style(self.pin_btn)
            else:
                self._style_title_button(self.pin_btn)
            
            # Reload icon after styling
            self._load_pin_icon_immediate()
            
            # Ensure text is always cleared using original method to avoid recursion
            if hasattr(self.pin_btn, '_original_setText'):
                self.pin_btn._original_setText("")
            else:
                self.pin_btn.setText("")
            
            logger.debug(f"Updated pin button state: active={pin_active}")
            
        except Exception as e:
            logger.error(f"Failed to update pin button state: {e}")
    
    def _load_search_icon(self):
        """Load theme-appropriate search icon."""
        try:
            # Determine if theme is dark or light
            icon_variant = self._get_icon_variant()
            
            search_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"search_{icon_variant}.png"
            )
            
            if os.path.exists(search_icon_path):
                search_icon = QIcon(search_icon_path)
                self.search_btn.setIcon(search_icon)
                logger.debug(f"Loaded search icon: search_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                self.search_btn.setText("⌕")
                logger.warning(f"Search icon not found: {search_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load search icon: {e}")
            if hasattr(self, 'search_btn') and self.search_btn:
                self.search_btn.setText("⌕")  # Fallback
    
    def _load_chain_icon(self):
        """Load theme-appropriate chain icon."""
        try:
            # Check if attach_btn exists first
            if not hasattr(self, 'attach_btn') or not self.attach_btn:
                logger.debug("attach_btn not yet created, skipping chain icon loading")
                return
                
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            chain_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"chain_{icon_variant}.png"
            )
            
            if os.path.exists(chain_icon_path):
                chain_icon = QIcon(chain_icon_path)
                self.attach_btn.setIcon(chain_icon)
                logger.debug(f"Loaded chain icon: chain_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                self.attach_btn.setText("⚲")
                logger.warning(f"Chain icon not found: {chain_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load chain icon: {e}")
            if hasattr(self, 'attach_btn') and self.attach_btn:
                self.attach_btn.setText("⚲")  # Fallback
    
    def _load_filebar_icon(self):
        """Load theme-appropriate filebar icon - EXACT COPY of _load_search_icon pattern."""
        logger.info("🎨 ICON: Loading filebar icon...")
        try:
            # Check button exists
            if not hasattr(self, 'upload_btn'):
                logger.error("❌ ICON: upload_btn doesn't exist yet!")
                return
                
            # Determine if theme is dark or light
            icon_variant = self._get_icon_variant()
            logger.info(f"🎨 ICON: Theme variant = {icon_variant}")
            
            filebar_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"filebar_{icon_variant}.png"
            )
            logger.info(f"🎨 ICON: Looking for icon at: {filebar_icon_path}")
            
            if os.path.exists(filebar_icon_path):
                logger.info(f"✅ ICON: File exists at {filebar_icon_path}")
                filebar_icon = QIcon(filebar_icon_path)
                
                if filebar_icon.isNull():
                    logger.error(f"❌ ICON: QIcon is null after loading from {filebar_icon_path}")
                    self.upload_btn.setText("📁")
                else:
                    self.upload_btn.setIcon(filebar_icon)
                    
                    # Set icon size explicitly
                    from PyQt6.QtCore import QSize
                    self.upload_btn.setIconSize(QSize(16, 16))
                    
                    # Verify the icon was actually set
                    final_icon = self.upload_btn.icon()
                    if final_icon.isNull():
                        logger.error("❌ ICON: Icon is null after setting!")
                        self.upload_btn.setText("📁")  # Fallback
                    else:
                        logger.info(f"✅ ICON: Icon successfully set and verified: filebar_{icon_variant}.png")
                        # Clear any text when icon is set successfully
                        self.upload_btn.setText("")
                    
                    # Check final button state
                    button_text = self.upload_btn.text()
                    logger.info(f"🔧 ICON: Final button text = '{button_text}'")
            else:
                # Fallback to Unicode symbol
                logger.warning(f"❌ ICON: Filebar icon not found at: {filebar_icon_path}")
                self.upload_btn.setText("📁")
                
        except Exception as e:
            logger.error(f"❌ ICON: Exception loading filebar icon: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self, 'upload_btn') and self.upload_btn:
                self.upload_btn.setText("📁")  # Fallback
    
    def _load_chat_icon(self):
        """Load theme-appropriate chat icon."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            chat_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"chat_{icon_variant}.png"
            )
            
            if os.path.exists(chat_icon_path):
                chat_icon = QIcon(chat_icon_path)
                self.chat_btn.setIcon(chat_icon)
                logger.debug(f"Loaded chat icon: chat_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                self.chat_btn.setText("☰")
                logger.warning(f"Chat icon not found: {chat_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load chat icon: {e}")
            self.chat_btn.setText("☰")  # Fallback
    
    def _load_gear_icon(self, button):
        """Load theme-appropriate gear icon for a given button."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            gear_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"gear_{icon_variant}.png"
            )
            
            if os.path.exists(gear_icon_path):
                gear_icon = QIcon(gear_icon_path)
                button.setIcon(gear_icon)
                logger.debug(f"Loaded gear icon: gear_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                button.setText("⚙")
                logger.warning(f"Gear icon not found: {gear_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load gear icon: {e}")
            button.setText("⚙")  # Fallback
    
    def _load_plus_icon(self, button):
        """Load theme-appropriate plus icon for a given button."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            plus_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"plus_{icon_variant}.png"
            )
            
            if os.path.exists(plus_icon_path):
                plus_icon = QIcon(plus_icon_path)
                button.setIcon(plus_icon)
                logger.debug(f"Loaded plus icon: plus_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                button.setText("➕")
                logger.warning(f"Plus icon not found: {plus_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load plus icon: {e}")
            button.setText("➕")  # Fallback
    
    def _load_themed_icon(self, icon_name):
        """Load theme-appropriate icon and return QIcon object for menus."""
        try:
            # Determine icon variant based on menu background color
            icon_variant = self._get_menu_icon_variant()
            
            icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"{icon_name}_{icon_variant}.png"
            )
            
            if os.path.exists(icon_path):
                logger.debug(f"Loaded themed icon: {icon_name}_{icon_variant}.png")
                return QIcon(icon_path)
            else:
                logger.warning(f"Themed icon not found: {icon_path}")
                return QIcon()  # Return empty icon
                
        except Exception as e:
            logger.error(f"Failed to load themed icon '{icon_name}': {e}")
            return QIcon()  # Return empty icon
    
    def _load_help_icon(self, button):
        """Load theme-appropriate help-docs icon for a given button."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            # First try help-docs icon (preferred)
            help_docs_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"help-docs_{icon_variant}.png"
            )
            
            # Fallback to regular help icon if help-docs not found
            help_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"help_{icon_variant}.png"
            )
            
            if os.path.exists(help_docs_icon_path):
                help_icon = QIcon(help_docs_icon_path)
                button.setIcon(help_icon)
                logger.debug(f"Loaded help-docs icon: help-docs_{icon_variant}.png")
            elif os.path.exists(help_icon_path):
                help_icon = QIcon(help_icon_path)
                button.setIcon(help_icon)
                logger.debug(f"Loaded help icon: help_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                button.setText("❓")
                logger.warning(f"Help icons not found: {help_docs_icon_path} or {help_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load help icon: {e}")
            button.setText("❓")  # Fallback
    
    def _load_help_command_icon(self, button):
        """Load theme-appropriate regular help icon for help command button."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            # Use regular help icon (not help-docs)
            help_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"help_{icon_variant}.png"
            )
            
            if os.path.exists(help_icon_path):
                help_icon = QIcon(help_icon_path)
                button.setIcon(help_icon)
                logger.debug(f"Loaded help command icon: help_{icon_variant}.png")
            else:
                logger.warning(f"Help command icon not found: {help_icon_path}")
                button.setText("❓")  # Fallback
                
        except Exception as e:
            logger.error(f"Failed to load help command icon: {e}")
            button.setText("❓")  # Fallback
    
    def _load_move_icon(self, button):
        """Load theme-appropriate move icon for a given button."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            move_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"move_{icon_variant}.png"
            )
            
            if os.path.exists(move_icon_path):
                move_icon = QIcon(move_icon_path)
                button.setIcon(move_icon)
                logger.debug(f"Loaded move icon: move_{icon_variant}.png")
            else:
                # Fallback to Unicode symbol
                button.setText("✥")
                logger.warning(f"Move icon not found: {move_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load move icon: {e}")
            button.setText("✥")  # Fallback
    
    def _load_save_icon(self, button):
        """Load theme-appropriate save icon for a given button."""
        try:
            # Use the enhanced theme manager's icon suffix
            if self.theme_manager and hasattr(self.theme_manager, 'current_icon_suffix'):
                icon_suffix = self.theme_manager.current_icon_suffix
                current_theme_name = getattr(self.theme_manager, '_current_theme_name', 'unknown')
                theme_mode = self.theme_manager.current_theme_mode if hasattr(self.theme_manager, 'current_theme_mode') else 'unknown'
                logger.debug(f"Theme info - Name: {current_theme_name}, Mode: {theme_mode}, Icon suffix: {icon_suffix}")
            else:
                # Fallback to old method if theme manager not available
                icon_suffix = f"_{self._get_icon_variant()}"
                logger.debug(f"Using fallback icon variant: {icon_suffix}")
            
            save_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"save{icon_suffix}.png"
            )
            
            if os.path.exists(save_icon_path):
                save_icon = QIcon(save_icon_path)
                button.setIcon(save_icon)
                logger.info(f"✓ Loaded save icon: save{icon_suffix}.png")
            else:
                # Fallback to Unicode symbol
                button.setText("💾")
                logger.warning(f"Save icon not found: {save_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load save icon: {e}")
            button.setText("💾")  # Fallback
    
    def _get_icon_variant(self) -> str:
        """Determine which icon variant to use based on theme."""
        try:
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
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
    
    def _load_theme_icon(self, icon_name: str, use_theme_variant: bool = True) -> QIcon:
        """Load icon using centralized resource resolver."""
        try:
            from ...utils.resource_resolver import resolve_icon
            
            # Determine theme suffix
            theme_suffix = ""
            if use_theme_variant:
                variant = self._get_icon_variant()
                theme_suffix = f"_{variant}"
            
            icon_path = resolve_icon(icon_name, theme_suffix)
            if icon_path:
                return QIcon(str(icon_path))
        except Exception as e:
            logger.debug(f"Failed to load theme icon {icon_name}: {e}")
        
        return QIcon()  # Empty icon as fallback
    
    def _get_menu_icon_variant(self) -> str:
        """Determine which icon variant to use for menu items based on menu background color.
        
        Menus use background_secondary, and if it's light, we need dark icons.
        If it's dark, we need light icons.
        """
        try:
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                colors = self.theme_manager.current_theme
                # Check menu background color (background_secondary)
                menu_bg_color = colors.background_secondary
                
                # Calculate luminance to determine if background is light or dark
                if menu_bg_color.startswith('#'):
                    # Remove # and get RGB values
                    hex_color = menu_bg_color.lstrip('#')
                    if len(hex_color) == 6:
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        
                        # Calculate relative luminance using W3C formula
                        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                        
                        # If luminance > 0.5, background is light, use dark icons
                        # If luminance <= 0.5, background is dark, use light icons
                        if luminance > 0.5:
                            logger.debug(f"Menu background is light (luminance: {luminance:.2f}), using dark icons")
                            return "dark"
                        else:
                            logger.debug(f"Menu background is dark (luminance: {luminance:.2f}), using lite icons")
                            return "lite"
                    elif len(hex_color) == 3:
                        # Handle shorthand hex colors like #fff
                        r = int(hex_color[0] * 2, 16)
                        g = int(hex_color[1] * 2, 16)
                        b = int(hex_color[2] * 2, 16)
                        
                        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                        
                        if luminance > 0.5:
                            logger.debug(f"Menu background is light (luminance: {luminance:.2f}), using dark icons")
                            return "dark"
                        else:
                            logger.debug(f"Menu background is dark (luminance: {luminance:.2f}), using lite icons")
                            return "lite"
                
                # Fallback: check using simple heuristic
                if menu_bg_color.startswith('#') and len(menu_bg_color) >= 2:
                    first_hex_digit = int(menu_bg_color[1], 16)
                    # If first digit is 8-F, it's likely light, use dark icons
                    return "dark" if first_hex_digit >= 8 else "lite"
            
            # Default fallback for dark menus
            return "lite"
            
        except Exception as e:
            logger.error(f"Failed to determine menu icon variant: {e}")
            return "lite"  # Default to lite icons for dark backgrounds
    
    def _get_emoji_font_stack(self) -> str:
        """Get a font stack that supports emoji rendering on Windows."""
        # Windows emoji-compatible fonts in priority order
        emoji_fonts = [
            "Segoe UI Emoji",      # Primary Windows emoji font
            "Segoe UI Symbol",     # Windows symbol font  
            "Segoe UI",           # Standard Windows UI font with emoji support
            "Microsoft YaHei",     # Chinese font with good emoji support
            "Apple Color Emoji",   # For cross-platform compatibility
            "Noto Color Emoji",    # Google emoji font
            "Noto Emoji",         # Google monochrome emoji
            "Arial Unicode MS",    # Fallback Unicode font
            "sans-serif"          # Final fallback
        ]
        
        # Format as CSS font-family list
        font_stack = ", ".join(f'"{font}"' for font in emoji_fonts)
        logger.debug(f"Generated emoji font stack: {font_stack}")
        return font_stack
    
    def _restore_button_emoji(self, button: QToolButton, emoji_text: str, button_name: str):
        """Restore emoji text to a button using multiple strategies."""
        try:
            # Strategy 1: Force font and text refresh
            original_font = button.font()
            
            # Create emoji-compatible font
            emoji_font = QFont()
            emoji_font.setFamily("Segoe UI Emoji")
            emoji_font.setPointSize(12)
            
            # Clear and restore text with font context
            button.setText("")  # Clear first
            button.setFont(emoji_font)  # Set emoji font
            button.setText(emoji_text)  # Set emoji text
            
            # Strategy 2: Force widget update
            button.update()
            button.repaint()
            
            logger.debug(f"Restored emoji for {button_name}: {emoji_text}")
            
        except Exception as e:
            logger.warning(f"Failed to restore emoji for {button_name}: {e}")
            # Fallback: just set the text without font manipulation
            try:
                button.setText(emoji_text)
            except Exception as fallback_error:
                logger.error(f"Fallback emoji restoration failed for {button_name}: {fallback_error}")
    
    def _refresh_toolbar_icons(self):
        """Refresh toolbar button icons to prevent ellipses display after theme changes."""
        try:
            # Define all toolbar buttons with their Unicode symbols
            button_icons = [
                ('chat_btn', "☰"),
                ('search_btn', "⌕"),
                ('browse_btn', "≡"),
                ('export_btn', "↗"),
                ('settings_btn', "⚙"),
            ]
            
            # Refresh each button's emoji text with enhanced restoration
            for widget_name, icon_text in button_icons:
                if hasattr(self, widget_name):
                    button = getattr(self, widget_name)
                    if button and hasattr(button, 'setText'):
                        # Skip buttons that are using icons instead of text
                        if hasattr(button, 'icon') and not button.icon().isNull():
                            logger.debug(f"Skipping icon refresh for {widget_name} - using icon file")
                            continue
                        # Multi-step restoration process for text-based buttons
                        self._restore_button_emoji(button, icon_text, widget_name)
            
            # Special handling for attach button state (changes based on checked state)
            if hasattr(self, 'attach_btn') and self.attach_btn:
                # Skip if using icon file
                if hasattr(self.attach_btn, 'icon') and not self.attach_btn.icon().isNull():
                    logger.debug("Skipping attach button refresh - using icon file")
                else:
                    # Using text fallback
                    attached = self.attach_btn.isChecked()
                    icon = "⚲" if attached else "⚮"
                    self._restore_button_emoji(self.attach_btn, icon, "attach_btn")
            
            # PROTECTION: Ensure pin button never gets emoji restoration
            if hasattr(self, 'pin_btn') and self.pin_btn:
                # Pin button should ONLY use PNG icons, never emoji
                if hasattr(self.pin_btn, 'icon') and not self.pin_btn.icon().isNull():
                    logger.debug("Pin button using icon file - preserving icon")
                    # Ensure text is always cleared
                    self.pin_btn.setText("")
                else:
                    # If icon is null for some reason, reload it immediately
                    logger.warning("Pin button icon is null - force reloading")
                    self._load_pin_icon_immediate()
                
            logger.debug("Completed toolbar icon refresh to prevent ellipses")
        except Exception as e:
            logger.error(f"Failed to refresh toolbar icons: {e}")
    
    def _load_opacity_from_settings(self):
        """Load panel opacity from settings manager."""
        if not _global_settings:
            return
            
        try:
            # Try new percent-based settings first
            percent = _global_settings.get('interface.opacity', None)
            if percent is None:
                # Backward compatibility with legacy float-based settings
                legacy_opacity = _global_settings.get('ui.window_opacity', None)
                if isinstance(legacy_opacity, (int, float)):
                    if legacy_opacity <= 1.0:
                        percent = int(round(legacy_opacity * 100))
                    else:
                        percent = int(legacy_opacity)
            
            if percent is not None:
                if isinstance(percent, (int, float)):
                    percent_int = max(10, min(100, int(percent)))
                    self._panel_opacity = percent_int / 100.0
                    logger.debug(f"Loaded panel opacity from settings: {percent_int}% -> {self._panel_opacity:.2f}")
        except Exception as e:
            logger.warning(f"Failed to load opacity from settings: {e}")
    
    def _init_ui(self):
        """Initialize the enhanced user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)  # Reduce default spacing by ~50% (from ~6 to 3)
        
        # Initialize resize functionality
        self._init_resize_functionality()
        
        # Tab bar above title bar
        self._init_tab_bar(layout)
        
        # Title bar with new conversation and help buttons
        self._init_title_bar(layout)
        
        # Output display - NOW HANDLED BY TAB MANAGER!
        # Each tab owns its own MixedContentDisplay widget in the TabManager's QStackedWidget
        # We keep self.output_display as a property for backward compatibility,
        # but it now points to the active tab's widget

        # Add the tab manager's QStackedWidget to the layout in the correct position
        # This replaces the old self.output_display widget
        if self.tab_manager and hasattr(self.tab_manager, 'output_stack'):
            layout.addWidget(self.tab_manager.output_stack, 1)  # Stretch factor of 1
            logger.debug("Added tab_manager.output_stack to layout")

        # In-conversation search bar (initially hidden)
        self._init_search_bar(layout)

        # File browser stack (per-tab file browsers)
        if self.tab_manager and hasattr(self.tab_manager, 'file_browser_stack'):
            layout.addWidget(self.tab_manager.file_browser_stack)
            logger.debug("Added tab_manager.file_browser_stack to layout")
        
        # Input area with background styling for prompt
        input_layout = QHBoxLayout()
        
        # Prompt label with background styling for better visual separation
        # Align to center to match Send/Stop button baseline
        self.prompt_label = QLabel(">>>")
        self._style_prompt_label(normal=True)
        # Set internal text alignment to center both horizontally and vertically
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Set size policy to match buttons and allow vertical centering
        self.prompt_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, 
            QSizePolicy.Policy.Fixed
        )
        # Set fixed height to match typical button height for proper alignment
        self.prompt_label.setFixedHeight(32)  # Standard button height
        # Add to layout with center alignment to match button baseline
        input_layout.addWidget(self.prompt_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Command input - using QPlainTextEdit for multiline support
        self.command_input = QPlainTextEdit()
        # Use font service for user input font
        input_font = font_service.create_qfont('user_input')
        self.command_input.setFont(input_font)
        # Enable word wrapping for long text
        self.command_input.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.command_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        # Set initial height to match button height (32px) to prevent font squishing
        # The dynamic height system will take over after initialization, but this ensures
        # proper baseline alignment from the start
        BUTTON_HEIGHT = 32  # Match the button height from ButtonStyleManager "small" size
        self.command_input.setMinimumHeight(BUTTON_HEIGHT)
        self.command_input.setMaximumHeight(BUTTON_HEIGHT)  # Start with fixed height, will be adjusted dynamically
        self.command_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Ensure field grows downward by setting size policy
        self.command_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Preferred
        )
        self.command_input.installEventFilter(self)
        # Add with center alignment to match prompt and button baselines
        input_layout.addWidget(self.command_input, 1, Qt.AlignmentFlag.AlignVCenter)
        
        # Send button - align to bottom baseline
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._on_command_entered)
        self.send_button.setFixedHeight(32)  # Match prompt label height
        self._style_send_button()
        input_layout.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Stop button (hidden by default) - align to bottom baseline
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_query)
        self.stop_button.setVisible(False)
        self._style_stop_button()
        input_layout.addWidget(self.stop_button, 0, Qt.AlignmentFlag.AlignBottom)
        
        layout.addLayout(input_layout)
        
        # Initial startup and preamble - will be set after startup tasks complete
        # This will be replaced by _display_startup_preamble() called from _load_conversations_deferred
        
        # Initialize dynamic input height system after UI is created
        self._init_dynamic_input_height()
        
        # Focus on input
        self.command_input.setFocus()
    
    def _apply_styles(self):
        """(Re)apply stylesheet using current panel opacity and theme system."""
        logger.debug(f"🎨 Applying REPL styles with opacity: {self._panel_opacity:.3f}")
        
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            # Use theme system for consistent styling
            self._apply_themed_styles()
        else:
            # Fallback to legacy styling
            self._apply_legacy_styles()
    
    def _apply_themed_styles(self):
        """Apply styles using the theme system - NO opacity for UI components."""
        try:
            colors = self.theme_manager.current_theme
            
            # Generate themed style WITHOUT opacity (root panel stays opaque)
            style = StyleTemplates.get_repl_panel_style(colors)
            
            # Add input field styles
            input_style = StyleTemplates.get_input_field_style(colors)
            
            # Child element backgrounds - ALWAYS fully opaque for UI controls - use same as panel for consistency
            child_bg = colors.background_secondary
            
            # Combine styles using string formatting to avoid CSS syntax issues
            # UI components (input fields, etc.) stay fully opaque - remove unnecessary borders
            textedit_style = f"#repl-root QTextEdit {{ background-color: {child_bg}; color: {colors.text_primary}; border: none; border-radius: 5px; padding: 5px; selection-background-color: {colors.secondary}; selection-color: {colors.text_primary}; }}"
            lineedit_style = f"#repl-root QLineEdit {{ background-color: {child_bg}; color: {colors.text_primary}; border: none; border-radius: 3px; padding: 5px; selection-background-color: {colors.secondary}; selection-color: {colors.text_primary}; }}"
            lineedit_focus_style = f"#repl-root QLineEdit:focus {{ border: none; }}"
            plaintext_style = f"#repl-root QPlainTextEdit {{ background-color: {child_bg}; color: {colors.text_primary}; border: none; border-radius: 3px; padding: 5px; selection-background-color: {colors.secondary}; selection-color: {colors.text_primary}; }}"
            plaintext_focus_style = f"#repl-root QPlainTextEdit:focus {{ border: none; }}"
            
            # Add explicit tab frame transparency to override theme inheritance
            tab_frame_style = "#repl-root QFrame#tab_frame { background-color: rgba(0,0,0,0) !important; background: none !important; }"
            
            # Properly combine all styles (root style includes border-radius)
            combined_style = f"{style} {textedit_style} {lineedit_style} {lineedit_focus_style} {plaintext_style} {plaintext_focus_style}"
            
            
            self.setStyleSheet(combined_style)
            logger.debug("🎨 Applied themed REPL styles (no opacity for UI controls)")
            
        except Exception as e:
            logger.error(f"Failed to apply themed styles: {e}")
            # Fallback to legacy styles
            self._apply_legacy_styles()
    
    def _apply_legacy_styles(self):
        """Apply legacy hardcoded styles as fallback - NO opacity for UI controls."""
        # Root panel always opaque for UI controls
        panel_bg = "rgba(30, 30, 30, 1.0)"
        border_style = "border-radius: 10px 10px 0px 0px;"
            
        # UI elements always fully opaque (opacity only applied to output display separately)
        textedit_bg = "rgba(20, 20, 20, 1.0)"
        lineedit_bg = "rgba(40, 40, 40, 1.0)"
        
        logger.debug(f"🎨 Legacy CSS colors generated (no opacity for UI controls):")
        logger.debug(f"  📦 Panel background: {panel_bg}")
        logger.debug(f"  📝 Text area background: {textedit_bg}")
        logger.debug(f"  ⌨️  Input background: {lineedit_bg}")
        # Use simple string formatting to avoid CSS syntax issues - remove unnecessary borders
        root_style = f"#repl-root {{ background-color: {panel_bg}; {border_style} }}"
        textedit_fallback = f"#repl-root QTextEdit {{ background-color: {textedit_bg}; color: #f0f0f0; border: none; border-radius: 5px; padding: 5px; }}"
        lineedit_fallback = f"#repl-root QLineEdit {{ background-color: {lineedit_bg}; color: #ffffff; border: none; border-radius: 3px; padding: 5px; }}"
        lineedit_focus_fallback = "#repl-root QLineEdit:focus { border: none; }"
        plaintext_fallback = f"#repl-root QPlainTextEdit {{ background-color: {lineedit_bg}; color: #ffffff; border: none; border-radius: 3px; padding: 5px; }}"
        plaintext_focus_fallback = "#repl-root QPlainTextEdit:focus { border: none; }"
        
        self.setStyleSheet(f"{root_style} {textedit_fallback} {lineedit_fallback} {lineedit_focus_fallback} {plaintext_fallback} {plaintext_focus_fallback}")

    def set_panel_opacity(self, opacity: float):
        """Set the frame (panel) background opacity only.

        Args:
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque) for panel background.
        """
        logger.info(f"🎨 REPL panel opacity change requested: {opacity:.3f}")
        
        if not isinstance(opacity, (float, int)):
            logger.error(f"✗ Invalid opacity type: {type(opacity)} (expected float/int)")
            return
            
        old_val = self._panel_opacity
        new_val = max(0.0, min(1.0, float(opacity)))
        
        if abs(new_val - self._panel_opacity) < 0.001:
            logger.debug(f"🎨 Opacity unchanged: {old_val:.3f} -> {new_val:.3f} (difference < 0.001)")
            return
            
        logger.info(f"🎨 Applying panel opacity: {old_val:.3f} -> {new_val:.3f}")
        self._panel_opacity = new_val

        # CRITICAL: Apply window-level opacity for true transparency
        parent_window = self.window()
        if parent_window:
            parent_window.setWindowOpacity(new_val)
            logger.debug(f"   ✅ Set window opacity to {new_val:.3f}")

        self._apply_styles()

        # Also update the output display style with new opacity
        if hasattr(self, 'output_display'):
            self._style_output_display()

        # Ensure tab frame transparency after opacity changes (which may trigger style reapplication)
        self._schedule_tab_transparency_enforcement()

        logger.info(f"✓ REPL panel opacity applied successfully: {new_val:.3f}")
        
        # Force immediate visual update by refreshing all themed components
        self._refresh_opacity_dependent_styles()
    
    def _apply_startup_opacity(self):
        """Apply opacity settings immediately after widget initialization.

        This method ensures opacity takes immediate visual effect on startup
        by forcing a style refresh after all components are initialized.
        """
        try:
            # CRITICAL: Apply window-level opacity for true transparency at startup
            parent_window = self.window()
            if parent_window:
                parent_window.setWindowOpacity(self._panel_opacity)
                logger.debug(f"   ✅ Set startup window opacity to {self._panel_opacity:.3f}")

            # Force immediate application of opacity to output display
            if hasattr(self, 'output_display'):
                self._style_output_display()

            # Apply opacity to command input if needed
            if hasattr(self, 'command_input'):
                self._style_command_input_with_opacity()

            # Apply opacity to title frame
            if hasattr(self, 'title_frame'):
                self._style_title_frame_with_opacity()

            logger.info(f"🎨 Startup opacity applied: {self._panel_opacity:.3f} ({int(self._panel_opacity * 100)}%)")
        except Exception as e:
            logger.error(f"Failed to apply startup opacity: {e}")
    
    def _refresh_opacity_dependent_styles(self):
        """Refresh all styles that depend on opacity settings."""
        try:
            # Re-apply output display styling with current opacity
            if hasattr(self, 'output_display'):
                self._style_output_display()
                
            # Re-apply command input styling
            if hasattr(self, 'command_input'):
                self._style_command_input_with_opacity()
                
            # Re-apply title frame styling
            if hasattr(self, 'title_frame'):
                self._style_title_frame_with_opacity()
                
            logger.debug("Refreshed all opacity-dependent styles")
        except Exception as e:
            logger.warning(f"Failed to refresh opacity-dependent styles: {e}")
    
    def _style_command_input_with_opacity(self):
        """Apply command input styling - ALWAYS fully opaque."""
        try:
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                colors = self.theme_manager.current_theme
                
                # Command input ALWAYS fully opaque for UI clarity
                input_bg = colors.background_secondary
                
                self.command_input.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: {input_bg} !important;
                        color: {colors.text_primary};
                        border: 2px solid {colors.border_secondary};
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-size: 13px;
                        selection-background-color: {colors.primary};
                        selection-color: {colors.background_primary};
                    }}
                    QLineEdit:focus {{
                        border-color: {colors.border_focus};
                        background-color: {input_bg} !important;
                    }}
                """)
            else:
                # Fallback styling without theme system - ALWAYS fully opaque
                input_bg = "rgba(40, 40, 40, 1.0)"
                self.command_input.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: {input_bg} !important;
                        color: #ffffff;
                        border: 2px solid rgba(255, 255, 255, 0.3);
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-size: 13px;
                    }}
                    QLineEdit:focus {{
                        border-color: #FFA500;
                        background-color: {input_bg} !important;
                    }}
                """)
        except Exception as e:
            logger.warning(f"Failed to style command input: {e}")
    
    def _style_title_frame_with_opacity(self):
        """Apply title frame styling - ALWAYS fully opaque."""
        try:
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                colors = self.theme_manager.current_theme
                
                # Title frame ALWAYS fully opaque for UI clarity
                frame_bg = colors.background_tertiary
                
                self.title_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {frame_bg} !important;
                        border: none;
                        border-radius: 4px;
                        padding: 0px;
                    }}
                    QLabel {{
                        color: {colors.text_primary};
                        font-weight: bold;
                    }}
                """)
            else:
                # Fallback styling - ALWAYS fully opaque
                frame_bg = "rgba(40, 40, 40, 1.0)"
                self.title_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {frame_bg} !important;
                        border: none;
                        border-radius: 5px;
                        margin: 0px;
                        padding: 4px;
                    }}
                """)
        except Exception as e:
            logger.warning(f"Failed to style title frame: {e}")
    
    def refresh_fonts(self):
        """Refresh fonts from font service when settings change."""
        try:
            logger.info("🔤 REPL: Starting font refresh from settings...")
            
            # Clear font service cache to get latest settings
            font_service.clear_cache()
            logger.debug("  ✓ Font service cache cleared")
            
            # Debug: Check what fonts we're getting from settings
            try:
                ai_font_config = font_service.get_font_config('ai_response')
                user_font_config = font_service.get_font_config('user_input')
                code_font_config = font_service.get_font_config('code_snippets')
                logger.info(f"  📝 AI Response font: {ai_font_config}")
                logger.info(f"  📝 User Input font: {user_font_config}")  
                logger.info(f"  📝 Code Snippets font: {code_font_config}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not get font configs for debugging: {e}")
            
            # Update input font (user input font)
            input_font = font_service.create_qfont('user_input')
            self.command_input.setFont(input_font)
            logger.debug("  ✓ Input font updated")
            
            # Clear markdown renderer cache so it uses new fonts and update theme
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.clear_cache()
                self._markdown_renderer.update_theme()
                logger.debug("  ✓ Markdown renderer cache cleared and theme updated")
            
            # Re-apply output display styling to ensure font colors are correct
            self._style_output_display()
            logger.debug("  ✓ Output display styling reapplied")
            
            # Re-render existing content with new fonts
            self._refresh_existing_output()
            logger.debug("  ✓ Existing output re-rendered")
            
            logger.info("🔤 ✓ Fonts refreshed from settings - ALL STEPS COMPLETED")
            
        except Exception as e:
            logger.error(f"Failed to refresh fonts: {e}")
            import traceback
            logger.error(f"Font refresh error details: {traceback.format_exc()}")
    
    def _refresh_existing_output(self):
        """Re-render all existing output with current theme colors - preserves content."""
        try:
            # Clear markdown renderer cache to ensure fresh colors
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.clear_cache()
                self._markdown_renderer.update_theme()
            
            # MixedContentDisplay theme colors are already updated in _style_output_display()
            # Just ensure theme colors are applied to the display
            if hasattr(self, 'output_display'):
                self._style_output_display()
            
            logger.debug("Existing output refreshed with new theme colors")
            
        except Exception as e:
            logger.error(f"Failed to refresh existing output: {e}")
    
    
    def clear_output(self):
        """Clear the output display and reset markdown renderer cache."""
        self.output_display.clear()
        
        # Clear markdown renderer cache to free memory
        if hasattr(self, '_markdown_renderer'):
            self._markdown_renderer.clear_cache()
    
    def _set_processing_mode(self, processing: bool):
        """Set the UI to processing mode with spinner or normal mode."""
        try:
            if processing:
                # get current width
                current_width = self.prompt_label.width()
                # set min width
                self.prompt_label.setMinimumWidth(current_width)
                # Show spinner in prompt label
                self.prompt_label.setText("⠋")  # Spinner character
                self._style_prompt_label(normal=False, processing=True)
                
                # Optionally add animation (requires QTimer)
                if not hasattr(self, '_spinner_timer'):
                    from PyQt6.QtCore import QTimer
                    self._spinner_timer = QTimer()
                    self._spinner_timer.timeout.connect(self._update_spinner)
                    self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                    self._spinner_index = 0
                
                self._spinner_timer.start(100)  # Update every 100ms
                
                # Hide send button, show stop button
                if hasattr(self, 'send_button'):
                    self.send_button.setVisible(False)
                if hasattr(self, 'stop_button'):
                    self.stop_button.setVisible(True)
            else:
                # Stop spinner animation and restore normal prompt
                if hasattr(self, '_spinner_timer'):
                    self._spinner_timer.stop()
                
                self.prompt_label.setText(">>>")
                self._style_prompt_label(normal=True, processing=False)
                
                # Show send button, hide stop button
                if hasattr(self, 'send_button'):
                    self.send_button.setVisible(True)
                if hasattr(self, 'stop_button'):
                    self.stop_button.setVisible(False)
        except Exception as e:
            logger.error(f"Failed to set processing mode: {e}")
    
    def _update_spinner(self):
        """Update the spinner animation."""
        try:
            if hasattr(self, '_spinner_chars') and hasattr(self, '_spinner_index'):
                self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
                self.prompt_label.setText(self._spinner_chars[self._spinner_index])
                # ensure middle of spinner is aligned
                self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception as e:
            logger.error(f"Failed to update spinner: {e}")
    
    def eventFilter(self, obj, event):
        """Event filter for command input navigation and link detection."""
        # Handle link clicks and hover in output display
        if hasattr(self, 'output_display') and obj == self.output_display:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Use the robust link handler for click detection
                    if hasattr(self, 'link_handler'):
                        if self.link_handler.handle_mouse_click(event.pos()):
                            return True  # Event handled
            
            elif event.type() == event.Type.MouseMove:
                # Use the robust link handler for cursor changes
                if hasattr(self, 'link_handler'):
                    self.link_handler.handle_mouse_move(event.pos())
                    
                return False  # Allow normal processing
        
        # Handle command input keyboard events
        elif hasattr(self, 'command_input') and obj == self.command_input and event.type() == event.Type.KeyPress:
            key_event = event
            
            # Handle Enter key - submit on Enter, newline on Shift+Enter
            if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                if key_event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    # Shift+Enter: Insert newline and trigger height update
                    logger.debug("🔥 Shift+Enter pressed - inserting newline")
                    cursor = self.command_input.textCursor()
                    cursor.insertText('\n')
                    self.command_input.setTextCursor(cursor)
                    # Trigger height update after newline is inserted
                    QTimer.singleShot(10, self._on_input_text_changed)
                    logger.debug("🔥 Shift+Enter processed - height update scheduled")
                    return True
                else:
                    # Enter alone: Submit command
                    self._on_command_entered()
                    return True
            
            # Handle history navigation (only when at boundaries AND no text selection)
            elif key_event.key() == Qt.Key.Key_Up:
                cursor = self.command_input.textCursor()
                # Only navigate history if:
                # 1. On first line (blockNumber == 0)
                # 2. At beginning of line or cursor at start of document
                if (cursor.blockNumber() == 0 and 
                    (cursor.positionInBlock() == 0 or cursor.position() == 0)):
                    self._navigate_history(-1)
                    return True
                # Otherwise allow normal up arrow navigation
                return False
            
            # Down arrow - next command (only at end of last line)
            elif key_event.key() == Qt.Key.Key_Down:
                cursor = self.command_input.textCursor()
                document = self.command_input.document()
                last_block = document.blockCount() - 1
                # Only navigate history if:
                # 1. On last line
                # 2. At end of line or cursor at end of document
                if (cursor.blockNumber() == last_block and
                    (cursor.positionInBlock() == cursor.block().length() - 1 or 
                     cursor.position() == document.characterCount() - 1)):
                    self._navigate_history(1)
                    return True
                # Otherwise allow normal down arrow navigation
                return False
        
        return super().eventFilter(obj, event)
    
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts."""
        # Ctrl+F to open search
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._toggle_search()
            return
        
        # Ctrl+U to toggle file browser
        elif event.key() == Qt.Key.Key_U and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._toggle_file_browser()
            return
        
        # Escape to close search if open
        elif event.key() == Qt.Key.Key_Escape and self.search_frame.isVisible():
            self._close_search()
            return
        
        # Escape to close file browser if open
        elif (event.key() == Qt.Key.Key_Escape and 
              hasattr(self, 'file_browser_bar') and 
              self.file_browser_bar.isVisible()):
            self._close_file_browser()
            return
        
        super().keyPressEvent(event)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for file drops."""
        try:
            if event.mimeData().hasUrls():
                # Check if any URLs point to files
                valid_files = []
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        import os
                        if os.path.isfile(file_path):
                            valid_files.append(file_path)
                
                if valid_files:
                    event.acceptProposedAction()
                    logger.debug(f"Drag enter accepted for {len(valid_files)} files")
                    return
            
            event.ignore()
        except Exception as e:
            logger.error(f"Error in dragEnterEvent: {e}")
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events."""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception as e:
            logger.error(f"Error in dragMoveEvent: {e}")
            event.ignore()
    
    def dropEvent(self, event):
        """Handle file drop events."""
        try:
            if not event.mimeData().hasUrls():
                event.ignore()
                return
            
            # Extract file paths
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    import os
                    if os.path.isfile(file_path):
                        file_paths.append(file_path)
            
            if file_paths:
                logger.info(f"📁 Files dropped: {len(file_paths)} files")
                
                # Show file browser bar if hidden
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.show()
                
                # Process dropped files
                self._process_uploaded_files(file_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
                
        except Exception as e:
            logger.error(f"Error in dropEvent: {e}")
            event.ignore()
    
    def _navigate_history(self, direction: int):
        """Navigate through command history."""
        if not self.command_history:
            return
        
        # Save current input if starting to navigate
        if self.history_index == -1:
            self.current_input = self.command_input.toPlainText()
        
        # Update index
        self.history_index += direction
        
        # Clamp index
        if self.history_index < -1:
            self.history_index = -1
        elif self.history_index >= len(self.command_history):
            self.history_index = len(self.command_history) - 1
        
        # Update input
        if self.history_index == -1:
            self.command_input.setPlainText(self.current_input)
        else:
            self.command_input.setPlainText(self.command_history[self.history_index])
    
    # Enhanced event handlers for conversation management
    @pyqtSlot(str)
    def _on_conversation_selected(self, display_name: str):
        """Handle conversation selection from dropdown."""
        # Check if conversation selector exists (it may not be implemented yet)
        if not hasattr(self, 'conversation_selector'):
            logger.debug("Conversation selector not available - ignoring selection")
            return
            
        current_index = self.conversation_selector.currentIndex()
        if current_index < 0:
            return
        
        conversation_id = self.conversation_selector.itemData(current_index)
        
        if not conversation_id:  # New conversation selected
            # Use the working _start_new_conversation approach instead of broken _create_new_conversation
            self._start_new_conversation(save_current=False)
            return
        
        # Find conversation in list
        selected_conversation = None
        for conv in self.conversations_list:
            if conv.id == conversation_id:
                selected_conversation = conv
                break
        
        if selected_conversation:
            self._switch_to_conversation(selected_conversation)
        else:
            logger.warning(f"Conversation not found: {conversation_id}")
    
    def _switch_to_conversation(self, conversation: Conversation):
        """Switch to a different conversation."""
        if self.current_conversation and self.current_conversation.id == conversation.id:
            return  # Already active
        
        logger.info(f"🔄 Switching to conversation: {conversation.title}")
        
        # CRITICAL FIX: Hide current conversation's files BEFORE switching
        if hasattr(self, 'file_browser_bar') and self.file_browser_bar and self.current_conversation:
            self.file_browser_bar.hide_files_for_conversation(self.current_conversation.id)
            logger.info(f"📁 Hidden files for conversation {self.current_conversation.id[:8]}...")
        
        # Clear internal file tracking
        if hasattr(self, '_uploaded_files'):
            self._uploaded_files.clear()
        
        # Save current conversation state if needed and mark as inactive
        if self.current_conversation:
            self.idle_detector.reset_activity(conversation.id)
        # Set new conversation as active (this will automatically mark others as pinned)
        if self.conversation_manager:
            success = self.conversation_manager.set_conversation_active_simple(conversation.id)
            if success:
                logger.info(f"✓ Set conversation {conversation.id[:8]}... as active (enforcing uniqueness)")
                # Update local conversation status
                conversation.status = ConversationStatus.ACTIVE
                # Refresh the conversation selector UI
                self._refresh_conversation_selector()
            else:
                logger.error(f"✗ Failed to set conversation {conversation.id[:8]}... as active")
        
        # Switch to new conversation
        self.current_conversation = conversation
        self._update_status_label(conversation)
        
        # Associate conversation with current tab if tab system is available and not already associated
        if hasattr(self, 'tab_manager') and self.tab_manager:
            active_tab = self.tab_manager.get_active_tab()
            if active_tab and not active_tab.conversation_id:
                self.tab_manager.associate_conversation_with_tab(
                    active_tab.tab_id, 
                    conversation.id, 
                    conversation.title
                )
                logger.info(f"✓ Associated loaded conversation {conversation.id} with tab {active_tab.tab_id}")
        
        # Start autosave timer for the new conversation
        self._start_autosave_timer()
        
        # Load conversation messages in output
        self._load_conversation_messages(conversation)
        
        # CRITICAL: Update AI service context when switching conversations
        if self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                logger.info(f"🔄 Updating AI service context for conversation switch")
                
                # Use the proper method to set conversation and load context
                ai_service.set_current_conversation(conversation.id)
                
                logger.info(f"✓ AI service context updated for conversation: {conversation.id}")
        
        # Reset idle detector for new conversation
        self.idle_detector.reset_activity(conversation.id)
        
        # Sync tab title with conversation
        self._sync_tab_with_conversation()
        
        # Emit signal for external components
        self.conversation_changed.emit(conversation.id)
        
        logger.info(f"✓ Switched to conversation: {conversation.title}")
    
    def _create_new_conversation(self):
        """Create a new conversation."""
        if not self.conversation_manager:
            logger.warning("Cannot create conversation - manager not available")
            return
        
        logger.info("🆕 Creating new conversation...")
        
        # Create new conversation asynchronously
        import asyncio
        
        async def create_async():
            try:
                # Generate a default title
                title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                conversation = await self.conversation_manager.create_conversation(
                    title=title,
                    initial_message="New conversation started"
                )
                
                if conversation:
                    # Add to conversations list
                    self.conversations_list.insert(0, conversation)
                    
                    # Update selector only if it exists
                    if hasattr(self, 'conversation_selector'):
                        display_name = f"{self._get_status_icon(conversation)} {conversation.title}"
                        self.conversation_selector.insertItem(0, display_name, conversation.id)
                        self.conversation_selector.setCurrentIndex(0)
                    
                    # Switch to new conversation
                    self._switch_to_conversation(conversation)
                    
                    self.append_output(f"✨ Created new conversation: {conversation.title}", "system")
                    logger.info(f"✓ New conversation created: {conversation.id}")
                
            except Exception as e:
                logger.error(f"✗ Failed to create conversation: {e}")
                self.append_output("✗ Failed to create new conversation", "error")
        
        # Run async task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task if loop is already running
                asyncio.create_task(create_async())
            else:
                loop.run_until_complete(create_async())
        except Exception as e:
            logger.error(f"Failed to run async conversation creation: {e}")
    
    def _load_conversation_messages(self, conversation: Conversation):
        """Load conversation messages into output display with proper rendering."""
        self.clear_output()
        
        # CRITICAL FIX: Ensure theme colors are set before loading content
        # This fixes the issue where existing conversation content doesn't update colors on theme switch
        if self.theme_manager and hasattr(self, 'output_display'):
            try:
                self._style_output_display()
                logger.debug("Applied theme colors before loading conversation messages")
            except Exception as e:
                logger.warning(f"Failed to apply theme colors before loading conversation: {e}")
        
        # Load conversation files and update file browser bar
        self._load_conversation_files(conversation.id)
        
        self.append_output(f"💬 Conversation: {conversation.title}", "system")
        
        if conversation.summary:
            self.append_output(f"💡 Summary: {conversation.summary.summary}", "info")
            if conversation.summary.key_topics:
                topics = ", ".join(conversation.summary.key_topics)
                self.append_output(f"📝 Topics: {topics}", "info")
        
        self.append_output("-" * 50, "system")
        
        # Load messages with proper rendering
        for message in conversation.messages:
            if message.role == MessageRole.SYSTEM:
                continue  # Skip system messages in display
            
            if message.role == MessageRole.USER:
                # User messages - show with timestamp and icon
                timestamp = message.timestamp.strftime("%m/%d %H:%M")
                self.append_output(f"[{timestamp}] 👤 You:", "input")
                # Render the actual message content preserving markdown
                self.append_output(message.content, "input")
                
            elif message.role == MessageRole.ASSISTANT:
                # AI messages - show with timestamp and proper markdown rendering
                timestamp = message.timestamp.strftime("%m/%d %H:%M")
                self.append_output(f"[{timestamp}] 🤖 AI:", "response")
                # Render the AI response with full markdown support (including code blocks)
                self.append_output(message.content, "response")
            
            # Add spacing between messages
            self.append_output("", "normal")
        
        if not conversation.messages:
            self.append_output("🎆 Start a new conversation!", "info")
    
    @pyqtSlot()
    def _on_export_requested(self):
        """Handle export request for current conversation."""
        if not self.current_conversation:
            self.append_output("⚠ No conversation selected for export", "warning")
            return
        
        logger.info(f"📤 Export requested for conversation: {self.current_conversation.id}")
        self.export_requested.emit(self.current_conversation.id)
    
    @pyqtSlot(str)
    def _on_idle_detected(self, conversation_id: str):
        """Handle idle detection for background summarization."""
        if not self.conversation_manager or not conversation_id:
            return
        
        # Check if conversation needs summarization
        try:
            # Check current conversation
            if self.current_conversation and self.current_conversation.id == conversation_id:
                # Skip if no messages
                if self.current_conversation.get_message_count() == 0:
                    logger.debug(f"⏭️ Skipping summarization for {conversation_id}: No messages")
                    return
                
                # Skip if already has a summary (title is set and not default)
                if (hasattr(self.current_conversation, 'title') and 
                    self.current_conversation.title and 
                    not self.current_conversation.title.startswith('New Conversation')):
                    logger.debug(f"⏭️ Skipping summarization for {conversation_id}: Already has title/summary")
                    return
                
                # Track messages since last summary
                MIN_MESSAGES_FOR_SUMMARY = 2  # Minimum messages needed for a summary
                if self.current_conversation.get_message_count() < MIN_MESSAGES_FOR_SUMMARY:
                    logger.debug(f"⏭️ Skipping summarization for {conversation_id}: Only {self.current_conversation.get_message_count()} messages (min: {MIN_MESSAGES_FOR_SUMMARY})")
                    return
                    
        except Exception as e:
            logger.error(f"Failed to check conversation before summarization: {e}")
            return
        
        # Add to summarization queue if not already present
        if conversation_id not in self.summarization_queue:
            self.summarization_queue.append(conversation_id)
            logger.info(f"🕰️ Idle detected - queued conversation for summarization: {conversation_id}")
        
        # Start background summarization if not already running
        if not self.is_summarizing:
            self._start_background_summarization()
    
    def _start_background_summarization(self):
        """Start background summarization process."""
        if not self.summarization_queue or self.is_summarizing:
            return
        
        self.is_summarizing = True
        
        # Show progress indicator (with safety check)
        if hasattr(self, 'summary_progress'):
            self.summary_progress.setVisible(True)
        if hasattr(self, 'summary_notification'):
            self.summary_notification.setText("🧪 Generating summary...")
            self.summary_notification.setVisible(True)
        
        logger.info("🔄 Starting background summarization...")
        
        # Process first conversation in queue asynchronously
        conversation_id = self.summarization_queue[0]
        
        # Start async summarization without blocking the UI
        QTimer.singleShot(0, lambda: self._run_summarization_async(conversation_id))
    
    def _run_summarization_async(self, conversation_id: str):
        """Run summarization asynchronously without blocking the UI."""
        async def async_summarization():
            try:
                if hasattr(self.conversation_manager, 'conversation_service'):
                    summary_service = self.conversation_manager.conversation_service.summary_service
                    
                    # Generate summary - this is already async
                    success = await summary_service.generate_summary(conversation_id)
                    
                    # Call completion handler on main thread
                    QTimer.singleShot(0, lambda: self._on_summarization_finished(conversation_id, success))
                else:
                    QTimer.singleShot(0, lambda: self._on_summarization_finished(conversation_id, False))
                    
            except Exception as e:
                logger.error(f"Async summarization error: {e}")
                QTimer.singleShot(0, lambda: self._on_summarization_finished(conversation_id, False))
        
        # Run the async function using asyncio
        try:
            import asyncio
            
            # Try to get existing event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task if loop is already running
                    asyncio.create_task(async_summarization())
                else:
                    # Run until complete if loop is not running
                    loop.run_until_complete(async_summarization())
            except RuntimeError:
                # No event loop exists, create a new one
                asyncio.run(async_summarization())
                
        except Exception as e:
            logger.error(f"Failed to run async summarization: {e}")
            self._on_summarization_finished(conversation_id, False)
    
    @pyqtSlot(str, bool)
    def _on_summarization_finished(self, conversation_id: str, success: bool):
        """Handle completion of background summarization."""
        # Remove from queue
        if conversation_id in self.summarization_queue:
            self.summarization_queue.remove(conversation_id)
        
        if success:
            if hasattr(self, 'summary_notification'):
                self.summary_notification.setText("✓ Summary generated")
            logger.info(f"✓ Summary generated for conversation: {conversation_id}")
            
            # Update conversation data if it's the current one
            if self.current_conversation and self.current_conversation.id == conversation_id:
                self._refresh_current_conversation()
        else:
            if hasattr(self, 'summary_notification'):
                self.summary_notification.setText("✗ Summary failed")
            logger.warning(f"✗ Summary generation failed for conversation: {conversation_id}")
        
        # Hide progress after delay
        QTimer.singleShot(3000, self._hide_summary_notification)
        
        # Process next item in queue
        self.is_summarizing = False
        if self.summarization_queue:
            QTimer.singleShot(1000, self._start_background_summarization)
    
    def _hide_summary_notification(self):
        """Hide summary notification and progress bar."""
        if hasattr(self, 'summary_progress'):
            self.summary_progress.setVisible(False)
        if hasattr(self, 'summary_notification'):
            self.summary_notification.setVisible(False)
    
    def _refresh_current_conversation(self):
        """Refresh current conversation data from database."""
        if not self.current_conversation or not self.conversation_manager:
            return
        
        async def refresh_async():
            try:
                updated_conv = await self.conversation_manager.get_conversation(
                    self.current_conversation.id
                )
                if updated_conv:
                    self.current_conversation = updated_conv
                    self._update_status_label(updated_conv)
                    
                    # Update conversation in list
                    for i, conv in enumerate(self.conversations_list):
                        if conv.id == updated_conv.id:
                            self.conversations_list[i] = updated_conv
                            break
            except Exception as e:
                logger.error(f"Failed to refresh conversation: {e}")
        
        # Run refresh asynchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(refresh_async())
            else:
                loop.run_until_complete(refresh_async())
        except Exception as e:
            logger.error(f"Failed to run async conversation refresh: {e}")
    
    def _on_command_entered(self):
        """Handle command entry."""
        command = self.command_input.toPlainText().strip()
        
        if not command:
            return
        
        # Add to history
        if not self.command_history or command != self.command_history[-1]:
            self.command_history.append(command)
        
        # Reset history navigation
        self.history_index = -1
        self.current_input = ""
                
        # Display command in output with better separation
        self.append_output(f"👤 **You:**\n{command}", "input")
        self.append_output("", "normal")  # Add spacing
        
        # Clear input
        self.command_input.clear()
        
        # Process command
        self._process_command(command)
        
        # Emit signal for external processing
        self.command_entered.emit(command)
    
    def _is_debug_mode_enabled(self) -> bool:
        """Check if debug mode is enabled in advanced settings."""
        try:
            if _global_settings:
                # Check new debug commands setting first
                debug_commands_enabled = _global_settings.get("advanced.enable_debug_commands", False)
                if debug_commands_enabled:
                    return True
                
                # Fallback to log level for backward compatibility
                log_mode = _global_settings.get("advanced.log_level", "Standard")
                return (log_mode == "Detailed")
        except Exception:
            pass
        return False

    def _process_command(self, command: str):
        """Process built-in commands."""
        command_lower = command.lower()
        
        if command_lower == "help":
            debug_enabled = self._is_debug_mode_enabled()
            
            self.append_output("Available commands:", "info")
            
            # Basic commands (always shown)
            self.append_output("  help     - Show this help message", "info")
            self.append_output("  clear    - Clear the output display", "info")
            self.append_output("  history  - Show command history", "info")
            self.append_output("  resend   - Resend the last failed message", "info")
            self.append_output("  exit     - Minimize to system tray", "info")
            
            # Debug commands (only shown when debug mode enabled)
            if debug_enabled:
                self.append_output("", "info")  # Empty line separator
                self.append_output("Debug commands:", "info")
                self.append_output("  quit     - Exit the application", "info")
                self.append_output("  context  - Show AI context status (debug)", "info")
                self.append_output("  render_stats - Show markdown rendering statistics", "info")
                self.append_output("  test_markdown - Test markdown rendering with examples", "info")
                self.append_output("  test_themes - Test all theme switching and rendering", "info")
            
            self.append_output("\nAny other input will be sent to the AI assistant.", "info")
        
        elif command_lower == "clear":
            self.clear_output()
            self.append_output("Output cleared", "system")
        
        elif command_lower == "history":
            if self.command_history:
                self.append_output("Command history:", "info")
                for i, cmd in enumerate(self.command_history[-10:], 1):
                    self.append_output(f"  {i}. {cmd}", "info")
            else:
                self.append_output("No command history", "info")
        
        elif command_lower == "exit":
            self.minimize_requested.emit()
        
        elif command_lower == "quit":
            if self._is_debug_mode_enabled():
                # Would need to connect to app quit
                self.append_output("Use system tray menu to quit application", "warning")
            else:
                self.append_output("❌ Unknown command. Type 'help' to see available commands.", "warning")
        
        elif command_lower == "context":
            if self._is_debug_mode_enabled():
                # Debug command to show AI context status
                self._show_context_status()
            else:
                self.append_output("❌ Unknown command. Type 'help' to see available commands.", "warning")
        
        elif command_lower == "render_stats":
            if self._is_debug_mode_enabled():
                # Debug command to show render statistics
                self._show_render_stats()
            else:
                self.append_output("❌ Unknown command. Type 'help' to see available commands.", "warning")
        
        elif command_lower == "test_markdown":
            if self._is_debug_mode_enabled():
                # Debug command to test markdown rendering
                self._test_markdown_rendering()
            else:
                self.append_output("❌ Unknown command. Type 'help' to see available commands.", "warning")
        
        elif command_lower == "test_themes":
            if self._is_debug_mode_enabled():
                # Debug command to test all theme switching
                # Prevent recursive theme switching during automated theme changes
                app = QApplication.instance()
                if app and app.property("theme_switching"):
                    self.append_output("⚠ Theme testing disabled during theme switching to prevent recursion", "warning")
                    return
                self._test_all_themes()
            else:
                self.append_output("❌ Unknown command. Type 'help' to see available commands.", "warning")
        
        elif command_lower == "resend":
            # Resend the last failed message
            if self.last_failed_message:
                self.append_output(f"🔄 **Resending last message...**", "system")
                self.append_output("", "system")  # Add spacing
                self._send_to_ai(self.last_failed_message)
            else:
                self.append_output("❌ No failed message to resend", "warning")
        
        else:
            # Send to AI service
            self._send_to_ai(command)
            
            # Trigger autosave after user sends a message
            self._trigger_autosave_soon()
    
    def append_output(self, text: str, style: str = "normal", force_plain: bool = False):
        """
        Append text to the output display with advanced markdown rendering and styling.

        Features:
        - Full markdown support (headers, emphasis, code blocks, lists, links, tables)
        - Preserves message type color coding
        - Graceful fallback to plain text rendering
        - Performance optimized for long conversations
        - Code snippets with solid backgrounds and proper formatting

        Args:
            text: Text to append (supports markdown formatting)
            style: Style type for color coding (normal, input, response, system, info, warning, error)
            force_plain: If True, bypasses markdown processing for plain text rendering
        """
        # Defensive check: if no output_display (no tabs yet), skip silently
        if not self.output_display:
            logger.debug(f"Skipping output append - no tabs created yet: {text[:50]}")
            return

        if not hasattr(self, '_markdown_renderer'):
            self._markdown_renderer = MarkdownRenderer(self.theme_manager)

        # Render content with markdown support
        try:
            if force_plain:
                # Plain text rendering - use add_plain_text method
                self.output_display.add_plain_text(text, style)
            else:
                html_content = self._markdown_renderer.render(text, style, force_plain)
                # Use the MixedContentDisplay method to add HTML content with code block extraction
                self.output_display.add_html_content(html_content, style)

            # Performance optimization: limit content size for very long conversations
            self._manage_document_size()

        except Exception as e:
            logger.error(f"Error rendering output: {e}")
            # Fallback to plain text rendering - check again if output_display exists
            if self.output_display:
                self.output_display.add_plain_text(str(text), style)
    
    def _manage_document_size(self):
        """
        Manage document size for performance in long conversations.
        Uses MixedContentDisplay's built-in content management.
        """
        # Defensive check: if no output_display, skip
        if not self.output_display:
            return

        # Use MixedContentDisplay's built-in content size management
        self.output_display.manage_content_size(max_widgets=500)

    def clear_output(self):
        """Clear the output display and reset markdown renderer cache."""
        # Defensive check: if no output_display (no tabs yet), skip
        if not self.output_display:
            logger.debug("Skipping clear_output - no tabs created yet")
            return

        self.output_display.clear()

        # Clear markdown renderer cache to free memory
        if hasattr(self, '_markdown_renderer'):
            self._markdown_renderer.clear_cache()
    
    def append_plain_output(self, text: str, style: str = "normal"):
        """
        Append text with plain text rendering (bypasses markdown processing).
        Useful for performance-critical scenarios or when markdown formatting should be ignored.
        
        Args:
            text: Plain text to append
            style: Style type for color coding
        """
        self.append_output(text, style, force_plain=True)
    
    def get_render_stats(self) -> Dict[str, Any]:
        """
        Get rendering performance statistics for debugging and monitoring.
        
        Returns:
            Dictionary containing render statistics
        """
        stats = {
            'content_widgets': len(self.output_display.content_widgets) if self.output_display and hasattr(self.output_display, 'content_widgets') else 0,
            'content_height': self.output_display.get_content_height() if self.output_display and hasattr(self.output_display, 'get_content_height') else 0,
            'markdown_available': MARKDOWN_AVAILABLE
        }
        
        if hasattr(self, '_markdown_renderer'):
            stats.update(self._markdown_renderer.get_cache_stats())
        
        return stats
    
    def _show_context_status(self):
        """Show AI context status for debugging."""
        self.append_output("=== AI Context Status ===", "info")
        
        # Current conversation info
        if self.current_conversation:
            self.append_output(f"Current Conversation: {self.current_conversation.title}", "info")
            self.append_output(f"Conversation ID: {self.current_conversation.id}", "info")
            if hasattr(self.current_conversation, 'messages'):
                self.append_output(f"Messages in DB: {len(self.current_conversation.messages)}", "info")
        else:
            self.append_output("Current Conversation: None", "warning")
        
        # AI service context info
        if self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                self.append_output(f"AI Service Available: Yes", "info")
                self.append_output(f"AI Current Conversation: {ai_service.get_current_conversation_id()}", "info")
                self.append_output(f"AI Context Messages: {len(ai_service.conversation.messages)}", "info")
                self.append_output(f"AI Max Messages: {ai_service.conversation.max_messages}", "info")
                
                # Show recent messages in context
                if ai_service.conversation.messages:
                    self.append_output("Recent AI Context Messages:", "info")
                    for i, msg in enumerate(ai_service.conversation.messages[-5:]):  # Last 5 messages
                        preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                        self.append_output(f"  {msg.role}: {preview}", "info")
                else:
                    self.append_output("AI Context: Empty", "warning")
            else:
                self.append_output("AI Service Available: No", "warning")
        else:
            self.append_output("Conversation Manager AI Service: Not Available", "warning")
        
        self.append_output("========================", "info")
    
    def _show_render_stats(self):
        """Show markdown rendering statistics for debugging."""
        self.append_output("=== Markdown Rendering Statistics ===", "info")
        
        try:
            stats = self.get_render_stats()
            
            self.append_output(f"Document Blocks: {stats['document_blocks']}", "info")
            self.append_output(f"Markdown Available: {stats['markdown_available']}", "info")
            
            if 'cache_size' in stats:
                self.append_output(f"Render Cache Size: {stats['cache_size']}/{stats['cache_max_size']}", "info")
                cache_efficiency = (stats['cache_size'] / stats['cache_max_size']) * 100 if stats['cache_max_size'] > 0 else 0
                self.append_output(f"Cache Efficiency: {cache_efficiency:.1f}%", "info")
            
            # Memory usage approximation
            if hasattr(self, '_markdown_renderer'):
                renderer = self._markdown_renderer
                if hasattr(renderer, '_render_cache'):
                    cache_memory = sum(len(str(content)) for content in renderer._render_cache.values())
                    self.append_output(f"Approximate Cache Memory: {cache_memory:,} characters", "info")
        
        except Exception as e:
            self.append_output(f"Error getting render stats: {e}", "error")
        
        self.append_output("==========================================", "info")
    
    def _test_markdown_rendering(self):
        """Test markdown rendering with comprehensive examples."""
        self.append_output("=== Markdown Rendering Test ===", "info")
        
        # Test different message types with markdown
        test_cases = [
            ("# Headers Test", "response"),
            ("## Secondary Header\n### Tertiary Header", "response"),
            ("**Bold text** and *italic text*", "response"),
            ("Here's some `inline code` in a sentence", "response"),
            ("```python\ndef hello_world():\n    print('Hello, World!')\n```", "response"),
            ("- List item 1\n- List item 2\n  - Nested item", "response"),
            ("1. First item\n2. Second item\n3. Third item", "response"),
            ("> This is a blockquote\n> with multiple lines", "response"),
            ("[Link text](https://example.com)", "response"),
            ("| Column 1 | Column 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |", "response"),
            ("Mixed **bold** with `code` and *italic*", "response"),
        ]
        
        for i, (markdown_text, style) in enumerate(test_cases):
            self.append_output(f"Test {i+1}:", "info")
            self.append_output(markdown_text, style)
            if i < len(test_cases) - 1:
                self.append_output("", "system")  # Empty line separator
        
        # Test different styles
        self.append_output("Style variations:", "info")
        test_markdown = "**Bold**, *italic*, and `code` formatting"
        
        for style in ["input", "response", "system", "warning", "error"]:
            self.append_output(f"{style.upper()}: {test_markdown}", style)
        
        self.append_output("===============================", "info")
        
        # Performance test
        self.append_output("Performance test - rendering same content 10 times:", "info")
        import time
        start_time = time.time()
        
        perf_text = "# Performance Test\n**Bold** *italic* `code` [link](http://example.com)\n- Item 1\n- Item 2"
        for i in range(10):
            self.append_output(f"Iteration {i+1}: {perf_text}", "system")
        
        end_time = time.time()
        self.append_output(f"Performance test completed in {(end_time - start_time)*1000:.2f}ms", "info")
    
    def _test_all_themes(self):
        """Test switching through all available themes to verify rendering consistency."""
        if not (self.theme_manager and THEME_SYSTEM_AVAILABLE):
            self.append_output("⚠ Theme system not available for testing", "error")
            return
            
        # Additional safety check against recursive theme switching
        app = QApplication.instance()
        if app and app.property("theme_switching"):
            self.append_output("⚠ Theme testing aborted: detected ongoing theme switch to prevent recursion", "warning")
            return
        
        self.append_output("=== Theme Switching Test ===", "info")
        self.append_output("Testing all 26+ themes for rendering consistency...", "info")
        
        # Get all available themes
        available_themes = self.theme_manager.get_available_themes()
        current_theme = self.theme_manager.current_theme_name
        
        self.append_output(f"Found {len(available_themes)} themes to test", "info")
        self.append_output(f"Current theme: {current_theme}", "info")
        
        # Test content for consistency
        test_content = """# Theme Test Content
        
**Bold text** and *italic text* for visual testing.
        
Here's some `inline code` and a code block:

```python
def test_theme():
    print("Testing theme rendering")
    return True
```

- List item 1
- List item 2
  - Nested item

> This is a blockquote to test contrast

| Theme | Status | Contrast |
|-------|--------|----------|
| Testing | ✓ Good | High |

**Status colors:** Info, Warning, Error, Success
        """
        
        failed_themes = []
        themes_with_warnings = []
        
        # Test each theme
        for i, theme_name in enumerate(available_themes):
            try:
                self.append_output(f"\n--- Testing Theme {i+1}/{len(available_themes)}: {theme_name} ---", "system")
                
                # Switch to theme
                success = self.theme_manager.set_theme(theme_name)
                if not success:
                    failed_themes.append(theme_name)
                    self.append_output(f"❌ Failed to switch to theme: {theme_name}", "error")
                    continue
                
                # Test theme validation
                theme_obj = self.theme_manager.get_theme(theme_name)
                if theme_obj:
                    is_valid, issues = theme_obj.validate()
                    if not is_valid:
                        themes_with_warnings.append((theme_name, issues))
                        self.append_output(f"⚠ Theme validation issues: {', '.join(issues[:3])}", "warning")
                    else:
                        self.append_output(f"✓ Theme validation passed", "info")
                
                # Render test content
                self.append_output("Test rendering:", "info")
                self.append_output(test_content, "response")
                
                # Test different message types
                self.append_output("Message type tests:", "info")
                self.append_output("This is **input** formatting", "input")
                self.append_output("This is **system** formatting", "system")
                self.append_output("This is **warning** formatting", "warning")
                self.append_output("This is **error** formatting", "error")
                
                # Force UI update
                QApplication.processEvents()
                
            except Exception as e:
                failed_themes.append(theme_name)
                self.append_output(f"❌ Exception testing theme {theme_name}: {e}", "error")
        
        # Restore original theme
        try:
            self.theme_manager.set_theme(current_theme)
            self.append_output(f"\n✓ Restored original theme: {current_theme}", "info")
        except Exception as e:
            self.append_output(f"⚠ Failed to restore original theme: {e}", "warning")
        
        # Summary
        self.append_output("\n=== Theme Test Summary ===", "info")
        self.append_output(f"Total themes tested: {len(available_themes)}", "info")
        
        if failed_themes:
            self.append_output(f"❌ Failed themes ({len(failed_themes)}): {', '.join(failed_themes)}", "error")
        else:
            self.append_output("✓ All themes switched successfully", "info")
        
        if themes_with_warnings:
            self.append_output(f"⚠ Themes with validation warnings ({len(themes_with_warnings)}):", "warning")
            for theme_name, issues in themes_with_warnings:
                self.append_output(f"  - {theme_name}: {', '.join(issues[:2])}", "warning")
        
        success_count = len(available_themes) - len(failed_themes)
        self.append_output(f"Success rate: {success_count}/{len(available_themes)} ({(success_count/len(available_themes)*100):.1f}%)", "info")
        self.append_output("================================", "info")
    
    def _ensure_conversation_exists_for_message(self, message: str):
        """EDGE CASE FIX: Ensure conversation exists when user sends message after deleting all conversations."""
        if not self.conversation_manager:
            return
            
        try:
            # Check if we have ANY conversations at all (user may have deleted all)
            conv_service = self.conversation_manager.conversation_service
            if conv_service:
                # Count existing non-deleted conversations
                import asyncio
                import threading
                
                def check_conversation_count():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            # Use list_conversations to count existing conversations
                            conversations = new_loop.run_until_complete(
                                conv_service.repository.list_conversations(
                                    limit=1,  # Just need to check if ANY exist
                                    include_deleted=False  # Don't count deleted ones
                                )
                            )
                            return len(conversations)
                        finally:
                            new_loop.close()
                    except Exception as e:
                        logger.error(f"Error checking conversation count: {e}")
                        return -1  # Error state
                
                conversation_count = check_conversation_count()
                
                if conversation_count == 0:
                    logger.warning("⚠️ EDGE CASE: User has 0 conversations - auto-creating new conversation for message")
                    self._create_new_conversation_for_message(message)
                elif conversation_count == -1:
                    logger.error("❌ Error checking conversation count - forcing conversation creation")
                    self._create_new_conversation_for_message(message)
                else:
                    logger.debug(f"✓ {conversation_count} conversations exist - no auto-creation needed")
                    
        except Exception as e:
            logger.error(f"Error in _ensure_conversation_exists_for_message: {e}")
            # Fallback: try to create conversation anyway
            logger.info("🔄 Fallback: Creating conversation due to error checking count")
            self._create_new_conversation_for_message(message)
    
    def _send_to_ai(self, message: str):
        """Send message to AI service with conversation management."""
        # Store message for potential resend
        self.last_failed_message = message
        
        # EDGE CASE FIX: Check if user deleted all conversations and needs a new one
        if self.conversation_manager:
            self._ensure_conversation_exists_for_message(message)
        
        # Ensure we have an active conversation
        if not self.current_conversation and self.conversation_manager:
            logger.info("🆕 Auto-creating conversation for AI interaction")
            self._create_new_conversation_for_message(message)
            
            # User requested that tabs remain fresh - no automatic conversation association
            # Conversations are only loaded when explicitly requested through conversation dialog
            if TAB_SYSTEM_AVAILABLE and hasattr(self, 'tab_manager') and self.tab_manager:
                active_tab = self.tab_manager.get_active_tab()
                if active_tab:
                    # Keep tab title as "New Conversation" - don't associate with created conversations
                    logger.debug(f"Tab {active_tab.tab_id} remains fresh - no conversation association")
            
        # Ensure AI service has the correct conversation context from active tab
        active_conversation_id = self._get_safe_conversation_id()
        if active_conversation_id and self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                # Make sure the current conversation is set in the AI service
                current_ai_conversation = ai_service.get_current_conversation_id()
                if current_ai_conversation != active_conversation_id:
                    logger.debug(f"Syncing AI service to active tab conversation: {active_conversation_id[:8]}...")
                    ai_service.set_current_conversation(active_conversation_id)
        
        # Show spinner in prompt instead of "Processing with AI..." message
        self._set_processing_mode(True)
        
        # Reset idle detector
        self.idle_detector.reset_activity(
            self.current_conversation.id if self.current_conversation else None
        )
        
        # Disable input while processing
        self.command_input.setEnabled(False)
        
        # Create enhanced AI worker thread
        class EnhancedAIWorker(QObject):
            response_received = pyqtSignal(str, bool)  # response, success
            
            def __init__(self, message, conversation_manager, current_conversation, rag_session=None, conversation_id=None, file_browser_bar=None):
                super().__init__()
                self.message = message
                self.conversation_manager = conversation_manager
                self.current_conversation = current_conversation
                self.rag_session = rag_session
                self.conversation_id = conversation_id
                self.file_browser_bar = file_browser_bar  # For RAG optimization
            
            def run(self):
                try:
                    # Enhance message with file context if available
                    enhanced_message = self._enhance_message_with_file_context(self.message)
                    
                    # ALWAYS prefer conversation-aware AI service for context persistence
                    ai_service = None
                    if self.conversation_manager:
                        # Call get_ai_service() which will initialize it if needed
                        ai_service = self.conversation_manager.get_ai_service()
                        if ai_service:
                            logger.info("🎯 Using conversation-aware AI service for context persistence")
                        
                        if ai_service:
                            # Ensure current conversation context is set
                            conversation_context = {}
                            if self.current_conversation:
                                logger.debug(f"Setting AI service conversation context to: {self.current_conversation.id}")
                                ai_service.set_current_conversation(self.current_conversation.id)
                                conversation_context['conversation_id'] = self.current_conversation.id
                            elif hasattr(self, '_current_conversation_id') and self._current_conversation_id:
                                # Use internal conversation ID if available
                                conversation_context['conversation_id'] = self._current_conversation_id
                                ai_service.set_current_conversation(self._current_conversation_id)
                                logger.debug(f"Using internal conversation ID: {self._current_conversation_id}")
                            
                            # Send message with full conversation context for strict file isolation
                            result = ai_service.send_message(
                                enhanced_message, 
                                save_conversation=True,
                                conversation_context=conversation_context
                            )
                            
                            if result.get('success', False):
                                response_content = result['response']
                                logger.info(f"✓ AI response received with context (context size: {len(ai_service.conversation.messages)} messages)")
                                logger.info(f"🔍 AI WORKER SUCCESS - Response length: {len(response_content) if response_content else 0}")
                                logger.info(f"🔍 AI WORKER SUCCESS - Response content: '{response_content}'")
                                self.response_received.emit(response_content, True)
                            else:
                                raw_error = result.get('error', 'Unknown error')
                                logger.error(f"AI service error: {raw_error}")
                                
                                # Convert to user-friendly error message
                                friendly_error = self._get_user_friendly_error(str(raw_error))
                                self.response_received.emit(friendly_error, False)
                            return
                        else:
                            logger.warning("⚠  Conversation manager AI service not available")
                    
                    # Only fallback to basic AI service if conversation manager not available
                    logger.warning("🔄 Falling back to basic AI service (context may be lost)")
                    ai_service = self._get_basic_ai_service()
                    
                    if not ai_service or not ai_service.is_initialized:
                        self.response_received.emit(
                            "✗ AI service not available. Please configure AI settings first.", 
                            False
                        )
                        return
                    
                    # Send message to basic AI service (without conversation context)
                    logger.debug("Sent Message: %s", enhanced_message)
                    result = ai_service.send_message(enhanced_message)
                    
                    if result.get('success', False):
                        response_content = result['response']
                        logger.warning("⚠  Using basic AI service - conversation context may be limited")
                        logger.info(f"🔍 BASIC AI WORKER SUCCESS - Response length: {len(response_content) if response_content else 0}")
                        logger.info(f"🔍 BASIC AI WORKER SUCCESS - Response content: '{response_content}'")
                        self.response_received.emit(response_content, True)
                    else:
                        raw_error = result.get('error', 'Unknown error')
                        logger.error(f"Basic AI service error: {raw_error}")
                        
                        # Convert to user-friendly error message
                        friendly_error = self._get_user_friendly_error(str(raw_error))
                        self.response_received.emit(friendly_error, False)
                        
                except Exception as e:
                    logger.error(f"Enhanced AI worker error: {e}")
                    friendly_error = self._get_user_friendly_error(str(e))
                    self.response_received.emit(friendly_error, False)
            
            def _enhance_message_with_file_context(self, message: str) -> str:
                """Enhance message with file context using SafeRAG pipeline."""
                print(f"🔍 PRINT DEBUG: _enhance_message_with_file_context called with message: '{message[:50]}...'")
                logger.info(f"🔍 DEBUG: _enhance_message_with_file_context called with message: '{message[:50]}...'")
                logger.info(f"🔍 DEBUG: rag_session present: {self.rag_session is not None}")
                print(f"🔍 PRINT DEBUG: rag_session present: {self.rag_session is not None}")
                
                if not self.rag_session:
                    logger.info("🔍 DEBUG: No RAG session available, returning original message")
                    return message
                
                try:
                    # Create a SafeRAGSession for context retrieval
                    logger.info("🔍 Retrieving relevant context from SafeRAG pipeline")
                    
                    # Reuse existing RAG session if available, otherwise create new one
                    safe_rag = None
                    is_new_session = False
                    if hasattr(self, 'rag_session') and self.rag_session and self.rag_session.is_ready:
                        safe_rag = self.rag_session
                        logger.info("♻️ Reusing existing RAG session for context retrieval")
                    else:
                        # Import and create SafeRAGSession as fallback
                        from ...infrastructure.rag_pipeline.threading.safe_rag_session import create_safe_rag_session
                        safe_rag = create_safe_rag_session()
                        is_new_session = True
                        logger.info("🆕 Created new RAG session for context retrieval")
                    
                    if not safe_rag or not safe_rag.is_ready:
                        logger.warning("⚠️ SafeRAG session not available for context retrieval")
                        return message
                    
                    # First, check if we have any documents in the pipeline
                    try:
                        stats = safe_rag.get_stats(timeout=5.0)
                        logger.info(f"📊 RAG pipeline stats before query: {stats}")
                        
                        # Check if there are any documents
                        rag_stats = stats.get('rag_pipeline', {}) if stats else {}
                        docs_processed = rag_stats.get('documents_processed', 0)
                        chunks_stored = rag_stats.get('vector_store', {}).get('chunks_stored', 0)
                        logger.info(f"📊 Documents processed: {docs_processed}, Chunks stored: {chunks_stored}")
                        
                        if docs_processed == 0:
                            logger.warning("⚠️ RAG pipeline has no documents - no context to retrieve")
                            if is_new_session:
                                safe_rag.close()
                            return message
                    except Exception as stats_error:
                        logger.warning(f"Failed to check RAG pipeline stats: {stats_error}")
                        if is_new_session:
                            safe_rag.close()
                        return message
                    
                    # CRITICAL OPTIMIZATION: Skip RAG query if this conversation has no files
                    # This prevents expensive FAISS searches when result is guaranteed to be empty
                    current_conversation_id = self.conversation_id
                    logger.info(f"🔍 RAG OPTIMIZATION CHECK:")
                    logger.info(f"  - conversation_id: {current_conversation_id[:8] if current_conversation_id else 'NONE'}")

                    if current_conversation_id and hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                        try:
                            logger.info(f"  - file_browser_bar: ✅ FOUND")
                            logger.info(f"  - Calling get_files_for_conversation({current_conversation_id[:8]})...")
                            files = self.file_browser_bar.get_files_for_conversation(current_conversation_id)
                            file_count = len(files) if files else 0
                            logger.info(f"  - File count result: {file_count}")

                            if file_count == 0:
                                logger.info(f"⏭️⏭️⏭️ SKIPPING RAG: Conversation {current_conversation_id[:8]} has no files uploaded ⏭️⏭️⏭️")
                                if is_new_session:
                                    safe_rag.close()
                                return message
                            else:
                                logger.info(f"✅ Conversation {current_conversation_id[:8]} has {file_count} files - proceeding with RAG query")
                        except Exception as e:
                            logger.warning(f"❌ File browser check failed: {e} - proceeding with query to be safe")
                            import traceback
                            logger.debug(f"Traceback: {traceback.format_exc()}")
                    else:
                        if not current_conversation_id:
                            logger.warning(f"⚠️ No conversation ID - cannot optimize RAG query")
                        elif not hasattr(self, 'file_browser_bar'):
                            logger.warning(f"⚠️ File browser not available - cannot optimize RAG query")
                        logger.info(f"  - Proceeding with RAG query (no optimization possible)")

                    # Use SafeRAG query to get relevant context (thread-safe)
                    logger.info(f"Querying SafeRAG pipeline with: '{message[:100]}...'")
                    
                    try:
                        # Get current conversation ID for filtering - already retrieved above in optimization check
                        
                        # Query using SafeRAGSession with SmartContextSelector progressive fallback
                        # NEW: Smart context selection eliminates "all or nothing" problem
                        logger.info(f"🧠 Using SmartContextSelector for conversation: {current_conversation_id or 'None'}")
                        
                        response = safe_rag.query(
                            query_text=message,
                            top_k=3,
                            filters=None,  # Filters now handled by SmartContextSelector
                            timeout=10.0,
                            conversation_id=current_conversation_id  # Pass conversation_id for smart selection
                        )
                        
                        if response:
                            sources = response.get('sources', [])
                            selection_info = response.get('selection_info', {})
                            built_in_context = response.get('context', '')
                            
                            # Log transparency information
                            strategies = selection_info.get('strategies_attempted', [])
                            final_strategy = selection_info.get('final_strategy', 'unknown')
                            fallback_occurred = selection_info.get('fallback_occurred', False)
                            
                            logger.info(f"🧠 SmartContextSelector results: {len(sources)} sources using strategy '{final_strategy}'")
                            logger.info(f"🔄 Strategies attempted: {strategies}")
                            if fallback_occurred:
                                logger.info("🔄 Fallback strategies were activated")
                            
                            if sources:
                                # Log detailed source information with transparency
                                for i, source in enumerate(sources):
                                    if isinstance(source, dict):
                                        content_preview = source.get('content', '')[:100]
                                        source_type = source.get('source_type', 'unknown')
                                        score = source.get('score', 0.0)
                                        tier = source.get('selection_tier', 0)
                                        threshold = source.get('threshold_used', 0.0)
                                        
                                        logger.info(f"  Source {i+1} [{source_type.upper()}]: Score={score:.3f}, Tier={tier}, "
                                                  f"Threshold={threshold:.3f}, Content: {content_preview}...")
                                
                                # Use the built-in context from SmartContextSelector
                                if built_in_context:
                                    enhanced_message = f"Context from files:\n{built_in_context}\n\nUser question: {message}"
                                    
                                    logger.info(f"✅ Enhanced message with {len(sources)} smart-selected context sources")
                                    if is_new_session:
                                        safe_rag.close()
                                    return enhanced_message
                                else:
                                    logger.warning("⚠️ SmartContextSelector returned sources but no built context")
                            else:
                                # Log why no sources were found
                                message_text = response.get('message', 'No explanation provided')
                                logger.warning(f"⚠️ SmartContextSelector found no sources: {message_text}")
                        else:
                            logger.warning("⚠️ SafeRAG query returned no response")
                            
                    except Exception as e:
                        logger.error(f"SafeRAG query failed: {e}")
                        import traceback
                        logger.error(f"SafeRAG query traceback: {traceback.format_exc()}")
                    
                    # Close SafeRAG session and return original message
                    if is_new_session:
                        safe_rag.close()
                    return message
                    
                except Exception as e:
                    logger.error(f"Failed to enhance message with file context: {e}")
                    if 'safe_rag' in locals() and is_new_session:
                        safe_rag.close()
                    return message
            
            def _get_relevant_file_contexts(self, user_message: str, max_contexts: int = 3) -> list:
                """Get the most relevant file contexts using vector similarity."""
                try:
                    if not self.rag_session or not self.rag_session.is_ready():
                        return []
                    
                    # Use the file context service's intelligent retrieval
                    import asyncio
                    
                    def run_async_retrieval():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            logger.info(f"🔍 DEBUG: Starting context retrieval for query: '{user_message[:50]}...'")
                            
                            # Get relevant contexts using RAG session
                            if hasattr(self.rag_session, 'query'):
                                # Use RAG pipeline query method
                                logger.info(f"🔍 DEBUG: Querying RAG pipeline with: '{user_message[:50]}...'")
                                rag_response = loop.run_until_complete(
                                    self.rag_session.query(user_message)
                                )
                                
                                logger.info(f"🔍 DEBUG: RAG response: {type(rag_response)}")
                                
                                if rag_response and hasattr(rag_response, 'sources') and rag_response.sources:
                                    logger.info(f"🔍 DEBUG: Processing {len(rag_response.sources)} RAG sources")
                                    contexts = []
                                    for i, source in enumerate(rag_response.sources):
                                        logger.info(f"🔍 DEBUG: Source {i}: {type(source)}")
                                        context = {
                                            'filename': getattr(source, 'metadata', {}).get('filename', f'Document_{i}'),
                                            'file_type': getattr(source, 'metadata', {}).get('file_type', 'unknown'),
                                            'content': source.content[:2000] if hasattr(source, 'content') else str(source)[:2000],
                                            'similarity_score': getattr(source, 'similarity_score', 0.8),
                                            'chunk_id': getattr(source, 'document_id', f'chunk_{i}')
                                        }
                                        contexts.append(context)
                                    
                                    logger.info(f"🔍 DEBUG: Successfully processed {len(contexts)} RAG contexts")
                                    return contexts
                                else:
                                    logger.warning("No relevant contexts found from RAG pipeline")
                                    return []
                            else:
                                # Fallback - no context available
                                logger.warning("RAG pipeline query method not available")
                                return []
                                
                        except Exception as e:
                            logger.error(f"Error in async context retrieval: {e}")
                            return []
                        finally:
                            loop.close()
                    
                    return run_async_retrieval()
                    
                except Exception as e:
                    logger.error(f"Failed to get relevant file contexts: {e}")
                    return []
            
            def _get_user_friendly_error(self, error_message: str) -> str:
                """Convert technical error messages to user-friendly ones."""
                try:
                    from ...infrastructure.ai.api_test_service import _get_user_friendly_error
                    return _get_user_friendly_error(error_message)
                except ImportError:
                    # Fallback if import fails
                    return f"Connection failed: {error_message}"
            
            def _get_basic_ai_service(self):
                """Get basic AI service instance as fallback."""
                try:
                    from ...infrastructure.ai.ai_service import AIService
                    ai_service = AIService()
                    
                    # Initialize with current settings
                    if ai_service.initialize():
                        return ai_service
                    else:
                        return None
                        
                except ImportError:
                    logger.error("AI service not available")
                    return None
                except Exception as e:
                    logger.error(f"Failed to get AI service: {e}")
                    return None
        
        # Create and start worker thread
        self.ai_thread = QThread()
        self.ai_worker = EnhancedAIWorker(
            message, 
            self.conversation_manager, 
            self.current_conversation, 
            self.rag_session,
            conversation_id=self._get_safe_conversation_id(),
            file_browser_bar=self.file_browser_bar  # Pass file browser for RAG optimization
        )
        self.ai_worker.moveToThread(self.ai_thread)
        
        # Store references for cancellation
        self.current_ai_thread = self.ai_thread
        self.current_ai_worker = self.ai_worker
        
        # Connect signals
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.response_received.connect(self._on_ai_response)
        self.ai_worker.response_received.connect(self.ai_thread.quit)
        self.ai_worker.response_received.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self._cleanup_ai_thread)
        
        # Start processing
        self.ai_thread.start()
    
    def _on_ai_response(self, response: str, success: bool):
        """Handle AI response with conversation management."""
        # Log all AI responses for debugging
        logger.info(f"🔍 AI RESPONSE RECEIVED: success={success}, length={len(response) if response else 0}")
        logger.info(f"🔍 AI RESPONSE CONTENT: '{response}'")
        
        # Restore normal prompt and re-enable input
        self._set_processing_mode(False)
        self.command_input.setEnabled(True)
        self.command_input.setFocus()
        
        # Reset idle detector
        self.idle_detector.reset_activity(
            self.current_conversation.id if self.current_conversation else None
        )
        
        # Clear thread references
        self.current_ai_thread = None
        self.current_ai_worker = None
        
        # Display response with appropriate icon
        if success:
            # Clear failed message on successful response
            self.last_failed_message = None
            
            # Debug: Check response content
            if not response or not response.strip():
                logger.warning(f"Empty AI response received: '{response}'")
                response = "[No response content received]"
            
            # Display AI response with better separation
            try:
                self.append_output("🤖 **Spector:**", "response")
                # Display the actual response without prefixing to preserve markdown
                self.append_output(response, "response")
                # Add spacing after AI response
                self.append_output("", "normal")
                self.append_output("\n--------------------------------------------------\n", "normal")  # Changed from "divider" to "normal"
            except Exception as e:
                logger.error(f"Error displaying AI response: {e}", exc_info=True)
                # Try fallback plain text display
                try:
                    if self.output_display:
                        self.output_display.add_plain_text(f"🤖 Spector: {response}", "response")
                except Exception as e2:
                    logger.error(f"Fallback display also failed: {e2}", exc_info=True)
            
            # NOTE: Conversation refresh disabled to prevent asyncio event loop conflicts with Qt
            # The conversation manager already handles message persistence in the background
            # If we need to refresh conversation metadata, it should be done via Qt signals/slots
            # to avoid creating conflicting event loops

            # if self.conversation_manager and self.current_conversation:
            #     # This code was causing crashes by creating a new asyncio event loop
            #     # which conflicts with Qt's event loop
            #     pass

            logger.debug("Conversation data refresh skipped (handled by conversation manager)")
        else:
            # Error occurred - display error message with resend option
            self.append_output("❌ **Connection Failed**", "error")
            self.append_output(response, "error")
            
            # Add resend option if we have a failed message stored
            if self.last_failed_message:
                self.append_output("", "system")  # Add some spacing
                self._add_resend_option()
        
        logger.debug(f"Enhanced AI response displayed: success={success}")
    
    def _add_resend_option(self):
        """Add a resend button option to the output display."""
        try:
            # Create a clickable resend link using HTML
            message_preview = self.last_failed_message[:100] + "..." if len(self.last_failed_message) > 100 else self.last_failed_message
            resend_html = f'''
            <div style="margin: 10px 0; padding: 8px; border: 1px solid #666; border-radius: 4px; background-color: rgba(255,255,255,0.05);">
                <a href="resend_message" style="color: #4CAF50; text-decoration: none; font-weight: bold;">
                    🔄 Click here to resend your message
                </a>
                <br><span style="color: #888; font-size: 10px;">
                    Message: "{html.escape(message_preview)}"
                </span>
            </div>
            '''
            
            # Add the resend option using MixedContentDisplay
            if self.output_display:
                self.output_display.add_html_content(resend_html, "system")
            else:
                logger.warning("Cannot add resend option - no output display available")
                
        except Exception as e:
            logger.error(f"Failed to add resend option: {e}")
            # Fallback to simple text
            self.append_output("Type 'resend' to try sending your message again", "system")
    
    def _handle_link_click(self, url):
        """Handle clicks on all links including resend and external links."""
        # Handle both QUrl objects and strings
        if isinstance(url, str):
            url_string = url
        else:
            url_string = url.toString()
        
        # Handle resend links
        if url_string == "resend_message" and self.last_failed_message:
            logger.info(f"Resending failed message: {self.last_failed_message[:50]}...")
            self.append_output(f"🔄 **Resending message...**", "system")
            self.append_output("", "system")  # Add spacing
            self._send_to_ai(self.last_failed_message)
            return
        
        # Handle external links
        if url_string.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
            import webbrowser
            try:
                webbrowser.open(url_string)
                logger.debug(f"Opened external link: {url_string}")
            except Exception as e:
                logger.error(f"Failed to open link {url_string}: {e}")
                self.append_output(f"Failed to open link: {url_string}", "error")
    
    def _handle_resend_click(self, url):
        """Legacy method - redirects to new link handler."""
        self._handle_link_click(url)
        
    def _show_output_context_menu(self, position):
        """Show context menu for output display with link operations."""
        # Create context menu
        context_menu = QMenu(self.output_display)
        
        # MixedContentDisplay doesn't have cursor/link detection like QTextEdit
        # Provide general context menu actions
        
        clear_action = context_menu.addAction("🗑️ Clear Display")
        clear_action.triggered.connect(self.clear_output)
        
        context_menu.addSeparator()
        
        refresh_action = context_menu.addAction("🔄 Refresh Theme")
        refresh_action.triggered.connect(self._refresh_existing_output)
        
        # Show context menu
        context_menu.exec(self.output_display.mapToGlobal(position))
    
    def _copy_link_to_clipboard(self, url):
        """Copy link URL to clipboard."""
        try:
            from PyQt6.QtGui import QGuiApplication
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(url)
            logger.debug(f"Copied link to clipboard: {url}")
        except Exception as e:
            logger.error(f"Failed to copy link to clipboard: {e}")
    
    def _setup_link_handling(self):
        """Setup link detection and handling for MixedContentDisplay."""
        # Connect the MixedContentDisplay link_clicked signal
        self.output_display.link_clicked.connect(self._handle_link_click)
    
    
    
    def _on_stop_query(self):
        """Handle stop button click to cancel active AI query."""
        logger.info("Stop button clicked - cancelling AI query")
        
        try:
            # Stop the AI thread if it's running
            if self.current_ai_thread and self.current_ai_thread.isRunning():
                logger.info("Terminating AI worker thread...")
                self.current_ai_thread.quit()
                if not self.current_ai_thread.wait(3000):  # Wait up to 3 seconds
                    logger.warning("AI thread did not quit gracefully, terminating forcefully")
                    self.current_ai_thread.terminate()
                    self.current_ai_thread.wait()
                
            # Clean up thread references
            self.current_ai_thread = None
            self.current_ai_worker = None
            
            # Restore UI to normal state
            self._set_processing_mode(False)
            self.command_input.setEnabled(True)
            self.command_input.setFocus()
            
            # Show cancellation message
            self.append_output("🛑 **Query cancelled by user**", "system")
            
        except Exception as e:
            logger.error(f"Failed to stop AI query: {e}")
            # Ensure UI is restored even if stop fails
            self._set_processing_mode(False)
            self.command_input.setEnabled(True)
            self.command_input.setFocus()
    
    def _cleanup_ai_thread(self):
        """Clean up AI thread references when thread finishes."""
        logger.debug("Cleaning up AI thread")
        self.current_ai_thread = None
        self.current_ai_worker = None
    
    # Public methods for external integration
    
    def set_conversation_manager(self, conversation_manager: ConversationManager):
        """Set the conversation manager instance."""
        self.conversation_manager = conversation_manager
        if conversation_manager and conversation_manager.is_initialized():
            # Reload conversations
            try:
                logger.debug("Reloading conversations after setting manager...")
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._load_conversations())
                else:
                    loop.run_until_complete(self._load_conversations())
                logger.debug("Conversation reload initiated successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load conversations after setting manager: {e}", exc_info=True)
        logger.info("Conversation manager set for REPL widget")
    
    def get_current_conversation_id(self) -> Optional[str]:
        """Get the ID of the currently active conversation."""
        # Don't return ID for empty conversations
        if self.current_conversation:
            # Check if conversation has any messages
            if hasattr(self.current_conversation, 'get_message_count') and self.current_conversation.get_message_count() > 0:
                return self.current_conversation.id
            elif hasattr(self.current_conversation, 'messages') and len(self.current_conversation.messages) > 0:
                return self.current_conversation.id
        return None
    
    def restore_conversation(self, conversation_id: str):
        """Restore a specific conversation by ID."""
        if not self.conversation_manager:
            logger.warning("Cannot restore conversation - no conversation manager available")
            return
            
        try:
            logger.debug(f"Attempting to restore conversation: {conversation_id}")
            
            # Use async manager to handle the restore operation safely
            from ...infrastructure.async_manager import run_async_task_safe
            
            def on_restore_complete(result, error):
                if error:
                    logger.error(f"✗ Failed to restore conversation {conversation_id}: {error}")
                    self.append_output(f"✗ Failed to restore conversation: {error}", "error")
                else:
                    logger.debug(f"✓ Successfully restored conversation: {conversation_id}")
            
            # Run the async operation safely
            run_async_task_safe(
                self._restore_conversation_async(conversation_id),
                callback=on_restore_complete,
                timeout=30.0  # 30 second timeout for conversation restoration
            )
                
        except Exception as e:
            logger.error(f"✗ Failed to schedule conversation restore {conversation_id}: {e}", exc_info=True)
    
    async def _restore_conversation_async(self, conversation_id: str):
        """Restore conversation asynchronously."""
        try:
            # Save current conversation if it has messages
            if self.current_conversation and self._has_unsaved_messages():
                await self._save_current_conversation_before_switch()
            
            # Simple atomic database operation: set this conversation as active, all others as pinned
            success = self.conversation_manager.set_conversation_active_simple(conversation_id)
            if not success:
                logger.error(f"✗ Failed to set conversation {conversation_id} as active in database")
                self.append_output("✗ Failed to restore conversation", "error")
                return
            
            # Load the conversation from database with messages
            conversation = await self.conversation_manager.get_conversation(conversation_id, include_messages=True)
            
            if conversation:
                # Set as current conversation and update AI context
                self.current_conversation = conversation
                logger.info(f"✓ Restored conversation: {conversation.title}")
                
                # Start autosave timer for the restored conversation
                self._start_autosave_timer()
                
                # Update AI service context
                if self.conversation_manager and self.conversation_manager.has_ai_service():
                    ai_service = self.conversation_manager.get_ai_service()
                    if ai_service:
                        ai_service.set_current_conversation(conversation.id)
                        logger.info(f"🔄 AI service context updated for restored conversation")
                
                # Clear REPL and load conversation messages
                self.clear_output()
                self.append_output(f"📂 Restored conversation: {conversation.title}", "system")
                
                # Display conversation history
                if hasattr(conversation, 'messages') and conversation.messages:
                    logger.info(f"📜 Restoring {len(conversation.messages)} messages")
                    for message in conversation.messages:
                        if hasattr(message, 'role') and hasattr(message, 'content'):
                            if message.role.value == 'user':
                                self.append_output(f">>> {message.content}", "input")
                            elif message.role.value == 'assistant':
                                self.append_output(message.content, "response")
                            elif message.role.value == 'system':
                                self.append_output(f"[System] {message.content}", "system")
                else:
                    logger.debug("No messages found for conversation")
                
                # Load conversation files and update file browser bar
                self._load_conversation_files(conversation.id)
                
                self.append_output("", "system")  # Add spacing
                self.append_output("💬 Conversation restored. Continue chatting...", "system")
                
                # Update idle detector
                self.idle_detector.reset_activity(conversation_id)
                
            else:
                logger.warning(f"⚠  Conversation {conversation_id} not found in database")
                self.append_output(f"⚠ Could not restore conversation {conversation_id[:8]}... (not found)", "warning")
                
        except Exception as e:
            logger.error(f"✗ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
            self.append_output(f"✗ Failed to restore conversation: {str(e)}", "error")
    
    def _has_unsaved_messages(self) -> bool:
        """Check if current conversation has unsaved messages and user messages."""
        if not self.current_conversation:
            return False
        
        # First check if there are any user messages in this conversation
        user_message_count = 0
        for message in self.current_conversation.messages:
            if hasattr(message, 'role') and message.role and str(message.role).lower() == 'user':
                user_message_count += 1
        
        # Only consider saving if there are user messages
        if user_message_count == 0:
            logger.debug(f"No user messages found in conversation - not saving (total messages: {len(self.current_conversation.messages)})")
            return False
        
        # Check if there's content in the MixedContentDisplay
        if not hasattr(self.output_display, 'content_widgets'):
            return False
            
        # If there are content widgets and user messages, assume there might be unsaved content
        # This is a simplified check since MixedContentDisplay doesn't have toPlainText()
        return len(self.output_display.content_widgets) > 0
    
    async def _save_current_conversation_before_switch(self):
        """Save current conversation before switching to another."""
        try:
            if self.conversation_manager and self.conversation_manager.has_ai_service():
                ai_service = self.conversation_manager.get_ai_service()
                if ai_service and hasattr(ai_service, '_save_current_conversation'):
                    await ai_service._save_current_conversation()
                    logger.info(f"💾 Saved current conversation before switch: {self.current_conversation.id}")
        except Exception as e:
            logger.error(f"Failed to save current conversation before switch: {e}")
    
    async def _update_conversation_status(self, conversation_id: str, status: 'ConversationStatus'):
        """Update conversation status in database and refresh UI."""
        try:
            if self.conversation_manager:
                await self.conversation_manager.update_conversation_status(conversation_id, status)
                logger.debug(f"Updated conversation {conversation_id[:8]}... status to {status.value}")
                
                # Update the conversation object in our local list
                for i, conv in enumerate(self.conversations_list):
                    if conv.id == conversation_id:
                        # Update the status in the local object
                        conv.status = status
                        break
                
                # Refresh the conversation selector UI
                self._refresh_conversation_selector()
                
        except Exception as e:
            logger.error(f"Failed to update conversation status: {e}")
    
    def _refresh_conversation_selector(self):
        """Refresh the conversation selector dropdown with updated status icons."""
        try:
            # Check if conversation_selector exists (it may not be implemented yet)
            if not hasattr(self, 'conversation_selector'):
                return
                
            if not self.conversations_list:
                return
            
            # Store current selection
            current_id = None
            if self.conversation_selector.currentIndex() >= 0:
                current_id = self.conversation_selector.itemData(self.conversation_selector.currentIndex())
            
            # Clear and rebuild the selector
            self.conversation_selector.clear()
            
            # Add "New Conversation" option
            self.conversation_selector.addItem("🆕 New Conversation", None)
            
            # Add all conversations with updated status icons
            for i, conversation in enumerate(self.conversations_list):
                display_name = f"{self._get_status_icon(conversation)} {conversation.title}"
                self.conversation_selector.addItem(display_name, conversation.id)
                
                # Restore selection if this was the previously selected conversation
                if conversation.id == current_id:
                    self.conversation_selector.setCurrentIndex(i + 1)  # +1 because of "New Conversation" item
            
            logger.debug("Conversation selector refreshed with updated status icons")
            
        except Exception as e:
            logger.error(f"Failed to refresh conversation selector: {e}")
    
    def show_bulk_delete_dialog(self):
        """Show dialog for bulk deletion of conversations with multi-select."""
        if not self.conversations_list:
            QMessageBox.information(self, "No Conversations", "No conversations available to delete.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Delete Conversations")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instruction_label = QLabel("Select conversations to delete (hold Ctrl/Cmd for multiple selections):")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        # List widget for multi-selection
        conversation_list = QListWidget()
        conversation_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Populate with conversations
        for conversation in self.conversations_list:
            if conversation.id != getattr(self.current_conversation, 'id', None):  # Don't allow deleting current conversation
                status_icon = self._get_status_icon(conversation)
                item_text = f"{status_icon} {conversation.title} ({conversation.created_at.strftime('%Y-%m-%d %H:%M')})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, conversation.id)
                conversation_list.addItem(item)
        
        layout.addWidget(conversation_list)
        
        # Warning label
        warning_label = QLabel("⚠ This action cannot be undone. Deleted conversations will be permanently removed.")
        warning_color = self.theme_manager.current_theme.status_error if (self.theme_manager and THEME_SYSTEM_AVAILABLE) else "#ff6b6b"
        warning_label.setStyleSheet(f"color: {warning_color}; font-weight: bold;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        delete_btn = QPushButton("Delete Selected")
        delete_bg = self.theme_manager.current_theme.status_error if (self.theme_manager and THEME_SYSTEM_AVAILABLE) else "#ff6b6b"
        delete_btn.setStyleSheet(f"background-color: {delete_bg}; color: white; font-weight: bold;")
        delete_btn.clicked.connect(lambda: self._handle_bulk_delete(dialog, conversation_list))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _handle_bulk_delete(self, dialog: 'QDialog', conversation_list: QListWidget):
        """Handle bulk deletion of selected conversations."""
        selected_items = conversation_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one conversation to delete.")
            return
        
        # Get conversation IDs and titles
        selected_conversations = []
        for item in selected_items:
            conv_id = item.data(Qt.ItemDataRole.UserRole)
            conv_title = item.text()
            selected_conversations.append((conv_id, conv_title))
        
        # Confirmation dialog
        count = len(selected_conversations)
        titles_preview = "\n".join([f"• {title}" for _, title in selected_conversations[:5]])
        if count > 5:
            titles_preview += f"\n... and {count - 5} more"
        
        reply = QMessageBox.question(
            dialog,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} conversation{'s' if count > 1 else ''}?\n\n{titles_preview}\n\n⚠ This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Perform deletion
            asyncio.create_task(self._delete_conversations_async([conv_id for conv_id, _ in selected_conversations]))
            dialog.accept()
    
    async def _delete_conversations_async(self, conversation_ids: list):
        """Delete multiple conversations asynchronously."""
        try:
            if not self.conversation_manager:
                logger.error("No conversation manager available for deletion")
                return
            
            deleted_count = 0
            for conv_id in conversation_ids:
                try:
                    await self.conversation_manager.delete_conversation(conv_id)
                    deleted_count += 1
                    logger.info(f"Deleted conversation: {conv_id}")
                except Exception as e:
                    logger.error(f"Failed to delete conversation {conv_id}: {e}")
            
            # Refresh conversations list
            await self._load_conversations()
            
            # Update UI
            self.append_output(f"✓ Deleted {deleted_count} conversation{'s' if deleted_count != 1 else ''}", "system")
            
        except Exception as e:
            logger.error(f"Failed to delete conversations: {e}")
            self.append_output(f"✗ Failed to delete conversations: {str(e)}", "error")
    
    def _autosave_current_conversation(self):
        """Autosave the current conversation if it has messages."""
        try:
            if not self.autosave_enabled or not self.current_conversation:
                return
            
            # Check if there are messages to save
            if not self._has_unsaved_messages():
                return
            
            # Check if enough time has passed since last autosave
            now = datetime.now()
            if (self.last_autosave_time and 
                (now - self.last_autosave_time).total_seconds() < 30):  # Min 30 seconds between autosaves
                return
            
            logger.info(f"💾 Autosaving conversation: {self.current_conversation.title}")
            
            # Perform autosave synchronously (we're in a Qt context, not async)
            self._perform_autosave_sync()
            
        except Exception as e:
            logger.error(f"Failed to autosave conversation: {e}")
    
    def _perform_autosave_sync(self):
        """Perform the actual autosave operation synchronously."""
        try:
            if self.conversation_manager and self.conversation_manager.has_ai_service():
                ai_service = self.conversation_manager.get_ai_service()
                if ai_service:
                    # Save the conversation through the conversation manager
                    # which handles both messages and the conversation state
                    if hasattr(self.conversation_manager, 'save_current_conversation'):
                        self.conversation_manager.save_current_conversation()
                    elif hasattr(ai_service, 'save_current_conversation_sync'):
                        # Fallback to sync method if available
                        ai_service.save_current_conversation_sync()
                    self.last_autosave_time = datetime.now()
                    logger.debug(f"✓ Autosaved conversation: {self.current_conversation.id}")
        except Exception as e:
            logger.error(f"Failed to perform autosave: {e}")
    
    async def _perform_autosave(self):
        """Perform the actual autosave operation asynchronously (legacy method)."""
        try:
            if self.conversation_manager and self.conversation_manager.has_ai_service():
                ai_service = self.conversation_manager.get_ai_service()
                if ai_service and hasattr(ai_service, '_save_current_conversation'):
                    await ai_service._save_current_conversation()
                    self.last_autosave_time = datetime.now()
                    logger.debug(f"✓ Autosaved conversation: {self.current_conversation.id}")
        except Exception as e:
            logger.error(f"Failed to perform autosave: {e}")
    
    def _start_autosave_timer(self):
        """Start the autosave timer."""
        if self.autosave_enabled and not self.autosave_timer.isActive():
            self.autosave_timer.start(self.autosave_interval)
            logger.debug(f"📅 Autosave timer started (interval: {self.autosave_interval/1000}s)")
    
    def _stop_autosave_timer(self):
        """Stop the autosave timer."""
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            logger.debug("⏹️ Autosave timer stopped")
    
    def _trigger_autosave_soon(self):
        """Trigger autosave after a short delay (e.g., after user sends a message)."""
        if self.autosave_enabled and self.current_conversation:
            # Use a single-shot timer for immediate autosave after user interaction
            QTimer.singleShot(5000, self._autosave_current_conversation)  # 5 seconds delay
    
    def _create_new_conversation_for_message(self, message: str):
        """Create a new conversation automatically when user starts chatting."""
        if not self.conversation_manager:
            return
            
        try:
            # Generate a title from the message (first few words)
            words = message.strip().split()[:5]  # First 5 words
            title = " ".join(words)
            if len(title) > 50:
                title = title[:47] + "..."
            elif len(title) < 5:
                title = f"Chat {datetime.now().strftime('%H:%M')}"
            
            logger.debug(f"🆕 Creating conversation with title: {title}")
            
            # CRITICAL: Create conversation synchronously to ensure it's ready for AI processing
            # This is necessary to avoid race conditions where messages are sent before conversation exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new event loop for synchronous operation
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        conversation = new_loop.run_until_complete(self._create_conversation_async(title, message))
                        if conversation:
                            self.current_conversation = conversation
                            logger.info(f"✓ Auto-created conversation synchronously: {conversation.title}")
                        else:
                            logger.error("✗ Failed to create conversation - None returned")
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(loop)  # Restore original loop
                else:
                    # Run synchronously
                    conversation = loop.run_until_complete(self._create_conversation_async(title, message))
                    if conversation:
                        self.current_conversation = conversation
                        logger.info(f"✓ Auto-created conversation: {conversation.title}")
                    else:
                        logger.error("✗ Failed to create conversation - None returned")
                        
            except Exception as loop_error:
                logger.error(f"✗ Loop error during conversation creation: {loop_error}")
                # Fallback: try direct sync creation
                logger.info("🔄 Attempting fallback conversation creation...")
                try:
                    # Create a minimal conversation object for immediate use
                    from ...infrastructure.conversation_management.models.conversation import Conversation, ConversationMetadata
                    from ...infrastructure.conversation_management.models.enums import ConversationStatus
                    from uuid import uuid4
                    
                    conversation_id = str(uuid4())
                    metadata = ConversationMetadata()
                    temp_conversation = Conversation(
                        id=conversation_id,
                        title=title,
                        status=ConversationStatus.PINNED,  # Start as pinned, will be set active properly
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        metadata=metadata
                    )
                    
                    self.current_conversation = temp_conversation
                    logger.info(f"⚡ Created temporary conversation for immediate use: {conversation_id}")
                    
                    # Save to database synchronously to avoid async issues in Qt thread
                    try:
                        if self.conversation_service:
                            # Use the synchronous version of save
                            saved_conversation = self.conversation_service.create_conversation(
                                title=temp_conversation.title,
                                model=temp_conversation.model,
                                system_prompt=temp_conversation.system_prompt
                            )
                            if saved_conversation:
                                temp_conversation.id = saved_conversation.id
                                logger.info(f"✓ Saved temp conversation to database: {saved_conversation.id}")
                    except Exception as save_error:
                        logger.warning(f"Could not save temp conversation to DB: {save_error}")
                    
                    # Set as active using proper uniqueness enforcement
                    if self.conversation_manager:
                        success = self.conversation_manager.set_conversation_active_simple(conversation_id)
                        if success:
                            temp_conversation.status = ConversationStatus.ACTIVE
                            logger.info(f"✓ Set temp conversation as active with uniqueness enforced")
                    
                except Exception as fallback_error:
                    logger.error(f"✗ Fallback conversation creation also failed: {fallback_error}")
                
        except Exception as e:
            logger.error(f"✗ Failed to auto-create conversation: {e}", exc_info=True)
    
    
    def refresh_conversations(self):
        """Refresh the conversations list from the database."""
        if not self.conversation_manager:
            return
        
        try:
            logger.debug("Refreshing conversations list...")
            # Use synchronous conversation loading to avoid async issues in Qt threads
            if hasattr(self.conversation_manager, 'get_conversations'):
                conversations = self.conversation_manager.get_conversations()
                if conversations:
                    self.conversations_list = conversations
                    logger.debug(f"✓ Loaded {len(conversations)} conversations")
            logger.debug("Conversation refresh completed successfully")
        except Exception as e:
            logger.error(f"✗ Failed to refresh conversations: {e}", exc_info=True)
    
    def create_new_conversation_with_title(self, title: str):
        """Create a new conversation with a specific title."""
        if not self.conversation_manager:
            logger.warning("Cannot create conversation - manager not available")
            return
        
        async def create_with_title():
            try:
                conversation = await self.conversation_manager.create_conversation(
                    title=title,
                    initial_message=f"New conversation: {title}"
                )
                
                if conversation:
                    # Add to conversations list
                    self.conversations_list.insert(0, conversation)
                    
                    # Update UI only if conversation selector exists
                    if hasattr(self, 'conversation_selector'):
                        display_name = f"{self._get_status_icon(conversation)} {conversation.title}"
                        self.conversation_selector.insertItem(0, display_name, conversation.id)
                        self.conversation_selector.setCurrentIndex(0)
                    
                    # Switch to new conversation
                    self._switch_to_conversation(conversation)
                    
                    self.append_output(f"✨ Created conversation: {conversation.title}", "system")
                    logger.info(f"✓ Conversation created with title: {title}")
                
            except Exception as e:
                logger.error(f"✗ Failed to create conversation with title: {e}")
                self.append_output("✗ Failed to create new conversation", "error")
        
        # Run async task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(create_with_title())
            else:
                loop.run_until_complete(create_with_title())
        except Exception as e:
            logger.error(f"Failed to run async conversation creation: {e}")
    
    def set_ai_service(self, ai_service):
        """Set the AI service instance (for backward compatibility)."""
        self._ai_service = ai_service
        logger.debug("AI service set for REPL widget")
    
    def _on_new_conversation_clicked(self):
        """Handle new conversation button click (without menu)."""
        self._start_new_conversation(save_current=False)
    
    def _on_help_clicked(self):
        """Handle help button click - open help docs directly in browser."""
        logger.info("Help button clicked - opening help docs in browser")
        import webbrowser
        
        try:
            # Try to find local help documentation using centralized resolver
            from ...utils.resource_resolver import resolve_help_file
            
            help_path = resolve_help_file()
            
            if help_path:
                # Open local help file
                help_url = help_path.as_uri()
                webbrowser.open(help_url)
                logger.info(f"Opened local help documentation: {help_url}")
            else:
                # Fallback: open online docs
                webbrowser.open("https://github.com/ghost-ng/ghost-ng/tree/main/docs")
                logger.info("Opened online documentation (local help not found)")
                
        except Exception as e:
            logger.error(f"Failed to open help docs: {e}")
            # Last resort fallback
            try:
                webbrowser.open("https://github.com/ghost-ng/ghost-ng")
                logger.info("Opened project homepage as fallback")
            except Exception as e2:
                logger.error(f"Failed to open any help resource: {e2}")
    
    def _on_help_command_clicked(self):
        """Handle help command button click - send 'help' command to chat."""
        logger.info("Help command button clicked - sending 'help' command")
        # Set the command input to 'help' and send it
        self.command_input.setPlainText("help")
        self._on_command_entered()
    
    def _handle_debug_command(self):
        """Handle debug command to show attachment state."""
        try:
            # Get the main window from the parent chain
            main_window = None
            parent = self.parent()
            while parent:
                if hasattr(parent, 'debug_attachment_state'):
                    main_window = parent
                    break
                parent = parent.parent()
            
            if main_window:
                main_window.debug_attachment_state()
                self._display_response("🔍 Debug info logged to console. Check debug logs for attachment state details.", "system")
            else:
                self._display_response("✗ Could not find main window for debugging.", "error")
        except Exception as e:
            self._display_response(f"✗ Debug command failed: {e}", "error")
    
    
    def _load_pin_icon_immediate(self):
        """Immediately load pin icon with maximum force - no fallbacks."""
        try:
            # Determine if theme is dark or light  
            icon_variant = self._get_icon_variant()
            
            pin_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"pin_{icon_variant}.png"
            )
            
            if os.path.exists(pin_icon_path):
                # Create icon and verify it loads
                icon = QIcon(pin_icon_path)
                if not icon.isNull():
                    # FORCE clear any existing content
                    self.pin_btn.setText("")
                    self.pin_btn.setIcon(QIcon())  # Clear first
                    
                    # Set the new icon
                    self.pin_btn.setIcon(icon)
                    
                    # Set icon size explicitly
                    self.pin_btn.setIconSize(QSize(16, 16))
                    
                    # FORCE icon-only mode
                    self.pin_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                    
                    # Clear text again
                    self.pin_btn.setText("")
                    
                    # Force update
                    self.pin_btn.update()
                    
                else:
                    logger.error(f"✗ QIcon creation failed for: {pin_icon_path}")
            else:
                logger.error(f"✗ Pin icon file not found: {pin_icon_path}")
                
        except Exception as e:
            logger.error(f"✗ Failed to force load pin icon: {e}")
            # Clear everything on error - NO EMOJI FALLBACK
            self.pin_btn.setText("")
            self.pin_btn.setIcon(QIcon())
    
    def _load_pin_icon(self):
        """Compatibility method - redirects to immediate loader."""
        self._load_pin_icon_immediate()
    
    def _on_pin_toggle_clicked(self):
        """Handle pin button toggle - change always on top setting."""
        try:
            always_on_top = self.pin_btn.isChecked()
            logger.info(f"Pin button toggled: always_on_top = {always_on_top}")
            
            # Apply visual feedback IMMEDIATELY like move button
            if always_on_top:
                # Apply amber/gold toggle styling
                self._apply_pin_button_toggle_style(self.pin_btn)
                logger.debug("🟡 Pin mode ON - applied amber styling")
            else:
                # Reset to normal styling - SAME AS MOVE BUTTON
                self._style_title_button(self.pin_btn)
                logger.debug("⚠ Pin mode OFF - reset to normal styling")
            
            # Reload icon after styling to preserve it
            self._load_pin_icon_immediate()
            
            # Clear any text that might have been set by styling
            if hasattr(self.pin_btn, '_original_setText'):
                self.pin_btn._original_setText("")
            
            # Save to settings
            if _global_settings:
                _global_settings.set('interface.always_on_top', always_on_top)
            
            # Apply the setting immediately by triggering the app coordinator
            self.pin_toggle_requested.emit(always_on_top)
            
            # Update tooltip
            self.pin_btn.setToolTip("Always stay on top" if always_on_top else "Click to stay on top")
            
        except Exception as e:
            logger.error(f"Failed to handle pin toggle: {e}")
    
    def _show_new_conv_menu(self):
        """Show the new conversation menu for title button."""
        if hasattr(self, 'title_new_conv_menu'):
            # Re-apply styling before showing menu
            logger.debug("Re-styling title menu before show")
            self._style_menu(self.title_new_conv_menu)
            
            # Position menu below the button
            button_pos = self.title_new_conv_btn.mapToGlobal(self.title_new_conv_btn.rect().bottomLeft())
            logger.debug(f"Showing title menu at position: {button_pos}")
            self.title_new_conv_menu.exec(button_pos)
    
    def _show_toolbar_new_conv_menu(self):
        """Show the new conversation menu for toolbar button."""
        if hasattr(self, 'toolbar_new_conv_menu'):
            # Re-apply styling before showing menu
            logger.debug("Re-styling toolbar menu before show")
            self._style_menu(self.toolbar_new_conv_menu)
            
            # Position menu below the button
            button_pos = self.toolbar_new_conv_btn.mapToGlobal(self.toolbar_new_conv_btn.rect().bottomLeft())
            logger.debug(f"Showing toolbar menu at position: {button_pos}")
            self.toolbar_new_conv_menu.exec(button_pos)
    
    def _on_settings_clicked(self):
        """Handle settings button click - open settings dialog."""
        self.settings_requested.emit()
    
    def _on_chat_clicked(self):
        """Handle chat button click - browse conversations."""
        self.browse_requested.emit()
    
    def _on_move_toggle_clicked(self):
        """Handle move/resize arrow toggle button click."""
        # Get the parent floating REPL window
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, '_direct_arrow_manager'):
            parent_window = parent_window.parent()
        
        if parent_window and hasattr(parent_window, '_direct_arrow_manager'):
            if self.move_btn.isChecked():
                # Show grips - resize mode ON
                parent_window.show_resize_arrows(auto_hide=False)  # Compatibility method
                # Apply toggle styling that preserves all size constraints
                self._apply_move_button_toggle_style(self.move_btn)
                print("🔘 Move mode ON - edge grips visible, REPL fully clickable")
            else:
                # Hide grips - normal mode restored
                parent_window.hide_resize_arrows()  # Compatibility method
                # Reset to normal styling
                self._style_title_button(self.move_btn)
                print("🔘 Move mode OFF - grips hidden, normal control")
    
    def _save_current_conversation(self):
        """Save the current conversation without starting a new one."""
        try:
            if not self.conversation_manager:
                self.append_output("⚠ Conversation management not available", "error")
                return
            
            # Get AI service for conversation integration
            ai_service = None
            if self.conversation_manager:
                ai_service = self.conversation_manager.get_ai_service()
            
            if not ai_service or not hasattr(ai_service, 'conversation_service'):
                self.append_output("⚠ AI service doesn't support conversation management", "error")
                return
            
            async def save_conversation():
                try:
                    # Force sync between REPL and AI service first
                    if self.current_conversation and self.conversation_manager and self.conversation_manager.has_ai_service():
                        ai_service_current = ai_service.get_current_conversation_id()
                        if ai_service_current != self.current_conversation.id:
                            logger.debug(f"Syncing conversations before save: AI={ai_service_current}, REPL={self.current_conversation.id}")
                            ai_service.set_current_conversation(self.current_conversation.id)
                    
                    current_id = ai_service.get_current_conversation_id()
                    logger.debug(f"Save attempt - AI service current ID: {current_id}")
                    logger.debug(f"Save attempt - REPL current conversation: {self.current_conversation.id if self.current_conversation else None}")
                    
                    # Determine which conversation to save
                    conversation = None
                    
                    # First try: Use AI service current conversation
                    if current_id:
                        conversation = await ai_service.conversation_service.get_conversation(current_id, include_messages=True)
                        if conversation and conversation.messages:
                            logger.debug(f"Found conversation via AI service with {len(conversation.messages)} messages")
                        else:
                            logger.debug(f"AI service conversation has no messages: {conversation.messages if conversation else 'No conversation'}")
                    
                    # Second try: Use REPL's current conversation if AI service doesn't have a good one
                    if (not conversation or not conversation.messages) and self.current_conversation:
                        logger.debug(f"Trying REPL current conversation: {self.current_conversation.id}")
                        current_id = self.current_conversation.id
                        
                        # Try to get it from the database
                        try:
                            conversation = await ai_service.conversation_service.get_conversation(current_id, include_messages=True)
                            if conversation and conversation.messages:
                                logger.debug(f"Found REPL conversation in database with {len(conversation.messages)} messages")
                            else:
                                # Use the in-memory conversation object directly
                                conversation = self.current_conversation
                                logger.debug(f"Using in-memory REPL conversation with {len(conversation.messages) if hasattr(conversation, 'messages') else 'unknown'} messages")
                        except Exception as e:
                            logger.debug(f"Failed to get REPL conversation from database, using in-memory: {e}")
                            conversation = self.current_conversation
                    
                    if not current_id:
                        self.append_output("⚠ No active conversation to save", "system")
                        return
                    
                    if not conversation:
                        self.append_output("⚠ No conversation found to save", "system")
                        return
                        
                    # Check for messages in various ways
                    has_messages = False
                    message_count = 0
                    
                    if hasattr(conversation, 'messages') and conversation.messages:
                        has_messages = True
                        message_count = len(conversation.messages)
                    elif hasattr(conversation, 'get_message_count') and conversation.get_message_count() > 0:
                        has_messages = True
                        message_count = conversation.get_message_count()
                    
                    if not has_messages:
                        # Final check: see if there are unsent messages in the UI
                        ui_has_messages = self._has_unsaved_messages()
                        if ui_has_messages:
                            self.append_output("⚠ Conversation has content but messages may need to be sent first", "system") 
                            logger.debug("UI has messages but conversation object is empty - possible unsaved state")
                        else:
                            self.append_output("⚠ No conversation content to save", "system")
                            logger.debug(f"No messages found in conversation {current_id}")
                        return
                    
                    logger.debug(f"Proceeding with save for conversation {current_id} with {message_count} messages")
                    
                    # Ensure any files currently in browser are linked to this conversation
                    await self._ensure_files_linked_to_conversation(current_id, ai_service.conversation_service)
                    
                    # Generate title if needed
                    if len(conversation.messages) >= 2:
                        if conversation.title in ["New Conversation", "Untitled Conversation"] or not conversation.title.strip():
                            generated_title = await ai_service.conversation_service.generate_conversation_title(current_id)
                            if generated_title:
                                await ai_service.conversation_service.update_conversation_title(current_id, generated_title)
                                logger.info(f"Generated title for saved conversation: {generated_title}")
                                self.append_output(f"💾 Conversation saved with title: {generated_title}", "system")
                            else:
                                self.append_output("💾 Conversation saved", "system")
                        else:
                            self.append_output(f"💾 Conversation '{conversation.title}' saved", "system")
                    else:
                        self.append_output("💾 Conversation saved", "system")
                    
                    # Refresh conversation list to reflect any title changes
                    await self._load_conversations()
                    
                except Exception as e:
                    logger.error(f"Failed to save conversation: {e}")
                    self.append_output(f"✗ Error saving conversation: {e}", "error")
            
            # Use Qt timer to safely handle async operations
            from PyQt6.QtCore import QTimer
            
            def run_async():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(save_conversation())
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Failed to execute save conversation async: {e}")
                    self.append_output(f"✗ Error: {e}", "error")
            
            QTimer.singleShot(100, run_async)
            
        except Exception as e:
            logger.error(f"Save conversation failed: {e}")
            self.append_output(f"✗ Error: {e}", "error")
    
    async def _ensure_files_linked_to_conversation(self, conversation_id: str, conversation_service):
        """Ensure any files currently in the file browser are linked to the conversation."""
        try:
            if not hasattr(self, 'file_browser_bar') or not self.file_browser_bar:
                logger.debug("No file browser bar available")
                return
            
            # Get all files currently in the browser
            all_files = self.file_browser_bar.get_all_files_info()
            if not all_files:
                logger.debug("No files in browser to link")
                return
            
            # Check if conversation exists, create new one if not
            try:
                conversation = await conversation_service.get_conversation(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found, creating new one")
                    # Create a new conversation to link files to
                    new_conversation_id = await conversation_service.create_conversation("New Conversation")
                    if new_conversation_id:
                        conversation_id = new_conversation_id
                        logger.info(f"Created new conversation {conversation_id} for file linking")
                        # Update current conversation reference
                        if hasattr(self, 'conversation_manager') and self.conversation_manager.has_ai_service():
                            ai_service = self.conversation_manager.get_ai_service()
                            if ai_service:
                                ai_service.set_current_conversation(conversation_id)
                    else:
                        logger.error("Failed to create new conversation for file linking")
                        return
            except Exception as conv_check_error:
                logger.error(f"Error checking conversation existence: {conv_check_error}")
                return
            
            # Get existing files for this conversation to avoid duplicates
            existing_files = await conversation_service.get_conversation_files(conversation_id)
            existing_file_ids = {f.file_id for f in existing_files} if existing_files else set()
            
            files_linked = 0
            for file_info in all_files:
                file_id = file_info['file_id']
                
                # Skip if already linked to conversation
                if file_id in existing_file_ids:
                    logger.debug(f"File {file_id} already linked to conversation")
                    continue
                
                # For files in browser that aren't yet linked, we need the file path
                # Check if we have this in our uploaded files tracking
                file_path = None
                if hasattr(self, '_file_id_to_path_map') and file_id in self._file_id_to_path_map:
                    file_path = self._file_id_to_path_map[file_id]
                elif hasattr(self, '_uploaded_files_paths'):
                    # Try to find by filename match (fallback)
                    for path in self._uploaded_files_paths:
                        import os
                        if os.path.basename(path) == file_info['filename']:
                            file_path = path
                            break
                
                if not file_path:
                    logger.warning(f"Could not find file path for {file_id} ({file_info['filename']})")
                    continue
                
                # Add file to conversation
                from datetime import datetime
                success = await conversation_service.add_file_to_conversation(
                    conversation_id=conversation_id,
                    file_id=file_id,
                    filename=file_info['filename'],
                    file_path=file_path,
                    file_size=file_info['file_size'],
                    file_type=file_info['file_type'],
                    metadata={
                        'save_timestamp': datetime.now().isoformat(),
                        'processing_status': file_info['processing_status'],
                        'is_enabled': file_info['is_enabled'],
                        'tokens_used': file_info['tokens_used']
                    }
                )
                
                if success:
                    files_linked += 1
                    logger.info(f"✅ Linked file {file_info['filename']} to conversation on save")
                else:
                    logger.warning(f"⚠️ Failed to link file {file_info['filename']} to conversation")
            
            if files_linked > 0:
                logger.info(f"📎 Linked {files_linked} files to conversation {conversation_id} during save")
                
        except Exception as e:
            logger.error(f"Failed to ensure files linked to conversation: {e}")
    
    def _start_new_conversation(self, save_current: bool = False):
        """Start a new conversation with optional saving of current."""
        try:
            if not self.conversation_manager:
                self.append_output("⚠ Conversation management not available", "error")
                return
            
            # CRITICAL FIX: Hide file browser bar for new conversation
            if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                self.file_browser_bar.hide_all_files()
                logger.info("📁 Hidden file browser bar for new conversation")
            
            # Clear internal file tracking
            if hasattr(self, '_uploaded_files'):
                self._uploaded_files.clear()
            
            # Get AI service for conversation integration
            ai_service = None
            if self.conversation_manager:
                ai_service = self.conversation_manager.get_ai_service()
            
            if not ai_service or not hasattr(ai_service, 'conversation_service'):
                self.append_output("⚠ AI service doesn't support conversation management", "error")
                return
            
            async def create_new_conversation():
                try:
                    current_id = ai_service.get_current_conversation_id()
                    
                    if save_current and current_id:
                        # Save current conversation with generated title
                        await ai_service._save_current_conversation()
                        
                        # Generate title if needed
                        conversation = await ai_service.conversation_service.get_conversation(current_id, include_messages=True)
                        if conversation and len(conversation.messages) >= 2:
                            if conversation.title in ["New Conversation", "Untitled Conversation"] or not conversation.title.strip():
                                generated_title = await ai_service.conversation_service.generate_conversation_title(current_id)
                                if generated_title:
                                    await ai_service.conversation_service.update_conversation_title(current_id, generated_title)
                                    logger.info(f"Generated title for saved conversation: {generated_title}")
                    
                    # Clear REPL output before starting new conversation
                    self.clear_output()
                    
                    # Start new conversation
                    new_id = await ai_service.start_new_conversation(title="New Conversation")
                    if new_id:
                        # Migrate any pending files to this conversation
                        self._migrate_pending_files_to_conversation(new_id)
                        
                        # Refresh conversation list
                        await self._load_conversations()
                        #self.append_output("✓ Started new conversation", "system")
                        if save_current and current_id:
                            self.append_output("💾 Previous conversation saved with auto-generated title", "system")
                        
                        # Add welcome message for new conversation
                        #self.append_output("💬 Ghostman Conversation Manager v2.0", "system")
                        self.append_output("🚀 New conversation started - type your message or 'help' for commands", "system")
                    else:
                        self.append_output("✗ Failed to start new conversation", "error")
                        
                except Exception as e:
                    logger.error(f"Failed to create new conversation: {e}")
                    self.append_output(f"✗ Error creating new conversation: {e}", "error")
            
            # Use Qt timer to safely handle async operations
            from PyQt6.QtCore import QTimer
            
            def run_async():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(create_new_conversation())
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Failed to execute new conversation async: {e}")
                    self.append_output(f"✗ Error: {e}", "error")
            
            QTimer.singleShot(100, run_async)
            
        except Exception as e:
            logger.error(f"New conversation failed: {e}")
            self.append_output(f"✗ Error: {e}", "error")
    
    def _title_mouse_press(self, event):
        """Handle mouse press on title bar for drag functionality."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint()
    
    def _title_mouse_move(self, event):
        """Handle mouse move on title bar for drag functionality."""
        if self._dragging and self._drag_pos:
            # Get the floating REPL window
            floating_repl = self.parent()
            while floating_repl and not hasattr(floating_repl, 'move'):
                floating_repl = floating_repl.parent()
            
            if floating_repl:
                # Calculate new position
                diff = event.globalPosition().toPoint() - self._drag_pos
                new_pos = floating_repl.pos() + diff
                floating_repl.move(new_pos)
                self._drag_pos = event.globalPosition().toPoint()
    
    def _title_mouse_release(self, event):
        """Handle mouse release on title bar for drag functionality."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_pos = None
    
    def _init_resize_functionality(self):
        """Load saved window dimensions - resize handled by FloatingREPL window."""
        # Load saved dimensions
        self._load_window_dimensions()
    
    
    def _load_window_dimensions(self):
        """Load window dimensions from settings."""
        if not _global_settings:
            return
            
        try:
            width = _global_settings.get('ui.repl_width', 500)
            height = _global_settings.get('ui.repl_height', 400)
            
            # Get the floating REPL window and set its size
            floating_repl = self.parent()
            while floating_repl and not hasattr(floating_repl, 'resize'):
                floating_repl = floating_repl.parent()
            
            if floating_repl:
                floating_repl.resize(width, height)
                logger.debug(f"Loaded REPL dimensions: {width}x{height}")
        except Exception as e:
            logger.warning(f"Failed to load window dimensions: {e}")
    
    def _save_window_dimensions(self):
        """Save current window dimensions to settings."""
        if not _global_settings:
            return
            
        try:
            # Get the floating REPL window
            floating_repl = self.parent()
            while floating_repl and not hasattr(floating_repl, 'size'):
                floating_repl = floating_repl.parent()
            
            if floating_repl:
                size = floating_repl.size()
                _global_settings.set('ui.repl_width', size.width())
                _global_settings.set('ui.repl_height', size.height())
                logger.debug(f"Saved REPL dimensions: {size.width()}x{size.height()}")
        except Exception as e:
            logger.warning(f"Failed to save window dimensions: {e}")
    
# Resize functionality moved to FloatingREPL window with corner grips
    
    def save_current_conversation(self):
        """Save the current conversation."""
        try:
            if not self.conversation_manager:
                logger.warning("No conversation manager available for saving")
                return
            
            # Get AI service for conversation integration
            ai_service = self.conversation_manager.get_ai_service()
            if not ai_service or not hasattr(ai_service, 'conversation_service'):
                logger.warning("AI service doesn't support conversation management")
                return
            
            current_id = ai_service.get_current_conversation_id()
            if not current_id:
                logger.info("No current conversation to save")
                return
            
            async def save_conversation():
                try:
                    # Save current conversation
                    await ai_service._save_current_conversation()
                    
                    # Generate title if needed
                    conversation = await ai_service.conversation_service.get_conversation(current_id, include_messages=True)
                    if conversation and len(conversation.messages) >= 2:
                        if conversation.title in ["New Conversation", "Untitled Conversation"] or not conversation.title.strip():
                            generated_title = await ai_service.conversation_service.generate_conversation_title(current_id)
                            if generated_title:
                                await ai_service.conversation_service.update_conversation_title(current_id, generated_title)
                                logger.info(f"Generated title for saved conversation: {generated_title}")
                    
                    logger.info(f"Conversation saved successfully: {current_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to save conversation: {e}")
            
            # Run async save operation
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(save_conversation())
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Failed to execute save conversation async: {e}")
                
        except Exception as e:
            logger.error(f"Save conversation failed: {e}")
    
    async def _create_conversation_async(self, title: str, initial_message: str = None) -> Optional['Conversation']:
        """Create a conversation asynchronously with proper database persistence."""
        try:
            if not self.conversation_manager:
                logger.error("No conversation manager available")
                return None
            
            # Create conversation with initial message to ensure it's not considered empty
            conversation = await self.conversation_manager.create_conversation(
                title=title,
                initial_message=initial_message or "Conversation started."
            )
            
            if conversation:
                logger.info(f"✓ Created conversation: {conversation.id} - {conversation.title}")
                
                # Associate conversation with current tab if tab system is available
                if hasattr(self, 'tab_manager') and self.tab_manager:
                    active_tab = self.tab_manager.get_active_tab()
                    if active_tab:
                        self.tab_manager.associate_conversation_with_tab(
                            active_tab.tab_id, 
                            conversation.id, 
                            conversation.title
                        )
                        logger.info(f"✓ Associated conversation {conversation.id} with tab {active_tab.tab_id}")
                
                # Migrate any pending files to this conversation
                self._migrate_pending_files_to_conversation(conversation.id)
                return conversation
            else:
                logger.error("✗ Conversation creation returned None")
                return None
                
        except Exception as e:
            logger.error(f"✗ Failed to create conversation async: {e}")
            return None
    
    def _migrate_pending_files_to_conversation(self, conversation_id: str):
        """Migrate files with pending_conversation_id to the actual conversation."""
        try:
            if not hasattr(self, 'rag_session') or not self.rag_session:
                return
            
            # Get the pending conversation ID that was used for file uploads
            pending_id = getattr(self, '_pending_conversation_id', None)
            if not pending_id:
                logger.debug("No pending conversation ID to migrate")
                return
                
            logger.info(f"🔄 Migrating files from pending ID {pending_id[:8]}... to conversation: {conversation_id}")
            
            # Update the current conversation ID so future queries use the real conversation
            self._current_conversation_id = conversation_id
            
            # Clear the pending conversation ID since it's no longer needed
            if hasattr(self, '_pending_conversation_id'):
                delattr(self, '_pending_conversation_id')
                logger.info("✓ Cleared pending conversation ID - now using real conversation")
                
            # Note: The FAISS client handles the OR logic for pending_conversation_id automatically
            # Files uploaded with pending_conversation_id will be found when filtering by the real conversation_id
            # because the filtering logic looks for: conversation_id = real_id OR pending_conversation_id = real_id
            logger.info(f"✅ Files migrated to conversation {conversation_id} - isolation maintained")
            
        except Exception as e:
            logger.error(f"Failed to migrate pending files: {e}")
    
    def _toggle_search(self):
        """Toggle search bar visibility."""
        try:
            if not hasattr(self, 'search_frame') or not self.search_frame:
                logger.warning("Search bar not initialized")
                return
            
            if self.search_frame.isVisible():
                self._close_search()
            else:
                # Show search bar and focus on search input
                self.search_frame.setVisible(True)
                if hasattr(self, 'search_input'):
                    self.search_input.setFocus()
                    self.search_input.selectAll()
                logger.debug("Search bar opened")
                
            # Update search button visual state
            self._update_search_button_state()
                
        except Exception as e:
            logger.error(f"Failed to toggle search: {e}")
    
    def _close_search(self):
        """Close search bar and clear highlights."""
        try:
            if hasattr(self, 'search_frame'):
                self.search_frame.setVisible(False)
            
            # Clear search highlights in conversation display
            if hasattr(self, 'output_display'):
                # Clear highlights by refreshing the conversation display
                self._clear_search_highlights()
            
            # Clear search input
            if hasattr(self, 'search_input'):
                self.search_input.clear()
            
            # Reset search state
            self.current_search_matches = []
            self.current_search_index = -1
            self.current_search_query = ""
            
            # Clean up stored HTML content
            if hasattr(self, '_original_html_content'):
                delattr(self, '_original_html_content')
            
            logger.debug("Search closed and highlights cleared")
            
            # Update search button visual state
            self._update_search_button_state()
            
        except Exception as e:
            logger.error(f"Failed to close search: {e}")
    
    def _toggle_file_browser(self):
        """Toggle file browser bar visibility for the active tab."""
        logger.info("File browser toggle clicked")
        try:
            # Get file browser stack
            if not self.tab_manager or not hasattr(self.tab_manager, 'file_browser_stack'):
                logger.error("No tab manager or file browser stack available")
                return

            active_tab = self.tab_manager.get_active_tab()
            if not active_tab:
                logger.error("No active tab available")
                return

            # Toggle the file browser stack visibility (shows/hides the entire container)
            stack = self.tab_manager.file_browser_stack
            current_visibility = stack.isVisible()
            logger.info(f"Current file browser visibility: {current_visibility}")

            # Toggle visibility
            new_visibility = not current_visibility
            stack.setVisible(new_visibility)
            active_tab.file_browser_visible = new_visibility

            # Update upload button visual state
            self._update_upload_button_state()

            logger.info(f"File browser toggled to: {new_visibility}")

        except Exception as e:
            logger.error(f"Failed to toggle file browser: {e}")
            import traceback
            traceback.print_exc()
    
    def _close_file_browser(self):
        """Close file browser bar."""
        try:
            if hasattr(self, 'file_browser_bar'):
                self.file_browser_bar.setVisible(False)
            
            logger.debug("File browser bar closed")
            
            # Update upload button visual state
            self._update_upload_button_state()
            
        except Exception as e:
            logger.error(f"Failed to close file browser: {e}")
    
    def _search_next(self):
        """Navigate to next search match."""
        try:
            if not self.current_search_matches or len(self.current_search_matches) == 0:
                return
            
            # Move to next match
            self.current_search_index = (self.current_search_index + 1) % len(self.current_search_matches)
            
            # Scroll to and highlight current match
            self._highlight_current_match()
            
            # Update search status
            self.search_status_label.setText(
                f"{self.current_search_index + 1} of {len(self.current_search_matches)}"
            )
            
            logger.debug(f"Moved to search match {self.current_search_index + 1}/{len(self.current_search_matches)}")
            
        except Exception as e:
            logger.error(f"Failed to navigate to next search match: {e}")
    
    def _search_previous(self):
        """Navigate to previous search match."""
        try:
            if not self.current_search_matches or len(self.current_search_matches) == 0:
                return
            
            # Move to previous match
            self.current_search_index = (self.current_search_index - 1) % len(self.current_search_matches)
            
            # Scroll to and highlight current match
            self._highlight_current_match()
            
            # Update search status
            self.search_status_label.setText(
                f"{self.current_search_index + 1} of {len(self.current_search_matches)}"
            )
            
            logger.debug(f"Moved to search match {self.current_search_index + 1}/{len(self.current_search_matches)}")
            
        except Exception as e:
            logger.error(f"Failed to navigate to previous search match: {e}")
    
    def _perform_conversation_search(self):
        """Perform search in the current conversation display."""
        try:
            if not hasattr(self, 'search_input') or not self.search_input:
                return
            
            query = self.search_input.text().strip()
            if not query:
                self._clear_search_highlights()
                return
            
            self.current_search_query = query
            
            # Search in conversation display content
            self._find_matches_in_conversation(query)
            
            # Update search navigation
            if self.current_search_matches:
                self.current_search_index = 0
                self._highlight_current_match()
                
                # Update search status
                self.search_status_label.setText(
                    f"1 of {len(self.current_search_matches)}"
                )
            else:
                self.current_search_index = -1
                self.search_status_label.setText("No matches")
            
            logger.debug(f"Search completed: {len(self.current_search_matches)} matches for '{query}'")
            
        except Exception as e:
            logger.error(f"Failed to perform conversation search: {e}")
    
    def _find_matches_in_conversation(self, query: str):
        """Find all matches of query in current conversation display using plain text search with correct positioning."""
        try:
            self.current_search_matches = []
            
            if not hasattr(self, 'output_display') or not self.output_display:
                return
            
            if not query.strip():
                return
            
            document = self.output_display.document()
            
            # Store original HTML content to restore later if needed
            if not hasattr(self, '_original_html_content'):
                self._original_html_content = document.toHtml()
            
            # Get plain text content for accurate search
            plain_text = document.toPlainText()
            
            # Determine case sensitivity
            case_sensitive = hasattr(self, 'case_sensitive_checkbox') and self.case_sensitive_checkbox.isChecked()
            
            # Handle regex vs literal search
            if hasattr(self, 'regex_checkbox') and self.regex_checkbox.isChecked():
                # Use regex search on plain text
                import re
                try:
                    regex_flags = 0 if case_sensitive else re.IGNORECASE
                    pattern = re.compile(query, regex_flags)
                    
                    # Find all matches in plain text
                    for match in pattern.finditer(plain_text):
                        plain_start = match.start()
                        plain_end = match.end()
                        matched_text = match.group()
                        
                        # Map plain text positions to document positions
                        doc_cursor = self._map_plain_text_to_document_cursor(document, plain_start, plain_end, matched_text)
                        if doc_cursor and not doc_cursor.isNull():
                            self.current_search_matches.append({
                                'start': doc_cursor.selectionStart(),
                                'end': doc_cursor.selectionEnd(),
                                'text': doc_cursor.selectedText(),
                                'cursor': QTextCursor(doc_cursor)
                            })
                        
                except re.error as e:
                    if hasattr(self, 'search_status_label'):
                        self.search_status_label.setText(f"Invalid regex")
                    logger.warning(f"Invalid regex pattern '{query}': {e}")
                    return
                except Exception as e:
                    if hasattr(self, 'search_status_label'):
                        self.search_status_label.setText(f"Regex error")
                    logger.warning(f"Regex search error for '{query}': {e}")
                    return
            else:
                # Use literal string search on plain text
                search_text = plain_text if case_sensitive else plain_text.lower()
                search_query = query if case_sensitive else query.lower()
                
                start_pos = 0
                while True:
                    # Find next occurrence in plain text
                    plain_start = search_text.find(search_query, start_pos)
                    if plain_start == -1:
                        break
                    
                    plain_end = plain_start + len(query)
                    matched_text = plain_text[plain_start:plain_end]
                    
                    # Map plain text positions to document positions
                    doc_cursor = self._map_plain_text_to_document_cursor(document, plain_start, plain_end, matched_text)
                    if doc_cursor and not doc_cursor.isNull():
                        self.current_search_matches.append({
                            'start': doc_cursor.selectionStart(),
                            'end': doc_cursor.selectionEnd(),
                            'text': doc_cursor.selectedText(),
                            'cursor': QTextCursor(doc_cursor)
                        })
                    
                    # Move to next potential match
                    start_pos = plain_start + 1
            
            logger.debug(f"Found {len(self.current_search_matches)} matches for '{query}' using plain text search with position mapping")
            
        except Exception as e:
            logger.error(f"Failed to find matches in conversation: {e}")
    
    def _map_plain_text_to_document_cursor(self, document, plain_start: int, plain_end: int, expected_text: str):
        """Map plain text positions to document cursor positions.
        
        This method handles the discrepancy between plain text positions and
        document positions caused by HTML formatting in QTextDocument.
        
        Args:
            document: QTextDocument instance
            plain_start: Start position in plain text
            plain_end: End position in plain text  
            expected_text: The text we expect to find at this position
            
        Returns:
            QTextCursor with correct selection, or None if mapping failed
        """
        try:
            # Create cursor and navigate to the plain text position
            cursor = QTextCursor(document)
            
            # Method 1: Use movePosition with character count
            # This accounts for the fact that HTML formatting affects internal positioning
            cursor.setPosition(0)  # Start at beginning
            
            # Move forward by the plain text character count
            # QTextCursor.movePosition handles HTML tags correctly
            for i in range(plain_start):
                if not cursor.movePosition(QTextCursor.MoveOperation.NextCharacter):
                    break
            
            # Mark the start position
            start_pos = cursor.position()
            
            # Select the expected text length
            cursor.setPosition(start_pos)
            for i in range(len(expected_text)):
                if not cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor):
                    break
            
            # Verify the selection matches expected text (case-insensitive for verification)
            selected_text = cursor.selectedText()
            if selected_text.lower() == expected_text.lower():
                return cursor
            
            # Method 2: Fallback - use character-by-character navigation with verification
            # This is more robust but slower
            cursor.setPosition(0)
            plain_text = document.toPlainText()
            
            current_plain_pos = 0
            while current_plain_pos < len(plain_text) and cursor.position() < document.characterCount():
                if current_plain_pos == plain_start:
                    # Found our start position, now select the text
                    start_pos = cursor.position()
                    
                    # Select character by character to ensure we get the right text
                    cursor.setPosition(start_pos)
                    selected_chars = 0
                    while selected_chars < len(expected_text) and cursor.position() < document.characterCount():
                        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                        selected_chars += 1
                    
                    # Verify selection
                    selected_text = cursor.selectedText()
                    if selected_text.lower() == expected_text.lower():
                        return cursor
                    
                    break
                
                # Move to next character in both plain text and document
                if not cursor.movePosition(QTextCursor.MoveOperation.NextCharacter):
                    break
                current_plain_pos += 1
            
            # Method 3: Final fallback - search using QTextDocument.find() with exact text
            # This should work as a last resort
            cursor = QTextCursor(document)
            case_sensitive = hasattr(self, 'case_sensitive_checkbox') and self.case_sensitive_checkbox.isChecked()
            search_options = QTextDocument.FindFlag.FindCaseSensitively if case_sensitive else QTextDocument.FindFlag(0)
            
            # Try to find the exact expected text
            found_cursor = document.find(expected_text, cursor, search_options)
            if not found_cursor.isNull():
                # Verify this is actually the match we want by checking context
                found_start = found_cursor.selectionStart()
                
                # Check if this could be our target match by verifying surrounding context
                context_cursor = QTextCursor(document)
                context_cursor.setPosition(max(0, found_start - 10))
                context_cursor.setPosition(min(document.characterCount(), found_cursor.selectionEnd() + 10), QTextCursor.MoveMode.KeepAnchor)
                context = context_cursor.selectedText()
                
                # If the context seems reasonable, use this match
                if expected_text.lower() in context.lower():
                    return found_cursor
            
            logger.warning(f"Failed to map plain text position {plain_start}-{plain_end} for text '{expected_text}'")
            return None
            
        except Exception as e:
            logger.error(f"Error mapping plain text to document cursor: {e}")
            return None
    
    def _highlight_current_match(self):
        """Highlight the current search match and scroll to it."""
        try:
            if not self.current_search_matches or self.current_search_index < 0:
                return

            # MixedContentDisplay doesn't support text highlighting like QTextEdit
            # Scroll to bottom as a simple fallback
            if self.output_display:
                self.output_display.scroll_to_bottom()

            logger.debug("Search highlighting not supported with MixedContentDisplay")

        except Exception as e:
            logger.error(f"Failed to highlight current match: {e}")
    
    def _highlight_all_matches(self):
        """Highlight all search matches with subtle background color."""
        # MixedContentDisplay doesn't support text highlighting
        logger.debug("Search highlighting not supported with MixedContentDisplay")
    
    def _clear_search_highlights(self):
        """Clear all search highlights from conversation display without destroying original formatting."""
        try:
            # MixedContentDisplay doesn't support text highlighting
            # Just clear the stored positions for cleanup
            if hasattr(self, '_current_highlight_positions'):
                self._current_highlight_positions = []
            if hasattr(self, '_all_match_positions'):
                self._all_match_positions = []
            
            logger.debug("Search position cleanup completed for MixedContentDisplay")
            
        except Exception as e:
            logger.error(f"Failed to clear search highlights: {e}")
    
    def _on_search_text_changed(self, text: str):
        """Handle search input text changes with debouncing."""
        try:
            # Stop any pending search
            if hasattr(self, 'search_timer'):
                self.search_timer.stop()
            
            # Clear matches if search is empty
            if not text.strip():
                self.current_search_matches = []
                self.current_search_index = -1
                self._clear_search_highlights()
                self.search_status_label.setText("0/0")
                return
            
            # Start debounce timer for search-as-you-type
            if hasattr(self, 'search_timer'):
                self.search_timer.start(300)  # 300ms debounce
            
        except Exception as e:
            logger.error(f"Failed to handle search text change: {e}")
    
    def _on_regex_toggled(self):
        """Handle regex checkbox toggle - re-search if there's a query."""
        try:
            if self.search_input.text().strip():
                # Re-perform search with new regex setting
                self._perform_conversation_search()
            
            # Update placeholder text to reflect mode
            if self.regex_checkbox.isChecked():
                self.search_input.setPlaceholderText("Search with regex pattern...")
            else:
                self.search_input.setPlaceholderText("Search in conversation...")
                
            logger.debug(f"Regex mode toggled: {self.regex_checkbox.isChecked()}")
            
        except Exception as e:
            logger.error(f"Failed to handle regex toggle: {e}")
    
    
    
    @pyqtSlot(str)
    def _on_conversation_context_switched(self, conversation_id: str):
        """Handle conversation context switching from tab manager."""
        try:
            logger.info(f"🔄 Conversation context switched to: {conversation_id}")

            if not conversation_id:
                # New tab with no conversation - just update references
                # DON'T clear output or files - they belong to the previous tab!
                # Tab manager handles saving/restoring per-tab state
                logger.info("📁 No conversation ID - updating references only (tab manager handles state)")
                self.current_conversation = None
                self._current_conversation_id = None
                # Tab manager will restore the correct state for this tab
                return

            # CRITICAL FIX: When tab manager is active, DON'T reload conversation
            # Tab manager already restored the cached output/files for this tab
            # Reloading would overwrite the cache with database content!
            if hasattr(self, 'tab_manager') and self.tab_manager:
                logger.info(f"⏭️⏭️⏭️ TAB MANAGER ACTIVE - SKIPPING CONVERSATION RELOAD (using cached state) ⏭️⏭️⏭️")
                # Just update the conversation reference, don't reload messages
                self._current_conversation_id = conversation_id

                # Load conversation object but DON'T call _switch_to_conversation
                if self.conversation_manager:
                    async def load_conv_ref_only():
                        try:
                            conversation = await self.conversation_manager.get_conversation(conversation_id)
                            if conversation:
                                self.current_conversation = conversation
                                self._update_status_label(conversation)
                                logger.info(f"✅ Updated conversation reference (cache preserved)")
                        except Exception as e:
                            logger.error(f"Failed to load conversation reference: {e}")

                    import asyncio
                    try:
                        # Try to get running event loop
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(load_conv_ref_only())
                        except RuntimeError:
                            # No running loop - skip async load (non-critical)
                            logger.debug("No running event loop - skipping conversation reference load")
                    except Exception as e:
                        logger.debug(f"Error loading conversation reference (non-critical): {e}")
                return

            # NO TAB MANAGER: Original behavior - load conversation from database
            # Find the conversation
            if not self.conversation_manager:
                logger.warning("Cannot switch conversation context - no conversation manager")
                return

            # Load the conversation asynchronously
            async def load_conversation():
                try:
                    conversation = await self.conversation_manager.get_conversation(conversation_id)
                    if conversation:
                        # Switch to the conversation (this will update UI)
                        self._switch_to_conversation(conversation)
                        logger.info(f"Switched to conversation context: {conversation.title}")
                    else:
                        logger.warning(f"Conversation {conversation_id} not found")

                except Exception as e:
                    logger.error(f"Failed to load conversation {conversation_id}: {e}")
            
            # Run the async operation
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule for later execution
                    asyncio.create_task(load_conversation())
                else:
                    loop.run_until_complete(load_conversation())
            except Exception as e:
                logger.error(f"Error running async conversation load: {e}")
                
        except Exception as e:
            logger.error(f"Error switching conversation context: {e}")
    
    @pyqtSlot(str, str) 
    def _on_tab_created(self, tab_id: str, title: str):
        """Handle tab creation event."""
        try:
            logger.debug(f"Tab created: {tab_id} - {title}")
            
            # Update active tab title if this is the current conversation
            if hasattr(self, 'tab_manager') and self.tab_manager:
                active_tab = self.tab_manager.get_active_tab()
                if active_tab and self.current_conversation:
                    # Sync tab title with conversation title
                    if self.current_conversation.title and self.current_conversation.title != title:
                        self.tab_manager.update_tab_title(tab_id, self.current_conversation.title)
                        
        except Exception as e:
            logger.error(f"Error handling tab creation: {e}")
    
    @pyqtSlot(str)
    def _on_tab_closed(self, tab_id: str):
        """Handle tab closure event."""
        try:
            logger.debug(f"Tab closed: {tab_id}")
            
            # UI cleanup is handled by tab manager
            # Just log the event for now
            
        except Exception as e:
            logger.error(f"Error handling tab closure: {e}")
    
    def _clear_current_conversation(self):
        """
        DEPRECATED: Tab manager now handles clearing per-tab state.
        This method only updates conversation references.

        DO NOT use this for clearing output, files, or UI state.
        The tab manager handles all per-tab state (output, files, scroll position).
        """
        try:
            # Update current tab's conversation reference
            if hasattr(self, 'tab_manager') and self.tab_manager:
                active_tab = self.tab_manager.get_active_tab()
                if active_tab:
                    active_tab.conversation_id = None

            # Update global references (will be overwritten when switching tabs)
            self.current_conversation = None
            self._current_conversation_id = None

            # DON'T clear output - tab manager handles this!
            # DON'T clear files - tab manager handles this!
            # DON'T hide file browser - tab manager handles this!
            # DON'T clear _uploaded_files - this is global state that breaks isolation!

            logger.debug("Cleared conversation references only (tab manager handles state)")

        except Exception as e:
            logger.error(f"Error clearing conversation references: {e}")
    
    def _sync_tab_with_conversation(self):
        """Sync active tab title with current conversation title."""
        try:
            if not (hasattr(self, 'tab_manager') and self.tab_manager and self.current_conversation):
                return
                
            active_tab = self.tab_manager.get_active_tab()
            if active_tab:
                conversation_title = self.current_conversation.title or "New Chat"
                if active_tab.title != conversation_title:
                    self.tab_manager.update_tab_title(active_tab.tab_id, conversation_title)
                    logger.debug(f"Synced tab title: {conversation_title}")
                    
        except Exception as e:
            logger.error(f"Error syncing tab with conversation: {e}")
    
    # Tab event handlers
    
    def _on_tab_created(self, tab_id: str):
        """Handle new tab creation."""
        logger.debug(f"New tab created: {tab_id}")
        # Tab is automatically switched to by the manager
    
    def _on_tab_closed(self, tab_id: str):
        """Handle tab closing."""
        logger.debug(f"Tab closed: {tab_id}")
        # Tab manager handles cleanup and switching to another tab
    
    def _on_new_tab_requested(self):
        """Handle new tab request from plus button."""
        if hasattr(self, 'tab_manager') and self.tab_manager:
            new_tab_id = self.tab_manager.create_tab()
            logger.debug(f"Created new tab from plus button: {new_tab_id}")
        else:
            logger.warning("Tab manager not available for new tab request")
    
    def _create_new_tab(self):
        """Create a new tab with conversation."""
        if not hasattr(self, 'tab_manager') or not self.tab_manager:
            logger.warning("Tab manager not available for new tab creation")
            return
            
        # If this is the first tab being created, we need to:
        # 1. Create a tab for the current content (Tab 1)  
        # 2. Create a new empty tab (Tab 2)
        # 3. Switch to the new empty tab
        
        if len(self.tab_manager.tabs) == 0:
            # First tab creation - preserve current content in Tab 1
            logger.info("Creating first tabs - preserving current content")
            
            # Create Tab 1 with current content/conversation  
            if (self.current_conversation and 
                self.current_conversation.title.strip() and 
                not self.current_conversation.title.startswith("[No response content") and
                not self.current_conversation.title.startswith("No response content")):
                # Use conversation title if available, not empty, and meaningful
                current_tab_title = self.current_conversation.title[:23] + "..." if len(self.current_conversation.title) > 25 else self.current_conversation.title
            else:
                # Use "Default" for first tab when no meaningful conversation title exists
                current_tab_title = "Default"
            
            first_tab_id = self.tab_manager.create_tab(title=current_tab_title, activate=False)
            first_tab = self.tab_manager.tabs.get(first_tab_id)
            # Note: Don't clear conversation_id here - the tab_created signal handler
            # already associated a conversation, and we shouldn't overwrite it
            if first_tab and first_tab.conversation_id:
                logger.info(f"Tab 1 created with conversation: {first_tab.conversation_id[:8]}")
            else:
                logger.info("Tab 1 created (conversation will be assigned by signal handler)")
            
            # Create Tab 2 as new empty tab
            new_tab_id = self.tab_manager.create_tab(title="Conversation", activate=True)
            logger.info(f"Created new empty tab: {new_tab_id}")
            
        else:
            # Normal tab creation - just create new tab
            new_tab_id = self.tab_manager.create_tab(title="Conversation")
            logger.debug(f"Created new tab: {new_tab_id}")
    
    # --- Tab Event Handlers ---
    
    def _on_tab_switched(self, old_tab_id: str, new_tab_id: str):
        """
        Handle tab switching - restore conversation context for the new tab.

        The tab manager already:
        - Saved old tab state (output, files, scroll position)
        - Restored new tab state (output, files, scroll position)
        - Showed files for new tab via show_files_for_tab()
        - Set file browser visibility based on file count

        This method handles conversation context switching.
        """
        try:
            logger.info(f"🔄 TAB SWITCH: {old_tab_id} → {new_tab_id}")

            # Get the conversation ID for the new tab
            new_conversation_id = None
            if self.tab_manager:
                new_conversation_id = self.tab_manager.get_conversation_for_tab(new_tab_id)

            logger.info(f"🔄 Conversation context switched to: {new_conversation_id[:8] if new_conversation_id else 'None'}")

            # Switch the conversation context in the AI service AND update self.current_conversation
            if new_conversation_id and self.conversation_manager:
                try:
                    ai_service = self.conversation_manager.get_ai_service()
                    if ai_service:
                        ai_service.set_current_conversation(new_conversation_id)
                        logger.info(f"✅ AI service conversation context switched to: {new_conversation_id[:8]}")

                        # CRITICAL: Update self.current_conversation to match the tab's conversation
                        # This ensures send_message() uses the correct conversation ID
                        try:
                            conversation_service = self.conversation_manager.conversation_service
                            if conversation_service:
                                conversation_obj = conversation_service.get_conversation(new_conversation_id)
                                if conversation_obj:
                                    self.current_conversation = conversation_obj
                                    logger.info(f"✅ Updated self.current_conversation to match tab conversation: {new_conversation_id[:8]}")
                                else:
                                    logger.warning(f"⚠️ Could not load conversation object for {new_conversation_id[:8]}")
                        except Exception as conv_load_error:
                            logger.error(f"Failed to load conversation object: {conv_load_error}")
                    else:
                        logger.warning("AI service not available for conversation switch")
                except Exception as conv_error:
                    logger.error(f"Failed to switch AI service conversation: {conv_error}")
            else:
                if not new_conversation_id:
                    logger.info("📁 No conversation ID - updating references only (tab manager handles state)")
                    # Clear current_conversation if no conversation for this tab
                    self.current_conversation = None
                if not self.conversation_manager:
                    logger.warning("No conversation manager available")

            logger.info(f"✅ Tab switch complete (tab manager handled state restoration)")

        except Exception as e:
            logger.error(f"Error handling tab switch: {e}")
    
    def _on_tab_created(self, tab_id: str):
        """Handle new tab creation - create a new conversation for the tab."""
        logger.info(f"")
        logger.info(f"{'='*80}")
        logger.info(f"💬 CREATING NEW CONVERSATION FOR TAB")
        logger.info(f"{'='*80}")
        logger.info(f"   Tab ID: {tab_id}")

        # Create a new conversation for this tab immediately
        if self.tab_manager and self.conversation_manager:
            try:
                # Create new conversation
                title = "New Conversation"

                logger.info(f"   📝 Conversation title: {title}")
                logger.info(f"")
                logger.info(f"   ⚙️ Creating conversation in database...")

                # Create conversation using async manager (thread-safe)
                # This ensures the conversation is in the database before we associate it with the tab
                conversation_id = None
                if hasattr(self.conversation_manager, 'conversation_service'):
                    try:
                        # Use the async manager's event loop to run the coroutine synchronously
                        from ...infrastructure.async_manager import get_async_manager
                        import asyncio
                        import concurrent.futures

                        async_manager = get_async_manager()
                        if async_manager and async_manager._loop:
                            # Use asyncio.run_coroutine_threadsafe with the async manager's loop
                            future = asyncio.run_coroutine_threadsafe(
                                self.conversation_manager.conversation_service.create_conversation(
                                    title=title,
                                    force_create=True
                                ),
                                async_manager._loop
                            )

                            # Wait for result with timeout
                            try:
                                conversation_obj = future.result(timeout=5.0)
                                if conversation_obj:
                                    conversation_id = conversation_obj.id
                                    logger.info(f"   ✅ Conversation created in database: {conversation_id[:8]}")
                                else:
                                    logger.error(f"   ❌ Conversation creation returned None")
                                    return
                            except concurrent.futures.TimeoutError:
                                logger.error(f"   ❌ Conversation creation timed out after 5s")
                                return
                        else:
                            logger.error(f"   ❌ AsyncManager not available or not initialized")
                            return
                    except Exception as create_error:
                        logger.error(f"   ❌ Failed to create conversation: {create_error}", exc_info=True)
                        return
                else:
                    logger.error(f"   ❌ No conversation_service available!")
                    return

                logger.info(f"")
                logger.info(f"   🔗 Associating conversation with tab...")

                # Associate conversation with tab
                self.tab_manager.associate_conversation_with_tab(tab_id, conversation_id, title)
                logger.info(f"   ✅ Conversation {conversation_id[:8]} → Tab {tab_id}")

                logger.info(f"")
                logger.info(f"   🎯 Setting conversation as active in AI service...")

                # Set this conversation as active in AI service
                ai_service = self.conversation_manager.get_ai_service()
                if ai_service:
                    ai_service.set_current_conversation(conversation_id)
                    logger.info(f"   ✅ AI service → Conversation {conversation_id[:8]}")
                else:
                    logger.warning(f"   ⚠️ AI service not available")

                # Set up link handling and context menu for this tab's output widget
                tab = self.tab_manager.tabs.get(tab_id)
                if tab and tab.output_display:
                    from PyQt6.QtCore import Qt
                    # Note: MixedContentDisplay is QScrollArea-based, not QTextEdit-based
                    # so it doesn't have setOpenExternalLinks() or anchorClicked signal
                    # Link handling is done in the HTML widgets it contains

                    # Enable custom context menu
                    tab.output_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    if hasattr(self, '_show_output_context_menu'):
                        tab.output_display.customContextMenuRequested.connect(self._show_output_context_menu)

                    # Apply theme colors to the tab's output widget
                    # Use the same approach as _style_output_display()
                    if hasattr(self, 'theme_manager') and self.theme_manager:
                        try:
                            colors = self.theme_manager.current_theme

                            # Apply opacity to background
                            alpha = max(0.0, min(1.0, getattr(self, '_panel_opacity', 0.90)))
                            if alpha >= 0.99:
                                bg_color = colors.background_primary
                            else:
                                if colors.background_primary.startswith('#'):
                                    r = int(colors.background_primary[1:3], 16)
                                    g = int(colors.background_primary[3:5], 16)
                                    b = int(colors.background_primary[5:7], 16)
                                    bg_color = f"rgba({r}, {g}, {b}, {alpha:.3f})"
                                else:
                                    bg_color = f"rgba(30, 30, 30, {alpha:.3f})"

                            # Create theme color dictionary
                            theme_colors = {
                                'bg_primary': bg_color,
                                'bg_secondary': colors.background_secondary,
                                'bg_tertiary': colors.background_tertiary,
                                'text_primary': colors.text_primary,
                                'text_secondary': colors.text_secondary,
                                'border': colors.border_primary,
                                'info': colors.status_info,
                                'warning': colors.status_warning,
                                'error': colors.status_error,
                                'keyword': colors.primary,
                                'string': colors.secondary,
                                'comment': colors.text_tertiary,
                                'function': colors.primary,
                                'number': colors.secondary,
                                'interactive': colors.interactive_normal,
                                'interactive_hover': colors.interactive_hover,
                                'selection': colors.primary
                            }

                            tab.output_display.set_theme_colors(theme_colors)
                            logger.info(f"   ✅ Theme colors applied to tab widget (opacity: {alpha:.3f})")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Failed to apply theme colors: {e}", exc_info=True)

                    logger.info(f"   ✅ Context menu and theme colors configured for tab widget")

                logger.info(f"")
                logger.info(f"   ✅ NEW REPL SESSION READY")
                logger.info(f"   Tab: {tab_id}")
                logger.info(f"   Conversation: {conversation_id}")
                logger.info(f"{'='*80}")
                logger.info(f"")

            except Exception as e:
                logger.error(f"")
                logger.error(f"{'='*80}")
                logger.error(f"❌ FAILED TO CREATE CONVERSATION")
                logger.error(f"{'='*80}")
                logger.error(f"   Tab: {tab_id}")
                logger.error(f"   Error: {e}")
                logger.error(f"{'='*80}")
                logger.error(f"")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback
                tab = self.tab_manager.tabs.get(tab_id)
                if tab:
                    tab.conversation_id = None
        else:
            logger.warning(f"")
            logger.warning(f"{'='*80}")
            logger.warning(f"⚠️ CANNOT CREATE CONVERSATION")
            logger.warning(f"{'='*80}")
            logger.warning(f"   Tab: {tab_id}")
            logger.warning(f"   tab_manager: {'✅' if self.tab_manager else '❌'}")
            logger.warning(f"   conversation_manager: {'✅' if self.conversation_manager else '❌'}")
            logger.warning(f"{'='*80}")
            logger.warning(f"")
    
    def _on_tab_closed(self, tab_id: str):
        """Handle tab closure."""
        logger.info(f"Tab closed: {tab_id}")
        # Note: Conversation cleanup could be added here if needed
    
    def _load_tab_conversation(self, tab_id: str, conversation_id: str):
        """Load conversation for a specific tab asynchronously."""
        try:
            conversation = asyncio.run(
                self.conversation_manager.get_conversation(conversation_id)
            )
            if conversation:
                self.current_conversation = conversation
                self._load_conversation_messages(conversation)
                logger.debug(f"Loaded conversation {conversation_id} for tab {tab_id}")
            else:
                logger.warning(f"Could not load conversation {conversation_id} for tab {tab_id}")
                self.clear_output()
                self.append_output("⚠ Could not load conversation", "warning")
        except Exception as e:
            logger.error(f"Error loading conversation for tab {tab_id}: {e}")
            self.clear_output()
            self.append_output(f"❌ Error loading conversation: {str(e)}", "error")
    
    
    def update_tab_title_for_conversation(self, conversation_id: str, new_title: str):
        """Update tab title when conversation title changes."""
        if not self.tab_manager:
            return
            
        # Find tab with this conversation ID
        for tab_id, tab in self.tab_manager.tabs.items():
            if tab.conversation_id == conversation_id:
                self.tab_manager.update_tab_title(tab_id, new_title)
                logger.debug(f"Updated tab {tab_id} title to '{new_title}' for conversation {conversation_id}")
                break
    
    def shutdown(self):
        """Shutdown the enhanced REPL widget."""
        logger.info("Shutting down Enhanced REPL Widget...")
        
        try:
            # Stop idle detector
            if hasattr(self, 'idle_detector'):
                self.idle_detector.check_timer.stop()
            
            # Stop autosave timer
            if hasattr(self, 'autosave_timer'):
                self._stop_autosave_timer()
                logger.debug("Autosave timer stopped during shutdown")
            
            # Stop any running AI threads
            if hasattr(self, 'ai_thread') and self.ai_thread.isRunning():
                self.ai_thread.quit()
                self.ai_thread.wait(3000)  # Wait up to 3 seconds
            
            # Stop and cleanup processing threads
            if hasattr(self, '_processing_threads'):
                logger.info(f"Cleaning up {len(self._processing_threads)} processing threads...")
                for thread, processor in self._processing_threads:
                    try:
                        if thread.isRunning():
                            thread.quit()
                            thread.wait(2000)  # Wait up to 2 seconds
                        thread.deleteLater()
                        processor.deleteLater()
                    except Exception as e:
                        logger.error(f"Error cleaning up processing thread: {e}")
                self._processing_threads.clear()
                logger.info("Processing threads cleanup completed")
            
            # Clear summarization queue
            self.summarization_queue.clear()
            self.is_summarizing = False
            
            # Clean up tab manager
            if hasattr(self, 'tab_manager') and self.tab_manager:
                self.tab_manager.cleanup()
                logger.debug("Tab manager cleaned up")
            
            # Clear conversation references
            self.current_conversation = None
            self.conversations_list.clear()
            
            logger.info("✓ Enhanced REPL Widget shut down successfully")

        except Exception as e:
            logger.error(f"✗ Error during REPL widget shutdown: {e}")

    def showEvent(self, event):
        """Handle show event - apply window opacity on first show."""
        super().showEvent(event)

        # Apply window opacity once when widget is first shown
        # This ensures opacity is applied after widget is added to window
        if not hasattr(self, '_opacity_applied_on_show'):
            parent_window = self.window()
            if parent_window and hasattr(self, '_panel_opacity'):
                parent_window.setWindowOpacity(self._panel_opacity)
                self._opacity_applied_on_show = True
                logger.debug(f"Applied window opacity on show: {self._panel_opacity:.3f}")