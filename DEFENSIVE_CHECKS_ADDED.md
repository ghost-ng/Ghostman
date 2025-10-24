# Defensive Checks Added - CRITICAL FIX

## Problem

After the per-tab widget refactor, the app was crashing on startup with:

```
AttributeError: 'NoneType' object has no attribute 'clear'
AttributeError: 'NoneType' object has no attribute 'add_html_content'
AttributeError: 'NoneType' object has no attribute 'add_plain_text'
```

**Root Cause:** Code was trying to use `self.output_display` before any tabs were created during the startup flow.

**Timeline:**
1. App starts
2. `_init_ui()` runs (no tabs created yet)
3. `_load_conversations_deferred()` runs
4. Code tries to call `self.clear_output()` or `self.append_output()`
5. `self.output_display` property returns `None` (no tabs exist)
6. **CRASH** trying to call methods on `None`

## Fix Applied

Added defensive checks to all methods that access `self.output_display`:

### 1. `append_output()` - Lines 7701-7704

```python
def append_output(self, text: str, style: str = "normal", force_plain: bool = False):
    # Defensive check: if no output_display (no tabs yet), skip silently
    if not self.output_display:
        logger.debug(f"Skipping output append - no tabs created yet: {text[:50]}")
        return

    # ... rest of method
```

**Also added** check in exception handler (Line 7725):
```python
except Exception as e:
    logger.error(f"Error rendering output: {e}")
    # Fallback to plain text rendering - check again if output_display exists
    if self.output_display:
        self.output_display.add_plain_text(str(text), style)
```

### 2. `clear_output()` - Lines 7742-7745

```python
def clear_output(self):
    """Clear the output display and reset markdown renderer cache."""
    # Defensive check: if no output_display (no tabs yet), skip
    if not self.output_display:
        logger.debug("Skipping clear_output - no tabs created yet")
        return

    self.output_display.clear()
    # ...
```

### 3. `_manage_document_size()` - Lines 7733-7735

```python
def _manage_document_size(self):
    """Manage document size for performance in long conversations."""
    # Defensive check: if no output_display, skip
    if not self.output_display:
        return

    self.output_display.manage_content_size(max_widgets=500)
```

### 4. `get_render_stats()` - Lines 7772-7773

```python
stats = {
    'content_widgets': len(self.output_display.content_widgets) if self.output_display and hasattr(self.output_display, 'content_widgets') else 0,
    'content_height': self.output_display.get_content_height() if self.output_display and hasattr(self.output_display, 'get_content_height') else 0,
    'markdown_available': MARKDOWN_AVAILABLE
}
```

### 5. `_highlight_current_match()` - Line 10331

```python
# MixedContentDisplay doesn't support text highlighting like QTextEdit
# Scroll to bottom as a simple fallback
if self.output_display:
    self.output_display.scroll_to_bottom()
```

## Behavior

**Before tabs exist:**
- `append_output()` → Logs debug message, returns early ✅
- `clear_output()` → Logs debug message, returns early ✅
- Other methods → Silently skip operations ✅

**After tabs are created:**
- All methods work normally ✅

## Why This Happens

The old architecture created `self.output_display = MixedContentDisplay()` during `_init_ui()`, so it always existed.

The new architecture creates output displays per-tab, so `self.output_display` is a property that returns the active tab's widget. Before tabs exist, it returns `None`.

**This is the correct behavior** - we just needed to add defensive checks to handle it gracefully.

## Testing

```bash
# Start Ghostman
python ghostman/src/main.py

# Expected behavior:
✅ App starts without crashes
✅ No AttributeError exceptions
✅ Debug logs show "Skipping output append - no tabs created yet" (normal)
✅ Once tabs are created, output works normally
```

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py`
  - `append_output()` - Added None check (Lines 7701-7704, 7725)
  - `clear_output()` - Added None check (Lines 7742-7745)
  - `_manage_document_size()` - Added None check (Lines 7733-7735)
  - `get_render_stats()` - Added None check (Lines 7772-7773)
  - `_highlight_current_match()` - Added None check (Line 10331)

---

**Status:** ✅ FIXED

**Impact:** CRITICAL - Prevents startup crashes

**Related:**
- [PER_TAB_WIDGET_REFACTOR_COMPLETE.md](PER_TAB_WIDGET_REFACTOR_COMPLETE.md)
- [STARTUP_ERRORS_FIXED.md](STARTUP_ERRORS_FIXED.md)
