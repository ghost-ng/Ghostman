# Ghostman Styling System - Complete Guide

The definitive guide to the Ghostman application's styling system, covering architecture, implementation, and best practices for developers and theme creators.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Color System](#color-system)
4. [Theme Management](#theme-management)
5. [Button Styling](#button-styling)
6. [Component Integration](#component-integration)
7. [Search Bar Implementation](#search-bar-implementation)
8. [REPL Area Styling](#repl-area-styling)
9. [Opacity System](#opacity-system)
10. [Style Templates](#style-templates)
11. [Developer Integration Guide](#developer-integration-guide)
12. [API Reference](#api-reference)
13. [Best Practices](#best-practices)
14. [Troubleshooting](#troubleshooting)
15. [Performance Optimization](#performance-optimization)

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
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        # Apply current theme
        self.update_theme(self.theme_manager.current_theme)
    
    def update_theme(self, color_system):
        # For buttons: ALWAYS use ButtonStyleManager
        ButtonStyleManager.apply_unified_button_style(
            my_button, color_system, "push", "medium", "normal"
        )
        
        # For other elements: Use StyleTemplates or color variables
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color_system.background_secondary};
                color: {color_system.text_primary};
            }}
        """)
```

---

## System Architecture

### Overview Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 Application Layer                        │
├─────────────────────────────────────────────────────────┤
│                  Theme Manager                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │   Signal    │ │  Validation │ │   Storage   │        │
│  │ Management  │ │   System    │ │   Manager   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│                 Style System Layer                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ ColorSystem │ │ButtonStyle  │ │StyleTemplate│        │
│  │    Core     │ │  Manager    │ │   Library   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│                Component Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │    REPL     │ │   Dialogs   │ │   Search    │        │
│  │   Widget    │ │   & Forms   │ │ Components  │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Core Design Principles

- **Centralized Color Management**: Single source of truth via `ColorSystem`
- **Signal-Based Updates**: Real-time theme changes across all components
- **Unified Button Styling**: Consistent appearance via `ButtonStyleManager`
- **Accessibility First**: WCAG 2.1 compliance with contrast validation
- **Performance Optimized**: Efficient theme switching with minimal recomputation
- **Selective Opacity**: Opacity applied only to specific areas without affecting UI controls

---

## Color System

### The 24-Variable Semantic Color System

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

### Accessibility Features

The ColorSystem includes comprehensive WCAG 2.1 AA compliance checking:

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

### Color Usage Guidelines

#### Semantic Consistency
- Always use colors for their intended semantic purpose
- Don't use `status_error` for non-error elements
- Keep `primary` colors for primary actions only

#### Accessibility Requirements
- Maintain minimum 4.5:1 contrast for normal text
- Maintain minimum 3:1 contrast for large text
- Ensure focus indicators are clearly visible
- Don't rely solely on color to convey information

---

## Theme Management

### ThemeManager Class

Central theme management with signal-based updates:

```python
from ghostman.src.ui.themes.theme_manager import get_theme_manager

theme_manager = get_theme_manager()

# Connect to theme change signals
theme_manager.theme_changed.connect(self._on_theme_changed)
theme_manager.theme_validation_failed.connect(self._on_validation_failed)

# Theme operations
theme_manager.set_theme("openai_like")
current_theme = theme_manager.current_theme
theme_manager.save_custom_theme("my_theme", custom_color_system)
```

#### Available Signals

- `theme_changed(ColorSystem)`: Emitted when theme changes
- `theme_loaded(str)`: Emitted when theme is loaded
- `theme_saved(str)`: Emitted when theme is saved
- `theme_deleted(str)`: Emitted when theme is deleted
- `theme_validation_failed(list)`: Emitted when validation fails

#### Theme Management Methods

| Method | Purpose |
|--------|---------|
| `set_theme(name)` | Set theme by name |
| `set_custom_theme(color_system, name)` | Apply custom theme |
| `save_custom_theme(name, color_system)` | Save to disk |
| `delete_custom_theme(name)` | Delete custom theme |
| `export_theme(name, file_path)` | Export to file |
| `import_theme(file_path, name)` | Import from file |
| `get_available_themes()` | List all themes |

---

## Button Styling

### Unified Button System - CRITICAL USAGE

**IMPORTANT**: ALL buttons MUST use `ButtonStyleManager` for consistency. Never apply direct CSS to buttons.

#### The Only Correct Way to Style Buttons

```python
from ghostman.src.ui.themes.style_templates import ButtonStyleManager

# Apply unified styling (ONLY method to use)
ButtonStyleManager.apply_unified_button_style(
    button=my_button,                    # Qt button widget
    colors=colors,                       # ColorSystem instance
    button_type="push",                  # "push", "tool", or "icon"
    size="medium",                       # Size configuration
    state="normal",                      # Button state
    special_colors=None,                 # Optional custom colors
    emoji_font="Segoe UI Emoji"         # Optional emoji font
)
```

#### Button Types and Sizes

**Button Types:**
- `"push"`: Standard QPushButton with borders (dialog buttons)
- `"tool"`: QToolButton without borders (toolbars)
- `"icon"`: Square icon-only buttons (minimal space)

**Size Configurations:**
- `"icon"`: Square buttons sized proportionally to icon + padding
- `"extra_small"`: 48x28px for compact interfaces
- `"small"`: 60x32px for secondary actions
- `"medium"`: 80x32px for primary actions (default)
- `"large"`: 100x36px for prominent actions

**Button States:**
- `"normal"`: Default appearance
- `"toggle"`: Active/selected state (primary color)
- `"danger"`: Destructive actions (status_error color)
- `"success"`: Positive actions (status_success color)
- `"warning"`: Caution actions (status_warning color)

#### Dynamic Icon Sizing System

The system automatically adjusts button dimensions based on configurable icon size:

```python
# Get current sizing information
sizes = ButtonStyleManager.get_computed_sizes()
print(f"Icon: {sizes['icon_size']}px, Button: {sizes['button_size']}px")

# Smart padding algorithm:
# Icons ≤10px: 2px total padding
# Icons 11-16px: 4px total padding
# Icons ≥17px: 6px total padding
```

#### Real-World Examples

```python
# Titlebar minimize button (clean, borderless icon)
ButtonStyleManager.apply_unified_button_style(
    self.minimize_btn, colors, "tool", "icon", "normal"
)

# Settings dialog OK button (primary action)
ButtonStyleManager.apply_unified_button_style(
    self.ok_btn, colors, "push", "medium", "success"
)

# Dangerous delete button
ButtonStyleManager.apply_unified_button_style(
    self.delete_btn, colors, "push", "medium", "danger"
)
```

---

## Component Integration

### Complete Integration Pattern

Every theme-aware component should follow this pattern:

```python
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.ui.themes.style_templates import StyleTemplates, ButtonStyleManager
from ghostman.src.ui.themes.color_system import ColorSystem

class ThemeAwareWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Step 1: Get theme manager and connect signals
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # Step 2: Setup UI structure
        self._setup_ui()
        
        # Step 3: Apply initial theme
        self._apply_initial_theme()
    
    def _setup_ui(self):
        """Create all UI elements before theme application."""
        # Create widgets, layouts, connections
        pass
    
    def _apply_initial_theme(self):
        """Apply theme after UI setup is complete."""
        self._on_theme_changed(self.theme_manager.current_theme)
    
    def _on_theme_changed(self, colors: ColorSystem):
        """Handle theme changes comprehensively."""
        try:
            # Apply base widget styling
            self._apply_base_styling(colors)
            
            # Style ALL buttons using ButtonStyleManager
            self._style_all_buttons(colors)
            
            # Apply component-specific styling
            self._apply_component_styling(colors)
            
        except Exception as e:
            logger.error(f"Theme application failed: {e}")
            self._apply_fallback_styling()
    
    def _style_all_buttons(self, colors: ColorSystem):
        """Style all buttons using ButtonStyleManager."""
        for button in self.findChildren((QPushButton, QToolButton)):
            ButtonStyleManager.apply_unified_button_style(
                button, colors, "push", "medium", "normal"
            )
```

---

## Search Bar Implementation

### Border-Free Search Components

Search bars use comprehensive border removal techniques:

```python
from ghostman.src.ui.themes.style_templates import StyleTemplates

# Apply border-free styling
search_style = StyleTemplates.get_search_frame_style(colors)
search_frame.setStyleSheet(search_style)
```

#### Complete Border Removal

```python
def remove_frame_borders_comprehensive(self, frame: QFrame):
    """Complete border removal using all available techniques."""
    
    # Qt API approach
    frame.setFrameStyle(QFrame.Shape.NoFrame)
    frame.setLineWidth(0)
    frame.setMidLineWidth(0)
    frame.setContentsMargins(0, 0, 0, 0)
    
    # CSS enforcement with !important directives
    border_removal_css = """
    QFrame {
        border: none !important;
        border-width: 0px !important;
        border-style: none !important;
        border-color: transparent !important;
        outline: none !important;
        box-shadow: none !important;
    }
    """
    frame.setStyleSheet(border_removal_css)
```

### High-Contrast Search Status Labels

Search status uses automatic contrast calculation:

```python
from ghostman.src.ui.themes.color_system import ColorUtils

# Apply high-contrast text automatically
optimal_color, contrast_ratio = ColorUtils.get_high_contrast_text_color_for_background(
    background_color=colors.background_tertiary,
    theme_colors=colors,
    min_ratio=4.5  # WCAG AA compliance
)

status_label.setStyleSheet(f"color: {optimal_color};")
```

---

## REPL Area Styling

### Selective Opacity Implementation

The REPL demonstrates selective opacity - only content areas get transparency:

```python
class REPLWidget(QWidget):
    def _apply_opacity_settings(self):
        """Apply opacity only to content areas."""
        opacity = self.settings.get_opacity_setting()
        colors = self.theme_manager.current_theme
        
        # Content areas can have opacity
        content_style = f"""
        #repl-content-display {{
            background-color: rgba({self._hex_to_rgb(colors.background_tertiary)}, {opacity});
        }}
        """
        
        # UI controls always remain fully opaque
        ui_control_style = f"""
        #repl-toolbar, #search-controls, .repl-button {{
            background-color: {colors.background_secondary};
            opacity: 1.0 !important;
        }}
        """
        
        self.setStyleSheet(content_style + ui_control_style)
```

### REPL Panel Structure

```python
def _setup_repl_structure(self):
    """Create REPL with proper ID assignments for styling."""
    self.setObjectName("repl-root")
    
    # Toolbar (always opaque)
    self.toolbar_frame = QFrame()
    self.toolbar_frame.setObjectName("repl-toolbar")
    
    # Content display (can have opacity)
    self.content_frame = QFrame()
    self.content_frame.setObjectName("repl-content-display")
    
    # Status bar (always opaque)
    self.status_frame = QFrame()
    self.status_frame.setObjectName("repl-status")
```

---

## Opacity System

### Correct vs Incorrect Implementation

#### ✅ Correct: Selective Opacity

```python
def apply_content_opacity(self, content_widget, opacity_value):
    """Apply opacity selectively to content areas only."""
    content_style = f"""
    #content-display, .message-content {{
        background-color: rgba({self._hex_to_rgba(bg_color)}, {opacity_value});
    }}
    
    /* UI controls always remain fully opaque */
    QPushButton, QToolButton, QLineEdit, QComboBox {{
        opacity: 1.0 !important;
        background-color: {colors.interactive_normal} !important;
    }}
    """
    content_widget.setStyleSheet(content_style)
```

#### ❌ Incorrect: Global Opacity

```python
def apply_panel_opacity_wrong(self, panel, opacity_value):
    """WRONG: This makes UI controls hard to see."""
    # BAD: This affects ALL child widgets including buttons
    panel.setStyleSheet(f"""
        QWidget {{
            background-color: rgba(0, 0, 0, {opacity_value});  /* WRONG */
        }}
    """)
```

---

## Style Templates

### Available Templates

The `StyleTemplates` class provides pre-built styles:

#### Application Templates
- `get_main_window_style()` - Main application window
- `get_repl_panel_style()` - REPL output panel with opacity handling
- `get_settings_dialog_style()` - Comprehensive dialog styling

#### Form Element Templates
- `get_input_field_style()` - Text inputs (QLineEdit, QTextEdit)
- `get_combo_box_style()` - Dropdown selections with custom arrows
- `get_checkbox_style()` - Custom checkbox indicators
- `get_list_widget_style()` - List views with selection states

#### Navigation Templates
- `get_tab_widget_style()` - Tabbed interfaces with rounded tabs
- `get_menu_style()` - Context and dropdown menus
- `get_scroll_bar_style()` - Modern rounded scrollbars

#### Search System Templates
- `get_search_frame_style()` - Border-free search containers
- `get_high_contrast_search_status_style()` - Auto-calculated high contrast text

### Creating Custom Templates

```python
def get_custom_widget_style(colors: ColorSystem, variant: str = "normal", **kwargs) -> str:
    """Custom widget template with variants and options."""
    size = kwargs.get('size', 'medium')
    show_borders = kwargs.get('show_borders', True)
    
    # Base styling
    base_style = f"""
    CustomWidget {{
        background-color: {colors.background_tertiary};
        color: {colors.text_primary};
        border-radius: 4px;
        padding: {'4px' if size == 'small' else '8px'};
    }}
    """
    
    # Variant-specific styling
    if variant == "emphasized":
        variant_style = f"""
        CustomWidget {{
            border: 2px solid {colors.border_focus};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        """
    elif variant == "minimal":
        variant_style = f"""
        CustomWidget {{
            background-color: transparent;
            border: none;
        }}
        """
    else:
        variant_style = f"""
        CustomWidget {{
            border: 1px solid {colors.border_primary if show_borders else 'transparent'};
        }}
        """
    
    return base_style + variant_style
```

---

## Developer Integration Guide

### Integration Checklist

When integrating a new component:

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

### Performance Optimization

#### Style Caching

```python
class OptimizedThemeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._style_cache = {}
        self._current_theme_hash = None
    
    def update_theme(self, color_system: ColorSystem):
        """Optimized theme update with caching."""
        theme_hash = self._hash_theme(color_system)
        
        if theme_hash == self._current_theme_hash:
            return  # No change, skip update
        
        if theme_hash in self._style_cache:
            style = self._style_cache[theme_hash]
        else:
            style = self._generate_style(color_system)
            self._style_cache[theme_hash] = style
        
        self.setStyleSheet(style)
        self._current_theme_hash = theme_hash
```

#### Debounced Updates

```python
from PyQt6.QtCore import QTimer

class DebouncedThemeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._apply_pending_theme)
        self._pending_theme = None
    
    def update_theme(self, color_system: ColorSystem):
        """Debounced theme update."""
        self._pending_theme = color_system
        self._update_timer.start(50)  # 50ms debounce
```

### Testing and Validation

```python
def test_theme_integration(component_class):
    """Comprehensive theme testing."""
    component = component_class()
    theme_manager = get_theme_manager()
    
    # Test theme switching
    test_themes = ["dracula", "openai_like", "arctic_white"]
    for theme_name in test_themes:
        theme_manager.set_theme(theme_name)
        # Verify component updated
        assert hasattr(component, '_last_theme_update')
    
    # Test button consistency
    buttons = component.findChildren((QPushButton, QToolButton))
    for button in buttons:
        style = button.styleSheet()
        assert "border-radius: 4px" in style
        assert "padding:" in style
```

---

## API Reference

### ColorSystem

#### Constructor
```python
ColorSystem(
    primary="#4CAF50",
    primary_hover="#45a049",
    # ... all 24 color variables
)
```

#### Methods
- `to_dict() -> Dict[str, str]`: Convert to dictionary
- `from_dict(data: Dict[str, str]) -> ColorSystem`: Create from dictionary
- `get_color(name: str) -> str`: Get color by name with fallback
- `validate() -> Tuple[bool, List[str]]`: Validate accessibility

### ThemeManager

#### Properties
- `current_theme: ColorSystem`: Current active theme
- `current_theme_name: str`: Current theme name

#### Methods
- `set_theme(name: str) -> bool`: Set theme by name
- `set_custom_theme(color_system, name=None) -> bool`: Apply custom theme
- `save_custom_theme(name: str, color_system=None) -> bool`: Save custom theme
- `get_available_themes() -> List[str]`: Get all theme names

### ButtonStyleManager

#### Class Constants
- `PADDING = "8px"`: Standard button padding
- `BORDER_RADIUS = "4px"`: Standard border radius
- `FONT_SIZE = "12px"`: Standard font size
- `DEFAULT_ICON_SIZE = 10`: Default icon size in pixels

#### Static Methods
- `get_icon_size() -> int`: Get current icon size from settings
- `get_computed_sizes() -> dict`: Get computed sizes for debugging
- `apply_unified_button_style(button, colors, button_type, size, state, special_colors, emoji_font)`: Apply unified styling

### ColorUtils

#### Static Methods
- `lighten(color: str, factor: float = 0.1) -> str`: Lighten a color
- `darken(color: str, factor: float = 0.1) -> str`: Darken a color
- `with_alpha(color: str, alpha: float) -> str`: Add alpha channel
- `blend(color1: str, color2: str, ratio: float = 0.5) -> str`: Blend colors
- `get_high_contrast_text_color_for_background(background_color: str, theme_colors=None, min_ratio: float = 4.5) -> Tuple[str, float]`: Calculate optimal text color

---

## Best Practices

### 1. Always Use Unified Button Styling

**✅ DO:**
```python
ButtonStyleManager.apply_unified_button_style(my_button, colors, "push", "medium")
```

**❌ DON'T:**
```python
my_button.setStyleSheet("background: blue; padding: 10px;")  # Inconsistent!
```

### 2. Connect to Theme Change Signals

```python
def __init__(self):
    self.theme_manager = get_theme_manager()
    self.theme_manager.theme_changed.connect(self._update_theme)

def _update_theme(self, colors):
    # Re-apply styling when theme changes
    ButtonStyleManager.apply_unified_button_style(self.my_button, colors)
```

### 3. Use Semantic Color Variables

**✅ DO:**
```python
color = colors.status_error  # Semantic meaning clear
```

**❌ DON'T:**
```python
color = "#ff0000"  # Hard-coded, no theme support
```

### 4. Validate Custom Themes

```python
is_valid, issues = custom_theme.validate()
if not is_valid:
    logger.warning(f"Theme validation issues: {issues}")
```

### 5. Apply Complete Widget Styling

```python
# Complete styling for dialogs
dialog.setStyleSheet(StyleTemplates.get_settings_dialog_style(colors))

# Rather than piecemeal styling
dialog.setStyleSheet(f"background-color: {colors.background_primary}")  # Incomplete!
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Buttons Look Different Across Dialogs

**Problem**: Some buttons have different padding or appearance
**Solution**: Ensure ALL buttons use `ButtonStyleManager.apply_unified_button_style()`

```python
# Check if button was styled manually
print(button.styleSheet())  # Should be empty or from ButtonStyleManager

# Re-apply unified styling
ButtonStyleManager.apply_unified_button_style(button, colors)
```

#### 2. Theme Changes Don't Update UI

**Problem**: UI doesn't refresh when theme changes
**Solution**: Connect to theme change signals

```python
theme_manager.theme_changed.connect(self._refresh_styling)

def _refresh_styling(self, colors):
    # Re-apply all styling with new colors
    self._apply_theme_styling(colors)
```

#### 3. Poor Text Contrast

**Problem**: Text is hard to read against backgrounds
**Solution**: Use high contrast text calculation

```python
optimal_color, ratio = ColorUtils.get_high_contrast_text_color_for_background(
    background_color, colors, min_ratio=4.5
)
label.setStyleSheet(f"color: {optimal_color}")
```

#### 4. Search Frames Have Visible Borders

**Problem**: Search components show unwanted borders
**Solution**: Use comprehensive border removal

```python
search_frame.setStyleSheet(StyleTemplates.get_search_frame_style(colors))

# Also apply Qt API methods
search_frame.setFrameStyle(QFrame.Shape.NoFrame)
search_frame.setLineWidth(0)
```

#### 5. Icon Buttons Are Wrong Size

**Problem**: Icon buttons don't match configured icon size
**Solution**: Ensure proper ButtonStyleManager usage

```python
ButtonStyleManager.apply_unified_button_style(
    icon_button, colors, "tool", "icon"
)
```

### Debug Commands

```python
# Get current theme info
theme_manager = get_theme_manager()
print(f"Current theme: {theme_manager.current_theme_name}")

# Get button size info
sizes = ButtonStyleManager.get_computed_sizes()
print(f"Button sizing: {sizes}")

# Check theme validation
is_valid, issues = theme_manager.current_theme.validate()
print(f"Theme valid: {is_valid}, Issues: {issues}")
```

---

## Performance Optimization

### Caching Strategies

1. **Style Caching**: Cache generated CSS for repeated use
2. **Selective Updates**: Only update when relevant colors change
3. **Debounced Updates**: Delay updates to avoid rapid-fire changes
4. **Batch Operations**: Update multiple components together

### Memory Management

- Disconnect signals properly in component cleanup
- Clear style caches periodically
- Use weak references for theme manager connections
- Avoid storing large style strings unnecessarily

---

## Conclusion

The Ghostman styling system provides a comprehensive, accessible, and maintainable approach to UI theming. Key benefits:

- **Visual Consistency**: ButtonStyleManager guarantees identical button styling
- **Accessibility Compliance**: Built-in WCAG 2.1 validation
- **Developer Productivity**: Signal-based updates and comprehensive templates
- **Performance**: Efficient theme switching with caching support
- **Extensibility**: Easy to add new themes and components

### Essential Integration Points

1. **ButtonStyleManager**: Always use for ALL buttons
2. **Theme Signals**: Connect to theme_changed for live updates
3. **StyleTemplates**: Use for consistent component styling
4. **High-Contrast Calculation**: Use for optimal text readability
5. **Error Handling**: Include fallbacks for graceful degradation

Following these patterns ensures your components integrate seamlessly with the theme system and provide a consistent, professional user experience.

---

## File Locations

- **Core System**: `ghostman/src/ui/themes/`
- **Theme Files**: `%APPDATA%/Ghostman/themes/`
- **Documentation**: `docs/STYLING_SYSTEM_GUIDE.md`

For implementation questions or system extensions, refer to the source code and this comprehensive documentation.