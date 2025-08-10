"""
Logging Configuration for Ghostman.

Provides structured logging with JSON output and performance monitoring.
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
try:  # Optional import (PyQt may not be present in some tooling contexts)
    from PyQt6.QtCore import QStandardPaths  # type: ignore
except Exception:  # pragma: no cover
    QStandardPaths = None


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'exc_info', 'exc_text', 'stack_info'):
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)


def _resolve_log_dir() -> Path:
    """Determine the unified log directory under AppData/Ghostman/logs.

    Mirrors SettingsManager path conventions (Ghostman/configs sibling directory).
    """
    # Prefer Qt AppDataLocation for consistent cross‑platform behavior
    base_path: Path | None = None
    try:
        if QStandardPaths:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            if base:
                base_path = Path(base)
    except Exception:  # pragma: no cover
        base_path = None

    if base_path is None:
        # Fallback: LOCALAPPDATA on Windows, ~/.local/share on *nix
        if os.name == 'nt':
            base_env = os.environ.get('LOCALAPPDATA', str(Path.home()))
            base_path = Path(base_env)
        else:
            base_path = Path.home() / '.local' / 'share'

    # Avoid double Ghostman nesting
    if base_path.name.lower() == 'ghostman':
        ghostman_root = base_path
    else:
        ghostman_root = base_path / 'Ghostman'
    log_dir = ghostman_root / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(debug: bool = False, log_dir: str | None = None) -> None:
    """
    Setup logging configuration for Ghostman.
    
    Args:
        debug: Enable debug level logging
        log_dir: Directory for log files (defaults to user data dir)
    """
    # Determine log directory
    if log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
    else:
        log_dir_path = _resolve_log_dir()
        log_dir = str(log_dir_path)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not debug else logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File handler with JSON format
    log_file = str(log_dir_path / 'ghostman.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_file = str(log_dir_path / 'ghostman_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Set specific logger levels
    logging.getLogger("ghostman").setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger("ghostman.logging")
    logger.info(f"Logging initialized - Debug: {debug}, Log dir: {log_dir}")


def get_performance_logger() -> logging.Logger:
    """Get a logger specifically for performance metrics."""
    return logging.getLogger("ghostman.performance")


def log_performance(operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
    """
    Log performance metrics.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        metadata: Additional metadata
    """
    perf_logger = get_performance_logger()
    extra = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "metadata": metadata or {}
    }
    perf_logger.info(f"Performance: {operation} took {duration:.3f}s", extra=extra)