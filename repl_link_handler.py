"""
Production-Ready Link Handler for REPL Widget
=============================================

This module provides a drop-in replacement for the link detection system
in your existing REPL widget, designed to work with your current architecture.

Usage:
1. Import ReplLinkHandler
2. Replace your existing eventFilter method
3. Use the improved HTML insertion method

Author: Claude Code (Anthropic)
"""

from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtCore import Qt, QEvent, QTimer, QPoint
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QDesktopServices, QUrl
import logging
import re
import weakref
from typing import Optional, Tuple, Dict, List
import html

logger = logging.getLogger(__name__)


class ReplLinkHandler:
    """
    Robust link detection and handling system for REPL widgets.
    
    This class provides:
    - Reliable link detection using multiple methods
    - Performance-optimized cursor updates
    - Support for both external URLs and internal actions
    - Debug logging capabilities
    - Fallback mechanisms for edge cases
    """
    
    def __init__(self, text_edit: QTextEdit, parent_repl=None):
        """
        Initialize the link handler.
        
        Args:
            text_edit: The QTextEdit widget to monitor
            parent_repl: Reference to the parent REPL widget (for callbacks)
        """
        self.text_edit = weakref.ref(text_edit)
        self.parent_repl = weakref.ref(parent_repl) if parent_repl else None
        
        # Link registry for reliable detection
        self.link_registry: Dict[int, List[Tuple[int, int, str]]] = {}  # block_num: [(start, end, href), ...]
        
        # Performance optimization
        self.last_position = QPoint(-1, -1)
        self.last_cursor_state = None
        self.position_cache: Dict[Tuple[int, int], Tuple[bool, Optional[str]]] = {}
        
        # Debounced updates for better performance
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_cursor_update)
        self._pending_position = None
        
        # Debug settings
        self.debug_enabled = False
        self._last_hover_debug = None
        
        # Initialize
        self._rebuild_link_registry()
        
        # Connect to document changes
        if text_edit.document():
            text_edit.document().contentsChanged.connect(self._on_document_changed)
    
    def handle_mouse_move(self, event_pos: QPoint) -> bool:
        """
        Handle mouse move events for cursor changes.
        
        Args:
            event_pos: Mouse position from the event
            
        Returns:
            bool: True if the event was handled
        """
        # Avoid redundant processing
        if event_pos == self.last_position:
            return False
        
        self.last_position = event_pos
        
        # Check cache first for performance
        cache_key = (event_pos.x(), event_pos.y())
        if cache_key in self.position_cache:
            is_link, href = self.position_cache[cache_key]
            self._update_cursor_state(is_link, href)
            return True
        
        # Queue update for performance optimization
        self._pending_position = event_pos
        if not self._update_timer.isActive():
            self._update_timer.start(10)  # 10ms debounce
        
        return True
    
    def handle_mouse_click(self, event_pos: QPoint) -> bool:
        """
        Handle mouse click events for link activation.
        
        Args:
            event_pos: Mouse position from the event
            
        Returns:
            bool: True if a link was clicked and handled
        """
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        try:
            # Detect link at click position
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
            # Remove oldest entries (simple approach)
            keys_to_remove = list(self.position_cache.keys())[:500]
            for key in keys_to_remove:
                del self.position_cache[key]
        
        # Update cursor
        self._update_cursor_state(is_link, href)
    
    def _detect_link_at_position(self, position: QPoint) -> Tuple[bool, Optional[str]]:
        """
        Detect if there's a link at the given position using multiple methods.
        
        Args:
            position: Mouse position to check
            
        Returns:
            Tuple[bool, Optional[str]]: (is_link, href)
        """
        text_edit = self.text_edit()
        if not text_edit:
            return False, None
        
        # Method 1: Registry-based detection (most reliable)
        registry_result = self._detect_via_registry(position)
        if registry_result[0]:
            return registry_result
        
        # Method 2: Character format detection (reliable for Qt-inserted anchors)
        format_result = self._detect_via_char_format(position)
        if format_result[0]:
            return format_result
        
        # Method 3: anchorAt method (fast but sometimes unreliable)
        anchor_result = self._detect_via_anchor_at(position)
        if anchor_result[0]:
            return anchor_result
        
        return False, None
    
    def _detect_via_registry(self, position: QPoint) -> Tuple[bool, Optional[str]]:
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
    
    def _detect_via_char_format(self, position: QPoint) -> Tuple[bool, Optional[str]]:
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
    
    def _detect_via_anchor_at(self, position: QPoint) -> Tuple[bool, Optional[str]]:
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
    
    def _update_cursor_state(self, is_link: bool, href: Optional[str]):
        """Update the cursor state and provide debug feedback."""
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
            
            # Debug logging
            if self.debug_enabled and self._last_hover_debug != new_state:
                logger.debug(f"Cursor state changed to {new_state} - href: {href}")
                self._last_hover_debug = new_state
    
    def _handle_link_activation(self, href: str):
        """
        Handle link activation (clicks).
        
        Args:
            href: The link href to activate
        """
        if self.debug_enabled:
            logger.debug(f"Link activated: {href}")
        
        try:
            # Handle internal resend message links
            if href.startswith('resend_message'):
                self._handle_resend_message(href)
            
            # Handle external URLs
            elif href.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
                self._handle_external_url(href)
            
            # Handle file URLs
            elif href.startswith('file://'):
                self._handle_file_url(href)
            
            else:
                # Handle other internal actions or custom schemes
                self._handle_custom_link(href)
        
        except Exception as e:
            logger.error(f"Error handling link activation '{href}': {e}")
    
    def _handle_resend_message(self, href: str):
        """Handle resend message links."""
        parent_repl = self.parent_repl() if self.parent_repl else None
        if parent_repl and hasattr(parent_repl, '_handle_resend_click'):
            parent_repl._handle_resend_click(href)
        else:
            logger.warning(f"No resend handler available for: {href}")
    
    def _handle_external_url(self, href: str):
        """Handle external URL links."""
        try:
            QDesktopServices.openUrl(QUrl(href))
        except Exception as e:
            logger.error(f"Failed to open external URL '{href}': {e}")
    
    def _handle_file_url(self, href: str):
        """Handle file URL links."""
        try:
            QDesktopServices.openUrl(QUrl(href))
        except Exception as e:
            logger.error(f"Failed to open file URL '{href}': {e}")
    
    def _handle_custom_link(self, href: str):
        """Handle custom link schemes."""
        logger.info(f"Custom link activated: {href}")
        # Implement custom link handling based on your application needs
    
    def _rebuild_link_registry(self):
        """Rebuild the link registry by scanning the document."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        self.link_registry.clear()
        self.position_cache.clear()  # Clear position cache as well
        
        document = text_edit.document()
        
        try:
            for block_num in range(document.blockCount()):
                block = document.findBlockByNumber(block_num)
                if not block.isValid():
                    continue
                
                # Analyze text fragments in this block
                self._scan_block_for_links(block_num, block)
        
        except Exception as e:
            logger.error(f"Error rebuilding link registry: {e}")
    
    def _scan_block_for_links(self, block_num: int, block):
        """Scan a single block for links and add them to the registry."""
        block_it = block.begin()
        block_position = block.position()
        
        while not block_it.atEnd():
            fragment = block_it.fragment()
            if fragment.isValid():
                char_format = fragment.charFormat()
                
                # Check if this fragment is an anchor
                if char_format.isAnchor():
                    href = char_format.anchorHref()
                    if href:
                        start_pos = fragment.position() - block_position
                        end_pos = start_pos + fragment.length()
                        
                        # Add to registry
                        if block_num not in self.link_registry:
                            self.link_registry[block_num] = []
                        
                        self.link_registry[block_num].append((start_pos, end_pos, href))
            
            block_it += 1
    
    def _on_document_changed(self):
        """Handle document content changes."""
        # Rebuild registry when document changes
        self._rebuild_link_registry()
    
    def insert_html_with_reliable_anchors(self, cursor: QTextCursor, html_content: str):
        """
        Insert HTML content with reliable anchor detection.
        
        This method ensures that links are inserted in a way that works
        with all detection methods.
        
        Args:
            cursor: QTextCursor to insert at
            html_content: HTML content to insert
        """
        try:
            # Process HTML to ensure proper anchor formatting
            processed_html = self._process_html_for_reliability(html_content)
            
            # Parse links for dual-format insertion
            anchor_pattern = re.compile(
                r'<a\s+([^>]*?)href\s*=\s*["\']([^"\']*)["\']([^>]*?)>(.*?)</a>',
                re.IGNORECASE | re.DOTALL
            )
            
            matches = list(anchor_pattern.finditer(processed_html))
            
            if matches:
                self._insert_html_with_links(cursor, processed_html, matches)
            else:
                # No links, insert normally
                cursor.insertHtml(processed_html)
            
            # Trigger registry rebuild
            self._rebuild_link_registry()
        
        except Exception as e:
            logger.error(f"Error inserting HTML with anchors: {e}")
            # Fallback to simple insertion
            try:
                cursor.insertHtml(html_content)
            except Exception as fallback_error:
                logger.error(f"Fallback HTML insertion failed: {fallback_error}")
                cursor.insertText(html.escape(str(html_content)))
    
    def _process_html_for_reliability(self, html_content: str) -> str:
        """Process HTML to ensure maximum compatibility with Qt's anchor system."""
        # Ensure proper anchor tag formatting
        anchor_pattern = re.compile(
            r'<a\s+([^>]*?)href\s*=\s*["\']([^"\']*)["\']([^>]*?)>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        
        def fix_anchor(match):
            attrs_before = match.group(1).strip()
            href = match.group(2)
            attrs_after = match.group(3).strip()
            text = match.group(4)
            
            # Combine attributes properly
            all_attrs = []
            if attrs_before:
                all_attrs.append(attrs_before)
            if attrs_after:
                all_attrs.append(attrs_after)
            
            attrs_str = ' '.join(all_attrs)
            if attrs_str and not attrs_str.endswith(' '):
                attrs_str += ' '
            
            return f'<a {attrs_str}href="{href}">{text}</a>'
        
        return anchor_pattern.sub(fix_anchor, html_content)
    
    def _insert_html_with_links(self, cursor: QTextCursor, html_content: str, matches: List):
        """Insert HTML content with dual-format links for maximum reliability."""
        last_end = 0
        
        for match in matches:
            # Insert content before the link
            before_link = html_content[last_end:match.start()]
            if before_link:
                cursor.insertHtml(before_link)
            
            # Extract link information
            href = match.group(2)
            link_text = match.group(4)
            
            # Insert link with character format for reliable detection
            link_format = QTextCharFormat()
            link_format.setAnchor(True)
            link_format.setAnchorHref(href)
            link_format.setForeground(QColor("#007bff"))  # Standard link color
            link_format.setFontUnderline(True)
            
            # Insert the link text with proper formatting
            cursor.insertText(link_text, link_format)
            
            last_end = match.end()
        
        # Insert remaining content after last link
        remaining = html_content[last_end:]
        if remaining:
            cursor.insertHtml(remaining)


# Integration helper for existing REPL widgets
class ReplEventFilterMixin:
    """
    Mixin class that can be added to existing REPL widgets to provide
    improved link detection without major refactoring.
    """
    
    def setup_improved_link_detection(self):
        """Call this method in your REPL widget's __init__ method."""
        if not hasattr(self, 'output_display'):
            logger.error("ReplEventFilterMixin requires 'output_display' attribute")
            return
        
        # Initialize the link handler
        self.link_handler = ReplLinkHandler(self.output_display, self)
        
        # Enable debug mode if needed
        if hasattr(self, 'debug_mode') and self.debug_mode:
            self.link_handler.debug_enabled = True
        
        # Install event filter and enable mouse tracking
        self.output_display.installEventFilter(self)
        self.output_display.setMouseTracking(True)
    
    def eventFilter(self, obj, event):
        """
        Drop-in replacement for your existing eventFilter method.
        
        Call this from your existing eventFilter or replace it entirely.
        """
        if hasattr(self, 'output_display') and obj == self.output_display:
            # Handle mouse move events
            if event.type() == QEvent.Type.MouseMove:
                if hasattr(self, 'link_handler'):
                    self.link_handler.handle_mouse_move(event.pos())
                return False  # Allow other handlers
            
            # Handle mouse click events
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton and hasattr(self, 'link_handler'):
                    if self.link_handler.handle_mouse_click(event.pos()):
                        return True  # Event handled
        
        # Call parent implementation or handle other events
        return super().eventFilter(obj, event) if hasattr(super(), 'eventFilter') else False
    
    def insert_output_with_improved_links(self, text: str, style: str = "normal", force_plain: bool = False):
        """
        Use this method instead of your current output insertion method
        to get improved link handling.
        """
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if hasattr(self, 'link_handler') and hasattr(self, '_markdown_renderer'):
            # Render with your existing markdown renderer
            try:
                html_content = self._markdown_renderer.render(text, style, force_plain)
                self.link_handler.insert_html_with_reliable_anchors(cursor, html_content)
            except Exception as e:
                logger.error(f"Error with improved link insertion: {e}")
                # Fallback to original method
                if hasattr(self, 'insert_output'):
                    self.insert_output(text, style, force_plain)
        else:
            # Fallback if link handler not available
            if hasattr(self, 'insert_output'):
                self.insert_output(text, style, force_plain)


# Example integration
if __name__ == "__main__":
    """
    Example of how to integrate this into your existing REPL widget.
    """
    
    # For your existing REPL widget, you would modify it like this:
    
    class ExampleReplWidget(ReplEventFilterMixin):
        def __init__(self, parent=None):
            super().__init__(parent)
            
            # Your existing initialization code...
            self.output_display = QTextEdit()
            
            # Add this line to enable improved link detection
            self.setup_improved_link_detection()
            
            # Rest of your initialization...
        
        def insert_output(self, text: str, style: str = "normal", force_plain: bool = False):
            """Your existing method - can be replaced or kept as fallback."""
            # Use the improved version
            self.insert_output_with_improved_links(text, style, force_plain)
    
    print("Integration example complete. See the class above for implementation details.")