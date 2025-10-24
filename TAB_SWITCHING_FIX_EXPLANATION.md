# Tab Switching Fix - The Real Problem and Solution

## The Problem You Experienced

When you switched tabs, all content was erased and files disappeared. This happened because of a **signal timing issue** where the tab manager's state restoration was being immediately overwritten.

## Root Cause Analysis

### What Was Happening (Broken Flow)

```
User switches from Tab 1 to Tab 2
    ↓
TabManager.switch_to_tab(tab_2)
    ↓
1. SAVE Tab 1 state ✅
   - output_cache = output_display.toHtml()
   - Files saved
    ↓
2. RESTORE Tab 2 state ✅
   - output_display.setHtml(tab_2.output_cache)
   - Show Tab 2 files
    ↓
3. EMIT conversation_context_switched(tab_2.conversation_id) ✅
    ↓
4. _on_conversation_context_switched() receives signal ✅
    ↓
5. ❌ CALLS _switch_to_conversation()
    ↓
6. ❌ _switch_to_conversation() calls _load_conversation_messages()
    ↓
7. ❌ _load_conversation_messages() loads from DATABASE
    ↓
8. ❌ output_display HTML is OVERWRITTEN
    ↓
9. ❌ Your cached content is LOST!
    ↓
Result: Empty display, no files, everything erased
```

### Why This Happened

The `conversation_context_switched` signal was designed for single-conversation mode (no tabs). When tabs were added, this signal kept firing and triggering a full conversation reload from the database, which **destroyed** the cached content that the tab manager had just restored.

## The Fix

### Modified Method: `_on_conversation_context_switched()`

**File:** `ghostman/src/presentation/widgets/repl_widget.py`
**Lines:** 10307-10336

### What Changed

Added a critical check that detects if the tab manager is active. If it is, the method now:

1. ✅ **SKIPS** calling `_switch_to_conversation()`
2. ✅ **SKIPS** calling `_load_conversation_messages()`
3. ✅ **ONLY** updates the conversation reference
4. ✅ **PRESERVES** the cached content from the tab manager

### Code Explanation

```python
# CRITICAL FIX: When tab manager is active, DON'T reload conversation
# Tab manager already restored the cached output/files for this tab
# Reloading would overwrite the cache with database content!
if hasattr(self, 'tab_manager') and self.tab_manager:
    logger.info(f"⏭️ Tab manager active - skipping conversation reload (using cached state)")
    # Just update the conversation reference, don't reload messages
    self._current_conversation_id = conversation_id

    # Load conversation object but DON'T call _switch_to_conversation
    if self.conversation_manager:
        async def load_conv_ref_only():
            try:
                conversation = await self.conversation_manager.get_conversation(conversation_id)
                if conversation:
                    self.current_conversation = conversation
                    self._update_status_label(conversation)
                    logger.info(f"✅ Updated conversation reference (cache preserved)")
            except Exception as e:
                logger.error(f"Failed to load conversation reference: {e}")

        # ... run async ...
    return  # ← CRITICAL: Return here, don't reload!

# If no tab manager, proceed with original behavior...
```

### The Key Insight

The tab manager **already has the correct content** in its cache. We don't need to reload from the database. We just need to:
- Update the conversation reference so the app knows which conversation is active
- Update the status label
- **NOT touch the output display or files**

## New Flow (Fixed)

```
User switches from Tab 1 to Tab 2
    ↓
TabManager.switch_to_tab(tab_2)
    ↓
1. SAVE Tab 1 state ✅
   - output_cache = output_display.toHtml()
   - Files saved
    ↓
2. RESTORE Tab 2 state ✅
   - output_display.setHtml(tab_2.output_cache)
   - Show Tab 2 files
    ↓
3. EMIT conversation_context_switched(tab_2.conversation_id) ✅
    ↓
4. _on_conversation_context_switched() receives signal ✅
    ↓
5. ✅ DETECTS tab manager is active
    ↓
6. ✅ SKIPS _switch_to_conversation()
    ↓
7. ✅ ONLY updates conversation reference
    ↓
8. ✅ output_display content PRESERVED
    ↓
9. ✅ Files remain visible
    ↓
Result: Tab 2 content exactly as you left it!
```

## How to Verify the Fix

### Run the Debug Script

```bash
python debug_tab_switching.py
```

This explains what to look for in the logs.

### Test Steps

1. **Start the app**
2. **Type "Hello from Tab 1" in the input**
3. **Send the message**
4. **Create a new tab (Tab 2)**
5. **Type "Hello from Tab 2"**
6. **Send the message**
7. **Switch back to Tab 1**

### Expected Result

✅ You should see "Hello from Tab 1" still visible
✅ The output display should show your previous messages
✅ If you had files uploaded, they should still be there

### Log Messages to Look For

When you switch tabs, you should see:

```
🔄 Switched to tab: tab-xxxx (from tab-yyyy)
Saved output cache for tab tab-yyyy
Restored output cache for tab tab-xxxx
⏭️ Tab manager active - skipping conversation reload (using cached state)
✅ Updated conversation reference (cache preserved)
```

### Bad Signs (If These Appear, Something's Wrong)

❌ `Switched to conversation context: [title]`
❌ `_load_conversation_messages` in logs
❌ `output_display.clear()` in logs
❌ Empty display after tab switch

## Why the Previous Fix Didn't Work

The previous fix focused on:
- ✅ Adding per-tab state storage (this worked)
- ✅ Saving state on tab switch (this worked)
- ✅ Restoring state on tab switch (this worked)

But it **missed** the critical issue:
- ❌ The restored state was being **immediately overwritten** by `_on_conversation_context_switched()`

It's like:
1. You carefully save your document
2. You restore it perfectly
3. But then someone immediately deletes it before you can see it!

The state was being saved and restored correctly, but the `conversation_context_switched` signal was firing **after** the restoration and triggering a database reload that destroyed the cache.

## The Complete Picture

### All Changes Working Together

1. **Tab State Storage** (in `ConversationTab`)
   - Stores output_cache, file_ids, scroll_position
   - Each tab maintains its own state

2. **Save/Restore Logic** (in `TabManager.switch_to_tab()`)
   - Saves old tab state before switching
   - Restores new tab state after switching
   - Handles file browser visibility

3. **Signal Handling Fix** (in `repl_widget.py`) ← **THIS WAS THE MISSING PIECE**
   - Detects tab manager is active
   - Skips conversation reload
   - Preserves cached content

All three parts are necessary:
- Without #1: Nothing to save/restore
- Without #2: State never saved or restored
- Without #3: **Saved state gets overwritten** ← This was your bug!

## Summary

The tab sandboxing is now fully functional. The critical fix was preventing `_on_conversation_context_switched()` from reloading the conversation when the tab manager is active, since the tab manager already restored the correct cached content.

**Try it now** - create multiple tabs, type different messages in each, upload different files, and switch between them. Each tab should maintain its own independent state!
