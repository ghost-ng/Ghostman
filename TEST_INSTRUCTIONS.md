# Test Instructions - Tab Sandboxing Fix

## CRITICAL: You MUST Restart the App

**The changes will NOT work until you completely restart Ghostman!**

1. Close Ghostman completely
2. Start Ghostman fresh
3. Then follow the test steps below

## Test Steps

### Test 1: Basic Tab Switching

1. **In Tab 1**: Type "Hello from Tab 1" and send
2. **Create Tab 2**: Click the + button
3. **In Tab 2**: Type "Hello from Tab 2" and send
4. **Switch back to Tab 1**: Click Tab 1 button

**Expected:** You should see "Hello from Tab 1" message still visible

**If it fails:** Content will be erased/empty

### Test 2: File Isolation

1. **In Tab 1**: Upload a file (any .txt or .py file)
2. **Create Tab 2**: Click the + button
3. **In Tab 2**: Upload a DIFFERENT file
4. **Switch back to Tab 1**: Click Tab 1 button

**Expected:**
- Tab 1 shows only the first file
- Tab 2 shows only the second file
- Files don't leak between tabs

**If it fails:** Files will be mixed or disappear

## What to Look For in Logs

After restarting and testing, check the log file:
```
C:\Users\miguel\AppData\Roaming\Ghostman\logs\ghostman.log
```

Look for these messages when switching tabs:

### ✅ GOOD SIGNS (Fix is Working):
```
💾 SAVED output cache for tab tab-xxxx (12345 chars)
📥 RESTORED output cache for tab tab-yyyy (67890 chars)
⏭️⏭️⏭️ TAB MANAGER ACTIVE - SKIPPING CONVERSATION RELOAD (using cached state) ⏭️⏭️⏭️
✅ Updated conversation reference (cache preserved)
```

### ❌ BAD SIGNS (Fix Not Working):
```
Switched to conversation context: [title]
_load_conversation_messages
_switch_to_conversation
output_display.clear()
```

## If It Still Doesn't Work

Run this command to see the last 100 tab-related log lines:

```bash
tail -500 /c/Users/miguel/AppData/Roaming/Ghostman/logs/ghostman.log | grep -i "SAVED\|RESTORED\|TAB MANAGER\|switch" | tail -100
```

Copy and paste the output so I can see what's happening.

## Quick Checklist

- [ ] Completely closed Ghostman
- [ ] Restarted Ghostman
- [ ] Tested tab switching
- [ ] Checked logs for "SAVED" and "RESTORED" messages
- [ ] Checked logs for "TAB MANAGER ACTIVE" message

If you don't see those messages, the new code isn't running!
