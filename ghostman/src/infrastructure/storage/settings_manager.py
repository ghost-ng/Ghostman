"""
Settings Manager with encryption support for Ghostman.

Provides secure storage of application settings including API keys,
with dot notation access and automatic encryption of sensitive data.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger("ghostman.settings")


class SettingsManager:
    """
    Manages application settings with encryption for sensitive data.
    
    Features:
    - Dot notation access (settings.ui.window_opacity)
    - Automatic encryption of sensitive keys (API keys, tokens)
    - Secure storage in user directory without admin permissions
    - Default value handling
    """
    
    SENSITIVE_KEYS = {
        'openai_api_key',
        'anthropic_api_key', 
        'api_key',
        'token',
        'password',
        'secret'
    }
    
    DEFAULT_SETTINGS = {
        'ui': {
            'window_opacity': 0.95,
            'always_on_top': True,
            'start_minimized': False,
            'auto_restore_on_response': True,
            'window_position': {'x': 100, 'y': 100},
            'window_size': {'width': 400, 'height': 600}
        },
        'ai': {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'max_tokens': 4096,
            'temperature': 0.7,
            'stream_responses': True
        },
        'app': {
            'current_state': 'tray',  # 'tray' or 'avatar'
            'log_level': 'INFO',
            'auto_start': False,
            'check_updates': True
        },
        'tray': {
            'show_animations': True,
            'status_tooltips': True,
            'context_menu_items': ['show', 'settings', 'about', 'quit']
        }
    }
    
    def __init__(self):
        self.settings_dir = Path.home() / ".ghostman"
        self.settings_file = self.settings_dir / "settings.json"
        self.key_file = self.settings_dir / ".key"
        
        self._settings = {}
        self._encryption_key = None
        
        self._ensure_settings_dir()
        self._initialize_encryption()
        self.load()
    
    def _ensure_settings_dir(self):
        """Create settings directory if it doesn't exist."""
        self.settings_dir.mkdir(exist_ok=True)
        logger.debug(f"Settings directory: {self.settings_dir}")
    
    def _initialize_encryption(self):
        """Initialize or load encryption key for sensitive data."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self._encryption_key = f.read()
        else:
            # Generate new encryption key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            # Use machine-specific entropy for key generation
            password = (str(Path.home()) + str(os.environ.get('USERNAME', 'user'))).encode()
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self._encryption_key = key
            
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Hide key file on Windows
            if os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(self.key_file), 2)  # Hidden
        
        logger.debug("Encryption key initialized")
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value."""
        if not isinstance(value, str):
            value = str(value)
        
        fernet = Fernet(self._encryption_key)
        encrypted = fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value."""
        try:
            fernet = Fernet(self._encryption_key)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return ""
    
    def _is_sensitive_key(self, key_path: str) -> bool:
        """Check if a key path contains sensitive data."""
        key_lower = key_path.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)
    
    def _get_nested_dict(self, data: Dict, path: str, create_missing: bool = False) -> tuple:
        """Navigate nested dictionary structure using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                if create_missing:
                    current[key] = {}
                else:
                    return None, keys[-1]
            current = current[key]
        
        return current, keys[-1]
    
    def load(self):
        """Load settings from file or create defaults."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
                logger.info("Settings loaded successfully")
            else:
                self._settings = self.DEFAULT_SETTINGS.copy()
                self.save()
                logger.info("Default settings created")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
    
    def save(self):
        """Save current settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            logger.debug("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get setting value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., 'ui.window_opacity')
            default: Default value if key doesn't exist
            
        Returns:
            Setting value, with automatic decryption for sensitive keys
        """
        try:
            parent_dict, final_key = self._get_nested_dict(self._settings, key_path)
            
            if parent_dict is None or final_key not in parent_dict:
                return default
            
            value = parent_dict[final_key]
            
            # Decrypt sensitive values
            if self._is_sensitive_key(key_path) and isinstance(value, str) and value.startswith('enc:'):
                return self._decrypt_value(value[4:])  # Remove 'enc:' prefix
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to get setting '{key_path}': {e}")
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set setting value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., 'ui.window_opacity')
            value: Value to set, with automatic encryption for sensitive keys
        """
        try:
            parent_dict, final_key = self._get_nested_dict(self._settings, key_path, create_missing=True)
            
            # Encrypt sensitive values
            if self._is_sensitive_key(key_path) and value:
                value = f"enc:{self._encrypt_value(str(value))}"
            
            parent_dict[final_key] = value
            self.save()
            logger.debug(f"Setting '{key_path}' updated")
            
        except Exception as e:
            logger.error(f"Failed to set setting '{key_path}': {e}")
    
    def delete(self, key_path: str):
        """Delete a setting using dot notation."""
        try:
            parent_dict, final_key = self._get_nested_dict(self._settings, key_path)
            
            if parent_dict is not None and final_key in parent_dict:
                del parent_dict[final_key]
                self.save()
                logger.debug(f"Setting '{key_path}' deleted")
                
        except Exception as e:
            logger.error(f"Failed to delete setting '{key_path}': {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings (sensitive values remain encrypted)."""
        return self._settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._settings = self.DEFAULT_SETTINGS.copy()
        self.save()
        logger.info("Settings reset to defaults")


# Global settings instance
settings = SettingsManager()