"""
REPL Widget for Ghostman.

Provides a Read-Eval-Print-Loop interface for interacting with the AI.
"""

import logging
import asyncio
import html
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Markdown rendering imports
try:
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger = logging.getLogger("ghostman.repl_widget")
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
    from ...ui.themes.style_templates import StyleTemplates
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    logger = logging.getLogger("ghostman.repl_widget")
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
    
    def __init__(self):
        """Initialize the markdown renderer with optimized configuration."""
        self.markdown_available = MARKDOWN_AVAILABLE
        
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
        
        # Color scheme for different message types
        self.color_scheme = {
            "normal": "#f0f0f0",
            "input": "#00ff00", 
            "response": "#00bfff",
            "system": "#808080",
            "info": "#ffff00",
            "warning": "#ffa500",
            "error": "#ff0000",
            "divider": "#666666"
        }
        
        # Performance cache for repeated renders (small cache to avoid memory issues)
        self._render_cache = {}
        self._cache_max_size = 100
    
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
            return '<span style="color: #808080;">[Empty message]</span><br>'
        
        # Cache key for performance optimization
        cache_key = f"{hash(text)}{style}{force_plain}"
        if cache_key in self._render_cache:
            return self._render_cache[cache_key]
        
        base_color = self.color_scheme.get(style, "#f0f0f0")
        
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
            'a': "#4A9EFF"  # Link color that works across all themes
        }
        
        # Get appropriate font based on message style
        font_type = 'user_input' if style == 'input' else 'ai_response'
        font_css = font_service.get_css_font_style(font_type)
        
        # Wrap entire content with base color and font configuration
        styled_html = f'<div style="color: {base_color}; line-height: 1.4; {font_css};">{html_content}</div>'
        
        # Apply specific styling to elements
        replacements = {
            '<code>': f'<code style="background-color: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 3px; color: {style_colors["code"]}; font-family: Consolas, Monaco, monospace;">',
            '<pre>': f'<pre style="background-color: rgba(255,255,255,0.05); padding: 8px; border-radius: 4px; border-left: 3px solid {base_color}; margin: 4px 0; overflow-x: auto;">',
            '<em>': f'<em style="color: {style_colors["em"]}; font-style: italic;">',
            '<strong>': f'<strong style="color: {style_colors["strong"]}; font-weight: bold;">',
            '<h1>': f'<h1 style="color: {style_colors["h1"]}; font-size: 1.4em; margin: 8px 0 4px 0; border-bottom: 2px solid {base_color};">',
            '<h2>': f'<h2 style="color: {style_colors["h2"]}; font-size: 1.3em; margin: 6px 0 3px 0; border-bottom: 1px solid {base_color};">',
            '<h3>': f'<h3 style="color: {style_colors["h3"]}; font-size: 1.2em; margin: 4px 0 2px 0;">',
            '<blockquote>': f'<blockquote style="color: {style_colors["blockquote"]}; border-left: 3px solid {base_color}; padding-left: 12px; margin: 4px 0; font-style: italic;">',
            '<ul>': '<ul style="margin: 4px 0; padding-left: 20px;">',
            '<ol>': '<ol style="margin: 4px 0; padding-left: 20px;">',
            '<li>': f'<li style="margin: 2px 0;">',
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
        msg_count.setStyleSheet("color: #888; font-size: 9px;")
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
        time_label.setStyleSheet("color: #888; font-size: 9px;")
        meta_row.addWidget(time_label)
        
        meta_row.addStretch()
        layout.addLayout(meta_row)
        
        # Tags if any
        if self.conversation.metadata.tags:
            tags_text = " ".join([f"#{tag}" for tag in list(self.conversation.metadata.tags)[:3]])
            if len(self.conversation.metadata.tags) > 3:
                tags_text += "💬"
            tags_label = QLabel(tags_text)
            tags_label.setStyleSheet("color: #666; font-size: 8px; font-style: italic;")
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
    attach_toggle_requested = pyqtSignal(bool)
    
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
            logger.debug("REPL widget styles updated for new theme")
        except Exception as e:
            logger.error(f"Failed to update REPL widget theme: {e}")
    
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
                self.send_button.setStyleSheet(StyleTemplates.get_button_primary_style(colors))
            
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
            
        except Exception as e:
            logger.error(f"Failed to update component themes: {e}")
    
    def _get_themed_button_style(self, variant="secondary"):
        """Get themed button style string."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            colors = self.theme_manager.current_theme
            if variant == "primary":
                return StyleTemplates.get_button_primary_style(colors)
            else:
                return StyleTemplates.get_tool_button_style(colors)
        else:
            # Fallback to legacy button styles
            return """
                QToolButton {
                    background-color: rgba(255, 255, 255, 0.15);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QToolButton:hover {
                    background-color: rgba(255, 255, 255, 0.25);
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
                logger.info("✅ Conversation manager initialized successfully")
            else:
                logger.error("❌ Failed to initialize conversation manager")
                self.conversation_manager = None
        except Exception as e:
            logger.error(f"❌ Conversation manager initialization failed: {e}")
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
            logger.error(f"❌ Failed to perform startup tasks: {e}")
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
            logger.error(f"❌ Failed deferred conversation loading: {e}", exc_info=True)
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
            # Get recent conversations (all statuses) for the conversation UI
            conversations = await self.conversation_manager.list_conversations(limit=20)
            logger.debug(f"Loaded {len(conversations)} conversations")
            self.conversations_list = conversations
            
            # Set current conversation to the active one (if any), otherwise most recent
            self.current_conversation = None
            if conversations:
                # Find the active conversation
                active_conversations = [c for c in conversations if c.status == ConversationStatus.ACTIVE]
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
            logger.error(f"❌ Failed to load conversations: {e}", exc_info=True)
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
            self.status_label.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 10px;")
            return
        
        status_text = conversation.status.value.title()
        icon = self._get_status_icon(conversation)
        self.status_label.setText(f"{icon} {status_text}")
        
        # Color coding based on status
        colors = {
            "Active": "#4CAF50",
            "Pinned": "#FFD700", 
            "Archived": "#888888",
            "Deleted": "#FF5555"
        }
        color = colors.get(status_text, "#4CAF50")
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
                    margin: 2px;
                }
            """)
        
        # Enable drag functionality for the title frame
        self.title_frame.mousePressEvent = self._title_mouse_press
        self.title_frame.mouseMoveEvent = self._title_mouse_move
        self.title_frame.mouseReleaseEvent = self._title_mouse_release
        self._dragging = False
        self._drag_pos = None
        
        title_layout = QHBoxLayout(self.title_frame)
        title_layout.setContentsMargins(8, 4, 8, 4)
        title_layout.setSpacing(8)
        
        # New conversation button with menu (with extra padding)
        new_conv_btn = QToolButton()
        new_conv_btn.setText("➕")
        new_conv_btn.setToolTip("Start new conversation")
        new_conv_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        new_conv_btn.clicked.connect(self._on_new_conversation_clicked)
        #new_conv_btn.setFixedSize(40, 40)  
        self._style_title_button(new_conv_btn, add_right_padding=True)
        
        # Create menu for new conversation options
        new_conv_menu = QMenu(new_conv_btn)
        
        # Start new conversation action
        new_action = QAction("Start New Conversation", new_conv_btn)
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Start new conversation and save current action
        save_and_new_action = QAction("Save Current & Start New", new_conv_btn)
        save_and_new_action.triggered.connect(lambda: self._start_new_conversation(save_current=True))
        new_conv_menu.addAction(save_and_new_action)
        
        new_conv_btn.setMenu(new_conv_menu)
        title_layout.addWidget(new_conv_btn)
        
        # Help button
        help_btn = QToolButton()
        help_btn.setText("❓")
        help_btn.setToolTip("Show help")
        #help_btn.setFixedSize(40, 40)  # Consistent size with other buttons
        help_btn.clicked.connect(self._on_help_clicked)
        self._style_title_button(help_btn)
        title_layout.addWidget(help_btn)
        
        # Settings button
        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        
        settings_btn.setToolTip("Open settings")
        settings_btn.clicked.connect(self._on_settings_clicked)
        #settings_btn.setFixedSize(40, 40)
        self._style_title_button(settings_btn)
        title_layout.addWidget(settings_btn)
        
        # Chat/Browse button
        chat_btn = QToolButton()
        chat_btn.setText("💬")  # Use text for reliable display
        chat_btn.setToolTip("Browse conversations (💬)")  # Put emoji in tooltip instead
        chat_btn.clicked.connect(self._on_chat_clicked)
        chat_btn.setStyleSheet(self._get_themed_button_style())
        # Special styling for chat button with more width
        #chat_btn.setFixedSize(40, 40)  # Wider than normal buttons
        #self._style_title_button(chat_btn)
        title_layout.addWidget(chat_btn)
        
        # Attach (snap to avatar) toggle button
        self.attach_btn = QToolButton()
        self.attach_btn.setText("🔗")  # Link icon when attached
        self.attach_btn.setToolTip("Attach REPL to avatar (toggle)")
        self.attach_btn.setCheckable(True)
        # Initialize from settings if available
        try:
            from ...infrastructure.storage.settings_manager import settings as _settings
            initial_attached = bool(_settings.get('interface.repl_attached', False))
            self.attach_btn.setChecked(initial_attached)
        except Exception:
            initial_attached = False
        # Style: highlight when checked
        self.attach_btn.setStyleSheet(
            """
            QToolButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                font-size: 14px;
                padding: 2px 6px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.5);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.35);
            }
            QToolButton:checked {
                background-color: rgba(76, 175, 80, 0.5); /* green tint when attached */
                border: 1px solid rgba(76, 175, 80, 0.8);
            }
            """
        )
        self.attach_btn.clicked.connect(self._on_attach_toggle_clicked)
        title_layout.addWidget(self.attach_btn)
        
        # Search button
        search_btn = QToolButton()
        search_btn.setText("🔍")
        search_btn.setToolTip("Search conversations (Ctrl+F)")
        search_btn.clicked.connect(self._toggle_search)
        search_btn.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                font-size: 14px;
                padding: 2px 6px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.5);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.35);
            }
        """)
        title_layout.addWidget(search_btn)

        # Move/Resize arrow toggle button
        self.move_btn = QToolButton()
        self.move_btn.setText("✥")  # Four arrows symbol
        self.move_btn.setToolTip("Toggle resize arrows")
        self.move_btn.setCheckable(True)  # Make it a toggle button
        self.move_btn.clicked.connect(self._on_move_toggle_clicked)
        self._style_title_button(self.move_btn)
        title_layout.addWidget(self.move_btn)
        
        title_layout.addStretch()
        
        # Minimize button (expanded)
        minimize_btn = QPushButton("__")
        minimize_btn.setFixedSize(28, 24)  # Expanded from 20x20
        minimize_btn.clicked.connect(self.minimize_requested.emit)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.3);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
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
        self.regex_checkbox.setFixedSize(35, 25)
        self.regex_checkbox.stateChanged.connect(self._on_regex_toggled)
        search_layout.addWidget(self.regex_checkbox)
        
        # Search navigation buttons
        self.search_prev_btn = QPushButton("↑")
        self.search_prev_btn.setToolTip("Previous match")
        self.search_prev_btn.setFixedSize(30, 25)
        self.search_prev_btn.clicked.connect(self._search_previous)
        search_layout.addWidget(self.search_prev_btn)
        
        self.search_next_btn = QPushButton("↓")
        self.search_next_btn.setToolTip("Next match")
        self.search_next_btn.setFixedSize(30, 25)
        self.search_next_btn.clicked.connect(self._search_next)
        search_layout.addWidget(self.search_next_btn)
        
        # Search results label
        self.search_status_label = QLabel("0/0")
        self.search_status_label.setMinimumWidth(40)
        self.search_status_label.setStyleSheet("color: #888; font-size: 10px;")
        search_layout.addWidget(self.search_status_label)
        
        # Close search button
        close_search_btn = QPushButton("✕")
        close_search_btn.setToolTip("Close search")
        close_search_btn.setFixedSize(25, 25)
        close_search_btn.clicked.connect(self._close_search)
        search_layout.addWidget(close_search_btn)
        
        # Style search buttons
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: #666;
                border-color: rgba(255, 255, 255, 0.1);
            }
        """
        self.search_prev_btn.setStyleSheet(button_style)
        self.search_next_btn.setStyleSheet(button_style)
        close_search_btn.setStyleSheet(button_style)
        
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
            QCheckBox::indicator:checked {
                background-color: #FFA500;
                border-color: #FFA500;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # Search input styling
        self.search_input.setStyleSheet("""
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
        """)
        
        # Initialize search state
        self.current_search_matches = []
        self.current_search_index = -1
        self.current_search_query = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_conversation_search)
        self.search_debounce_ms = 300  # Faster debounce for in-conversation search
        
        parent_layout.addWidget(self.search_frame)
    
    def _on_attach_toggle_clicked(self):
        """Emit attach toggle request with current state and update tooltip/icon."""
        attached = self.attach_btn.isChecked()
        # Update visual feedback
        self.attach_btn.setText("🔗" if attached else "⛓")
        self.attach_btn.setToolTip("Attached to avatar" if attached else "Detached from avatar")
        # Emit to parent window to handle positioning/persistence
        self.attach_toggle_requested.emit(attached)

    def set_attach_state(self, attached: bool):
        """Externally update the attach button state and visuals."""
        if hasattr(self, 'attach_btn'):
            self.attach_btn.setChecked(bool(attached))
            self.attach_btn.setText("🔗" if attached else "⛓")
            self.attach_btn.setToolTip("Attached to avatar" if attached else "Detached from avatar")
    
    def _init_conversation_toolbar(self, parent_layout):
        """Initialize conversation management toolbar."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # New conversation button with menu
        new_conv_btn = QToolButton()
        new_conv_btn.setText("➕")
        # add padding to right
        new_conv_btn.setStyleSheet("padding-right: 4px;")
        new_conv_btn.setToolTip("Start new conversation")
        new_conv_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        new_conv_btn.clicked.connect(self._on_new_conversation_clicked)
        self._style_tool_button(new_conv_btn)
        
        # Create menu for new conversation options
        new_conv_menu = QMenu(new_conv_btn)
        
        # Start new conversation action
        new_action = QAction("Start New Conversation", new_conv_btn)
        new_action.triggered.connect(lambda: self._start_new_conversation(save_current=False))
        new_conv_menu.addAction(new_action)
        
        # Start new conversation and save current action
        save_and_new_action = QAction("Save Current & Start New", new_conv_btn)
        save_and_new_action.triggered.connect(lambda: self._start_new_conversation(save_current=True))
        new_conv_menu.addAction(save_and_new_action)
        
        new_conv_btn.setMenu(new_conv_menu)
        toolbar_layout.addWidget(new_conv_btn)
        
        # Browse conversations button
        browse_btn = QToolButton()
        browse_btn.setText("📋")
        browse_btn.setToolTip("Browse conversations")
        browse_btn.clicked.connect(self.browse_requested.emit)
        self._style_tool_button(browse_btn)
        toolbar_layout.addWidget(browse_btn)
        
        # Export button
        export_btn = QToolButton()
        export_btn.setText("📤")
        export_btn.setToolTip("Export current conversation")
        export_btn.clicked.connect(self._on_export_requested)
        self._style_tool_button(export_btn)
        toolbar_layout.addWidget(export_btn)
        
        # Settings button
        settings_btn = QToolButton()
        settings_btn.setText("⚙️")
        settings_btn.setToolTip("Conversation settings")
        settings_btn.clicked.connect(self.settings_requested.emit)
        self._style_tool_button(settings_btn)
        toolbar_layout.addWidget(settings_btn)
        
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
        self.summary_notification.setStyleSheet("color: #4CAF50; font-size: 9px; font-style: italic;")
        toolbar_layout.addWidget(self.summary_notification)
        
        parent_layout.addLayout(toolbar_layout)
    
    def _style_conversation_selector(self):
        """Apply custom styling to conversation selector."""
        self.conversation_selector.setStyleSheet("""
            QComboBox {
                background-color: rgba(40, 40, 40, 0.8);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid white;
                margin-top: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 30, 30, 0.95);
                color: white;
                selection-background-color: #4CAF50;
                border: 1px solid rgba(255, 255, 255, 0.3);
                outline: none;
            }
        """)
    
    def _style_tool_button(self, button: QToolButton):
        """Apply consistent styling to toolbar buttons."""
        button.setMaximumSize(30, 25)
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                font-size: 12px;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
    
    def _style_title_button(self, button: QToolButton, add_right_padding: bool = False):
        """Apply styling to title bar buttons."""
        button.setFixedSize(32 if add_right_padding else 28, 24)
        padding = "2px 8px 2px 4px" if add_right_padding else "2px 6px"
        button.setStyleSheet(f"""
            QToolButton {{
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                font-size: 14px;
                padding: {padding};
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.5);
            }}
            QToolButton:pressed {{
                background-color: rgba(255, 255, 255, 0.35);
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
            }}
        """)
    
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
        self.prompt_label.setStyleSheet("""
            color: #00ff00; 
            font-family: Segoe UI Emoji, Consolas, monospace; 
            font-size: 11px;
            background-color: rgba(0, 255, 0, 0.1);
            border-radius: 3px;
            padding: 5px 8px;
            margin-right: 5px;
        """)
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
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._on_command_entered)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        input_layout.addWidget(send_btn)
        
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
            
            # Generate themed style with opacity
            style = StyleTemplates.get_repl_panel_style(colors, alpha)
            
            # Add input field styles
            input_style = StyleTemplates.get_input_field_style(colors)
            
            # Combine styles
            combined_style = f"""
            {style}
            #repl-root QTextEdit {{
                background-color: {colors.background_tertiary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_secondary};
                border-radius: 5px;
                padding: 5px;
                selection-background-color: {colors.secondary};
                selection-color: {colors.text_primary};
            }}
            #repl-root QLineEdit {{
                background-color: {colors.background_tertiary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_primary};
                border-radius: 3px;
                padding: 5px;
                selection-background-color: {colors.secondary};
                selection-color: {colors.text_primary};
            }}
            #repl-root QLineEdit:focus {{
                border: 2px solid {colors.border_focus};
            }}
            """
            
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
        panel_bg = f"rgba(30, 30, 30, {alpha:.3f})"
        # Use the same alpha for text areas - no additional reduction
        textedit_bg = f"rgba(20, 20, 20, {alpha:.3f})"
        lineedit_bg = f"rgba(40, 40, 40, {alpha:.3f})"
        
        logger.debug(f"🎨 CSS colors generated:")
        logger.debug(f"  📦 Panel background: {panel_bg}")
        logger.debug(f"  📝 Text area background: {textedit_bg}")
        logger.debug(f"  ⌨️  Input background: {lineedit_bg}")
        self.setStyleSheet(f"""
            #repl-root {{
                background-color: {panel_bg};
                border-radius: 6px;
            }}
            #repl-root QTextEdit {{
                background-color: {textedit_bg};
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                padding: 5px;
            }}
            #repl-root QLineEdit {{
                background-color: {lineedit_bg};
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 5px;
            }}
            #repl-root QLineEdit:focus {{
                border: 1px solid #4CAF50;
            }}
        """)

    def set_panel_opacity(self, opacity: float):
        """Set the frame (panel) background opacity only.

        Args:
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque) for panel background.
        """
        logger.info(f"🎨 REPL panel opacity change requested: {opacity:.3f}")
        
        if not isinstance(opacity, (float, int)):
            logger.error(f"❌ Invalid opacity type: {type(opacity)} (expected float/int)")
            return
            
        old_val = self._panel_opacity
        new_val = max(0.0, min(1.0, float(opacity)))
        
        if abs(new_val - self._panel_opacity) < 0.001:
            logger.debug(f"🎨 Opacity unchanged: {old_val:.3f} -> {new_val:.3f} (difference < 0.001)")
            return
            
        logger.info(f"🎨 Applying panel opacity: {old_val:.3f} -> {new_val:.3f}")
        self._panel_opacity = new_val
        self._apply_styles()
        logger.info(f"✅ REPL panel opacity applied successfully: {new_val:.3f}")
    
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
            
            # Clear markdown renderer cache so it uses new fonts
            if hasattr(self, '_markdown_renderer'):
                self._markdown_renderer.clear_cache()
            
            # Re-render existing content with new fonts
            self._refresh_existing_output()
            
            logger.info("✅ Fonts refreshed from settings")
            
        except Exception as e:
            logger.error(f"Failed to refresh fonts: {e}")
    
    def _refresh_existing_output(self):
        """Re-render all existing output with current font settings."""
        try:
            # Get current cursor position to restore later
            cursor = self.output_display.textCursor()
            current_position = cursor.position()
            
            # Get the document and clear all content
            document = self.output_display.document()
            
            # Store the current conversation for re-rendering
            if hasattr(self, 'conversation') and self.conversation:
                # Clear the output display
                self.output_display.clear()
                
                # Re-render all messages with new font settings
                for message in self.conversation.messages:
                    role_icon = "👤" if message.role.value == "user" else "🤖"
                    role_name = "You" if message.role.value == "user" else "AI"
                    style = "input" if message.role.value == "user" else "response"
                    
                    timestamp = message.timestamp.strftime("%H:%M")
                    self.append_output(f"[{timestamp}] {role_icon} {role_name}: {message.content}", style)
                
                # Scroll to bottom
                scrollbar = self.output_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
                logger.debug("Existing REPL content re-rendered with new fonts")
            else:
                # Just update the document font if no conversation to re-render
                ai_font = font_service.create_qfont('ai_response')
                document.setDefaultFont(ai_font)
                logger.debug("Output display default font updated")
                
        except Exception as e:
            logger.error(f"Failed to refresh existing output: {e}")
    
    def _set_processing_mode(self, processing: bool):
        """Set the UI to processing mode with spinner or normal mode."""
        try:
            if processing:
                # Show spinner in prompt label
                self.prompt_label.setText("⠋")  # Spinner character
                self.prompt_label.setStyleSheet("""
                    color: #ff8c00; 
                    font-family: Segoe UI Emoji, Consolas, monospace; 
                    font-size: 11px;
                    background-color: rgba(255, 140, 0, 0.1);
                    border-radius: 3px;
                    padding: 5px 8px;
                    margin-right: 5px;
                """)
                
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
                self.prompt_label.setStyleSheet("""
                    color: #00ff00; 
                    font-family: Segoe UI Emoji, Consolas, monospace; 
                    font-size: 11px;
                    background-color: rgba(0, 255, 0, 0.1);
                    border-radius: 3px;
                    padding: 5px 8px;
                    margin-right: 5px;
                """)
        except Exception as e:
            logger.error(f"Failed to set processing mode: {e}")
    
    def _update_spinner(self):
        """Update the spinner animation."""
        try:
            if hasattr(self, '_spinner_chars') and hasattr(self, '_spinner_index'):
                self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
                self.prompt_label.setText(self._spinner_chars[self._spinner_index])
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
            # Mark previous conversation as inactive
            asyncio.create_task(self._update_conversation_status(self.current_conversation.id, ConversationStatus.PINNED))
        
        # Mark new conversation as active
        asyncio.create_task(self._update_conversation_status(conversation.id, ConversationStatus.ACTIVE))
        
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
                
                logger.info(f"✅ AI service context updated for conversation: {conversation.id}")
        
        # Reset idle detector for new conversation
        self.idle_detector.reset_activity(conversation.id)
        
        # Emit signal for external components
        self.conversation_changed.emit(conversation.id)
        
        logger.info(f"✅ Switched to conversation: {conversation.title}")
    
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
                    logger.info(f"✅ New conversation created: {conversation.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create conversation: {e}")
                self.append_output("❌ Failed to create new conversation", "error")
        
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
            self.append_output("⚠️ No conversation selected for export", "warning")
            return
        
        logger.info(f"📤 Export requested for conversation: {self.current_conversation.id}")
        self.export_requested.emit(self.current_conversation.id)
    
    @pyqtSlot(str)
    def _on_idle_detected(self, conversation_id: str):
        """Handle idle detection for background summarization."""
        if not self.conversation_manager or not conversation_id:
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
        
        # Create background worker
        class SummarizationWorker(QObject):
            finished = pyqtSignal(str, bool)  # conversation_id, success
            
            def __init__(self, conversation_manager, conversation_id):
                super().__init__()
                self.conversation_manager = conversation_manager
                self.conversation_id = conversation_id
            
            def run(self):
                try:
                    # Get summary service
                    if hasattr(self.conversation_manager, 'conversation_service'):
                        summary_service = self.conversation_manager.conversation_service.summary_service
                        
                        # Generate summary asynchronously
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            success = loop.run_until_complete(
                                summary_service.generate_summary(self.conversation_id)
                            )
                            self.finished.emit(self.conversation_id, success)
                        finally:
                            loop.close()
                    else:
                        self.finished.emit(self.conversation_id, False)
                        
                except Exception as e:
                    logger.error(f"Summarization worker error: {e}")
                    self.finished.emit(self.conversation_id, False)
        
        # Process first conversation in queue
        conversation_id = self.summarization_queue[0]
        
        # Create and start worker thread
        self.summary_thread = QThread()
        self.summary_worker = SummarizationWorker(self.conversation_manager, conversation_id)
        self.summary_worker.moveToThread(self.summary_thread)
        
        # Connect signals
        self.summary_thread.started.connect(self.summary_worker.run)
        self.summary_worker.finished.connect(self._on_summarization_finished)
        self.summary_worker.finished.connect(self.summary_thread.quit)
        self.summary_worker.finished.connect(self.summary_worker.deleteLater)
        self.summary_thread.finished.connect(self.summary_thread.deleteLater)
        
        # Start processing
        self.summary_thread.start()
    
    @pyqtSlot(str, bool)
    def _on_summarization_finished(self, conversation_id: str, success: bool):
        """Handle completion of background summarization."""
        # Remove from queue
        if conversation_id in self.summarization_queue:
            self.summarization_queue.remove(conversation_id)
        
        if success:
            if hasattr(self, 'summary_notification'):
                self.summary_notification.setText("✅ Summary generated")
            logger.info(f"✅ Summary generated for conversation: {conversation_id}")
            
            # Update conversation data if it's the current one
            if self.current_conversation and self.current_conversation.id == conversation_id:
                self._refresh_current_conversation()
        else:
            if hasattr(self, 'summary_notification'):
                self.summary_notification.setText("❌ Summary failed")
            logger.warning(f"❌ Summary generation failed for conversation: {conversation_id}")
        
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
        
        # Display command in output
        self.append_output(f">>> {command}", "input")
        
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
            self.append_output("  exit     - Minimize to system tray", "info")
            self.append_output("  quit     - Exit the application", "info")
            self.append_output("  context  - Show AI context status (debug)", "info")
            self.append_output("  render_stats - Show markdown rendering statistics", "info")
            self.append_output("  test_markdown - Test markdown rendering with examples", "info")
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
            self._markdown_renderer = MarkdownRenderer()
        
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
            color = self._markdown_renderer.color_scheme.get(style, "#f0f0f0")
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
            cursor.insertHtml('<span style="color: #808080; font-style: italic;">[Previous messages truncated for performance]</span><br><br>')
            
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
    
    def _send_to_ai(self, message: str):
        """Send message to AI service with conversation management."""
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
                                logger.info(f"✅ AI response received with context (context size: {len(ai_service.conversation.messages)} messages)")
                                logger.info(f"🔍 AI WORKER SUCCESS - Response length: {len(response_content) if response_content else 0}")
                                logger.info(f"🔍 AI WORKER SUCCESS - Response content: '{response_content}'")
                                self.response_received.emit(response_content, True)
                            else:
                                error_msg = f"❌ AI Error: {result.get('error', 'Unknown error')}"
                                logger.error(f"AI service error: {error_msg}")
                                self.response_received.emit(error_msg, False)
                            return
                        else:
                            logger.warning("⚠️  Conversation manager AI service not available")
                    
                    # Only fallback to basic AI service if conversation manager not available
                    logger.warning("🔄 Falling back to basic AI service (context may be lost)")
                    ai_service = self._get_basic_ai_service()
                    
                    if not ai_service or not ai_service.is_initialized:
                        self.response_received.emit(
                            "❌ AI service not available. Please configure AI settings first.", 
                            False
                        )
                        return
                    
                    # Send message to basic AI service (without conversation context)
                    logger.debug("Sent Message: %s", self.message)
                    result = ai_service.send_message(self.message)
                    
                    if result.get('success', False):
                        response_content = result['response']
                        logger.warning("⚠️  Using basic AI service - conversation context may be limited")
                        logger.info(f"🔍 BASIC AI WORKER SUCCESS - Response length: {len(response_content) if response_content else 0}")
                        logger.info(f"🔍 BASIC AI WORKER SUCCESS - Response content: '{response_content}'")
                        self.response_received.emit(response_content, True)
                    else:
                        error_msg = f"❌ AI Error: {result.get('error', 'Unknown error')}"
                        self.response_received.emit(error_msg, False)
                        
                except Exception as e:
                    logger.error(f"Enhanced AI worker error: {e}")
                    self.response_received.emit(f"❌ Error: {str(e)}", False)
            
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
            # Debug: Check response content
            if not response or not response.strip():
                logger.warning(f"Empty AI response received: '{response}'")
                response = "[No response content received]"
            
            # Display AI label first
            self.append_output("🤖 **AI Response:**", "response")
            # Display the actual response without prefixing to preserve markdown
            self.append_output(response, "response")
            
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
            self.append_output(response, "error")
        
        logger.debug(f"Enhanced AI response displayed: success={success}")
    
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
                logger.error(f"❌ Failed to load conversations after setting manager: {e}", exc_info=True)
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
            logger.error(f"❌ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
    
    async def _restore_conversation_async(self, conversation_id: str):
        """Restore conversation asynchronously."""
        try:
            # Save current conversation if it has messages
            if self.current_conversation and self._has_unsaved_messages():
                await self._save_current_conversation_before_switch()
            
            # Simple atomic database operation: set this conversation as active, all others as pinned
            success = self.conversation_manager.set_conversation_active_simple(conversation_id)
            if not success:
                logger.error(f"❌ Failed to set conversation {conversation_id} as active in database")
                self.append_output("❌ Failed to restore conversation", "error")
                return
            
            # Load the conversation from database with messages
            conversation = await self.conversation_manager.get_conversation(conversation_id, include_messages=True)
            
            if conversation:
                # Set as current conversation and update AI context
                self.current_conversation = conversation
                logger.info(f"✅ Restored conversation: {conversation.title}")
                
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
                logger.warning(f"⚠️  Conversation {conversation_id} not found in database")
                self.append_output(f"⚠️ Could not restore conversation {conversation_id[:8]}... (not found)", "warning")
                
        except Exception as e:
            logger.error(f"❌ Failed to restore conversation {conversation_id}: {e}", exc_info=True)
            self.append_output(f"❌ Failed to restore conversation: {str(e)}", "error")
    
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
        warning_label = QLabel("⚠️ This action cannot be undone. Deleted conversations will be permanently removed.")
        warning_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
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
            f"Are you sure you want to delete {count} conversation{'s' if count > 1 else ''}?\n\n{titles_preview}\n\n⚠️ This action cannot be undone.",
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
            self.append_output(f"✅ Deleted {deleted_count} conversation{'s' if deleted_count != 1 else ''}", "system")
            
        except Exception as e:
            logger.error(f"Failed to delete conversations: {e}")
            self.append_output(f"❌ Failed to delete conversations: {str(e)}", "error")
    
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
                    logger.debug(f"✅ Autosaved conversation: {self.current_conversation.id}")
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
                            logger.info(f"✅ Auto-created conversation synchronously: {conversation.title}")
                        else:
                            logger.error("❌ Failed to create conversation - None returned")
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(loop)  # Restore original loop
                else:
                    # Run synchronously
                    conversation = loop.run_until_complete(self._create_conversation_async(title, message))
                    if conversation:
                        self.current_conversation = conversation
                        logger.info(f"✅ Auto-created conversation: {conversation.title}")
                    else:
                        logger.error("❌ Failed to create conversation - None returned")
                        
            except Exception as loop_error:
                logger.error(f"❌ Loop error during conversation creation: {loop_error}")
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
                        status=ConversationStatus.ACTIVE,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        metadata=metadata
                    )
                    
                    self.current_conversation = temp_conversation
                    logger.info(f"⚡ Created temporary conversation for immediate use: {conversation_id}")
                    
                    # Schedule proper database creation in background
                    asyncio.create_task(self._save_temp_conversation_to_db(temp_conversation, message))
                    
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback conversation creation also failed: {fallback_error}")
                
        except Exception as e:
            logger.error(f"❌ Failed to auto-create conversation: {e}", exc_info=True)
    
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
                logger.info(f"✅ Created conversation: {conversation.title}")
                return conversation
            
        except Exception as e:
            logger.error(f"❌ Failed to create conversation async: {e}")
        
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
                logger.info(f"✅ Saved temporary conversation to database: {db_conversation.id}")
                
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
                logger.error(f"❌ Failed to save temporary conversation to database")
                
        except Exception as e:
            logger.error(f"❌ Failed to save temporary conversation to database: {e}", exc_info=True)
    
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
            logger.error(f"❌ Failed to refresh conversations: {e}", exc_info=True)
    
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
                    logger.info(f"✅ Conversation created with title: {title}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create conversation with title: {e}")
                self.append_output("❌ Failed to create new conversation", "error")
        
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
        """Handle help button click - send help command and display result."""
        # Send help command to the REPL
        self.command_input.setText("help")
        self._on_command_entered()
    
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
                # Style button as active/pressed
                self.move_btn.setStyleSheet("""
                    QToolButton {
                        background-color: rgba(255, 215, 0, 0.8);
                        color: black;
                        border: 2px solid rgba(255, 255, 255, 0.8);
                        border-radius: 4px;
                        padding: 4px;
                        font-weight: bold;
                    }
                    QToolButton:hover {
                        background-color: rgba(255, 215, 0, 0.9);
                    }
                """)
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
                self.append_output("⚠️ Conversation management not available", "error")
                return
            
            # Get AI service for conversation integration
            ai_service = None
            if self.conversation_manager:
                ai_service = self.conversation_manager.get_ai_service()
            
            if not ai_service or not hasattr(ai_service, 'conversation_service'):
                self.append_output("⚠️ AI service doesn't support conversation management", "error")
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
                        self.append_output("✅ Started new conversation", "system")
                        if save_current and current_id:
                            self.append_output("💾 Previous conversation saved with auto-generated title", "system")
                        
                        # Add welcome message for new conversation
                        self.append_output("💬 Ghostman Conversation Manager v2.0", "system")
                        self.append_output("🚀 New conversation started - type your message or 'help' for commands", "system")
                    else:
                        self.append_output("❌ Failed to start new conversation", "error")
                        
                except Exception as e:
                    logger.error(f"Failed to create new conversation: {e}")
                    self.append_output(f"❌ Error creating new conversation: {e}", "error")
            
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
                    self.append_output(f"❌ Error: {e}", "error")
            
            QTimer.singleShot(100, run_async)
            
        except Exception as e:
            logger.error(f"New conversation failed: {e}")
            self.append_output(f"❌ Error: {e}", "error")
    
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
            
            # Create highlight format
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor("#ffff00"))  # Yellow background
            highlight_format.setForeground(QColor("#000000"))  # Black text
            
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
            
            # Stop summarization threads
            if hasattr(self, 'summary_thread') and self.summary_thread.isRunning():
                self.summary_thread.quit()
                self.summary_thread.wait(3000)
            
            # Clear conversation references
            self.current_conversation = None
            self.conversations_list.clear()
            
            logger.info("✅ Enhanced REPL Widget shut down successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during REPL widget shutdown: {e}")