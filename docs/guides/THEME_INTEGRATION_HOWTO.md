# Theme Integration How-To Guide

A practical guide for developers to integrate components with the Ghostman theme system, covering everything from basic integration to advanced customization.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Integration](#basic-integration)
- [Advanced Integration](#advanced-integration)
- [Creating Custom Style Templates](#creating-custom-style-templates)
- [Signal Handling](#signal-handling)
- [Performance Optimization](#performance-optimization)
- [Testing and Validation](#testing-and-validation)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 5-Minute Integration

For a new widget that needs basic theme support:

```python
from PyQt6.QtWidgets import QWidget, QPushButton
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
        # Use existing style template
        style = StyleTemplates.get_button_primary_style(color_system)
        self.setStyleSheet(style)
```

That's it! Your widget now responds to theme changes automatically.

## Basic Integration

### Step 1: Import Required Modules

```python
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.ui.themes.color_system import ColorSystem
from ghostman.src.ui.themes.style_templates import StyleTemplates
```

### Step 2: Get Theme Manager Reference

```python
class MyComponent(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        # ... rest of initialization
```

### Step 3: Connect to Theme Signals

```python
def _connect_theme_signals(self):
    """Connect to theme manager signals."""
    self.theme_manager.theme_changed.connect(self.update_theme)
    self.theme_manager.theme_loaded.connect(self._on_theme_loaded)
    # Optional: Listen for validation failures
    self.theme_manager.theme_validation_failed.connect(self._on_validation_failed)
```

### Step 4: Apply Current Theme

```python
def _apply_initial_theme(self):
    """Apply the current theme during initialization."""
    current_theme = self.theme_manager.current_theme
    self.update_theme(current_theme)
```

### Step 5: Implement Theme Update Method

```python
def update_theme(self, color_system: ColorSystem):
    """Update component styling based on the color system."""
    # Method 1: Use existing style template
    style = StyleTemplates.get_button_primary_style(color_system)
    self.setStyleSheet(style)
    
    # Method 2: Access individual colors
    self.setStyleSheet(f"""
        QWidget {{
            background-color: {color_system.background_secondary};
            color: {color_system.text_primary};
        }}
    """)
```

## Advanced Integration

### Complex Components with Multiple Elements

```python
class AdvancedDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self._init_ui()
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Create various UI elements
        self.title_label = QLabel("Dialog Title")
        self.content_text = QTextEdit()
        self.primary_button = QPushButton("Apply")
        self.secondary_button = QPushButton("Cancel")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.content_text)
        layout.addWidget(self.primary_button)
        layout.addWidget(self.secondary_button)
        
        self.setLayout(layout)
    
    def update_theme(self, color_system: ColorSystem):
        """Apply theme to all components."""
        # Dialog background
        dialog_style = StyleTemplates.get_dialog_style(color_system)
        self.setStyleSheet(dialog_style)
        
        # Title with primary text color
        title_style = StyleTemplates.get_label_style(color_system, "primary")
        self.title_label.setStyleSheet(title_style)
        
        # Content area
        input_style = StyleTemplates.get_input_field_style(color_system)
        self.content_text.setStyleSheet(input_style)
        
        # Buttons with different styles
        primary_style = StyleTemplates.get_button_primary_style(color_system)
        secondary_style = StyleTemplates.get_button_secondary_style(color_system)
        
        self.primary_button.setStyleSheet(primary_style)
        self.secondary_button.setStyleSheet(secondary_style)
```

### Custom Styling with Color System

```python
def create_custom_panel_style(self, color_system: ColorSystem) -> str:
    """Create custom panel styling using theme colors."""
    return f"""
    QFrame#custom-panel {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {color_system.background_secondary},
            stop: 1 {color_system.background_tertiary}
        );
        border: 2px solid {color_system.border_primary};
        border-radius: 8px;
        padding: 10px;
    }}
    
    QFrame#custom-panel:hover {{
        border-color: {color_system.border_focus};
    }}
    
    QLabel#panel-title {{
        color: {color_system.text_primary};
        font-weight: bold;
        font-size: 14px;
        padding: 4px 0px;
    }}
    
    QLabel#panel-subtitle {{
        color: {color_system.text_secondary};
        font-size: 12px;
    }}
    """
```

### Dynamic Theme Switching Support

```python
class ThemeAwareWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self._cached_styles = {}  # Cache styles for performance
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def update_theme(self, color_system: ColorSystem):
        """Update theme with caching for performance."""
        # Generate cache key based on color system
        cache_key = self._generate_cache_key(color_system)
        
        if cache_key not in self._cached_styles:
            # Generate and cache new style
            self._cached_styles[cache_key] = self._generate_styles(color_system)
        
        # Apply cached style
        self.setStyleSheet(self._cached_styles[cache_key])
    
    def _generate_cache_key(self, color_system: ColorSystem) -> str:
        """Generate a cache key for the color system."""
        # Use a subset of colors that affect this widget
        relevant_colors = [
            color_system.background_primary,
            color_system.text_primary,
            color_system.border_primary
        ]
        return "|".join(relevant_colors)
    
    def _generate_styles(self, color_system: ColorSystem) -> str:
        """Generate styles for the color system."""
        return f"""
        QWidget {{
            background-color: {color_system.background_primary};
            color: {color_system.text_primary};
            border: 1px solid {color_system.border_primary};
        }}
        """
```

## Creating Custom Style Templates

### Template Structure

```python
# In your custom module or extending style_templates.py
def get_my_component_style(colors: ColorSystem, **kwargs) -> str:
    """
    Style template for MyComponent.
    
    Args:
        colors: Color system to use
        **kwargs: Additional customization options
            - size: 'small', 'medium', 'large' (default: 'medium')
            - variant: 'primary', 'secondary' (default: 'primary')
    
    Returns:
        CSS string for the component
    """
    size = kwargs.get('size', 'medium')
    variant = kwargs.get('variant', 'primary')
    
    # Size-based padding
    padding_map = {
        'small': '4px 8px',
        'medium': '6px 12px',
        'large': '8px 16px'
    }
    padding = padding_map.get(size, padding_map['medium'])
    
    # Variant-based colors
    if variant == 'primary':
        bg_color = colors.primary
        hover_color = colors.primary_hover
    else:
        bg_color = colors.secondary
        hover_color = colors.secondary_hover
    
    return f"""
    MyComponent {{
        background-color: {bg_color};
        color: {colors.text_primary};
        border: 1px solid {colors.border_primary};
        border-radius: 4px;
        padding: {padding};
        font-weight: bold;
    }}
    
    MyComponent:hover {{
        background-color: {hover_color};
        border-color: {colors.border_focus};
    }}
    
    MyComponent:pressed {{
        background-color: {colors.interactive_active};
    }}
    
    MyComponent:disabled {{
        background-color: {colors.interactive_disabled};
        color: {colors.text_disabled};
        border-color: {colors.border_secondary};
    }}
    """
```

### Using Custom Templates

```python
def update_theme(self, color_system: ColorSystem):
    """Apply custom template with options."""
    style = get_my_component_style(
        color_system,
        size='large',
        variant='secondary'
    )
    self.my_component.setStyleSheet(style)
```

### Extending Existing Templates

```python
def get_enhanced_button_style(colors: ColorSystem, **kwargs) -> str:
    """Enhanced button style based on existing template."""
    # Start with existing template
    base_style = StyleTemplates.get_button_primary_style(colors)
    
    # Add enhancements
    enhancements = f"""
    QPushButton {{
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        transition: all 0.2s ease;
    }}
    
    QPushButton:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }}
    """
    
    return base_style + enhancements
```

## Signal Handling

### Complete Signal Implementation

```python
class FullyIntegratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self._connect_all_signals()
        self._apply_initial_theme()
    
    def _connect_all_signals(self):
        """Connect to all relevant theme signals."""
        # Primary signal - theme changes
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        # Optional signals for advanced behavior
        self.theme_manager.theme_loaded.connect(self._on_theme_loaded)
        self.theme_manager.theme_saved.connect(self._on_theme_saved)
        self.theme_manager.theme_deleted.connect(self._on_theme_deleted)
        self.theme_manager.theme_validation_failed.connect(self._on_validation_failed)
    
    def update_theme(self, color_system: ColorSystem):
        """Primary theme update handler."""
        # Apply new theme
        style = self._generate_style(color_system)
        self.setStyleSheet(style)
        
        # Update any dynamic content
        self._update_dynamic_colors(color_system)
        
        # Emit custom signal if needed
        self.theme_updated.emit(color_system)
    
    def _on_theme_loaded(self, theme_name: str):
        """Handle theme loaded signal."""
        print(f"Theme '{theme_name}' loaded")
        # Optional: Update UI to reflect theme name
    
    def _on_theme_saved(self, theme_name: str):
        """Handle theme saved signal."""
        print(f"Theme '{theme_name}' saved")
        # Optional: Show notification
    
    def _on_theme_deleted(self, theme_name: str):
        """Handle theme deleted signal."""
        print(f"Theme '{theme_name}' deleted")
        # Optional: Clean up references
    
    def _on_validation_failed(self, issues: list):
        """Handle theme validation failure."""
        print(f"Theme validation failed: {issues}")
        # Optional: Show validation issues to user
```

### Conditional Signal Handling

```python
def _connect_theme_signals(self, live_updates: bool = True):
    """Connect theme signals with conditional live updates."""
    if live_updates:
        # Connect for immediate updates
        self.theme_manager.theme_changed.connect(self.update_theme)
    else:
        # Only connect to explicit apply signals
        self.theme_manager.theme_loaded.connect(self._apply_theme_after_load)

def _apply_theme_after_load(self, theme_name: str):
    """Apply theme only after explicit load."""
    theme = self.theme_manager.get_theme(theme_name)
    if theme:
        self.update_theme(theme)
```

## Performance Optimization

### Style Caching

```python
class OptimizedThemeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._style_cache = {}
        self._current_theme_hash = None
        self.theme_manager = get_theme_manager()
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def update_theme(self, color_system: ColorSystem):
        """Optimized theme update with caching."""
        # Generate theme hash for caching
        theme_hash = self._hash_theme(color_system)
        
        # Check if theme changed
        if theme_hash == self._current_theme_hash:
            return  # No change, skip update
        
        # Check cache
        if theme_hash in self._style_cache:
            style = self._style_cache[theme_hash]
        else:
            # Generate and cache new style
            style = self._generate_style(color_system)
            self._style_cache[theme_hash] = style
            
            # Limit cache size
            if len(self._style_cache) > 10:
                # Remove oldest entry
                oldest_key = next(iter(self._style_cache))
                del self._style_cache[oldest_key]
        
        # Apply style
        self.setStyleSheet(style)
        self._current_theme_hash = theme_hash
    
    def _hash_theme(self, color_system: ColorSystem) -> str:
        """Generate hash for theme caching."""
        # Only hash colors that affect this widget
        relevant_colors = [
            color_system.background_primary,
            color_system.text_primary,
            color_system.primary,
            color_system.border_primary
        ]
        return "|".join(relevant_colors)
```

### Debounced Updates

```python
from PyQt6.QtCore import QTimer

class DebouncedThemeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        
        # Debounce timer
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._apply_pending_theme)
        
        self._pending_theme = None
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def update_theme(self, color_system: ColorSystem):
        """Debounced theme update."""
        self._pending_theme = color_system
        self._update_timer.start(50)  # 50ms debounce
    
    def _apply_pending_theme(self):
        """Apply the pending theme update."""
        if self._pending_theme:
            style = self._generate_style(self._pending_theme)
            self.setStyleSheet(style)
            self._pending_theme = None
```

### Selective Updates

```python
class SelectiveThemeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self._relevant_colors = [
            'background_primary',
            'text_primary',
            'border_primary'
        ]
        self._last_color_values = {}
        self._connect_theme_signals()
        self._apply_initial_theme()
    
    def update_theme(self, color_system: ColorSystem):
        """Only update if relevant colors changed."""
        current_values = {
            color: getattr(color_system, color)
            for color in self._relevant_colors
        }
        
        if current_values == self._last_color_values:
            return  # No relevant changes
        
        # Apply update
        style = self._generate_style(color_system)
        self.setStyleSheet(style)
        
        # Cache current values
        self._last_color_values = current_values
```

## Testing and Validation

### Theme Testing Mixin

```python
class ThemeTestMixin:
    """Mixin for testing theme integration."""
    
    def test_theme_integration(self):
        """Test widget with all preset themes."""
        theme_manager = get_theme_manager()
        
        for theme_name in theme_manager.get_preset_themes():
            theme = theme_manager.get_theme(theme_name)
            
            # Apply theme
            self.update_theme(theme)
            
            # Verify style was applied
            self.assertIsNotNone(self.styleSheet())
            
            # Check for common CSS issues
            style = self.styleSheet()
            self.assertNotIn('undefined', style.lower())
            self.assertNotIn('null', style.lower())
    
    def test_theme_signal_handling(self):
        """Test signal connection and handling."""
        theme_manager = get_theme_manager()
        
        # Count update calls
        update_count = 0
        original_update = self.update_theme
        
        def counting_update(color_system):
            nonlocal update_count
            update_count += 1
            original_update(color_system)
        
        self.update_theme = counting_update
        
        # Trigger theme change
        theme_manager.set_theme('dark_matrix')
        
        # Verify update was called
        self.assertGreater(update_count, 0)
```

### Validation Helpers

```python
def validate_theme_integration(widget, color_system: ColorSystem) -> list:
    """Validate theme integration for a widget."""
    issues = []
    
    # Check if widget has theme update method
    if not hasattr(widget, 'update_theme'):
        issues.append("Widget missing update_theme method")
    
    # Check if signals are connected
    theme_manager = get_theme_manager()
    if not theme_manager.theme_changed.isConnected():
        issues.append("Theme signals not connected")
    
    # Apply theme and check for errors
    try:
        widget.update_theme(color_system)
    except Exception as e:
        issues.append(f"Theme update failed: {e}")
    
    # Check if style was applied
    if not widget.styleSheet():
        issues.append("No stylesheet applied after theme update")
    
    return issues
```

## Common Patterns

### Pattern 1: Simple Widget Theme Integration

```python
class SimpleThemedWidget(QWidget):
    """Basic pattern for simple widgets."""
    
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme)
    
    def update_theme(self, color_system):
        style = StyleTemplates.get_button_primary_style(color_system)
        self.setStyleSheet(style)
```

### Pattern 2: Complex Dialog with Multiple Elements

```python
class ThemedDialog(QDialog):
    """Pattern for complex dialogs with multiple styled elements."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._connect_theme()
        self._apply_theme()
    
    def _init_ui(self):
        # Create UI elements
        pass
    
    def _connect_theme(self):
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
    
    def _apply_theme(self):
        self.update_theme(self.theme_manager.current_theme)
    
    def update_theme(self, color_system):
        # Apply different templates to different elements
        self.setStyleSheet(StyleTemplates.get_dialog_style(color_system))
        self.primary_button.setStyleSheet(
            StyleTemplates.get_button_primary_style(color_system)
        )
        self.secondary_button.setStyleSheet(
            StyleTemplates.get_button_secondary_style(color_system)
        )
```

### Pattern 3: Custom Component with State Management

```python
class StatefulThemedComponent(QWidget):
    """Pattern for components that need to maintain state across theme changes."""
    
    def __init__(self):
        super().__init__()
        self._state = {'selected': False, 'enabled': True}
        self._init_ui()
        self._connect_theme()
        self._apply_theme()
    
    def set_selected(self, selected: bool):
        self._state['selected'] = selected
        self._update_styling()
    
    def set_enabled(self, enabled: bool):
        self._state['enabled'] = enabled
        super().setEnabled(enabled)
        self._update_styling()
    
    def update_theme(self, color_system):
        self._color_system = color_system
        self._update_styling()
    
    def _update_styling(self):
        """Update styling based on current state and theme."""
        if not hasattr(self, '_color_system'):
            return
        
        style = self._generate_state_style(self._color_system, self._state)
        self.setStyleSheet(style)
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Theme Not Applying
```python
# Problem: Widget doesn't update when theme changes
class BrokenWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Missing theme connection!
        
# Solution: Always connect theme signals
class FixedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme)
```

#### Issue: Performance Problems
```python
# Problem: Expensive style generation on every update
def update_theme(self, color_system):
    # Expensive operation every time
    complex_style = self._generate_complex_style(color_system)
    self.setStyleSheet(complex_style)

# Solution: Add caching
def update_theme(self, color_system):
    cache_key = self._get_theme_cache_key(color_system)
    if cache_key not in self._style_cache:
        self._style_cache[cache_key] = self._generate_complex_style(color_system)
    self.setStyleSheet(self._style_cache[cache_key])
```

#### Issue: Signal Memory Leaks
```python
# Problem: Not disconnecting signals properly
class LeakyWidget(QWidget):
    def __init__(self):
        super().__init__()
        theme_manager = get_theme_manager()
        theme_manager.theme_changed.connect(self.update_theme)
        # Widget gets destroyed but signal connection remains!

# Solution: Proper cleanup
class CleanWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
    
    def closeEvent(self, event):
        # Disconnect signals before destruction
        self.theme_manager.theme_changed.disconnect(self.update_theme)
        super().closeEvent(event)
```

### Debugging Theme Issues

```python
def debug_theme_integration(widget):
    """Debug helper for theme integration issues."""
    print(f"Debugging widget: {widget.__class__.__name__}")
    
    # Check theme manager connection
    theme_manager = get_theme_manager()
    print(f"Theme manager available: {theme_manager is not None}")
    
    # Check current theme
    current_theme = theme_manager.current_theme
    print(f"Current theme: {current_theme}")
    
    # Check signal connections
    signal_count = len(theme_manager.theme_changed.receivers())
    print(f"Theme signal receivers: {signal_count}")
    
    # Check if widget has update method
    has_update = hasattr(widget, 'update_theme')
    print(f"Widget has update_theme: {has_update}")
    
    # Check current stylesheet
    current_style = widget.styleSheet()
    print(f"Current stylesheet length: {len(current_style)}")
    
    # Test theme application
    try:
        if has_update:
            widget.update_theme(current_theme)
            print("Theme update successful")
        else:
            print("Widget missing update_theme method")
    except Exception as e:
        print(f"Theme update failed: {e}")
```

### Validation Tools

```python
def validate_style_templates():
    """Validate all style templates work with default theme."""
    theme_manager = get_theme_manager()
    default_theme = theme_manager.get_theme('default')
    
    # Test all available templates
    template_methods = [
        method for method in dir(StyleTemplates)
        if method.startswith('get_') and method.endswith('_style')
    ]
    
    for method_name in template_methods:
        try:
            method = getattr(StyleTemplates, method_name)
            style = method(default_theme)
            assert isinstance(style, str)
            assert len(style) > 0
            print(f"✓ {method_name} - OK")
        except Exception as e:
            print(f"✗ {method_name} - Failed: {e}")
```

## Integration Checklist

When integrating a new component with the theme system:

- [ ] Import theme manager and style templates
- [ ] Get theme manager instance in `__init__`
- [ ] Connect to `theme_changed` signal
- [ ] Implement `update_theme(color_system)` method
- [ ] Apply current theme during initialization
- [ ] Use appropriate style templates when possible
- [ ] Test with all preset themes
- [ ] Verify performance with live theme switching
- [ ] Handle signal disconnection in cleanup
- [ ] Add validation for theme-related functionality
- [ ] Document any custom styling requirements
- [ ] Consider caching for complex style generation

Following these patterns and guidelines will ensure your components integrate seamlessly with the Ghostman theme system and provide a consistent, professional user experience.