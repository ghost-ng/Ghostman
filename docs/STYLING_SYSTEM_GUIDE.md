# Ghostman Styling System - Complete Guide

The definitive guide to the Ghostman application's styling system, covering architecture, implementation, and best practices for developers and theme creators.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Theme Switching Architecture (Enhanced)](#theme-switching-architecture)
4. [Advanced Color Management](#advanced-color-management)
5. [Multi-Strategy HTML Color Injection](#multi-strategy-html-color-injection)
6. [Self-Healing Theme System](#self-healing-theme-system)
7. [Debugging Tools](#debugging-tools)
8. [Theme Manager Enhancements](#theme-manager-enhancements)
9. [39 JSON-Based Themes](#39-json-based-themes)
10. [Color System](#color-system)
11. [Button Styling](#button-styling)
12. [Component Integration](#component-integration)
13. [REPL Area Styling](#repl-area-styling)
14. [Performance Optimization](#performance-optimization)
15. [Developer Integration Guide](#developer-integration-guide)
16. [API Reference](#api-reference)
17. [Best Practices](#best-practices)
18. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 5-Minute Theme Integration

For developers adding theme support to a new widget:

```python
from PyQt6.QtWidgets import QWidget
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.ui.themes.style_templates import ButtonStyleManager

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Get theme manager and connect signals
        self.theme_manager = get_theme_manager()
        self.theme_manager.register_widget(self, "_on_theme_changed")
        
        # Apply current theme
        self._on_theme_changed(self.theme_manager.current_theme)
    
    def _on_theme_changed(self, color_system):
        # For buttons: ALWAYS use ButtonStyleManager
        ButtonStyleManager.apply_unified_button_style(
            my_button, color_system, "push", "medium", "normal"
        )
        
        # For other elements: Use ColorSystem variables
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color_system.background_secondary};
                color: {color_system.text_primary};
            }}
        """)
```

---

## System Architecture

### Enhanced Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Application Layer                        │
├─────────────────────────────────────────────────────────┤
│              Enhanced Theme Manager                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │Widget Reg.  │ │  Debounce   │ │39 JSON      │        │
│  │& Updates    │ │  System     │ │Themes       │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│          Multi-Strategy Theme Switching Layer           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │5-Strategy   │ │Widget       │ │Self-Healing │        │
│  │HTML Inject. │ │Recreation   │ │Recovery     │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│              Advanced Color Management                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │Smart Text   │ │Message Style│ │Luminance    │        │
│  │Fallbacks    │ │Color Mapping│ │Detection    │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│                 Style System Layer                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ ColorSystem │ │ButtonStyle  │ │StyleTemplate│        │
│  │  (24 vars)  │ │  Manager    │ │   Library   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│          Enhanced Component Layer                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │MixedContent │ │   REPL      │ │Theme-aware  │        │
│  │  Display    │ │  Widget     │ │ Widgets     │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Core Design Principles (Updated)

- **Multi-Strategy Theme Switching**: 5-step HTML color injection with comprehensive fallback mechanisms
- **Self-Healing System**: Automatic recovery from PyQt6 HTML caching and theme switching issues
- **Widget Recreation Capability**: Nuclear option for stubborn theme update cases
- **Debounced Theme Switching**: Performance-optimized theme changes with 200ms debounce
- **Advanced Debugging Tools**: Comprehensive diagnostic and repair capabilities
- **39 JSON Theme Collection**: Rich variety of pre-built themes with consistent structure
- **Smart Color Fallbacks**: Luminance-based text color selection for accessibility
- **Message Style Mapping**: Enhanced color mapping for different message types

---

## Theme Switching Architecture

### Critical Issue Resolved: Existing Content Color Updates

**Problem**: Previously, when users switched themes, existing conversation content retained old colors despite new theme activation.

**Solution**: Comprehensive multi-strategy theme switching system with self-healing mechanisms.

### Multi-Strategy HTML Color Injection System

The theme switching system now uses a robust 5-step approach to overcome PyQt6's HTML caching issues:

#### Strategy 1: Cleanup Phase
```python
cleanup_patterns = [
    r'color:\s*[^;}"\']+[;]?',      # Remove CSS color properties
    r'style="[^"]*color[^"]*[;"]',  # Remove inline color styles
    r'text="[^"]*"',                # Remove HTML text attributes
    r'color="[^"]*"',               # Remove direct color attributes
]
```

#### Strategy 2: Container Wrapping
```python
html_text = f'''<div style="color: {color} !important; 
                font-family: inherit; font-size: inherit;">
                {html_text}
                </div>'''
```

#### Strategy 3: Systematic Tag Injection
```python
all_text_tags = ['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                 'a', 'strong', 'em', 'b', 'i', 'u', 'li', 'ul', 'ol', 
                 'blockquote', 'code', 'pre']

for tag in all_text_tags:
    pattern = f'<({tag})(?![^>]*style="[^"]*color[^"]*")([^>]*)>'
    replacement = f'<\\1\\2 style="color: {color} !important;">'
    html_text = re.sub(pattern, replacement, html_text, flags=re.IGNORECASE)
```

#### Strategy 4: Special Element Handling
```python
special_patterns = [
    (r'<(br|hr|img)([^>]*)/?>', f'<\\1\\2 style="color: {color} !important;" />'),
]
```

#### Strategy 5: CSS Reset Override
```python
css_reset = f'<style>* {{ color: {color} !important; }}</style>'
html_text = css_reset + html_text
```

### Implementation in MixedContentDisplay

The `_inject_theme_color_into_html()` method implements all five strategies:

```python
def _inject_theme_color_into_html(self, html_text: str, color: str) -> str:
    """
    Comprehensive HTML color injection that bypasses PyQt6 QLabel caching issues.
    
    This method aggressively modifies HTML content to ensure theme colors are applied
    by using multiple strategies to overcome PyQt6's HTML rendering cache.
    """
    # ... Strategy 1: Cleanup
    # ... Strategy 2: Container wrapping  
    # ... Strategy 3: Tag injection
    # ... Strategy 4: Special elements
    # ... Strategy 5: CSS reset
    
    return html_text
```

---

## Self-Healing Theme System

### Dual-Approach Update System

The system provides both fast-path HTML injection and nuclear widget recreation:

#### Fast Path: HTML Injection
```python
def _try_html_color_injection(self, widget: QLabel, original_content: str, 
                             color: str, message_style: str) -> bool:
    try:
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
        
        return True
    except Exception:
        return False
```

#### Nuclear Option: Widget Recreation
```python
def _recreate_label_widget(self, index: int, content: str, message_style: str) -> bool:
    """
    Completely recreate a QLabel widget with fresh theme colors.
    This is the nuclear option when HTML injection fails.
    """
    try:
        old_widget = self.content_widgets[index]
        
        # Create new label with current theme colors
        new_label = QLabel()
        # ... configuration ...
        
        # Apply theme styling BEFORE setting content
        self._apply_label_styling(new_label, message_style)
        
        # Get color and inject into content
        color = self._get_message_style_color(message_style)
        themed_content = self._inject_theme_color_into_html(content, color)
        
        # Replace in layout
        self.content_layout.insertWidget(index, new_label)
        self.content_layout.removeWidget(old_widget)
        old_widget.deleteLater()
        
        # Update widget list
        self.content_widgets[index] = new_label
        
        return True
    except Exception:
        return False
```

### Comprehensive Recovery System

The update system includes automatic fallback with detailed logging:

```python
def _update_existing_widgets_theme(self):
    """Update theme colors for existing widgets with comprehensive recovery."""
    widgets_updated = 0
    widgets_recreated = 0
    
    for i, (content, message_style, widget_type) in enumerate(self.content_history):
        widget = self.content_widgets[i]
        color = self._get_message_style_color(message_style)
        
        try:
            # Try fast HTML injection first
            if self._try_html_color_injection(widget, content, color, message_style):
                widgets_updated += 1
            else:
                # Fall back to widget recreation
                if self._recreate_label_widget(i, content, message_style):
                    widgets_recreated += 1
        except Exception:
            # Final fallback attempt
            try:
                self._recreate_label_widget(i, content, message_style)
                widgets_recreated += 1
            except Exception as e2:
                logger.error(f"All recovery methods failed: {e2}")
    
    logger.info(f"Theme update: {widgets_updated} updated, {widgets_recreated} recreated")
```

---

## Advanced Color Management

### Smart Text Color Fallback System

The system includes intelligent color fallback based on background luminance:

```python
def _get_smart_text_fallback(self, bg_color: str) -> str:
    """Get smart text color fallback based on background brightness."""
    try:
        # Remove # if present
        hex_color = bg_color.lstrip('#')
        
        # Convert hex to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
        
        # Calculate luminance (0.299*R + 0.587*G + 0.114*B)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Return appropriate contrast
        if luminance > 0.5:
            return '#2d2d2d'  # Dark text for light background
        else:
            return '#f0f0f0'  # Light text for dark background
    except:
        return '#2d2d2d'  # Safe fallback
```

### Enhanced Message Style Color Mapping

Comprehensive color mapping with intelligent fallbacks:

```python
def _get_message_style_color(self, message_style: str) -> str:
    """Get the appropriate color for a message style from the current theme."""
    if not self.theme_colors:
        return '#ffffff'  # Fallback if no theme
    
    # Get base colors with fallback handling
    bg_color = self.theme_colors.get('bg_primary', 
                                   self.theme_colors.get('background_primary', '#000000'))
    text_primary = self.theme_colors.get('text_primary')
    
    if not text_primary:
        text_primary = self._get_smart_text_fallback(bg_color)
    
    # Enhanced style-to-color mapping
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
```

---

## Debugging Tools

### Comprehensive Diagnostic System

The system now includes advanced debugging tools for theme troubleshooting:

#### Basic Color Analysis
```python
widget.debug_color_analysis()
```

**Output**: Basic diagnostic showing theme availability, expected colors, and stylesheet analysis.

#### Comprehensive Analysis
```python
widget.debug_comprehensive_analysis()
```

**Sample Output**:
```
============================================================
   COMPREHENSIVE THEME COLOR DIAGNOSTIC
============================================================
Theme colors available: True
Content widgets: 12
Content history: 12

📊 CURRENT THEME COLORS:
  background_primary: #1a1a1a
  background_secondary: #2d2d2d
  text_primary: #ffffff
  text_secondary: #cccccc
  primary: #4CAF50
  ...

🎯 EXPECTED MESSAGE STYLE COLORS:
  normal: #ffffff
  input: #4CAF50
  response: #ffffff
  system: #cccccc
  error: #f44336
  ...

🔍 WIDGET-BY-WIDGET ANALYSIS:

  Widget 0 [html] - ✅ OK
    Message style: normal
    Expected color: #ffffff
    Stylesheet colors: ['#ffffff']
    HTML colors: ['#ffffff']
    Content preview: 'Hello, this is a test message...'

  Widget 5 [html] - ❌ ISSUE
    Message style: error
    Expected color: #f44336
    Stylesheet colors: ['#ffffff']
    HTML colors: ['NO COLOR']
    Content preview: 'Error: Unable to connect...'
    ⚠️  Color mismatch detected!

============================================================
   DIAGNOSTIC SUMMARY
============================================================
Total widgets: 12
QLabel widgets: 10
Widgets with color issues: 1
⚠️  1 widgets may have color issues.
   Consider running debug_fix_widget_colors() to attempt fixes.
============================================================
```

#### Automated Color Fixes
```python
widget.debug_fix_widget_colors()
```

**Features**:
- Forces comprehensive theme update using all recovery strategies
- Enables debug logging during the fix process
- Provides status feedback on repair success

#### Widget Recreation Testing
```python
widget.debug_widget_recreation_test(widget_index=0)
```

**Features**:
- Tests widget recreation capabilities on specific widgets
- Analyzes widget structure and compatibility
- Reports recreation success/failure with detailed diagnostics

---

## Theme Manager Enhancements

### Debounce System for Performance

The theme manager now includes improved debouncing to prevent rapid theme switching issues:

```python
def set_theme(self, name: str) -> bool:
    # Debounce rapid theme changes
    if self._is_switching_theme:
        if (self._theme_switch_debounce_timer is not None and 
            self._theme_switch_debounce_timer.isActive()):
            logger.debug(f"Theme switch debounced: {name}")
            return False
        else:
            # Timer finished but flag wasn't reset - reset it now
            logger.debug(f"Resetting stuck debounce flag for theme: {name}")
            self._is_switching_theme = False
    
    # Set debounce flag
    self._is_switching_theme = True
    
    # ... theme switching logic ...
    
    # Set up debounce timer
    self._theme_switch_debounce_timer = QTimer()
    self._theme_switch_debounce_timer.setSingleShot(True)
    self._theme_switch_debounce_timer.timeout.connect(self._reset_theme_switching_flag)
    self._theme_switch_debounce_timer.start(200)  # 200ms debounce
```

### Widget Registration System

Enhanced widget registration with multiple update methods:

```python
def register_widget(self, widget, update_method: str = "_on_theme_changed") -> bool:
    """Register a widget to receive theme updates."""
    try:
        widget_ref = weakref.ref(widget, self._cleanup_widget_reference)
        self._registered_widgets.add(widget_ref)
        self._widget_update_methods[widget_ref] = update_method
        
        # Apply current theme immediately
        if self._current_theme is not None:
            self._apply_theme_to_widget(widget, update_method)
        
        return True
    except Exception as e:
        logger.error(f"Failed to register widget: {e}")
        return False
```

### Performance-Optimized Color Caching

```python
def _get_cached_theme_color_dict(self) -> Dict[str, str]:
    """Get cached theme color dictionary for performance optimization."""
    if self._theme_color_dict_cache is None:
        # Create and cache the color dictionary
        color_dict = self._current_theme.to_dict() if self._current_theme else {}
        
        # Add legacy key mappings for backward compatibility
        if self._current_theme:
            legacy_mappings = {
                'bg_primary': color_dict.get('background_primary'),
                'bg_secondary': color_dict.get('background_secondary'), 
                'bg_tertiary': color_dict.get('background_tertiary'),
                'border': color_dict.get('border_subtle')
            }
            # Add without overwriting existing keys
            for key, value in legacy_mappings.items():
                if key not in color_dict and value is not None:
                    color_dict[key] = value
        
        self._theme_color_dict_cache = color_dict
    
    return self._theme_color_dict_cache
```

---

## 39 JSON-Based Themes

### Theme Collection Overview

The system includes 39 professionally crafted JSON themes organized in `/ghostman/src/ui/themes/json/`:

#### Popular Themes
- **openai_like**: ChatGPT-inspired clean design
- **dracula**: Popular dark theme with purple accents
- **solarized_dark** / **solarized_light**: Professional color schemes
- **arctic_white**: Clean light theme for brightness
- **cyberpunk**: Futuristic neon aesthetic

#### Fantasy & Fictional Themes
- **jedi** / **sith**: Star Wars inspired themes
- **republic** / **empire**: More Star Wars variants
- **gryffindor** / **slytherin** / **hufflepuff** / **ravenclaw**: Harry Potter houses

#### Nature & Color Themes
- **ocean** / **ocean_deep**: Blue water themes
- **forest** / **forest_green**: Green nature themes
- **sunset_orange** / **sunburst**: Warm orange themes
- **earth_tones**: Natural brown and beige
- **midnight_blue**: Deep blue night theme

#### Unique Aesthetics
- **steampunk**: Victorian-industrial design
- **fireswamp**: Mysterious red-black theme
- **birthday_cake**: Playful colorful theme
- **mintly**: Fresh mint green aesthetic

### Theme Structure

Each JSON theme follows a consistent structure:

```json
{
  "name": "theme_name",
  "display_name": "Theme Display Name",
  "description": "Theme description",
  "author": "Theme Creator",
  "version": "1.0.0",
  "colors": {
    "primary": "#4CAF50",
    "primary_hover": "#45A045",
    "secondary": "#2196F3",
    "secondary_hover": "#1976D2",
    "background_primary": "#1a1a1a",
    "background_secondary": "#2d2d2d",
    "background_tertiary": "#3a3a3a",
    "background_overlay": "#000000cc",
    "text_primary": "#ffffff",
    "text_secondary": "#cccccc",
    "text_tertiary": "#888888",
    "text_disabled": "#555555",
    "interactive_normal": "#4a4a4a",
    "interactive_hover": "#5a5a5a",
    "interactive_active": "#6a6a6a",
    "interactive_disabled": "#2a2a2a",
    "status_success": "#4CAF50",
    "status_warning": "#FF9800",
    "status_error": "#F44336",
    "status_info": "#2196F3",
    "border_primary": "#4a4a4a",
    "border_secondary": "#3a3a3a",
    "border_focus": "#4CAF50",
    "separator": "#2a2a2a"
  }
}
```

---

## Color System

### 24-Variable Semantic Color System

The `ColorSystem` provides 24 semantic color variables organized into logical groups:

#### Complete Variable Reference

| Variable | Category | Purpose | Example Usage |
|----------|----------|---------|---------------|
| `primary` | Brand | Main brand color | Primary buttons, focus rings |
| `primary_hover` | Brand | Primary hover state | Button hover effects |
| `secondary` | Brand | Secondary accent | Selections, links |
| `secondary_hover` | Brand | Secondary hover | Link hover effects |
| `background_primary` | Background | Main app background | Window background |
| `background_secondary` | Background | Panel backgrounds | Dialog backgrounds |
| `background_tertiary` | Background | Elevated surfaces | Input fields, cards |
| `background_overlay` | Background | Modal overlays | Dialog backdrops |
| `text_primary` | Text | High contrast text | Main content, headings |
| `text_secondary` | Text | Medium contrast text | Labels, descriptions |
| `text_tertiary` | Text | Low contrast text | Placeholders, hints |
| `text_disabled` | Text | Disabled text | Inactive elements |
| `interactive_normal` | Interactive | Default button state | Button backgrounds |
| `interactive_hover` | Interactive | Hover feedback | Hover states |
| `interactive_active` | Interactive | Pressed/active state | Click feedback |
| `interactive_disabled` | Interactive | Disabled controls | Disabled buttons |
| `status_success` | Status | Success messages | Confirmation dialogs |
| `status_warning` | Status | Warning messages | Caution alerts |
| `status_error` | Status | Error messages | Error dialogs |
| `status_info` | Status | Information messages | Info notifications |
| `border_primary` | Border | Main borders | Input borders, panels |
| `border_secondary` | Border | Subtle borders | Internal dividers |
| `border_focus` | Border | Focus indicators | Keyboard focus |
| `separator` | Border | Dividers | Menu separators |

### Enhanced Accessibility Features

The ColorSystem includes comprehensive WCAG 2.1 AA compliance checking with improved contrast validation:

```python
# Validate theme for accessibility
is_valid, issues = colors.validate()
if not is_valid:
    print("Accessibility issues:", issues)

# Calculate contrast ratios
contrast = colors._calculate_contrast_ratio("#ffffff", "#000000")
print(f"Contrast ratio: {contrast:.2f}")  # Should be > 4.5 for AA

# Enhanced validation includes:
# - Text readability on all background combinations
# - Status color visibility against backgrounds
# - Color differentiation for accessibility
# - Similar color detection to prevent confusion
```

---

## Performance Optimization

### Multi-Stage Visual Refresh

The system uses staged refresh for optimal visual updates:

```python
def _force_complete_visual_refresh(self):
    """Force a complete visual refresh of the entire widget tree."""
    # Stage 1: Refresh main containers
    self.update()
    self.repaint()
    
    # Stage 2: Refresh content widget
    if hasattr(self, 'content_widget') and self.content_widget:
        self.content_widget.update()
        self.content_widget.repaint()
    
    # Stage 3: Refresh all child widgets
    for widget in self.content_widgets:
        if widget and hasattr(widget, 'update'):
            widget.update()
            if hasattr(widget, 'repaint'):
                widget.repaint()
    
    # Stage 4: Schedule final refresh
    QTimer.singleShot(50, self._final_visual_refresh)
```

### Optimized Theme Application

Performance improvements in theme manager:

```python
def _apply_theme_to_all_widgets(self):
    """Apply current theme to all registered widgets with cleanup."""
    dead_refs = set()
    
    # Performance: Create copy to avoid runtime errors
    widgets_to_update = list(self._registered_widgets)
    
    for widget_ref in widgets_to_update:
        widget = widget_ref()
        if widget is None:
            dead_refs.add(widget_ref)
            continue
            
        update_method = self._widget_update_methods.get(widget_ref, "_on_theme_changed")
        self._apply_theme_to_widget(widget, update_method)
    
    # Cleanup dead references for memory optimization
    for dead_ref in dead_refs:
        self._registered_widgets.discard(dead_ref)
        self._widget_update_methods.pop(dead_ref, None)
```

---

## Developer Integration Guide

### Enhanced Integration Checklist

When integrating a new component with the enhanced theme system:

- [ ] Import theme manager and register widget
- [ ] Implement `_on_theme_changed(color_system)` method
- [ ] Use appropriate ColorSystem variables (not hardcoded colors)
- [ ] Apply ButtonStyleManager for ALL buttons
- [ ] Test with multiple themes from the 39-theme collection
- [ ] Verify advanced color management for content areas
- [ ] **NEW**: Implement debugging tool integration if widget displays dynamic content
- [ ] **NEW**: Test self-healing mechanisms work correctly with theme switching
- [ ] **NEW**: Verify widget supports both HTML injection and recreation approaches
- [ ] Handle widget registration cleanup in `closeEvent()` or destructor
- [ ] Test performance with rapid theme switching

### Advanced Integration for Content Widgets

For widgets that display dynamic content (like MixedContentDisplay):

```python
class ContentWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_advanced_theme_support()
    
    def _setup_advanced_theme_support(self):
        """Setup advanced theme support for content areas."""
        # Register with theme manager
        self.theme_manager = get_theme_manager()
        self.theme_manager.register_widget(self, "_on_theme_changed")
        
        # Enable comprehensive debugging
        self._enable_debug_support()
    
    def _on_theme_changed(self, color_system):
        """Enhanced theme update with content preservation."""
        try:
            # Standard theme application
            self._apply_standard_theme(color_system)
            
            # Advanced content color management
            if hasattr(self, '_update_existing_content_theme'):
                self._update_existing_content_theme(color_system)
            
            # Verify theme application in debug mode
            if hasattr(self, 'debug_comprehensive_analysis') and logger.level <= logging.DEBUG:
                self.debug_comprehensive_analysis()
        
        except Exception as e:
            logger.error(f"Advanced theme update failed: {e}")
            # Fallback to basic theme application
            self._apply_basic_theme_fallback(color_system)
```

---

## API Reference (Updated)

### MixedContentDisplay (Enhanced)

#### New Debug Methods
- `debug_color_analysis()`: Basic color diagnostic with theme availability check
- `debug_comprehensive_analysis()`: Detailed theme state analysis with widget-by-widget breakdown
- `debug_fix_widget_colors()`: Automatic theme color repair using all recovery strategies
- `debug_widget_recreation_test(index)`: Test widget recreation capabilities

#### Enhanced Theme Methods
- `set_theme_colors(colors)`: Now includes multi-strategy updating with fallback handling
- `_update_existing_widgets_theme()`: Comprehensive widget updating with recreation fallback
- `_inject_theme_color_into_html(html, color)`: 5-strategy HTML injection system
- `_recreate_label_widget(index, content, style)`: Nuclear widget recreation option
- `_get_smart_text_fallback(bg_color)`: Luminance-based text color selection

### ThemeManager (Enhanced)

#### New Properties
- `_is_switching_theme`: Debounce flag preventing rapid theme changes
- `_theme_switch_debounce_timer`: Timer for 200ms theme switching debounce
- `_theme_color_dict_cache`: Performance-optimized color dictionary cache

#### Enhanced Methods
- `set_theme(name)`: Now includes debouncing, stuck flag detection, and comprehensive error handling
- `_reset_theme_switching_flag()`: Reset debounce state and global switching flags
- `register_widget(widget, method)`: Enhanced widget registration with immediate theme application
- `_get_cached_theme_color_dict()`: Performance-optimized cached color access

---

## Best Practices (Updated)

### 1. Theme Switching Best Practices

**✅ DO:**
```python
# Implement debugging support for content widgets
if hasattr(widget, 'debug_comprehensive_analysis'):
    widget.debug_comprehensive_analysis()

# Use multi-strategy theme updating
widget.set_theme_colors(enhanced_colors_with_fallbacks)

# Register widgets properly
theme_manager.register_widget(widget, "_on_theme_changed")

# Test with multiple themes from the 39-theme collection
for theme_name in ["dracula", "openai_like", "arctic_white", "cyberpunk"]:
    theme_manager.set_theme(theme_name)
```

**❌ DON'T:**
```python
# Don't rely on single-strategy theme updates
widget.setText(html_with_hardcoded_colors)  # Fragile!

# Don't connect signals directly - use registration
theme_manager.theme_changed.connect(widget.update_theme)  # Causes double updates

# Don't ignore debouncing
for theme in themes: theme_manager.set_theme(theme)  # Too rapid!
```

### 2. Content Area Color Management

```python
def _update_content_colors_safely(self, colors):
    """Safe content color updating with comprehensive fallback."""
    try:
        # Try advanced multi-strategy update
        self._update_existing_widgets_theme()
    except Exception as e:
        logger.warning(f"Advanced update failed: {e}")
        # Fallback to full content recreation
        self._rerender_all_content()
    
    # Verify update success
    if hasattr(self, 'debug_comprehensive_analysis'):
        self.debug_comprehensive_analysis()
```

### 3. Debug Integration for Development

```python
# Enable debugging in development builds
if logger.level <= logging.DEBUG:
    content_widget.debug_comprehensive_analysis()

# Test theme switching robustness
def test_theme_switching_robustness(widget):
    """Test widget's theme switching capabilities."""
    theme_names = ["dracula", "openai_like", "arctic_white", "solarized_dark"]
    
    for theme_name in theme_names:
        theme_manager.set_theme(theme_name)
        QApplication.processEvents()  # Allow theme to apply
        
        # Check for issues
        if hasattr(widget, 'debug_fix_widget_colors'):
            widget.debug_fix_widget_colors()
            
        # Verify theme applied correctly
        if hasattr(widget, 'debug_comprehensive_analysis'):
            widget.debug_comprehensive_analysis()
```

---

## Troubleshooting (Enhanced)

### 1. Theme Colors Not Updating in Existing Content

**Problem**: New theme colors don't apply to previously rendered content
**Cause**: PyQt6 HTML caching prevents color updates
**Solution**: Use the comprehensive multi-strategy update system

```python
# Diagnosis
if hasattr(content_widget, 'debug_comprehensive_analysis'):
    content_widget.debug_comprehensive_analysis()

# Automatic fix
if hasattr(content_widget, 'debug_fix_widget_colors'):
    content_widget.debug_fix_widget_colors()

# Manual fix for custom widgets
def force_theme_update(widget, colors):
    """Force comprehensive theme update."""
    try:
        widget._update_existing_widgets_theme()
    except AttributeError:
        # Widget doesn't support advanced updating
        widget._on_theme_changed(colors)
```

### 2. PyQt6 HTML Caching Issues

**Problem**: HTML content caches colors despite stylesheet changes
**Cause**: PyQt6 optimizations cache rendered HTML content
**Solution**: Multi-strategy HTML injection with widget recreation fallback

```python
# Check if widget supports advanced updating
if hasattr(widget, '_inject_theme_color_into_html'):
    # Widget has multi-strategy support
    updated_html = widget._inject_theme_color_into_html(content, new_color)
    widget.setText("")  # Clear cache
    widget.setText(updated_html)  # Apply with new colors
    
    # Force style refresh
    widget.style().unpolish(widget)
    widget.style().polish(widget)
```

### 3. Widget Recreation Failures

**Problem**: Some widgets fail to recreate during theme switching
**Solution**: Test and verify recreation capabilities

```python
# Test widget recreation support
def test_widget_recreation(content_widget, index=0):
    """Test if widget supports recreation."""
    if hasattr(content_widget, 'debug_widget_recreation_test'):
        success = content_widget.debug_widget_recreation_test(index)
        if not success:
            logger.warning(f"Widget recreation failed for index {index}")
            # Consider alternative theme update approach
```

### 4. Theme Switching Performance Issues

**Problem**: Slow theme switching with many widgets
**Cause**: Too many widgets updating simultaneously
**Solution**: Use debouncing and performance monitoring

```python
# Monitor theme switch performance
def monitor_theme_switch_performance(theme_manager, theme_name):
    """Monitor theme switching performance."""
    start_time = time.time()
    success = theme_manager.set_theme(theme_name)
    end_time = time.time()
    
    duration = end_time - start_time
    if duration > 0.5:  # More than 500ms
        logger.warning(f"Slow theme switch to {theme_name}: {duration:.2f}s")
        # Consider reducing registered widgets or optimizing update methods
    
    return success, duration
```

### 5. Debugging Theme Issues

**Problem**: Theme not applying correctly to specific components
**Solution**: Use comprehensive diagnostic tools

```python
# Full diagnostic workflow
def diagnose_theme_issues(widget):
    """Complete theme diagnostic workflow."""
    print("=== THEME DIAGNOSTIC WORKFLOW ===")
    
    # Step 1: Check theme manager status
    if hasattr(widget, 'theme_manager') and widget.theme_manager:
        print(f"✅ Theme manager available: {widget.theme_manager.current_theme_name}")
    else:
        print("❌ No theme manager available")
        return
    
    # Step 2: Run comprehensive analysis
    if hasattr(widget, 'debug_comprehensive_analysis'):
        widget.debug_comprehensive_analysis()
    
    # Step 3: Attempt automated fixes
    if hasattr(widget, 'debug_fix_widget_colors'):
        print("🔧 Attempting automated color fixes...")
        widget.debug_fix_widget_colors()
        
        # Re-analyze after fix
        print("🔍 Re-analyzing after fixes...")
        widget.debug_comprehensive_analysis()
    
    print("=== DIAGNOSTIC COMPLETE ===")
```

---

## Conclusion

The enhanced Ghostman styling system now provides a robust, self-healing approach to UI theming with comprehensive color management. Key improvements include:

### Major Enhancements

- **Multi-Strategy Theme Switching**: 5-step HTML color injection system overcomes PyQt6 caching issues
- **Self-Healing Recovery**: Automatic fallback mechanisms with widget recreation ensure visual consistency
- **39 JSON Theme Collection**: Rich variety of professionally crafted themes with consistent structure
- **Advanced Debugging Tools**: Comprehensive diagnostic and repair capabilities for troubleshooting
- **Performance Optimization**: Debounced theme switching with cached color dictionaries
- **Enhanced Widget Registration**: Improved theme manager with automatic widget updates

### Critical Fixes Implemented

1. **Fixed existing content color updates**: Solved the major issue where previously rendered content didn't update colors when switching themes
2. **PyQt6 HTML caching bypass**: Multi-strategy HTML injection ensures colors always apply
3. **Widget recreation fallback**: Nuclear option for stubborn cases that resist color updates
4. **Debounce mechanism repair**: Fixed stuck theme switching flags that blocked subsequent changes
5. **Smart color fallbacks**: Luminance-based text color selection for accessibility

### Essential Integration Points

1. **Multi-Strategy Updates**: Use enhanced color management for content areas
2. **Debug Integration**: Implement debugging support for complex widgets
3. **Widget Registration**: Always use theme manager registration instead of direct signals
4. **39-Theme Testing**: Test components with diverse themes from the collection
5. **Self-Healing Support**: Use fallback mechanisms for robust operation
6. **Performance Monitoring**: Monitor and optimize theme switch timing

Following these enhanced patterns ensures your components integrate seamlessly with the advanced theme system and provide a consistent, professional user experience with comprehensive content management and robust error recovery.

---

## File Locations

### Core System Files
- **Theme Manager**: `ghostman/src/ui/themes/theme_manager.py`
- **Color System**: `ghostman/src/ui/themes/color_system.py`
- **Style Templates**: `ghostman/src/ui/themes/style_templates.py`

### Enhanced Widgets
- **MixedContentDisplay**: `ghostman/src/presentation/widgets/mixed_content_display.py`
- **REPL Widget**: `ghostman/src/presentation/widgets/repl_widget.py`

### Theme Collection
- **39 JSON Themes**: `ghostman/src/ui/themes/json/*.json`
- **Custom Themes**: `%APPDATA%/Ghostman/themes/` (Windows)

### Documentation
- **This Guide**: `docs/STYLING_SYSTEM_GUIDE.md`

For implementation questions, advanced system extensions, or troubleshooting complex theme issues, refer to the comprehensive debugging tools and this updated documentation.