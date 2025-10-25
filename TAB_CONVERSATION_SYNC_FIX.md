# Tab Conversation Sync Fix

## Problem

When switching tabs, the conversation context in the AI service was correct, but `self.current_conversation` was not being updated. This caused the `send_message()` method to override the correct conversation ID with the wrong one.

### Symptoms

**User Report:** "I uploaded a requirements.txt file but the logs show it's reviewing for a single file, and the results exclude the file I uploaded in this tab"

### Root Cause Analysis

From the logs:

1. **User uploaded file to Tab 2** (conversation `4c2bb825`)
2. **User switched to Tab 1** (conversation `b68afe86`)
3. **User sent a query from Tab 1**
4. **Tab switch correctly set AI service** to conversation `b68afe86`
5. **BUT `send_message()` then overrode it** with conversation `426b20de` (old `self.current_conversation.id`)

The flow:

```python
# In _on_tab_switched() (line 10686)
ai_service.set_current_conversation(new_conversation_id)  # ✅ Correctly set to b68afe86

# But self.current_conversation was NOT updated! ❌

# Later in send_message() (line 8108-8109)
if current_ai_conversation != self.current_conversation.id:
    ai_service.set_current_conversation(self.current_conversation.id)  # ❌ Overrides with wrong ID!
```

This caused:
- **Tab 1's query** used **conversation `426b20de`** instead of `b68afe86`
- **File uploads in Tab 2** were associated with conversation `4c2bb825`
- **RAG query from Tab 1** checked conversation `b68afe86` → found 0 files
- **Actual files were in** conversation `4c2bb825` (Tab 2)

### Evidence from Logs

```
2025-10-24 19:25:47,319 - ghostman.repl_widget - INFO - 🔄 Syncing AI service conversation context: 1c3772a1... -> 426b20de...
                                                                                                                    ^^^^^^^^
                                                                                                                    Wrong ID!

2025-10-24 19:26:02,630 - ghostman.repl_widget - INFO -    ✅ Conversation 4c2bb825 → Tab tab-7642adbd
                                                                              ^^^^^^^^
                                                                              Tab 2's conversation (where file was uploaded)

2025-10-24 19:26:03,185 - ghostman.repl_widget - INFO - 🔄 TAB SWITCH: tab-7642adbd → tab-a8986feb
                                                                        ^^^^^^^^^^^    ^^^^^^^^^^^^^
                                                                        Tab 2          Tab 1

2025-10-24 19:26:47,327 - ghostman.repl_widget - INFO -   - conversation_id: b68afe86
                                                                              ^^^^^^^^
                                                                              Tab 1's conversation (queried for files)

2025-10-24 19:26:47,327 - ghostman.repl_widget - INFO -   - File count result: 0
                                                                              ^
                                                                              No files! (Files were in 4c2bb825, not b68afe86)
```

## Fix

**File:** `repl_widget.py` Lines 10681-10712

Updated `_on_tab_switched()` to also update `self.current_conversation` when switching tabs:

**BEFORE:**
```python
# Switch the conversation context in the AI service
if new_conversation_id and self.conversation_manager:
    try:
        ai_service = self.conversation_manager.get_ai_service()
        if ai_service:
            ai_service.set_current_conversation(new_conversation_id)
            logger.info(f"✅ AI service conversation context switched to: {new_conversation_id[:8]}")
        else:
            logger.warning("AI service not available for conversation switch")
    except Exception as conv_error:
        logger.error(f"Failed to switch AI service conversation: {conv_error}")
else:
    if not new_conversation_id:
        logger.info("📁 No conversation ID - updating references only (tab manager handles state)")
    if not self.conversation_manager:
        logger.warning("No conversation manager available")
```

**AFTER:**
```python
# Switch the conversation context in the AI service AND update self.current_conversation
if new_conversation_id and self.conversation_manager:
    try:
        ai_service = self.conversation_manager.get_ai_service()
        if ai_service:
            ai_service.set_current_conversation(new_conversation_id)
            logger.info(f"✅ AI service conversation context switched to: {new_conversation_id[:8]}")

            # CRITICAL: Update self.current_conversation to match the tab's conversation
            # This ensures send_message() uses the correct conversation ID
            try:
                conversation_service = self.conversation_manager.conversation_service
                if conversation_service:
                    conversation_obj = conversation_service.get_conversation(new_conversation_id)
                    if conversation_obj:
                        self.current_conversation = conversation_obj
                        logger.info(f"✅ Updated self.current_conversation to match tab conversation: {new_conversation_id[:8]}")
                    else:
                        logger.warning(f"⚠️ Could not load conversation object for {new_conversation_id[:8]}")
            except Exception as conv_load_error:
                logger.error(f"Failed to load conversation object: {conv_load_error}")
        else:
            logger.warning("AI service not available for conversation switch")
    except Exception as conv_error:
        logger.error(f"Failed to switch AI service conversation: {conv_error}")
else:
    if not new_conversation_id:
        logger.info("📁 No conversation ID - updating references only (tab manager handles state)")
        # Clear current_conversation if no conversation for this tab
        self.current_conversation = None
    if not self.conversation_manager:
        logger.warning("No conversation manager available")
```

## How It Works Now

### When Switching Tabs:

1. Get new tab's conversation ID from tab manager
2. Set AI service to use that conversation ID ✅
3. **Load the conversation object from database** ✅ NEW!
4. **Update `self.current_conversation`** to match the tab ✅ NEW!

### When Sending Messages:

1. Check if AI service conversation matches `self.current_conversation.id`
2. Since we now update `self.current_conversation` during tab switch, they match ✅
3. No override happens - correct conversation is used! ✅

## Expected Behavior

**Before Fix:**
1. Upload file to Tab 2 (conversation `4c2bb825`)
2. Switch to Tab 1 (conversation `b68afe86`)
3. Send query from Tab 1
4. Query uses **wrong conversation** (`426b20de`) ❌
5. RAG check looks for files in `b68afe86` → finds 0
6. Files were actually in `4c2bb825`
7. **Result: File context not included in query** ❌

**After Fix:**
1. Upload file to Tab 2 (conversation `4c2bb825`)
2. Switch to Tab 1 (conversation `b68afe86`)
3. **`self.current_conversation` updated to `b68afe86`** ✅
4. Send query from Tab 1
5. Query uses **correct conversation** (`b68afe86`) ✅
6. RAG check looks for files in `b68afe86` → finds 0 (correctly!)
7. **Result: Correct tab isolation** ✅

**OR if querying from Tab 2 (where file was uploaded):**
1. Upload file to Tab 2 (conversation `4c2bb825`)
2. Stay on Tab 2
3. Send query from Tab 2
4. Query uses **correct conversation** (`4c2bb825`) ✅
5. RAG check looks for files in `4c2bb825` → **finds requirements.txt!** ✅
6. **Result: File context included in query** ✅

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Test scenario:
1. Create Tab 1 (auto-created)
2. Create Tab 2
3. Upload requirements.txt to Tab 2
4. Send query from Tab 2 → Should find file ✅
5. Switch to Tab 1
6. Send query from Tab 1 → Should NOT find file (correct isolation) ✅
7. Switch back to Tab 2
8. Send query from Tab 2 → Should find file again ✅
```

## Logs to Look For

When switching tabs, you should now see:
```
✅ AI service conversation context switched to: <tab_conv_id>
✅ Updated self.current_conversation to match tab conversation: <tab_conv_id>
```

When sending messages, the sync log should either:
- **Not appear** (because IDs already match) ✅
- **OR show matching IDs** (no override) ✅

You should **NOT** see:
```
🔄 Syncing AI service conversation context: <id1> -> <different_id2>
```
Unless you're genuinely switching conversations outside of tabs.

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py` (Lines 10681-10712)
  - Added conversation object loading in `_on_tab_switched()`
  - Update `self.current_conversation` to match tab's conversation
  - Clear `self.current_conversation` if no conversation for tab

---

**Status:** ✅ FIXED

**Impact:** HIGH - Tab conversation isolation now works correctly

**Related:** Per-tab widget refactor, conversation isolation

**This ensures each tab's queries and file uploads are properly isolated by conversation.**
