# Settings System Implementation Plan

## Overview

This document outlines the comprehensive settings system for Ghostman, providing secure configuration management, user preferences, and system integration settings. The system must work without administrator permissions while supporting the two application states: maximized avatar mode and minimized tray mode.

## Core Requirements

### Settings Categories
1. **AI Configuration**: API endpoints, models, authentication
2. **UI Behavior**: Window appearance, opacity, positioning
3. **Application States**: State transition preferences and behaviors
4. **Conversation Management**: Token limits, memory strategies
5. **System Integration**: Startup behavior, tray functionality
6. **Security & Privacy**: Data encryption, cleanup policies

### Technical Constraints
- **No admin permissions required** for configuration access
- **Secure credential storage** for API keys
- **Persistent settings** across application restarts
- **Thread-safe access** for multi-threaded operations
- **Data validation** and error recovery

## Implementation Architecture

### 1. Settings Manager Core

**File**: `ghostman/src/infrastructure/settings/settings_manager.py`

```python
"""Core settings management for Ghostman application."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from threading import Lock
import toml
from cryptography.fernet import Fernet
import base64
import os
from datetime import datetime

from .settings_schemas import SettingsSchema, validate_settings
from .encryption_service import EncryptionService

@dataclass
class SettingsMetadata:
    """Metadata for settings file."""
    version: str = "1.0.0"
    created_at: str = ""
    last_modified: str = ""
    schema_version: str = "1.0.0"

class SettingsManager:
    """Manages application settings with encryption and validation."""
    
    def __init__(self, settings_file: Path):
        self.settings_file = Path(settings_file)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("ghostman.settings")
        self._lock = Lock()
        
        # Initialize encryption service
        self.encryption_service = EncryptionService(
            self.settings_file.parent / ".ghostman_key"
        )
        
        # Default settings
        self._default_settings = self._load_default_settings()
        self._current_settings = {}
        self._metadata = SettingsMetadata()
        
        # Load settings
        self.load_settings()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default settings configuration."""
        return {
            # AI Configuration
            "ai": {
                "provider": "openai",
                "api_url": "https://api.openai.com/v1",
                "model": "gpt-3.5-turbo",
                "max_tokens": 4000,
                "temperature": 0.7,
                "stream_responses": True,
                "timeout_seconds": 30,
                "retry_attempts": 3
            },
            
            # Application State Management
            "app_state": {
                "startup_state": "tray",  # "tray" or "maximized"
                "remember_last_state": True,
                "auto_show_on_activity": False,
                "minimize_to_tray_on_escape": True,
                "close_to_tray": True
            },
            
            # UI Configuration
            "ui": {
                "theme": "dark",
                "window_opacity": 0.95,
                "font_size": 12,
                "font_family": "Segoe UI",
                "animation_duration": 200,
                "show_typing_indicator": True,
                "compact_mode": False
            },
            
            # Window Behavior
            "window": {
                "always_on_top": True,
                "draggable": True,
                "snap_to_edges": True,
                "snap_distance": 20,
                "remember_position": True,
                "remember_size": True,
                "default_width": 450,
                "default_height": 600,
                "minimum_width": 400,
                "minimum_height": 500
            },
            
            # Conversation Management
            "conversation": {
                "memory_strategy": "hybrid",
                "max_conversation_tokens": 4000,
                "auto_save": True,
                "auto_save_interval": 30,
                "keep_conversation_days": 30,
                "search_enabled": True,
                "export_format": "json"
            },
            
            # System Integration
            "system": {
                "start_with_windows": False,
                "minimize_on_startup": True,
                "system_tray_enabled": True,
                "tray_notifications": False,
                "global_hotkey": "",
                "auto_update_check": True
            },
            
            # Privacy & Security
            "privacy": {
                "encrypt_conversations": True,
                "clear_clipboard_timeout": 30,
                "secure_deletion": True,
                "anonymous_telemetry": False,
                "data_retention_days": 90,
                "auto_cleanup_enabled": True
            },
            
            # Logging Configuration
            "logging": {
                "level": "INFO",
                "enable_performance_logging": True,
                "enable_security_logging": True,
                "log_retention_days": 30,
                "max_log_size_mb": 10
            }
        }
    
    def load_settings(self):
        """Load settings from file."""
        with self._lock:
            try:
                if self.settings_file.exists():
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract metadata
                    if 'metadata' in data:
                        self._metadata = SettingsMetadata(**data['metadata'])
                    
                    # Load settings
                    if 'settings' in data:
                        loaded_settings = data['settings']
                        
                        # Decrypt sensitive data
                        loaded_settings = self._decrypt_sensitive_settings(loaded_settings)
                        
                        # Validate settings
                        if validate_settings(loaded_settings):
                            self._current_settings = self._merge_with_defaults(loaded_settings)
                        else:
                            self.logger.warning("Invalid settings detected, using defaults")
                            self._current_settings = self._default_settings.copy()
                    else:
                        self._current_settings = self._default_settings.copy()
                else:
                    # First run - create with defaults
                    self._current_settings = self._default_settings.copy()
                    self.save_settings()
                
                self.logger.info("Settings loaded successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to load settings: {e}")
                self._current_settings = self._default_settings.copy()
    
    def save_settings(self):
        """Save current settings to file."""
        with self._lock:
            try:
                # Update metadata
                self._metadata.last_modified = datetime.utcnow().isoformat()
                if not self._metadata.created_at:
                    self._metadata.created_at = self._metadata.last_modified
                
                # Encrypt sensitive data
                settings_to_save = self._encrypt_sensitive_settings(self._current_settings)
                
                # Prepare data structure
                data = {
                    'metadata': asdict(self._metadata),
                    'settings': settings_to_save
                }
                
                # Write to file
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.logger.info("Settings saved successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to save settings: {e}")
                raise
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """Get a setting value using dot notation (e.g., 'ai.model')."""
        with self._lock:
            try:
                keys = key_path.split('.')
                value = self._current_settings
                
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return default
                
                return value
                
            except Exception:
                return default
    
    def update_setting(self, key_path: str, value: Any):
        """Update a setting value using dot notation."""
        with self._lock:
            try:
                keys = key_path.split('.')
                current = self._current_settings
                
                # Navigate to parent
                for key in keys[:-1]:
                    if key not in current or not isinstance(current[key], dict):
                        current[key] = {}
                    current = current[key]
                
                # Set value
                old_value = current.get(keys[-1])
                current[keys[-1]] = value
                
                # Save settings
                self.save_settings()
                
                self.logger.info(f"Setting updated: {key_path} = {value}")
                
                # Notify listeners of critical changes
                self._handle_setting_change(key_path, old_value, value)
                
            except Exception as e:
                self.logger.error(f"Failed to update setting {key_path}: {e}")
                raise
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get a copy of all current settings."""
        with self._lock:
            return self._deep_copy_dict(self._current_settings)
    
    def reset_to_defaults(self, category: Optional[str] = None):
        """Reset settings to defaults."""
        with self._lock:
            if category:
                if category in self._default_settings:
                    self._current_settings[category] = self._default_settings[category].copy()
                    self.logger.info(f"Reset {category} settings to defaults")
            else:
                self._current_settings = self._default_settings.copy()
                self.logger.info("Reset all settings to defaults")
            
            self.save_settings()
    
    def backup_settings(self, backup_path: Optional[Path] = None) -> Path:
        """Create a backup of current settings."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.settings_file.parent / f"settings_backup_{timestamp}.json"
        
        try:
            # Create backup without encryption
            backup_data = {
                'metadata': asdict(self._metadata),
                'settings': self._current_settings,
                'backup_timestamp': datetime.utcnow().isoformat(),
                'backup_version': self._metadata.version
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Settings backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to backup settings: {e}")
            raise
    
    def restore_from_backup(self, backup_path: Path):
        """Restore settings from backup."""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            if 'settings' in backup_data:
                restored_settings = backup_data['settings']
                
                # Validate restored settings
                if validate_settings(restored_settings):
                    self._current_settings = self._merge_with_defaults(restored_settings)
                    self.save_settings()
                    self.logger.info(f"Settings restored from: {backup_path}")
                else:
                    raise ValueError("Invalid settings in backup file")
            else:
                raise ValueError("No settings found in backup file")
                
        except Exception as e:
            self.logger.error(f"Failed to restore settings: {e}")
            raise
    
    def _merge_with_defaults(self, loaded_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded settings with defaults to ensure all keys exist."""
        merged = self._deep_copy_dict(self._default_settings)
        self._deep_merge_dict(merged, loaded_settings)
        return merged
    
    def _deep_copy_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary."""
        import copy
        return copy.deepcopy(d)
    
    def _deep_merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source dictionary into target."""
        for key, value in source.items():
            if (key in target and 
                isinstance(target[key], dict) and 
                isinstance(value, dict)):
                self._deep_merge_dict(target[key], value)
            else:
                target[key] = value
    
    def _encrypt_sensitive_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive settings values."""
        encrypted_settings = self._deep_copy_dict(settings)
        
        # Define sensitive keys that should be encrypted
        sensitive_keys = [
            "ai.api_key",
            "ai.organization_id",
            "privacy.user_id"
        ]
        
        for key_path in sensitive_keys:
            value = self.get_setting(key_path)
            if value:
                try:
                    encrypted_value = self.encryption_service.encrypt(str(value))
                    self._set_nested_value(encrypted_settings, key_path, encrypted_value)
                except Exception as e:
                    self.logger.error(f"Failed to encrypt {key_path}: {e}")
        
        return encrypted_settings
    
    def _decrypt_sensitive_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive settings values."""
        decrypted_settings = self._deep_copy_dict(settings)
        
        # Define sensitive keys that should be decrypted
        sensitive_keys = [
            "ai.api_key",
            "ai.organization_id", 
            "privacy.user_id"
        ]
        
        for key_path in sensitive_keys:
            value = self._get_nested_value(settings, key_path)
            if value and isinstance(value, str):
                try:
                    # Check if value looks encrypted (base64)
                    if self._looks_encrypted(value):
                        decrypted_value = self.encryption_service.decrypt(value)
                        self._set_nested_value(decrypted_settings, key_path, decrypted_value)
                except Exception as e:
                    self.logger.error(f"Failed to decrypt {key_path}: {e}")
                    # Keep original value if decryption fails
        
        return decrypted_settings
    
    def _looks_encrypted(self, value: str) -> bool:
        """Check if a string looks like it's encrypted."""
        try:
            # Simple check for base64-encoded data
            base64.b64decode(value.encode())
            return len(value) > 20 and '=' in value[-4:]
        except:
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get nested dictionary value using dot notation."""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, data: Dict[str, Any], key_path: str, value: Any):
        """Set nested dictionary value using dot notation."""
        keys = key_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _handle_setting_change(self, key_path: str, old_value: Any, new_value: Any):
        """Handle critical setting changes that require immediate action."""
        # Handle AI configuration changes
        if key_path.startswith("ai."):
            self.logger.info(f"AI configuration changed: {key_path}")
        
        # Handle UI changes
        elif key_path.startswith("ui."):
            self.logger.info(f"UI configuration changed: {key_path}")
        
        # Handle app state changes
        elif key_path.startswith("app_state."):
            self.logger.info(f"App state configuration changed: {key_path}")
        
        # Handle system integration changes
        elif key_path.startswith("system."):
            if key_path == "system.start_with_windows":
                self._handle_startup_setting_change(new_value)
    
    def _handle_startup_setting_change(self, enabled: bool):
        """Handle changes to startup with Windows setting."""
        try:
            if enabled:
                self._enable_startup_with_windows()
            else:
                self._disable_startup_with_windows()
        except Exception as e:
            self.logger.error(f"Failed to update startup setting: {e}")
    
    def _enable_startup_with_windows(self):
        """Enable startup with Windows (no admin required)."""
        try:
            import winreg
            import sys
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            app_path = sys.executable
            winreg.SetValueEx(key, "Ghostman", 0, winreg.REG_SZ, f'"{app_path}" --minimized')
            winreg.CloseKey(key)
            
            self.logger.info("Enabled startup with Windows")
            
        except Exception as e:
            self.logger.error(f"Failed to enable startup with Windows: {e}")
    
    def _disable_startup_with_windows(self):
        """Disable startup with Windows."""
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            try:
                winreg.DeleteValue(key, "Ghostman")
                self.logger.info("Disabled startup with Windows")
            except FileNotFoundError:
                pass  # Already disabled
            
            winreg.CloseKey(key)
            
        except Exception as e:
            self.logger.error(f"Failed to disable startup with Windows: {e}")
    
    def get_settings_info(self) -> Dict[str, Any]:
        """Get information about the settings system."""
        return {
            'settings_file': str(self.settings_file),
            'file_exists': self.settings_file.exists(),
            'file_size_bytes': self.settings_file.stat().st_size if self.settings_file.exists() else 0,
            'metadata': asdict(self._metadata),
            'encryption_enabled': self.encryption_service.is_enabled(),
            'total_settings': len(self._current_settings)
        }
```

### 2. Encryption Service

**File**: `ghostman/src/infrastructure/settings/encryption_service.py`

```python
"""Encryption service for sensitive settings data."""

import os
import base64
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionService:
    """Handles encryption/decryption of sensitive settings data."""
    
    def __init__(self, key_file: Path):
        self.key_file = Path(key_file)
        self.logger = logging.getLogger("ghostman.encryption")
        
        self._fernet: Optional[Fernet] = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption system."""
        try:
            # Create key file directory
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.key_file.exists():
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                
                # Save key with restricted permissions
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                
                # Set file permissions (Windows)
                if os.name == 'nt':
                    try:
                        import stat
                        os.chmod(self.key_file, stat.S_IREAD | stat.S_IWRITE)
                    except:
                        pass  # Permissions setting is best-effort
                
                self.logger.info("Generated new encryption key")
            
            self._fernet = Fernet(key)
            self.logger.info("Encryption service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        if not self._fernet:
            self.logger.warning("Encryption not available, returning plaintext")
            return plaintext
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            return plaintext
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a string value."""
        if not self._fernet:
            self.logger.warning("Encryption not available, returning encrypted text")
            return encrypted_text
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            plaintext_bytes = self._fernet.decrypt(encrypted_bytes)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            return encrypted_text
    
    def is_enabled(self) -> bool:
        """Check if encryption is properly enabled."""
        return self._fernet is not None
    
    def rotate_key(self):
        """Generate a new encryption key (existing data will need re-encryption)."""
        try:
            # Backup old key
            if self.key_file.exists():
                backup_path = self.key_file.with_suffix('.key.backup')
                self.key_file.rename(backup_path)
                self.logger.info(f"Backed up old key to {backup_path}")
            
            # Generate new key
            new_key = Fernet.generate_key()
            
            with open(self.key_file, 'wb') as f:
                f.write(new_key)
            
            self._fernet = Fernet(new_key)
            
            self.logger.info("Encryption key rotated")
            
        except Exception as e:
            self.logger.error(f"Key rotation failed: {e}")
            raise
```

### 3. Settings Validation

**File**: `ghostman/src/infrastructure/settings/settings_schemas.py`

```python
"""Settings validation schemas and functions."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of settings validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

def validate_settings(settings: Dict[str, Any]) -> bool:
    """Validate settings dictionary against schema."""
    logger = logging.getLogger("ghostman.settings")
    
    try:
        result = _validate_settings_schema(settings)
        
        if not result.is_valid:
            logger.error(f"Settings validation failed: {result.errors}")
            return False
        
        if result.warnings:
            for warning in result.warnings:
                logger.warning(f"Settings validation warning: {warning}")
        
        return True
        
    except Exception as e:
        logger.error(f"Settings validation error: {e}")
        return False

def _validate_settings_schema(settings: Dict[str, Any]) -> ValidationResult:
    """Validate settings against defined schema."""
    errors = []
    warnings = []
    
    # Validate AI settings
    if 'ai' in settings:
        ai_errors, ai_warnings = _validate_ai_settings(settings['ai'])
        errors.extend(ai_errors)
        warnings.extend(ai_warnings)
    
    # Validate UI settings
    if 'ui' in settings:
        ui_errors, ui_warnings = _validate_ui_settings(settings['ui'])
        errors.extend(ui_errors)
        warnings.extend(ui_warnings)
    
    # Validate app state settings
    if 'app_state' in settings:
        state_errors, state_warnings = _validate_app_state_settings(settings['app_state'])
        errors.extend(state_errors)
        warnings.extend(state_warnings)
    
    # Add more category validations...
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def _validate_ai_settings(ai_settings: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate AI configuration settings."""
    errors = []
    warnings = []
    
    # Validate API URL
    if 'api_url' in ai_settings:
        url = ai_settings['api_url']
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            errors.append("AI API URL must be a valid HTTP/HTTPS URL")
    
    # Validate model
    if 'model' in ai_settings:
        model = ai_settings['model']
        if not isinstance(model, str) or len(model.strip()) == 0:
            errors.append("AI model must be a non-empty string")
    
    # Validate max_tokens
    if 'max_tokens' in ai_settings:
        max_tokens = ai_settings['max_tokens']
        if not isinstance(max_tokens, int) or max_tokens < 100 or max_tokens > 128000:
            errors.append("max_tokens must be between 100 and 128000")
    
    # Validate temperature
    if 'temperature' in ai_settings:
        temp = ai_settings['temperature']
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            errors.append("temperature must be between 0 and 2")
    
    return errors, warnings

def _validate_ui_settings(ui_settings: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate UI configuration settings."""
    errors = []
    warnings = []
    
    # Validate window opacity
    if 'window_opacity' in ui_settings:
        opacity = ui_settings['window_opacity']
        if not isinstance(opacity, (int, float)) or opacity < 0.1 or opacity > 1.0:
            errors.append("window_opacity must be between 0.1 and 1.0")
    
    # Validate theme
    if 'theme' in ui_settings:
        theme = ui_settings['theme']
        valid_themes = ['dark', 'light', 'auto']
        if theme not in valid_themes:
            errors.append(f"theme must be one of: {valid_themes}")
    
    return errors, warnings

def _validate_app_state_settings(state_settings: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate application state settings."""
    errors = []
    warnings = []
    
    # Validate startup state
    if 'startup_state' in state_settings:
        startup = state_settings['startup_state']
        valid_states = ['tray', 'maximized']
        if startup not in valid_states:
            errors.append(f"startup_state must be one of: {valid_states}")
    
    return errors, warnings
```

## Key Features

### 1. State Management Integration
- Settings for both maximized avatar mode and tray mode
- State transition preferences and behaviors
- Persistent state across sessions

### 2. Security & Privacy
- Encrypted storage of sensitive data (API keys)
- Secure key management without admin permissions
- Privacy-focused default settings

### 3. Validation & Recovery
- Comprehensive settings validation
- Automatic fallback to defaults on corruption
- Settings backup and restore functionality

### 4. User Experience
- Intuitive settings organization
- Real-time setting updates
- Import/export capabilities

This settings system provides a robust foundation for managing all aspects of the Ghostman application while maintaining security and user privacy.