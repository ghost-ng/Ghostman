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
                # NOTE: MixedContentDisplay is NOT registered with theme manager
                # The REPL widget manually passes opacity-adjusted colors to this widget
                # This prevents double updates and ensures proper opacity handling
                logger.debug("MixedContentDisplay uses manual theme updates from REPL widget")
            except Exception as e:
                logger.warning(f"Failed to initialize theme system: {e}")
        else:
            logger.debug("Theme system not available for MixedContentDisplay")
        
    def set_theme_colors(self, colors: Dict[str, str]):
        """Update theme colors with comprehensive widget updating."""
        self.theme_colors = colors
        self._update_stylesheet()
        
        # Update existing widgets with new theme colors using our advanced system
        self._update_existing_widgets_theme()
        
        # Note: _update_existing_widgets_theme() now handles all refresh scheduling
        
    def _update_stylesheet(self):
        """Update the stylesheet based on theme colors.

        Note: Transparency is handled at the window level via setWindowOpacity(),
        not via rgba colors in stylesheets (Qt doesn't support that well).
        """
        if not self.theme_colors:
            return

        bg_color = self.theme_colors.get('bg_primary', self.theme_colors.get('background_primary', '#000000'))
        border_color = self.theme_colors.get('border', self.theme_colors.get('border_subtle', '#666666'))

        # Convert rgba to hex (opacity is handled at window level, not stylesheet level)
        bg_hex = self._convert_rgba_to_hex(bg_color)
        border_hex = self._convert_rgba_to_hex(border_color)

        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_hex};
                border: 1px solid {border_hex};
            }}
            QWidget#MixedContentContainer {{
                background-color: {bg_hex};
            }}
        """)

        logger.debug(f"Applied theme colors: bg={bg_hex}, border={border_hex}")
    
    def _convert_rgba_to_hex(self, color: str) -> str:
        """
        Convert rgba() color to hex for Qt stylesheet compatibility.
        Qt stylesheets don't properly support rgba() colors.

        Args:
            color: Color in any format (hex, rgba, rgb, etc.)

        Returns:
            Hex color string (#RRGGBB)
        """
        import re

        # If already hex, return as-is
        if color.startswith('#'):
            return color

        # Check for rgba() format
        rgba_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)', color)
        if rgba_match:
            r, g, b = rgba_match.groups()[:3]
            # Convert to hex (ignoring alpha channel since Qt stylesheets don't support it)
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

        # If no match, return as-is and hope for the best
        logger.warning(f"Could not convert color '{color}' to hex, using as-is")
        return color

    def _get_smart_text_fallback(self, bg_color: str) -> str:
        """
        Get smart text color fallback based on background brightness.
        Returns dark text for light backgrounds and light text for dark backgrounds.
        """
        try:
            # Convert rgba to hex first if needed
            bg_color = self._convert_rgba_to_hex(bg_color)

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
    
    def _get_message_style_color(self, message_style: str) -> str:
        """Get the appropriate color for a message style from the current theme."""
        if not self.theme_colors:
            return '#ffffff'  # Fallback to white if no theme
        
        # Get base colors
        bg_color = self.theme_colors.get('bg_primary', self.theme_colors.get('background_primary', '#000000'))
        text_primary = self.theme_colors.get('text_primary')
        
        if not text_primary:
            text_primary = self._get_smart_text_fallback(bg_color)
        
        # Map message styles to colors
        style_colors = {
            'normal': text_primary,
            'input': self.theme_colors.get('primary', text_primary),
            'response': text_primary,
            'system': self.theme_colors.get('text_secondary', text_primary),
            'info': self.theme_colors.get('info', text_primary),
            'warning': self.theme_colors.get('warning', text_primary),
            'error': self.theme_colors.get('error', text_primary),
            'divider': self.theme_colors.get('text_secondary', text_primary),
        }
        
        return style_colors.get(message_style, text_primary)
    
    def _inject_theme_color_into_html(self, html_text: str, color: str) -> str:
        """
        Comprehensive HTML color injection that bypasses PyQt6 QLabel caching issues.
        
        This method aggressively modifies HTML content to ensure theme colors are applied
        by using multiple strategies to overcome PyQt6's HTML rendering cache.
        """
        import re
        
        logger.debug(f"Injecting color {color} into HTML: {html_text[:100]}...")
        
        # STRATEGY 1: Remove ALL existing color styles to prevent conflicts
        # This includes inline styles, CSS color properties, and text color attributes
        cleanup_patterns = [
            r'color:\s*[^;}"\']+[;]?',  # CSS color properties
            r'style="[^"]*color[^"]*[;"]',  # Inline color styles
            r'text="[^"]*"',  # HTML text attributes
            r'color="[^"]*"',  # Direct color attributes
        ]
        
        for pattern in cleanup_patterns:
            html_text = re.sub(pattern, '', html_text, flags=re.IGNORECASE)
        
        # STRATEGY 2: Wrap the entire content in a color-controlling div
        # This ensures that even if individual elements don't get color injection,
        # they inherit from the parent container
        html_text = f'<div style="color: {color} !important; font-family: inherit; font-size: inherit;">{html_text}</div>'
        
        # STRATEGY 3: Inject color into ALL HTML tags systematically
        # This covers every possible element that might contain text
        all_text_tags = ['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'strong', 'em', 'b', 'i', 'u', 'li', 'ul', 'ol', 'blockquote', 'code', 'pre']
        
        for tag in all_text_tags:
            # Pattern to match opening tags that don't already have color
            pattern = f'<({tag})(?![^>]*style="[^"]*color[^"]*")([^>]*)>'
            replacement = f'<\\1\\2 style="color: {color} !important;">'
            html_text = re.sub(pattern, replacement, html_text, flags=re.IGNORECASE)
        
        # STRATEGY 4: Handle self-closing and special tags
        # Some tags might be self-closing or have special attributes
        special_patterns = [
            (r'<(br|hr|img)([^>]*)/?>', f'<\\1\\2 style="color: {color} !important;" />'),
        ]
        
        for pattern, replacement in special_patterns:
            html_text = re.sub(pattern, replacement, html_text, flags=re.IGNORECASE)
        
        # STRATEGY 5: Add CSS reset to override any cached styles
        # This adds a style block that should override any existing color definitions
        css_reset = f'<style>* {{ color: {color} !important; }}</style>'
        html_text = css_reset + html_text
        
        logger.debug(f"Color injection complete: {len(html_text)} chars")
        return html_text
        
    def _update_existing_widgets_theme(self):
        """Update theme colors for existing widgets with comprehensive widget recreation strategy.""" 
        logger.debug(f"Updating theme colors for {len(self.content_widgets)} existing widgets")
        
        widgets_updated = 0
        widgets_recreated = 0
        
        # Update all widgets with new theme colors
        for i, (content, message_style, widget_type) in enumerate(self.content_history):
            if i < len(self.content_widgets):
                widget = self.content_widgets[i]
                
                try:
                    # Update code snippet widgets
                    if CODE_WIDGET_AVAILABLE and hasattr(widget, 'set_theme_colors'):
                        widget.set_theme_colors(self.theme_colors)
                        # Force visual update for code widgets
                        widget.update()
                        widget.repaint()
                        widgets_updated += 1
                        logger.debug(f"Updated code widget {i} with new theme colors")
                    
                    # Update QLabel widgets (text content) with AGGRESSIVE approach
                    elif isinstance(widget, QLabel) and widget_type == 'html':
                        color = self._get_message_style_color(message_style)
                        
                        # STRATEGY A: Try HTML injection first (fast path)
                        success = self._try_html_color_injection(widget, content, color, message_style)
                        
                        if success:
                            widgets_updated += 1
                            logger.debug(f"Updated label widget {i} with HTML injection")
                        else:
                            # STRATEGY B: Full widget recreation (nuclear option)
                            success = self._recreate_label_widget(i, content, message_style)
                            if success:
                                widgets_recreated += 1
                                logger.debug(f"Recreated label widget {i} for theme update")
                            else:
                                logger.warning(f"Failed to update widget {i}")
                    
                    # Handle other widget types
                    else:
                        # Apply styling and force refresh for any other widgets
                        if hasattr(widget, 'setStyleSheet'):
                            widget.setStyleSheet(widget.styleSheet())  # Force re-application
                        widget.update()
                        widget.repaint()
                        widgets_updated += 1
                        
                except Exception as e:
                    logger.warning(f"Error updating widget {i}: {e}")
                    # Try widget recreation as fallback
                    if widget_type == 'html' and isinstance(widget, QLabel):
                        try:
                            self._recreate_label_widget(i, content, message_style)
                            widgets_recreated += 1
                        except Exception as e2:
                            logger.error(f"Failed to recreate widget {i}: {e2}")
        
        # Force comprehensive refresh of the entire container
        self._force_complete_visual_refresh()
        
        logger.info(f"Theme update complete: {widgets_updated} updated, {widgets_recreated} recreated")
        
    def _try_html_color_injection(self, widget: QLabel, original_content: str, color: str, message_style: str) -> bool:
        """
        Try to update widget colors using HTML color injection.
        
        Returns:
            True if injection was successful, False if widget recreation is needed
        """
        try:
            # Get current HTML content from widget
            current_html = widget.text()
            
            # If the current HTML doesn't match the original content, something went wrong
            if not current_html or len(current_html) < 10:
                logger.debug("Widget has no/minimal content, trying original content")
                current_html = original_content
            
            # Apply comprehensive HTML color injection
            updated_html = self._inject_theme_color_into_html(current_html, color)
            
            # Apply label styling
            self._apply_label_styling(widget, message_style)
            
            # Clear and re-set HTML to force re-parse
            widget.setText("")  # Clear cache
            widget.setText(updated_html)  # Set new content
            
            # Force Qt style system refresh
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            
            # Force visual updates
            widget.update()
            widget.repaint()
            
            # Verify the update worked by checking if text changed
            new_text = widget.text()
            if len(new_text) > len(current_html) * 0.8:  # Reasonable sanity check
                return True
            else:
                logger.debug("HTML injection may have failed, content size changed significantly")
                return False
                
        except Exception as e:
            logger.debug(f"HTML injection failed: {e}")
            return False
    
    def _recreate_label_widget(self, index: int, content: str, message_style: str) -> bool:
        """
        Completely recreate a QLabel widget with fresh theme colors.
        This is the nuclear option when HTML injection fails.
        
        Returns:
            True if recreation was successful, False otherwise
        """
        try:
            if index >= len(self.content_widgets):
                return False
            
            old_widget = self.content_widgets[index]
            
            # Create new label with current theme colors
            new_label = QLabel()
            new_label.setWordWrap(True)
            new_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse | 
                Qt.TextInteractionFlag.LinksAccessibleByMouse
            )
            new_label.setOpenExternalLinks(False)
            new_label.setAutoFillBackground(False)
            new_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            
            # Apply theme styling BEFORE setting content
            self._apply_label_styling(new_label, message_style)
            
            # Get color and inject into content
            color = self._get_message_style_color(message_style)
            themed_content = self._inject_theme_color_into_html(content, color)
            
            # Set the content
            new_label.setText(themed_content)
            
            # Connect link handling
            new_label.linkActivated.connect(self._handle_link_click)
            
            # Replace in layout
            layout_item = self.content_layout.itemAt(index)
            if layout_item:
                # Insert new widget at the same position
                self.content_layout.insertWidget(index, new_label)
                
                # Remove old widget
                self.content_layout.removeWidget(old_widget)
                old_widget.setParent(None)
                old_widget.deleteLater()
                
                # Update widget list
                self.content_widgets[index] = new_label
                
                logger.debug(f"Successfully recreated widget {index}")
                return True
            else:
                logger.warning(f"Could not find layout item for widget {index}")
                return False
                
        except Exception as e:
            logger.error(f"Widget recreation failed for index {index}: {e}")
            return False
    
    def _force_complete_visual_refresh(self):
        """
        Force a complete visual refresh of the entire widget tree.
        This ensures all theme changes are visible.
        """
        try:
            # Refresh the main scroll area
            self.update()
            self.repaint()
            
            # Refresh the content widget
            if hasattr(self, 'content_widget') and self.content_widget:
                self.content_widget.update()
                self.content_widget.repaint()
            
            # Refresh all child widgets
            for i, widget in enumerate(self.content_widgets):
                if widget and hasattr(widget, 'update'):
                    widget.update()
                    if hasattr(widget, 'repaint'):
                        widget.repaint()
            
            # Schedule final refresh to catch any remaining issues
            QTimer.singleShot(50, self._final_visual_refresh)
            
            logger.debug("Complete visual refresh initiated")
            
        except Exception as e:
            logger.warning(f"Error in complete visual refresh: {e}")
    
    def _final_visual_refresh(self):
        """
        Final visual refresh pass - this is the last step in the theme update process.
        """
        try:
            # One final update pass for everything
            self.update()
            self.repaint()
            
            # Update viewport to ensure scroll area refreshes
            if hasattr(self, 'viewport'):
                self.viewport().update()
            
            logger.debug("Final visual refresh completed - theme update should be fully visible")
            
        except Exception as e:
            logger.debug(f"Final visual refresh error (non-critical): {e}")
    
    def debug_color_analysis(self):
        """Diagnostic method to analyze actual vs expected colors."""
        print("\n=== FONT COLOR DIAGNOSTIC ===")
        print(f"Theme colors available: {bool(self.theme_colors)}")
        
        if not self.theme_colors:
            print("❌ No theme colors available!")
            return
            
        print(f"Expected colors from theme:")
        print(f"  text_primary: {self.theme_colors.get('text_primary', 'MISSING')}")
        print(f"  text_secondary: {self.theme_colors.get('text_secondary', 'MISSING')}")
        print(f"  error: {self.theme_colors.get('error', 'MISSING')}")
        print(f"  info: {self.theme_colors.get('info', 'MISSING')}")
        
        print(f"\nAnalyzing {len(self.content_widgets)} widgets:")
        
        for i, widget in enumerate(self.content_widgets):
            if isinstance(widget, QLabel):
                # Get stylesheet
                stylesheet = widget.styleSheet()
                
                # Extract color from stylesheet
                import re
                color_match = re.search(r'color:\s*([^;!\s]+)', stylesheet)
                actual_color = color_match.group(1) if color_match else "NO COLOR FOUND"
                
                # Get message style from history
                message_style = "unknown"
                if i < len(self.content_history):
                    _, message_style, _ = self.content_history[i]
                
                # Get text preview
                text_preview = widget.text()[:40].replace('\n', ' ')
                
                print(f"  Widget {i}: style={message_style}, actual_color={actual_color}")
                print(f"    Text: '{text_preview}'")
                print(f"    Stylesheet length: {len(stylesheet)} chars")
                
                # Show first 200 chars of stylesheet
                if stylesheet:
                    print(f"    Stylesheet preview: {stylesheet[:200]}...")
                
        print("=== END DIAGNOSTIC ===\n")
    
    def debug_comprehensive_analysis(self):
        """Comprehensive diagnostic method to analyze actual vs expected colors and theme state."""
        print("\n" + "="*60)
        print("   COMPREHENSIVE THEME COLOR DIAGNOSTIC")
        print("="*60)
        
        # Basic theme availability
        print(f"Theme colors available: {bool(self.theme_colors)}")
        print(f"Content widgets: {len(self.content_widgets)}")
        print(f"Content history: {len(self.content_history)}")
        
        if not self.theme_colors:
            print("❌ CRITICAL: No theme colors available!")
            print("   This suggests the theme system isn't working properly.")
            return
        
        # Display current theme colors
        print(f"\n📊 CURRENT THEME COLORS:")
        for key, value in sorted(self.theme_colors.items()):
            print(f"  {key}: {value}")
        
        print(f"\n🎯 EXPECTED MESSAGE STYLE COLORS:")
        for style in ['normal', 'input', 'response', 'system', 'info', 'warning', 'error']:
            color = self._get_message_style_color(style)
            print(f"  {style}: {color}")
        
        print(f"\n🔍 WIDGET-BY-WIDGET ANALYSIS:")
        widgets_with_issues = 0
        
        for i, widget in enumerate(self.content_widgets):
            if isinstance(widget, QLabel):
                # Get history info
                message_style = "unknown"
                content_preview = "N/A"
                widget_type = "unknown"
                
                if i < len(self.content_history):
                    content, message_style, widget_type = self.content_history[i]
                    if isinstance(content, str):
                        content_preview = content[:30].replace('\n', ' ')
                    else:
                        content_preview = str(content)[:30]
                
                # Get expected vs actual colors
                expected_color = self._get_message_style_color(message_style)
                
                # Extract color from stylesheet
                stylesheet = widget.styleSheet()
                import re
                color_matches = re.findall(r'color:\s*([^;!\s}]+)', stylesheet)
                stylesheet_colors = color_matches if color_matches else ["NO COLOR"]
                
                # Extract color from HTML content
                widget_html = widget.text()
                html_color_matches = re.findall(r'color:\s*([^;!"\']+)', widget_html)
                html_colors = html_color_matches if html_color_matches else ["NO COLOR"]
                
                # Check for issues
                has_issues = (
                    expected_color not in stylesheet_colors and
                    expected_color not in html_colors and
                    not any(color.replace(' ', '').replace('!important', '') == expected_color.replace(' ', '') for color in stylesheet_colors + html_colors)
                )
                
                if has_issues:
                    widgets_with_issues += 1
                    status = "❌ ISSUE"
                else:
                    status = "✅ OK"
                
                print(f"\n  Widget {i} [{widget_type}] - {status}")
                print(f"    Message style: {message_style}")
                print(f"    Expected color: {expected_color}")
                print(f"    Stylesheet colors: {stylesheet_colors}")
                print(f"    HTML colors: {html_colors}")
                print(f"    Content preview: '{content_preview}...'")
                print(f"    HTML size: {len(widget_html)} chars")
                
                if has_issues:
                    print(f"    ⚠️  Color mismatch detected!")
                    # Show first part of HTML for debugging
                    html_preview = widget_html[:150].replace('\n', ' ')
                    print(f"    HTML preview: {html_preview}...")
            
            elif hasattr(widget, 'set_theme_colors'):
                print(f"\n  Widget {i} [CODE] - ✅ Code widget (has set_theme_colors)")
            else:
                print(f"\n  Widget {i} [OTHER] - ℹ️ {type(widget).__name__}")
        
        # Summary
        print(f"\n" + "="*60)
        print(f"   DIAGNOSTIC SUMMARY")
        print("="*60)
        print(f"Total widgets: {len(self.content_widgets)}")
        print(f"QLabel widgets: {sum(1 for w in self.content_widgets if isinstance(w, QLabel))}")
        print(f"Widgets with color issues: {widgets_with_issues}")
        
        if widgets_with_issues == 0:
            print("🎉 All widgets appear to have correct theme colors!")
        else:
            print(f"⚠️  {widgets_with_issues} widgets may have color issues.")
            print("   Consider running debug_fix_widget_colors() to attempt fixes.")
        
        print("="*60 + "\n")
    
    def debug_fix_widget_colors(self):
        """Debug method to forcefully fix widget colors by re-applying theme."""
        print("\n🔧 FORCING THEME COLOR FIXES...")
        
        if not self.theme_colors:
            print("❌ No theme colors available - cannot fix.")
            return
        
        original_log_level = logger.level
        logger.setLevel(logging.DEBUG)  # Enable debug logging
        
        try:
            # Force comprehensive theme update
            self._update_existing_widgets_theme()
            print("✅ Theme color fix completed.")
            print("   Run debug_comprehensive_analysis() again to verify fixes.")
        except Exception as e:
            print(f"❌ Error during theme fix: {e}")
        finally:
            logger.setLevel(original_log_level)  # Restore original log level
    
    def debug_widget_recreation_test(self, widget_index: int = 0):
        """Debug method to test widget recreation on a specific widget."""
        print(f"\n🧪 TESTING WIDGET RECREATION FOR INDEX {widget_index}")
        
        if widget_index >= len(self.content_widgets) or widget_index >= len(self.content_history):
            print(f"❌ Invalid widget index {widget_index}")
            return
        
        content, message_style, widget_type = self.content_history[widget_index]
        widget = self.content_widgets[widget_index]
        
        print(f"Widget type: {type(widget).__name__}")
        print(f"Content type: {widget_type}")
        print(f"Message style: {message_style}")
        
        if isinstance(widget, QLabel) and widget_type == 'html':
            print("🔄 Attempting widget recreation...")
            success = self._recreate_label_widget(widget_index, content, message_style)
            if success:
                print("✅ Widget recreation successful!")
            else:
                print("❌ Widget recreation failed!")
        else:
            print("ℹ️ Widget recreation only supports QLabel HTML widgets.")
    
    
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
        label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
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
                    text_label.setTextFormat(Qt.TextFormat.RichText)
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
            label.setTextFormat(Qt.TextFormat.RichText)
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
                # IMPORTANT: Do NOT remove leading spaces - they are indentation!
                code_content = re.sub(r'\n\s*\n', '\n', code_content)  # Remove extra blank lines only
                
                logger.debug(f"Cleaned code content: {len(code_content)} chars, first 50: {repr(code_content[:50])}")
                
                # Only strip trailing whitespace, preserve leading indentation
                code_content = code_content.rstrip()
                
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
        # Only use smart fallback if text_primary is actually missing
        bg_color = self.theme_colors.get('bg_primary', self.theme_colors.get('background_primary', '#000000'))
        
        # Use theme's text_primary directly if it exists
        text_primary = self.theme_colors.get('text_primary')
        if not text_primary:
            # Only calculate fallback if text_primary is missing
            text_primary = self._get_smart_text_fallback(bg_color)
            logger.warning(f"text_primary missing from theme_colors, using fallback: {text_primary}")
        
        style_colors = {
            'normal': text_primary,
            'input': self.theme_colors.get('primary', text_primary),  # Use primary color or text_primary
            'response': text_primary,  # Use text_primary for AI responses
            'system': self.theme_colors.get('text_secondary', text_primary),  # Use theme's text_secondary
            'info': self.theme_colors.get('info', text_primary),  # Use theme's info color
            'warning': self.theme_colors.get('warning', text_primary),  # Use theme's warning color
            'error': self.theme_colors.get('error', text_primary),  # Use theme's error color
            'divider': self.theme_colors.get('text_secondary', text_primary),  # Use theme's text_secondary
        }
        
        color = style_colors.get(message_style, text_primary)
        
        # Get text size setting for consistent font sizes
        from ...infrastructure.storage.settings_manager import settings
        text_size_percent = settings.get('ui.text_size', 100)
        base_font_size = int(14 * text_size_percent / 100)  # Base 14px scaled
        
        # Build more specific stylesheet for PyQt6 with higher precedence
        stylesheet = f"""
            QLabel {{
                color: {color} !important;
                background-color: transparent !important;
                background: none !important;
                padding: 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: {base_font_size}px;
                line-height: 1.5;
            }}
            QLabel a {{
                color: {self.theme_colors.get('info', text_primary)} !important;
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
                color: {color} !important;
            }}
            QLabel div {{
                background: none !important;
                background-color: transparent !important;
                color: {color} !important;
            }}
            QLabel span {{
                background: none !important;
                background-color: transparent !important;
                color: {color} !important;
            }}
            QLabel h1 {{
                font-size: {int(base_font_size * 2.0)}px;
                font-weight: bold;
                margin: 0.5em 0;
                color: {color} !important;
            }}
            QLabel h2 {{
                font-size: {int(base_font_size * 1.7)}px;
                font-weight: bold;
                margin: 0.4em 0;
                color: {color} !important;
            }}
            QLabel h3 {{
                font-size: {int(base_font_size * 1.4)}px;
                font-weight: bold;
                margin: 0.3em 0;
                color: {color} !important;
            }}
            QLabel h4 {{
                font-size: {int(base_font_size * 1.2)}px;
                font-weight: bold;
                margin: 0.2em 0;
                color: {color} !important;
            }}
            QLabel h5 {{
                font-size: {int(base_font_size * 1.1)}px;
                font-weight: bold;
                margin: 0.2em 0;
                color: {color} !important;
            }}
            QLabel h6 {{
                font-size: {base_font_size}px;
                font-weight: bold;
                margin: 0.2em 0;
                color: {color} !important;
            }}
        """
        
        # Apply stylesheet to the label
        label.setStyleSheet(stylesheet)
        
        # ADDITIONAL FIX: Force immediate stylesheet refresh for PyQt6
        # This ensures the new styles take effect immediately
        label.style().unpolish(label)
        label.style().polish(label)
        
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
            
        # Use theme colors if available, with smart defaults
        if self.theme_colors:
            colors = self.theme_colors
        else:
            # Smart fallback colors - assume dark theme for default
            colors = {
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
            separator.setStyleSheet(f"background-color: {self.theme_colors.get('border', self.theme_colors.get('text_secondary', '#666666'))};")
        self.content_layout.addWidget(separator)
        self.content_widgets.append(separator)
        
    def clear(self):
        """Clear all content."""
        import logging
        logger = logging.getLogger(__name__)

        widget_count = len(self.content_widgets)
        history_count = len(self.content_history)

        logger.debug(f"🗑️  Clearing REPL display: {widget_count} widgets, {history_count} history items")

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

        logger.debug(f"✅ REPL display cleared completely")
                
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
                    color: {self.theme_colors.get('text_secondary', self.theme_colors.get('text_primary', '#cccccc'))};
                    font-style: italic;
                    padding: 4px;
                """)
            self.content_layout.insertWidget(0, notice)

    # DEAD CODE REMOVED: save_content_state() and restore_content_state()
    # These methods were used for the old save/restore tab switching mechanism.
    # Now each tab owns its own MixedContentDisplay widget that persists, so save/restore is not needed.