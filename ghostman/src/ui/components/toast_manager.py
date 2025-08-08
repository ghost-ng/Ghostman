"""Simple toast notification system."""

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QMessageBox, QApplication
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import sys

class ToastType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ToastConfig:
    title: str
    message: str
    toast_type: ToastType = ToastType.INFO
    duration: int = 3000  # milliseconds

class SimpleToastManager(QObject):
    """Simple toast manager with fallback to console."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.use_console_fallback = True  # Start with console fallback
        
        # Try to initialize native notifications
        self._try_init_native()
    
    def _try_init_native(self):
        """Try to initialize native notifications."""
        try:
            # For now, let's use console fallback to avoid threading issues
            # We can implement proper Windows notifications later
            self.use_console_fallback = True
            self.logger.info("Using console fallback for notifications")
        except Exception as e:
            self.logger.warning(f"Native notifications not available: {e}")
            self.use_console_fallback = True
    
    def show_toast(self, config: ToastConfig):
        """Show toast notification."""
        if self.use_console_fallback:
            self._show_console_toast(config)
        else:
            # Future: implement native notifications
            self._show_console_toast(config)
    
    def _show_console_toast(self, config: ToastConfig):
        """Console notification with nice formatting."""
        symbols = {
            ToastType.INFO: "ℹ️",
            ToastType.SUCCESS: "✅", 
            ToastType.WARNING: "⚠️",
            ToastType.ERROR: "❌"
        }
        
        symbol = symbols.get(config.toast_type, "ℹ️")
        message = f"{symbol} {config.title}: {config.message}"
        
        # Log with appropriate level
        if config.toast_type == ToastType.ERROR:
            self.logger.error(f"TOAST - {config.title}: {config.message}")
        elif config.toast_type == ToastType.WARNING:
            self.logger.warning(f"TOAST - {config.title}: {config.message}")
        else:
            self.logger.info(f"TOAST - {config.title}: {config.message}")
        
        # Also print to console for immediate visibility
        print(message)
    
    def _show_qt_message_box(self, config: ToastConfig):
        """Show Qt message box (for testing - not recommended for production)."""
        try:
            if QApplication.instance():
                msg_box = QMessageBox()
                msg_box.setWindowTitle(config.title)
                msg_box.setText(config.message)
                
                if config.toast_type == ToastType.ERROR:
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                elif config.toast_type == ToastType.WARNING:
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                elif config.toast_type == ToastType.SUCCESS:
                    msg_box.setIcon(QMessageBox.Icon.Information)
                else:
                    msg_box.setIcon(QMessageBox.Icon.Information)
                
                # Auto-close after duration
                QTimer.singleShot(config.duration, msg_box.close)
                msg_box.show()
        except Exception as e:
            self.logger.error(f"Qt message box failed: {e}")
            self._show_console_toast(config)
    
    # Convenience methods
    def info(self, title: str, message: str, **kwargs):
        config = ToastConfig(title, message, ToastType.INFO, **kwargs)
        self.show_toast(config)
    
    def success(self, title: str, message: str, **kwargs):
        config = ToastConfig(title, message, ToastType.SUCCESS, **kwargs)
        self.show_toast(config)
    
    def warning(self, title: str, message: str, **kwargs):
        config = ToastConfig(title, message, ToastType.WARNING, **kwargs)
        self.show_toast(config)
    
    def error(self, title: str, message: str, **kwargs):
        config = ToastConfig(title, message, ToastType.ERROR, **kwargs)
        self.show_toast(config)