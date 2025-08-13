"""
Font Configuration Service for Ghostman.

Manages font settings for AI responses and user input with separate configurations.
"""

import logging
from typing import Dict, Any
from PyQt6.QtGui import QFont, QFontDatabase
from ..infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.font_service")


class FontService:
    """Service to manage font configurations for different text types."""
    
    def __init__(self):
        """Initialize the font service."""
        self._font_cache = {}
        self._available_fonts = None
        
    def get_available_fonts(self) -> list:
        """
        Get list of available system fonts.
        
        Returns:
            List of font family names available on the system
        """
        if self._available_fonts is None:
            try:
                font_db = QFontDatabase()
                self._available_fonts = sorted(font_db.families())
                logger.debug(f"Loaded {len(self._available_fonts)} available fonts")
            except Exception as e:
                logger.warning(f"Failed to load system fonts: {e}")
                # Fallback to common fonts
                self._available_fonts = [
                    'Arial', 'Calibri', 'Consolas', 'Courier New', 'Georgia',
                    'Helvetica', 'Impact', 'Lucida Console', 'Segoe UI', 'Tahoma',
                    'Times New Roman', 'Trebuchet MS', 'Verdana'
                ]
        
        return self._available_fonts
    
    def get_font_config(self, font_type: str) -> Dict[str, Any]:
        """
        Get font configuration for a specific type.
        
        Args:
            font_type: 'ai_response' or 'user_input'
            
        Returns:
            Dictionary with font configuration
        """
        try:
            config = settings.get(f'fonts.{font_type}', {})
            
            # Ensure all required keys exist with defaults
            defaults = {
                'ai_response': {
                    'family': 'Segoe UI',
                    'size': 11,
                    'weight': 'normal',
                    'style': 'normal'
                },
                'user_input': {
                    'family': 'Consolas',
                    'size': 10,
                    'weight': 'normal',
                    'style': 'normal'
                }
            }
            
            default_config = defaults.get(font_type, defaults['ai_response'])
            
            # Merge with defaults
            for key, default_value in default_config.items():
                if key not in config:
                    config[key] = default_value
            
            logger.debug(f"Font config for {font_type}: {config}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to get font config for {font_type}: {e}")
            # Return safe defaults
            if font_type == 'user_input':
                return {'family': 'Consolas', 'size': 10, 'weight': 'normal', 'style': 'normal'}
            else:
                return {'family': 'Segoe UI', 'size': 11, 'weight': 'normal', 'style': 'normal'}
    
    def create_qfont(self, font_type: str) -> QFont:
        """
        Create a QFont object for the specified font type.
        
        Args:
            font_type: 'ai_response' or 'user_input'
            
        Returns:
            QFont object configured with the settings
        """
        # Check cache first
        cache_key = font_type
        if cache_key in self._font_cache:
            cached_config, cached_font = self._font_cache[cache_key]
            current_config = self.get_font_config(font_type)
            
            # Return cached font if config hasn't changed
            if cached_config == current_config:
                return QFont(cached_font)  # Return a copy
        
        try:
            config = self.get_font_config(font_type)
            
            # Create QFont
            font = QFont()
            font.setFamily(config['family'])
            font.setPointSize(config['size'])
            
            # Set weight
            if config['weight'] == 'bold':
                font.setWeight(QFont.Weight.Bold)
            else:
                font.setWeight(QFont.Weight.Normal)
            
            # Set style
            if config['style'] == 'italic':
                font.setItalic(True)
            else:
                font.setItalic(False)
            
            # Cache the font
            self._font_cache[cache_key] = (config.copy(), QFont(font))
            
            logger.debug(f"Created QFont for {font_type}: {config}")
            return font
            
        except Exception as e:
            logger.error(f"Failed to create QFont for {font_type}: {e}")
            # Return system default font
            return QFont()
    
    def update_font_config(self, font_type: str, **config_updates):
        """
        Update font configuration for a specific type.
        
        Args:
            font_type: 'ai_response' or 'user_input'
            **config_updates: Font configuration updates (family, size, weight, style)
        """
        try:
            current_config = self.get_font_config(font_type)
            
            # Update with new values
            for key, value in config_updates.items():
                if key in ['family', 'size', 'weight', 'style']:
                    current_config[key] = value
                else:
                    logger.warning(f"Unknown font config key: {key}")
            
            # Validate font family
            if 'family' in config_updates:
                available_fonts = self.get_available_fonts()
                if current_config['family'] not in available_fonts:
                    logger.warning(f"Font family '{current_config['family']}' not available, keeping current")
                    current_config['family'] = self.get_font_config(font_type)['family']
            
            # Validate font size
            if 'size' in config_updates:
                size = current_config['size']
                if not isinstance(size, int) or size < 6 or size > 72:
                    logger.warning(f"Invalid font size {size}, using default")
                    current_config['size'] = 11 if font_type == 'ai_response' else 10
            
            # Save to settings
            settings.set(f'fonts.{font_type}', current_config)
            settings.save()
            
            # Clear cache to force recreation
            if font_type in self._font_cache:
                del self._font_cache[font_type]
            
            logger.info(f"Updated font config for {font_type}: {config_updates}")
            
        except Exception as e:
            logger.error(f"Failed to update font config for {font_type}: {e}")
    
    def get_css_font_style(self, font_type: str) -> str:
        """
        Get CSS font style string for the specified font type.
        
        Args:
            font_type: 'ai_response' or 'user_input'
            
        Returns:
            CSS font style string
        """
        try:
            config = self.get_font_config(font_type)
            
            css_parts = []
            css_parts.append(f"font-family: '{config['family']}'")
            css_parts.append(f"font-size: {config['size']}pt")
            
            if config['weight'] == 'bold':
                css_parts.append("font-weight: bold")
            
            if config['style'] == 'italic':
                css_parts.append("font-style: italic")
            
            css_style = "; ".join(css_parts)
            logger.debug(f"Generated CSS for {font_type}: {css_style}")
            return css_style
            
        except Exception as e:
            logger.error(f"Failed to generate CSS for {font_type}: {e}")
            return "font-family: 'Segoe UI'; font-size: 11pt"
    
    def clear_cache(self):
        """Clear the font cache to force recreation of fonts."""
        self._font_cache.clear()
        logger.debug("Font cache cleared")


# Global instance
font_service = FontService()