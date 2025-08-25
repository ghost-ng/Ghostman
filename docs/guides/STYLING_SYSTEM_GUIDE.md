# Ghostman Styling System Guide

A comprehensive guide to the Ghostman styling system, covering theme integration, CSS inheritance solutions, and advanced UI styling patterns for PyQt6 applications.

## Table of Contents

- [Overview](#overview)
- [Theme System Integration](#theme-system-integration)
- [CSS Inheritance Solutions](#css-inheritance-solutions)
- [Advanced Styling Patterns](#advanced-styling-patterns)
- [Component-Specific Styling](#component-specific-styling)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The Ghostman styling system provides:

- **24 Semantic Color Variables**: Organized into logical groups (primary, backgrounds, text, interactive, status, borders)
- **10 Preset Themes**: Carefully designed themes from dark matrix to arctic white
- **Live Theme Switching**: Real-time theme updates without application restart
- **CSS Inheritance Solutions**: Advanced techniques for overriding PyQt6 style inheritance
- **Component Integration**: Automatic styling for all UI components
- **Performance Optimization**: Caching and optimization strategies

### System Architecture

```
Theme Manager
├── Color System (24 variables)
├── Style Templates (component styles)
├── Preset Themes (10 built-in themes)
└── Theme Editor (live editing interface)
```

## Theme System Integration

### Quick Start Integration

For basic theme support in any widget:

```python
from PyQt6.QtWidgets import QWidget
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.ui.themes.style_templates import StyleTemplates

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Get theme manager instance
        self.theme_manager = get_theme_manager()
        
        # Connect to theme changes
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        # Apply current theme
        self.update_theme(self.theme_manager.current_theme)
    
    def update_theme(self, color_system):
        """Update widget styling when theme changes."""
        style = StyleTemplates.get_button_primary_style(color_system)
        self.setStyleSheet(style)
```

### Advanced Theme Integration

For complex components with multiple styled elements:

```python
class ComplexWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def _connect_theme_signals(self):
        """Connect to all relevant theme signals."""
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.theme_manager.theme_loaded.connect(self._on_theme_loaded)
    
    def update_theme(self, color_system):
        """Update all component styling."""
        # Main widget
        self.setStyleSheet(StyleTemplates.get_dialog_style(color_system))
        
        # Individual components
        self.primary_button.setStyleSheet(
            StyleTemplates.get_button_primary_style(color_system)
        )
        self.input_field.setStyleSheet(
            StyleTemplates.get_input_field_style(color_system)
        )
```

## CSS Inheritance Solutions

### The PyQt6 CSS Inheritance Problem

PyQt6 applies CSS inheritance where child widgets inherit styles from their parents, which can cause issues when you need specific elements to have different styling than their containers.

**Common Problem**: Tab bars or specific UI elements inherit background colors from themed parent containers, making them visually inconsistent.

### Maximum CSS Specificity Solution

This solution uses maximum CSS specificity combined with timing control to override inheritance:

```python
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
            background-color: rgba(0,0,0,0) !important;
            background-image: none !important;
            background-repeat: no-repeat !important;
            background-attachment: scroll !important;
            background-position: 0% 0% !important;
            border: none !important;
            margin: 0px;
            padding: 0px;
        }
    """
    
    try:
        self.tab_frame.setStyleSheet(transparency_css)
        self.tab_frame.setAutoFillBackground(False)
        
        # Force style system to reapply
        self.tab_frame.style().polish(self.tab_frame)
        
    except Exception as e:
        logger.warning(f"Failed to enforce tab transparency: {e}")
```

### Timing Control with QTimer

PyQt6 theme systems often apply styles asynchronously. Use QTimer.singleShot() to ensure your overrides apply after theme styles:

```python
def _schedule_tab_transparency_enforcement(self):
    """Schedule transparency enforcement with multiple timing intervals."""
    try:
        # Immediate application
        self._ensure_tab_frame_transparency()
        
        # Schedule at multiple intervals to handle theme system timing
        QTimer.singleShot(10, self._ensure_tab_frame_transparency)
        QTimer.singleShot(50, self._ensure_tab_frame_transparency)
        QTimer.singleShot(100, self._ensure_tab_frame_transparency)
        
    except Exception as e:
        logger.warning(f"Failed to schedule tab transparency: {e}")
```

### Integration with Theme Changes

Connect the inheritance solution to theme change events:

```python
def _on_theme_changed(self, color_system):
    """Handle theme changes by updating widget styles."""
    try:
        # Update all standard styling
        self._apply_styles()
        self._update_component_themes()
        
        # CRITICAL: Ensure inheritance overrides after theme changes
        self._schedule_tab_transparency_enforcement()
        
    except Exception as e:
        logger.error(f"Failed to update widget theme: {e}")
```

### CSS Specificity Hierarchy

Understanding CSS specificity in PyQt6:

1. **Inline styles** (highest priority)
2. **IDs** (#myWidget)
3. **Classes and attributes** (.myClass, [attribute="value"])
4. **Type selectors** (QWidget)
5. **!important declarations** (override above hierarchy)

**Best Practice**: Use multiple selectors with !important for maximum override power:

```css
/* Maximum specificity approach */
QFrame[objectName="tab_frame"],
#parent-widget QFrame#tab_frame,
#parent-widget QFrame[objectName="tab_frame"] {
    background: transparent !important;
}
```

## Advanced Styling Patterns

### State-Dependent Styling

For components that need different styles based on internal state:

```python
class StatefulComponent(QWidget):
    def __init__(self):
        super().__init__()
        self._state = {'selected': False, 'enabled': True}
        self._connect_theme_signals()
    
    def set_selected(self, selected: bool):
        self._state['selected'] = selected
        self._update_styling()
    
    def update_theme(self, color_system):
        self._color_system = color_system
        self._update_styling()
    
    def _update_styling(self):
        """Update styling based on current state and theme."""
        if not hasattr(self, '_color_system'):
            return
        
        if self._state['selected']:
            bg_color = self._color_system.primary
        else:
            bg_color = self._color_system.background_secondary
            
        if not self._state['enabled']:
            bg_color = self._color_system.interactive_disabled
        
        style = f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {self._color_system.border_primary};
            }}
        """
        self.setStyleSheet(style)
```

### Custom Style Templates

Create reusable styling templates for custom components:

```python
def get_custom_panel_style(colors, variant='primary', size='medium'):
    """
    Custom panel style template.
    
    Args:
        colors: ColorSystem instance
        variant: 'primary' or 'secondary'
        size: 'small', 'medium', or 'large'
    """
    # Size-based measurements
    padding_map = {
        'small': '4px 8px',
        'medium': '8px 12px',
        'large': '12px 16px'
    }
    padding = padding_map.get(size, padding_map['medium'])
    
    # Variant-based colors
    if variant == 'primary':
        bg_color = colors.background_secondary
        border_color = colors.primary
    else:
        bg_color = colors.background_tertiary
        border_color = colors.secondary
    
    return f"""
        QFrame#custom-panel {{
            background-color: {bg_color};
            border: 2px solid {border_color};
            border-radius: 8px;
            padding: {padding};
            margin: 2px;
        }}
        
        QFrame#custom-panel:hover {{
            border-color: {colors.border_focus};
            background-color: {colors.interactive_hover};
        }}
        
        QLabel#panel-title {{
            color: {colors.text_primary};
            font-weight: bold;
            background: transparent;
        }}
    """
```

### Dynamic Color Manipulation

Use color utilities for dynamic styling:

```python
from ghostman.src.ui.themes.color_system import ColorUtils

def create_gradient_style(colors, direction='vertical'):
    """Create gradient background styles."""
    if direction == 'vertical':
        gradient_css = f"""
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {colors.background_secondary},
                stop: 1 {ColorUtils.darken(colors.background_secondary, 0.2)}
            );
        """
    else:
        gradient_css = f"""
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {colors.primary},
                stop: 1 {ColorUtils.lighten(colors.primary, 0.1)}
            );
        """
    
    return f"""
        QWidget {{
            {gradient_css}
            border-radius: 4px;
        }}
    """
```

## Component-Specific Styling

### Tab Systems

For tabbed interfaces that need transparent backgrounds:

```python
class TabWidget(QWidget):
    def _init_tab_bar(self, parent_layout):
        """Initialize tab bar with transparency solution."""
        # Create frame with unique object name
        self.tab_frame = QFrame()
        self.tab_frame.setObjectName("tab_frame")
        self.tab_frame.setAutoFillBackground(False)
        
        # Apply initial styling
        self._apply_tab_transparency()
        
        # Add to layout
        parent_layout.addWidget(self.tab_frame)
        
        # Schedule reinforcement
        self._schedule_tab_transparency_enforcement()
    
    def _apply_tab_transparency(self):
        """Apply comprehensive transparency styling."""
        transparency_css = """
            QFrame[objectName="tab_frame"] {
                background: transparent !important;
                background-color: rgba(0,0,0,0) !important;
                background-image: none !important;
                border: none !important;
                margin: 0px;
                padding: 0px;
            }
        """
        self.tab_frame.setStyleSheet(transparency_css)
```

### Dialog Styling

For modal dialogs with theme integration:

```python
class ThemedDialog(QDialog):
    def update_theme(self, color_system):
        """Apply comprehensive dialog theming."""
        dialog_style = f"""
            QDialog {{
                background-color: {color_system.background_primary};
                color: {color_system.text_primary};
                border: 1px solid {color_system.border_primary};
            }}
            
            QLabel {{
                color: {color_system.text_primary};
                background: transparent;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: {color_system.background_secondary};
                color: {color_system.text_primary};
                border: 1px solid {color_system.border_primary};
                padding: 4px;
                border-radius: 2px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {color_system.border_focus};
            }}
        """
        
        self.setStyleSheet(dialog_style)
        
        # Apply button styles
        for button in self.findChildren(QPushButton):
            if button.objectName() == 'primary':
                button.setStyleSheet(StyleTemplates.get_button_primary_style(color_system))
            else:
                button.setStyleSheet(StyleTemplates.get_button_secondary_style(color_system))
```

## Performance Optimization

### Style Caching

Cache generated styles for better performance:

```python
class OptimizedThemedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._style_cache = {}
        self._current_theme_hash = None
    
    def update_theme(self, color_system):
        """Optimized theme update with caching."""
        theme_hash = self._generate_theme_hash(color_system)
        
        if theme_hash == self._current_theme_hash:
            return  # No change
        
        if theme_hash not in self._style_cache:
            self._style_cache[theme_hash] = self._generate_style(color_system)
        
        self.setStyleSheet(self._style_cache[theme_hash])
        self._current_theme_hash = theme_hash
    
    def _generate_theme_hash(self, color_system):
        """Generate hash for caching."""
        relevant_colors = [
            color_system.background_primary,
            color_system.text_primary,
            color_system.primary
        ]
        return "|".join(relevant_colors)
```

### Debounced Updates

For widgets that receive frequent theme updates:

```python
from PyQt6.QtCore import QTimer

class DebouncedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._apply_pending_theme)
        self._pending_theme = None
    
    def update_theme(self, color_system):
        """Debounced theme update."""
        self._pending_theme = color_system
        self._update_timer.start(50)  # 50ms debounce
    
    def _apply_pending_theme(self):
        """Apply the pending theme."""
        if self._pending_theme:
            style = self._generate_style(self._pending_theme)
            self.setStyleSheet(style)
            self._pending_theme = None
```

### Selective Updates

Only update when relevant colors change:

```python
class SelectiveWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._relevant_colors = ['background_primary', 'text_primary']
        self._last_values = {}
    
    def update_theme(self, color_system):
        """Only update if relevant colors changed."""
        current_values = {
            color: getattr(color_system, color)
            for color in self._relevant_colors
        }
        
        if current_values == self._last_values:
            return
        
        # Apply update
        self._apply_theme_update(color_system)
        self._last_values = current_values
```

## Troubleshooting

### Common CSS Inheritance Issues

**Problem**: Child widgets inherit unwanted styles from parents.

**Solution**: Use maximum CSS specificity with multiple selectors:

```css
/* Instead of */
QWidget { background: red; }

/* Use */
QWidget[objectName="myWidget"],
#parent-container QWidget#myWidget,
#parent-container QWidget[objectName="myWidget"] {
    background: blue !important;
}
```

**Problem**: Styles not applying after theme changes.

**Solution**: Use QTimer.singleShot() to delay application:

```python
def _on_theme_changed(self, color_system):
    # Apply standard styles
    self._apply_styles()
    
    # Schedule inheritance overrides
    QTimer.singleShot(10, self._apply_overrides)
    QTimer.singleShot(50, self._apply_overrides)  # Multiple attempts
```

**Problem**: Performance issues with live theme switching.

**Solution**: Implement caching and debouncing:

```python
def update_theme(self, color_system):
    # Check cache first
    cache_key = self._generate_cache_key(color_system)
    if cache_key in self._cache:
        self.setStyleSheet(self._cache[cache_key])
        return
    
    # Generate and cache
    style = self._generate_style(color_system)
    self._cache[cache_key] = style
    self.setStyleSheet(style)
```

### Debugging Tools

Use these debugging helpers:

```python
def debug_widget_styling(widget):
    """Debug widget styling issues."""
    print(f"Widget: {widget.__class__.__name__}")
    print(f"Object Name: {widget.objectName()}")
    print(f"Current Stylesheet Length: {len(widget.styleSheet())}")
    print(f"AutoFillBackground: {widget.autoFillBackground()}")
    
    # Check parent inheritance
    parent = widget.parent()
    if parent:
        print(f"Parent Stylesheet Length: {len(parent.styleSheet())}")

def validate_theme_colors(color_system):
    """Validate theme color system."""
    required_colors = [
        'primary', 'background_primary', 'text_primary',
        'border_primary', 'interactive_hover'
    ]
    
    missing = []
    for color in required_colors:
        if not hasattr(color_system, color):
            missing.append(color)
    
    if missing:
        print(f"Missing colors: {missing}")
    else:
        print("Theme validation passed")
```

## Best Practices

### CSS Inheritance Solutions

1. **Use Maximum Specificity**: Combine multiple selectors for highest priority
2. **Apply !important Declarations**: Override inheritance with !important
3. **Cover All Background Properties**: Set background, background-color, background-image, etc.
4. **Use Timing Control**: Apply QTimer.singleShot() for proper timing
5. **Disable AutoFillBackground**: Use `setAutoFillBackground(False)` when needed

### Theme Integration

1. **Always Connect Signals**: Connect to `theme_changed` signal in widget constructor
2. **Apply Current Theme**: Call `update_theme()` with current theme during initialization
3. **Use Style Templates**: Prefer existing templates over custom CSS
4. **Cache Complex Styles**: Implement caching for expensive style generation
5. **Handle Edge Cases**: Test with all preset themes

### Performance

1. **Cache Generated Styles**: Store styles by theme hash
2. **Use Debouncing**: Prevent excessive updates during live editing
3. **Selective Updates**: Only update when relevant colors change
4. **Lazy Loading**: Generate styles only when needed
5. **Cleanup Properly**: Disconnect signals in cleanup methods

### Code Organization

1. **Separate Concerns**: Keep styling logic separate from business logic
2. **Modular Templates**: Create reusable style templates
3. **Document Solutions**: Comment complex inheritance solutions
4. **Version Control**: Track theme system changes
5. **Test Thoroughly**: Validate with all themes and edge cases

### Integration Checklist

When implementing styling for new components:

- [ ] Import theme manager and style templates
- [ ] Connect to theme_changed signal
- [ ] Implement update_theme() method
- [ ] Apply current theme during initialization
- [ ] Test with all preset themes
- [ ] Handle CSS inheritance if needed
- [ ] Implement performance optimizations
- [ ] Add debugging information
- [ ] Document any custom patterns
- [ ] Test live theme switching

Following these patterns ensures consistent, performant, and maintainable styling throughout the Ghostman application while successfully handling PyQt6's CSS inheritance challenges.