# Embeddings Endpoint & Unified Outlook Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make RAG embeddings work regardless of AI provider (with zero-config for OpenAI-compatible endpoints), and unify 4 Outlook skills into 2 with operation registries + COM sandbox.

**Architecture:** Separate embedding config with fallback chain (embedding settings → ai_model settings). Shared OutlookCOMBridge for COM thread isolation + AST-validated sandbox. Two unified skills (outlook_email, outlook_calendar) with operation registries following the docx_formatter pattern.

**Tech Stack:** PyQt6, python-docx patterns (AST sandbox), win32com.client, pythoncom, FAISS, numpy, requests

---

## Task 1: Embedding Settings in settings_manager.py

**Files:**
- Modify: `specter/src/infrastructure/storage/settings_manager.py:36-173`

**Step 1: Add embedding section to DEFAULT_SETTINGS**

In `settings_manager.py`, add `embedding` key after the `tools` section (line 168), before `avatar`:

```python
        'embedding': {
            'base_url': '',      # Empty = inherit from ai_model.base_url
            'api_key': '',       # Empty = inherit from ai_model.api_key
            'model': 'text-embedding-3-small',
        },
```

**Step 2: Add embedding.api_key to SENSITIVE_KEYS**

In `SENSITIVE_KEYS` (line 36-43), the existing `'api_key'` entry already matches any key named `api_key` including nested ones. Verify by checking how `_is_sensitive_key()` works. If it does substring matching, no change needed. If it does exact path matching, add `'embedding.api_key'`.

**Step 3: Commit**

```bash
git add specter/src/infrastructure/storage/settings_manager.py
git commit -m "feat(settings): Add separate embedding configuration section"
```

---

## Task 2: EmbeddingConfig Fallback Chain

**Files:**
- Modify: `specter/src/infrastructure/rag_pipeline/config/rag_config.py:59-101`

**Step 1: Update EmbeddingConfig.__post_init__ with fallback chain**

Replace lines 77-100 of `rag_config.py`:

```python
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Fallback chain: embedding.* settings → ai_model.* settings
        if not self.api_endpoint:
            # Try dedicated embedding base_url first
            self.api_endpoint = settings.get("embedding.base_url", "") if settings else ""
            # Fall back to ai_model base_url
            if not self.api_endpoint:
                self.api_endpoint = settings.get("ai_model.base_url", "") if settings else ""
            if not self.api_endpoint:
                logger.warning("No API endpoint configured - RAG embeddings will fail")

        # Detect Anthropic endpoint (no embeddings API)
        self._is_anthropic_endpoint = False
        if self.api_endpoint and "anthropic" in self.api_endpoint.lower():
            self._is_anthropic_endpoint = True
            # Check if user configured a separate embedding endpoint
            dedicated_url = settings.get("embedding.base_url", "") if settings else ""
            if not dedicated_url:
                logger.warning(
                    "Chat provider appears to be Anthropic, which has no embeddings API. "
                    "Configure a separate embedding provider in Settings → Advanced "
                    "to use file context features."
                )

        # API key fallback chain
        if not self.api_key:
            self.api_key = settings.get("embedding.api_key", "") if settings else ""
            if not self.api_key:
                self.api_key = settings.get("ai_model.api_key") if settings else None
            if not self.api_key:
                logger.warning("No embedding API key found - embeddings will fail")

        # Model from embedding settings
        embedding_model = settings.get("embedding.model", "") if settings else ""
        if embedding_model:
            self.model = embedding_model

        # Set default dimensions based on model
        if not self.dimensions:
            model_dimensions = {
                "text-embedding-ada-002": 1536,
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "voyage-3": 1024,
                "voyage-3-lite": 512,
                "voyage-code-3": 1024,
            }
            self.dimensions = model_dimensions.get(self.model, 1536)
```

**Step 2: Commit**

```bash
git add specter/src/infrastructure/rag_pipeline/config/rag_config.py
git commit -m "feat(rag): Add embedding config fallback chain with Anthropic detection"
```

---

## Task 3: EmbeddingService Retry & Error Handling

**Files:**
- Modify: `specter/src/infrastructure/rag_pipeline/services/embedding_service.py:202-343`

**Step 1: Add retry helper method**

Add after `_rate_limit()` (line 151) and before `_validate_input()` (line 153):

```python
    def _should_retry(self, status_code: int, attempt: int, max_retries: int = 3) -> float:
        """
        Determine if request should be retried and return delay in seconds.
        Returns 0 if should not retry.
        """
        if attempt >= max_retries:
            return 0
        if status_code == 429:
            # Rate limit: exponential backoff 1s, 2s, 4s
            return min(2 ** attempt, 8)
        if status_code >= 500:
            # Server error: backoff 1s, 2s
            return min(2 ** attempt, 4) if attempt < 2 else 0
        return 0

    def _get_error_message(self, status_code: int, response_text: str) -> str:
        """Return actionable error message based on HTTP status."""
        if status_code == 404:
            return (
                f"Embedding endpoint returned 404 (Not Found). "
                f"If using Anthropic for chat, configure a separate embedding "
                f"provider in Settings → Advanced. URL: {self.api_endpoint}/embeddings"
            )
        if status_code in (401, 403):
            return (
                f"Embedding API key is invalid or expired (HTTP {status_code}). "
                f"Check Settings → Advanced → Embedding API Key."
            )
        if status_code == 429:
            return "Embedding rate limit exceeded after retries. Try again in a few minutes."
        if status_code >= 500:
            return f"Embedding server error (HTTP {status_code}). The provider may be experiencing issues."
        return f"Embedding API error: HTTP {status_code} - {response_text[:200]}"
```

**Step 2: Rewrite create_embedding with retry loop**

Replace `create_embedding` method (lines 202-293):

```python
    def create_embedding(self, text: str, model: str = None) -> Optional[np.ndarray]:
        """
        Create embedding for text with caching, retry, and error handling.

        Args:
            text: Input text to embed
            model: Override default model

        Returns:
            numpy array embedding or None if failed
        """
        try:
            text = self._validate_input(text)
            model = model or self.model

            # Check cache first
            cache_key = self._generate_cache_key(text, model)
            cached_embedding = self._get_embedding_from_cache(cache_key)
            if cached_embedding is not None:
                logger.debug(f"Cache hit for text hash: {cache_key[:8]}...")
                return cached_embedding

            # Rate limiting
            self._rate_limit()

            # Prepare request
            request_data = {
                'input': text,
                'model': model
            }
            request_data.update(self._get_provider_params())

            logger.debug(f"Creating embedding for {len(text)} characters")

            # Retry loop
            max_retries = 3
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    response = self.session_manager.make_request(
                        method="POST",
                        url=f"{self.api_endpoint}/embeddings",
                        json=request_data,
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    self.stats['requests_made'] += 1

                    if response.status_code == 200:
                        response_data = response.json()
                        embedding = self._parse_response(response_data)
                        if embedding is not None:
                            self._store_in_cache(cache_key, embedding)
                            if 'usage' in response_data:
                                self.stats['total_tokens_processed'] += response_data['usage'].get('total_tokens', 0)
                            logger.debug(f"Successfully created embedding: {embedding.shape}")
                            return embedding
                        else:
                            logger.error("Failed to parse embedding from response")
                            self.stats['errors'] += 1
                            return None

                    # Check if we should retry
                    retry_delay = self._should_retry(response.status_code, attempt, max_retries)
                    if retry_delay > 0:
                        logger.warning(
                            f"Embedding request failed (HTTP {response.status_code}), "
                            f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        continue

                    # Non-retryable error
                    error_msg = self._get_error_message(response.status_code, response.text)
                    logger.error(error_msg)
                    self.stats['errors'] += 1
                    return None

                except requests.exceptions.Timeout:
                    last_error = "timeout"
                    if attempt < max_retries:
                        logger.warning(f"Embedding request timed out, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
                        continue
                    logger.error(f"Embedding request timed out after {max_retries} retries")
                    self.stats['errors'] += 1
                    return None

                except requests.exceptions.ConnectionError as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        logger.warning(f"Connection error, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
                        continue
                    logger.error(
                        f"Cannot connect to embedding endpoint: {self.api_endpoint}. "
                        f"Verify the URL in Settings → Advanced. Error: {e}"
                    )
                    self.stats['errors'] += 1
                    return None

            # Should not reach here, but just in case
            logger.error(f"Embedding failed after all retries. Last error: {last_error}")
            self.stats['errors'] += 1
            return None

        except ValueError as e:
            logger.error(f"Invalid embedding input: {e}")
            self.stats['errors'] += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating embedding: {e}")
            self.stats['errors'] += 1
            return None
```

**Step 3: Add validate_endpoint method**

Add after `_get_provider_params()` (line 343):

```python
    def validate_endpoint(self) -> dict:
        """
        Test that the embedding endpoint is reachable and functional.
        Returns dict with 'valid' (bool), 'error' (str), 'dimensions' (int or None).
        """
        try:
            test_text = "test"
            response = self.session_manager.make_request(
                method="POST",
                url=f"{self.api_endpoint}/embeddings",
                json={'input': test_text, 'model': self.model},
                headers=self.headers,
                timeout=min(self.timeout, 10.0)  # Shorter timeout for validation
            )
            if response.status_code == 200:
                data = response.json()
                embedding = self._parse_response(data)
                if embedding is not None:
                    return {'valid': True, 'error': '', 'dimensions': len(embedding)}
                return {'valid': False, 'error': 'Could not parse embedding response'}
            return {
                'valid': False,
                'error': self._get_error_message(response.status_code, response.text)
            }
        except requests.exceptions.ConnectionError:
            return {
                'valid': False,
                'error': f"Cannot connect to {self.api_endpoint}. Check the URL."
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}
```

**Step 4: Commit**

```bash
git add specter/src/infrastructure/rag_pipeline/services/embedding_service.py
git commit -m "feat(embeddings): Add retry with backoff, actionable errors, endpoint validation"
```

---

## Task 4: Embedding Settings UI

**Files:**
- Modify: `specter/src/presentation/dialogs/settings_dialog.py:1235-1435` (Advanced tab)
- Modify: `specter/src/presentation/dialogs/settings_dialog.py:3920-3931` (_get_current_config advanced section)
- Modify: `specter/src/presentation/dialogs/settings_dialog.py:4098-4099` (_apply_config_to_ui advanced section)

**Step 1: Add embedding config group to Advanced tab**

In `_create_advanced_tab()`, after the Data Storage group (~line 1432) and before the `return tab` / `addTab` call, insert a new group:

```python
        # --- Embedding Provider group ---
        embedding_group = QGroupBox("Embedding Provider (for File Context / RAG)")
        embedding_layout = QFormLayout(embedding_group)
        embedding_layout.setSpacing(8)

        # Info label
        embedding_info = QLabel(
            "Leave fields empty to use your AI Model settings automatically. "
            "Only configure these if your chat provider doesn't support embeddings "
            "(e.g., Anthropic) or you want a different embedding model."
        )
        embedding_info.setWordWrap(True)
        embedding_info.setStyleSheet("color: gray; font-size: 10px; margin-bottom: 6px;")
        embedding_layout.addRow(embedding_info)

        self.embedding_base_url_edit = QLineEdit()
        self.embedding_base_url_edit.setPlaceholderText("Leave empty to use AI Model URL")
        embedding_layout.addRow("Embedding Base URL:", self.embedding_base_url_edit)

        self.embedding_api_key_edit = QLineEdit()
        self.embedding_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.embedding_api_key_edit.setPlaceholderText("Leave empty to use AI Model Key")
        embedding_layout.addRow("Embedding API Key:", self.embedding_api_key_edit)

        self.embedding_model_edit = QLineEdit()
        self.embedding_model_edit.setPlaceholderText("text-embedding-3-small")
        self.embedding_model_edit.setText("text-embedding-3-small")
        embedding_layout.addRow("Embedding Model:", self.embedding_model_edit)

        layout.addWidget(embedding_group)
```

**Step 2: Save embedding settings in _get_current_config**

In `_get_current_config()`, add to the returned dict after the `advanced` key (~line 3931):

```python
            'embedding': {
                'base_url': self.embedding_base_url_edit.text().strip(),
                'api_key': self.embedding_api_key_edit.text().strip(),
                'model': self.embedding_model_edit.text().strip() or 'text-embedding-3-small',
            },
```

**Step 3: Load embedding settings in _apply_config_to_ui**

In `_apply_config_to_ui()`, after the advanced settings section (~line 4098), add:

```python
        # Embedding settings
        embedding = config.get('embedding', {})
        if hasattr(self, 'embedding_base_url_edit'):
            self.embedding_base_url_edit.setText(embedding.get('base_url', ''))
            self.embedding_api_key_edit.setText(embedding.get('api_key', ''))
            self.embedding_model_edit.setText(embedding.get('model', 'text-embedding-3-small'))
```

**Step 4: Save embedding category in _apply_settings**

In `_apply_settings()` (~line 4267-4344), find where it iterates settings categories and ensure `embedding` is included. The method calls `settings.set(category, values)` for each key in the config dict, so it should work automatically if `_get_current_config()` returns the `embedding` key.

**Step 5: Commit**

```bash
git add specter/src/presentation/dialogs/settings_dialog.py
git commit -m "feat(ui): Add embedding provider configuration in Advanced tab"
```

---

## Task 5: OutlookCOMBridge — Shared COM Infrastructure

**Files:**
- Create: `specter/src/infrastructure/skills/core/outlook_com_bridge.py`

**Step 1: Create the OutlookCOMBridge module**

This file contains three components:
1. `execute_in_com_thread()` — shared COM thread executor
2. `preflight_check()` — validates Outlook COM availability
3. `OutlookCOMSandbox` — AST-validated code execution

```python
"""
Shared Outlook COM infrastructure for email and calendar skills.

Provides:
- Thread-safe COM execution with pythoncom initialization
- Pre-flight Outlook availability checking
- AST-validated sandbox for AI-generated COM code
"""

import ast
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("specter.outlook_com_bridge")


@dataclass
class COMExecutionResult:
    """Result from a COM thread execution."""
    success: bool
    data: Any = None
    error: str = ""


@dataclass
class CodeValidationResult:
    """Result from AST code validation."""
    valid: bool
    error: str = ""
    line_count: int = 0
    char_count: int = 0


@dataclass
class CodeExecutionResult:
    """Result from sandboxed code execution."""
    success: bool
    message: str = ""
    error: str = ""
    output: Any = None


def preflight_check() -> Tuple[bool, str]:
    """
    Check if Outlook COM automation is available.
    Returns (success, error_message).
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            r"Outlook.Application\CLSID"
        )
        winreg.CloseKey(key)
        return True, ""
    except FileNotFoundError:
        return False, (
            "Microsoft Outlook (classic) is not installed or the New Outlook "
            "(olk.exe) is active. COM automation requires classic Outlook."
        )
    except ImportError:
        return False, "winreg module not available on this platform."
    except Exception as e:
        return False, f"Outlook COM check failed: {e}"


def execute_in_com_thread(
    func: Callable,
    timeout: int = 30,
    **kwargs
) -> COMExecutionResult:
    """
    Execute a function in a dedicated COM-initialized thread.

    Args:
        func: Callable that receives (outlook, namespace, **kwargs) and returns data.
        timeout: Maximum execution time in seconds.
        **kwargs: Additional arguments passed to func.

    Returns:
        COMExecutionResult with success/data/error.
    """
    result_queue = queue.Queue()

    def _worker():
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                import win32com.client
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                data = func(outlook=outlook, namespace=namespace, **kwargs)
                result_queue.put(COMExecutionResult(success=True, data=data))
            except Exception as e:
                logger.error(f"COM operation failed: {e}", exc_info=True)
                error_str = str(e)
                # Detect specific COM errors
                if "0x800401F3" in error_str or "Invalid class string" in error_str:
                    error_str = (
                        "Outlook COM class not found. The New Outlook (olk.exe) "
                        "does not support COM automation."
                    )
                result_queue.put(COMExecutionResult(success=False, error=error_str))
            finally:
                pythoncom.CoUninitialize()
        except ImportError as e:
            result_queue.put(COMExecutionResult(
                success=False,
                error=f"Required package not installed: {e}. Run: pip install pywin32"
            ))

    # Pre-flight check
    ok, err = preflight_check()
    if not ok:
        return COMExecutionResult(success=False, error=err)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return COMExecutionResult(
            success=False,
            error=f"Outlook COM operation timed out after {timeout}s"
        )

    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return COMExecutionResult(
            success=False,
            error="No result from COM thread"
        )


class OutlookCOMSandbox:
    """
    AST-validated sandbox for AI-generated Outlook COM code.

    Safety model:
    - Blocks dangerous builtins (exec, eval, os, sys, subprocess, etc.)
    - Blocks dangerous COM methods (Send, Delete, PermanentlyDelete, Move, SaveAs)
    - Allows Display, Save, property access, Recipients.Add, etc.
    - Runs in COM-initialized daemon thread with timeout
    - Restricted __builtins__ namespace
    """

    _BLOCKED_NAMES = frozenset({
        # Dangerous builtins
        "exec", "eval", "compile", "__import__", "open", "input",
        "breakpoint", "exit", "quit", "globals", "locals",
        "getattr", "setattr", "delattr", "vars", "dir",
        # Dangerous modules
        "os", "sys", "subprocess", "pathlib", "shutil", "socket",
        "requests", "urllib", "pickle", "marshal", "ctypes",
        "importlib", "builtins", "__builtins__",
    })

    _BLOCKED_COM_METHODS = frozenset({
        "Send",                # Never auto-send emails
        "Delete",              # Never auto-delete items
        "PermanentlyDelete",   # Never permanently delete
        "Move",                # Don't move items without consent
        "SaveAs",              # Don't write to arbitrary paths
    })

    _MAX_CODE_CHARS = 5000
    _MAX_CODE_LINES = 100

    @staticmethod
    def validate_code(code: str) -> CodeValidationResult:
        """
        Validate AI-generated code using AST analysis.
        Returns CodeValidationResult with valid=True/False and error details.
        """
        if not code or not code.strip():
            return CodeValidationResult(valid=False, error="Code is empty")

        code = code.strip()
        char_count = len(code)
        line_count = code.count('\n') + 1

        if char_count > OutlookCOMSandbox._MAX_CODE_CHARS:
            return CodeValidationResult(
                valid=False,
                error=f"Code exceeds {OutlookCOMSandbox._MAX_CODE_CHARS} character limit ({char_count} chars)",
                line_count=line_count, char_count=char_count
            )
        if line_count > OutlookCOMSandbox._MAX_CODE_LINES:
            return CodeValidationResult(
                valid=False,
                error=f"Code exceeds {OutlookCOMSandbox._MAX_CODE_LINES} line limit ({line_count} lines)",
                line_count=line_count, char_count=char_count
            )

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return CodeValidationResult(
                valid=False, error=f"Syntax error: {e}",
                line_count=line_count, char_count=char_count
            )

        # Walk AST for violations
        for node in ast.walk(tree):
            # Block imports (except win32com, pythoncom)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in ("win32com", "win32com.client", "pythoncom"):
                        return CodeValidationResult(
                            valid=False,
                            error=f"Import not allowed: '{alias.name}'. Only win32com and pythoncom are permitted.",
                            line_count=line_count, char_count=char_count
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in ("win32com", "win32com.client", "pythoncom"):
                    return CodeValidationResult(
                        valid=False,
                        error=f"Import not allowed: 'from {node.module}'. Only win32com and pythoncom are permitted.",
                        line_count=line_count, char_count=char_count
                    )

            # Block star imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in getattr(node, 'names', []):
                    if alias.name == '*':
                        return CodeValidationResult(
                            valid=False, error="Star imports are not allowed.",
                            line_count=line_count, char_count=char_count
                        )

            # Block dangerous names
            if isinstance(node, ast.Name) and node.id in OutlookCOMSandbox._BLOCKED_NAMES:
                return CodeValidationResult(
                    valid=False,
                    error=f"Blocked name: '{node.id}' is not allowed for security.",
                    line_count=line_count, char_count=char_count
                )

            # Block dunder attribute access (except __init__)
            if isinstance(node, ast.Attribute):
                if node.attr.startswith('__') and node.attr.endswith('__') and node.attr != '__init__':
                    return CodeValidationResult(
                        valid=False,
                        error=f"Dunder attribute access not allowed: '{node.attr}'",
                        line_count=line_count, char_count=char_count
                    )
                # Block dangerous COM methods
                if node.attr in OutlookCOMSandbox._BLOCKED_COM_METHODS:
                    return CodeValidationResult(
                        valid=False,
                        error=f"Blocked COM method: '.{node.attr}()' is not allowed for safety. "
                              f"Use .Display() to show items for user review instead.",
                        line_count=line_count, char_count=char_count
                    )

            # Block del statements
            if isinstance(node, ast.Delete):
                return CodeValidationResult(
                    valid=False, error="'del' statements are not allowed.",
                    line_count=line_count, char_count=char_count
                )

        return CodeValidationResult(
            valid=True, line_count=line_count, char_count=char_count
        )

    def execute_code(
        self,
        code: str,
        timeout: int = 30
    ) -> CodeExecutionResult:
        """
        Validate and execute AI-generated COM code in a sandboxed environment.

        The code receives 'outlook' and 'mapi' objects in its namespace.
        It should store its result in a variable named 'result'.

        Args:
            code: Python code string to execute
            timeout: Maximum execution time in seconds

        Returns:
            CodeExecutionResult with success/message/error/output
        """
        # Step 1: AST validation
        validation = self.validate_code(code)
        if not validation.valid:
            return CodeExecutionResult(
                success=False,
                error=f"Code validation failed: {validation.error}"
            )

        # Step 2: Execute in COM thread
        def _run_sandboxed(outlook, namespace, **kwargs):
            sandbox_namespace = {
                "outlook": outlook,
                "mapi": namespace,
                "result": None,  # Code should set this
            }
            sandbox_namespace["__builtins__"] = {
                "range": range, "len": len, "str": str, "int": int,
                "float": float, "bool": bool, "list": list, "dict": dict,
                "set": set, "tuple": tuple, "enumerate": enumerate,
                "zip": zip, "min": min, "max": max, "round": round,
                "abs": abs, "sorted": sorted, "reversed": reversed,
                "isinstance": isinstance, "hasattr": hasattr,
                "True": True, "False": False, "None": None,
                "print": lambda *a, **kw: None,  # no-op
            }

            exec(code, sandbox_namespace)  # noqa: S102 - intentional sandboxed exec
            return sandbox_namespace.get("result")

        com_result = execute_in_com_thread(_run_sandboxed, timeout=timeout)

        if com_result.success:
            return CodeExecutionResult(
                success=True,
                message="Custom code executed successfully",
                output=com_result.data
            )
        else:
            return CodeExecutionResult(
                success=False,
                error=com_result.error
            )
```

**Step 2: Commit**

```bash
git add specter/src/infrastructure/skills/core/outlook_com_bridge.py
git commit -m "feat(skills): Add shared OutlookCOMBridge with COM thread executor and AST sandbox"
```

---

## Task 6: Unified OutlookEmailSkill

**Files:**
- Create: `specter/src/infrastructure/skills/skills_library/outlook_email_skill.py`

**Step 1: Create OutlookEmailSkill**

This skill consolidates `email_draft_skill.py` and `email_search_skill.py` into a single skill with an operation registry. The internal methods are refactored from the existing code to use `OutlookCOMBridge`.

Key design points:
- `ALL_OPERATIONS` list serves as allowlist, execution order reference, and AI discovery
- Each operation has its own `try/except` isolation
- `custom` operation uses `OutlookCOMSandbox` for AI-generated code
- All COM calls go through `execute_in_com_thread()`

The full file is large (~800-1000 lines) because it contains the complete logic from both existing skills. The structure is:

```python
"""Unified Outlook email skill with operation registry and COM sandbox."""

import logging
import difflib
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..core.base_skill import BaseSkill, SkillMetadata, SkillParameter, SkillResult
from ..core.base_skill import SkillCategory, PermissionType
from ..core.outlook_com_bridge import (
    execute_in_com_thread, preflight_check, OutlookCOMSandbox,
    CodeExecutionResult,
)

logger = logging.getLogger("specter.outlook_email_skill")

ALL_OPERATIONS = [
    "draft_email",
    "search_email",
    "reply_email",
    "forward_email",
    "custom",
]

# Outlook folder constants (olDefaultFolders)
FOLDER_MAP = {
    "inbox": 6, "sent": 5, "drafts": 16, "deleted": 3,
    "junk": 23, "outbox": 4, "all": None,
}


class OutlookEmailSkill(BaseSkill):
    """Unified Outlook email skill with operation registry and COM sandbox."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="outlook_email",
            name="Outlook Email",
            description=(
                "Manage Outlook emails: draft new emails, search the mailbox, "
                "reply to or forward emails, and run custom email operations. "
                "Operations: " + ", ".join(ALL_OPERATIONS)
            ),
            version="1.0.0",
            category=SkillCategory.COMMUNICATION,
            ai_callable=True,
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
        )

    @property
    def parameters(self) -> list:
        return [
            SkillParameter("operation", str, required=True,
                          description=f"Operation to perform. One of: {', '.join(ALL_OPERATIONS)}",
                          constraints={"choices": ALL_OPERATIONS}),
            # draft_email params
            SkillParameter("to", str, required=False,
                          description="Recipient email(s), comma-separated",
                          constraints={"min_length": 3, "max_length": 500}),
            SkillParameter("subject", str, required=False,
                          description="Email subject line",
                          constraints={"max_length": 255}),
            SkillParameter("body", str, required=False,
                          description="Email body (plain text or HTML)",
                          constraints={"min_length": 1, "max_length": 50000}),
            SkillParameter("cc", str, required=False,
                          description="CC recipients, comma-separated",
                          constraints={"max_length": 500}),
            SkillParameter("bcc", str, required=False,
                          description="BCC recipients, comma-separated",
                          constraints={"max_length": 500}),
            SkillParameter("html", bool, required=False,
                          description="Force HTML format (auto-detected if not set)"),
            SkillParameter("importance", str, required=False,
                          description="Email importance: low, normal, or high"),
            # search_email params
            SkillParameter("sender", str, required=False,
                          description="Filter by sender name or email"),
            SkillParameter("recipient", str, required=False,
                          description="Filter by recipient in To/CC"),
            SkillParameter("body_contains", str, required=False,
                          description="Search email body text"),
            SkillParameter("days_back", int, required=False,
                          description="Search within last N days (1-3650)"),
            SkillParameter("has_attachments", bool, required=False,
                          description="Filter for emails with attachments"),
            SkillParameter("unread_only", bool, required=False,
                          description="Only return unread emails"),
            SkillParameter("folder", str, required=False,
                          description="Mailbox folder: inbox, sent, drafts, deleted, junk, outbox, all"),
            SkillParameter("max_results", int, required=False,
                          description="Maximum results to return (1-500)",
                          constraints={"min_value": 1, "max_value": 500}),
            SkillParameter("semantic_query", str, required=False,
                          description="Natural language query for semantic ranking"),
            SkillParameter("include_body", bool, required=False,
                          description="Include body preview in search results"),
            # reply/forward params
            SkillParameter("reply_subject", str, required=False,
                          description="Subject of email to reply to (finds most recent match)"),
            SkillParameter("forward_to", str, required=False,
                          description="Recipient(s) to forward to"),
            SkillParameter("reply_body", str, required=False,
                          description="Body text for reply or forward"),
            # custom params
            SkillParameter("custom_code", str, required=False,
                          description="Python code for custom Outlook operations (sandboxed)"),
        ]

    async def execute(self, **params) -> SkillResult:
        operation = params.get("operation", "")
        if operation not in ALL_OPERATIONS:
            return SkillResult(
                success=False,
                skill_id=self.metadata.skill_id,
                error=f"Unknown operation: '{operation}'. Valid: {', '.join(ALL_OPERATIONS)}"
            )

        try:
            if operation == "draft_email":
                return await self._draft_email(params)
            elif operation == "search_email":
                return await self._search_email(params)
            elif operation == "reply_email":
                return await self._reply_email(params)
            elif operation == "forward_email":
                return await self._forward_email(params)
            elif operation == "custom":
                return await self._execute_custom(params)
        except Exception as e:
            logger.error(f"Operation '{operation}' failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                skill_id=self.metadata.skill_id,
                error=f"Operation '{operation}' failed: {e}"
            )

    # --- Internal operation methods ---
    # Each method is refactored from the original skill files,
    # using execute_in_com_thread() from outlook_com_bridge.

    async def _draft_email(self, params: dict) -> SkillResult:
        """Create and display an email draft. Refactored from EmailDraftSkill."""
        to = params.get("to", "")
        if not to:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'to' is required for draft_email")
        body = params.get("body", "")
        if not body:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'body' is required for draft_email")

        subject = params.get("subject", "")
        cc = params.get("cc", "")
        bcc = params.get("bcc", "")
        importance = params.get("importance", "normal")
        is_html = params.get("html", None)
        if is_html is None:
            is_html = self._is_html(body)

        def _create_draft(outlook, namespace, **kw):
            mail = outlook.CreateItem(0)  # olMailItem
            mail.To = to
            if cc:
                mail.CC = cc
            if bcc:
                mail.BCC = bcc
            mail.Subject = subject

            if is_html:
                mail.BodyFormat = 2  # olFormatHTML
                html_body = body
                if not body.strip().lower().startswith("<html"):
                    html_body = f"<html><body>{body}</body></html>"
                mail.HTMLBody = html_body
            else:
                mail.Body = body

            importance_map = {"low": 0, "normal": 1, "high": 2}
            mail.Importance = importance_map.get(importance.lower(), 1)

            mail.Display(False)
            return {
                "to": to, "subject": subject, "cc": cc, "bcc": bcc,
                "importance": importance, "format": "html" if is_html else "text",
                "action": "Draft opened in Outlook for review"
            }

        result = execute_in_com_thread(_create_draft, timeout=30)
        if result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=f"Email draft created and opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _search_email(self, params: dict) -> SkillResult:
        """Search Outlook mailbox. Refactored from EmailSearchSkill."""
        import datetime

        sender = params.get("sender")
        recipient = params.get("recipient")
        subject = params.get("subject")
        body_contains = params.get("body_contains")
        days_back = params.get("days_back")
        has_attachments = params.get("has_attachments")
        unread_only = params.get("unread_only", False)
        importance = params.get("importance")
        folder_name = params.get("folder", "inbox").lower()
        max_results = min(params.get("max_results", 10), 500)
        semantic_query = params.get("semantic_query")
        include_body = params.get("include_body", True)

        # Determine if this is a "get recent" (no filters) or filtered search
        has_filters = any([sender, recipient, subject, body_contains,
                          has_attachments, unread_only, importance, semantic_query])

        if days_back is None:
            days_back = 365 if not has_filters or (sender and not subject and not body_contains) else 90
        days_back = max(1, min(days_back, 3650))

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)

        def _search(outlook, namespace, **kw):
            # Get folder
            if folder_name == "all":
                folders_to_search = [
                    namespace.GetDefaultFolder(6),   # Inbox
                    namespace.GetDefaultFolder(5),   # Sent
                ]
            else:
                folder_id = FOLDER_MAP.get(folder_name, 6)
                folders_to_search = [namespace.GetDefaultFolder(folder_id)]

            all_results = []
            for folder in folders_to_search:
                items = folder.Items

                # Pass 1: Jet filter (boolean/integer fields)
                jet_parts = []
                if unread_only:
                    jet_parts.append("[UnRead] = True")
                if importance:
                    imp_map = {"low": 0, "normal": 1, "high": 2}
                    imp_val = imp_map.get(importance.lower())
                    if imp_val is not None:
                        jet_parts.append(f"[Importance] = {imp_val}")
                if jet_parts:
                    items = items.Restrict(" AND ".join(jet_parts))

                # Pass 2: DASL filter (text fields)
                dasl_parts = []
                if sender:
                    s = sender.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:sendername\" like '%{s}%' OR "
                        f"\"urn:schemas:httpmail:fromemail\" like '%{s}%'"
                    )
                if subject:
                    s = subject.replace("'", "''")
                    dasl_parts.append(f"\"urn:schemas:httpmail:subject\" like '%{s}%'")
                if body_contains:
                    s = body_contains.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:textdescription\" ci_phrasematch '{s}'"
                    )
                if recipient:
                    r = recipient.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:displayto\" like '%{r}%' OR "
                        f"\"urn:schemas:httpmail:displaycc\" like '%{r}%'"
                    )
                if dasl_parts:
                    dasl_filter = "@SQL=" + " AND ".join(f"({p})" for p in dasl_parts)
                    items = items.Restrict(dasl_filter)

                # Sort descending by date
                is_sent = (folder_name == "sent")
                sort_field = "[SentOn]" if is_sent else "[ReceivedTime]"
                items.Sort(sort_field, True)

                # Iterate with date cutoff
                item = items.GetFirst()
                candidates = []
                while item and len(candidates) < max_results * 3:
                    try:
                        item_time = item.SentOn if is_sent else item.ReceivedTime
                        if item_time and hasattr(item_time, 'year'):
                            item_dt = datetime.datetime(
                                item_time.year, item_time.month, item_time.day,
                                item_time.hour, item_time.minute, item_time.second
                            )
                            if item_dt < cutoff_date:
                                break  # Sorted descending, done

                        # Python-side post-filters
                        if has_attachments is not None:
                            if bool(item.Attachments.Count > 0) != has_attachments:
                                item = items.GetNext()
                                continue

                        # Fuzzy sender matching
                        if sender and not self._fuzzy_match_sender(item, sender):
                            item = items.GetNext()
                            continue

                        candidates.append(self._extract_email_data(
                            item, include_body, is_sent
                        ))
                    except Exception as e:
                        logger.debug(f"Skipping item: {e}")
                    item = items.GetNext()

                all_results.extend(candidates)

            # Semantic ranking if requested
            if semantic_query and all_results:
                all_results = self._semantic_rank(all_results, semantic_query)

            return all_results[:max_results]

        result = execute_in_com_thread(_search, timeout=60)
        if result.success:
            items = result.data or []
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=f"Found {len(items)} email(s)",
                data={"items": items, "count": len(items), "folder": folder_name}
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _reply_email(self, params: dict) -> SkillResult:
        """Reply to the most recent email matching subject."""
        reply_subject = params.get("reply_subject", "")
        if not reply_subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'reply_subject' is required for reply_email")
        reply_body = params.get("reply_body", "")

        def _reply(outlook, namespace, **kw):
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            # Find most recent matching email
            subj_lower = reply_subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No email found matching subject: '{reply_subject}'"}

            reply = found.Reply()
            if reply_body:
                if self._is_html(reply_body):
                    reply.HTMLBody = reply_body + reply.HTMLBody
                else:
                    reply.Body = reply_body + "\n\n" + reply.Body
            reply.Display(False)
            return {
                "original_subject": found.Subject,
                "original_sender": getattr(found, 'SenderName', ''),
                "action": "Reply opened in Outlook for review"
            }

        result = execute_in_com_thread(_reply, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Reply draft opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _forward_email(self, params: dict) -> SkillResult:
        """Forward the most recent email matching subject."""
        reply_subject = params.get("reply_subject", "") or params.get("subject", "")
        forward_to = params.get("forward_to", "")
        if not reply_subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'reply_subject' or 'subject' is required for forward_email")
        if not forward_to:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'forward_to' is required for forward_email")
        reply_body = params.get("reply_body", "")

        def _forward(outlook, namespace, **kw):
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            subj_lower = reply_subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No email found matching subject: '{reply_subject}'"}

            fwd = found.Forward()
            fwd.To = forward_to
            if reply_body:
                if self._is_html(reply_body):
                    fwd.HTMLBody = reply_body + fwd.HTMLBody
                else:
                    fwd.Body = reply_body + "\n\n" + fwd.Body
            fwd.Display(False)
            return {
                "original_subject": found.Subject,
                "forward_to": forward_to,
                "action": "Forward opened in Outlook for review"
            }

        result = execute_in_com_thread(_forward, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Forward draft opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _execute_custom(self, params: dict) -> SkillResult:
        """Execute AI-generated custom COM code via sandbox."""
        code = params.get("custom_code", "")
        if not code:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'custom_code' is required for custom operation")

        sandbox = OutlookCOMSandbox()
        exec_result = sandbox.execute_code(code, timeout=30)

        if exec_result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=exec_result.message,
                data={"output": str(exec_result.output) if exec_result.output else None}
            )
        return SkillResult(
            success=False, skill_id=self.metadata.skill_id,
            error=exec_result.error
        )

    # --- Helper methods (refactored from existing skills) ---

    @staticmethod
    def _is_html(text: str) -> bool:
        """Check if text contains HTML tags."""
        lower = text.lower()
        html_tags = ["<html", "<p>", "<p ", "<div", "<br", "<table", "<ul", "<ol", "<h1", "<h2", "<h3"]
        return any(tag in lower for tag in html_tags)

    @staticmethod
    def _fuzzy_match_sender(item, query: str) -> bool:
        """Fuzzy match sender against query string."""
        try:
            sender_name = getattr(item, 'SenderName', '') or ''
            sender_email = ''
            try:
                if getattr(item, 'SenderEmailType', '') == "EX":
                    try:
                        sender_email = item.Sender.GetExchangeUser().PrimarySmtpAddress or ''
                    except Exception:
                        sender_email = getattr(item, 'SenderEmailAddress', '') or ''
                else:
                    sender_email = getattr(item, 'SenderEmailAddress', '') or ''
            except Exception:
                sender_email = getattr(item, 'SenderEmailAddress', '') or ''

            query_lower = query.lower()
            for field in [sender_name.lower(), sender_email.lower()]:
                if query_lower in field:
                    return True
                ratio = difflib.SequenceMatcher(None, query_lower, field).ratio()
                if ratio >= 0.4:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_email_data(item, include_body: bool, is_sent: bool) -> dict:
        """Extract data from an Outlook mail item."""
        try:
            sender_email = ''
            try:
                if getattr(item, 'SenderEmailType', '') == "EX":
                    try:
                        sender_email = item.Sender.GetExchangeUser().PrimarySmtpAddress or ''
                    except Exception:
                        try:
                            sender_email = item.PropertyAccessor.GetProperty(
                                "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
                            ) or ''
                        except Exception:
                            sender_email = getattr(item, 'SenderEmailAddress', '') or ''
                else:
                    sender_email = getattr(item, 'SenderEmailAddress', '') or ''
            except Exception:
                sender_email = getattr(item, 'SenderEmailAddress', '') or ''

            data = {
                "subject": getattr(item, 'Subject', '') or '',
                "sender_name": getattr(item, 'SenderName', '') or '',
                "sender_email": sender_email,
                "to": getattr(item, 'To', '') or '',
                "cc": getattr(item, 'CC', '') or '',
                "received_time": str(item.SentOn if is_sent else item.ReceivedTime),
                "has_attachments": item.Attachments.Count > 0,
                "attachment_count": item.Attachments.Count,
                "unread": getattr(item, 'UnRead', False),
                "importance": {0: "low", 1: "normal", 2: "high"}.get(
                    getattr(item, 'Importance', 1), "normal"
                ),
            }
            if include_body:
                body = getattr(item, 'Body', '') or ''
                data["body_preview"] = body[:500]

            # Attachment names (up to 10)
            if data["has_attachments"]:
                names = []
                for i in range(1, min(item.Attachments.Count + 1, 11)):
                    try:
                        names.append(item.Attachments.Item(i).FileName)
                    except Exception:
                        pass
                data["attachment_names"] = names

            return data
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _semantic_rank(items: list, query: str) -> list:
        """Rank items by semantic relevance using TF-IDF or word overlap."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts = [
                f"{item.get('subject', '')} {item.get('body_preview', '')} "
                f"{item.get('sender_name', '')}"
                for item in items
            ]
            texts.insert(0, query)
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            ranked = sorted(zip(items, similarities), key=lambda x: x[1], reverse=True)
            return [item for item, _ in ranked]
        except ImportError:
            # Fallback: simple word overlap
            query_words = set(query.lower().split())
            def score(item):
                text = f"{item.get('subject', '')} {item.get('body_preview', '')}".lower()
                return sum(1 for w in query_words if w in text)
            return sorted(items, key=score, reverse=True)

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Outlook email operation succeeded: {result.message}")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Outlook email operation failed: {result.error}")
```

**Step 2: Commit**

```bash
git add specter/src/infrastructure/skills/skills_library/outlook_email_skill.py
git commit -m "feat(skills): Add unified OutlookEmailSkill with operation registry and COM sandbox"
```

---

## Task 7: Unified OutlookCalendarSkill

**Files:**
- Create: `specter/src/infrastructure/skills/skills_library/outlook_calendar_skill.py`

**Step 1: Create OutlookCalendarSkill**

Same pattern as OutlookEmailSkill. Consolidates `calendar_event_skill.py` and `calendar_search_skill.py`.

```python
"""Unified Outlook calendar skill with operation registry and COM sandbox."""

import datetime
import difflib
import logging
from typing import Any, Dict, List, Optional

from ..core.base_skill import BaseSkill, SkillMetadata, SkillParameter, SkillResult
from ..core.base_skill import SkillCategory, PermissionType
from ..core.outlook_com_bridge import (
    execute_in_com_thread, OutlookCOMSandbox,
)

logger = logging.getLogger("specter.outlook_calendar_skill")

ALL_OPERATIONS = [
    "create_event",
    "search_events",
    "update_event",
    "cancel_event",
    "custom",
]

# Datetime formats to try when parsing user input
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]

MEETING_STATUS_MAP = {
    0: "nonmeeting", 1: "meeting", 3: "received",
    5: "cancelled", 7: "received_cancelled",
}
BUSY_STATUS_MAP = {
    0: "free", 1: "tentative", 2: "busy", 3: "oof", 4: "working_elsewhere",
}
RECURRENCE_MAP = {
    0: "daily", 1: "weekly", 2: "monthly",
    3: "monthly_nth", 5: "yearly", 6: "yearly_nth",
}


class OutlookCalendarSkill(BaseSkill):
    """Unified Outlook calendar skill with operation registry and COM sandbox."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="outlook_calendar",
            name="Outlook Calendar",
            description=(
                "Manage Outlook calendar: create events, search for appointments, "
                "update or cancel events, and run custom calendar operations. "
                "Operations: " + ", ".join(ALL_OPERATIONS)
            ),
            version="1.0.0",
            category=SkillCategory.PRODUCTIVITY,
            ai_callable=True,
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
        )

    @property
    def parameters(self) -> list:
        return [
            SkillParameter("operation", str, required=True,
                          description=f"Operation to perform. One of: {', '.join(ALL_OPERATIONS)}",
                          constraints={"choices": ALL_OPERATIONS}),
            # create_event / update_event params
            SkillParameter("subject", str, required=False,
                          description="Event subject/title",
                          constraints={"min_length": 1, "max_length": 255}),
            SkillParameter("start", str, required=False,
                          description="Start datetime (e.g., '2026-02-25 14:00')"),
            SkillParameter("end", str, required=False,
                          description="End datetime (e.g., '2026-02-25 15:00')"),
            SkillParameter("location", str, required=False,
                          description="Event location",
                          constraints={"max_length": 255}),
            SkillParameter("body", str, required=False,
                          description="Event notes/description",
                          constraints={"max_length": 10000}),
            SkillParameter("reminder_minutes", int, required=False,
                          description="Reminder minutes before event (0=none, max 10080)"),
            SkillParameter("attendees", str, required=False,
                          description="Comma-separated attendee email addresses",
                          constraints={"max_length": 1000}),
            # search_events params
            SkillParameter("start_date", str, required=False,
                          description="Search start date (YYYY-MM-DD, default: today)"),
            SkillParameter("end_date", str, required=False,
                          description="Search end date (YYYY-MM-DD)"),
            SkillParameter("days_ahead", int, required=False,
                          description="Search N days ahead (1-365, default: 7)"),
            SkillParameter("attendee", str, required=False,
                          description="Filter by attendee name or email"),
            SkillParameter("include_recurring", bool, required=False,
                          description="Include recurring event instances (default: true)"),
            SkillParameter("max_results", int, required=False,
                          description="Maximum results (1-200)",
                          constraints={"min_value": 1, "max_value": 200}),
            # cancel_event params
            SkillParameter("cancel_subject", str, required=False,
                          description="Subject of event to cancel"),
            # custom params
            SkillParameter("custom_code", str, required=False,
                          description="Python code for custom calendar operations (sandboxed)"),
        ]

    async def execute(self, **params) -> SkillResult:
        operation = params.get("operation", "")
        if operation not in ALL_OPERATIONS:
            return SkillResult(
                success=False,
                skill_id=self.metadata.skill_id,
                error=f"Unknown operation: '{operation}'. Valid: {', '.join(ALL_OPERATIONS)}"
            )

        try:
            if operation == "create_event":
                return await self._create_event(params)
            elif operation == "search_events":
                return await self._search_events(params)
            elif operation == "update_event":
                return await self._update_event(params)
            elif operation == "cancel_event":
                return await self._cancel_event(params)
            elif operation == "custom":
                return await self._execute_custom(params)
        except Exception as e:
            logger.error(f"Operation '{operation}' failed: {e}", exc_info=True)
            return SkillResult(
                success=False, skill_id=self.metadata.skill_id,
                error=f"Operation '{operation}' failed: {e}"
            )

    def _parse_datetime(self, dt_str: str) -> Optional[datetime.datetime]:
        """Parse datetime string trying multiple formats."""
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None

    async def _create_event(self, params: dict) -> SkillResult:
        """Create and display a calendar event. Refactored from CalendarEventSkill."""
        subject = params.get("subject", "")
        start_str = params.get("start", "")
        end_str = params.get("end", "")

        if not subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'subject' is required for create_event")
        if not start_str or not end_str:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'start' and 'end' are required for create_event")

        start_dt = self._parse_datetime(start_str)
        end_dt = self._parse_datetime(end_str)
        if not start_dt or not end_dt:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error=f"Cannot parse datetime. Supported formats: YYYY-MM-DD HH:MM")
        if end_dt <= start_dt:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="End time must be after start time")

        location = params.get("location", "")
        body = params.get("body", "")
        reminder_minutes = params.get("reminder_minutes", 15)
        attendees_str = params.get("attendees", "")

        def _create(outlook, namespace, **kw):
            appt = outlook.CreateItem(1)  # olAppointmentItem
            appt.Subject = subject
            appt.Start = start_dt.strftime("%Y-%m-%d %H:%M")
            appt.End = end_dt.strftime("%Y-%m-%d %H:%M")
            if location:
                appt.Location = location
            if body:
                appt.Body = body

            if reminder_minutes and reminder_minutes > 0:
                appt.ReminderSet = True
                appt.ReminderMinutesBeforeStart = min(reminder_minutes, 10080)
            else:
                appt.ReminderSet = False

            attendees_list = []
            if attendees_str:
                for email in attendees_str.split(","):
                    email = email.strip()
                    if email:
                        appt.Recipients.Add(email)
                        attendees_list.append(email)
                appt.MeetingStatus = 1  # olMeeting

            appt.Display(False)

            duration = int((end_dt - start_dt).total_seconds() / 60)
            return {
                "subject": subject,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "location": location,
                "duration_minutes": duration,
                "attendees": attendees_list,
                "is_meeting": bool(attendees_list),
                "reminder_minutes": reminder_minutes,
                "action": "Event opened in Outlook for review"
            }

        result = execute_in_com_thread(_create, timeout=30)
        if result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Calendar event created and opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _search_events(self, params: dict) -> SkillResult:
        """Search Outlook calendar. Refactored from CalendarSearchSkill."""
        subject = params.get("subject")
        location = params.get("location")
        attendee = params.get("attendee")
        days_ahead = max(1, min(params.get("days_ahead", 7), 365))
        include_recurring = params.get("include_recurring", True)
        max_results = min(params.get("max_results", 25), 200)

        # Parse date range
        today = datetime.date.today()
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")

        if start_date_str:
            try:
                start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                start_dt = datetime.datetime.combine(today, datetime.time.min)
        else:
            start_dt = datetime.datetime.combine(today, datetime.time.min)

        if end_date_str:
            try:
                end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_dt = start_dt + datetime.timedelta(days=days_ahead)
        else:
            end_dt = start_dt + datetime.timedelta(days=days_ahead)

        def _search(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)  # olFolderCalendar
            items = calendar.Items

            # Sort MUST happen before IncludeRecurrences (Microsoft docs)
            items.Sort("[Start]")
            if include_recurring:
                items.IncludeRecurrences = True

            # DASL filter for subject/location (no date filter — locale issues)
            dasl_parts = []
            if subject:
                s = subject.replace("'", "''")
                dasl_parts.append(f"\"urn:schemas:httpmail:subject\" like '%{s}%'")
            if location:
                loc = location.replace("'", "''")
                dasl_parts.append(f"\"urn:schemas:calendar:location\" like '%{loc}%'")
            if dasl_parts:
                items = items.Restrict("@SQL=" + " AND ".join(f"({p})" for p in dasl_parts))

            # Python-side date iteration (locale-independent)
            results = []
            candidate_limit = max_results * 5 if attendee else max_results
            item = items.GetFirst()
            skip_count = 0
            max_skip = 50000

            while item and len(results) < candidate_limit and skip_count < max_skip:
                try:
                    item_start = item.Start
                    if not item_start or not hasattr(item_start, 'year'):
                        item = items.GetNext()
                        skip_count += 1
                        continue

                    item_start_dt = datetime.datetime(
                        item_start.year, item_start.month, item_start.day,
                        item_start.hour, item_start.minute, item_start.second
                    )

                    if item_start_dt < start_dt:
                        item = items.GetNext()
                        skip_count += 1
                        continue
                    if item_start_dt > end_dt:
                        break  # Sorted ascending, done

                    # Attendee filter
                    if attendee and not self._fuzzy_match_attendee(item, attendee):
                        item = items.GetNext()
                        continue

                    results.append(self._extract_event_data(item))
                except Exception as e:
                    logger.debug(f"Skipping calendar item: {e}")

                item = items.GetNext()
                skip_count += 1

            return results[:max_results]

        result = execute_in_com_thread(_search, timeout=60)
        if result.success:
            items = result.data or []
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=f"Found {len(items)} calendar event(s)",
                data={"items": items, "count": len(items)}
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _update_event(self, params: dict) -> SkillResult:
        """Find an event by subject and open it for editing."""
        subject = params.get("subject", "") or params.get("cancel_subject", "")
        if not subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'subject' is required for update_event")

        def _update(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)
            items = calendar.Items
            items.Sort("[Start]", True)  # Most recent first

            subj_lower = subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No event found matching subject: '{subject}'"}

            found.Display(False)
            return {
                "subject": found.Subject,
                "start": str(found.Start),
                "action": "Event opened in Outlook for editing"
            }

        result = execute_in_com_thread(_update, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Event opened for editing",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _cancel_event(self, params: dict) -> SkillResult:
        """Find an event and open it for user to cancel/delete."""
        cancel_subject = params.get("cancel_subject", "") or params.get("subject", "")
        if not cancel_subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'cancel_subject' or 'subject' is required for cancel_event")

        def _cancel(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)
            items = calendar.Items
            items.Sort("[Start]", True)

            subj_lower = cancel_subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No event found matching subject: '{cancel_subject}'"}

            # Open for user review — never auto-delete
            found.Display(False)
            return {
                "subject": found.Subject,
                "start": str(found.Start),
                "action": "Event opened in Outlook — user can cancel/delete manually"
            }

        result = execute_in_com_thread(_cancel, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Event opened for cancellation review",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _execute_custom(self, params: dict) -> SkillResult:
        """Execute AI-generated custom COM code via sandbox."""
        code = params.get("custom_code", "")
        if not code:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'custom_code' is required for custom operation")

        sandbox = OutlookCOMSandbox()
        exec_result = sandbox.execute_code(code, timeout=30)

        if exec_result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=exec_result.message,
                data={"output": str(exec_result.output) if exec_result.output else None}
            )
        return SkillResult(
            success=False, skill_id=self.metadata.skill_id,
            error=exec_result.error
        )

    # --- Helper methods ---

    @staticmethod
    def _fuzzy_match_attendee(item, query: str) -> bool:
        """Fuzzy match against organizer and all attendees."""
        try:
            query_lower = query.lower()
            # Check organizer
            organizer = getattr(item, 'Organizer', '') or ''
            if query_lower in organizer.lower():
                return True
            if difflib.SequenceMatcher(None, query_lower, organizer.lower()).ratio() >= 0.4:
                return True

            # Check recipients
            for i in range(1, item.Recipients.Count + 1):
                try:
                    recip = item.Recipients.Item(i)
                    name = recip.Name or ''
                    email = ''
                    try:
                        addr_entry = recip.AddressEntry
                        if addr_entry.Type == "EX":
                            try:
                                email = addr_entry.GetExchangeUser().PrimarySmtpAddress or ''
                            except Exception:
                                email = addr_entry.Address or ''
                        else:
                            email = addr_entry.Address or ''
                    except Exception:
                        pass

                    for field in [name.lower(), email.lower()]:
                        if query_lower in field:
                            return True
                        if difflib.SequenceMatcher(None, query_lower, field).ratio() >= 0.4:
                            return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_event_data(item) -> dict:
        """Extract data from an Outlook appointment item."""
        try:
            # Attendees
            attendees = []
            try:
                for i in range(1, item.Recipients.Count + 1):
                    try:
                        recip = item.Recipients.Item(i)
                        email = ''
                        try:
                            addr_entry = recip.AddressEntry
                            if addr_entry.Type == "EX":
                                try:
                                    email = addr_entry.GetExchangeUser().PrimarySmtpAddress or ''
                                except Exception:
                                    email = addr_entry.Address or ''
                            else:
                                email = addr_entry.Address or ''
                        except Exception:
                            pass
                        response_map = {0: "none", 1: "organizer", 2: "tentative",
                                       3: "accepted", 4: "declined"}
                        attendees.append({
                            "name": recip.Name or '',
                            "email": email,
                            "response_status": response_map.get(recip.MeetingResponseStatus, "unknown")
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            # Recurrence
            is_recurring = getattr(item, 'IsRecurring', False)
            recurrence_pattern = ""
            if is_recurring:
                try:
                    rp = item.GetRecurrencePattern()
                    recurrence_pattern = RECURRENCE_MAP.get(rp.RecurrenceType, "unknown")
                except Exception:
                    recurrence_pattern = "unknown"

            # Duration
            start_time = item.Start
            end_time = item.End
            duration = 0
            try:
                start_dt = datetime.datetime(
                    start_time.year, start_time.month, start_time.day,
                    start_time.hour, start_time.minute
                )
                end_dt = datetime.datetime(
                    end_time.year, end_time.month, end_time.day,
                    end_time.hour, end_time.minute
                )
                duration = int((end_dt - start_dt).total_seconds() / 60)
            except Exception:
                pass

            body = getattr(item, 'Body', '') or ''

            return {
                "subject": getattr(item, 'Subject', '') or '',
                "start": str(start_time),
                "end": str(end_time),
                "duration_minutes": duration,
                "location": getattr(item, 'Location', '') or '',
                "organizer": getattr(item, 'Organizer', '') or '',
                "attendees": attendees,
                "body_preview": body[:300],
                "is_recurring": is_recurring,
                "recurrence_pattern": recurrence_pattern,
                "categories": getattr(item, 'Categories', '') or '',
                "is_all_day": getattr(item, 'AllDayEvent', False),
                "meeting_status": MEETING_STATUS_MAP.get(
                    getattr(item, 'MeetingStatus', 0), "nonmeeting"
                ),
                "busy_status": BUSY_STATUS_MAP.get(
                    getattr(item, 'BusyStatus', 2), "busy"
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Outlook calendar operation succeeded: {result.message}")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Outlook calendar operation failed: {result.error}")
```

**Step 2: Commit**

```bash
git add specter/src/infrastructure/skills/skills_library/outlook_calendar_skill.py
git commit -m "feat(skills): Add unified OutlookCalendarSkill with operation registry and COM sandbox"
```

---

## Task 8: Migration — Update Registrations and Tool Bridge

**Files:**
- Modify: `specter/src/infrastructure/skills/skills_library/__init__.py`
- Modify: `specter/src/application/app_coordinator.py:294-338`
- Modify: `specter/src/infrastructure/skills/core/tool_bridge.py:149-180`

**Step 1: Update skills_library/__init__.py**

Replace the entire file:

```python
"""
Skills Library - Built-in skills for Specter.

Each skill implements the BaseSkill interface and can be registered with the SkillManager.
"""

# Outlook skills (unified)
from .outlook_email_skill import OutlookEmailSkill
from .outlook_calendar_skill import OutlookCalendarSkill

# File operations
from .file_search_skill import FileSearchSkill

# Screen capture
from .screen_capture_skill import ScreenCaptureSkill

# Task tracking
from .task_tracker_skill import TaskTrackerSkill

# Web search
from .web_search_skill import WebSearchSkill

# Document formatting
from .docx_formatter_skill import DocxFormatterSkill

__all__ = [
    "OutlookEmailSkill",
    "OutlookCalendarSkill",
    "FileSearchSkill",
    "ScreenCaptureSkill",
    "TaskTrackerSkill",
    "WebSearchSkill",
    "DocxFormatterSkill",
]
```

**Step 2: Update app_coordinator.py skill imports and registration**

In `_initialize_skills_system()` (lines 300-311), replace the import block:

```python
                from ..infrastructure.skills.skills_library import (
                    OutlookEmailSkill,
                    OutlookCalendarSkill,
                    FileSearchSkill,
                    ScreenCaptureSkill,
                    TaskTrackerSkill,
                    WebSearchSkill,
                    DocxFormatterSkill,
                )
```

And update the `skills_to_register` list (lines 314-324) to use the new skill classes:

```python
                skills_to_register = [
                    OutlookEmailSkill,
                    OutlookCalendarSkill,
                    FileSearchSkill,
                    ScreenCaptureSkill,
                    TaskTrackerSkill,
                    WebSearchSkill,
                    DocxFormatterSkill,
                ]
```

**Step 3: Update tool_bridge.py USAGE_EXAMPLES**

In `build_tool_awareness_prompt()` (lines 149-180), replace the four old skill entries with two new ones:

```python
            "outlook_email": (
                "User says 'draft an email', 'search my inbox', 'reply to the email from John', "
                "'forward that email to Sarah', or asks to do something custom with email. "
                "Parameters: operation (required: draft_email/search_email/reply_email/forward_email/custom), "
                "to, subject, body, cc, bcc, html, importance, sender, recipient, body_contains, "
                "days_back, has_attachments, unread_only, folder, max_results, semantic_query, "
                "include_body, reply_subject, forward_to, reply_body, custom_code"
            ),
            "outlook_calendar": (
                "User says 'schedule a meeting', 'what meetings do I have this week', "
                "'update my 3pm meeting', 'cancel the standup', or asks to do something custom with calendar. "
                "Parameters: operation (required: create_event/search_events/update_event/cancel_event/custom), "
                "subject, start, end, location, body, reminder_minutes, attendees, "
                "start_date, end_date, days_ahead, attendee, include_recurring, max_results, "
                "cancel_subject, custom_code"
            ),
```

Remove the old `"email_draft"`, `"email_search"`, `"calendar_event"`, and `"calendar_search"` entries.

**Step 4: Commit**

```bash
git add specter/src/infrastructure/skills/skills_library/__init__.py
git add specter/src/application/app_coordinator.py
git add specter/src/infrastructure/skills/core/tool_bridge.py
git commit -m "refactor(skills): Migrate to unified Outlook skills, update registrations and tool bridge"
```

---

## Task 9: Remove Old Skill Files

**Files:**
- Delete: `specter/src/infrastructure/skills/skills_library/email_draft_skill.py`
- Delete: `specter/src/infrastructure/skills/skills_library/email_search_skill.py`
- Delete: `specter/src/infrastructure/skills/skills_library/calendar_event_skill.py`
- Delete: `specter/src/infrastructure/skills/skills_library/calendar_search_skill.py`

**Step 1: Delete old files**

```bash
git rm specter/src/infrastructure/skills/skills_library/email_draft_skill.py
git rm specter/src/infrastructure/skills/skills_library/email_search_skill.py
git rm specter/src/infrastructure/skills/skills_library/calendar_event_skill.py
git rm specter/src/infrastructure/skills/skills_library/calendar_search_skill.py
```

**Step 2: Commit**

```bash
git commit -m "refactor(skills): Remove legacy email/calendar skills replaced by unified versions"
```

---

## Task 10: Smoke Test and Verification

**Step 1: Run the application**

```bash
python -m specter --debug
```

**Step 2: Verify embedding settings**

1. Open Settings → Advanced
2. Confirm "Embedding Provider" group appears with Base URL, API Key, Model fields
3. Leave all empty → verify embeddings use AI Model settings (check logs)
4. Set a custom embedding URL → verify it's used instead

**Step 3: Verify Outlook skills**

1. Open a chat and ask "draft an email to test@example.com about Hello World"
2. Verify the AI calls `outlook_email` with `operation=draft_email`
3. Ask "search my inbox for emails from John"
4. Verify the AI calls `outlook_email` with `operation=search_email`
5. Ask "what meetings do I have this week"
6. Verify the AI calls `outlook_calendar` with `operation=search_events`

**Step 4: Check logs**

```bash
tail -50 "%APPDATA%\Specter\logs\specter.log"
```

Verify no import errors, no missing skill registration errors, no broken tool definitions.

**Step 5: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: Address issues from smoke testing"
```
