# Embeddings Endpoint & Unified Outlook Skills Design

**Date:** 2026-02-25
**Status:** Approved

## Overview

Two related improvements:
1. **Embeddings Endpoint** — Make RAG features work regardless of AI chat provider by separating embedding configuration from chat configuration, with proper error handling and retry logic.
2. **Unified Outlook Skills** — Consolidate 4 Outlook skills into 2 unified skills (`outlook_email`, `outlook_calendar`) with operation registries and a shared AST-validated COM sandbox for AI-generated custom operations.

---

## Part 1: Embeddings Endpoint Redesign

### Problem

The embedding endpoint currently shares `base_url` and `api_key` with the chat model. This breaks when:
- Chat provider is Anthropic (no embeddings API)
- User wants a specialized embedding model from a different provider
- Error handling is minimal (returns `None`, no retry, no actionable messages)

### Design

#### 1.1 Separate Embedding Settings

Add `embedding` section to `DEFAULT_SETTINGS` in `settings_manager.py`:

```python
'embedding': {
    'base_url': '',      # empty = inherit from ai_model.base_url
    'api_key': '',       # empty = inherit from ai_model.api_key
    'model': 'text-embedding-3-small',
}
```

Add `embedding.api_key` to `SENSITIVE_KEYS` for encryption at rest.

#### 1.2 EmbeddingConfig Fallback Chain (Zero-Config for OpenAI-Compatible)

In `rag_config.py`, `EmbeddingConfig.__post_init__`:

```
embedding.base_url → (if empty) ai_model.base_url → (if empty) error
embedding.api_key  → (if empty) ai_model.api_key  → (if empty) warning
embedding.model    → uses configured value (default: text-embedding-3-small)
```

**Zero-config goal:** If the user's chat provider is OpenAI-compatible (OpenAI, OpenRouter, LM Studio, Ollama, Azure OpenAI, any `/v1/` endpoint), embeddings work automatically using the same `base_url` and `api_key`. No extra configuration needed.

**Auto-test on first use:** When RAG processes its first file, `EmbeddingService` sends a minimal test request to `{base_url}/embeddings`. If it succeeds, cache the result — the endpoint supports embeddings. If it fails with 404, check if a separate `embedding.base_url` is configured and try that. If both fail, surface an actionable error.

**Anthropic detection:** If resolved `base_url` contains `api.anthropic.com` or `anthropic`, skip the auto-test (it will always fail) and immediately check for separate embedding config. If none configured, return a clear message: "Your chat provider (Anthropic) doesn't support embeddings. Configure an embedding provider in Settings → Advanced to use file context features."

#### 1.3 Improved Error Handling in EmbeddingService

**Retry with exponential backoff:**
- On HTTP 429: retry up to 3 times with 1s, 2s, 4s delays
- On HTTP 5xx: retry up to 2 times with 1s, 2s delays
- On HTTP 404: no retry — this means the endpoint doesn't support embeddings. Return clear error message.

**Actionable error messages:**
- 404 → "Embedding endpoint returned 404. If using Anthropic for chat, configure a separate embedding provider in Settings → Advanced."
- 401/403 → "Embedding API key is invalid or expired. Check Settings → Advanced → Embedding API Key."
- 429 after retries → "Embedding rate limit exceeded after 3 retries. Try again in a few minutes."
- Connection error → "Cannot connect to embedding endpoint: {url}. Verify the URL in Settings → Advanced."

**Pre-flight validation:**
- `validate_endpoint()` method that sends a minimal test embedding request
- Called when settings change (via `on_change` observer) and on first RAG file upload
- Result cached until settings change

#### 1.4 Settings UI

Add embedding configuration fields in the Advanced tab of settings_dialog.py:
- Embedding Base URL (text field, placeholder: "Leave empty to use AI Model URL")
- Embedding API Key (password field, placeholder: "Leave empty to use AI Model Key")
- Embedding Model (text field, default: "text-embedding-3-small")

#### 1.5 Dimensions Auto-Detection

Expand the known-models lookup table:

```python
model_dimensions = {
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
}
```

For unknown models, attempt to detect dimensions from the first successful embedding response.

---

## Part 2: Unified Outlook Skills

### Problem

Four separate Outlook skills with hardcoded operations. No way for the AI to handle unpredictable requests. Duplicated COM threading boilerplate across all four skills.

### Design

#### 2.1 Shared COM Infrastructure: `outlook_com_bridge.py`

**Location:** `specter/src/infrastructure/skills/core/outlook_com_bridge.py`

**`execute_in_com_thread(callable, timeout) → result`**
- Shared COM thread executor replacing the duplicated pattern in all 4 skills
- Handles `pythoncom.CoInitialize()` / `CoUninitialize()`
- Uses `queue.Queue` for result passing
- Configurable timeout (default 30s for create ops, 60s for search ops)

**`preflight_check() → bool`**
- Checks `winreg.HKEY_CLASSES_ROOT\Outlook.Application\CLSID`
- Returns `False` with descriptive error for New Outlook (olk.exe)

**`OutlookCOMSandbox`**

AST-based code validation (`_validate_code`):

Blocked builtins (same as docx):
```python
_BLOCKED_NAMES = frozenset({
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "exit", "quit", "globals", "locals",
    "getattr", "setattr", "delattr", "vars", "dir",
    "os", "sys", "subprocess", "pathlib", "shutil", "socket",
    "requests", "urllib", "pickle", "marshal", "ctypes",
    "importlib", "builtins", "__builtins__",
})
```

Blocked COM methods (Outlook-specific safety):
```python
_BLOCKED_COM_METHODS = frozenset({
    "Send",                # Never auto-send
    "Delete",              # Never auto-delete
    "PermanentlyDelete",   # Never permanently delete
    "Move",                # Don't move items without consent
    "Copy",                # Don't duplicate items silently
    "SaveAs",              # Don't write to arbitrary file paths
})
```

Allowed COM methods (non-exhaustive): `.Display()`, `.Save()`, `.Recipients.Add()`, `.Attachments.Add()`, `.Restrict()`, `.Sort()`, `.GetFirst()`, `.GetNext()`, `.GetDefaultFolder()`, `.CreateItem()`, property access/writes.

Restricted namespace provided to sandboxed code:
```python
namespace = {
    "outlook": outlook_app,          # COM Application object
    "mapi": outlook.GetNamespace("MAPI"),
    "pythoncom": <constants_only>,   # For olFolderInbox etc.
    "__builtins__": {
        "range", "len", "str", "int", "float", "bool",
        "list", "dict", "set", "tuple", "enumerate", "zip",
        "min", "max", "round", "abs", "sorted", "reversed",
        "isinstance", "hasattr", "True", "False", "None",
        "print": lambda *a, **kw: None,  # no-op
    }
}
```

Execution: runs in a daemon thread within a COM-initialized thread, with configurable timeout (default 30s).

Size limits: 5000 chars, 100 lines (same as docx).

#### 2.2 Unified `OutlookEmailSkill`

**Replaces:** `email_draft_skill.py` + `email_search_skill.py`

**Metadata:**
- `skill_id`: `"outlook_email"`
- `version`: `"1.0.0"`
- `category`: `COMMUNICATION`
- `ai_callable`: `True`
- `permissions_required`: `[PermissionType.OUTLOOK_ACCESS]`

**Operation Registry:**
```python
ALL_OPERATIONS = [
    "draft_email",     # Create and display email draft
    "search_email",    # Search mailbox with filters
    "reply_email",     # Reply to an email by subject/conversation
    "forward_email",   # Forward an email to new recipients
    "custom",          # AI-generated COM code via sandbox
]
```

**Parameters:**
```python
parameters = [
    SkillParameter("operation", str, required=True,
                   constraints={"choices": ALL_OPERATIONS}),
    # draft_email params (from email_draft_skill):
    SkillParameter("to", str, required=False),
    SkillParameter("subject", str, required=False),
    SkillParameter("body", str, required=False),
    SkillParameter("cc", str, required=False),
    SkillParameter("bcc", str, required=False),
    SkillParameter("html", bool, required=False),
    SkillParameter("importance", str, required=False),
    # search_email params (from email_search_skill):
    SkillParameter("sender", str, required=False),
    SkillParameter("recipient", str, required=False),
    SkillParameter("body_contains", str, required=False),
    SkillParameter("days_back", int, required=False),
    SkillParameter("has_attachments", bool, required=False),
    SkillParameter("unread_only", bool, required=False),
    SkillParameter("folder", str, required=False),
    SkillParameter("max_results", int, required=False),
    SkillParameter("semantic_query", str, required=False),
    SkillParameter("include_body", bool, required=False),
    # reply/forward params:
    SkillParameter("reply_subject", str, required=False),
    SkillParameter("forward_to", str, required=False),
    SkillParameter("reply_body", str, required=False),
    # custom params:
    SkillParameter("custom_code", str, required=False),
]
```

**Execute dispatch (same pattern as docx_formatter):**
```python
async def execute(self, **params):
    operation = params.get("operation")
    if operation not in ALL_OPERATIONS:
        return SkillResult(success=False, error=f"Unknown operation: {operation}")

    result = {}
    try:
        if operation == "draft_email":
            result = await self._draft_email(params)
        elif operation == "search_email":
            result = await self._search_email(params)
        elif operation == "reply_email":
            result = await self._reply_email(params)
        elif operation == "forward_email":
            result = await self._forward_email(params)
        elif operation == "custom":
            result = await self._execute_custom(params)
    except Exception as e:
        logger.error(f"Operation '{operation}' failed: {e}", exc_info=True)
        result = {"error": str(e)}

    return SkillResult(success="error" not in result, data=result)
```

**Internal methods:** Refactored from existing skill code, using `OutlookCOMBridge.execute_in_com_thread()` instead of duplicated threading.

#### 2.3 Unified `OutlookCalendarSkill`

**Replaces:** `calendar_event_skill.py` + `calendar_search_skill.py`

**Metadata:**
- `skill_id`: `"outlook_calendar"`
- `version`: `"1.0.0"`
- `category`: `PRODUCTIVITY`

**Operation Registry:**
```python
ALL_OPERATIONS = [
    "create_event",    # Create and display calendar event
    "search_events",   # Search calendar with filters
    "update_event",    # Modify existing event (opens for review)
    "cancel_event",    # Cancel event (opens for review, doesn't auto-delete)
    "custom",          # AI-generated COM code via sandbox
]
```

**Parameters:** Combined from `calendar_event_skill` + `calendar_search_skill`, plus new `update_event`/`cancel_event` params.

**Same dispatch pattern** as `OutlookEmailSkill`.

#### 2.4 Migration Path

1. Create new unified skills
2. Update `app_coordinator.py` to register new skills instead of old ones
3. Update `tool_bridge.py` awareness prompt for new tool names
4. Remove old 4 skill files
5. Old skill_ids (`email_draft`, `email_search`, `calendar_event`, `calendar_search`) cease to exist — no backward compatibility needed since tool definitions are regenerated each session

---

## File Changes Summary

### New Files
- `specter/src/infrastructure/skills/core/outlook_com_bridge.py`
- `specter/src/infrastructure/skills/skills_library/outlook_email_skill.py`
- `specter/src/infrastructure/skills/skills_library/outlook_calendar_skill.py`

### Modified Files
- `specter/src/infrastructure/storage/settings_manager.py` — add `embedding` settings
- `specter/src/infrastructure/rag_pipeline/config/rag_config.py` — fallback chain
- `specter/src/infrastructure/rag_pipeline/services/embedding_service.py` — retry, errors
- `specter/src/presentation/dialogs/settings_dialog.py` — embedding UI fields
- `specter/src/application/app_coordinator.py` — register new skills
- `specter/src/infrastructure/skills/core/tool_bridge.py` — update awareness prompt

### Removed Files
- `specter/src/infrastructure/skills/skills_library/email_draft_skill.py`
- `specter/src/infrastructure/skills/skills_library/email_search_skill.py`
- `specter/src/infrastructure/skills/skills_library/calendar_event_skill.py`
- `specter/src/infrastructure/skills/skills_library/calendar_search_skill.py`
