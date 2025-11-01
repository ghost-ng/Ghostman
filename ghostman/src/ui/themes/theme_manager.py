"""
Theme Manager for Ghostman Application.

Provides centralized theme management with signal-based updates,
theme persistence, and live theme switching capabilities.
"""

import logging
import json
import os
import weakref
from typing import Dict, Optional, List, Any, Set
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

from .color_system import ColorSystem, ColorUtils
from ...infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.theme_manager")


class ThemeManager(QObject):
    """
    Centralized theme management system.
    
    Features:
    - Signal-based theme updates for real-time UI changes
    - Theme persistence and loading
    - Preset theme management
    - Custom theme support
    - Theme validation and accessibility checking
    - Import/export functionality
    """
    
    # Signals
    theme_changed = pyqtSignal(ColorSystem)  # Emitted when theme changes
    theme_loaded = pyqtSignal(str)           # Emitted when theme is loaded (theme name)
    theme_saved = pyqtSignal(str)            # Emitted when theme is saved (theme name)
    theme_deleted = pyqtSignal(str)          # Emitted when theme is deleted (theme name)
    theme_validation_failed = pyqtSignal(list)  # Emitted when theme validation fails
    
    def __init__(self):
        super().__init__()
        self._current_theme: Optional[ColorSystem] = None
        self._current_theme_name: str = "cyber"
        self._preset_themes: Dict[str, ColorSystem] = {}
        self._custom_themes: Dict[str, ColorSystem] = {}
        self._theme_history: List[ColorSystem] = []
        self._max_history_size: int = 20
        
        # Widget registry for comprehensive theme updates
        self._registered_widgets: Set[weakref.ReferenceType] = set()
        self._widget_update_methods: Dict[weakref.ReferenceType, str] = {}
        
        # Performance optimization: Cache theme color dictionary
        self._theme_color_dict_cache: Optional[Dict[str, str]] = None
        
        # Theme switch debouncing to prevent notification spam
        self._theme_switch_debounce_timer = None
        self._is_switching_theme = False
        self._pending_theme_name = None  # Track the most recent theme switch request
        
        # Initialize theme directories
        self._init_theme_directories()
        
        # Load preset themes
        self._load_preset_themes()
        
        # Load custom themes
        self._load_custom_themes()
        
        # Load current theme from settings
        self._load_current_theme()
        
        logger.info("ThemeManager initialized")
    
    def _init_theme_directories(self):
        """Initialize theme storage directories."""
        try:
            from ...utils.config_paths import get_user_data_dir
            self._themes_dir = Path(get_user_data_dir()) / "themes"
        except ImportError:
            # Fallback to a local themes directory
            self._themes_dir = Path.cwd() / "themes"
        
        self._themes_dir.mkdir(exist_ok=True)
        
        logger.debug(f"Theme directories initialized: {self._themes_dir}")
    
    def _load_preset_themes(self):
        """Load built-in preset themes from JSON files."""
        self._preset_themes = {}
        
        # Get the built-in themes directory (relative to this file)
        builtin_themes_dir = Path(__file__).parent / "json"
        
        if not builtin_themes_dir.exists():
            logger.warning(f"Built-in themes directory not found: {builtin_themes_dir}")
            # Fall back to a default theme
            self._preset_themes = {"cyber": ColorSystem()}
            return
        
        # Load all JSON theme files from the built-in directory
        for theme_file in builtin_themes_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                
                # Use 'name' field from JSON if available, otherwise use filename
                theme_name = theme_data.get('name', theme_file.stem)
                
                # Create ColorSystem from colors data
                color_system = ColorSystem.from_dict(theme_data.get('colors', {}))
                
                # Store additional metadata including theme mode
                if not hasattr(color_system, '_metadata'):
                    color_system._metadata = {}
                color_system._metadata.update({
                    'display_name': theme_data.get('display_name', theme_name),
                    'description': theme_data.get('description', ''),
                    'author': theme_data.get('author', 'Unknown'),
                    'version': theme_data.get('version', '1.0.0'),
                    'mode': theme_data.get('mode', 'light')  # Store theme mode
                })
                
                # Add to preset themes
                self._preset_themes[theme_name] = color_system
                logger.debug(f"Loaded built-in theme: {theme_name} (mode: {theme_data.get('mode', 'light')})")
                    
            except Exception as e:
                logger.error(f"Failed to load built-in theme {theme_file}: {e}")
        
        logger.info(f"Loaded {len(self._preset_themes)} preset themes")
    
    def _load_custom_themes(self):
        """Load custom themes from disk (themes folder)."""
        self._custom_themes = {}
        
        if not self._themes_dir.exists():
            return
            
        for theme_file in self._themes_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                
                # Use 'name' field from JSON if available, otherwise use filename
                theme_name = theme_data.get('name', theme_file.stem)
                
                # Create ColorSystem from colors data
                color_system = ColorSystem.from_dict(theme_data.get('colors', {}))
                
                # Store additional metadata including theme mode
                if not hasattr(color_system, '_metadata'):
                    color_system._metadata = {}
                color_system._metadata.update({
                    'display_name': theme_data.get('display_name', theme_name),
                    'description': theme_data.get('description', ''),
                    'author': theme_data.get('author', 'Unknown'),
                    'version': theme_data.get('version', '1.0.0'),
                    'mode': theme_data.get('mode', 'light')  # Store theme mode
                })
                
                # Validate theme (but allow loading with warnings for custom themes)
                is_valid, issues = color_system.validate()
                self._custom_themes[theme_name] = color_system
                
                if is_valid:
                    logger.debug(f"Loaded custom theme: {theme_name} from {theme_file}")
                else:
                    logger.warning(f"Loaded custom theme with accessibility warnings {theme_name}: {issues}")
                    logger.info(f"Custom theme '{theme_name}' loaded despite validation warnings")
                    
            except Exception as e:
                logger.error(f"Failed to load custom theme {theme_file}: {e}")
        
        logger.info(f"Loaded {len(self._custom_themes)} custom themes")
    
    def _load_current_theme(self):
        """Load the current theme from settings."""
        try:
            theme_name = settings.get('ui.theme', 'cyber')
            if self.has_theme(theme_name):
                self.set_theme(theme_name)
            else:
                logger.warning(f"Saved theme '{theme_name}' not found, using cyber")
                self.set_theme('cyber')
        except Exception as e:
            logger.error(f"Failed to load current theme: {e}")
            self.set_theme('cyber')
    
    @property
    def current_theme(self) -> ColorSystem:
        """Get the current active theme."""
        if self._current_theme is None:
            self._current_theme = ColorSystem()  # Default theme
        return self._current_theme
    
    @property
    def current_theme_name(self) -> str:
        """Get the current theme name."""
        return self._current_theme_name
    
    def get_available_themes(self) -> List[str]:
        """Get list of all available theme names."""
        themes = list(self._preset_themes.keys()) + list(self._custom_themes.keys())
        return sorted(themes)
    
    def get_preset_themes(self) -> List[str]:
        """Get list of preset theme names."""
        return sorted(self._preset_themes.keys())
    
    def get_custom_themes(self) -> List[str]:
        """Get list of custom theme names."""
        return sorted(self._custom_themes.keys())
    
    def has_theme(self, name: str) -> bool:
        """Check if a theme exists."""
        return name in self._preset_themes or name in self._custom_themes
    
    def get_theme(self, name: str) -> Optional[ColorSystem]:
        """Get a theme by name."""
        if name in self._preset_themes:
            return self._preset_themes[name]
        elif name in self._custom_themes:
            return self._custom_themes[name]
        return None
    
    def register_widget(self, widget, update_method: str = "_on_theme_changed") -> bool:
        """
        Register a widget to receive theme updates.
        
        Args:
            widget: The widget to register
            update_method: Name of the method to call on theme change (default: "_on_theme_changed")
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            widget_ref = weakref.ref(widget, self._cleanup_widget_reference)
            self._registered_widgets.add(widget_ref)
            self._widget_update_methods[widget_ref] = update_method
            
            # Apply current theme immediately if available
            if self._current_theme is not None:
                self._apply_theme_to_widget(widget, update_method)
            
            logger.debug(f"Registered widget {widget.__class__.__name__} for theme updates")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register widget for theme updates: {e}")
            return False
    
    def unregister_widget(self, widget) -> bool:
        """
        Unregister a widget from theme updates.
        
        Args:
            widget: The widget to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            # Find and remove widget reference
            for widget_ref in list(self._registered_widgets):
                if widget_ref() is widget:
                    self._registered_widgets.discard(widget_ref)
                    self._widget_update_methods.pop(widget_ref, None)
                    logger.debug(f"Unregistered widget {widget.__class__.__name__} from theme updates")
                    return True
            
            logger.debug(f"Widget {widget.__class__.__name__} was not registered")
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister widget from theme updates: {e}")
            return False
    
    def _cleanup_widget_reference(self, widget_ref):
        """Clean up widget reference when widget is destroyed."""
        self._registered_widgets.discard(widget_ref)
        self._widget_update_methods.pop(widget_ref, None)
    
    def _apply_theme_to_widget(self, widget, update_method: str):
        """Apply current theme to a specific widget."""
        try:
            if hasattr(widget, update_method):
                method = getattr(widget, update_method)
                if callable(method):
                    if update_method == "_on_theme_changed":
                        # Standard theme change handler expects ColorSystem
                        method(self._current_theme)
                    elif update_method == "set_theme_colors":
                        # Widget expects color dictionary - use cached version for performance
                        color_dict = self._get_cached_theme_color_dict()
                        method(color_dict)
                    elif update_method == "apply_theme":
                        # Widget expects ColorSystem
                        method(self._current_theme)
                    else:
                        # Generic call without parameters
                        method()
                    logger.debug(f"Applied theme to {widget.__class__.__name__} using {update_method}")
                else:
                    logger.warning(f"Widget {widget.__class__.__name__} method {update_method} is not callable")
            else:
                logger.warning(f"Widget {widget.__class__.__name__} missing method {update_method}")
                
        except Exception as e:
            logger.error(f"Failed to apply theme to {widget.__class__.__name__}: {e}")
    
    def _get_cached_theme_color_dict(self) -> Dict[str, str]:
        """Get cached theme color dictionary for performance optimization."""
        if self._theme_color_dict_cache is None:
            # Create and cache the color dictionary with legacy mappings
            color_dict = self._current_theme.to_dict() if self._current_theme else {}
            
            # Add legacy key mappings for backward compatibility
            if self._current_theme:
                legacy_mappings = {
                    'bg_primary': color_dict.get('background_primary'),
                    'bg_secondary': color_dict.get('background_secondary'), 
                    'bg_tertiary': color_dict.get('background_tertiary'),
                    'border': color_dict.get('border_subtle')
                }
                # Add legacy keys without overwriting existing ones
                for key, value in legacy_mappings.items():
                    if key not in color_dict and value is not None:
                        color_dict[key] = value
            
            self._theme_color_dict_cache = color_dict
            logger.debug(f"Created cached theme color dictionary with {len(color_dict)} keys")
        
        return self._theme_color_dict_cache
    
    def _apply_theme_to_all_widgets(self):
        """Apply current theme to all registered widgets."""
        dead_refs = set()
        
        # Create a copy to avoid RuntimeError if widgets register during iteration
        widgets_to_update = list(self._registered_widgets)
        
        for widget_ref in widgets_to_update:
            widget = widget_ref()
            if widget is None:
                # Widget has been garbage collected
                dead_refs.add(widget_ref)
                continue
                
            update_method = self._widget_update_methods.get(widget_ref, "_on_theme_changed")
            self._apply_theme_to_widget(widget, update_method)
        
        # Clean up dead references
        for dead_ref in dead_refs:
            self._registered_widgets.discard(dead_ref)
            self._widget_update_methods.pop(dead_ref, None)
        
        if dead_refs:
            logger.debug(f"Cleaned up {len(dead_refs)} dead widget references")
    
    def set_theme(self, name: str) -> bool:
        """
        Set the current theme by name.
        
        Args:
            name: Theme name to activate
            
        Returns:
            True if theme was set successfully, False otherwise
        """
        # Debounce rapid theme changes to prevent notification spam
        if self._is_switching_theme:
            # Check if debounce timer is still running
            if (self._theme_switch_debounce_timer is not None and 
                self._theme_switch_debounce_timer.isActive()):
                logger.debug(f"Theme switch debounced: {name} (already switching)")
                return False
            else:
                # Timer finished but flag wasn't reset - reset it now
                logger.debug(f"Resetting stuck debounce flag for theme: {name}")
                self._is_switching_theme = False
        
        theme = self.get_theme(name)
        if theme is None:
            logger.error(f"Theme '{name}' not found")
            return False
        
        # Set debounce flag to prevent rapid switching
        self._is_switching_theme = True
        
        # Set global flag to prevent dialog/window creation during theme switching
        app = QApplication.instance()
        if app:
            app.setProperty("theme_switching", True)
        
        # Clear any existing debounce timer
        if self._theme_switch_debounce_timer:
            self._theme_switch_debounce_timer.stop()
            self._theme_switch_debounce_timer = None
        
        # Validate theme
        is_valid, issues = theme.validate()
        if not is_valid:
            logger.warning(f"Theme '{name}' has validation issues: {issues}")
            self.theme_validation_failed.emit(issues)
            # Continue anyway, but warn user
        
        # Add current theme to history
        if self._current_theme is not None:
            self._add_to_history(self._current_theme)
        
        # Set new theme
        self._current_theme = theme
        self._current_theme_name = name
        
        # Invalidate cached color dictionary for performance optimization
        self._theme_color_dict_cache = None
        
        # Save to settings
        try:
            settings.set('ui.theme', name)
            settings.save()
        except Exception as e:
            logger.error(f"Failed to save theme setting: {e}")
        
        # Temporarily reduce logging verbosity during theme switching
        theme_loggers = [
            logging.getLogger("ghostman.theme_manager"),
            logging.getLogger("ghostman.repl_widget"),
            logging.getLogger("ghostman.embedded_code_widget"),
            logging.getLogger("ghostman.style_registry"),
            logging.getLogger("ghostman.style_templates"),
        ]
        
        # Store original levels and set to WARNING to reduce spam
        original_levels = []
        for theme_logger in theme_loggers:
            original_levels.append(theme_logger.level)
            if theme_logger.level < logging.WARNING:
                theme_logger.setLevel(logging.WARNING)
        
        try:
            # Apply theme to all registered widgets immediately
            self._apply_theme_to_all_widgets()
        finally:
            # Restore original logging levels
            for theme_logger, original_level in zip(theme_loggers, original_levels):
                theme_logger.setLevel(original_level)
        
        # Emit signals
        self.theme_changed.emit(theme)
        self.theme_loaded.emit(name)
        
        logger.info(f"Theme changed to: {name} - applied to {len(self._registered_widgets)} registered widgets")
        
        # Set up debounce timer to reset flag after theme switching is complete
        self._theme_switch_debounce_timer = QTimer()
        self._theme_switch_debounce_timer.setSingleShot(True)
        self._theme_switch_debounce_timer.timeout.connect(self._reset_theme_switching_flag)
        self._theme_switch_debounce_timer.start(200)  # 200ms debounce for more responsive switching
        
        return True
    
    def _reset_theme_switching_flag(self):
        """Reset the theme switching flag to allow new theme changes."""
        self._is_switching_theme = False
        
        # Clear global flag to allow dialog/window creation again
        app = QApplication.instance()
        if app:
            app.setProperty("theme_switching", False)
        
        logger.debug("Theme switching debounce flag reset")
    
    def set_custom_theme(self, color_system: ColorSystem, name: Optional[str] = None) -> bool:
        """
        Set a custom theme from a ColorSystem object.
        
        Args:
            color_system: The color system to apply
            name: Optional name for the theme (for saving purposes)
            
        Returns:
            True if theme was set successfully, False otherwise
        """
        # Validate theme
        is_valid, issues = color_system.validate()
        if not is_valid:
            logger.warning(f"Custom theme has validation issues: {issues}")
            self.theme_validation_failed.emit(issues)
            # Continue anyway, but warn user
        
        # Add current theme to history
        if self._current_theme is not None:
            self._add_to_history(self._current_theme)
        
        # Set new theme
        self._current_theme = color_system
        
        if name:
            self._current_theme_name = name
        else:
            self._current_theme_name = "custom"
            
        # Invalidate cached color dictionary for performance optimization
        self._theme_color_dict_cache = None
        
        # Temporarily reduce logging verbosity during theme switching
        theme_loggers = [
            logging.getLogger("ghostman.theme_manager"),
            logging.getLogger("ghostman.repl_widget"),
            logging.getLogger("ghostman.embedded_code_widget"),
            logging.getLogger("ghostman.style_registry"),
            logging.getLogger("ghostman.style_templates"),
        ]
        
        # Store original levels and set to WARNING to reduce spam
        original_levels = []
        for theme_logger in theme_loggers:
            original_levels.append(theme_logger.level)
            if theme_logger.level < logging.WARNING:
                theme_logger.setLevel(logging.WARNING)
        
        try:
            # Apply theme to all registered widgets immediately
            self._apply_theme_to_all_widgets()
        finally:
            # Restore original logging levels
            for theme_logger, original_level in zip(theme_loggers, original_levels):
                theme_logger.setLevel(original_level)
        
        # Emit signals
        self.theme_changed.emit(color_system)
        
        logger.info(f"Custom theme applied: {self._current_theme_name} - applied to {len(self._registered_widgets)} registered widgets")
        return True
    
    def save_custom_theme(self, name: str, color_system: Optional[ColorSystem] = None) -> bool:
        """
        Save a custom theme to disk.
        
        Args:
            name: Name for the custom theme
            color_system: Color system to save (uses current if None)
            
        Returns:
            True if theme was saved successfully, False otherwise
        """
        if color_system is None:
            color_system = self.current_theme
        
        # Validate theme
        is_valid, issues = color_system.validate()
        if not is_valid:
            logger.error(f"Cannot save invalid theme '{name}': {issues}")
            self.theme_validation_failed.emit(issues)
            return False
        
        # Don't allow overwriting preset themes
        if name in self._preset_themes:
            logger.error(f"Cannot overwrite preset theme '{name}'")
            return False
        
        try:
            theme_data = {
                'name': name,
                'created_at': str(datetime.now()),
                'colors': color_system.to_dict()
            }
            
            theme_file = self._themes_dir / f"{name}.json"
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2)
            
            # Add to custom themes
            self._custom_themes[name] = color_system
            
            # Emit signal
            self.theme_saved.emit(name)
            
            logger.info(f"Custom theme saved: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save custom theme '{name}': {e}")
            return False
    
    def delete_custom_theme(self, name: str) -> bool:
        """
        Delete a custom theme.
        
        Args:
            name: Name of the custom theme to delete
            
        Returns:
            True if theme was deleted successfully, False otherwise
        """
        if name in self._preset_themes:
            logger.error(f"Cannot delete preset theme '{name}'")
            return False
        
        if name not in self._custom_themes:
            logger.error(f"Custom theme '{name}' not found")
            return False
        
        try:
            # Remove from memory
            del self._custom_themes[name]
            
            # Remove file
            theme_file = self._themes_dir / f"{name}.json"
            if theme_file.exists():
                theme_file.unlink()
            
            # If this was the current theme, switch to cyber
            if self._current_theme_name == name:
                self.set_theme('cyber')
            
            # Emit signal
            self.theme_deleted.emit(name)
            
            logger.info(f"Custom theme deleted: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete custom theme '{name}': {e}")
            return False
    
    def export_theme(self, name: str, file_path: str) -> bool:
        """
        Export a theme to a file.
        
        Args:
            name: Name of the theme to export
            file_path: Path where to save the exported theme
            
        Returns:
            True if theme was exported successfully, False otherwise
        """
        theme = self.get_theme(name)
        if theme is None:
            logger.error(f"Theme '{name}' not found for export")
            return False
        
        try:
            export_data = {
                'name': name,
                'exported_at': str(datetime.now()),
                'version': '1.0',
                'colors': theme.to_dict()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Theme '{name}' exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export theme '{name}': {e}")
            return False
    
    def import_theme(self, file_path: str, name: Optional[str] = None) -> bool:
        """
        Import a theme from a file.
        
        Args:
            file_path: Path to the theme file to import
            name: Optional name for the imported theme (uses file name if None)
            
        Returns:
            True if theme was imported successfully, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # Extract theme name
            if name is None:
                name = theme_data.get('name', Path(file_path).stem)
            
            # Create color system
            colors = theme_data.get('colors', {})
            color_system = ColorSystem.from_dict(colors)
            
            # Validate theme
            is_valid, issues = color_system.validate()
            if not is_valid:
                logger.error(f"Cannot import invalid theme '{name}': {issues}")
                self.theme_validation_failed.emit(issues)
                return False
            
            # Save as custom theme
            return self.save_custom_theme(name, color_system)
            
        except Exception as e:
            logger.error(f"Failed to import theme from '{file_path}': {e}")
            return False
    
    def undo_theme_change(self) -> bool:
        """
        Undo the last theme change.
        
        Returns:
            True if undo was successful, False otherwise
        """
        if not self._theme_history:
            logger.info("No theme history available for undo")
            return False
        
        # Get previous theme
        previous_theme = self._theme_history.pop()
        
        # Apply previous theme without adding to history
        self._current_theme = previous_theme
        self._current_theme_name = "restored"
        
        # Emit signal
        self.theme_changed.emit(previous_theme)
        
        logger.info("Theme change undone")
        return True
    
    def _add_to_history(self, theme: ColorSystem):
        """Add a theme to the history stack."""
        self._theme_history.append(theme)
        
        # Limit history size
        while len(self._theme_history) > self._max_history_size:
            self._theme_history.pop(0)
    
    def get_color(self, name: str) -> str:
        """Get a color from the current theme."""
        return self.current_theme.get_color(name)
    
    @property
    def current_theme_mode(self) -> str:
        """
        Get the current theme's mode (light or dark).
        
        Returns:
            'light' or 'dark' based on the current theme's mode property.
            Defaults to 'light' if mode is not specified.
        """
        if self._current_theme and hasattr(self._current_theme, '_metadata'):
            return self._current_theme._metadata.get('mode', 'light')
        return 'light'
    
    def get_theme_mode(self, theme_name: str) -> str:
        """
        Get the mode of a specific theme.
        
        Args:
            theme_name: Name of the theme to check
            
        Returns:
            'light' or 'dark' based on the theme's mode property.
            Defaults to 'light' if mode is not specified or theme not found.
        """
        theme = self.get_theme(theme_name)
        if theme and hasattr(theme, '_metadata'):
            return theme._metadata.get('mode', 'light')
        return 'light'
    
    def get_icon_suffix_for_theme(self, theme_name: Optional[str] = None) -> str:
        """
        Get the appropriate icon suffix for a theme.
        
        Args:
            theme_name: Name of the theme to check (uses current theme if None)
            
        Returns:
            '_lite' for dark themes (light icons on dark backgrounds)
            '_dark' for light themes (dark icons on light backgrounds)
        """
        if theme_name is None:
            theme_mode = self.current_theme_mode
        else:
            theme_mode = self.get_theme_mode(theme_name)
        
        # Use light icons for dark themes, dark icons for light themes
        return '_lite' if theme_mode == 'dark' else '_dark'
    
    @property 
    def current_icon_suffix(self) -> str:
        """Get the appropriate icon suffix for the current theme."""
        return self.get_icon_suffix_for_theme()
    
    def apply_theme_to_widget(self, widget, style_template: str = None):
        """
        Apply current theme to a widget using style templates.
        
        Args:
            widget: The widget to apply the theme to
            style_template: Optional style template name
        """
        if style_template:
            try:
                from .style_templates import StyleTemplates
                style = StyleTemplates.get_style(style_template, self.current_theme)
                widget.setStyleSheet(style)
            except ImportError:
                logger.warning("Style templates not available")


# Global theme manager instance
theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return theme_manager

# Performance-optimized theme color helpers
# ========================================

# Cache for theme-system availability check (performance optimization)  
_theme_system_available_cache: Optional[bool] = None

# Default fallback colors optimized for both light and dark themes
_DEFAULT_FALLBACK_COLORS = {
    'text_primary': '#ecf0f1',      # Light text - works on dark backgrounds  
    'text_secondary': '#bdc3c7',    # Secondary light text
    'text_tertiary': '#95a5a6',     # Tertiary light text
    'background_primary': '#2c3e50', # Dark background
    'background_secondary': '#34495e', # Slightly lighter dark background  
    'primary': '#3498db',           # Blue accent
    'secondary': '#e74c3c',         # Red accent
    'status_success': '#27ae60',    # Green
    'status_warning': '#f39c12',    # Orange
    'status_error': '#e74c3c',      # Red
    'status_info': '#3498db',       # Blue
}


def get_theme_primary_color(theme_manager_instance: Optional[ThemeManager] = None) -> str:
    """Get the theme primary text color with performance optimization and fallback."""
    global _theme_system_available_cache
    
    # Fast path: Check cached availability first
    if _theme_system_available_cache is False:
        return _DEFAULT_FALLBACK_COLORS['text_primary']
    
    # Use provided theme manager or get global instance
    tm = theme_manager_instance or theme_manager
    
    # Check if theme manager and theme system are available
    if tm and hasattr(tm, 'current_theme') and tm.current_theme:
        try:
            # Use cached color dictionary for optimal performance
            cached_colors = tm._get_cached_theme_color_dict()
            if cached_colors and 'text_primary' in cached_colors:
                # Cache that theme system is available
                _theme_system_available_cache = True
                return cached_colors['text_primary']
            
            # Fallback to direct property access if cache is not available
            return tm.current_theme.text_primary
        except (AttributeError, KeyError):
            # Cache that theme system is not working properly
            _theme_system_available_cache = False
            pass
    
    # Theme system unavailable - use fallback
    _theme_system_available_cache = False
    return _DEFAULT_FALLBACK_COLORS['text_primary']






def get_theme_color(color_name: str, 
                   theme_manager_instance: Optional[ThemeManager] = None, 
                   fallback: Optional[str] = None) -> str:
    """
    Get any color from the current theme with performance optimization and fallback.
    
    Args:
        color_name: Name of the color to retrieve (e.g., 'text_primary', 'background_secondary')
        theme_manager_instance: Optional theme manager instance for better performance
        fallback: Custom fallback color. If None, uses predefined fallback for the color name.
    
    Returns:
        str: Hex color code for the requested color, or fallback if unavailable.
    """
    global _theme_system_available_cache
    
    # Determine fallback color
    if fallback is None:
        fallback = _DEFAULT_FALLBACK_COLORS.get(color_name, '#ecf0f1')
    
    # Fast path: Check cached availability first
    if _theme_system_available_cache is False:
        return fallback
    
    # Use provided theme manager or get global instance
    tm = theme_manager_instance or theme_manager
    
    # Check if theme manager and theme system are available
    if tm and hasattr(tm, 'current_theme') and tm.current_theme:
        try:
            # Use cached color dictionary for optimal performance
            cached_colors = tm._get_cached_theme_color_dict()
            if cached_colors and color_name in cached_colors:
                # Cache that theme system is available
                _theme_system_available_cache = True
                return cached_colors[color_name]
            
            # Fallback to direct property access if cache is not available
            if hasattr(tm.current_theme, color_name):
                color_value = getattr(tm.current_theme, color_name)
                _theme_system_available_cache = True
                return color_value
        except (AttributeError, KeyError):
            # Cache that theme system is not working properly
            _theme_system_available_cache = False
            pass
    
    # Theme system unavailable - use fallback
    _theme_system_available_cache = False
    return fallback

def get_theme_colors_dict(theme_manager_instance: Optional[ThemeManager] = None) -> Dict[str, str]:
    """Get a complete dictionary of theme colors with fallbacks."""
    global _theme_system_available_cache
    
    # Fast path: Check cached availability first
    if _theme_system_available_cache is False:
        return _DEFAULT_FALLBACK_COLORS.copy()
    
    # Use provided theme manager or get global instance
    tm = theme_manager_instance or theme_manager
    
    # Check if theme manager and theme system are available
    if tm and hasattr(tm, 'current_theme') and tm.current_theme:
        try:
            # Use cached color dictionary for optimal performance
            cached_colors = tm._get_cached_theme_color_dict()
            if cached_colors:
                # Cache that theme system is available
                _theme_system_available_cache = True
                return cached_colors
            
            # Fallback to direct theme object access
            theme_dict = tm.current_theme.to_dict()
            _theme_system_available_cache = True
            return theme_dict
        except (AttributeError, KeyError):
            # Cache that theme system is not working properly
            _theme_system_available_cache = False
            pass
    
    # Theme system unavailable - use fallback
    _theme_system_available_cache = False
    return _DEFAULT_FALLBACK_COLORS.copy()


def get_theme_text_color(theme_manager_instance: Optional[ThemeManager] = None) -> str:
    """Alias for get_theme_primary_color for backwards compatibility."""
    return get_theme_primary_color(theme_manager_instance)


def get_theme_background_color(theme_manager_instance: Optional[ThemeManager] = None) -> str:
    """Get the theme primary background color with fallback."""
    return get_theme_color('background_primary', theme_manager_instance)


def get_theme_accent_color(theme_manager_instance: Optional[ThemeManager] = None) -> str:
    """Get the theme primary accent color with fallback."""
    return get_theme_color('primary', theme_manager_instance)


# Export for backwards compatibility
THEME_SYSTEM_AVAILABLE = True
