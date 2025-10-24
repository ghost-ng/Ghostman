# Theme Colors Fix

## Problem

After the refactor, the REPL output area was not using the correct theme colors. It appeared with default/wrong colors instead of being theme-aware.

## Root Cause

`MixedContentDisplay` requires manual theme color application - it doesn't automatically register with the theme manager.

From the code comments in `mixed_content_display.py` lines 81-83:

```python
# NOTE: MixedContentDisplay is NOT registered with theme manager
# The REPL widget manually passes opacity-adjusted colors to this widget
# This prevents double updates and ensures proper opacity handling
```

**The Problem:** When we refactored to create a `MixedContentDisplay` per tab, we weren't calling `set_theme_colors()` on each new tab's output widget.

## Fix

**File:** `repl_widget.py` Lines 10751-10759

Added theme color application in the `_on_tab_created()` handler, right after link handling setup:

```python
# Apply theme colors to the tab's output widget
if hasattr(self, 'theme_manager') and self.theme_manager:
    try:
        theme_colors = self.theme_manager.get_current_theme_colors()
        if theme_colors:
            tab.output_display.set_theme_colors(theme_colors)
            logger.info(f"   ✅ Theme colors applied to tab widget")
    except Exception as e:
        logger.warning(f"   ⚠️ Failed to apply theme colors: {e}")
```

## Result

**Before:**
- Tab created
- Output widget uses default colors ❌
- Not theme-aware ❌

**After:**
- Tab created
- Theme colors fetched from theme_manager ✅
- `set_theme_colors()` called on output widget ✅
- Output widget properly themed ✅
- Respects user's theme selection ✅

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Expected:
✅ REPL output area uses current theme colors
✅ Text is readable with proper contrast
✅ Matches the rest of the UI theme
✅ If you change theme, new tabs get new theme colors
```

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py` (Lines 10751-10759)

---

**Status:** ✅ FIXED

**Impact:** HIGH - Affects visual consistency and readability
