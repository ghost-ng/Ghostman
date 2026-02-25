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
