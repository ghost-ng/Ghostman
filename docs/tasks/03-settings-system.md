# Settings System Implementation Plan

## Overview

This document outlines the comprehensive implementation plan for Ghostman's settings system, covering configuration management, secure credential storage, UI dialogs, and validation. The system must work without administrator permissions and provide a user-friendly interface for configuring AI providers and application behavior.

## Settings Architecture

### Configuration Schema

The settings system uses a layered approach with validation, defaults, and secure storage:

```
Configuration Layers:
├── Default Settings (built-in)
├── System Settings (read-only)
├── User Settings (modifiable)
└── Runtime Settings (temporary)
```

### Core Settings Categories

1. **AI Provider Settings**
   - API URL (OpenAI compatible)
   - Model selection
   - API key (secure storage)
   - Request parameters (temperature, max_tokens, etc.)

2. **Application Behavior**
   - Window positioning and opacity
   - Auto-hide timers
   - Always-on-top preferences
   - Conversation limits

3. **UI Preferences**
   - Theme selection
   - Font sizes
   - Toast notification preferences
   - Keyboard shortcuts

4. **Privacy & Security**
   - Data retention policies
   - Encryption preferences
   - Logging levels and configuration

5. **Logging & Monitoring**
   - Log level settings (DEBUG, INFO, WARNING, ERROR)
   - Log rotation and retention policies
   - Performance monitoring toggles
   - Debug information export
   - Log file location preferences

## Implementation Details

### 1. Settings Models and Validation

**File**: `ghostman/src/domain/models/settings.py`

```python
from pydantic import BaseModel, Field, validator, SecretStr
from typing import Optional, Dict, Any, List
from enum import Enum
import re
from pathlib import Path

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

class ToastPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"

class AIProviderSettings(BaseModel):
    """AI provider configuration with validation."""
    
    name: str = Field(default="OpenAI", description="Provider name")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API base URL"
    )
    model: str = Field(default="gpt-3.5-turbo", description="Model name")
    api_key: SecretStr = Field(default=SecretStr(""), description="API key")
    
    # Request parameters
    max_tokens: int = Field(default=1000, ge=1, le=32000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Response randomness")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Connection settings
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Retry attempts")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        """Validate API base URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        """Validate model name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Model name cannot be empty')
        return v.strip()

class WindowSettings(BaseModel):
    """Window behavior and positioning settings."""
    
    always_on_top: bool = Field(default=True, description="Keep windows always on top")
    remember_position: bool = Field(default=True, description="Remember window positions")
    auto_hide_delay: int = Field(default=30, ge=0, le=300, description="Auto-hide delay in seconds (0 = disabled)")
    
    # Opacity settings
    active_opacity: float = Field(default=0.95, ge=0.1, le=1.0, description="Window opacity when active")
    inactive_opacity: float = Field(default=0.8, ge=0.1, le=1.0, description="Window opacity when inactive")
    
    # Positioning
    avatar_position: Optional[tuple[int, int]] = Field(default=None, description="Avatar widget position")
    main_window_position: Optional[tuple[int, int]] = Field(default=None, description="Main window position")
    
    # Behavior
    start_minimized: bool = Field(default=False, description="Start application minimized")
    minimize_to_tray: bool = Field(default=True, description="Minimize to system tray")

class ConversationSettings(BaseModel):
    """Conversation management settings."""
    
    max_tokens: int = Field(default=4000, ge=1000, le=32000, description="Maximum tokens per conversation")
    auto_save: bool = Field(default=True, description="Automatically save conversations")
    backup_frequency: int = Field(default=24, ge=1, le=168, description="Backup frequency in hours")
    
    # Memory management
    trim_strategy: str = Field(default="sliding_window", description="Memory trimming strategy")
    summary_enabled: bool = Field(default=True, description="Enable conversation summarization")
    
    # Data retention
    max_conversations: int = Field(default=100, ge=10, le=1000, description="Maximum stored conversations")
    auto_delete_after_days: int = Field(default=90, ge=7, le=365, description="Auto-delete conversations after days")

class UISettings(BaseModel):
    """User interface preferences."""
    
    theme: Theme = Field(default=Theme.SYSTEM, description="Application theme")
    font_family: str = Field(default="Segoe UI", description="Font family")
    font_size: int = Field(default=10, ge=8, le=18, description="Font size")
    
    # Toast notifications
    toast_enabled: bool = Field(default=True, description="Enable toast notifications")
    toast_position: ToastPosition = Field(default=ToastPosition.BOTTOM_RIGHT, description="Toast position")
    toast_duration: int = Field(default=3000, ge=1000, le=10000, description="Toast duration in milliseconds")
    
    # Animations
    animations_enabled: bool = Field(default=True, description="Enable UI animations")
    animation_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Animation speed multiplier")

class PrivacySettings(BaseModel):
    """Privacy and security settings."""
    
    encrypt_conversations: bool = Field(default=False, description="Encrypt stored conversations")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    anonymous_analytics: bool = Field(default=False, description="Enable anonymous usage analytics")
    
    # Data handling
    clear_on_exit: bool = Field(default=False, description="Clear conversation data on exit")
    secure_delete: bool = Field(default=True, description="Secure deletion of files")

class HotkeySettings(BaseModel):
    """Keyboard shortcuts configuration."""
    
    toggle_visibility: str = Field(default="Ctrl+Shift+G", description="Toggle main window visibility")
    quick_prompt: str = Field(default="Ctrl+Shift+P", description="Quick prompt hotkey")
    emergency_hide: str = Field(default="Escape", description="Emergency hide hotkey")

class AppSettings(BaseModel):
    """Complete application settings."""
    
    # Core settings
    ai_provider: AIProviderSettings = Field(default_factory=AIProviderSettings)
    window: WindowSettings = Field(default_factory=WindowSettings)
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    ui: UISettings = Field(default_factory=UISettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)
    
    # Metadata
    version: str = Field(default="0.1.0", description="Settings version")
    created_at: Optional[str] = Field(default=None, description="Settings creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    
    class Config:
        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on assignment
        use_enum_values = True  # Use enum values instead of enum objects
        
    def update_timestamp(self):
        """Update the timestamp when settings change."""
        from datetime import datetime
        self.updated_at = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = self.updated_at
```

### 2. Configuration Storage and Security

**Important**: All user settings must be stored in the appropriate `%APPDATA%` directory in JSON format to ensure proper user-level data isolation and comply with Windows application data storage conventions.

**File**: `ghostman/src/infrastructure/config/config_store.py`

```python
import json
import base64
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import shutil
from datetime import datetime

class SecureConfigStore:
    """Secure configuration storage with encryption for sensitive data."""
    
    def __init__(self, config_dir: Path, encryption_key: Optional[str] = None):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.config_dir / "settings.json"
        self.secure_file = self.config_dir / "secure.dat"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Setup encryption for sensitive data
        self._setup_encryption(encryption_key)
    
    def _setup_encryption(self, password: Optional[str]):
        """Setup encryption for sensitive configuration data."""
        if password:
            # Use provided password
            password_bytes = password.encode()
        else:
            # Use machine-specific key (less secure but no user input needed)
            import platform
            machine_id = platform.node() + platform.machine()
            password_bytes = machine_id.encode()
        
        # Generate salt file if it doesn't exist
        salt_file = self.config_dir / ".salt"
        if not salt_file.exists():
            salt = os.urandom(16)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            # Hide salt file on Windows
            if os.name == 'nt':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(str(salt_file), 2)  # Hidden
                except:
                    pass
        else:
            with open(salt_file, 'rb') as f:
                salt = f.read()
        
        # Derive encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        self.cipher = Fernet(key)
    
    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save settings with sensitive data encryption."""
        # Create backup first
        self._create_backup()
        
        # Separate sensitive and non-sensitive data
        secure_data, regular_data = self._separate_sensitive_data(settings)
        
        # Save regular settings
        regular_data['_metadata'] = {
            'version': '1.0',
            'saved_at': datetime.utcnow().isoformat(),
            'has_secure_data': len(secure_data) > 0
        }
        
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(regular_data, f, indent=2, ensure_ascii=False)
            
            # Save encrypted sensitive data
            if secure_data:
                encrypted_data = self.cipher.encrypt(json.dumps(secure_data).encode())
                with open(self.secure_file, 'wb') as f:
                    f.write(encrypted_data)
            
        except Exception as e:
            # Restore from backup if save failed
            self._restore_backup()
            raise RuntimeError(f"Failed to save settings: {e}")
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings with secure data decryption."""
        settings = {}
        
        # Load regular settings
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Remove metadata
                settings.pop('_metadata', None)
                
            except Exception as e:
                print(f"Error loading settings: {e}")
                return {}
        
        # Load secure data
        if self.secure_file.exists():
            try:
                with open(self.secure_file, 'rb') as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.cipher.decrypt(encrypted_data)
                secure_settings = json.loads(decrypted_data.decode())
                
                # Merge secure settings back into main settings
                self._merge_secure_data(settings, secure_settings)
                
            except Exception as e:
                print(f"Error loading secure settings: {e}")
                # Continue with non-secure settings
        
        return settings
    
    def _separate_sensitive_data(self, settings: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Separate sensitive data that needs encryption."""
        secure_data = {}
        regular_data = settings.copy()
        
        # Define sensitive paths
        sensitive_paths = [
            ['ai_provider', 'api_key'],
            # Add more sensitive paths as needed
        ]
        
        for path in sensitive_paths:
            value = regular_data
            for key in path[:-1]:
                if key in value and isinstance(value[key], dict):
                    value = value[key]
                else:
                    break
            else:
                # Extract sensitive value
                final_key = path[-1]
                if final_key in value:
                    # Store in secure data with path as key
                    secure_key = '.'.join(path)
                    secure_data[secure_key] = value[final_key]
                    
                    # Replace with placeholder in regular data
                    value[final_key] = "***ENCRYPTED***"
        
        return secure_data, regular_data
    
    def _merge_secure_data(self, settings: Dict[str, Any], secure_data: Dict[str, Any]):
        """Merge decrypted secure data back into settings."""
        for secure_key, secure_value in secure_data.items():
            path = secure_key.split('.')
            
            # Navigate to the correct nested location
            current = settings
            for key in path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set the secure value
            current[path[-1]] = secure_value
    
    def _create_backup(self):
        """Create backup of current settings."""
        if not self.settings_file.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"settings_backup_{timestamp}.json"
        
        try:
            shutil.copy2(self.settings_file, backup_file)
            
            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob("settings_backup_*.json"))
            while len(backups) > 10:
                oldest = backups.pop(0)
                oldest.unlink()
                
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
    
    def _restore_backup(self):
        """Restore from the most recent backup."""
        backups = sorted(self.backup_dir.glob("settings_backup_*.json"))
        if backups:
            try:
                shutil.copy2(backups[-1], self.settings_file)
                print("Settings restored from backup")
            except Exception as e:
                print(f"Error restoring backup: {e}")
    
    def reset_to_defaults(self):
        """Reset settings to defaults by removing config files."""
        try:
            if self.settings_file.exists():
                self.settings_file.unlink()
            if self.secure_file.exists():
                self.secure_file.unlink()
            print("Settings reset to defaults")
        except Exception as e:
            raise RuntimeError(f"Failed to reset settings: {e}")
    
    def export_settings(self, export_path: Path, include_sensitive: bool = False):
        """Export settings for backup or sharing."""
        settings = self.load_settings()
        
        if not include_sensitive:
            # Remove sensitive data for sharing
            if 'ai_provider' in settings and 'api_key' in settings['ai_provider']:
                settings['ai_provider']['api_key'] = ""
        
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'version': '1.0',
            'settings': settings
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def import_settings(self, import_path: Path):
        """Import settings from file."""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'settings' in data:
            self.save_settings(data['settings'])
        else:
            raise ValueError("Invalid settings file format")
```

### 3. Settings Service Layer

**File**: `ghostman/src/domain/services/settings_service.py`

```python
from typing import Optional, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from ..models.settings import AppSettings
from ...infrastructure.config.config_store import SecureConfigStore
import logging

class SettingsService(QObject):
    """Service for managing application settings with validation and persistence."""
    
    # Signals
    settings_changed = pyqtSignal(str)  # Setting path that changed
    ai_settings_changed = pyqtSignal()
    ui_settings_changed = pyqtSignal()
    validation_error = pyqtSignal(str, str)  # field, error
    
    def __init__(self, config_dir: Path, encryption_password: Optional[str] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_store = SecureConfigStore(config_dir, encryption_password)
        self._settings: Optional[AppSettings] = None
        self._change_callbacks: dict[str, list[Callable]] = {}
        
        # Load initial settings
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load settings from storage."""
        try:
            data = self.config_store.load_settings()
            if data:
                self._settings = AppSettings(**data)
            else:
                self._settings = AppSettings()
            
            self.logger.info("Settings loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self._settings = AppSettings()  # Use defaults
    
    def save_settings(self) -> None:
        """Save current settings to storage."""
        if not self._settings:
            return
        
        try:
            # Update timestamp
            self._settings.update_timestamp()
            
            # Convert to dict for storage
            data = self._settings.dict(exclude_none=True)
            
            self.config_store.save_settings(data)
            self.logger.info("Settings saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            raise RuntimeError(f"Failed to save settings: {e}")
    
    def get_settings(self) -> AppSettings:
        """Get current settings."""
        if not self._settings:
            self.load_settings()
        return self._settings
    
    def update_ai_settings(self, **kwargs) -> bool:
        """Update AI provider settings."""
        try:
            for key, value in kwargs.items():
                if hasattr(self._settings.ai_provider, key):
                    setattr(self._settings.ai_provider, key, value)
                else:
                    raise ValueError(f"Unknown AI setting: {key}")
            
            self.save_settings()
            self.ai_settings_changed.emit()
            self.settings_changed.emit("ai_provider")
            return True
            
        except ValueError as e:
            self.validation_error.emit("ai_provider", str(e))
            return False
        except Exception as e:
            self.logger.error(f"Error updating AI settings: {e}")
            return False
    
    def update_ui_settings(self, **kwargs) -> bool:
        """Update UI settings."""
        try:
            for key, value in kwargs.items():
                if hasattr(self._settings.ui, key):
                    setattr(self._settings.ui, key, value)
                else:
                    raise ValueError(f"Unknown UI setting: {key}")
            
            self.save_settings()
            self.ui_settings_changed.emit()
            self.settings_changed.emit("ui")
            return True
            
        except ValueError as e:
            self.validation_error.emit("ui", str(e))
            return False
        except Exception as e:
            self.logger.error(f"Error updating UI settings: {e}")
            return False
    
    def update_window_settings(self, **kwargs) -> bool:
        """Update window settings."""
        try:
            for key, value in kwargs.items():
                if hasattr(self._settings.window, key):
                    setattr(self._settings.window, key, value)
                else:
                    raise ValueError(f"Unknown window setting: {key}")
            
            self.save_settings()
            self.settings_changed.emit("window")
            return True
            
        except ValueError as e:
            self.validation_error.emit("window", str(e))
            return False
    
    def test_ai_connection(self) -> tuple[bool, str]:
        """Test AI provider connection with current settings."""
        try:
            # Import here to avoid circular dependencies
            from ...infrastructure.network.providers.openai_provider import OpenAIProvider
            from ...infrastructure.network.http_client import HTTPClient
            
            http_client = HTTPClient()
            provider = OpenAIProvider(self._settings.ai_provider, http_client)
            
            # Test with a simple request
            test_messages = [{"role": "user", "content": "Hello"}]
            
            # This would be async in real implementation
            # response = await provider.chat_completion(test_messages)
            
            return True, "Connection successful"
            
        except Exception as e:
            return False, f"Connection failed: {e}"
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        try:
            self.config_store.reset_to_defaults()
            self._settings = AppSettings()
            self.save_settings()
            
            # Emit change signals
            self.settings_changed.emit("*")  # All settings changed
            self.ai_settings_changed.emit()
            self.ui_settings_changed.emit()
            
            self.logger.info("Settings reset to defaults")
            
        except Exception as e:
            self.logger.error(f"Error resetting settings: {e}")
            raise RuntimeError(f"Failed to reset settings: {e}")
    
    def export_settings(self, export_path: Path, include_api_key: bool = False) -> None:
        """Export settings to file."""
        try:
            self.config_store.export_settings(export_path, include_api_key)
            self.logger.info(f"Settings exported to {export_path}")
        except Exception as e:
            self.logger.error(f"Error exporting settings: {e}")
            raise RuntimeError(f"Failed to export settings: {e}")
    
    def import_settings(self, import_path: Path) -> None:
        """Import settings from file."""
        try:
            self.config_store.import_settings(import_path)
            self.load_settings()  # Reload from storage
            
            # Emit change signals
            self.settings_changed.emit("*")
            self.ai_settings_changed.emit()
            self.ui_settings_changed.emit()
            
            self.logger.info(f"Settings imported from {import_path}")
            
        except Exception as e:
            self.logger.error(f"Error importing settings: {e}")
            raise RuntimeError(f"Failed to import settings: {e}")
    
    def register_change_callback(self, setting_path: str, callback: Callable):
        """Register callback for setting changes."""
        if setting_path not in self._change_callbacks:
            self._change_callbacks[setting_path] = []
        self._change_callbacks[setting_path].append(callback)
    
    def unregister_change_callback(self, setting_path: str, callback: Callable):
        """Unregister callback for setting changes."""
        if setting_path in self._change_callbacks:
            try:
                self._change_callbacks[setting_path].remove(callback)
            except ValueError:
                pass
```

### 4. Settings Dialog UI

**File**: `ghostman/src/ui/dialogs/settings_dialog.py`

```python
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                            QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
                            QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
                            QGroupBox, QFormLayout, QTextEdit, QMessageBox,
                            QFileDialog, QProgressBar, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QIcon
from ..components.qt_toast_bridge import QtToastManager
from ...domain.services.settings_service import SettingsService
from ...domain.models.settings import Theme, ToastPosition, LogLevel
import asyncio

class ConnectionTestWorker(QThread):
    """Worker thread for testing AI connection."""
    
    test_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, settings_service):
        super().__init__()
        self.settings_service = settings_service
    
    def run(self):
        success, message = self.settings_service.test_ai_connection()
        self.test_completed.emit(success, message)

class SettingsDialog(QDialog):
    """Main settings dialog with tabbed interface."""
    
    # Signals
    settings_applied = pyqtSignal()
    ai_connection_tested = pyqtSignal(bool, str)
    
    def __init__(self, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings_service
        self.toast_manager = QtToastManager()
        self.test_worker = None
        
        # Track changes
        self.has_changes = False
        self.original_settings = None
        
        self.setup_ui()
        self.load_current_settings()
        self.setup_connections()
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # Auto-save every 30 seconds
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Ghostman Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_ai_tab()
        self.create_appearance_tab()
        self.create_behavior_tab()
        self.create_privacy_tab()
        self.create_advanced_tab()
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Left side buttons
        self.test_connection_button = QPushButton("Test AI Connection")
        self.test_connection_button.clicked.connect(self.test_ai_connection)
        button_layout.addWidget(self.test_connection_button)
        
        # Connection status
        self.connection_status = QLabel("")
        button_layout.addWidget(self.connection_status)
        
        button_layout.addStretch()
        
        # Right side buttons
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_settings)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def create_ai_tab(self):
        """Create AI provider settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Provider settings group
        provider_group = QGroupBox("AI Provider Configuration")
        provider_layout = QFormLayout(provider_group)
        
        self.provider_name_edit = QLineEdit()
        self.provider_name_edit.setPlaceholderText("e.g., OpenAI, Azure OpenAI")
        provider_layout.addRow("Provider Name:", self.provider_name_edit)
        
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        provider_layout.addRow("Base URL:", self.base_url_edit)
        
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gpt-3.5-turbo")
        provider_layout.addRow("Model:", self.model_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Your API key")
        
        # Show/hide API key button
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(self.api_key_edit)
        self.show_api_key_button = QPushButton("Show")
        self.show_api_key_button.setMaximumWidth(60)
        self.show_api_key_button.clicked.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_api_key_button)
        
        provider_layout.addRow("API Key:", api_key_layout)
        
        layout.addWidget(provider_group)
        
        # Request parameters group
        params_group = QGroupBox("Request Parameters")
        params_layout = QFormLayout(params_group)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32000)
        self.max_tokens_spin.setSuffix(" tokens")
        params_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(1)
        params_layout.addRow("Temperature:", self.temperature_spin)
        
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.1)
        self.top_p_spin.setDecimals(1)
        params_layout.addRow("Top P:", self.top_p_spin)
        
        layout.addWidget(params_group)
        
        # Connection settings group
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout(connection_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSuffix(" seconds")
        connection_layout.addRow("Timeout:", self.timeout_spin)
        
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        connection_layout.addRow("Retry Attempts:", self.retry_spin)
        
        layout.addWidget(connection_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "AI Provider")
    
    def create_appearance_tab(self):
        """Create appearance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Theme group
        theme_group = QGroupBox("Theme and Colors")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        for theme in Theme:
            self.theme_combo.addItem(theme.value.title(), theme.value)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        layout.addWidget(theme_group)
        
        # Font group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)
        
        self.font_family_edit = QLineEdit()
        font_layout.addRow("Font Family:", self.font_family_edit)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 18)
        self.font_size_spin.setSuffix(" pt")
        font_layout.addRow("Font Size:", self.font_size_spin)
        
        layout.addWidget(font_group)
        
        # Notification group
        notification_group = QGroupBox("Toast Notifications")
        notification_layout = QFormLayout(notification_group)
        
        self.toast_enabled_check = QCheckBox()
        notification_layout.addRow("Enable Notifications:", self.toast_enabled_check)
        
        self.toast_position_combo = QComboBox()
        for position in ToastPosition:
            display_name = position.value.replace('-', ' ').title()
            self.toast_position_combo.addItem(display_name, position.value)
        notification_layout.addRow("Position:", self.toast_position_combo)
        
        self.toast_duration_spin = QSpinBox()
        self.toast_duration_spin.setRange(1000, 10000)
        self.toast_duration_spin.setSuffix(" ms")
        notification_layout.addRow("Duration:", self.toast_duration_spin)
        
        layout.addWidget(notification_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Appearance")
    
    def create_behavior_tab(self):
        """Create behavior settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Window behavior group
        window_group = QGroupBox("Window Behavior")
        window_layout = QFormLayout(window_group)
        
        self.always_on_top_check = QCheckBox()
        window_layout.addRow("Always on Top:", self.always_on_top_check)
        
        self.remember_position_check = QCheckBox()
        window_layout.addRow("Remember Position:", self.remember_position_check)
        
        self.start_minimized_check = QCheckBox()
        window_layout.addRow("Start Minimized:", self.start_minimized_check)
        
        self.minimize_to_tray_check = QCheckBox()
        window_layout.addRow("Minimize to Tray:", self.minimize_to_tray_check)
        
        # Auto-hide settings
        self.auto_hide_spin = QSpinBox()
        self.auto_hide_spin.setRange(0, 300)
        self.auto_hide_spin.setSuffix(" seconds (0 = disabled)")
        window_layout.addRow("Auto-hide Delay:", self.auto_hide_spin)
        
        layout.addWidget(window_group)
        
        # Opacity group
        opacity_group = QGroupBox("Window Opacity")
        opacity_layout = QFormLayout(opacity_group)
        
        # Active opacity
        active_layout = QHBoxLayout()
        self.active_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.active_opacity_slider.setRange(10, 100)
        self.active_opacity_slider.valueChanged.connect(
            lambda v: self.active_opacity_label.setText(f"{v}%")
        )
        self.active_opacity_label = QLabel("95%")
        active_layout.addWidget(self.active_opacity_slider)
        active_layout.addWidget(self.active_opacity_label)
        opacity_layout.addRow("Active Opacity:", active_layout)
        
        # Inactive opacity
        inactive_layout = QHBoxLayout()
        self.inactive_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.inactive_opacity_slider.setRange(10, 100)
        self.inactive_opacity_slider.valueChanged.connect(
            lambda v: self.inactive_opacity_label.setText(f"{v}%")
        )
        self.inactive_opacity_label = QLabel("80%")
        inactive_layout.addWidget(self.inactive_opacity_slider)
        inactive_layout.addWidget(self.inactive_opacity_label)
        opacity_layout.addRow("Inactive Opacity:", inactive_layout)
        
        layout.addWidget(opacity_group)
        
        # Conversation group
        conversation_group = QGroupBox("Conversation Settings")
        conversation_layout = QFormLayout(conversation_group)
        
        self.max_conversation_tokens_spin = QSpinBox()
        self.max_conversation_tokens_spin.setRange(1000, 32000)
        self.max_conversation_tokens_spin.setSuffix(" tokens")
        conversation_layout.addRow("Max Conversation Tokens:", self.max_conversation_tokens_spin)
        
        self.auto_save_check = QCheckBox()
        conversation_layout.addRow("Auto-save Conversations:", self.auto_save_check)
        
        layout.addWidget(conversation_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Behavior")
    
    def create_privacy_tab(self):
        """Create privacy settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Encryption group
        encryption_group = QGroupBox("Data Security")
        encryption_layout = QFormLayout(encryption_group)
        
        self.encrypt_conversations_check = QCheckBox()
        encryption_layout.addRow("Encrypt Conversations:", self.encrypt_conversations_check)
        
        self.secure_delete_check = QCheckBox()
        encryption_layout.addRow("Secure File Deletion:", self.secure_delete_check)
        
        layout.addWidget(encryption_group)
        
        # Data retention group
        retention_group = QGroupBox("Data Retention")
        retention_layout = QFormLayout(retention_group)
        
        self.max_conversations_spin = QSpinBox()
        self.max_conversations_spin.setRange(10, 1000)
        retention_layout.addRow("Max Stored Conversations:", self.max_conversations_spin)
        
        self.auto_delete_days_spin = QSpinBox()
        self.auto_delete_days_spin.setRange(7, 365)
        self.auto_delete_days_spin.setSuffix(" days")
        retention_layout.addRow("Auto-delete After:", self.auto_delete_days_spin)
        
        self.clear_on_exit_check = QCheckBox()
        retention_layout.addRow("Clear Data on Exit:", self.clear_on_exit_check)
        
        layout.addWidget(retention_group)
        
        # Logging group
        logging_group = QGroupBox("Logging and Analytics")
        logging_layout = QFormLayout(logging_group)
        
        self.log_level_combo = QComboBox()
        for level in LogLevel:
            self.log_level_combo.addItem(level.value, level.value)
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        self.anonymous_analytics_check = QCheckBox()
        logging_layout.addRow("Anonymous Analytics:", self.anonymous_analytics_check)
        
        layout.addWidget(logging_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Privacy")
    
    def create_advanced_tab(self):
        """Create advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Import/Export group
        import_export_group = QGroupBox("Import/Export Settings")
        import_export_layout = QVBoxLayout(import_export_group)
        
        # Export settings
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Settings")
        self.export_button.clicked.connect(self.export_settings)
        export_layout.addWidget(self.export_button)
        
        self.export_include_api_key_check = QCheckBox("Include API Key")
        export_layout.addWidget(self.export_include_api_key_check)
        export_layout.addStretch()
        
        import_export_layout.addLayout(export_layout)
        
        # Import settings
        import_layout = QHBoxLayout()
        self.import_button = QPushButton("Import Settings")
        self.import_button.clicked.connect(self.import_settings)
        import_layout.addWidget(self.import_button)
        import_layout.addStretch()
        
        import_export_layout.addLayout(import_layout)
        
        layout.addWidget(import_export_group)
        
        # Debug group
        debug_group = QGroupBox("Debug Information")
        debug_layout = QVBoxLayout(debug_group)
        
        self.debug_info_text = QTextEdit()
        self.debug_info_text.setReadOnly(True)
        self.debug_info_text.setMaximumHeight(200)
        debug_layout.addWidget(self.debug_info_text)
        
        self.refresh_debug_button = QPushButton("Refresh Debug Info")
        self.refresh_debug_button.clicked.connect(self.refresh_debug_info)
        debug_layout.addWidget(self.refresh_debug_button)
        
        layout.addWidget(debug_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Advanced")
    
    def setup_connections(self):
        """Setup signal connections."""
        # Track changes for all inputs
        controls = [
            self.provider_name_edit, self.base_url_edit, self.model_edit, self.api_key_edit,
            self.max_tokens_spin, self.temperature_spin, self.top_p_spin,
            self.timeout_spin, self.retry_spin, self.theme_combo, self.font_family_edit,
            self.font_size_spin, self.toast_enabled_check, self.toast_position_combo,
            self.toast_duration_spin, self.always_on_top_check, self.remember_position_check,
            self.start_minimized_check, self.minimize_to_tray_check, self.auto_hide_spin,
            self.active_opacity_slider, self.inactive_opacity_slider,
            self.max_conversation_tokens_spin, self.auto_save_check,
            self.encrypt_conversations_check, self.secure_delete_check,
            self.max_conversations_spin, self.auto_delete_days_spin,
            self.clear_on_exit_check, self.log_level_combo, self.anonymous_analytics_check
        ]
        
        for control in controls:
            if hasattr(control, 'textChanged'):
                control.textChanged.connect(self.mark_changed)
            elif hasattr(control, 'valueChanged'):
                control.valueChanged.connect(self.mark_changed)
            elif hasattr(control, 'currentTextChanged'):
                control.currentTextChanged.connect(self.mark_changed)
            elif hasattr(control, 'toggled'):
                control.toggled.connect(self.mark_changed)
    
    def load_current_settings(self):
        """Load current settings into UI controls."""
        settings = self.settings_service.get_settings()
        self.original_settings = settings.dict()
        
        # AI Provider settings
        self.provider_name_edit.setText(settings.ai_provider.name)
        self.base_url_edit.setText(settings.ai_provider.base_url)
        self.model_edit.setText(settings.ai_provider.model)
        if settings.ai_provider.api_key:
            self.api_key_edit.setText(settings.ai_provider.api_key.get_secret_value())
        
        self.max_tokens_spin.setValue(settings.ai_provider.max_tokens)
        self.temperature_spin.setValue(settings.ai_provider.temperature)
        self.top_p_spin.setValue(settings.ai_provider.top_p)
        self.timeout_spin.setValue(settings.ai_provider.timeout)
        self.retry_spin.setValue(settings.ai_provider.retry_attempts)
        
        # UI settings
        theme_index = self.theme_combo.findData(settings.ui.theme.value)
        self.theme_combo.setCurrentIndex(theme_index)
        
        self.font_family_edit.setText(settings.ui.font_family)
        self.font_size_spin.setValue(settings.ui.font_size)
        
        self.toast_enabled_check.setChecked(settings.ui.toast_enabled)
        position_index = self.toast_position_combo.findData(settings.ui.toast_position.value)
        self.toast_position_combo.setCurrentIndex(position_index)
        self.toast_duration_spin.setValue(settings.ui.toast_duration)
        
        # Window settings
        self.always_on_top_check.setChecked(settings.window.always_on_top)
        self.remember_position_check.setChecked(settings.window.remember_position)
        self.start_minimized_check.setChecked(settings.window.start_minimized)
        self.minimize_to_tray_check.setChecked(settings.window.minimize_to_tray)
        self.auto_hide_spin.setValue(settings.window.auto_hide_delay)
        
        # Opacity settings
        self.active_opacity_slider.setValue(int(settings.window.active_opacity * 100))
        self.inactive_opacity_slider.setValue(int(settings.window.inactive_opacity * 100))
        
        # Conversation settings
        self.max_conversation_tokens_spin.setValue(settings.conversation.max_tokens)
        self.auto_save_check.setChecked(settings.conversation.auto_save)
        
        # Privacy settings
        self.encrypt_conversations_check.setChecked(settings.privacy.encrypt_conversations)
        self.secure_delete_check.setChecked(settings.privacy.secure_delete)
        self.max_conversations_spin.setValue(settings.conversation.max_conversations)
        self.auto_delete_days_spin.setValue(settings.conversation.auto_delete_after_days)
        self.clear_on_exit_check.setChecked(settings.privacy.clear_on_exit)
        
        log_index = self.log_level_combo.findData(settings.privacy.log_level.value)
        self.log_level_combo.setCurrentIndex(log_index)
        self.anonymous_analytics_check.setChecked(settings.privacy.anonymous_analytics)
        
        self.has_changes = False
    
    def mark_changed(self):
        """Mark that settings have been changed."""
        self.has_changes = True
        self.apply_button.setEnabled(True)
    
    def collect_settings_data(self) -> dict:
        """Collect current settings from UI controls."""
        return {
            # AI Provider
            'ai_provider': {
                'name': self.provider_name_edit.text(),
                'base_url': self.base_url_edit.text(),
                'model': self.model_edit.text(),
                'api_key': self.api_key_edit.text(),
                'max_tokens': self.max_tokens_spin.value(),
                'temperature': self.temperature_spin.value(),
                'top_p': self.top_p_spin.value(),
                'timeout': self.timeout_spin.value(),
                'retry_attempts': self.retry_spin.value()
            },
            # UI
            'ui': {
                'theme': self.theme_combo.currentData(),
                'font_family': self.font_family_edit.text(),
                'font_size': self.font_size_spin.value(),
                'toast_enabled': self.toast_enabled_check.isChecked(),
                'toast_position': self.toast_position_combo.currentData(),
                'toast_duration': self.toast_duration_spin.value()
            },
            # Window
            'window': {
                'always_on_top': self.always_on_top_check.isChecked(),
                'remember_position': self.remember_position_check.isChecked(),
                'start_minimized': self.start_minimized_check.isChecked(),
                'minimize_to_tray': self.minimize_to_tray_check.isChecked(),
                'auto_hide_delay': self.auto_hide_spin.value(),
                'active_opacity': self.active_opacity_slider.value() / 100.0,
                'inactive_opacity': self.inactive_opacity_slider.value() / 100.0
            },
            # Conversation
            'conversation': {
                'max_tokens': self.max_conversation_tokens_spin.value(),
                'auto_save': self.auto_save_check.isChecked(),
                'max_conversations': self.max_conversations_spin.value(),
                'auto_delete_after_days': self.auto_delete_days_spin.value()
            },
            # Privacy
            'privacy': {
                'encrypt_conversations': self.encrypt_conversations_check.isChecked(),
                'secure_delete': self.secure_delete_check.isChecked(),
                'clear_on_exit': self.clear_on_exit_check.isChecked(),
                'log_level': self.log_level_combo.currentData(),
                'anonymous_analytics': self.anonymous_analytics_check.isChecked()
            }
        }
    
    def apply_settings(self):
        """Apply current settings without closing dialog."""
        try:
            settings_data = self.collect_settings_data()
            
            # Update each section
            self.settings_service.update_ai_settings(**settings_data['ai_provider'])
            self.settings_service.update_ui_settings(**settings_data['ui'])
            self.settings_service.update_window_settings(**settings_data['window'])
            
            # Update other settings sections similarly...
            
            self.has_changes = False
            self.apply_button.setEnabled(False)
            self.settings_applied.emit()
            
            self.toast_manager.show_success("Settings", "Settings applied successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings:\n{str(e)}")
    
    def accept_settings(self):
        """Apply settings and close dialog."""
        if self.has_changes:
            self.apply_settings()
        self.accept()
    
    def auto_save(self):
        """Auto-save settings if changed."""
        if self.has_changes:
            self.apply_settings()
    
    def test_ai_connection(self):
        """Test AI provider connection."""
        if self.test_worker and self.test_worker.isRunning():
            return
        
        # Temporarily apply AI settings
        try:
            ai_settings = self.collect_settings_data()['ai_provider']
            self.settings_service.update_ai_settings(**ai_settings)
            
            self.test_connection_button.setEnabled(False)
            self.test_connection_button.setText("Testing...")
            self.connection_status.setText("Testing connection...")
            
            self.test_worker = ConnectionTestWorker(self.settings_service)
            self.test_worker.test_completed.connect(self.on_connection_test_completed)
            self.test_worker.start()
            
        except Exception as e:
            self.connection_status.setText(f"Error: {e}")
            self.test_connection_button.setEnabled(True)
            self.test_connection_button.setText("Test AI Connection")
    
    def on_connection_test_completed(self, success: bool, message: str):
        """Handle connection test completion."""
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("Test AI Connection")
        
        if success:
            self.connection_status.setText("✅ " + message)
            self.connection_status.setStyleSheet("color: green;")
            self.toast_manager.show_success("Connection Test", "AI connection successful")
        else:
            self.connection_status.setText("❌ " + message)
            self.connection_status.setStyleSheet("color: red;")
            self.toast_manager.show_error("Connection Test", "AI connection failed")
        
        self.ai_connection_tested.emit(success, message)
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility."""
        if self.api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_api_key_button.setText("Hide")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_api_key_button.setText("Show")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings_service.reset_to_defaults()
                self.load_current_settings()
                self.toast_manager.show_info("Settings", "Settings reset to defaults")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings:\n{str(e)}")
    
    def export_settings(self):
        """Export settings to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            "ghostman_settings.json",
            "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            try:
                include_api_key = self.export_include_api_key_check.isChecked()
                self.settings_service.export_settings(Path(file_path), include_api_key)
                self.toast_manager.show_success("Export", "Settings exported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export settings:\n{str(e)}")
    
    def import_settings(self):
        """Import settings from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            "",
            "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            reply = QMessageBox.question(
                self,
                "Import Settings",
                "Importing settings will overwrite current settings. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.settings_service.import_settings(Path(file_path))
                    self.load_current_settings()
                    self.toast_manager.show_success("Import", "Settings imported successfully")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to import settings:\n{str(e)}")
    
    def refresh_debug_info(self):
        """Refresh debug information display."""
        import platform
        import sys
        from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        
        settings = self.settings_service.get_settings()
        
        debug_info = f"""System Information:
- Platform: {platform.platform()}
- Python: {sys.version}
- PyQt6: {PYQT_VERSION_STR}
- Qt: {QT_VERSION_STR}

Application Information:
- Settings Version: {settings.version}
- Config Directory: {self.settings_service.config_store.config_dir}
- Settings Created: {settings.created_at or 'Not set'}
- Settings Updated: {settings.updated_at or 'Not set'}

Current Settings:
- AI Provider: {settings.ai_provider.name}
- Model: {settings.ai_provider.model}
- Theme: {settings.ui.theme}
- Always On Top: {settings.window.always_on_top}
- Conversation Token Limit: {settings.conversation.max_tokens}
"""
        
        self.debug_info_text.setText(debug_info)
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.has_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.apply_settings()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        # Clean up
        self.auto_save_timer.stop()
        if self.test_worker:
            self.test_worker.quit()
            self.test_worker.wait()
        
        self.toast_manager.cleanup()
        event.accept()
```

## Integration and Testing

### Integration with Main Application

**File**: `ghostman/src/app/application.py` (settings integration)

```python
class GhostmanApplication:
    def __init__(self):
        # Initialize settings service - use %APPDATA% directory for proper Windows compliance
        import os
        appdata_dir = Path(os.environ.get('APPDATA', Path.home()))
        config_dir = appdata_dir / "Ghostman"
        self.settings_service = SettingsService(config_dir)
        
        # Connect to settings changes
        self.settings_service.ai_settings_changed.connect(self.on_ai_settings_changed)
        self.settings_service.ui_settings_changed.connect(self.on_ui_settings_changed)
        
        # Initialize other components with settings
        self.initialize_with_settings()
    
    def show_settings_dialog(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings_service, self)
        dialog.settings_applied.connect(self.on_settings_applied)
        dialog.exec()
    
    def on_ai_settings_changed(self):
        """Handle AI settings changes."""
        # Reinitialize AI service with new settings
        self.conversation_manager.update_ai_settings()
    
    def on_ui_settings_changed(self):
        """Handle UI settings changes."""
        # Apply new UI settings
        settings = self.settings_service.get_settings()
        self.apply_ui_theme(settings.ui.theme)
        self.update_window_opacity(settings.window.active_opacity)
```

This comprehensive settings system provides secure configuration management, user-friendly dialogs, and seamless integration with the main application while working within standard user permissions.