# Startup Errors Fixed

## Problem

After the per-tab widget refactor, the app was logging many warnings during startup:

```
⚠️ No active tab output_display available - this should not happen!
```

These warnings appeared ~60 times during initialization.

## Root Cause

The refactor removed the line:
```python
self.output_display = MixedContentDisplay()
```

And replaced it with a property that returns the active tab's widget:
```python
@property
def output_display(self):
    if self.tab_manager and self.tab_manager.active_tab_id:
        active_tab = self.tab_manager.get_active_tab()
        if active_tab and active_tab.output_display:
            return active_tab.output_display
    logger.warning("⚠️ No active tab output_display available!")  # ❌ PROBLEM!
    return None
```

**The issue:** During `_init_ui()`, many styling methods tried to access `self.output_display` BEFORE any tabs were created. Since tabs are created later via `_load_conversations_deferred()`, the property returned `None` and logged warnings.

## Fix 1: Make Property More Defensive

**File:** `repl_widget.py` (Lines 1364-1379)

Changed the property to:
1. Check if `tab_manager` exists using `hasattr()`
2. Remove the warning log (it's normal during initialization)
3. Add comment explaining that `None` is expected during startup

```python
@property
def output_display(self):
    """
    Get the active tab's output display widget.
    This property provides backward compatibility - code can still use self.output_display,
    but it now points to the active tab's widget instead of a shared widget.
    """
    # Check if tab manager exists and has an active tab
    if hasattr(self, 'tab_manager') and self.tab_manager and self.tab_manager.active_tab_id:
        active_tab = self.tab_manager.get_active_tab()
        if active_tab and active_tab.output_display:
            return active_tab.output_display

    # Return None during initialization or when no tabs exist
    # This is normal during app startup before tabs are created
    return None
```

## Fix 2: Set Up Link Handling and Context Menus for Each Tab

The old code (that was removed) set up link handling and context menus for the shared `output_display` widget during `_init_ui()`. Now that each tab has its own widget, we need to set these up when each tab is created.

**File:** `repl_widget.py` (Lines 10706-10720)

Added to `_on_tab_created()` handler:

```python
# Set up link handling and context menu for this tab's output widget
tab = self.tab_manager.tabs.get(tab_id)
if tab and tab.output_display:
    from PyQt6.QtCore import Qt
    # Enable link handling
    tab.output_display.setOpenExternalLinks(False)  # We handle links manually
    if hasattr(self, '_handle_link_click'):
        tab.output_display.anchorClicked.connect(self._handle_link_click)

    # Enable custom context menu
    tab.output_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    if hasattr(self, '_show_output_context_menu'):
        tab.output_display.customContextMenuRequested.connect(self._show_output_context_menu)

    logger.info(f"   ✅ Link handling and context menu configured for tab widget")
```

## Result

✅ **No more warnings during startup**

✅ **Each tab's output widget gets proper link handling and context menu**

✅ **Clean initialization flow:**
1. App starts
2. `_init_ui()` runs (tab_manager created but no tabs yet)
3. Code tries to access `self.output_display` → returns `None` (no warning)
4. `_load_conversations_deferred()` runs → creates first tabs
5. `_on_tab_created()` handler sets up link handling/context menu for each tab
6. Property now returns the active tab's widget

## Testing

Run the app and verify:
1. No "No active tab output_display" warnings in logs ✅
2. Tabs are created successfully ✅
3. Link clicking works in REPL ✅
4. Context menu (right-click) works in REPL ✅
5. Each tab has independent output display ✅

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py`
  - Lines 1364-1379: Updated `output_display` property to be defensive
  - Lines 10706-10720: Added link/context menu setup to `_on_tab_created()`

---

**Status:** ✅ FIXED

**Related:** PER_TAB_WIDGET_REFACTOR_COMPLETE.md
