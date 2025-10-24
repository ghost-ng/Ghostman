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
try:  # Optional import; during early bootstrap PyQt may be absent
    from PyQt6.QtCore import QStandardPaths  # type: ignore
except Exception:  # pragma: no cover
    QStandardPaths = None
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
            'window_size': {'width': 400, 'height': 600},
            'repl_window_size': {'width': 520, 'height': 450}
        },
        'interface': {  # new namespace for percent-based values
            'opacity': 90  # percent (10-100)
        },
        'fonts': {
            'ai_response': {
                'family': 'Segoe UI',  # Font family for AI responses
                'size': 11,            # Font size in points
                'weight': 'normal',    # Font weight: normal, bold
                'style': 'normal'      # Font style: normal, italic
            },
            'user_input': {
                'family': 'Consolas',  # Font family for user input
                'size': 10,            # Font size in points  
                'weight': 'normal',    # Font weight: normal, bold
                'style': 'normal'      # Font style: normal, italic
            }
        },
        'resize': {
            'enabled': True,  # Master enable/disable for resize functionality
            'border_width': 8,  # Resize border width in pixels
            'enable_cursor_changes': True,  # Show resize cursors
            'avatar': {
                'enabled': True,
                'border_width': 6,  # Smaller border for avatar
                'min_size': {'width': 80, 'height': 80},
                'max_size': {'width': 200, 'height': 200},
                'maintain_aspect_ratio': True
            },
            'repl': {
                'enabled': True,
                'border_width': 8,
                'min_size': {'width': 360, 'height': 320},
                'max_size': {'width': None, 'height': None}  # Unlimited
            }
        },
        'ai': {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'max_tokens': 16384,  # Increased for modern AI models
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
    
    APP_DIR_NAME = "Ghostman"
    CONFIG_SUBDIR = "configs"

    def __init__(self):
        # Resolve preferred settings directory (AppData/Ghostman/configs)
        self.settings_dir = self._determine_settings_dir()
        self.settings_file = self.settings_dir / "settings.json"
        self.key_file = self.settings_dir / ".key"

        self._settings = {}
        self._encryption_key = None

        self._ensure_settings_dir()
        # Clean up any nested path issues
        self._cleanup_nested_paths()
        self._initialize_encryption()
        self.load()
        self._log_paths()

    # --- Path / Migration helpers -------------------------------------------------
    def _determine_settings_dir(self) -> Path:
        """Determine settings directory.

        Always uses platform-specific AppData location (AppData/Roaming/Ghostman on Windows).
        No longer supports legacy ~/.ghostman directory.
        """
        # Try to get platform-specific AppData location
        try:
            if QStandardPaths:
                base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
                if base:
                    base_path = Path(base)
                    # If base already ends with Ghostman (case-insensitive), reuse it
                    if base_path.name.lower() == self.APP_DIR_NAME.lower():
                        settings_root = base_path
                    else:
                        settings_root = base_path / self.APP_DIR_NAME
                    settings_dir = settings_root / self.CONFIG_SUBDIR
                    settings_dir.mkdir(parents=True, exist_ok=True)
                    return settings_dir
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed to get Qt AppData location: {e}")
        
        # Fallback to manual AppData path on Windows
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA')
            if appdata:
                settings_dir = Path(appdata) / self.APP_DIR_NAME / self.CONFIG_SUBDIR
                settings_dir.mkdir(parents=True, exist_ok=True)
                return settings_dir
        
        # Last resort fallback (should rarely happen)
        fallback_dir = Path.home() / f".{self.APP_DIR_NAME.lower()}_data" / self.CONFIG_SUBDIR
        fallback_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback settings directory: {fallback_dir}")
        return fallback_dir

    def _migrate_legacy(self):
        """No longer migrates from legacy ~/.ghostman - this method is kept for compatibility."""
        # Legacy migration removed - all data should be in APPDATA
        pass
    
    def _cleanup_nested_paths(self):
        """Cleanup accidental nested Ghostman/Ghostman/configs (from older path logic)."""
        try:
            # Example of bad nesting: .../AppData/Roaming/Ghostman/Ghostman/configs
            parts = [p.lower() for p in self.settings_dir.parts]
            # Look for duplicate consecutive 'ghostman'
            for i in range(len(parts) - 1):
                if parts[i] == self.APP_DIR_NAME.lower() and parts[i+1] == self.APP_DIR_NAME.lower():
                    # target nested root
                    nested_root = Path(*self.settings_dir.parts[:i+2])  # first Ghostman/Ghostman
                    good_root = Path(*self.settings_dir.parts[:i+1])    # first Ghostman
                    if nested_root.name.lower() == self.APP_DIR_NAME.lower():
                        nested_configs = nested_root / self.CONFIG_SUBDIR
                        good_configs = good_root / self.CONFIG_SUBDIR
                        if nested_configs.exists():
                            good_configs.mkdir(parents=True, exist_ok=True)
                            # Move files
                            for item in nested_configs.iterdir():
                                target = good_configs / item.name
                                if not target.exists():
                                    item.replace(target)
                            # Update self.settings_dir if we moved current directory
                            if self.settings_dir == nested_configs:
                                self.settings_dir = good_configs
                                self.settings_file = self.settings_dir / "settings.json"
                                self.key_file = self.settings_dir / ".key"
                            logger.info(f"Flattened duplicate Ghostman path. Using {self.settings_dir}")
                        break
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed cleaning nested Ghostman folders: {e}")

    def _log_paths(self):
        """Log resolved settings-related paths for diagnostics."""
        try:
            logger.info(
                "Paths: settings_dir=%s settings_file=%s key_file=%s",
                self.settings_dir,
                self.settings_file,
                self.key_file
            )
        except Exception:  # pragma: no cover
            pass

    def get_paths(self) -> Dict[str, str]:
        """Return important path locations (for external logging / UI)."""
        return {
            'settings_dir': str(self.settings_dir),
            'settings_file': str(self.settings_file),
            'key_file': str(self.key_file)
        }
    
    def _ensure_settings_dir(self):
        """Ensure directory exists (idempotent)."""
        self.settings_dir.mkdir(parents=True, exist_ok=True)
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
        
        if self._encryption_key is None:  # pragma: no cover - defensive
            raise RuntimeError("Encryption key not initialized")
        fernet = Fernet(self._encryption_key)
        encrypted = fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value."""
        try:
            if self._encryption_key is None:  # pragma: no cover - defensive
                raise RuntimeError("Encryption key not initialized")
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
        
        # Special case: max_tokens is NOT sensitive even though it contains "token"
        if 'max_tokens' in key_lower:
            return False
            
        # Check for exact matches or common patterns
        # Only consider it sensitive if it ends with a sensitive key or has it as a complete segment
        path_parts = key_lower.split('.')
        for part in path_parts:
            if part in self.SENSITIVE_KEYS:
                return True
                
        # Also check for compound words like "api_key" or "apikey"
        for sensitive in self.SENSITIVE_KEYS:
            if sensitive in key_lower and sensitive != 'token':  # 'token' is too generic
                return True
                
        return False
    
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
                # Backward compatibility: migrate legacy ui.window_opacity -> interface.opacity percent
                try:
                    ui_cfg = self._settings.get('ui', {})
                    interface_cfg = self._settings.setdefault('interface', {})
                    if 'window_opacity' in ui_cfg and 'opacity' not in interface_cfg:
                        legacy_op = ui_cfg.get('window_opacity')
                        if isinstance(legacy_op, (int, float)):
                            if legacy_op <= 1.0:
                                percent = int(round(float(legacy_op) * 100))
                            else:
                                percent = int(legacy_op)
                            percent = max(10, min(100, percent))
                            interface_cfg['opacity'] = percent
                            logger.info(f"Migrated legacy ui.window_opacity {legacy_op} -> interface.opacity {percent}%")
                            self.save()
                except Exception as e:  # pragma: no cover
                    logger.warning(f"Opacity migration failed: {e}")
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
    
    # Resize-specific helper methods
    def get_resize_config(self, widget_type: str = None) -> Dict[str, Any]:
        """
        Get resize configuration for a specific widget type or global.
        
        Args:
            widget_type: 'avatar', 'repl', or None for global settings
            
        Returns:
            Dictionary containing resize configuration
        """
        base_config = {
            'enabled': self.get('resize.enabled', True),
            'border_width': self.get('resize.border_width', 8),
            'enable_cursor_changes': self.get('resize.enable_cursor_changes', True),
        }
        
        if widget_type:
            widget_config = self.get(f'resize.{widget_type}', {})
            base_config.update(widget_config)
        
        return base_config
    
    def set_resize_config(self, config: Dict[str, Any], widget_type: str = None):
        """
        Set resize configuration for a specific widget type or global.
        
        Args:
            config: Configuration dictionary to set
            widget_type: 'avatar', 'repl', or None for global settings
        """
        if widget_type:
            # Set widget-specific config
            for key, value in config.items():
                self.set(f'resize.{widget_type}.{key}', value)
        else:
            # Set global config
            for key, value in config.items():
                self.set(f'resize.{key}', value)
    
    def is_resize_enabled(self, widget_type: str = None) -> bool:
        """
        Check if resize is enabled globally and for a specific widget type.
        
        Args:
            widget_type: 'avatar', 'repl', or None for global check only
            
        Returns:
            True if resize is enabled
        """
        global_enabled = self.get('resize.enabled', True)
        if not global_enabled:
            return False
        
        if widget_type:
            return self.get(f'resize.{widget_type}.enabled', True)
        
        return True


# Global settings instance
settings = SettingsManager()