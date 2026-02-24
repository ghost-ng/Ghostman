"""
Single Instance Detection for Specter Application.

Provides robust single instance detection using multiple methods:
- File locking on the log file
- Process detection by name
- Port binding detection
- Lock file creation in the config directory

Also provides a theme-aware warning dialog for user interaction.
"""

import logging
import os
import sys
import socket
import time
import psutil
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager

# Import fcntl only on Unix-like systems
try:
    import fcntl
except ImportError:
    fcntl = None  # Windows doesn't have fcntl

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QWidget, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap

logger = logging.getLogger("specter.single_instance")


class SingleInstanceError(Exception):
    """Exception raised when another instance is detected."""
    pass


class InstanceDetectionResult:
    """Result of instance detection check."""
    
    def __init__(self, is_running: bool, detection_method: str = "", 
                 process_info: Optional[dict] = None, lock_file: Optional[str] = None):
        self.is_running = is_running
        self.detection_method = detection_method
        self.process_info = process_info or {}
        self.lock_file = lock_file
        self.timestamp = time.time()


class SingleInstanceDetector:
    """
    Robust single instance detection system.
    
    Uses multiple detection methods to ensure reliability:
    1. File locking on log file (primary method)
    2. Process detection by name
    3. Port binding detection
    4. Lock file in config directory
    """
    
    def __init__(self, app_name: str = "Specter", port: Optional[int] = None):
        self.app_name = app_name
        self.port = port or 29842  # Default port for Specter
        self.lock_file_handle: Optional[int] = None
        self.lock_file_path: Optional[Path] = None
        self.log_file_handle: Optional[int] = None
        
        # Initialize paths
        self._init_paths()
    
    def _init_paths(self):
        """Initialize file paths for lock files."""
        try:
            from ...utils.config_paths import get_user_data_dir
            self.config_dir = Path(get_user_data_dir())
        except ImportError:
            # Fallback
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', str(Path.home() / "AppData" / "Roaming"))
                self.config_dir = Path(appdata) / "Specter"
            else:
                self.config_dir = Path.home() / ".local" / "share" / "specter"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file_path = self.config_dir / f"{self.app_name.lower()}.lock"
        
        # Log directory
        self.log_dir = self.config_dir / "logs"
        self.log_file_path = self.log_dir / "specter.log"
    
    def detect_running_instance(self) -> InstanceDetectionResult:
        """
        Detect if another instance is running using multiple methods.
        
        Returns:
            InstanceDetectionResult with detection information
        """
        logger.debug("Starting single instance detection...")
        
        # Method 1: Try to lock the log file
        result = self._check_log_file_lock()
        if result.is_running:
            logger.info(f"Instance detected via log file lock: {result.detection_method}")
            return result
        
        # Method 2: Check for lock file (OS-level locking on Windows)
        result = self._check_lock_file()
        if result.is_running:
            logger.info(f"Instance detected via lock file: {result.detection_method}")
            return result

        # Log file lock + lock file check are sufficient.
        # Process detection (psutil.process_iter with cmdline) is very slow
        # on Windows (~30s) and port binding adds no value over file locking.
        logger.info("No other instances detected")
        return InstanceDetectionResult(False, "none")
    
    def _check_log_file_lock(self) -> InstanceDetectionResult:
        """Check if the log file is locked by another process."""
        try:
            if not self.log_file_path.exists():
                return InstanceDetectionResult(False, "log_file_not_exists")
            
            # Try to open the log file exclusively
            try:
                self.log_file_handle = os.open(str(self.log_file_path), 
                                             os.O_RDWR | os.O_CREAT)
                
                if os.name != 'nt' and fcntl:  # Unix-like systems with fcntl available
                    fcntl.flock(self.log_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                return InstanceDetectionResult(False, "log_file_available")
                
            except (OSError, IOError) as e:
                if self.log_file_handle is not None:
                    try:
                        os.close(self.log_file_handle)
                    except:
                        pass
                    self.log_file_handle = None
                
                # The error we're looking for (file is locked/in use)
                if (os.name == 'nt' and e.errno == 32) or (os.name != 'nt'):
                    return InstanceDetectionResult(
                        True, 
                        "log_file_locked",
                        {"error": str(e), "errno": getattr(e, 'errno', None)}
                    )
                
                return InstanceDetectionResult(False, "log_file_error", {"error": str(e)})
                
        except Exception as e:
            logger.error(f"Error checking log file lock: {e}")
            return InstanceDetectionResult(False, "log_file_check_error", {"error": str(e)})
    
    def _check_lock_file(self) -> InstanceDetectionResult:
        """Check for application lock file using OS-level file locking.

        On Windows, tries to open the lock file exclusively.  If another
        process holds the file open (via acquire_instance_lock), the open
        will fail with WinError 32 — proving a live instance exists.
        If the file can be opened (or doesn't exist), no instance is running.
        """
        try:
            if not self.lock_file_path.exists():
                return InstanceDetectionResult(False, "lock_file_not_exists")

            if os.name == 'nt':
                # Windows: attempt to open the lock file exclusively.
                # acquire_instance_lock keeps a handle open for the
                # process lifetime, so this will fail if another
                # Specter instance is alive.
                try:
                    handle = os.open(
                        str(self.lock_file_path),
                        os.O_RDWR | os.O_CREAT,
                    )
                    # Try to lock byte 0 — if another process holds it,
                    # msvcrt.locking raises OSError immediately.
                    import msvcrt
                    try:
                        msvcrt.locking(handle, msvcrt.LK_NBLCK, 1)
                        # Lock succeeded → no live instance holds the file.
                        msvcrt.locking(handle, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        os.close(handle)
                        # Another process has the lock → instance is running.
                        return InstanceDetectionResult(
                            True,
                            "lock_file_valid",
                            {"lock_file": str(self.lock_file_path)},
                        )
                    os.close(handle)
                    # Stale lock file from a crashed process — clean it up.
                    self.lock_file_path.unlink(missing_ok=True)
                    logger.info("Removed stale lock file (no live process holds it)")
                    return InstanceDetectionResult(False, "stale_lock_removed")
                except OSError as e:
                    # Cannot even open the file (rare). Try PID-based fallback.
                    logger.debug(f"Lock file open failed: {e}, trying PID fallback")

            # Fallback (non-Windows or open failure): read PID from lock file
            try:
                with open(self.lock_file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        parts = content.split('|')
                        if len(parts) >= 2:
                            pid = int(parts[0])
                            timestamp = float(parts[1])

                            if self._is_process_running(pid):
                                return InstanceDetectionResult(
                                    True,
                                    "lock_file_valid",
                                    {
                                        "pid": pid,
                                        "timestamp": timestamp,
                                        "lock_file": str(self.lock_file_path),
                                    },
                                )
                            else:
                                self.lock_file_path.unlink(missing_ok=True)
                                logger.info(f"Removed stale lock file for PID {pid}")
                                return InstanceDetectionResult(False, "stale_lock_removed")

            except (ValueError, IOError) as e:
                # Corrupt or unreadable — delete and move on
                try:
                    self.lock_file_path.unlink(missing_ok=True)
                except OSError:
                    pass
                logger.debug(f"Cleaned up unreadable lock file: {e}")
                return InstanceDetectionResult(False, "invalid_lock_removed")

            return InstanceDetectionResult(False, "lock_file_empty")

        except Exception as e:
            logger.error(f"Error checking lock file: {e}")
            return InstanceDetectionResult(False, "lock_file_error", {"error": str(e)})
    
    def _check_process_detection(self) -> InstanceDetectionResult:
        """Check for running processes by name."""
        try:
            current_pid = os.getpid()
            running_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                    
                    name = proc.info['name'].lower()
                    cmdline = proc.info['cmdline'] or []
                    
                    # Check if it's a Specter MAIN APPLICATION process (not test scripts)
                    # Must be python/pythonw AND have "-m specter" in cmdline 
                    if (name in ['python.exe', 'pythonw.exe', 'python', 'pythonw'] and
                        len(cmdline) >= 2 and 
                        cmdline[-2:] == ['-m', 'specter']):
                        
                        
                        running_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': proc.info['cmdline'],
                            'create_time': proc.info['create_time']
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if running_processes:
                return InstanceDetectionResult(
                    True,
                    "process_detection",
                    {"processes": running_processes}
                )
            
            return InstanceDetectionResult(False, "no_processes_found")
            
        except Exception as e:
            logger.error(f"Error in process detection: {e}")
            return InstanceDetectionResult(False, "process_detection_error", {"error": str(e)})
    
    def _check_port_binding(self) -> InstanceDetectionResult:
        """Check if the application port is already bound."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                sock.bind(('localhost', self.port))
                sock.close()
                return InstanceDetectionResult(False, "port_available")
                
            except OSError as e:
                sock.close()
                if e.errno == 98:  # Address already in use
                    return InstanceDetectionResult(
                        True,
                        "port_in_use",
                        {"port": self.port, "error": str(e)}
                    )
                return InstanceDetectionResult(False, "port_check_error", {"error": str(e)})
                
        except Exception as e:
            logger.error(f"Error checking port binding: {e}")
            return InstanceDetectionResult(False, "port_binding_error", {"error": str(e)})
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            return psutil.pid_exists(pid)
        except:
            return False
    
    def acquire_instance_lock(self) -> bool:
        """
        Acquire the instance lock to prevent other instances from running.

        On Windows the file handle is kept open with an msvcrt byte-lock so
        that _check_lock_file() on another process can reliably detect it.
        The handle is released in release_instance_lock().

        Returns:
            True if lock was acquired successfully, False otherwise
        """
        try:
            # Write PID info into the lock file
            lock_content = f"{os.getpid()}|{time.time()}|{self.app_name}"

            if os.name == 'nt':
                # Open (create if needed) and keep the handle for the process lifetime
                handle = os.open(
                    str(self.lock_file_path),
                    os.O_RDWR | os.O_CREAT | os.O_TRUNC,
                )
                os.write(handle, lock_content.encode('utf-8'))
                os.lseek(handle, 0, os.SEEK_SET)

                import msvcrt
                try:
                    msvcrt.locking(handle, msvcrt.LK_NBLCK, 1)
                except OSError:
                    # Another process already holds the lock (shouldn't happen
                    # since _check_lock_file ran first, but be safe).
                    os.close(handle)
                    return False

                self.lock_file_handle = handle
            else:
                # Unix: write and rely on fcntl / PID-based detection
                with open(self.lock_file_path, 'w') as f:
                    f.write(lock_content)

            logger.info(f"Instance lock acquired: {self.lock_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to acquire instance lock: {e}")
            return False
    
    def release_instance_lock(self):
        """Release the instance lock."""
        try:
            # Close log file handle if open
            if self.log_file_handle is not None:
                try:
                    if os.name == 'nt':
                        # Unlock the byte lock, then close the handle
                        import msvcrt
                        try:
                            os.lseek(self.log_file_handle, 0, os.SEEK_SET)
                            msvcrt.locking(self.log_file_handle, msvcrt.LK_UNLCK, 1)
                        except OSError:
                            pass
                    elif fcntl:
                        fcntl.flock(self.log_file_handle, fcntl.LOCK_UN)
                    os.close(self.log_file_handle)
                except Exception:
                    pass
                self.log_file_handle = None

            # Remove lock file
            if self.lock_file_path and self.lock_file_path.exists():
                self.lock_file_path.unlink(missing_ok=True)
                logger.info("Instance lock released")

        except Exception as e:
            logger.error(f"Error releasing instance lock: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        result = self.detect_running_instance()
        if result.is_running:
            raise SingleInstanceError(f"Another instance detected: {result.detection_method}")
        
        if not self.acquire_instance_lock():
            raise SingleInstanceError("Failed to acquire instance lock")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release_instance_lock()


class ThemedInstanceWarningDialog(QDialog):
    """
    Theme-aware warning dialog for single instance detection.
    
    Uses the modern styling system to provide a consistent, themed appearance
    that matches the current application theme.
    """
    
    switch_to_existing = pyqtSignal()
    exit_application = pyqtSignal()
    
    def __init__(self, detection_result: InstanceDetectionResult, parent=None):
        super().__init__(parent)
        self.detection_result = detection_result
        self.setWindowTitle("Specter Already Running")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.setFixedSize(480, 220)
        
        # Initialize UI
        self._setup_ui()
        self._apply_theme()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Warning icon and title
        header_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel()
        try:
            from ...utils.resource_resolver import resolve_icon
            icon_path = resolve_icon("warning_color", "")
            if icon_path and icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                icon_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
            else:
                icon_label.setText("⚠️")
                font = QFont()
                font.setPointSize(24)
                icon_label.setFont(font)
        except Exception:
            icon_label.setText("⚠️")
            font = QFont()
            font.setPointSize(24)
            icon_label.setFont(font)
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(icon_label)
        
        # Title and message
        text_layout = QVBoxLayout()
        
        title_label = QLabel("Specter is Already Running")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        text_layout.addWidget(title_label)
        
        # Message based on detection method
        message = self._get_detection_message()
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_font = QFont()
        message_font.setPointSize(10)
        message_label.setFont(message_font)
        text_layout.addWidget(message_label)
        
        header_layout.addLayout(text_layout)
        layout.addLayout(header_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Switch button (if applicable)
        if self._can_switch_to_existing():
            switch_btn = QPushButton("Switch to Existing")
            switch_btn.clicked.connect(self._on_switch_clicked)
            button_layout.addWidget(switch_btn)
        
        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self._on_exit_clicked)
        exit_btn.setDefault(True)
        button_layout.addWidget(exit_btn)
        
        layout.addLayout(button_layout)
        
        # Store references for theming
        self.title_label = title_label
        self.message_label = message_label
        self.icon_label = icon_label
    
    def _get_detection_message(self) -> str:
        """Get appropriate message based on detection method."""
        method = self.detection_result.detection_method
        
        if method == "log_file_locked":
            return ("Another instance of Specter is currently writing to the log file. "
                   "Only one instance can run at a time to prevent conflicts.")
        
        elif method == "lock_file_valid":
            pid = self.detection_result.process_info.get('pid', 'unknown')
            return (f"Another instance of Specter is running (Process ID: {pid}). "
                   "Only one instance can run at a time.")
        
        elif method == "process_detection":
            processes = self.detection_result.process_info.get('processes', [])
            if processes:
                return (f"Found {len(processes)} Specter process(es) already running. "
                       "Only one instance can run at a time.")
        
        elif method == "port_in_use":
            port = self.detection_result.process_info.get('port', 'unknown')
            return (f"Another instance of Specter is using port {port}. "
                   "Only one instance can run at a time.")
        
        return ("Another instance of Specter appears to be running. "
               "Only one instance can run at a time to prevent conflicts.")
    
    def _can_switch_to_existing(self) -> bool:
        """Check if we can switch to the existing instance."""
        # This would require IPC implementation - for now, return False
        # Future enhancement: implement named pipes or socket communication
        return False
    
    def _apply_theme(self):
        """Apply the current theme to the dialog."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            
            # Apply dialog styling
            theme_manager.apply_theme_to_widget(self, "dialog")
            
            # Apply clean styling to buttons
            for child in self.findChildren(QPushButton):
                theme_manager.apply_clean_icon_styling(child, "normal")
            
            logger.debug("Applied theme to instance warning dialog")
            
        except Exception as e:
            logger.error(f"Failed to apply theme to instance warning dialog: {e}")
            # Apply basic fallback styling
            self._apply_fallback_styling()
    
    def _apply_fallback_styling(self):
        """Apply basic fallback styling if theming fails."""
        style = """
        QDialog {
            background-color: #ffffff;
            color: #000000;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QLabel {
            color: #000000;
        }
        QPushButton {
            background-color: #e1e1e1;
            border: 1px solid #adadad;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #d1d1d1;
        }
        QPushButton:pressed {
            background-color: #c1c1c1;
        }
        QPushButton:default {
            background-color: #0078d4;
            color: white;
            border-color: #0078d4;
        }
        QPushButton:default:hover {
            background-color: #106ebe;
        }
        """
        self.setStyleSheet(style)
    
    def _on_switch_clicked(self):
        """Handle switch to existing instance."""
        self.switch_to_existing.emit()
        self.accept()
    
    def _on_exit_clicked(self):
        """Handle exit application."""
        self.exit_application.emit()
        self.reject()
    
    @staticmethod
    def show_instance_warning(detection_result: InstanceDetectionResult, parent=None) -> int:
        """
        Show the instance warning dialog.
        
        Args:
            detection_result: Result from instance detection
            parent: Parent widget
            
        Returns:
            QDialog.DialogCode (Accepted/Rejected)
        """
        dialog = ThemedInstanceWarningDialog(detection_result, parent)
        return dialog.exec()


def check_single_instance(app_name: str = "Specter", 
                         show_dialog: bool = True,
                         parent=None) -> Tuple[bool, Optional[InstanceDetectionResult]]:
    """
    Check for single instance and optionally show warning dialog.
    
    Args:
        app_name: Name of the application
        show_dialog: Whether to show warning dialog if another instance is detected
        parent: Parent widget for dialog
        
    Returns:
        Tuple of (should_continue, detection_result)
        - should_continue: False if another instance detected and user chose to exit
        - detection_result: Detection result information
    """
    detector = SingleInstanceDetector(app_name)
    result = detector.detect_running_instance()
    
    if not result.is_running:
        # No other instance, acquire lock and continue
        if detector.acquire_instance_lock():
            logger.info("Single instance check passed, lock acquired")
            return True, result
        else:
            logger.error("Failed to acquire instance lock")
            return False, result
    
    # Another instance detected
    logger.warning(f"Another instance detected via {result.detection_method}")
    
    if show_dialog and QApplication.instance():
        # Show warning dialog
        dialog_result = ThemedInstanceWarningDialog.show_instance_warning(result, parent)
        return dialog_result == QDialog.DialogCode.Accepted, result
    
    return False, result