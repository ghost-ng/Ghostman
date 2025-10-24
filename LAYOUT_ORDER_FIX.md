# Layout Order Fix - Input Window Pushed to Bottom

## Problem

After the refactor, the UI layout was completely broken:
- Output area took up almost all vertical space
- Input window was pushed to the very bottom
- User couldn't see or use the input properly

**Visual:** The teal/cyan output box expanded to fill the entire window, pushing the "Send" button and input area to the bottom edge.

## Root Cause

The `QStackedWidget` (output_stack) was being added to the layout in the WRONG position.

### Original Flow:
```
_init_ui():
  1. layout = QVBoxLayout()
  2. _init_tab_bar(layout)
       - Adds tab_frame to layout
       - Creates TabConversationManager
       - TabConversationManager adds output_stack to layout ← PROBLEM! Added here!
  3. _init_title_bar(layout)
       - Adds title_bar to layout
  4. (old output_display was added here)
  5. _init_search_bar(layout)
  6. _init_file_browser_bar(layout)
  7. Input area added to layout
```

**Result:** Layout order was:
1. tab_frame (tab buttons)
2. **output_stack** ← WRONG! Should be after title bar!
3. title_bar
4. search_bar
5. file_browser_bar
6. input_area

The output_stack was inserted BEFORE the title bar, completely breaking the visual layout.

## Fix

**Changed:** Don't add output_stack to layout inside `TabConversationManager.__init__()`. Instead, let REPLWidget add it in the correct position.

### File 1: `tab_conversation_manager.py` (Lines 86-94)

**BEFORE:**
```python
self.output_stack = QStackedWidget()
self.output_stack.setMinimumHeight(300)

if output_container_layout:
    self.output_container_layout = output_container_layout
    # Add with stretch factor of 1 to take available vertical space
    output_container_layout.addWidget(self.output_stack, 1)  # ❌ WRONG POSITION!
```

**AFTER:**
```python
self.output_stack = QStackedWidget()
self.output_stack.setMinimumHeight(300)

# NOTE: We create the QStackedWidget here but DON'T add it to the layout yet
# The parent (REPLWidget) will add it in the correct position in its layout
# This ensures proper ordering: tab_bar → title_bar → output_stack → input
self.output_container_layout = output_container_layout
```

### File 2: `repl_widget.py` (Lines 6531-6535)

**ADDED** after title bar init, where old output_display used to be:

```python
# Output display - NOW HANDLED BY TAB MANAGER!
# Each tab owns its own MixedContentDisplay widget in the TabManager's QStackedWidget

# Add the tab manager's QStackedWidget to the layout in the correct position
# This replaces the old self.output_display widget
if self.tab_manager and hasattr(self.tab_manager, 'output_stack'):
    layout.addWidget(self.tab_manager.output_stack, 1)  # Stretch factor of 1
    logger.debug("Added tab_manager.output_stack to layout")
```

## Result

**Correct layout order:**
1. tab_frame (tab buttons)
2. title_bar (conversation title, buttons)
3. **output_stack** ← CORRECT! After title bar!
4. search_bar (initially hidden)
5. file_browser_bar (initially hidden)
6. input_area (text input + Send button)

**Visual result:**
- Title bar at top ✅
- Output area takes appropriate space (stretch factor 1) ✅
- Input area visible and usable at bottom ✅
- Proper vertical distribution ✅

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Expected visual layout:
✅ Tab buttons at very top
✅ Title bar with "New Conversation" below tabs
✅ Output area (teal box) in middle - reasonable height
✅ Input text box visible at bottom
✅ "Send" button visible and accessible
✅ Can type and send messages normally
```

## Files Modified

1. `ghostman/src/presentation/widgets/tab_conversation_manager.py` (Lines 86-94)
   - Removed automatic layout addition of output_stack
   - Added comment explaining why

2. `ghostman/src/presentation/widgets/repl_widget.py` (Lines 6531-6535)
   - Added explicit layout addition of output_stack in correct position
   - Added after title bar, where old output_display used to be

---

**Status:** ✅ FIXED

**Impact:** CRITICAL - UI was completely unusable without this fix

**Related:** Per-tab widget refactor
