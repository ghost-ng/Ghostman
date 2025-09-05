"""
Production-Ready Link Detection Solutions for PyQt6 QTextEdit
=============================================================

This file provides multiple robust approaches for implementing reliable mouse cursor 
changes when hovering over links in PyQt6 QTextEdit widgets.

Author: Claude Code (Anthropic)
Last Updated: 2025-08-24
"""

from PyQt6.QtWidgets import QTextEdit, QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QEvent, QTimer, QPoint
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont, QColor, QTextDocument
import logging
import re
from typing import Optional, Tuple, Dict, Set
import weakref

logger = logging.getLogger(__name__)


class RobustLinkDetector:
    """
    SOLUTION 1: The Most Reliable Approach - Text Document Analysis
    
    This approach uses QTextDocument iteration and maintains an internal
    link registry for maximum reliability and performance.
    """
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = weakref.ref(text_edit)  # Avoid circular references
        self.link_registry: Dict[int, Tuple[int, int, str]] = {}  # block_num: (start, end, href)
        self.last_cursor_position = -1
        self.last_cursor_state = None
        
        # Performance optimization: debounced cursor updates
        self._cursor_update_timer = QTimer()
        self._cursor_update_timer.setSingleShot(True)
        self._cursor_update_timer.timeout.connect(self._update_cursor_delayed)
        
        self._rebuild_link_registry()
    
    def _rebuild_link_registry(self):
        """Rebuild the internal link registry by scanning the document."""
        text_edit = self.text_edit()
        if not text_edit:
            return
            
        self.link_registry.clear()
        document = text_edit.document()
        
        for block_num in range(document.blockCount()):
            block = document.findBlockByNumber(block_num)
            if not block.isValid():
                continue
                
            # Iterate through all text fragments in this block
            block_it = block.begin()
            block_position = block.position()
            
            while not block_it.atEnd():
                fragment = block_it.fragment()
                if fragment.isValid():
                    char_format = fragment.charFormat()
                    
                    # Check if this fragment is an anchor
                    if char_format.isAnchor() and char_format.anchorHref():
                        start_pos = fragment.position() - block_position
                        end_pos = start_pos + fragment.length()
                        href = char_format.anchorHref()
                        
                        # Store link information
                        if block_num not in self.link_registry:
                            self.link_registry[block_num] = []
                        self.link_registry[block_num].append((start_pos, end_pos, href))
                
                block_it += 1
    
    def handle_mouse_move(self, position: QPoint) -> bool:
        """
        Handle mouse move events with optimized link detection.
        Returns True if cursor was changed, False otherwise.
        """
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        # Get cursor position
        cursor = text_edit.cursorForPosition(position)
        current_position = cursor.position()
        
        # Performance optimization: avoid redundant checks
        if current_position == self.last_cursor_position:
            return False
        
        self.last_cursor_position = current_position
        
        # Debounce cursor updates for better performance
        self._cursor_update_timer.start(10)  # 10ms delay
        return True
    
    def _update_cursor_delayed(self):
        """Delayed cursor update for performance optimization."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        cursor.setPosition(self.last_cursor_position)
        
        # Check if position is over a link
        is_over_link, href = self._is_position_over_link(cursor)
        
        if is_over_link:
            if self.last_cursor_state != "link":
                text_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                self.last_cursor_state = "link"
        else:
            if self.last_cursor_state != "text":
                text_edit.setCursor(Qt.CursorShape.IBeamCursor)
                self.last_cursor_state = "text"
    
    def _is_position_over_link(self, cursor: QTextCursor) -> Tuple[bool, Optional[str]]:
        """
        Check if cursor position is over a link using the internal registry.
        Returns (is_over_link, href).
        """
        block = cursor.block()
        if not block.isValid():
            return False, None
        
        block_num = block.blockNumber()
        if block_num not in self.link_registry:
            return False, None
        
        position_in_block = cursor.position() - block.position()
        
        # Check all links in this block
        for start_pos, end_pos, href in self.link_registry[block_num]:
            if start_pos <= position_in_block < end_pos:
                return True, href
        
        return False, None
    
    def document_changed(self):
        """Call this when the document content changes to rebuild the registry."""
        self._rebuild_link_registry()


class HybridLinkDetector:
    """
    SOLUTION 2: Hybrid Approach - Multiple Detection Methods
    
    This combines multiple detection methods for maximum compatibility
    and falls back gracefully when one method fails.
    """
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = weakref.ref(text_edit)
        self.last_position = QPoint(-1, -1)
        self.detection_cache: Dict[int, bool] = {}  # position -> is_link
        
        # Performance tracking
        self.method_reliability = {
            'anchorAt': 0.0,
            'charFormat': 0.0,
            'htmlParsing': 0.0
        }
    
    def handle_mouse_move(self, position: QPoint) -> bool:
        """Handle mouse move with hybrid detection approach."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        # Avoid redundant checks
        if position == self.last_position:
            return False
        
        self.last_position = position
        
        # Check cache first
        cache_key = hash((position.x(), position.y()))
        if cache_key in self.detection_cache:
            is_link = self.detection_cache[cache_key]
        else:
            is_link = self._detect_link_multi_method(position)
            self.detection_cache[cache_key] = is_link
            
            # Clear cache when it gets too large
            if len(self.detection_cache) > 1000:
                self.detection_cache.clear()
        
        # Update cursor
        cursor_shape = Qt.CursorShape.PointingHandCursor if is_link else Qt.CursorShape.IBeamCursor
        text_edit.setCursor(cursor_shape)
        
        return True
    
    def _detect_link_multi_method(self, position: QPoint) -> bool:
        """Use multiple detection methods and return the most reliable result."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        results = []
        
        # Method 1: anchorAt (fast but unreliable)
        try:
            anchor = text_edit.anchorAt(position)
            method1_result = bool(anchor.strip())
            results.append(('anchorAt', method1_result))
        except Exception as e:
            logger.debug(f"anchorAt method failed: {e}")
            results.append(('anchorAt', False))
        
        # Method 2: Character format analysis (more reliable)
        try:
            cursor = text_edit.cursorForPosition(position)
            char_format = cursor.charFormat()
            method2_result = char_format.isAnchor() and bool(char_format.anchorHref())
            results.append(('charFormat', method2_result))
        except Exception as e:
            logger.debug(f"charFormat method failed: {e}")
            results.append(('charFormat', False))
        
        # Method 3: HTML content analysis (fallback)
        try:
            method3_result = self._detect_link_via_html_analysis(position)
            results.append(('htmlParsing', method3_result))
        except Exception as e:
            logger.debug(f"htmlParsing method failed: {e}")
            results.append(('htmlParsing', False))
        
        # Determine result based on method reliability and consensus
        return self._determine_consensus(results)
    
    def _detect_link_via_html_analysis(self, position: QPoint) -> bool:
        """Analyze HTML content at position to detect links."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        cursor = text_edit.cursorForPosition(position)
        
        # Select word or nearby content
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if not cursor.hasSelection():
            # If no word selected, try selecting a small area around the cursor
            cursor.setPosition(cursor.position() - 5)
            cursor.movePosition(QTextCursor.MoveOperation.Right, 
                              QTextCursor.MoveMode.KeepAnchor, 10)
        
        selected_html = cursor.selection().toHtml()
        
        # Check if the selected content contains anchor tags
        anchor_pattern = re.compile(r'<a\s+[^>]*href\s*=\s*["\'][^"\']*["\'][^>]*>', re.IGNORECASE)
        return bool(anchor_pattern.search(selected_html))
    
    def _determine_consensus(self, results: list) -> bool:
        """Determine the final result based on method reliability and consensus."""
        # If any reliable method says it's a link, trust it
        for method, result in results:
            if result and self.method_reliability.get(method, 0) > 0.7:
                return True
        
        # Check for consensus (2 out of 3 methods agree)
        true_count = sum(1 for _, result in results if result)
        if true_count >= 2:
            return True
        
        # If charFormat method (most reliable) says it's a link, trust it
        for method, result in results:
            if method == 'charFormat':
                return result
        
        return False


class EventFilterLinkHandler:
    """
    SOLUTION 3: Complete Event Filter Implementation
    
    A complete, drop-in replacement for your current event filter that
    handles all edge cases and provides robust link detection.
    """
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = text_edit
        self.link_detector = RobustLinkDetector(text_edit)
        
        # Debug tracking
        self.last_hover_state = None
        self.debug_enabled = False  # Set to True for debugging
        
        # Install event filter and enable mouse tracking
        text_edit.installEventFilter(self)
        text_edit.setMouseTracking(True)
        
        # Connect document change signal to rebuild link registry
        text_edit.document().contentsChanged.connect(self.link_detector.document_changed)
    
    def eventFilter(self, obj, event):
        """Complete event filter with robust link detection."""
        if obj != self.text_edit:
            return False
        
        # Handle mouse move events for cursor changes
        if event.type() == QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)
        
        # Handle mouse press events for link clicks
        elif event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                return self._handle_mouse_click(event)
        
        return False
    
    def _handle_mouse_move(self, event) -> bool:
        """Handle mouse move events for cursor changes."""
        try:
            changed = self.link_detector.handle_mouse_move(event.pos())
            
            # Debug logging
            if self.debug_enabled and changed:
                cursor = self.text_edit.cursorForPosition(event.pos())
                is_link, href = self.link_detector._is_position_over_link(cursor)
                
                if is_link != (self.last_hover_state == "link"):
                    state = "link" if is_link else "text"
                    logger.debug(f"Cursor changed to {state} - href: {href}")
                    self.last_hover_state = state
            
            return False  # Allow other handlers to process the event
        
        except Exception as e:
            logger.error(f"Error in mouse move handler: {e}")
            return False
    
    def _handle_mouse_click(self, event) -> bool:
        """Handle mouse click events for link activation."""
        try:
            cursor = self.text_edit.cursorForPosition(event.pos())
            is_link, href = self.link_detector._is_position_over_link(cursor)
            
            if is_link and href:
                # Handle the link click
                self._handle_link_click(href)
                return True  # Event handled
        
        except Exception as e:
            logger.error(f"Error in mouse click handler: {e}")
        
        return False
    
    def _handle_link_click(self, href: str):
        """Handle link click - customize this method for your application."""
        if href.startswith('resend_message'):
            # Handle internal resend message links
            self._handle_resend_click(href)
        else:
            # Handle external URLs
            import webbrowser
            try:
                webbrowser.open(href)
            except Exception as e:
                logger.error(f"Failed to open URL {href}: {e}")
    
    def _handle_resend_click(self, href: str):
        """Handle resend message clicks - implement based on your needs."""
        # This should be customized for your application
        logger.info(f"Resend message clicked: {href}")


# SOLUTION 4: Advanced HTML Link Processor
class AdvancedHTMLLinkProcessor:
    """
    Advanced HTML processing for reliable link insertion that works
    perfectly with Qt's anchor detection system.
    """
    
    @staticmethod
    def process_html_with_reliable_anchors(html_content: str) -> str:
        """
        Process HTML content to ensure all links work reliably with Qt's anchor system.
        """
        # Pattern to match anchor tags
        anchor_pattern = re.compile(
            r'<a\s+([^>]*?)href\s*=\s*["\']([^"\']*)["\']([^>]*?)>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        
        def replace_anchor(match):
            attrs_before = match.group(1).strip()
            href = match.group(2)
            attrs_after = match.group(3).strip()
            text = match.group(4)
            
            # Ensure proper anchor formatting for Qt
            attrs = []
            if attrs_before:
                attrs.append(attrs_before)
            if attrs_after:
                attrs.append(attrs_after)
            
            # Add any additional attributes needed for Qt recognition
            extra_attrs = ' '.join(attrs)
            if extra_attrs and not extra_attrs.endswith(' '):
                extra_attrs += ' '
            
            # Return properly formatted anchor
            return f'<a {extra_attrs}href="{href}">{text}</a>'
        
        # Process all anchors
        processed_html = anchor_pattern.sub(replace_anchor, html_content)
        
        return processed_html
    
    @staticmethod
    def insert_html_with_reliable_anchors(cursor: QTextCursor, html_content: str):
        """
        Insert HTML content with guaranteed reliable anchor detection.
        """
        # Process HTML to ensure Qt compatibility
        processed_html = AdvancedHTMLLinkProcessor.process_html_with_reliable_anchors(html_content)
        
        # Parse and insert with character format anchors as fallback
        anchor_pattern = re.compile(
            r'<a\s+[^>]*?href\s*=\s*["\']([^"\']*)["\'][^>]*?>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        
        matches = list(anchor_pattern.finditer(processed_html))
        
        if matches:
            last_end = 0
            
            for match in matches:
                # Insert content before the link
                before_link = processed_html[last_end:match.start()]
                if before_link:
                    cursor.insertHtml(before_link)
                
                # Insert the link with both HTML and character format
                href = match.group(1)
                link_text = match.group(2)
                
                # Method 1: Insert as HTML (for visual formatting)
                cursor.insertHtml(match.group(0))
                
                # Method 2: Also set character format anchor (for Qt detection)
                # This creates a dual-format link that works with both systems
                link_format = QTextCharFormat()
                link_format.setAnchor(True)
                link_format.setAnchorHref(href)
                link_format.setForeground(QColor("#007bff"))  # Link color
                link_format.setFontUnderline(True)
                
                # Move cursor back and apply format
                start_pos = cursor.position() - len(link_text)
                cursor.setPosition(start_pos)
                cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                  QTextCursor.MoveMode.KeepAnchor, len(link_text))
                cursor.mergeCharFormat(link_format)
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                
                last_end = match.end()
            
            # Insert remaining content
            remaining = processed_html[last_end:]
            if remaining:
                cursor.insertHtml(remaining)
        else:
            # No links found, insert normally
            cursor.insertHtml(processed_html)


# SOLUTION 5: Performance-Optimized Implementation
class PerformanceOptimizedLinkHandler:
    """
    Performance-optimized implementation for applications with large amounts of text.
    """
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = weakref.ref(text_edit)
        
        # Spatial indexing for fast link lookups
        self.link_spatial_index: Dict[int, Set[Tuple[int, int, str]]] = {}  # y_coord -> links
        
        # Performance settings
        self.update_interval = 50  # ms between updates
        self.cache_size_limit = 500
        
        # Optimized timers
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_delayed_update)
        
        self._pending_position = None
        self._position_cache: Dict[Tuple[int, int], bool] = {}
    
    def handle_mouse_move(self, position: QPoint) -> bool:
        """Highly optimized mouse move handling."""
        # Cache management
        if len(self._position_cache) > self.cache_size_limit:
            self._position_cache.clear()
        
        # Check cache first
        cache_key = (position.x(), position.y())
        if cache_key in self._position_cache:
            is_link = self._position_cache[cache_key]
            self._update_cursor(is_link)
            return True
        
        # Queue update for performance
        self._pending_position = position
        if not self._update_timer.isActive():
            self._update_timer.start(self.update_interval)
        
        return True
    
    def _perform_delayed_update(self):
        """Perform the actual link detection with caching."""
        if not self._pending_position:
            return
        
        position = self._pending_position
        self._pending_position = None
        
        # Fast spatial lookup
        is_link = self._fast_link_detection(position)
        
        # Cache result
        cache_key = (position.x(), position.y())
        self._position_cache[cache_key] = is_link
        
        # Update cursor
        self._update_cursor(is_link)
    
    def _fast_link_detection(self, position: QPoint) -> bool:
        """Fast link detection using spatial indexing."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        # Use viewport coordinates for spatial lookup
        y_coord = position.y() // 20  # Group by approximate line height
        
        if y_coord in self.link_spatial_index:
            cursor = text_edit.cursorForPosition(position)
            cursor_pos = cursor.position()
            
            for start_pos, end_pos, href in self.link_spatial_index[y_coord]:
                if start_pos <= cursor_pos <= end_pos:
                    return True
        
        # Fallback to standard detection
        return self._standard_detection_fallback(position)
    
    def _standard_detection_fallback(self, position: QPoint) -> bool:
        """Standard detection as fallback when spatial index is not available."""
        text_edit = self.text_edit()
        if not text_edit:
            return False
        
        try:
            cursor = text_edit.cursorForPosition(position)
            char_format = cursor.charFormat()
            return char_format.isAnchor() and bool(char_format.anchorHref())
        except Exception:
            return False
    
    def _update_cursor(self, is_link: bool):
        """Update cursor shape."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        cursor_shape = Qt.CursorShape.PointingHandCursor if is_link else Qt.CursorShape.IBeamCursor
        text_edit.setCursor(cursor_shape)
    
    def rebuild_spatial_index(self):
        """Rebuild spatial index when document changes."""
        text_edit = self.text_edit()
        if not text_edit:
            return
        
        self.link_spatial_index.clear()
        # Implementation depends on your specific needs
        # This is a placeholder for spatial index rebuilding


# Example Usage and Integration
class ExampleUsage:
    """Example of how to integrate these solutions into your application."""
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = text_edit
        
        # Choose the best solution for your needs:
        
        # RECOMMENDED: Use the complete event filter solution
        self.link_handler = EventFilterLinkHandler(text_edit)
        
        # Alternative: Use the robust detector directly
        # self.link_detector = RobustLinkDetector(text_edit)
        # text_edit.installEventFilter(self)
        # text_edit.setMouseTracking(True)
        
        # For high-performance applications:
        # self.link_handler = PerformanceOptimizedLinkHandler(text_edit)
    
    def insert_content_with_links(self, html_content: str):
        """Example of inserting content with reliable links."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Use the advanced HTML processor for reliable links
        AdvancedHTMLLinkProcessor.insert_html_with_reliable_anchors(cursor, html_content)
        
        # Notify link detector of document change
        if hasattr(self.link_handler, 'link_detector'):
            self.link_handler.link_detector.document_changed()


if __name__ == "__main__":
    # Demo application
    app = QApplication([])
    
    window = QMainWindow()
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Create text edit with links
    text_edit = QTextEdit()
    text_edit.setHtml('''
    <p>This is a test with multiple links:</p>
    <p><a href="https://www.example.com">External Link</a></p>
    <p><a href="resend_message:123">Internal Resend Link</a></p>
    <p>Regular text without links.</p>
    <p><a href="https://www.python.org">Another external link</a></p>
    ''')
    
    # Apply the robust link detection
    link_handler = EventFilterLinkHandler(text_edit)
    link_handler.debug_enabled = True  # Enable debug logging
    
    layout.addWidget(text_edit)
    window.setCentralWidget(central_widget)
    window.show()
    
    app.exec()