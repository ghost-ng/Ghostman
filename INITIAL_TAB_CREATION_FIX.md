# Initial Tab Creation Fix - No Output Displayed

## Problem

After the refactor, AI responses were being received successfully but **NOT displayed** in the REPL.

**Logs showed:**
```
✓ AI response received with context (context size: 2 messages)
✓ Message sent successfully
Response length: 376
```

But the REPL remained empty - no output was shown to the user.

## Root Cause

**No tabs were being created during startup!**

### The Flow:

1. App starts
2. `_init_ui()` creates TabConversationManager with `create_initial_tab=False`
3. No tabs exist yet
4. User sends a message
5. AI response comes back
6. `append_output()` is called
7. `self.output_display` property returns `None` (no active tab)
8. Defensive check: `if not self.output_display: return` ← Output is skipped!
9. User sees nothing 😞

### Why No Tabs Were Created:

Looking at the code:

**Line 2496** in `repl_widget.py`:
```python
self.tab_manager = TabConversationManager(
    self,
    self.tab_frame,
    self.tab_layout,
    output_container_layout=parent_layout,
    create_initial_tab=False  # ← NO INITIAL TAB!
)
```

**`_create_new_tab()`** is only called when user clicks "New Tab" button - not automatically during startup.

**Result:** The app started with **zero tabs**, so there was nowhere to display output!

## Fix

**Added automatic initial tab creation** after conversations are loaded.

**File:** `repl_widget.py` Lines 2387-2398

**Added to `_load_conversations()` method:**

```python
logger.info(f"📋 Loaded {len(conversations)} conversations")

# Create initial tab if tab manager exists and no tabs created yet
if hasattr(self, 'tab_manager') and self.tab_manager and len(self.tab_manager.tabs) == 0:
    logger.info("Creating initial tab for current conversation...")
    # Determine tab title from current conversation
    if self.current_conversation and self.current_conversation.title:
        tab_title = self.current_conversation.title[:23] + "..." if len(self.current_conversation.title) > 25 else self.current_conversation.title
    else:
        tab_title = "New Conversation"

    # Create and activate the first tab
    first_tab_id = self.tab_manager.create_tab(title=tab_title, activate=True)
    logger.info(f"✅ Created initial tab: {first_tab_id}")
```

## Behavior

### Before Fix:
1. App starts
2. Zero tabs created
3. `self.output_display` returns `None`
4. AI responses received but not displayed ❌

### After Fix:
1. App starts
2. Conversations loaded
3. **Initial tab automatically created** ✅
4. Tab is activated
5. `self.output_display` returns active tab's widget ✅
6. AI responses displayed properly ✅

## Expected Logs

When the app starts, you should now see:

```
📋 Loaded 20 conversations
Creating initial tab for current conversation...
🆕 CREATING NEW TAB
   Tab ID: tab-abc12345
   ✅ Tab object created with its own output display widget
   📺 Added tab's output widget to QStackedWidget
✅ Created initial tab: tab-abc12345
💬 CREATING NEW CONVERSATION FOR TAB
   ✅ Link handling and context menu configured for tab widget
   ✅ NEW REPL SESSION READY
```

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Expected behavior:
✅ App starts with 1 tab visible at top
✅ Tab shows conversation title or "New Conversation"
✅ Send a message to AI
✅ AI response appears in REPL output area
✅ Can see and interact with the response
```

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py` (Lines 2387-2398)
  - Added automatic initial tab creation in `_load_conversations()`
  - Tab created after conversations are loaded
  - Uses current conversation title if available

---

**Status:** ✅ FIXED

**Impact:** CRITICAL - Users couldn't see AI responses without this fix

**Related:** Per-tab widget refactor
