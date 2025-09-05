# Theme Switching Solution - Complete Fix

## Problem Analysis

**Issue**: Theme switching from the settings dialog was not applying theme JSON stylings correctly to all widgets.

**Root Causes**:
1. **No Global Theme Propagation**: Only the settings dialog itself received theme updates
2. **Missing Widget Registration**: No central system to track and update all widgets
3. **Incomplete Signal Connections**: Most widgets had no connection to theme changes
4. **Inconsistent Application**: Different results between startup and runtime theme switching

## Technical Solution

### 1. Unified Widget Registry System

**Added to ThemeManager**:
- `_registered_widgets`: WeakRef set of all theme-aware widgets  
- `_widget_update_methods`: Maps widgets to their update method names
- Automatic widget registration with `register_widget(widget, method_name)`
- Automatic cleanup of dead references via weak references

### 2. Comprehensive Theme Application  

**Enhanced `set_theme()` method**:
```python
# Apply theme to all registered widgets immediately
self._apply_theme_to_all_widgets()

# Then emit signals for backward compatibility
self.theme_changed.emit(theme)
```

**Method support**:
- `_on_theme_changed(color_system)` - Standard handler expecting ColorSystem
- `set_theme_colors(color_dict)` - Handler expecting color dictionary
- `apply_theme(color_system)` - Generic theme application
- Custom methods - Called without parameters

### 3. Backward Compatibility

**Legacy color key mapping**:
```python
legacy_mappings = {
    'bg_primary': color_dict.get('background_primary'),
    'bg_secondary': color_dict.get('background_secondary'), 
    'bg_tertiary': color_dict.get('background_tertiary'),
    'border': color_dict.get('border_subtle')
}
```

### 4. Automatic Widget Registration

**Updated widgets to self-register**:
- **MixedContentDisplay**: `theme_manager.register_widget(self, "set_theme_colors")`
- **EmbeddedCodeSnippetWidget**: `theme_manager.register_widget(self, "set_theme_colors")`  
- **REPLWidget**: `theme_manager.register_widget(self, "_on_theme_changed")`

## Results

### Before Fix
- **Startup**: ✅ All widgets themed correctly
- **Settings Dialog**: ❌ Only some widgets updated, visual inconsistencies

### After Fix  
- **Startup**: ✅ All widgets themed correctly (unchanged)
- **Settings Dialog**: ✅ All widgets themed correctly (now matches startup)

**Test Output Confirmation**:
```
INFO:ghostman.theme_manager:Theme changed to: cyber - applied to 4 registered widgets
```

## Key Benefits

1. **Consistency**: Settings dialog theme switching now identical to startup loading
2. **Robustness**: All widgets receive theme updates regardless of initialization order
3. **Performance**: Efficient weak reference system prevents memory leaks
4. **Compatibility**: Both old and new widgets work without modification
5. **Extensibility**: Easy to add new widgets via simple registration call

## Technical Implementation Files

### Modified Files:
- `ghostman/src/ui/themes/theme_manager.py` - Core unified system
- `ghostman/src/presentation/widgets/mixed_content_display.py` - Added registration
- `ghostman/src/presentation/widgets/embedded_code_widget.py` - Added registration + color key compatibility
- `ghostman/src/presentation/widgets/repl_widget.py` - Enhanced registration

### New Functionality:
- `ThemeManager.register_widget(widget, update_method)`
- `ThemeManager._apply_theme_to_all_widgets()` 
- Automatic widget lifecycle management with weak references
- Legacy color key mapping for backward compatibility

## Usage

**For new widgets**:
```python
# In widget __init__
if THEME_SYSTEM_AVAILABLE:
    theme_manager = get_theme_manager()
    theme_manager.register_widget(self, "set_theme_colors")  # or "_on_theme_changed"
```

**Result**: Theme switching through settings dialog now produces identical visual results to startup theme loading.