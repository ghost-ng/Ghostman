"""
Theme Manager for Ghostman Application.

Provides centralized theme management with signal-based updates,
theme persistence, and live theme switching capabilities.
"""

import logging
import json
import os
from typing import Dict, Optional, List, Any
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
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
        self._current_theme_name: str = "default"
        self._preset_themes: Dict[str, ColorSystem] = {}
        self._custom_themes: Dict[str, ColorSystem] = {}
        self._theme_history: List[ColorSystem] = []
        self._max_history_size: int = 20
        
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
        """Load built-in preset themes."""
        # Import preset themes (will be created next)
        try:
            from .preset_themes import get_preset_themes
            self._preset_themes = get_preset_themes()
            logger.info(f"Loaded {len(self._preset_themes)} preset themes")
        except ImportError:
            logger.warning("Preset themes not available, using openai_like theme only")
            self._preset_themes = {"openai_like": ColorSystem()}
    
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
                
                # Store additional metadata if available
                if hasattr(color_system, '_metadata'):
                    color_system._metadata = {
                        'display_name': theme_data.get('display_name', theme_name),
                        'description': theme_data.get('description', ''),
                        'author': theme_data.get('author', 'Unknown'),
                        'version': theme_data.get('version', '1.0.0')
                    }
                
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
            theme_name = settings.get('ui.theme', 'openai_like')
            if self.has_theme(theme_name):
                self.set_theme(theme_name)
            else:
                logger.warning(f"Saved theme '{theme_name}' not found, using openai_like")
                self.set_theme('openai_like')
        except Exception as e:
            logger.error(f"Failed to load current theme: {e}")
            self.set_theme('openai_like')
    
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
    
    def set_theme(self, name: str) -> bool:
        """
        Set the current theme by name.
        
        Args:
            name: Theme name to activate
            
        Returns:
            True if theme was set successfully, False otherwise
        """
        theme = self.get_theme(name)
        if theme is None:
            logger.error(f"Theme '{name}' not found")
            return False
        
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
        
        # Save to settings
        try:
            settings.set('ui.theme', name)
            settings.save()
        except Exception as e:
            logger.error(f"Failed to save theme setting: {e}")
        
        # Emit signals
        self.theme_changed.emit(theme)
        self.theme_loaded.emit(name)
        
        logger.info(f"Theme changed to: {name}")
        return True
    
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
        
        # Emit signals
        self.theme_changed.emit(color_system)
        
        logger.info(f"Custom theme applied: {self._current_theme_name}")
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
            
            # If this was the current theme, switch to openai_like
            if self._current_theme_name == name:
                self.set_theme('openai_like')
            
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