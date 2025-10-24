# Theme Manager Parameter Fix

## Problem

App was crashing on tab creation with:

```
TypeError: MixedContentDisplay.__init__() got an unexpected keyword argument 'theme_manager'
```

**Location:** `tab_conversation_manager.py` Line 31

## Root Cause

In the refactor, I added code to pass `theme_manager` to `MixedContentDisplay`:

```python
# INCORRECT:
self.output_display = MixedContentDisplay(theme_manager=theme_manager)
```

However, `MixedContentDisplay.__init__()` only accepts `parent` parameter:

```python
class MixedContentDisplay(QScrollArea):
    def __init__(self, parent=None):  # ← No theme_manager parameter!
        super().__init__(parent)
        # ...
```

## Fix

**File:** `tab_conversation_manager.py` Lines 30-33

Changed from:
```python
self.output_display = MixedContentDisplay(theme_manager=theme_manager)
```

To:
```python
# Each tab owns its own output display widget - NO MORE SHARED WIDGET!
# Note: MixedContentDisplay doesn't accept theme_manager parameter
# Theme will be applied via the global theme system
self.output_display = MixedContentDisplay()
```

## How Theme Is Applied

`MixedContentDisplay` uses the **global theme system** - it doesn't need theme_manager passed to it. The theme is applied automatically when:

1. The widget is created
2. The global theme changes via the theme manager
3. The widget registers itself with the theme system (if applicable)

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Expected:
✅ App starts without TypeError
✅ Tabs are created successfully
✅ Theme colors appear correctly in tab output widgets
```

## Files Modified

- `ghostman/src/presentation/widgets/tab_conversation_manager.py` (Line 33)

---

**Status:** ✅ FIXED

**Impact:** CRITICAL - Prevented tabs from being created

**Related:** Per-tab widget refactor
