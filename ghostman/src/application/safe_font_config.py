"""
Safe Font Configuration System

Provides validated, mainstream font options that are guaranteed to work
without breaking HTML/CSS structure in Qt.
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class SafeFontConfig:
    """Manages safe, validated font configurations."""
    
    # 4 Mainstream fonts for AI responses and user input
    SAFE_TEXT_FONTS = [
        ("Arial", "Universal sans-serif font"),
        ("Times New Roman", "Classic serif font"),
        ("Calibri", "Modern clean font"),
        ("Segoe UI", "Windows system font")
    ]
    
    # 4 Mainstream monospace fonts for code
    SAFE_CODE_FONTS = [
        ("Consolas", "Modern monospace font"),
        ("Courier New", "Classic monospace font"),
        ("Lucida Console", "Clear monospace font"),
        ("Cascadia Code", "Modern coding font")
    ]
    
    # Safe font sizes that work well in Qt
    SAFE_FONT_SIZES = [8, 9, 10, 11, 12, 14]
    
    # Characters that can break HTML/CSS if in font names
    UNSAFE_CHARACTERS = ['<', '>', '"', "'", '&', ';', '\\', '/', '{', '}', '|', '`']
    
    @classmethod
    def get_safe_text_fonts(cls) -> List[Tuple[str, str]]:
        """Get list of safe text fonts with descriptions."""
        return cls.SAFE_TEXT_FONTS.copy()
    
    @classmethod
    def get_safe_code_fonts(cls) -> List[Tuple[str, str]]:
        """Get list of safe code fonts with descriptions."""
        return cls.SAFE_CODE_FONTS.copy()
    
    @classmethod
    def get_safe_font_sizes(cls) -> List[int]:
        """Get list of safe font sizes."""
        return cls.SAFE_FONT_SIZES.copy()
    
    @classmethod
    def validate_font_name(cls, font_name: str) -> Tuple[bool, str]:
        """
        Validate a font name for safety.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not font_name:
            return False, "Font name cannot be empty"
        
        # Check for unsafe characters
        for char in cls.UNSAFE_CHARACTERS:
            if char in font_name:
                return False, f"Font name contains unsafe character: {char}"
        
        # Check length
        if len(font_name) > 50:
            return False, "Font name too long (max 50 characters)"
        
        # Check if it's in our safe lists
        all_safe_fonts = [f[0] for f in cls.SAFE_TEXT_FONTS + cls.SAFE_CODE_FONTS]
        if font_name not in all_safe_fonts:
            logger.warning(f"Font '{font_name}' not in validated safe font list")
            # Still allow but with warning
        
        return True, ""
    
    @classmethod
    def validate_font_size(cls, size: int) -> Tuple[bool, str]:
        """
        Validate a font size for safety.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(size, (int, float)):
            return False, "Font size must be a number"
        
        if size < 6 or size > 24:
            return False, "Font size must be between 6 and 24"
        
        if size not in cls.SAFE_FONT_SIZES:
            logger.warning(f"Font size {size} not in recommended safe sizes")
            # Still allow but with warning
        
        return True, ""
    
    @classmethod
    def sanitize_font_config(cls, font_config: Dict) -> Dict:
        """
        Sanitize a font configuration to ensure it's safe.
        
        Args:
            font_config: Dictionary with 'family' and 'size' keys
            
        Returns:
            Sanitized font configuration
        """
        safe_config = font_config.copy()
        
        # Validate and sanitize font family
        family = safe_config.get('family', 'Arial')
        is_valid, error = cls.validate_font_name(family)
        if not is_valid:
            logger.error(f"Invalid font family '{family}': {error}. Using Arial.")
            safe_config['family'] = 'Arial'
        
        # Validate and sanitize font size
        size = safe_config.get('size', 10)
        is_valid, error = cls.validate_font_size(size)
        if not is_valid:
            logger.error(f"Invalid font size {size}: {error}. Using size 10.")
            safe_config['size'] = 10
        
        # Ensure size is integer
        safe_config['size'] = int(safe_config['size'])
        
        # Remove any potentially dangerous characters from the family name
        safe_family = safe_config['family']
        for char in cls.UNSAFE_CHARACTERS:
            safe_family = safe_family.replace(char, '')
        safe_config['family'] = safe_family.strip()
        
        return safe_config
    
    @classmethod
    def get_safe_css_string(cls, font_config: Dict) -> str:
        """
        Generate a safe CSS font string that won't break HTML structure.
        
        Args:
            font_config: Font configuration dictionary
            
        Returns:
            Safe CSS string for font styling
        """
        safe_config = cls.sanitize_font_config(font_config)
        
        # Escape the font family name for CSS
        family = safe_config['family'].replace("'", "\\'")
        size = safe_config['size']
        
        # Build safe CSS string with proper escaping
        css = f"font-family: '{family}', sans-serif; font-size: {size}pt"
        
        return css
    
    @classmethod
    def is_monospace_font(cls, font_name: str) -> bool:
        """Check if a font is a monospace/code font."""
        code_fonts = [f[0].lower() for f in cls.SAFE_CODE_FONTS]
        return font_name.lower() in code_fonts or 'mono' in font_name.lower() or 'console' in font_name.lower()
    
    @classmethod
    def get_fallback_font(cls, font_type: str) -> Dict:
        """
        Get a safe fallback font configuration.
        
        Args:
            font_type: 'code' or 'text'
            
        Returns:
            Safe fallback font configuration
        """
        if font_type == 'code':
            return {
                'family': 'Consolas',
                'size': 10,
                'weight': 'normal',
                'style': 'normal'
            }
        else:
            return {
                'family': 'Arial', 
                'size': 10,
                'weight': 'normal',
                'style': 'normal'
            }