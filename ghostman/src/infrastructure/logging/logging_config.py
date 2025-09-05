"""
Logging Configuration for Ghostman.

Provides structured logging with JSON output and performance monitoring.
"""

import logging
import logging.handlers
import json
import os
import sys
import glob
from datetime import datetime, timedelta
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

    Uses the same path as config_paths to ensure consistency.
    """
    # Use the same logic as config_paths for consistency
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            base_path = Path(appdata) / "Ghostman"
        else:
            base_path = Path.home() / "AppData" / "Roaming" / "Ghostman"
    else:
        # Fallback for other platforms - use XDG standard
        xdg_data_home = os.environ.get('XDG_DATA_HOME')
        if xdg_data_home:
            base_path = Path(xdg_data_home) / "ghostman"
        else:
            base_path = Path.home() / ".local" / "share" / "ghostman"
    
    log_dir = base_path / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def cleanup_old_logs(log_dir: Path, retention_days: int) -> int:
    """
    Clean up old log files beyond the retention period.
    
    Args:
        log_dir: Directory containing log files
        retention_days: Number of days to retain log files
        
    Returns:
        Number of files cleaned up
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        # Pattern for rotated log files (both main and error logs)
        patterns = ['ghostman-*.log', 'ghostman-errors-*.log']
        
        for pattern in patterns:
            log_files = list(log_dir.glob(pattern))
            
            for log_file in log_files:
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        log_file.unlink()
                        cleaned_count += 1
                        print(f"Cleaned up old log file: {log_file.name}")
                        
                except (OSError, ValueError) as e:
                    print(f"Failed to clean up log file {log_file}: {e}")
                    continue
        
        if cleaned_count > 0:
            print(f"Log cleanup: removed {cleaned_count} old log file(s)")
        
        return cleaned_count
        
    except Exception as e:
        print(f"Error during log cleanup: {e}")
        return 0


def setup_logging(debug: bool = False, log_dir: str | None = None, retention_days: int = 10) -> None:
    """
    Setup logging configuration for Ghostman with daily rotation.
    
    Args:
        debug: Enable debug level logging
        log_dir: Directory for log files (defaults to user data dir)
        retention_days: Number of days to retain log files (default: 10)
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
    
    # Daily rotating file handler with JSON format
    log_file = str(log_dir_path / 'ghostman.log')
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',  # Rotate at midnight
        interval=1,       # Rotate every day
        backupCount=retention_days,  # Keep specified number of days
        encoding='utf-8'
    )
    file_handler.suffix = '-%Y-%m-%d.log'  # Format: ghostman-YYYY-MM-DD.log
    file_handler.extMatch = None  # Disable default extension matching
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Daily rotating error file handler
    error_file = str(log_dir_path / 'ghostman-errors.log')
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_file,
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    error_handler.suffix = '-%Y-%m-%d.log'  # Format: ghostman-errors-YYYY-MM-DD.log
    error_handler.extMatch = None  # Disable default extension matching
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Clean up old log files beyond retention period
    cleanup_old_logs(log_dir_path, retention_days)
    
    # Set specific logger levels
    logging.getLogger("ghostman").setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Suppress Qt internal warnings unless in debug mode
    if not debug:
        try:
            from PyQt6.QtCore import QLoggingCategory
            # Suppress Qt CSS parser warnings about unknown properties
            QLoggingCategory.setFilterRules("qt.css.debug=false")
            QLoggingCategory.setFilterRules("qt.css.warning=false") 
            QLoggingCategory.setFilterRules("*.debug=false")
        except ImportError:
            # PyQt6 not available or older version
            pass
    
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