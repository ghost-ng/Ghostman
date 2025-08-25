# Ghostman Styling System Guide

A comprehensive guide to the Ghostman styling system, covering theme integration, CSS inheritance solutions, and advanced UI styling patterns for PyQt6 applications.

## Table of Contents

- [Overview](#overview)
- [Icon System Updates](#icon-system-updates)
- [Menu System Enhancements](#menu-system-enhancements)
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
- **26 Preset Themes**: Carefully designed themes from dark matrix to arctic white, including the redesigned professional Lilac theme
- **Smart Icon System**: Automatic theme-aware icon selection with luminance-based variant loading
- **16px Icon Standard**: Consistent icon sizing across all interface elements
- **Enhanced Menu Styling**: Professional dropdown menus with theme-aware backgrounds and hover states
- **Live Theme Switching**: Real-time theme updates without application restart
- **CSS Inheritance Solutions**: Advanced techniques for overriding PyQt6 style inheritance
- **Component Integration**: Automatic styling for all UI components
- **Performance Optimization**: Caching and optimization strategies

### System Architecture

```
Theme Manager
├── Color System (24 variables)
├── Style Templates (component styles)
├── Preset Themes (26 built-in themes)
├── Icon System (smart variant loading)
├── Menu Styling (theme-aware backgrounds)
└── Theme Editor (live editing interface)
```

## Icon System Updates

### New 16px Icon Standard

The ButtonStyleManager has been updated with a new default icon size:

```python
# Updated in ButtonStyleManager
DEFAULT_ICON_SIZE = 16  # Changed from 10px to 16px

# Usage example
from ghostman.src.ui.themes.style_templates import ButtonStyleManager

button_style = ButtonStyleManager.apply_unified_button_style(
    button=my_button,
    color_system=color_system,
    icon_path="save.png"  # Will be automatically sized to 16px
)
```

### Smart Icon Variant Selection

The system now automatically chooses between dark and light icon variants based on menu background luminance:

```python
def _load_themed_icon(self, base_icon_name: str) -> QIcon:
    """
    Load theme-appropriate icon variant based on menu background luminance.
    
    Args:
        base_icon_name: Base name without _dark/_lite suffix (e.g., 'save')
        
    Returns:
        QIcon with appropriate variant loaded
    """
    try:
        color_system = get_theme_manager().current_theme
        
        # Calculate W3C luminance for menu background
        menu_bg_color = color_system.background_secondary
        luminance = self._calculate_luminance(menu_bg_color)
        
        # Choose variant based on luminance (0.5 threshold)
        variant = 'dark' if luminance > 0.5 else 'lite'
        icon_filename = f"{base_icon_name}_{variant}.png"
        icon_path = self.assets_dir / "icons" / icon_filename
        
        if icon_path.exists():
            return QIcon(str(icon_path))
        else:
            # Fallback to base name without variant
            fallback_path = self.assets_dir / "icons" / f"{base_icon_name}.png"
            return QIcon(str(fallback_path)) if fallback_path.exists() else QIcon()
            
    except Exception as e:
        logger.warning(f"Failed to load themed icon {base_icon_name}: {e}")
        return QIcon()
```

### W3C Luminance Calculation

The system uses W3C standard luminance calculation for optimal contrast:

```python
def _calculate_luminance(self, color_string: str) -> float:
    """
    Calculate W3C luminance for automatic icon variant selection.
    
    Args:
        color_string: CSS color string (e.g., '#FF5733', 'rgb(255, 87, 51)')
        
    Returns:
        Luminance value between 0.0 (black) and 1.0 (white)
    """
    try:
        from PyQt6.QtGui import QColor
        
        color = QColor(color_string)
        if not color.isValid():
            return 0.0
        
        # Convert to linear RGB values (0-1 range)
        r = color.redF()
        g = color.greenF() 
        b = color.blueF()
        
        # Apply gamma correction
        def gamma_correct(val):
            return val / 12.92 if val <= 0.04045 else pow((val + 0.055) / 1.055, 2.4)
        
        r_linear = gamma_correct(r)
        g_linear = gamma_correct(g)
        b_linear = gamma_correct(b)
        
        # Calculate luminance using W3C formula
        luminance = 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear
        return luminance
        
    except Exception as e:
        logger.warning(f"Failed to calculate luminance for {color_string}: {e}")
        return 0.0
```

## Menu System Enhancements

### Theme-Aware Menu Styling

Menus now automatically adapt their styling based on the current theme:

```python
def _style_menu(self, menu):
    """Apply theme-aware styling to dropdown menu."""
    try:
        color_system = get_theme_manager().current_theme
        menu_style = StyleTemplates.get_menu_style(color_system)
        menu.setStyleSheet(menu_style)
        
        # Update menu icons based on background luminance
        self._update_menu_icons(menu)
        
    except Exception as e:
        logger.warning(f"Failed to style menu: {e}")
```

### Enhanced Menu CSS Template

The menu styling template provides comprehensive theming:

```python
def get_menu_style(color_system) -> str:
    """
    Generate comprehensive menu styling with theme integration.
    
    Features:
    - Theme-aware background colors
    - Proper hover states
    - Enhanced separators
    - Accessibility-compliant contrast
    """
    return f"""
        QMenu {{
            background-color: {color_system.background_secondary};
            color: {color_system.text_primary};
            border: 1px solid {color_system.border_primary};
            border-radius: 4px;
            padding: 4px 0px;
            min-width: 120px;
        }}
        
        QMenu::item {{
            background-color: transparent;
            color: {color_system.text_primary};
            padding: 6px 12px 6px 28px;
            margin: 1px 0px;
            min-height: 20px;
        }}
        
        QMenu::item:selected {{
            background-color: {color_system.interactive_hover};
            color: {color_system.text_primary};
            border-radius: 2px;
        }}
        
        QMenu::item:pressed {{
            background-color: {color_system.interactive_pressed};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {color_system.border_secondary};
            margin: 4px 8px;
        }}
        
        QMenu::icon {{
            left: 6px;
            width: 16px;
            height: 16px;
        }}
    """
```

### Save Button Integration

The new dedicated save button uses smart icon loading:

```python
def _load_save_icon(self) -> QIcon:
    """Load appropriate save icon variant based on theme."""
    return self._load_themed_icon("save")  # Automatically loads save_dark.png or save_lite.png

def _create_save_button(self):
    """Create theme-aware save button for title bar."""
    save_button = QPushButton()
    save_button.setIcon(self._load_save_icon())
    save_button.setIconSize(QSize(16, 16))  # Standard 16px sizing
    save_button.setToolTip("Save Conversation (replaces dropdown menu save)")
    save_button.setObjectName("title_save_button")
    
    # Apply unified button styling
    ButtonStyleManager.apply_unified_button_style(
        button=save_button,
        color_system=get_theme_manager().current_theme
    )
    
    save_button.clicked.connect(self._handle_save_conversation)
    return save_button
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
        
        # Individual components with 16px icons
        self.primary_button.setStyleSheet(
            StyleTemplates.get_button_primary_style(color_system)
        )
        self.primary_button.setIconSize(QSize(16, 16))
        
        self.input_field.setStyleSheet(
            StyleTemplates.get_input_field_style(color_system)
        )
        
        # Apply menu styling if present
        if hasattr(self, 'context_menu'):
            self._style_menu(self.context_menu)
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
        
        # Update icons for new theme
        self._update_themed_icons()
        
        # CRITICAL: Ensure inheritance overrides after theme changes
        self._schedule_tab_transparency_enforcement()
        
    except Exception as e:
        logger.error(f"Failed to update widget theme: {e}")

def _update_themed_icons(self):
    """Update all themed icons after theme change."""
    if hasattr(self, 'save_button'):
        self.save_button.setIcon(self._load_save_icon())
    
    if hasattr(self, 'context_menu'):
        self._update_menu_icons(self.context_menu)
```

## Advanced Styling Patterns

### Icon Integration Patterns

For components that use the new icon system:

```python
class IconAwareWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.assets_dir = Path(__file__).parent.parent / "assets"
        self._init_icons()
    
    def _init_icons(self):
        """Initialize icons with theme awareness."""
        # Load themed icons
        self.save_icon = self._load_themed_icon("save")
        self.new_icon = self._load_themed_icon("new_conversation")
        
        # Apply to buttons with standard 16px sizing
        self.save_button.setIcon(self.save_icon)
        self.save_button.setIconSize(QSize(16, 16))
    
    def update_theme(self, color_system):
        """Update theme including icon variants."""
        # Update standard styling
        self._apply_theme_styles(color_system)
        
        # Reload icons for new theme
        self._reload_themed_icons()
    
    def _reload_themed_icons(self):
        """Reload all themed icons after theme change."""
        self.save_icon = self._load_themed_icon("save")
        self.new_icon = self._load_themed_icon("new_conversation")
        
        # Update button icons
        self.save_button.setIcon(self.save_icon)
        self.new_button.setIcon(self.new_icon)
```

### Menu Integration Patterns

For widgets with context menus:

```python
class MenuIntegratedWidget(QWidget):
    def _create_context_menu(self):
        """Create context menu with theme integration."""
        menu = QMenu(self)
        
        # Add actions with themed icons
        save_action = menu.addAction("Save")
        save_action.setIcon(self._load_themed_icon("save"))
        
        # Remove unnecessary separators for cleaner look
        menu.addAction("New Tab")
        menu.addAction("New Conversation")
        # Note: Save moved to title bar, no longer in dropdown menu
        
        # Apply theme styling
        self._style_menu(menu)
        
        return menu
    
    def _update_menu_icons(self, menu):
        """Update menu icons based on current theme."""
        for action in menu.actions():
            if action.text() == "Save":
                action.setIcon(self._load_themed_icon("save"))
            elif action.text() == "New Tab":
                action.setIcon(self._load_themed_icon("new_tab"))
```

## Component-Specific Styling

### Title Bar Components

For title bar elements with the new save button:

```python
class TitleBarWidget(QWidget):
    def _init_title_bar(self):
        """Initialize title bar with new save button."""
        layout = QHBoxLayout()
        
        # Create save button (replaces dropdown menu save)
        self.save_button = self._create_save_button()
        layout.addWidget(self.save_button)
        
        # Create plus menu (without save option)
        self.plus_button = self._create_plus_button()
        layout.addWidget(self.plus_button)
        
        # Apply consistent 16px icon sizing
        self._standardize_icon_sizes()
    
    def _standardize_icon_sizes(self):
        """Ensure all title bar icons use 16px sizing."""
        standard_size = QSize(16, 16)
        
        for button in [self.save_button, self.plus_button, self.pin_button]:
            button.setIconSize(standard_size)
    
    def _create_plus_menu(self):
        """Create plus menu without save option (moved to title bar)."""
        menu = QMenu(self)
        
        # Streamlined menu structure
        menu.addAction("New Tab", self._handle_new_tab)
        menu.addAction("New Conversation", self._handle_new_conversation)
        # Note: Save option removed - now handled by dedicated button
        
        self._style_menu(menu)
        return menu
```

### Tab System Integration

For tabbed interfaces with proper transparency:

```python
class TabSystemWidget(QWidget):
    def _init_tab_system(self):
        """Initialize tab system with transparency and theme integration."""
        # Create tab frame with proper naming
        self.tab_frame = QFrame()
        self.tab_frame.setObjectName("tab_frame")
        self.tab_frame.setAutoFillBackground(False)
        
        # Initialize tab bar with 16px close icons
        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setCloseButtonSize(QSize(16, 16))
        
        # Apply transparency solution
        self._apply_tab_transparency()
        self._schedule_tab_transparency_enforcement()
    
    def update_theme(self, color_system):
        """Update theme including tab styling."""
        # Standard theme update
        self._apply_theme_styles(color_system)
        
        # Update tab close icons
        self._update_tab_close_icons()
        
        # Maintain transparency overrides
        self._schedule_tab_transparency_enforcement()
    
    def _update_tab_close_icons(self):
        """Update tab close button icons for current theme."""
        close_icon = self._load_themed_icon("close")
        # Apply to tab bar close buttons
        for i in range(self.tab_bar.count()):
            # Tab close buttons are handled internally by Qt
            # but we can influence through styling
            pass
```

## Performance Optimization

### Icon Caching

Cache themed icons for better performance:

```python
class IconCacheManager:
    def __init__(self):
        self._icon_cache = {}
        self._current_theme_hash = None
    
    def get_themed_icon(self, base_name: str) -> QIcon:
        """Get themed icon with caching."""
        theme_hash = self._get_current_theme_hash()
        cache_key = f"{base_name}_{theme_hash}"
        
        if cache_key not in self._icon_cache:
            self._icon_cache[cache_key] = self._load_themed_icon(base_name)
        
        return self._icon_cache[cache_key]
    
    def clear_cache(self):
        """Clear icon cache on theme change."""
        self._icon_cache.clear()
        self._current_theme_hash = None
```

### Style Caching with Icon Support

Enhanced caching that includes icon variants:

```python
class OptimizedThemedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._style_cache = {}
        self._icon_cache = {}
        self._current_theme_hash = None
    
    def update_theme(self, color_system):
        """Optimized theme update with style and icon caching."""
        theme_hash = self._generate_theme_hash(color_system)
        
        if theme_hash == self._current_theme_hash:
            return  # No change
        
        # Update cached styles
        if theme_hash not in self._style_cache:
            self._style_cache[theme_hash] = self._generate_style(color_system)
        self.setStyleSheet(self._style_cache[theme_hash])
        
        # Update cached icons
        self._update_cached_icons(theme_hash)
        
        self._current_theme_hash = theme_hash
    
    def _update_cached_icons(self, theme_hash):
        """Update icon cache for current theme."""
        if theme_hash not in self._icon_cache:
            self._icon_cache[theme_hash] = {
                'save': self._load_themed_icon('save'),
                'new': self._load_themed_icon('new_conversation'),
            }
        
        # Apply cached icons
        icons = self._icon_cache[theme_hash]
        self.save_button.setIcon(icons['save'])
        self.new_button.setIcon(icons['new'])
```

## Best Practices

### Icon System Best Practices

1. **Use Standard 16px Sizing**: All title bar and button icons should use 16x16 pixels
2. **Provide Both Variants**: Create both _dark.png and _lite.png versions for all icons
3. **Use Luminance Calculation**: Let the system automatically choose appropriate variants
4. **Cache Icon Loading**: Implement caching for frequently accessed themed icons
5. **Test All Themes**: Verify icon visibility across all 26 preset themes

### Menu System Best Practices

1. **Apply Theme Styling**: Always use StyleTemplates.get_menu_style() for menus
2. **Update Icon Variants**: Refresh menu icons when themes change
3. **Remove Redundant Options**: Keep menus clean (save moved to title bar)
4. **Test Hover States**: Verify menu hover behavior across themes
5. **Use Proper Separators**: Apply theme-aware separator styling

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
5. **Handle Edge Cases**: Test with all preset themes, including the redesigned Lilac theme

### Performance

1. **Cache Generated Styles**: Store styles by theme hash
2. **Cache Themed Icons**: Store icon variants by theme
3. **Use Debouncing**: Prevent excessive updates during live editing
4. **Selective Updates**: Only update when relevant colors change
5. **Lazy Loading**: Generate styles and load icons only when needed

### Code Organization

1. **Separate Icon Logic**: Keep icon loading separate from other styling logic
2. **Modular Templates**: Create reusable style and icon templates
3. **Document Solutions**: Comment complex inheritance solutions
4. **Version Control**: Track theme system changes and icon additions
5. **Test Thoroughly**: Validate with all themes and both icon variants

### Integration Checklist

When implementing styling for new components:

- [ ] Import theme manager and style templates
- [ ] Connect to theme_changed signal
- [ ] Implement update_theme() method with icon updates
- [ ] Apply current theme during initialization
- [ ] Use 16px standard sizing for all icons
- [ ] Provide both dark and lite icon variants
- [ ] Test with all preset themes (including redesigned Lilac)
- [ ] Handle CSS inheritance if needed
- [ ] Implement performance optimizations
- [ ] Cache themed icons appropriately
- [ ] Add debugging information
- [ ] Document any custom patterns
- [ ] Test live theme switching with icon updates
- [ ] Verify menu styling if applicable

Following these patterns ensures consistent, performant, and maintainable styling throughout the Ghostman application while successfully handling PyQt6's CSS inheritance challenges and providing optimal visual experiences across all 26 available themes.