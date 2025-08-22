"""
REPL Widget for Ghostman.

Provides a Read-Eval-Print-Loop interface for interacting with the AI.
"""

import logging
import asyncio
import html
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("ghostman.repl_widget")
# Markdown rendering imports
try:
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    
    logger.warning("Markdown library not available - falling back to plain text rendering")
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QLabel, QFrame, QComboBox,
    QToolButton, QMenu, QProgressBar, QListWidget,
    QListWidgetItem, QApplication, QMessageBox, QDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QSize, pyqtSlot
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QTextCharFormat, QColor, QPalette, QIcon, QPixmap, QAction

# Import startup service for preamble
from ...application.startup_service import startup_service
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
            # Configure markdown processor with AI-friendly extensions
            self.md_processor = markdown.Markdown(
                extensions=[
                    'fenced_code',  # ```code blocks```
                    'tables',       # Table support
                    'nl2br',        # Newline to <br>
                    'toc',          # Table of contents
                    'attr_list',    # Attribute lists {: .class}
                ],
                extension_configs={
                    'fenced_code': {
                        'lang_prefix': 'language-',
                    },
                    'toc': {
                        'permalink': False,  # Don't add permalink anchors
                    }
                },
                # Output format optimized for Qt HTML rendering
                output_format='html5',
                tab_length=4
            )
        
        # Update color scheme based on theme or use defaults
        self._update_color_scheme()
        
        # Performance cache for repeated renders (small cache to avoid memory issues)
        self._render_cache = {}
        self._cache_max_size = 100
    
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
            # Process markdown to HTML
            html_content = self.md_processor.convert(text)
            
            # Apply message-type styling to the HTML
            styled_html = self._apply_color_styling(html_content, base_color, style)
            
            # Clean up and optimize for Qt rendering
            styled_html = self._optimize_qt_html(styled_html)
            
            # Reset markdown processor for next use
            self.md_processor.reset()
            
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
        
        # Wrap entire content with base color and font configuration
        styled_html = f'<div style="color: {base_color}; line-height: {{\'1.4\'}}; {font_css};">{html_content}</div>'
        
        # Apply specific styling to elements
        replacements = {
            '<code>': f'<code style="background-color: rgba(255,255,255,0.1); padding: {{\'2px\'}} {{\'4px\'}}; border-radius: {{\'3px\'}}; color: {style_colors["code"]}; font-family: Consolas, Monaco, monospace;">',
            '<pre>': f'<pre style="background-color: rgba(255,255,255,0.05); padding: {{\'8px\'}}; border-radius: {{\'4px\'}}; border-left: {{\'3px\'}} solid {base_color}; margin: {{\'4px\'}} {{\'0\'}}; overflow-x: auto;">',
            '<em>': f'<em style="color: {style_colors["em"]}; font-style: italic;">',
            '<strong>': f'<strong style="color: {style_colors["strong"]}; font-weight: bold;">',
            '<h1>': f'<h1 style="color: {style_colors["h1"]}; font-size: {{\'1.4em\'}}; margin: {{\'8px\'}} {{\'0\'}} {{\'4px\'}} {{\'0\'}}; border-bottom: {{\'2px\'}} solid {base_color};">',
            '<h2>': f'<h2 style="color: {style_colors["h2"]}; font-size: {{\'1.3em\'}}; margin: {{\'6px\'}} {{\'0\'}} {{\'3px\'}} {{\'0\'}}; border-bottom: {{\'1px\'}} solid {base_color};">',
            '<h3>': f'<h3 style="color: {style_colors["h3"]}; font-size: {{\'1.2em\'}}; margin: {{\'4px\'}} {{\'0\'}} {{\'2px\'}} {{\'0\'}};">',
            '<blockquote>': f'<blockquote style="color: {style_colors["blockquote"]}; border-left: {{\'3px\'}} solid {base_color}; padding-left: {{\'12px\'}}; margin: {{\'4px\'}} {{\'0\'}}; font-style: italic;">',
            '<ul>': '<ul style="margin: 4px 0; padding-left: 20px;">',
            '<ol>': '<ol style="margin: 4px 0; padding-left: 20px;">',
            '<li>': f'<li style="margin: {{\'2px\'}} {{\'0\'}};">',
            '<table>': f'<table style="border-collapse: collapse; margin: 8px 0; border: 1px solid {base_color};">',
            '<th>': f'<th style="padding: 4px 8px; border: 1px solid {base_color}; background-color: rgba(255,255,255,0.1); font-weight: bold;">',
            '<td>': f'<td style="padding: 4px 8px; border: 1px solid {base_color};">',
        }
        
        for old, new in replacements.items():
            styled_html = styled_html.replace(old, new)
        
        # Handle links with special care
        styled_html = re.sub(
            r'<a href="([^"]+)">',
            f'<a href="\\1" style="color: {style_colors["a"]}; text-decoration: underline;">',
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
        
        # Panel (frame) opacity (only background, not text/content). 0.0 - 1.0
        # Initialize with default 90% opacity
        self._panel_opacity = 0.90
        
        # Conversation management
        self.conversation_manager: Optional[ConversationManager] = None
        self.current_conversation: Optional[Conversation] = None
        self.conversations_list: List[Conversation] = []
        
        # Error handling and resend functionality
        self.last_failed_message = None
        
        # Idle detection for background summarization
        self.idle_detector = IdleDetector(idle_threshold_minutes=5)
        self.idle_detector.idle_detected.connect(self._on_idle_detected)
        
        # Background summarization state
        self.summarization_queue: List[str] = []  # conversation IDs
        self.is_summarizing = False
        
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

        self._init_ui()
        self._apply_styles()
        self._update_component_themes()  # Apply theme to all components after UI init
        self._init_conversation_manager()
        
        # Load conversations after UI is fully initialized
        QTimer.singleShot(100, self._load_conversations_deferred)
        
        # Load dimensions after UI is fully initialized
        QTimer.singleShot(200, self._load_window_dimensions)
        
        logger.info("Enhanced REPLWidget initialized with conversation management")
    
    def _init_theme_system(self):
        """Initialize theme system connection."""
        if THEME_SYSTEM_AVAILABLE:
            try:
                self.theme_manager = get_theme_manager()
                # Connect to theme change signal for live updates
                self.theme_manager.theme_changed.connect(self._on_theme_changed)
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
            
            # Update conversation selector styling
            if hasattr(self, 'conversation_selector'):
                self._style_conversation_selector()
            
            # Update send button styling
            if hasattr(self, 'send_button'):
                self._style_send_button()
            
            # Update search elements if they exist
            if hasattr(self, 'search_status_label'):
                status_color = self.theme_manager.current_theme.text_tertiary
                self.search_status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
            
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
            
            logger.debug("REPL widget styles updated for new theme")
        except Exception as e:
            logger.error(f"Failed to update REPL widget theme: {e}")
    
    def _force_comprehensive_style_refresh(self):
        """Force a comprehensive style refresh for all UI elements."""
        try:
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
            
            self.output_display.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_color};
                    color: {colors.text_primary};
                    border: none;
                    selection-background-color: {colors.primary};
                    selection-color: {colors.background_primary};
                }}
                QScrollBar:vertical {{
                    background: {colors.background_secondary};
                    width: 12px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical {{
                    background: {colors.interactive_normal};
                    border-radius: 6px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {colors.interactive_hover};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    border: none;
                    background: none;
                }}
            """)
        except Exception as e:
            logger.warning(f"Failed to style output display: {e}")
    
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
                            border: 1px solid {colors.border_secondary};
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
            
            # Update conversation selector if it exists
            if hasattr(self, 'conversation_selector'):
                self.conversation_selector.setStyleSheet(StyleTemplates.get_combo_box_style(colors))
            
            # Update search frame if it exists
            if hasattr(self, 'search_frame'):
                self.search_frame.setStyleSheet(StyleTemplates.get_search_frame_style(colors))
            
            # Update status labels to use theme colors
            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(StyleTemplates.get_label_style(colors, "secondary"))
            
            if hasattr(self, 'search_status_label'):
                self.search_status_label.setStyleSheet(StyleTemplates.get_label_style(colors, "tertiary"))
            
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
            
            if hasattr(self, 'title_settings_btn'):
                self._load_gear_icon(self.title_settings_btn)
            
            if hasattr(self, 'title_new_btn'):
                self._load_plus_icon(self.title_new_btn)
            
            if hasattr(self, 'chat_btn'):
                self._load_chat_icon()
            
            if hasattr(self, 'attach_btn'):
                self._load_chain_icon()
            
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
            self._update_search_button_state()
            self._update_attach_button_state()
            self._update_pin_button_state()
            
            # Reload theme-specific icons
            self._load_search_icon()
            self._load_chain_icon()
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
                text_color = getattr(colors, 'text_primary', '#FFFFFF')

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
            # Fallback to improved colors without background - force opacity to 1.0
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
        """Get theme-aware styling for search input."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            return f"""
                QLineEdit {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_primary};
                    border: {{'1px'}} solid {colors.border_secondary};
                    padding: {{'4px'}} {{'6px'}};
                    border-radius: {{'3px'}};
                    font-size: {{'11px'}};
                }}
                QLineEdit:focus {{
                    border-color: {colors.border_focus};
                    background-color: {colors.background_tertiary};
                }}
            """
        else:
            return """
                QLineEdit {
                    background-color: rgba(30, 30, 30, 0.8);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    padding: 4px 6px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border-color: #FFA500;
                    background-color: rgba(40, 40, 40, 0.9);
                }
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
            else:
                logger.error("✗ Failed to initialize conversation manager")
                self.conversation_manager = None
        except Exception as e:
            logger.error(f"✗ Conversation manager initialization failed: {e}")
            self.conversation_manager = None
    
    def _perform_startup_tasks(self):
        """Perform application startup tasks and display preamble."""
        try:
            logger.info("Performing startup tasks...")
            
            # Perform startup tasks
            startup_result = startup_service.perform_startup_tasks()
            
            # Display the appropriate preamble
            preamble = startup_result.get('preamble', '')
            if preamble:
                # Split preamble into lines and display each one
                for line in preamble.split('\n'):
                    if line.strip():  # Only display non-empty lines
                        self.append_output(line, "system")
            else:
                # Empty preamble for first run - display nothing
                logger.info("First run detected - showing empty preamble")
            
            # Add separator if preamble was shown
            if preamble:
                self.append_output("-" * 50, "system")
            
            logger.info(f"Startup tasks completed - first_run: {startup_result.get('first_run')}, api_status: {startup_result.get('api_status')}")
            
        except Exception as e:
            logger.error(f"✗ Failed to perform startup tasks: {e}")
            # Fallback to basic welcome message
            self.append_output("💬 Ghostman AI Assistant", "system")
            self.append_output("Type your message or 'help' for commands", "system")
            self.append_output("-" * 50, "system")
    
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
    
    def _init_title_bar(self, parent_layout):
        """Initialize title bar with new conversation and help buttons."""
        # Create a frame for the title bar to make it more visible and draggable
        self.title_frame = QFrame()
        # Apply theme-aware styling
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            self.title_frame.setStyleSheet(StyleTemplates.get_title_frame_style(self.theme_manager.current_theme))
        else:
            self.title_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(40, 40, 40, 0.8);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 5px;
                    margin: 0px;
                }
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
        
        # Start new conversation action
        new_action = QAction("Start New Conversation", self.title_new_conv_btn)
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Start new conversation and save current action
        save_and_new_action = QAction("Save Current & Start New", self.title_new_conv_btn)
        save_and_new_action.triggered.connect(lambda: self._start_new_conversation(save_current=True))
        new_conv_menu.addAction(save_and_new_action)
        
        # Store menu reference but don't set it on the button (avoids arrow)
        self.title_new_conv_menu = new_conv_menu
        
        # Apply styling without menu attached
        self._style_title_button(self.title_new_conv_btn, add_right_padding=True)
        
        title_layout.addWidget(self.title_new_conv_btn)
        
        # Help documentation button (with help-docs icon)
        self.title_help_btn = QToolButton()
        # Load help icon (theme-specific)
        self._load_help_icon(self.title_help_btn)
        # Icon size is now handled by ButtonStyleManager
        self.title_help_btn.setToolTip("Open help documentation")
        self.title_help_btn.clicked.connect(self._on_help_clicked)
        self._style_title_button(self.title_help_btn)
        title_layout.addWidget(self.title_help_btn)
        
        # Help command button (with ? mark)
        self.help_command_btn = QToolButton()
        self.help_command_btn.setText("?")
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
        # Search bar frame (initially hidden)
        self.search_frame = QFrame()
        self.search_frame.setVisible(False)
        self.search_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 0.9);
                border: 1px solid rgba(255, 165, 0, 0.5);
                border-radius: 4px;
                margin: 2px;
            }
        """)
        
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(6)
        
        # Search icon/label
        search_icon = QLabel("🔍")
        search_layout.addWidget(search_icon)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in conversation...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._search_next)
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
        
        # Search results label
        self.search_status_label = QLabel("0/0")
        self.search_status_label.setMinimumWidth(40)
        status_color = self.theme_manager.current_theme.text_tertiary if (self.theme_manager and THEME_SYSTEM_AVAILABLE) else "#888"
        self.search_status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
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
        
        # Start new conversation action
        new_action = QAction("Start New Conversation", self.toolbar_new_conv_btn)
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Start new conversation and save current action
        save_and_new_action = QAction("Save Current & Start New", self.toolbar_new_conv_btn)
        save_and_new_action.triggered.connect(lambda: self._start_new_conversation(save_current=True))
        new_conv_menu.addAction(save_and_new_action)
        
        # Store menu reference but don't set it on the button (avoids arrow)
        self.toolbar_new_conv_menu = new_conv_menu
        
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
        """Apply custom styling to conversation selector."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            # Use theme colors for conversation selector
            bg_color = colors.background_secondary
            text_color = colors.text_primary
            border_color = colors.border_secondary
            focus_color = colors.border_focus
            
            style = f"QComboBox {{background-color: {bg_color}; color: {text_color}; border: 1px solid {border_color}; border-radius: 5px; padding: 5px 10px; font-size: 11px;}} QComboBox:hover {{border: 1px solid {focus_color};}} QComboBox::drop-down {{border: none; width: 20px;}} QComboBox::down-arrow {{image: none; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 5px solid {text_color}; margin-top: 2px;}} QComboBox QAbstractItemView {{background-color: {colors.background_primary}; color: {text_color}; selection-background-color: {colors.primary}; border: 1px solid {border_color}; outline: none;}}"
        else:
            # Fallback styles
            style = "QComboBox {background-color: rgba(40, 40, 40, 0.8); color: white; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 5px; padding: 5px 10px; font-size: 11px;} QComboBox:hover {border: 1px solid #4CAF50;} QComboBox::drop-down {border: none; width: 20px;} QComboBox::down-arrow {image: none; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 5px solid white; margin-top: 2px;} QComboBox QAbstractItemView {background-color: rgba(30, 30, 30, 0.95); color: white; selection-background-color: #4CAF50; border: 1px solid rgba(255, 255, 255, 0.3); outline: none;}"
        
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
            # Use a darker/more contrasted approach for all themes
            special_colors = {
                "text": colors.text_primary,  # Use primary text color
                "background": colors.background_tertiary,  # Use tertiary background for better contrast
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
            # Use the dedicated plus button styling method
            ButtonStyleManager.apply_plus_button_style(button, colors, emoji_font_stack)
        else:
            # Apply theme-aware styling for better visibility
            # Only apply special colors to QToolButtons (icon buttons), NOT QPushButtons (minimize)
            special_colors = {}
            if isinstance(button, QToolButton) and colors:
                # Use a darker/more contrasted approach for all themes
                special_colors = {
                    "text": colors.text_primary,  # Use primary text color
                    "background": colors.background_tertiary,  # Use tertiary background for better contrast
                    "hover": colors.interactive_hover,  # Use theme's hover color
                    "active": colors.interactive_active  # Use theme's active color
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
                    padding: 6px 12px;
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
                    # Use a darker/more contrasted approach for all themes
                    special_colors = {
                        "text": colors.text_primary,  # Use primary text color
                        "background": colors.background_tertiary,  # Use tertiary background for better contrast
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
                    # Use a darker/more contrasted approach for all themes
                    special_colors = {
                        "text": colors.text_primary,  # Use primary text color
                        "background": colors.background_tertiary,  # Use tertiary background for better contrast
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
            self.search_btn.setText("⌕")  # Fallback
    
    def _load_chain_icon(self):
        """Load theme-appropriate chain icon."""
        try:
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
            self.attach_btn.setText("⚲")  # Fallback
    
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
        
        # Initialize resize functionality
        self._init_resize_functionality()
        
        # Title bar with new conversation and help buttons
        self._init_title_bar(layout)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        # Note: QTextEdit doesn't have setOpenExternalLinks - anchorClicked signal works by default
        # Use font service for AI response font (default for output display)
        ai_font = font_service.create_qfont('ai_response')
        self.output_display.setFont(ai_font)
        self.output_display.setMinimumHeight(300)
        layout.addWidget(self.output_display, 1)
        
        # In-conversation search bar (initially hidden)
        self._init_search_bar(layout)
        
        # Input area with background styling for prompt
        input_layout = QHBoxLayout()
        
        # Prompt label with background styling for better visual separation
        self.prompt_label = QLabel(">>>")
        self._style_prompt_label(normal=True)
        input_layout.addWidget(self.prompt_label)
        
        # Command input
        self.command_input = QLineEdit()
        # Use font service for user input font
        input_font = font_service.create_qfont('user_input')
        self.command_input.setFont(input_font)
        self.command_input.returnPressed.connect(self._on_command_entered)
        self.command_input.installEventFilter(self)
        input_layout.addWidget(self.command_input)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._on_command_entered)
        self._style_send_button()
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Initial startup and preamble - will be set after startup tasks complete
        # This will be replaced by _display_startup_preamble() called from _load_conversations_deferred
        
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
        """Apply styles using the theme system."""
        try:
            colors = self.theme_manager.current_theme
            alpha = max(0.0, min(1.0, self._panel_opacity))
            
            # Generate themed style with opacity (includes border-radius)
            style = StyleTemplates.get_repl_panel_style(colors, alpha)
            
            # Add input field styles
            input_style = StyleTemplates.get_input_field_style(colors)
            
            # Handle child element backgrounds based on opacity
            if alpha >= 1.0:
                # Fully opaque - use original hex color
                child_bg = colors.background_tertiary
            elif colors.background_tertiary.startswith('#'):
                # Transparent - convert to rgba with correct opacity (alpha is 0.0-1.0)
                r = int(colors.background_tertiary[1:3], 16)
                g = int(colors.background_tertiary[3:5], 16)
                b = int(colors.background_tertiary[5:7], 16)
                child_bg = f"rgba({r}, {g}, {b}, {alpha:.3f})"
            else:
                child_bg = colors.background_tertiary
            
            # Combine styles using string formatting to avoid CSS syntax issues
            textedit_style = f"#repl-root QTextEdit {{ background-color: {child_bg}; color: {colors.text_primary}; border: 1px solid {colors.border_secondary}; border-radius: 5px; padding: 5px; selection-background-color: {colors.secondary}; selection-color: {colors.text_primary}; }}"
            lineedit_style = f"#repl-root QLineEdit {{ background-color: {child_bg}; color: {colors.text_primary}; border: 1px solid {colors.border_primary}; border-radius: 3px; padding: 5px; selection-background-color: {colors.secondary}; selection-color: {colors.text_primary}; }}"
            lineedit_focus_style = f"#repl-root QLineEdit:focus {{ border: 2px solid {colors.border_focus}; }}"
            
            # Properly combine all styles (root style includes border-radius)
            combined_style = f"{style} {textedit_style} {lineedit_style} {lineedit_focus_style}"
            
            
            self.setStyleSheet(combined_style)
            logger.debug("🎨 Applied themed REPL styles")
            
        except Exception as e:
            logger.error(f"Failed to apply themed styles: {e}")
            # Fallback to legacy styles
            self._apply_legacy_styles()
    
    def _apply_legacy_styles(self):
        """Apply legacy hardcoded styles as fallback."""
        # Clamp opacity
        alpha = max(0.0, min(1.0, self._panel_opacity))
        
        # For true transparency, make root transparent when opacity < 1
        if alpha >= 0.99:
            panel_bg = "rgba(30, 30, 30, 1.0)"
            border_style = "border-radius: 10px 10px 0px 0px;"
        else:
            panel_bg = "transparent"
            border_style = "border: none;"
            
        # Use rgba for child elements to control actual opacity
        textedit_bg = f"rgba(20, 20, 20, {alpha:.3f})"
        lineedit_bg = f"rgba(40, 40, 40, {alpha:.3f})"
        
        logger.debug(f"🎨 CSS colors generated:")
        logger.debug(f"  📦 Panel background: {panel_bg}")
        logger.debug(f"  📝 Text area background: {textedit_bg}")
        logger.debug(f"  ⌨️  Input background: {lineedit_bg}")
        # Use simple string formatting to avoid CSS syntax issues
        root_style = f"#repl-root {{ background-color: {panel_bg}; {border_style} }}"
        textedit_fallback = f"#repl-root QTextEdit {{ background-color: {textedit_bg}; color: #f0f0f0; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 5px; padding: 5px; }}"
        lineedit_fallback = f"#repl-root QLineEdit {{ background-color: {lineedit_bg}; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 3px; padding: 5px; }}"
        lineedit_focus_fallback = "#repl-root QLineEdit:focus { border: 1px solid #4CAF50; }"
        
        self.setStyleSheet(f"{root_style} {textedit_fallback} {lineedit_fallback} {lineedit_focus_fallback}")

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
        self._apply_styles()
        
        # Also update the output display style with new opacity
        if hasattr(self, 'output_display'):
            self._style_output_display()
            
        logger.info(f"✓ REPL panel opacity applied successfully: {new_val:.3f}")
    
    def refresh_fonts(self):
        """Refresh fonts from font service when settings change."""
        try:
            # Clear font service cache to get latest settings
            font_service.clear_cache()
            
            # Update output display font (AI response font)
            ai_font = font_service.create_qfont('ai_response')
            self.output_display.setFont(ai_font)
            
            # Update input font (user input font)
            input_font = font_service.create_qfont('user_input')
            self.command_input.setFont(input_font)
            
            # Clear markdown renderer cache so it uses new fonts and update theme
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.clear_cache()
                self._markdown_renderer.update_theme()
            
            # Re-render existing content with new fonts
            self._refresh_existing_output()
            
            logger.info("✓ Fonts refreshed from settings")
            
        except Exception as e:
            logger.error(f"Failed to refresh fonts: {e}")
    
    def _refresh_existing_output(self):
        """Re-render all existing output with current theme colors - preserves content."""
        try:
            # Clear markdown renderer cache to ensure fresh colors
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.clear_cache()
                self._markdown_renderer.update_theme()
            
            # Get current cursor position to restore later
            cursor = self.output_display.textCursor()
            current_position = cursor.position()
            
            # Store current scroll position
            scrollbar = self.output_display.verticalScrollBar()
            scroll_position = scrollbar.value()
            
            # Update the document font with new theme settings
            document = self.output_display.document()
            ai_font = font_service.create_qfont('ai_response')
            document.setDefaultFont(ai_font)
            
            # Update text color formats for existing content with improved theme awareness
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                colors = self.theme_manager.current_theme
                
                # Update the default text format for the entire document
                default_format = QTextCharFormat()
                default_format.setForeground(QColor(colors.text_primary))
                
                # Apply new colors to the entire document
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.setCharFormat(default_format)
                
                # Create comprehensive color updates for inline styled text
                self._update_inline_text_colors(colors)
                
                # Force a complete refresh of the widget with opacity support
                alpha = max(0.0, min(1.0, self._panel_opacity))
                if alpha >= 1.0:
                    bg_color = colors.background_primary
                elif colors.background_primary.startswith('#'):
                    r = int(colors.background_primary[1:3], 16)
                    g = int(colors.background_primary[3:5], 16)
                    b = int(colors.background_primary[5:7], 16)
                    bg_color = f"rgba({r}, {g}, {b}, {alpha:.3f})"
                else:
                    bg_color = colors.background_primary
                    
                self.output_display.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {bg_color};
                        color: {colors.text_primary};
                        border: none;
                        selection-background-color: {colors.primary};
                        selection-color: {colors.background_primary};
                    }}
                """)
                
            # Restore cursor position and scroll
            cursor.setPosition(min(current_position, document.characterCount() - 1))
            self.output_display.setTextCursor(cursor)
            
            # Restore scroll position
            scrollbar.setValue(scroll_position)
            
            logger.debug("Existing output refreshed with new theme colors")
            
        except Exception as e:
            logger.error(f"Failed to refresh existing output: {e}")
    
    def _update_inline_text_colors(self, colors):
        """Update colors for inline styled text elements."""
        try:
            # Get the document
            document = self.output_display.document()
            cursor = QTextCursor(document)
            
            # Color mappings based on common text patterns
            color_mappings = {
                'input': colors.primary,
                'response': colors.text_primary,
                'system': colors.text_tertiary,
                'info': colors.status_info,
                'warning': colors.status_warning,
                'error': colors.status_error,
                'divider': colors.separator
            }
            
            # Iterate through the document and update color-specific formats
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            while not cursor.atEnd():
                char_format = cursor.charFormat()
                current_color = char_format.foreground().color()
                
                # Check if this text needs color updating based on context
                # This is a simplified approach - could be enhanced with more sophisticated detection
                
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
            
            logger.debug("Updated inline text colors for theme")
            
        except Exception as e:
            logger.warning(f"Failed to update inline text colors: {e}")
    
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
            else:
                # Stop spinner animation and restore normal prompt
                if hasattr(self, '_spinner_timer'):
                    self._spinner_timer.stop()
                
                self.prompt_label.setText(">>>")
                self._style_prompt_label(normal=True, processing=False)
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
        """Event filter for command input navigation."""
        if obj == self.command_input and event.type() == event.Type.KeyPress:
            key_event = event
            
            # Up arrow - previous command
            if key_event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            
            # Down arrow - next command
            elif key_event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        
        return super().eventFilter(obj, event)
    
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts."""
        # Ctrl+F to open search
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._toggle_search()
            return
        
        # Escape to close search if open
        elif event.key() == Qt.Key.Key_Escape and self.search_frame.isVisible():
            self._close_search()
            return
        
        super().keyPressEvent(event)
    
    def _navigate_history(self, direction: int):
        """Navigate through command history."""
        if not self.command_history:
            return
        
        # Save current input if starting to navigate
        if self.history_index == -1:
            self.current_input = self.command_input.text()
        
        # Update index
        self.history_index += direction
        
        # Clamp index
        if self.history_index < -1:
            self.history_index = -1
        elif self.history_index >= len(self.command_history):
            self.history_index = len(self.command_history) - 1
        
        # Update input
        if self.history_index == -1:
            self.command_input.setText(self.current_input)
        else:
            self.command_input.setText(self.command_history[self.history_index])
    
    # Enhanced event handlers for conversation management
    @pyqtSlot(str)
    def _on_conversation_selected(self, display_name: str):
        """Handle conversation selection from dropdown."""
        current_index = self.conversation_selector.currentIndex()
        if current_index < 0:
            return
        
        conversation_id = self.conversation_selector.itemData(current_index)
        
        if not conversation_id:  # New conversation selected
            self._create_new_conversation()
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
                    
                    # Update selector
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
        """Load conversation messages into output display."""
        self.clear_output()
        
        self.append_output(f"💬 Conversation: {conversation.title}", "system")
        
        if conversation.summary:
            self.append_output(f"💡 Summary: {conversation.summary.summary}", "info")
            if conversation.summary.key_topics:
                topics = ", ".join(conversation.summary.key_topics)
                self.append_output(f"📝 Topics: {topics}", "info")
        
        self.append_output("-" * 50, "system")
        
        # Load messages with appropriate icons
        for message in conversation.messages:
            if message.role == MessageRole.SYSTEM:
                continue  # Skip system messages in display
            
            role_icon = "👤" if message.role == MessageRole.USER else "🤖"
            role_name = "You" if message.role == MessageRole.USER else "AI"
            style = "input" if message.role == MessageRole.USER else "response"
            
            timestamp = message.timestamp.strftime("%H:%M")
            self.append_output(f"[{timestamp}] {role_icon} {role_name}: {message.content}", style)
        
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
                if self.current_conversation.message_count == 0:
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
                if self.current_conversation.message_count < MIN_MESSAGES_FOR_SUMMARY:
                    logger.debug(f"⏭️ Skipping summarization for {conversation_id}: Only {self.current_conversation.message_count} messages (min: {MIN_MESSAGES_FOR_SUMMARY})")
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
        command = self.command_input.text().strip()
        
        if not command:
            return
        
        # Add to history
        if not self.command_history or command != self.command_history[-1]:
            self.command_history.append(command)
        
        # Reset history navigation
        self.history_index = -1
        self.current_input = ""
        
        # Add light grey divider before user input reflection
        self.append_output("--------------------------------------------------", "divider")
        
        # Display command in output with better separation
        self.append_output(f"👤 **You:**\n{command}", "input")
        self.append_output("", "normal")  # Add spacing
        
        # Clear input
        self.command_input.clear()
        
        # Process command
        self._process_command(command)
        
        # Emit signal for external processing
        self.command_entered.emit(command)
    
    def _process_command(self, command: str):
        """Process built-in commands."""
        command_lower = command.lower()
        
        if command_lower == "help":
            self.append_output("Available commands:", "info")
            self.append_output("  help     - Show this help message", "info")
            self.append_output("  clear    - Clear the output display", "info")
            self.append_output("  history  - Show command history", "info")
            self.append_output("  resend   - Resend the last failed message", "info")
            self.append_output("  exit     - Minimize to system tray", "info")
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
            # Would need to connect to app quit
            self.append_output("Use system tray menu to quit application", "warning")
        
        elif command_lower == "context":
            # Debug command to show AI context status
            self._show_context_status()
        
        elif command_lower == "render_stats":
            # Debug command to show render statistics
            self._show_render_stats()
        
        elif command_lower == "test_markdown":
            # Debug command to test markdown rendering
            self._test_markdown_rendering()
        
        elif command_lower == "test_themes":
            # Debug command to test all theme switching
            self._test_all_themes()
        
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
        
        Args:
            text: Text to append (supports markdown formatting)
            style: Style type for color coding (normal, input, response, system, info, warning, error)
            force_plain: If True, bypasses markdown processing for plain text rendering
        """
        if not hasattr(self, '_markdown_renderer'):
            self._markdown_renderer = MarkdownRenderer(self.theme_manager)
        
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Render content with markdown support
        try:
            html_content = self._markdown_renderer.render(text, style, force_plain)
            
            # Insert the rendered HTML content
            cursor.insertHtml(html_content)
            
            # Performance optimization: limit document size for very long conversations
            self._manage_document_size()
            
        except Exception as e:
            logger.error(f"Error rendering output: {e}")
            # Fallback to simple text rendering
            color = self._markdown_renderer.color_scheme.get(style, self._markdown_renderer.color_scheme.get("normal", "#f0f0f0"))
            escaped_text = html.escape(str(text))
            cursor.insertHtml(f'<span style="color: {color};">{escaped_text}</span><br>')
        
        # Auto-scroll to bottom
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
    
    def _manage_document_size(self):
        """
        Manage document size for performance in long conversations.
        Removes older content when document becomes too large.
        """
        document = self.output_display.document()
        block_count = document.blockCount()
        
        # If document has more than 1000 blocks, remove the oldest 200
        if block_count > 1000:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            # Select first 200 blocks
            for _ in range(200):
                cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
            
            # Remove selected content and add notice
            cursor.removeSelectedText()
            truncate_color = self._markdown_renderer.color_scheme.get("system", "#808080") if hasattr(self, '_markdown_renderer') else "#808080"
            cursor.insertHtml(f'<span style="color: {truncate_color}; font-style: italic;">[Previous messages truncated for performance]</span><br><br>')
            
            logger.debug(f"Document size managed: removed 200 blocks, {document.blockCount()} remaining")
    
    def clear_output(self):
        """Clear the output display and reset markdown renderer cache."""
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
            'document_blocks': self.output_display.document().blockCount(),
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
    
    def _send_to_ai(self, message: str):
        """Send message to AI service with conversation management."""
        # Store message for potential resend
        self.last_failed_message = message
        
        # Ensure we have an active conversation
        if not self.current_conversation and self.conversation_manager:
            logger.info("🆕 Auto-creating conversation for AI interaction")
            self._create_new_conversation_for_message(message)
            
        # Ensure AI service has the correct conversation context
        if self.current_conversation and self.conversation_manager and self.conversation_manager.has_ai_service():
            ai_service = self.conversation_manager.get_ai_service()
            if ai_service:
                # Make sure the current conversation is set in the AI service
                current_ai_conversation = ai_service.get_current_conversation_id()
                if current_ai_conversation != self.current_conversation.id:
                    logger.info(f"🔄 Syncing AI service conversation context: {current_ai_conversation} -> {self.current_conversation.id}")
                    ai_service.set_current_conversation(self.current_conversation.id)
        
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
            
            def __init__(self, message, conversation_manager, current_conversation):
                super().__init__()
                self.message = message
                self.conversation_manager = conversation_manager
                self.current_conversation = current_conversation
            
            def run(self):
                try:
                    # ALWAYS prefer conversation-aware AI service for context persistence
                    ai_service = None
                    if self.conversation_manager:
                        # Call get_ai_service() which will initialize it if needed
                        ai_service = self.conversation_manager.get_ai_service()
                        if ai_service:
                            logger.info("🎯 Using conversation-aware AI service for context persistence")
                        
                        if ai_service:
                            # Ensure current conversation context is set
                            if self.current_conversation:
                                logger.debug(f"Setting AI service conversation context to: {self.current_conversation.id}")
                                ai_service.set_current_conversation(self.current_conversation.id)
                            
                            # Send message with full conversation context
                            result = ai_service.send_message(self.message, save_conversation=True)
                            
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
                    logger.debug("Sent Message: %s", self.message)
                    result = ai_service.send_message(self.message)
                    
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
        self.ai_worker = EnhancedAIWorker(message, self.conversation_manager, self.current_conversation)
        self.ai_worker.moveToThread(self.ai_thread)
        
        # Connect signals
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.response_received.connect(self._on_ai_response)
        self.ai_worker.response_received.connect(self.ai_thread.quit)
        self.ai_worker.response_received.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        
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
        
        # Display response with appropriate icon
        if success:
            # Clear failed message on successful response
            self.last_failed_message = None
            
            # Debug: Check response content
            if not response or not response.strip():
                logger.warning(f"Empty AI response received: '{response}'")
                response = "[No response content received]"
            
            # Display AI response with better separation
            self.append_output("🤖 **Spector:**", "response")
            # Display the actual response without prefixing to preserve markdown
            self.append_output(response, "response")
            # Add spacing after AI response
            self.append_output("", "normal")
            self.append_output("\n--------------------------------------------------\n", "divider")
            
            # If we have a conversation manager, refresh the conversation data
            # to update message counts and other metadata
            if self.conversation_manager and self.current_conversation:
                # Refresh conversation data to get updated message count
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Reload the current conversation to get updated message count
                        updated_conv = loop.run_until_complete(
                            self.conversation_manager.get_conversation(
                                self.current_conversation.id, 
                                include_messages=False
                            )
                        )
                        if updated_conv:
                            self.current_conversation = updated_conv
                            self._update_status_label(updated_conv)
                            logger.debug(f"Refreshed conversation data - message count: {updated_conv.get_message_count()}")
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Failed to refresh conversation data: {e}")
            elif not self.conversation_manager and self.current_conversation:
                # Manual fallback - add to conversation if needed
                logger.info("Manual message saving not yet implemented")
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
            resend_html = '''
            <div style="margin: 10px 0; padding: 8px; border: 1px solid #666; border-radius: 4px; background-color: rgba(255,255,255,0.05);">
                <a href="resend_message" style="color: #4CAF50; text-decoration: none; font-weight: bold;">
                    🔄 Click here to resend your message
                </a>
                <br><span style="color: #888; font-size: 10px;">
                    Message: "{}"
                </span>
            </div>
            '''.format(html.escape(self.last_failed_message[:100] + "..." if len(self.last_failed_message) > 100 else self.last_failed_message))
            
            # Insert the resend option
            cursor = self.output_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(resend_html)
            
            # Connect to click handler if not already connected
            if not hasattr(self, '_resend_connected'):
                self.output_display.anchorClicked.connect(self._handle_resend_click)
                self._resend_connected = True
                
        except Exception as e:
            logger.error(f"Failed to add resend option: {e}")
            # Fallback to simple text
            self.append_output("Type 'resend' to try sending your message again", "system")
    
    def _handle_resend_click(self, url):
        """Handle clicks on resend links."""
        if url.toString() == "resend_message" and self.last_failed_message:
            logger.info(f"Resending failed message: {self.last_failed_message[:50]}...")
            self.append_output(f"🔄 **Resending message...**", "system")
            self.append_output("", "system")  # Add spacing
            self._send_to_ai(self.last_failed_message)
    
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
            if hasattr(self.current_conversation, 'message_count') and self.current_conversation.message_count > 0:
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
            
            # Create async task to load the conversation
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._restore_conversation_async(conversation_id))
            else:
                loop.run_until_complete(self._restore_conversation_async(conversation_id))
                
        except Exception as e:
            logger.error(f"✗ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
    
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
        """Check if current conversation has unsaved messages."""
        if not self.current_conversation:
            return False
        
        # Check if there's content in the REPL that hasn't been saved
        output_text = self.output_display.toPlainText().strip()
        if not output_text:
            return False
        
        # Basic check - if there's user input or AI responses beyond just system messages
        lines = output_text.split('\n')
        user_messages = [line for line in lines if line.strip().startswith('>>>')]
        return len(user_messages) > 0
    
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
            
            # Perform autosave asynchronously
            asyncio.create_task(self._perform_autosave())
            
        except Exception as e:
            logger.error(f"Failed to autosave conversation: {e}")
    
    async def _perform_autosave(self):
        """Perform the actual autosave operation."""
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
                    
                    # Schedule proper database creation and activation in background
                    asyncio.create_task(self._save_temp_conversation_to_db(temp_conversation, message))
                    
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
    
    async def _create_conversation_async(self, title: str, initial_message: str):
        """Create conversation asynchronously."""
        try:
            conversation = await self.conversation_manager.create_conversation(
                title=title,
                initial_message=initial_message
            )
            
            if conversation:
                # Update current conversation if this was called synchronously
                self.current_conversation = conversation
                # Add to conversations list
                if conversation not in self.conversations_list:
                    self.conversations_list.insert(0, conversation)
                logger.info(f"✓ Created conversation: {conversation.title}")
                return conversation
            
        except Exception as e:
            logger.error(f"✗ Failed to create conversation async: {e}")
        
        return None
    
    async def _save_temp_conversation_to_db(self, temp_conversation, initial_message: str):
        """Save temporary conversation to database in background."""
        try:
            logger.debug(f"💾 Saving temporary conversation to database: {temp_conversation.id}")
            
            # Create proper conversation in database
            db_conversation = await self.conversation_manager.create_conversation(
                title=temp_conversation.title,
                initial_message=initial_message
            )
            
            if db_conversation:
                logger.info(f"✓ Saved temporary conversation to database: {db_conversation.id}")
                
                # Update the current conversation reference to use the database version
                self.current_conversation = db_conversation
                
                # Update conversations list
                if db_conversation not in self.conversations_list:
                    self.conversations_list.insert(0, db_conversation)
                    
                # Sync with AI service if available
                if self.conversation_manager.has_ai_service():
                    ai_service = self.conversation_manager.get_ai_service()
                    if ai_service:
                        ai_service.set_current_conversation(db_conversation.id)
                        logger.debug(f"🔄 Synced AI service to database conversation: {db_conversation.id}")
            else:
                logger.error(f"✗ Failed to save temporary conversation to database")
                
        except Exception as e:
            logger.error(f"✗ Failed to save temporary conversation to database: {e}", exc_info=True)
    
    def refresh_conversations(self):
        """Refresh the conversations list from the database."""
        if not self.conversation_manager:
            return
        
        try:
            logger.debug("Refreshing conversations list...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._load_conversations())
            else:
                loop.run_until_complete(self._load_conversations())
            logger.debug("Conversation refresh initiated successfully")
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
                    # Add to conversations list and update UI
                    self.conversations_list.insert(0, conversation)
                    
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
        import sys
        from pathlib import Path
        
        try:
            # Try to find local help documentation
            possible_paths = [
                # Development mode
                Path(__file__).parent.parent.parent.parent / "assets" / "help" / "index.html",
                # Installed package mode
                Path(sys.prefix) / "share" / "ghostman" / "help" / "index.html",
                # Bundled executable mode
                Path(getattr(sys, '_MEIPASS', Path.cwd())) / "ghostman" / "assets" / "help" / "index.html",
                # Relative to current working directory
                Path.cwd() / "ghostman" / "assets" / "help" / "index.html",
            ]
            
            help_path = None
            for path in possible_paths:
                if path.exists():
                    help_path = path
                    break
            
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
        self.command_input.setText("help")
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
            # Position menu below the button
            button_pos = self.title_new_conv_btn.mapToGlobal(self.title_new_conv_btn.rect().bottomLeft())
            self.title_new_conv_menu.exec(button_pos)
    
    def _show_toolbar_new_conv_menu(self):
        """Show the new conversation menu for toolbar button."""
        if hasattr(self, 'toolbar_new_conv_menu'):
            # Position menu below the button
            button_pos = self.toolbar_new_conv_btn.mapToGlobal(self.toolbar_new_conv_btn.rect().bottomLeft())
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
    
    def _start_new_conversation(self, save_current: bool = False):
        """Start a new conversation with optional saving of current."""
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
                        # Refresh conversation list
                        await self._load_conversations()
                        self.append_output("✓ Started new conversation", "system")
                        if save_current and current_id:
                            self.append_output("💾 Previous conversation saved with auto-generated title", "system")
                        
                        # Add welcome message for new conversation
                        self.append_output("💬 Ghostman Conversation Manager v2.0", "system")
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
            
            logger.debug("Search closed and highlights cleared")
            
            # Update search button visual state
            self._update_search_button_state()
            
        except Exception as e:
            logger.error(f"Failed to close search: {e}")
    
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
        """Find all matches of query in current conversation display."""
        try:
            self.current_search_matches = []
            
            if not hasattr(self, 'output_display') or not self.output_display:
                return
            
            # Get the conversation display text
            cursor = self.output_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            
            # Get full document text
            document = self.output_display.document()
            full_text = document.toPlainText()
            
            # Search for current conversation with optional regex support
            import re
            
            try:
                if hasattr(self, 'regex_checkbox') and self.regex_checkbox.isChecked():
                    # Use regex pattern directly
                    pattern = re.compile(query, re.IGNORECASE)
                else:
                    # Escape special characters for literal search
                    pattern = re.compile(re.escape(query), re.IGNORECASE)
            except re.error as e:
                # Invalid regex pattern - show error in status
                if hasattr(self, 'search_status_label'):
                    self.search_status_label.setText(f"Invalid regex: {str(e)[:20]}...")
                logger.warning(f"Invalid regex pattern '{query}': {e}")
                return
            
            # Find all matches
            for match in pattern.finditer(full_text):
                start_pos = match.start()
                end_pos = match.end()
                
                # Convert to QTextCursor positions
                cursor.setPosition(start_pos)
                start_cursor = QTextCursor(cursor)
                cursor.setPosition(end_pos, cursor.MoveMode.KeepAnchor)
                end_cursor = QTextCursor(cursor)
                
                self.current_search_matches.append({
                    'start': start_pos,
                    'end': end_pos,
                    'text': match.group(),
                    'cursor': QTextCursor(cursor)
                })
            
            logger.debug(f"Found {len(self.current_search_matches)} matches for '{query}'")
            
        except Exception as e:
            logger.error(f"Failed to find matches in conversation: {e}")
    
    def _highlight_current_match(self):
        """Highlight the current search match and scroll to it."""
        try:
            if not self.current_search_matches or self.current_search_index < 0:
                return
            
            match = self.current_search_matches[self.current_search_index]
            
            # Clear previous highlights
            self._clear_search_highlights()
            
            # Create highlight format with theme colors
            highlight_format = QTextCharFormat()
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                highlight_bg = self.theme_manager.current_theme.status_warning
                highlight_fg = self.theme_manager.current_theme.background_primary
            else:
                highlight_bg = "#ffff00"  # Yellow background
                highlight_fg = "#000000"  # Black text
            highlight_format.setBackground(QColor(highlight_bg))
            highlight_format.setForeground(QColor(highlight_fg))
            
            # Apply highlight to current match
            cursor = self.output_display.textCursor()
            cursor.setPosition(match['start'])
            cursor.setPosition(match['end'], cursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(highlight_format)
            
            # Scroll to the match
            self.output_display.setTextCursor(cursor)
            self.output_display.ensureCursorVisible()
            
            logger.debug(f"Highlighted match at position {match['start']}-{match['end']}")
            
        except Exception as e:
            logger.error(f"Failed to highlight current match: {e}")
    
    def _clear_search_highlights(self):
        """Clear all search highlights from conversation display."""
        try:
            if not hasattr(self, 'output_display') or not self.output_display:
                return
            
            # Reset all text formatting to default
            cursor = self.output_display.textCursor()
            cursor.select(cursor.SelectionType.Document)
            
            # Apply default format
            default_format = QTextCharFormat()
            cursor.setCharFormat(default_format)
            
            # Move cursor to start
            cursor.movePosition(cursor.MoveOperation.Start)
            self.output_display.setTextCursor(cursor)
            
            logger.debug("Search highlights cleared")
            
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
            
            # Clear summarization queue
            self.summarization_queue.clear()
            self.is_summarizing = False
            
            # Clear conversation references
            self.current_conversation = None
            self.conversations_list.clear()
            
            logger.info("✓ Enhanced REPL Widget shut down successfully")
            
        except Exception as e:
            logger.error(f"✗ Error during REPL widget shutdown: {e}")