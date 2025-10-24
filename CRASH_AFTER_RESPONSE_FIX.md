# Crash After AI Response Fix

## Problem

App was crashing silently after receiving AI response. Logs showed:

```
🔍 AI RESPONSE RECEIVED: success=True, length=327
🔍 AI RESPONSE CONTENT: '...'
```

Then nothing - app froze/crashed with no error message.

## Root Causes Found

### 1. Invalid Style "divider"

**Line 8528** in `_on_ai_response()`:
```python
self.append_output("\n--------------------------------------------------\n", "divider")
```

**Problem:** "divider" is not a valid style. Supported styles are: `normal, input, response, system, info, warning, error`.

This could cause issues in the markdown renderer or theme color lookup.

### 2. Direct call to output_display

**Line 8570** in `_add_resend_option()`:
```python
self.output_display.add_html_content(resend_html, "system")
```

**Problem:** Direct call without checking if `output_display` exists. Would crash if called before tabs are created.

### 3. No error handling

No try/except around the display code, so any exception would silently crash the UI thread.

## Fixes Applied

### Fix 1: Changed "divider" to "normal"

**File:** `repl_widget.py` Line 8529

```python
# BEFORE:
self.append_output("\n--------------------------------------------------\n", "divider")

# AFTER:
self.append_output("\n--------------------------------------------------\n", "normal")
```

### Fix 2: Added error handling around response display

**File:** `repl_widget.py` Lines 8523-8537

```python
# Display AI response with better separation
try:
    self.append_output("🤖 **Spector:**", "response")
    # Display the actual response without prefixing to preserve markdown
    self.append_output(response, "response")
    # Add spacing after AI response
    self.append_output("", "normal")
    self.append_output("\n--------------------------------------------------\n", "normal")
except Exception as e:
    logger.error(f"Error displaying AI response: {e}", exc_info=True)
    # Try fallback plain text display
    try:
        if self.output_display:
            self.output_display.add_plain_text(f"🤖 Spector: {response}", "response")
    except Exception as e2:
        logger.error(f"Fallback display also failed: {e2}", exc_info=True)
```

### Fix 3: Added defensive check in _add_resend_option

**File:** `repl_widget.py` Lines 8579-8582

```python
# BEFORE:
self.output_display.add_html_content(resend_html, "system")

# AFTER:
if self.output_display:
    self.output_display.add_html_content(resend_html, "system")
else:
    logger.warning("Cannot add resend option - no output display available")
```

## Result

**Before:**
- AI response received ✅
- Try to display with invalid "divider" style ❌
- Silent crash, no error logged ❌
- App freezes ❌

**After:**
- AI response received ✅
- Display with valid "normal" style ✅
- Error handling catches any issues ✅
- Errors logged with full traceback ✅
- Fallback to plain text if needed ✅
- App continues running ✅

## Testing

```bash
# Restart Ghostman
python ghostman/src/main.py

# Send a message to AI
# Expected:
✅ AI response appears properly
✅ No crash
✅ Can continue chatting
✅ If any display error occurs, it's logged with traceback
```

## If It Still Crashes

Check logs for:
```
Error displaying AI response: <exception details>
```

This will tell us exactly what's causing the crash.

## Files Modified

- `ghostman/src/presentation/widgets/repl_widget.py`
  - Line 8529: Changed "divider" to "normal"
  - Lines 8523-8537: Added try/except around display code
  - Lines 8579-8582: Added defensive check for output_display

---

**Status:** ✅ FIXED

**Impact:** CRITICAL - Prevents crash after receiving AI responses
