"""
Universal syntax highlighting color adapter for all themes.
Automatically adjusts colors for optimal contrast and theme compatibility.
"""

from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger('specter.universal_syntax_colors')


class UniversalSyntaxColorAdapter:
    """
    Provides theme-aware syntax highlighting colors that work across all themes.
    Automatically detects light/dark themes and provides appropriate colors.
    """
    
    def __init__(self):
        # Define color palettes for different theme types
        self.dark_theme_colors = {
            'keyword': '#569cd6',       # Blue - VS Code inspired
            'string': '#ce9178',        # Orange/brown - VS Code inspired  
            'comment': '#6a9955',       # Green - VS Code inspired
            'function': '#dcdcaa',      # Yellow - VS Code inspired
            'number': '#b5cea8',        # Light green - VS Code inspired
            'builtin': '#4ec9b0',       # Cyan - VS Code inspired
            'operator': '#d4d4d4',      # Light gray
            'class': '#4ec9b0',         # Cyan
        }
        
        self.light_theme_colors = {
            'keyword': '#0000ff',       # Classic blue
            'string': '#a31515',        # Red/brown
            'comment': '#008000',       # Green  
            'function': '#795e26',      # Brown/yellow
            'number': '#098658',        # Dark green
            'builtin': '#267f99',       # Dark cyan
            'operator': '#000000',      # Black
            'class': '#267f99',         # Dark cyan
        }
        
    def get_syntax_colors(self, theme_colors: Dict[str, str]) -> Dict[str, str]:
        """
        Get appropriate syntax colors for the given theme.
        
        Args:
            theme_colors: Current theme color dictionary
            
        Returns:
            Dictionary of syntax highlighting colors optimized for the theme
        """
        try:
            # Detect if theme is light or dark
            is_dark = self._is_dark_theme(theme_colors)
            
            # Get base colors for theme type
            if is_dark:
                base_colors = self.dark_theme_colors.copy()
            else:
                base_colors = self.light_theme_colors.copy()
            
            # Enhance colors with theme-specific adjustments
            enhanced_colors = self._enhance_with_theme_colors(base_colors, theme_colors, is_dark)
            
            # Validate contrast ratios
            validated_colors = self._validate_contrast(enhanced_colors, theme_colors)
            
            logger.debug(f"Generated syntax colors for {'dark' if is_dark else 'light'} theme")
            return validated_colors
            
        except Exception as e:
            logger.warning(f"Failed to generate syntax colors: {e}")
            # Return safe fallback colors
            return self._get_fallback_colors(theme_colors)
    
    def _is_dark_theme(self, theme_colors: Dict[str, str]) -> bool:
        """
        Determine if the theme is dark or light based on background color.
        
        Args:
            theme_colors: Theme color dictionary
            
        Returns:
            True if theme is dark, False if light
        """
        try:
            # Get background color
            bg_color = theme_colors.get('bg_primary', '#000000')
            
            # Handle non-hex colors (rgba, etc.) by checking for common patterns
            if not bg_color.startswith('#'):
                # Look for common dark theme indicators
                if any(indicator in bg_color.lower() for indicator in ['black', 'dark', 'night']):
                    return True
                if any(indicator in bg_color.lower() for indicator in ['white', 'light', 'bright']):
                    return False
                return True  # Default to dark for non-hex
            
            # Calculate luminance for hex colors
            luminance = self._calculate_luminance(bg_color)
            return luminance < 0.5
            
        except Exception:
            # If we can't determine, assume dark theme
            return True
    
    def _calculate_luminance(self, hex_color: str) -> float:
        """
        Calculate relative luminance of a hex color.
        
        Args:
            hex_color: Color in #RRGGBB format
            
        Returns:
            Luminance value between 0 (dark) and 1 (light)
        """
        try:
            # Remove # and convert to RGB
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6:
                return 0.0
                
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255  
            b = int(hex_color[4:6], 16) / 255
            
            # Apply gamma correction
            def gamma_correct(c):
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r = gamma_correct(r)
            g = gamma_correct(g)
            b = gamma_correct(b)
            
            # Calculate luminance using ITU-R BT.709 formula
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
        except Exception:
            return 0.0
    
    def _enhance_with_theme_colors(self, base_colors: Dict[str, str], theme_colors: Dict[str, str], is_dark: bool) -> Dict[str, str]:
        """
        Enhance base syntax colors by blending with theme colors.
        
        Args:
            base_colors: Base syntax color palette
            theme_colors: Current theme colors
            is_dark: Whether theme is dark
            
        Returns:
            Enhanced syntax colors
        """
        enhanced = base_colors.copy()
        
        try:
            # Use theme accent colors if available and appropriate
            if 'info' in theme_colors:
                info_color = theme_colors['info']
                if self._is_good_contrast_color(info_color, theme_colors.get('bg_tertiary', '#ffffff')):
                    enhanced['function'] = info_color
            
            if 'warning' in theme_colors and is_dark:
                warning_color = theme_colors['warning'] 
                if self._is_good_contrast_color(warning_color, theme_colors.get('bg_tertiary', '#000000')):
                    enhanced['number'] = warning_color
            
            # Adjust colors to theme primary colors when appropriate
            text_primary = theme_colors.get('text_primary')
            if text_primary:
                # Use a muted version of text_primary for operators
                enhanced['operator'] = self._adjust_color_brightness(text_primary, 0.8)
                
        except Exception as e:
            logger.debug(f"Theme color enhancement failed: {e}")
        
        return enhanced
    
    def _validate_contrast(self, colors: Dict[str, str], theme_colors: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and adjust colors for proper contrast ratios.
        
        Args:
            colors: Syntax colors to validate
            theme_colors: Theme colors for background reference
            
        Returns:
            Contrast-validated colors
        """
        validated = colors.copy()
        background = theme_colors.get('bg_tertiary', theme_colors.get('bg_primary', '#ffffff'))
        
        for color_type, color in colors.items():
            try:
                contrast_ratio = self._calculate_contrast_ratio(color, background)
                
                # WCAG AA standard requires 4.5:1 for normal text
                if contrast_ratio < 4.5:
                    # Adjust color to meet contrast requirements
                    adjusted_color = self._adjust_for_contrast(color, background, 4.5)
                    if adjusted_color:
                        validated[color_type] = adjusted_color
                        logger.debug(f"Adjusted {color_type} color for contrast: {color} -> {adjusted_color}")
                        
            except Exception as e:
                logger.debug(f"Contrast validation failed for {color_type}: {e}")
                
        return validated
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate contrast ratio between two colors.
        
        Args:
            color1: First color in hex format
            color2: Second color in hex format
            
        Returns:
            Contrast ratio (1-21)
        """
        try:
            lum1 = self._calculate_luminance(color1)
            lum2 = self._calculate_luminance(color2)
            
            # Ensure lighter color is on top
            if lum1 < lum2:
                lum1, lum2 = lum2, lum1
                
            return (lum1 + 0.05) / (lum2 + 0.05)
            
        except Exception:
            return 1.0
    
    def _adjust_for_contrast(self, color: str, background: str, target_ratio: float) -> Optional[str]:
        """
        Adjust a color to meet minimum contrast ratio against background.
        
        Args:
            color: Color to adjust
            background: Background color
            target_ratio: Target contrast ratio
            
        Returns:
            Adjusted color or None if adjustment failed
        """
        try:
            current_ratio = self._calculate_contrast_ratio(color, background)
            if current_ratio >= target_ratio:
                return color
            
            # Determine if we need to make color lighter or darker
            bg_luminance = self._calculate_luminance(background)
            
            # Try adjusting brightness
            for adjustment in [0.3, 0.5, 0.7, 1.5, 2.0]:
                if bg_luminance > 0.5:
                    # Light background, make color darker
                    adjusted = self._adjust_color_brightness(color, 1.0 / adjustment)
                else:
                    # Dark background, make color lighter  
                    adjusted = self._adjust_color_brightness(color, adjustment)
                
                if self._calculate_contrast_ratio(adjusted, background) >= target_ratio:
                    return adjusted
            
            return None
            
        except Exception:
            return None
    
    def _adjust_color_brightness(self, color: str, factor: float) -> str:
        """
        Adjust the brightness of a color by a factor.
        
        Args:
            color: Hex color to adjust
            factor: Brightness factor (>1 = lighter, <1 = darker)
            
        Returns:
            Adjusted hex color
        """
        try:
            # Remove # and convert to RGB
            hex_color = color.lstrip('#')
            if len(hex_color) != 6:
                return color
                
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Adjust each component
            r = min(255, max(0, int(r * factor)))
            g = min(255, max(0, int(g * factor)))
            b = min(255, max(0, int(b * factor)))
            
            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
            
        except Exception:
            return color
    
    def _is_good_contrast_color(self, color: str, background: str) -> bool:
        """Check if a color has good contrast against background."""
        try:
            return self._calculate_contrast_ratio(color, background) >= 3.0
        except:
            return False
    
    def _get_fallback_colors(self, theme_colors: Dict[str, str]) -> Dict[str, str]:
        """
        Get safe fallback colors when color generation fails.
        
        Args:
            theme_colors: Current theme colors
            
        Returns:
            Safe syntax colors
        """
        # Use theme text colors as fallbacks
        text_primary = theme_colors.get('text_primary', '#ffffff')
        text_secondary = theme_colors.get('text_secondary', '#cccccc')
        
        return {
            'keyword': text_primary,
            'string': text_secondary,  
            'comment': text_secondary,
            'function': text_primary,
            'number': text_secondary,
            'builtin': text_primary,
            'operator': text_primary,
            'class': text_primary,
        }