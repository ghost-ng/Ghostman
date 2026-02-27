"""
Settings Manager with encryption support for Specter.

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

logger = logging.getLogger("specter.settings")


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
            'repl_window_size': {'width': 520, 'height': 650},
            'avatar_position': None,
            'avatar_size': {'width': 120, 'height': 120},
            'repl_position': None,
            'repl_size': {'width': 520, 'height': 650},
            'repl_width': 520,
            'repl_height': 650,
            'theme': 'cyber'
        },
        'interface': {
            'opacity': 97,  # percent (10-100)
            'icon_size': 5,  # icon size (1-10, default 5)
            'repl_attached': False,
            'repl_attach_offset': None,
            'repl_was_visible': False,
            'always_on_top': True
        },
        'ai_model': {
            'preset': 'Custom',
            'model_name': '',
            'base_url': '',
            'api_key': '',
            'temperature': 0.7,
            'max_tokens': 16384,
            'system_prompt': '',
            'user_prompt': 'Your name is Spector, a friendly ghost AI assistant that helps with anything - be friendly, courteous, and a tadbit sassy!'
        },
        'advanced': {
            'log_level': 'INFO',
            'log_location': '',
            'log_retention_days': 10,
            'ignore_ssl_verification': False,
            'custom_ca_path': '',
            'auto_detect_code_language': True,
            'enable_code_lexing': True,
            'enable_debug_commands': False,
            'enable_ai_intent_classification': False,  # AI-powered skill detection fallback
            'ai_intent_confidence_threshold': 0.65,    # Minimum confidence for AI classification (0.0-1.0)
            'ai_intent_timeout_seconds': 5             # Timeout for AI classification requests
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
            },
            'user_customized': False   # Whether user manually changed fonts (vs theme defaults)
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
        },
        'pki': {
            'enabled': False,
            'client_cert_path': None,
            'client_key_path': None,
            'ca_chain_path': None,
            'p12_file_hash': None,
            'last_validation': None,
            'certificate_info': None
        },
        'screen_capture': {
            'default_save_path': '',  # Empty string = use default %APPDATA%\Specter\captures
            'border_color': '#FF0000'  # Default red border color
        },
        'tools': {
            'enabled': True,                    # Master toggle for AI tool calling
            'max_tool_iterations': 5,           # Max tool-call loop iterations per message
            'web_search': {
                'enabled': True,
                'max_results': 5,
                'tavily_api_key': ''  # Empty = use DuckDuckGo (free); set key for Tavily
            },
            'docx_formatter': {
                'enabled': True,
                'default_font': 'Calibri',
                'default_font_size': 11,
                'line_spacing': 1.15,
                'margins': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0},
                'default_operations': [
                    'standardize_fonts', 'fix_margins', 'normalize_spacing',
                    'fix_bullets', 'fix_spelling', 'fix_case', 'normalize_headings'
                ]
            }
        },
        'embedding': {
            'base_url': '',      # Empty = inherit from ai_model.base_url
            'api_key': '',       # Empty = inherit from ai_model.api_key
            'model': 'text-embedding-3-small',
        },
        'avatar': {
            'selected': 'specter',
            'scale': 1.0
        },
        'document_studio': {
            'panel_visible': False,
            'splitter_sizes': [600, 350],
            'recipes': {},
        },
    }
    
    APP_DIR_NAME = "Specter"
    CONFIG_SUBDIR = "configs"

    def __init__(self):
        # Resolve preferred settings directory (AppData/Specter/configs)
        self.settings_dir = self._determine_settings_dir()
        self.settings_file = self.settings_dir / "settings.json"
        self.key_file = self.settings_dir / ".key"

        self._settings = {}
        self._encryption_key = None
        self._change_callbacks = []  # Observer callbacks for settings changes

        self._ensure_settings_dir()
        # Clean up any nested path issues
        self._cleanup_nested_paths()
        self._initialize_encryption()
        self.load()
        self._log_paths()

    # --- Observer pattern for settings changes ------------------------------------

    def on_change(self, callback) -> None:
        """Register a callback to be notified when settings change.

        Args:
            callback: Callable accepting one argument (the dot-notation key that changed).
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def remove_change_callback(self, callback) -> None:
        """Remove a previously registered change callback."""
        try:
            self._change_callbacks.remove(callback)
        except ValueError:
            pass

    def _notify_change(self, key_path: str) -> None:
        """Notify all registered callbacks that a setting changed."""
        for cb in self._change_callbacks:
            try:
                cb(key_path)
            except Exception as e:
                logger.warning(f"Settings change callback error for key '{key_path}': {e}")

    # --- Path / Migration helpers -------------------------------------------------
    def _determine_settings_dir(self) -> Path:
        """Determine settings directory.

        Always uses platform-specific AppData location (AppData/Roaming/Specter on Windows).
        No longer supports legacy ~/.specter directory.
        """
        # Try to get platform-specific AppData location
        try:
            if QStandardPaths:
                base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
                if base:
                    base_path = Path(base)
                    # If base already ends with Specter (case-insensitive), reuse it
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
        """No longer migrates from legacy ~/.specter - this method is kept for compatibility."""
        # Legacy migration removed - all data should be in APPDATA
        pass
    
    def _cleanup_nested_paths(self):
        """Cleanup accidental nested Specter/Specter/configs (from older path logic)."""
        try:
            # Example of bad nesting: .../AppData/Roaming/Specter/Specter/configs
            parts = [p.lower() for p in self.settings_dir.parts]
            # Look for duplicate consecutive 'specter'
            for i in range(len(parts) - 1):
                if parts[i] == self.APP_DIR_NAME.lower() and parts[i+1] == self.APP_DIR_NAME.lower():
                    # target nested root
                    nested_root = Path(*self.settings_dir.parts[:i+2])  # first Specter/Specter
                    good_root = Path(*self.settings_dir.parts[:i+1])    # first Specter
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
                            logger.info(f"Flattened duplicate Specter path. Using {self.settings_dir}")
                        break
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed cleaning nested Specter folders: {e}")

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
    
    def _migrate_pki_config(self):
        """Migrate PKI configuration from old location (pki/pki_config.json) to main settings."""
        try:
            # Check if PKI config already exists in main settings
            pki_cfg = self._settings.get('pki', {})
            if pki_cfg.get('enabled') or pki_cfg.get('client_cert_path'):
                logger.debug("PKI config already in main settings, skipping migration")
                return

            # Get PKI directory (same logic as certificate_manager)
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', '')
                if not appdata:
                    return
                pki_dir = Path(appdata) / "Specter" / "pki"
            else:  # Linux/Mac
                home = os.path.expanduser("~")
                pki_dir = Path(home) / ".Specter" / "pki"

            old_config_file = pki_dir / "pki_config.json"

            # If old config file exists, migrate it
            if old_config_file.exists():
                logger.info(f"Migrating PKI config from {old_config_file}")
                with open(old_config_file, 'r') as f:
                    old_pki_data = json.load(f)

                # Copy all PKI fields to main settings
                self._settings.setdefault('pki', {})
                self._settings['pki']['enabled'] = old_pki_data.get('enabled', False)
                self._settings['pki']['client_cert_path'] = old_pki_data.get('client_cert_path')
                self._settings['pki']['client_key_path'] = old_pki_data.get('client_key_path')
                self._settings['pki']['ca_chain_path'] = old_pki_data.get('ca_chain_path')
                self._settings['pki']['p12_file_hash'] = old_pki_data.get('p12_file_hash')
                self._settings['pki']['last_validation'] = old_pki_data.get('last_validation')
                self._settings['pki']['certificate_info'] = old_pki_data.get('certificate_info')

                # Save to main settings
                self.save()
                logger.info("✅ PKI config migrated to main settings file")

                # Optionally rename old file to .bak to preserve it
                try:
                    backup_file = old_config_file.with_suffix('.json.bak')
                    old_config_file.rename(backup_file)
                    logger.info(f"Old PKI config backed up to {backup_file}")
                except Exception as e:
                    logger.warning(f"Could not backup old PKI config: {e}")

        except Exception as e:
            logger.warning(f"PKI config migration failed: {e}")

    def _validate_and_merge_settings(self, loaded_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and merge loaded settings with defaults.

        Only keys that exist in DEFAULT_SETTINGS are kept.
        Values are validated for correct data types.
        Missing keys are filled with defaults.

        Args:
            loaded_settings: Settings loaded from file

        Returns:
            Validated and merged settings dictionary
        """
        import copy

        def validate_value(value, default_value, key_path):
            """Validate a single value against its default."""
            # If default is None, allow any type
            if default_value is None:
                return value

            # Type validation
            expected_type = type(default_value)

            # Special handling for numeric types (allow int where float expected)
            if expected_type == float and isinstance(value, (int, float)):
                return float(value)
            elif expected_type == int and isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, expected_type):
                return value
            else:
                logger.warning(
                    f"Invalid type for '{key_path}': expected {expected_type.__name__}, "
                    f"got {type(value).__name__}. Using default: {default_value}"
                )
                return default_value

        def merge_dict(loaded_dict, default_dict, path=""):
            """Recursively merge and validate nested dictionaries."""
            result = {}

            # Start with all default keys
            for key, default_value in default_dict.items():
                current_path = f"{path}.{key}" if path else key

                if key not in loaded_dict:
                    # Missing key - use default
                    result[key] = copy.deepcopy(default_value)
                    logger.debug(f"Using default for missing key: {current_path}")
                else:
                    loaded_value = loaded_dict[key]

                    # Recursively validate nested dictionaries
                    if isinstance(default_value, dict):
                        if isinstance(loaded_value, dict):
                            result[key] = merge_dict(loaded_value, default_value, current_path)
                        else:
                            logger.warning(
                                f"Invalid type for '{current_path}': expected dict, "
                                f"got {type(loaded_value).__name__}. Using default"
                            )
                            result[key] = copy.deepcopy(default_value)
                    else:
                        # Validate primitive value
                        result[key] = validate_value(loaded_value, default_value, current_path)

            # Log any extra keys in loaded settings that don't exist in defaults
            for key in loaded_dict.keys():
                if key not in default_dict:
                    current_path = f"{path}.{key}" if path else key
                    logger.debug(f"Ignoring unknown key from config file: {current_path}")

            return result

        return merge_dict(loaded_settings, self.DEFAULT_SETTINGS)

    def load(self):
        """Load settings from file or create defaults with comprehensive validation."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)

                # Validate and merge with defaults
                self._settings = self._validate_and_merge_settings(loaded_settings)
                logger.info("Settings loaded and validated successfully")

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

                # Migrate PKI config from old location if needed
                self._migrate_pki_config()
            else:
                self._settings = self.DEFAULT_SETTINGS.copy()
                self.save()
                logger.info("Default settings created")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in settings file: {e}. Using defaults.")
            self._settings = self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
    
    def save(self):
        """
        Save all current settings to file.

        Ensures all settings in memory are written to disk, including:
        - UI settings (window opacity, position, size)
        - Interface settings (opacity percentage)
        - Font settings (AI response and user input fonts)
        - Resize settings (global and widget-specific)
        - App settings (state, log level, auto-start)
        - Tray settings (animations, tooltips)
        - PKI settings (certificates, validation)
        - AI model settings (model name, base_url, api_key)
        - Advanced settings (log location, SSL verification)

        All settings are validated against DEFAULT_SETTINGS structure.
        Sensitive values (API keys) remain encrypted with 'enc:' prefix.
        """
        try:
            # Ensure all default top-level keys exist (but don't overwrite existing values)
            for key in self.DEFAULT_SETTINGS.keys():
                if key not in self._settings:
                    logger.debug(f"Adding missing default key to settings before save: {key}")
                    self._settings[key] = self.DEFAULT_SETTINGS[key].copy() if isinstance(self.DEFAULT_SETTINGS[key], dict) else self.DEFAULT_SETTINGS[key]

            # Write to file with pretty formatting
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)

            logger.debug(f"Settings saved successfully to {self.settings_file}")
            logger.debug(f"Total top-level keys saved: {len(self._settings)}")

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
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
            self._notify_change(key_path)

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
                self._notify_change(key_path)
                
        except Exception as e:
            logger.error(f"Failed to delete setting '{key_path}': {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings (sensitive values remain encrypted)."""
        return self._settings.copy()

    def get_all_settings(self) -> Dict[str, Any]:
        """Alias for get_all() - returns all settings with encrypted sensitive values."""
        return self.get_all()

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