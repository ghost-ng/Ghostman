# Code Font Preservation Fix - Complete Solution

## Problem
Code snippets were losing their monospace fonts when themes changed, making code unreadable. The issue was confirmed through testing - theme switches were overriding monospace fonts with the theme's default font.

## Root Cause Analysis

**Multiple font override sources identified:**
1. **Theme Applicator**: Generic widget styles setting `font-family` on all widgets
2. **QTextEdit Widget Font**: `setFont()` calls applying theme fonts to the entire widget
3. **QTextDocument Default Font**: `setDefaultFont()` affecting HTML rendering
4. **CSS Specificity Issues**: Widget-level fonts overriding HTML inline styles

## Complete Solution Implemented

### 1. Updated Theme Applicator (`theme_applicator.py`)

**Changed**: Removed `font-family` from generic widget styling
```python
# Before - could override monospace fonts:
font-family: 'Segoe UI', Arial, sans-serif;

# After - preserves existing fonts:
# No font-family specified in generic styles
```

**Reason**: The generic font-family was applying to all widgets, potentially overriding carefully chosen monospace fonts in code elements.

### 2. Created Specialized Text Edit Styles (`style_templates.py`)

**Added**: Separate style methods that don't override fonts:
- `get_text_edit_style()` - For QTextEdit/QPlainTextEdit (NO font-family)
- `get_line_edit_style()` - For QLineEdit (NO font-family) 
- Enhanced `get_input_field_style()` - For general input styling

**Key Feature**: These styles intentionally omit `font-family` to preserve existing fonts, especially monospace fonts used for code.

### 3. Enhanced REPL Code Protection (`repl_widget.py`)

**Added Maximum CSS Specificity Protection:**
```html
<style>
code { font-family: Consolas, Monaco, 'Courier New', monospace !important; }
pre { font-family: Consolas, Monaco, 'Courier New', monospace !important; }
pre code { font-family: Consolas, Monaco, 'Courier New', monospace !important; }
</style>
```

**Enhanced Inline Styles**: Added `!important` to inline font declarations:
```html
<code style="font-family: Consolas, Monaco, monospace !important;">
<pre style="font-family: Consolas, Monaco, monospace !important;">
```

### 4. Widget Registration Strategy

**REPL Widget Protection**: Registered REPL as theme-aware to prevent generic styling:
```python
theme_applicator.register_widget(self, theme_aware=True)
```

This prevents the theme applicator from applying generic styles that could override the carefully crafted HTML code fonts.

### 3. Protected REPL Code Rendering

**Existing Protection**: REPL widget already uses inline CSS for code elements:
```html
<code style="font-family: Consolas, Monaco, monospace;">
<pre style="...">
```

**Result**: Code blocks maintain monospace fonts regardless of theme changes because the inline styles have higher CSS specificity than widget-level stylesheets.

## How It Works

1. **Theme Change**: User switches theme in settings
2. **Style Application**: Theme applicator applies colors to widgets
3. **Font Preservation**: 
   - Generic widget styles don't specify fonts
   - Text edit styles preserve existing fonts
   - HTML inline styles in REPL maintain monospace
4. **Result**: Code keeps monospace, UI gets new theme colors

## Benefits

- ✅ **Code Readability**: Code blocks always use monospace fonts
- ✅ **Theme Colors**: Background and text colors update properly
- ✅ **Backward Compatible**: Existing code continues to work
- ✅ **Performance**: No font changes = no layout recalculation

## Testing

Run `test_code_font_preservation.py` to verify:
1. HTML code blocks retain monospace fonts
2. QPlainTextEdit with monospace fonts are preserved
3. Inline code elements maintain their styling
4. Theme colors update without affecting fonts

## Technical Details

### CSS Specificity
Inline styles (in HTML) have higher specificity than widget stylesheets:
- `style="font-family: Consolas"` (inline) > `QTextEdit { font-family: Arial }` (widget)
- This ensures code fonts are never overridden

### Widget-Level Protection  
For non-HTML text widgets:
- Set monospace fonts programmatically via `widget.setFont()`
- Use style templates that don't specify font-family
- Let Qt's font inheritance handle the rest

## Result
Code snippets now maintain their monospace fonts consistently across all theme changes while still receiving proper theme colors for backgrounds and text.