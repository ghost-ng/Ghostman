# Single Instance Detection Implementation

## Overview

This document describes the robust single instance detection system implemented for Ghostman to prevent multiple instances from running simultaneously and causing the PermissionError with log file access.

## Features Implemented

### 1. Multi-Method Instance Detection

The system uses four complementary detection methods:

#### Primary Method: File Locking
- **Windows**: Detects file lock via `OSError` with errno 32 (file in use)
- **Unix/Linux**: Uses `fcntl.flock()` for exclusive file locking
- **Target**: Log file (`ghostman.log`) in the logs directory

#### Secondary Method: Lock File Creation
- Creates a lock file with process information (PID, timestamp, app name)
- Validates that the process referenced in the lock file is still running
- Automatically removes stale lock files from dead processes

#### Tertiary Method: Process Detection
- Scans running processes using `psutil` library
- Matches process names and command lines for "ghostman" keywords
- Filters out the current process to avoid false positives

#### Quaternary Method: Port Binding
- Attempts to bind to a specific port (default: 29842)
- Detects if another instance is using the application port
- Releases the socket immediately after testing

### 2. Theme-Aware Warning Dialog

#### Modern Styling Integration
- **ThemedInstanceWarningDialog**: Inherits from QDialog with full theming support
- **Automatic Theme Application**: Integrates with the existing ThemeManager system
- **Fallback Styling**: Graceful degradation to basic styling if theming fails
- **Responsive Layout**: Fixed size dialog (480x220) optimized for readability

#### User Interface Features
- **Warning Icon**: Displays warning icon from assets or Unicode fallback (⚠️)
- **Context-Aware Messages**: Different messages based on detection method
- **Action Buttons**: 
  - "Exit" button (default) - closes the application
  - "Switch to Existing" button (for future IPC implementation)

### 3. Application Integration

#### Startup Flow Integration
```python
# In GhostmanApplication.run()
1. Setup Qt Application (required for dialogs)
2. Check Single Instance (with dialog if needed)
3. Initialize App Coordinator (only if check passes)
4. Continue normal startup
```

#### Graceful Cleanup
```python
def _cleanup_application(self):
    - Shutdown coordinator safely
    - Release instance locks
    - Handle cleanup errors gracefully
```

### 4. Error Handling and Recovery

#### Lock File Management
- **Stale Lock Detection**: Validates process existence before considering locks valid
- **Automatic Cleanup**: Removes invalid lock files automatically
- **Error Recovery**: Handles file system errors and permission issues

#### Robust Error Handling
- **SingleInstanceError**: Custom exception for instance conflicts
- **Detailed Logging**: Comprehensive logging of detection methods and results
- **Graceful Degradation**: Application exits cleanly when conflicts detected

## Technical Implementation

### Core Classes

#### SingleInstanceDetector
```python
class SingleInstanceDetector:
    """Robust single instance detection system"""
    
    def detect_running_instance(self) -> InstanceDetectionResult:
        """Detect if another instance is running using multiple methods"""
    
    def acquire_instance_lock(self) -> bool:
        """Acquire the instance lock to prevent other instances"""
    
    def release_instance_lock(self):
        """Release the instance lock"""
```

#### InstanceDetectionResult
```python
class InstanceDetectionResult:
    """Result of instance detection check"""
    - is_running: bool
    - detection_method: str  
    - process_info: Optional[dict]
    - lock_file: Optional[str]
    - timestamp: float
```

#### ThemedInstanceWarningDialog
```python
class ThemedInstanceWarningDialog(QDialog):
    """Theme-aware warning dialog for single instance detection"""
    
    # Signals
    switch_to_existing = pyqtSignal()
    exit_application = pyqtSignal()
```

### File Locations

```
ghostman/src/application/
├── single_instance.py          # Main implementation
└── ...

ghostman/src/main.py             # Integration with startup flow
requirements.txt                 # Added psutil>=5.9.0 dependency
```

### Integration Points

#### Main Application
- **main.py**: Modified to include single instance checking before coordinator initialization
- **GhostmanApplication.check_single_instance()**: New method for instance validation
- **GhostmanApplication._cleanup_application()**: Enhanced cleanup with lock release

#### Theme System Integration
- **Theme Manager**: Dialog automatically applies current theme using existing ThemeManager
- **Style Registry**: Uses the modern styling system for consistent appearance
- **Icon Styling**: Applies clean icon styling to dialog buttons

## Usage Examples

### Basic Usage
```python
from ghostman.src.application.single_instance import check_single_instance

# Check for single instance with dialog
should_continue, result = check_single_instance(
    app_name="Ghostman",
    show_dialog=True,
    parent=None
)

if not should_continue:
    sys.exit(1)
```

### Context Manager Usage
```python
from ghostman.src.application.single_instance import SingleInstanceDetector, SingleInstanceError

try:
    with SingleInstanceDetector("Ghostman") as detector:
        # Application code here - lock is automatically acquired and released
        run_application()
except SingleInstanceError as e:
    print(f"Another instance detected: {e}")
    sys.exit(1)
```

### Manual Control
```python
detector = SingleInstanceDetector("Ghostman")
result = detector.detect_running_instance()

if result.is_running:
    print(f"Instance detected via {result.detection_method}")
    if result.process_info:
        print(f"Process info: {result.process_info}")
    sys.exit(1)

# Acquire lock manually
if detector.acquire_instance_lock():
    try:
        # Run application
        run_application()
    finally:
        detector.release_instance_lock()
```

## Platform Compatibility

### Windows
- **File Locking**: Uses OSError errno 32 detection
- **Process Detection**: Full psutil support
- **Lock Files**: Uses Windows-style paths in APPDATA
- **No fcntl**: Gracefully handles missing fcntl module

### Unix/Linux
- **File Locking**: Uses fcntl.flock() for proper file locking
- **Process Detection**: Full psutil support
- **Lock Files**: Uses XDG-compliant paths
- **Full fcntl**: Complete file locking support

### Cross-Platform Compatibility
- **Path Resolution**: Uses consistent path resolution with existing config system
- **Error Handling**: Platform-specific error code handling
- **Fallback Methods**: Multiple detection methods ensure reliability across platforms

## Security Considerations

### Lock File Security
- **Process Validation**: Validates process existence before trusting lock files
- **Stale Lock Cleanup**: Automatically removes locks from dead processes
- **Information Disclosure**: Lock files contain minimal information (PID, timestamp, app name)

### File System Permissions
- **Graceful Degradation**: Handles permission errors without crashing
- **Error Logging**: Logs permission issues for debugging
- **Multiple Methods**: Uses alternative detection if file system access fails

## Testing and Validation

### Automated Testing
The implementation includes comprehensive error handling and has been tested with:
- **Multiple Detection Methods**: All four methods tested individually
- **Lock Acquisition**: Verified lock acquisition and release cycles
- **Context Manager**: Validated automatic cleanup functionality
- **Dialog Theming**: Confirmed theme integration works correctly

### Manual Testing Scenarios
1. **Normal Startup**: Single instance starts successfully
2. **Second Instance**: Attempt to start second instance shows warning dialog
3. **Process Crash**: Stale locks are automatically cleaned up
4. **Permission Issues**: Graceful handling of file system permission errors

## Future Enhancements

### Inter-Process Communication (IPC)
- **Named Pipes**: Windows named pipe communication
- **Unix Sockets**: Unix domain socket communication
- **Window Activation**: Ability to bring existing instance to foreground

### Advanced Features
- **Instance Handoff**: Pass command line arguments to existing instance
- **Multi-User Support**: Per-user instance detection
- **Service Mode**: Integration with system service detection

## Resolution of Original Issue

The original PermissionError has been resolved through:

1. **Early Detection**: Instance conflicts detected before log file creation
2. **Multiple Methods**: Comprehensive detection ensures conflicts are caught
3. **Graceful Exit**: Application exits cleanly without attempting log file access
4. **User Notification**: Clear dialog explains the situation to users
5. **Automatic Cleanup**: Stale locks are removed to prevent false positives

The system prevents the error by detecting conflicts before they occur, rather than trying to handle the permission error after it happens.