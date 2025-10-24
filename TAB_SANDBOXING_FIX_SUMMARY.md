# Tab Sandboxing Fix - Complete Summary

## Overview
Fixed critical bugs in the tabbed conversation system that prevented proper tab sandboxing. Each tab now functions as an independent sandbox with its own conversation, files, and UI state.

## Issues Fixed

### 1. ✅ New Tab Creates Conversation in ALL Tabs
**Problem:** Creating a new tab cleared conversations and files in ALL tabs.

**Root Cause:** `_on_conversation_context_switched()` called `_clear_current_conversation()` which cleared global state affecting all tabs.

**Solution:**
- Modified `_on_conversation_context_switched()` to only update conversation references without clearing state
- Tab manager now handles all per-tab state restoration

### 2. ✅ File Browser State Not Preserved Per Tab
**Problem:** File browser visibility not tracked per tab, closed when switching tabs even if user had it open.

**Solution:**
- Added `file_browser_visible` attribute to `ConversationTab` class
- Tab manager saves/restores file browser visibility state on tab switch
- File browser auto-opens when files are present, stays closed when no files

### 3. ✅ Files Not Isolated Per Tab
**Problem:** Files shown by conversation_id instead of tab_id, could leak between tabs.

**Solution:**
- Ensured `tab_id` is always retrieved and passed when adding files
- Tab manager uses `show_files_for_tab()` instead of `show_files_for_conversation()`
- Files now properly filtered by tab_id

### 4. ✅ Tab Hover Transparency Issue
**Problem:** Inactive tabs had transparent hover state, hard to see which tab you're hovering over.

**Solution:**
- Updated `get_conversation_tab_button_style()` in `style_templates.py`
- Added `border: 2px solid {colors.primary}` on hover for inactive tabs
- Theme-aware colored outline provides clear visual feedback

### 5. ✅ Tab Limit Not Enforced
**Problem:** Users could create unlimited tabs, degrading performance.

**Solution:**
- Added MAX_TABS = 6 limit to `create_tab()` method
- Shows warning message when limit reached
- User must close a tab to create a new one

---

## Files Modified

### 1. `ghostman/src/presentation/widgets/tab_conversation_manager.py`

#### Changes:
- **Added per-tab state storage** (Lines 27-31):
  ```python
  self.output_cache: str = ""  # Cached HTML output content
  self.file_ids: List[str] = []  # Files associated with THIS tab
  self.scroll_position: int = 0  # Remember scroll position
  self.file_browser_visible: bool = False  # File browser visibility state
  ```

- **Added tab limit enforcement** (Lines 102-112):
  ```python
  MAX_TABS = 6
  if len(self.tabs) >= MAX_TABS:
      logger.warning(f"Tab limit reached ({MAX_TABS} tabs). Cannot create more tabs.")
      return None
  ```

- **Added save/restore logic in `switch_to_tab()`** (Lines 205-296):
  - Saves old tab: output cache, scroll position, file browser visibility
  - Restores new tab: output content, scroll position, files, file browser state
  - Auto-opens file browser if files present, closes if no files

### 2. `ghostman/src/presentation/widgets/repl_widget.py`

#### Changes:
- **Fixed `_on_conversation_context_switched()`** (Line 10298):
  - Removed call to `_clear_current_conversation()`
  - Only updates conversation references without clearing state
  - Tab manager handles all state restoration

- **Deprecated `_clear_current_conversation()`** (Line 10376):
  - Removed global state clearing (output, files, file browser)
  - Only updates conversation references
  - Tab manager now handles per-tab clearing

- **Simplified `_on_tab_switched()`** (Line 10485):
  - Removed duplicate logic
  - Tab manager already handles all state restoration
  - Method now just logs the switch

- **Fixed `tab_id` propagation in `_process_uploaded_files()`** (Line 3919):
  - Gets tab_id BEFORE processing files
  - Consistently passes `tab_id` to `add_file()`
  - Added logging to verify tab_id propagation

- **Fixed critical bug in `_process_files_async()`** (Line 4988):
  - Moved conversation_id retrieval BEFORE using it
  - Fixed order of operations to prevent NameError
  - Ensured file browser bar receives valid conversation_id

### 3. `ghostman/src/ui/themes/style_templates.py`

#### Changes:
- **Updated inactive tab hover styling** (Lines 1512-1519):
  ```python
  QPushButton:hover {
      background-color: {inactive_bg_color} !important;
      color: {colors.text_primary} !important;
      border: 2px solid {colors.primary} !important;  /* Visible outline */
      font-weight: bold;
      height: 36px !important;
      cursor: pointer !important;
  }
  ```

- **Updated inactive tab pressed styling** (Lines 1520-1526):
  ```python
  QPushButton:pressed {
      background-color: {colors.interactive_active} !important;
      border: 2px solid {colors.primary_hover} !important;  /* Visible outline */
      outline: none !important;
      padding: 8px 10px !important;
      height: 36px !important;
  }
  ```

---

## Architecture Changes

### Before (Broken)
```
┌─────────────────────────────────────────┐
│          REPL Widget (Global)           │
│                                         │
│  Shared State (ALL TABS):               │
│  - output_display                       │
│  - current_conversation                 │
│  - _uploaded_files                      │
│                                         │
│  Tab Manager:                           │
│  - tabs{} (only UI buttons)             │
│  - active_tab_id                        │
│                                         │
│  ❌ Creating new tab cleared ALL tabs   │
│  ❌ Files shown by conversation not tab │
│  ❌ No per-tab state preservation       │
└─────────────────────────────────────────┘
```

### After (Fixed)
```
┌──────────────────────────────────────────────┐
│           REPL Widget (Global)               │
│                                              │
│  Global Display (swapped on tab switch):    │
│  - output_display (shows active tab cache)  │
│  - file_browser_bar (shows active tab files)│
│                                              │
│  Tab Manager:                                │
│  ┌─────────────────────────────────────┐    │
│  │ Tab 1: ConversationTab               │    │
│  │  - output_cache: str                 │    │
│  │  - file_ids: [...]                   │    │
│  │  - scroll_position: int              │    │
│  │  - file_browser_visible: bool        │    │
│  │  - conversation_id: str              │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │ Tab 2: ConversationTab               │    │
│  │  - output_cache: str                 │    │
│  │  - file_ids: [...]                   │    │
│  │  - scroll_position: int              │    │
│  │  - file_browser_visible: bool        │    │
│  │  - conversation_id: str              │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  ✅ Each tab has independent state           │
│  ✅ Files filtered by tab_id                 │
│  ✅ State saved/restored on switch           │
│  ✅ Max 6 tabs enforced                      │
└──────────────────────────────────────────────┘
```

---

## Flow Diagrams

### Tab Creation Flow (Fixed)
```
User clicks "New Tab"
    │
    ├─> Check tab limit (max 6)
    │     ├─> If at limit: Show warning, return None
    │     └─> If under limit: Continue
    │
    ├─> Create ConversationTab object
    │     ├─> Initialize: output_cache = ""
    │     ├─> Initialize: file_ids = []
    │     ├─> Initialize: scroll_position = 0
    │     └─> Initialize: file_browser_visible = False
    │
    ├─> Create tab button UI
    │
    └─> Switch to new tab
          ├─> SAVE old tab state
          │     ├─> output_cache = output_display.toHtml()
          │     ├─> scroll_position = scrollbar.value()
          │     ├─> file_browser_visible = browser.isVisible()
          │     └─> file_ids (already tracked)
          │
          ├─> UPDATE active tab ID
          │
          └─> RESTORE new tab state
                ├─> output_display.setHtml(output_cache)
                ├─> scrollbar.setValue(scroll_position)
                ├─> file_browser_bar.show_files_for_tab(tab_id)
                └─> Set file_browser visibility (auto-open if files present)
```

### File Upload Flow (Fixed)
```
User uploads files
    │
    ├─> Get active tab ID
    │     └─> current_tab_id = tab_manager.get_active_tab().tab_id
    │
    ├─> Get/create conversation ID for tab
    │     └─> Ensure conversation exists before processing files
    │
    ├─> Process each file
    │     ├─> Read file content
    │     ├─> Generate embeddings
    │     └─> Add to file browser bar
    │           └─> file_browser_bar.add_file(
    │                 file_id, filename, ...,
    │                 conversation_id=conv_id,
    │                 tab_id=current_tab_id  ✅ ALWAYS PASSED
    │               )
    │
    └─> File browser auto-opens (files present)
```

### Tab Switching Flow (Fixed)
```
User clicks different tab
    │
    ├─> Tab Manager: switch_to_tab(new_tab_id)
    │     │
    │     ├─> SAVE old tab state
    │     │     ├─> output_cache = output_display.toHtml()
    │     │     ├─> scroll_position = scrollbar.value()
    │     │     └─> file_browser_visible = browser.isVisible()
    │     │
    │     ├─> UPDATE active tab ID
    │     │
    │     ├─> RESTORE new tab state
    │     │     ├─> output_display.setHtml(new_tab.output_cache)
    │     │     ├─> scrollbar.setValue(new_tab.scroll_position)
    │     │     ├─> file_browser_bar.show_files_for_tab(new_tab_id)
    │     │     └─> Set file_browser visibility
    │     │           ├─> If files present: setVisible(True)
    │     │           └─> If no files: setVisible(False)
    │     │
    │     ├─> Emit: tab_switched(old_id, new_id)
    │     └─> Emit: conversation_context_switched(conv_id)
    │
    └─> REPL Widget: _on_tab_switched()
          └─> Just logs (tab manager already handled everything)
```

---

## Testing Checklist

### Critical Tests
- [x] ✅ Create Tab 1, add content, create Tab 2 → Tab 1 content preserved
- [x] ✅ Upload files in Tab 1, switch to Tab 2, upload different files → Files isolated
- [x] ✅ Create 3 tabs with different content → Each tab maintains its state
- [x] ✅ Switch between tabs rapidly → No crashes, no state corruption
- [x] ✅ Create 6 tabs → 7th tab creation shows warning
- [x] ✅ Hover over inactive tabs → Colored outline appears

### Edge Cases
- [x] ✅ Create new tab with existing tab having files → New tab starts with no files
- [x] ✅ Upload files then switch tabs immediately → Files appear in correct tab
- [x] ✅ Close middle tab → Other tabs unaffected
- [x] ✅ Switch tabs while file upload in progress → Upload completes in correct tab
- [x] ✅ File browser open in Tab 1, switch to Tab 2 with no files → Browser closes
- [x] ✅ File browser closed in Tab 1, switch to Tab 2 with files → Browser opens

---

## Benefits

### Performance
- ✅ Tab limit (6) prevents memory bloat
- ✅ Only active tab's output rendered (cached for others)
- ✅ File filtering by tab_id more efficient

### User Experience
- ✅ Clear tab hover feedback (colored outline)
- ✅ Each tab independent - no cross-contamination
- ✅ File browser auto-opens when needed
- ✅ Tab switching preserves exact state

### Maintainability
- ✅ Clean separation of concerns (tab manager handles state)
- ✅ Deprecated global state clearing methods
- ✅ Clear logging for debugging
- ✅ Type hints for tab state fields

---

## Known Limitations

1. **Conversation Loading:** Any existing conversation can be recalled into the active tab, which is the intended behavior per user requirements.

2. **File Browser State:** File browser defaults to closed for new tabs, but auto-opens when files are present as requested.

3. **Tab Limit:** Fixed at 6 tabs. If user needs more, the constant MAX_TABS can be adjusted in `create_tab()` method.

---

## Future Enhancements

### Potential Improvements
1. **Tab Reordering:** Drag-and-drop to reorder tabs
2. **Tab Persistence:** Save/restore tabs across app sessions
3. **Tab Duplication:** Duplicate tab with same conversation/files
4. **Tab Context Menu:** Add "Rename Tab", "Close Others", "Close All to Right"
5. **Tab Icons:** Add status icons (processing, error, unread)
6. **Tab Tooltips:** Show conversation summary on hover

### Configuration Options
1. **Configurable Tab Limit:** User setting for max tabs (default 6)
2. **File Browser Behavior:** User preference for default visibility
3. **Tab Switching Animation:** Optional smooth transitions
4. **Tab Memory:** Configurable output cache size per tab

---

## Migration Notes

### For Existing Users
- No migration needed - changes are backward compatible
- Existing conversations will load into tabs normally
- Files will be automatically associated with their tabs on first upload

### For Developers
- `_clear_current_conversation()` is now deprecated - use tab manager methods
- Always pass `tab_id` when calling `file_browser_bar.add_file()`
- Use `show_files_for_tab()` instead of `show_files_for_conversation()`
- Tab state is now managed by `TabConversationManager`, not `REPLWidget`

---

## Summary

All critical bugs have been fixed:
1. ✅ Creating new tabs no longer clears other tabs
2. ✅ File browser state preserved per tab
3. ✅ Files properly isolated to their tab
4. ✅ Tab hover styling provides clear feedback
5. ✅ Tab limit enforced (max 6 tabs)
6. ✅ File browser auto-opens when files present
7. ✅ Critical async file processing bug fixed

The tabbed conversation system now functions as a proper sandbox where each tab maintains complete independence from other tabs.