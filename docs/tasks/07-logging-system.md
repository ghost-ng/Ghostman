# Logging System Implementation Plan

## Overview

This document outlines the comprehensive logging system requirements for Ghostman, covering structured logging, performance monitoring, error tracking, security considerations, and compliance with Windows application logging standards. The logging system must work without administrator permissions and store logs in the appropriate %APPDATA% directory.

## Logging Architecture

### Core Requirements

1. **No Admin Permissions**: All logging operations must work with standard user privileges
2. **Structured Logging**: JSON-based structured logging for better parsing and analysis
3. **Performance Monitoring**: Track application performance metrics and bottlenecks
4. **Error Tracking**: Comprehensive error logging with context and stack traces
5. **Security**: Sensitive data filtering and secure log storage
6. **Compliance**: Follow Windows application logging best practices

### Log Storage Location

All log files must be stored in the appropriate `%APPDATA%\Ghostman\logs\` directory to ensure:
- User-level data isolation
- No admin permissions required
- Compliance with Windows application data storage conventions
- Easy access for troubleshooting and support

## Logging Categories

### 1. Application Logs
- Application startup and shutdown events
- UI state transitions (maximized avatar mode ↔ minimized tray mode)
- Settings changes and configuration updates
- Window management operations (positioning, opacity changes)

### 2. AI Service Logs
- API request/response cycles with timing
- Model selection and configuration changes
- Token usage tracking and limits
- Streaming response handling
- Error conditions and retry attempts

### 3. Conversation Management Logs
- Conversation creation, loading, and saving
- Memory management operations (trimming, summarization)
- Search and retrieval operations
- Data persistence operations

### 4. Security and Privacy Logs
- Authentication events (API key validation)
- Encryption operations for sensitive data
- Data cleanup and secure deletion events
- Privacy setting changes

### 5. Performance Logs
- Application startup time measurements
- UI responsiveness metrics
- Memory usage tracking
- API response times
- File I/O performance

### 6. System Integration Logs
- System tray operations
- Multi-monitor detection and handling
- Always-on-top behavior management
- State transition events

## Implementation Details

### 1. Logging Configuration

**File**: `ghostman/src/infrastructure/logging/logging_config.py`

```python
import logging
import logging.handlers
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class LogEntry:
    """Structured log entry with consistent format."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line: int
    thread_id: int
    process_id: int
    context: Dict[str, Any] = None
    error_details: Optional[Dict[str, str]] = None
    performance_metrics: Optional[Dict[str, float]] = None
    sensitive_data_filtered: bool = False

class SensitiveDataFilter:
    """Filter sensitive data from log messages."""
    
    SENSITIVE_PATTERNS = [
        r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9-_]{20,})["\']?',
        r'password["\']?\s*[:=]\s*["\']?([^"\']+)["\']?',
        r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9-_]{20,})["\']?',
        r'bearer\s+([a-zA-Z0-9-_]{20,})',
        r'authorization["\']?\s*[:=]\s*["\']?([^"\']+)["\']?'
    ]
    
    def __init__(self):
        import re
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS]
    
    def filter_message(self, message: str) -> tuple[str, bool]:
        """Filter sensitive data from message, return (filtered_message, was_filtered)."""
        original_message = message
        filtered = False
        
        for pattern in self.patterns:
            if pattern.search(message):
                message = pattern.sub(lambda m: f"{m.group().split('=')[0]}=***FILTERED***", message)
                filtered = True
        
        return message, filtered

class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self):
        super().__init__()
        self.sensitive_filter = SensitiveDataFilter()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Filter sensitive data
        filtered_message, was_filtered = self.sensitive_filter.filter_message(record.getMessage())
        
        # Extract error details if exception info is present
        error_details = None
        if record.exc_info:
            import traceback
            error_details = {
                'exception_type': record.exc_info[0].__name__,
                'exception_message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Extract performance metrics from record if available
        performance_metrics = getattr(record, 'performance_metrics', None)
        context = getattr(record, 'context', None)
        
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=filtered_message,
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            thread_id=record.thread,
            process_id=record.process,
            context=context,
            error_details=error_details,
            performance_metrics=performance_metrics,
            sensitive_data_filtered=was_filtered
        )
        
        return json.dumps(asdict(log_entry), default=str, ensure_ascii=False)

class LoggingConfig:
    """Centralized logging configuration for Ghostman."""
    
    def __init__(self, app_data_dir: Path, log_level: str = "INFO"):
        self.app_data_dir = Path(app_data_dir)
        self.log_dir = self.app_data_dir / "logs"
        self.log_level = getattr(logging, log_level.upper())
        
        # Create logs directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Define log files
        self.log_files = {
            'main': self.log_dir / "ghostman.log",
            'ai_service': self.log_dir / "ai_service.log",
            'conversations': self.log_dir / "conversations.log",
            'performance': self.log_dir / "performance.log",
            'security': self.log_dir / "security.log",
            'errors': self.log_dir / "errors.log"
        }
        
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging system."""
        # Remove existing handlers to avoid duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Setup root logger
        root_logger.setLevel(self.log_level)
        
        # Create formatters
        json_formatter = StructuredJSONFormatter()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Setup file handlers with rotation
        file_handlers = {}
        for log_name, log_file in self.log_files.items():
            # Rotating file handler (10MB max, keep 5 backups)
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            handler.setLevel(self.log_level)
            handler.setFormatter(json_formatter)
            file_handlers[log_name] = handler
        
        # Configure specific loggers
        self.setup_logger('ghostman.main', [console_handler, file_handlers['main']])
        self.setup_logger('ghostman.ai', [file_handlers['ai_service']])
        self.setup_logger('ghostman.conversations', [file_handlers['conversations']])
        self.setup_logger('ghostman.performance', [file_handlers['performance']])
        self.setup_logger('ghostman.security', [file_handlers['security']])
        
        # Error logger gets all error-level messages
        error_handler = file_handlers['errors']
        error_handler.setLevel(logging.ERROR)
        error_logger = logging.getLogger('ghostman.errors')
        error_logger.addHandler(error_handler)
        error_logger.propagate = False
        
        # Add error handler to all loggers to capture errors centrally
        for logger_name in ['ghostman.main', 'ghostman.ai', 'ghostman.conversations', 
                           'ghostman.performance', 'ghostman.security']:
            logger = logging.getLogger(logger_name)
            logger.addHandler(error_handler)
    
    def setup_logger(self, name: str, handlers: list):
        """Setup individual logger with specified handlers."""
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add new handlers
        for handler in handlers:
            logger.addHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get configured logger by name."""
        return logging.getLogger(f"ghostman.{name}")
    
    def cleanup(self):
        """Cleanup logging resources."""
        # Close all file handlers
        for handler in logging.getLogger().handlers[:]:
            if isinstance(handler, (logging.FileHandler, logging.handlers.RotatingFileHandler)):
                handler.close()
```

### 2. Performance Monitoring Service

**File**: `ghostman/src/infrastructure/logging/performance_monitor.py`

```python
import time
import psutil
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from functools import wraps
import logging

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation: str
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: float
    context: Optional[Dict[str, Any]] = None

class PerformanceMonitor:
    """Monitor and log application performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._metrics_cache = []
        self._cache_lock = threading.Lock()
        self._monitoring_enabled = True
        
        # Start background metrics collection
        self._monitor_thread = threading.Thread(target=self._system_metrics_loop, daemon=True)
        self._monitor_thread.start()
    
    def _system_metrics_loop(self):
        """Background thread for system metrics collection."""
        while self._monitoring_enabled:
            try:
                # Collect system metrics every 30 seconds
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                
                self.logger.info(
                    "System metrics collected",
                    extra={
                        'performance_metrics': {
                            'memory_usage_percent': memory_info.percent,
                            'memory_available_mb': memory_info.available / 1024 / 1024,
                            'cpu_usage_percent': cpu_percent,
                            'active_threads': threading.active_count()
                        }
                    }
                )
                
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                time.sleep(60)  # Wait longer on error
    
    @contextmanager
    def measure_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """Context manager for measuring operation performance."""
        start_time = time.perf_counter()
        start_memory = self._get_current_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            end_memory = self._get_current_memory_usage()
            memory_delta = end_memory - start_memory
            
            metrics = PerformanceMetrics(
                operation=operation_name,
                duration_ms=duration_ms,
                memory_usage_mb=memory_delta,
                cpu_usage_percent=psutil.cpu_percent(),
                timestamp=end_time,
                context=context
            )
            
            self._log_metrics(metrics)
    
    def measure_function(self, operation_name: Optional[str] = None):
        """Decorator for measuring function performance."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                with self.measure_operation(op_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _get_current_memory_usage(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _log_metrics(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self.logger.info(
            f"Performance: {metrics.operation} completed",
            extra={
                'performance_metrics': {
                    'operation': metrics.operation,
                    'duration_ms': metrics.duration_ms,
                    'memory_delta_mb': metrics.memory_usage_mb,
                    'cpu_usage_percent': metrics.cpu_usage_percent
                },
                'context': metrics.context
            }
        )
        
        # Cache metrics for analysis
        with self._cache_lock:
            self._metrics_cache.append(metrics)
            # Keep only last 1000 metrics to prevent memory growth
            if len(self._metrics_cache) > 1000:
                self._metrics_cache = self._metrics_cache[-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        with self._cache_lock:
            if not self._metrics_cache:
                return {}
            
            # Calculate statistics
            operations = {}
            for metric in self._metrics_cache:
                op = metric.operation
                if op not in operations:
                    operations[op] = []
                operations[op].append(metric.duration_ms)
            
            summary = {}
            for op, durations in operations.items():
                summary[op] = {
                    'count': len(durations),
                    'avg_duration_ms': sum(durations) / len(durations),
                    'min_duration_ms': min(durations),
                    'max_duration_ms': max(durations),
                    'total_duration_ms': sum(durations)
                }
            
            return summary
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_enabled = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
```

### 3. Security Logging Service

**File**: `ghostman/src/infrastructure/logging/security_logger.py`

```python
import logging
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: str
    severity: str
    description: str
    user_context: Optional[Dict[str, Any]] = None
    system_context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_authentication_attempt(self, success: bool, provider: str, 
                                 error_message: Optional[str] = None):
        """Log authentication attempts."""
        event = SecurityEvent(
            event_type="authentication",
            severity="INFO" if success else "WARNING",
            description=f"AI provider authentication {'successful' if success else 'failed'}",
            user_context={'provider': provider},
            system_context={'error': error_message} if error_message else None,
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_data_encryption(self, operation: str, data_type: str, success: bool):
        """Log encryption operations."""
        event = SecurityEvent(
            event_type="encryption",
            severity="INFO" if success else "ERROR",
            description=f"Data encryption {operation} for {data_type}",
            user_context={'data_type': data_type, 'operation': operation},
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_sensitive_data_access(self, data_type: str, operation: str, 
                                context: Optional[Dict[str, Any]] = None):
        """Log access to sensitive data."""
        event = SecurityEvent(
            event_type="sensitive_data_access",
            severity="INFO",
            description=f"Sensitive data access: {operation} on {data_type}",
            user_context=context or {},
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_configuration_change(self, setting_name: str, old_value_hash: str, 
                               new_value_hash: str, user_initiated: bool = True):
        """Log security-relevant configuration changes."""
        event = SecurityEvent(
            event_type="configuration_change",
            severity="INFO",
            description=f"Security configuration changed: {setting_name}",
            user_context={
                'setting': setting_name,
                'old_value_hash': old_value_hash,
                'new_value_hash': new_value_hash,
                'user_initiated': user_initiated
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_data_cleanup(self, operation: str, data_type: str, 
                        records_affected: int, secure_deletion: bool = False):
        """Log data cleanup and deletion operations."""
        event = SecurityEvent(
            event_type="data_cleanup",
            severity="INFO",
            description=f"Data cleanup: {operation} on {data_type}",
            user_context={
                'operation': operation,
                'data_type': data_type,
                'records_affected': records_affected,
                'secure_deletion': secure_deletion
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_privacy_violation_attempt(self, violation_type: str, 
                                    description: str, blocked: bool = True):
        """Log potential privacy violations."""
        event = SecurityEvent(
            event_type="privacy_violation",
            severity="WARNING" if blocked else "ERROR",
            description=f"Privacy violation attempt: {violation_type}",
            user_context={
                'violation_type': violation_type,
                'description': description,
                'blocked': blocked
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def log_app_state_transition(self, from_state: str, to_state: str, 
                                trigger: str, user_initiated: bool = True):
        """Log application state transitions."""
        event = SecurityEvent(
            event_type="state_transition",
            severity="INFO",
            description=f"Application state changed: {from_state} -> {to_state}",
            user_context={
                'from_state': from_state,
                'to_state': to_state,
                'trigger': trigger,
                'user_initiated': user_initiated
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        self._log_security_event(event)
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event with appropriate level."""
        log_method = getattr(self.logger, event.severity.lower())
        log_method(
            event.description,
            extra={
                'context': {
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'user_context': event.user_context,
                    'system_context': event.system_context,
                    'timestamp': event.timestamp
                }
            }
        )
    
    @staticmethod
    def hash_sensitive_value(value: str) -> str:
        """Create hash of sensitive value for logging comparison."""
        if not value:
            return ""
        return hashlib.sha256(value.encode()).hexdigest()[:16]  # First 16 chars for brevity
```

### 4. AI Service Logging Integration

**File**: `ghostman/src/infrastructure/logging/ai_service_logger.py`

```python
import logging
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

@dataclass
class APICallMetrics:
    """Metrics for AI API calls."""
    request_id: str
    provider: str
    model: str
    request_tokens: int
    response_tokens: int
    total_tokens: int
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

class AIServiceLogger:
    """Specialized logger for AI service operations."""
    
    def __init__(self, logger: logging.Logger, performance_monitor):
        self.logger = logger
        self.performance_monitor = performance_monitor
        self._active_requests = {}
    
    def log_api_request_start(self, request_id: str, provider: str, model: str, 
                            messages: List[Dict], parameters: Dict[str, Any]):
        """Log the start of an API request."""
        # Estimate token count (rough approximation)
        estimated_tokens = self._estimate_token_count(messages)
        
        self._active_requests[request_id] = {
            'start_time': time.perf_counter(),
            'provider': provider,
            'model': model,
            'estimated_tokens': estimated_tokens
        }
        
        self.logger.info(
            f"AI API request started: {provider}/{model}",
            extra={
                'context': {
                    'request_id': request_id,
                    'provider': provider,
                    'model': model,
                    'estimated_input_tokens': estimated_tokens,
                    'parameters': parameters,
                    'message_count': len(messages)
                }
            }
        )
    
    def log_api_request_complete(self, request_id: str, success: bool, 
                               response_tokens: int = 0, total_tokens: int = 0,
                               error_message: Optional[str] = None):
        """Log the completion of an API request."""
        if request_id not in self._active_requests:
            self.logger.warning(f"Completed request {request_id} not found in active requests")
            return
        
        request_data = self._active_requests.pop(request_id)
        end_time = time.perf_counter()
        duration_ms = (end_time - request_data['start_time']) * 1000
        
        metrics = APICallMetrics(
            request_id=request_id,
            provider=request_data['provider'],
            model=request_data['model'],
            request_tokens=request_data['estimated_tokens'],
            response_tokens=response_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(end_time))
        )
        
        log_level = logging.INFO if success else logging.ERROR
        self.logger.log(
            log_level,
            f"AI API request {'completed' if success else 'failed'}: {metrics.provider}/{metrics.model}",
            extra={
                'performance_metrics': {
                    'duration_ms': duration_ms,
                    'tokens_per_second': response_tokens / (duration_ms / 1000) if duration_ms > 0 else 0,
                    'total_tokens': total_tokens
                },
                'context': asdict(metrics)
            }
        )
    
    def log_streaming_chunk(self, request_id: str, chunk_data: str, 
                          chunk_index: int, is_final: bool = False):
        """Log streaming response chunks."""
        self.logger.debug(
            f"Streaming chunk received for request {request_id}",
            extra={
                'context': {
                    'request_id': request_id,
                    'chunk_index': chunk_index,
                    'chunk_size': len(chunk_data),
                    'is_final_chunk': is_final
                }
            }
        )
    
    def log_model_change(self, old_model: str, new_model: str, provider: str):
        """Log AI model changes."""
        self.logger.info(
            f"AI model changed: {old_model} → {new_model}",
            extra={
                'context': {
                    'old_model': old_model,
                    'new_model': new_model,
                    'provider': provider,
                    'change_type': 'model_change'
                }
            }
        )
    
    def log_provider_change(self, old_provider: str, new_provider: str):
        """Log AI provider changes."""
        self.logger.info(
            f"AI provider changed: {old_provider} → {new_provider}",
            extra={
                'context': {
                    'old_provider': old_provider,
                    'new_provider': new_provider,
                    'change_type': 'provider_change'
                }
            }
        )
    
    def log_rate_limit_hit(self, provider: str, retry_after: Optional[int] = None):
        """Log rate limiting events."""
        self.logger.warning(
            f"Rate limit hit for provider {provider}",
            extra={
                'context': {
                    'provider': provider,
                    'retry_after_seconds': retry_after,
                    'event_type': 'rate_limit'
                }
            }
        )
    
    def log_token_usage_summary(self, conversation_id: str, 
                              total_input_tokens: int, total_output_tokens: int,
                              conversation_length: int):
        """Log conversation token usage summary."""
        self.logger.info(
            f"Conversation token usage summary",
            extra={
                'context': {
                    'conversation_id': conversation_id,
                    'total_input_tokens': total_input_tokens,
                    'total_output_tokens': total_output_tokens,
                    'total_tokens': total_input_tokens + total_output_tokens,
                    'conversation_length': conversation_length,
                    'avg_tokens_per_message': (total_input_tokens + total_output_tokens) / conversation_length if conversation_length > 0 else 0
                }
            }
        )
    
    def _estimate_token_count(self, messages: List[Dict]) -> int:
        """Rough estimation of token count for logging purposes."""
        total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
        # Rough approximation: 1 token ≈ 4 characters
        return max(1, total_chars // 4)

    def get_api_performance_stats(self) -> Dict[str, Any]:
        """Get API performance statistics."""
        # This would typically query logged data
        # For now, return placeholder
        return {
            'active_requests': len(self._active_requests),
            'performance_summary': self.performance_monitor.get_performance_summary()
        }
```

## Integration Requirements

### Update Existing Task Documents

The following documents need to be updated to reference the comprehensive logging system:

1. **Settings System (`02-settings-system.md`)**:
   - Add logging level configuration options
   - Include log file management settings
   - Add debug information export functionality

2. **AI Service Integration**:
   - Performance monitoring for API calls
   - Error tracking and retry logic logging
   - Token usage monitoring

3. **Conversation Memory System (`05-conversation-memory.md`)**:
   - Memory operation logging
   - Data persistence logging
   - Cleanup operation tracking

4. **Packaging and Deployment (`06-packaging-deployment.md`)**:
   - Log file handling in packaged application
   - Log rotation and cleanup procedures
   - Troubleshooting log collection

### Compliance and Monitoring

#### Log Management
- **Automatic log rotation**: Prevent disk space issues
- **Log cleanup**: Automatic deletion of old logs based on settings
- **Log compression**: Compress archived logs to save space
- **Performance impact**: Minimal impact on application performance

#### Troubleshooting Support
- **Debug mode**: Enhanced logging for troubleshooting
- **Log export**: Easy export of relevant logs for support
- **Performance analysis**: Built-in performance metric analysis
- **Error correlation**: Link related errors across different log files

This comprehensive logging system ensures robust monitoring, debugging capabilities, and security compliance while maintaining the no-admin-permissions requirement and proper Windows application data storage practices.