# Ghostman Theme System Guide

A comprehensive guide to using and developing with the Ghostman theme system, featuring 24 semantic color variables, 10 preset themes, and live theme switching capabilities.

## Table of Contents

- [Overview](#overview)
- [User Guide](#user-guide)
- [Developer Guide](#developer-guide)
- [Architecture](#architecture)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Ghostman theme system provides a flexible, accessible theming framework built on PyQt6. It features:

- **24 Semantic Color Variables**: Organized into logical groups (primary, backgrounds, text, interactive, status, borders)
- **10 Preset Themes**: Carefully designed themes from dark matrix to arctic white
- **Live Theme Switching**: Real-time theme updates without application restart
- **Component Integration**: Automatic styling for all UI components
- **Accessibility**: Built-in contrast validation and WCAG compliance checking
- **Import/Export**: Save and share custom themes

### Color Variable Categories

1. **Primary Colors** (4 variables): Main brand colors and hover states
2. **Backgrounds** (4 variables): Various background surfaces
3. **Text Colors** (4 variables): Text hierarchy and disabled states
4. **Interactive Elements** (4 variables): Button and control states
5. **Status Colors** (4 variables): Success, warning, error, and info states
6. **Borders & Separators** (4 variables): Border, focus, and separator styling

## User Guide

### Accessing the Theme Editor

1. **From System Tray**: Right-click the Ghostman tray icon → Settings → Appearance
2. **From Main Window**: Click the settings gear → Appearance tab
3. **Keyboard Shortcut**: `Ctrl+T` (when main window is focused)

### Using Preset Themes

1. Open the Theme Editor dialog
2. In the "Preset Themes" dropdown, select any of the 10 available themes:
   - **Default**: Standard dark theme with green accents
   - **Dark Matrix**: Matrix-inspired with bright green highlights
   - **Midnight Blue**: Sophisticated blue color scheme
   - **Forest Green**: Natural green tones
   - **Sunset Orange**: Warm orange/brown palette
   - **Royal Purple**: Elegant purple theme
   - **Arctic White**: Clean light theme
   - **Cyberpunk**: Futuristic neon accents
   - **Earth Tones**: Warm brown color palette
   - **Ocean Deep**: Deep blue-green tones

3. Enable "Live Updates" to see changes in real-time
4. Click "Apply" to confirm your selection

### Creating Custom Themes

#### Method 1: Modify Existing Theme

1. Select a preset theme as your starting point
2. Navigate through the color category tabs:
   - Primary Colors
   - Backgrounds
   - Text Colors
   - Interactive Elements
   - Status Colors
   - Borders & Separators
3. Click any color preview button to open the color picker
4. Choose your desired color and see the preview update instantly
5. Use the undo button (↶) next to each color to revert changes

#### Method 2: Start from Scratch

1. Select any preset theme
2. Use "Reset All" to clear all modifications
3. Systematically customize each color category
4. Monitor the validation status in the preview panel

### Saving Custom Themes

1. After creating your custom theme, enter a name in the "Save Custom Theme" section
2. Click "Save Custom Theme"
3. Your theme will appear in the preset themes dropdown
4. Custom themes are stored in: `%APPDATA%/Ghostman/themes/custom/`

### Import/Export Themes

#### Exporting Themes
1. Configure your desired theme
2. Optionally enter a name for the export
3. Click "Export Theme"
4. Choose a save location (.json file)

#### Importing Themes
1. Click "Import Theme"
2. Select a .json theme file
3. The theme will be added to your custom themes
4. Select it from the preset dropdown to apply

### Theme Validation

The theme editor automatically validates your color choices:

- **✓ Passed**: All colors are valid and accessible
- **⚠ Issues**: Some accessibility concerns detected (hover over for details)

Common validation issues:
- Invalid hex color codes
- Low contrast ratios (below WCAG AA 4.5:1 standard)
- Missing color definitions

## Developer Guide

### Integrating Components with the Theme System

#### Basic Theme Integration

```python
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.ui.themes.style_templates import StyleTemplates

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme)
    
    def update_theme(self, color_system):
        """Update widget styling when theme changes."""
        style = StyleTemplates.get_button_primary_style(color_system)
        self.setStyleSheet(style)
```

#### Available Style Templates

The `StyleTemplates` class provides pre-built styles for common components:

- `get_main_window_style()` - Main application window
- `get_button_primary_style()` - Primary action buttons
- `get_button_secondary_style()` - Secondary buttons
- `get_input_field_style()` - Text inputs and text edits
- `get_combo_box_style()` - Dropdown menus
- `get_list_widget_style()` - List components
- `get_menu_style()` - Context menus
- `get_tab_widget_style()` - Tab controls
- `get_dialog_style()` - Modal dialogs
- `get_scroll_bar_style()` - Scroll bars
- `get_progress_bar_style()` - Progress indicators

#### Custom Style Templates

Create custom templates for your components:

```python
def get_my_component_style(colors: ColorSystem) -> str:
    return f"""
    MyComponent {{
        background-color: {colors.background_secondary};
        color: {colors.text_primary};
        border: 1px solid {colors.border_primary};
        border-radius: 4px;
    }}
    MyComponent:hover {{
        background-color: {colors.interactive_hover};
        border-color: {colors.border_focus};
    }}
    """
```

#### Accessing Individual Colors

```python
# Get current theme colors
theme_manager = get_theme_manager()
current_theme = theme_manager.current_theme

# Access specific colors
primary_color = current_theme.primary
background_color = current_theme.background_primary
text_color = current_theme.text_primary

# Or use the convenience method
border_color = current_theme.get_color('border_primary')
```

### Creating New Preset Themes

Add new preset themes to `preset_themes.py`:

```python
def get_my_custom_theme() -> ColorSystem:
    """My custom theme description."""
    return ColorSystem(
        # Primary colors
        primary="#your_color",
        primary_hover="#your_hover_color",
        secondary="#your_secondary",
        secondary_hover="#your_secondary_hover",
        
        # Continue with all 24 color variables...
        # See existing themes for complete examples
    )

# Add to get_preset_themes() function:
def get_preset_themes() -> Dict[str, ColorSystem]:
    return {
        # ... existing themes ...
        "my_custom": get_my_custom_theme(),
    }
```

### Color Utilities

Use the `ColorUtils` class for color manipulation:

```python
from ghostman.src.ui.themes.color_system import ColorUtils

# Lighten a color by 10%
lighter = ColorUtils.lighten("#4CAF50", 0.1)

# Darken a color by 20%
darker = ColorUtils.darken("#4CAF50", 0.2)

# Add transparency
transparent = ColorUtils.with_alpha("#4CAF50", 0.8)

# Blend two colors
blended = ColorUtils.blend("#4CAF50", "#2196F3", 0.5)
```

## Architecture

### Theme Manager (`theme_manager.py`)

Central theme management with these key features:

- **Signal-based Updates**: `theme_changed`, `theme_loaded`, `theme_saved`, `theme_deleted`
- **Theme Persistence**: Automatic saving/loading from user settings
- **Validation**: Built-in accessibility and consistency checking
- **History**: Undo support for theme changes

### Color System (`color_system.py`)

Defines the 24-variable color structure:

```python
@dataclass
class ColorSystem:
    # Primary brand colors (4)
    primary: str = "#4CAF50"
    primary_hover: str = "#45a049"
    secondary: str = "#2196F3"
    secondary_hover: str = "#1976D2"
    
    # Background colors (4)
    background_primary: str = "#1a1a1a"
    background_secondary: str = "#2a2a2a"
    background_tertiary: str = "#3a3a3a"
    background_overlay: str = "#000000cc"
    
    # Text colors (4)
    text_primary: str = "#ffffff"
    text_secondary: str = "#cccccc"
    text_tertiary: str = "#888888"
    text_disabled: str = "#555555"
    
    # Interactive elements (4)
    interactive_normal: str = "#4a4a4a"
    interactive_hover: str = "#5a5a5a"
    interactive_active: str = "#6a6a6a"
    interactive_disabled: str = "#333333"
    
    # Status colors (4)
    status_success: str = "#4CAF50"
    status_warning: str = "#FF9800"
    status_error: str = "#F44336"
    status_info: str = "#2196F3"
    
    # Borders and separators (4)
    border_primary: str = "#444444"
    border_secondary: str = "#333333"
    border_focus: str = "#4CAF50"
    separator: str = "#2a2a2a"
```

### Style Templates (`style_templates.py`)

Provides CSS template generation using theme variables. Each template:

- Takes a `ColorSystem` as input
- Returns a CSS string for PyQt6 `setStyleSheet()`
- Covers all component states (normal, hover, active, disabled)
- Maintains consistent styling patterns

### Theme Editor (`theme_editor.py`)

Comprehensive editing interface featuring:

- **Tabbed Color Organization**: Groups colors by function
- **Live Preview**: Real-time visual feedback
- **Validation Display**: Immediate accessibility feedback
- **Import/Export**: Theme sharing capabilities
- **Undo System**: Per-color and global reset options

## Best Practices

### For Users

1. **Test Accessibility**: Always check the validation status when creating custom themes
2. **Use Semantic Groups**: Understand what each color category affects before modifying
3. **Start with Presets**: Base custom themes on existing presets rather than starting from scratch
4. **Export Backups**: Save your custom themes as files for backup and sharing
5. **Consider Context**: Light themes work better in well-lit environments, dark themes in low light

### For Developers

1. **Use Style Templates**: Prefer existing templates over custom CSS when possible
2. **Connect to Signals**: Always listen for `theme_changed` signals to update your components
3. **Semantic Naming**: Use appropriate color variables based on their semantic meaning
4. **Validate Integration**: Test your components with all preset themes
5. **Handle Edge Cases**: Ensure your components work with both light and dark themes

### Accessibility Guidelines

1. **Contrast Ratios**: Maintain minimum 4.5:1 contrast for normal text, 3:1 for large text
2. **Color Independence**: Don't rely solely on color to convey information
3. **Focus Indicators**: Use `border_focus` for clear focus visibility
4. **Status Colors**: Keep status colors consistent with user expectations
5. **Test with Tools**: Use accessibility checkers to validate your themes

## Troubleshooting

### Common Issues

#### Theme Not Applying
**Problem**: Theme changes don't appear in the application
**Solutions**:
1. Check if "Live Updates" is enabled in the theme editor
2. Restart the application
3. Verify the theme was saved successfully
4. Check application logs for theme-related errors

#### Colors Appear Wrong
**Problem**: Colors don't match the theme editor preview
**Solutions**:
1. Ensure the component is properly connected to theme signals
2. Check if the component uses style templates
3. Verify the component's stylesheet isn't being overridden
4. Clear any cached stylesheets

#### Validation Failures
**Problem**: Theme validation shows errors
**Solutions**:
1. Check for invalid hex color codes (must start with # and be 3, 6, or 8 characters)
2. Improve contrast ratios between text and background colors
3. Ensure all required color variables are defined
4. Use the color picker rather than typing colors manually

#### Import/Export Problems
**Problem**: Cannot import or export themes
**Solutions**:
1. Verify file permissions in the themes directory
2. Check JSON file format validity
3. Ensure the file contains all required color variables
4. Try exporting a working theme first to see the expected format

#### Performance Issues
**Problem**: Theme switching is slow or causes lag
**Solutions**:
1. Disable "Live Updates" during editing
2. Reduce the frequency of theme changes
3. Check for memory leaks in custom components
4. Profile theme-related code for bottlenecks

### Getting Help

1. **Check Logs**: Application logs contain detailed theme system information
2. **Validation Messages**: Hover over validation warnings for specific issues
3. **Default Recovery**: Use "Reset All" to return to known working state
4. **Community**: Share theme files with other users for troubleshooting

### File Locations

- **Custom Themes**: `%APPDATA%/Ghostman/themes/custom/`
- **Settings**: `%APPDATA%/Ghostman/settings.json`
- **Logs**: `%APPDATA%/Ghostman/logs/`

For development, theme system files are located in:
- `ghostman/src/ui/themes/`