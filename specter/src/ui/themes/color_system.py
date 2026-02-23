"""
Color System for Specter Theme Framework.

Provides a comprehensive 24-variable color system with semantic naming
for consistent theming across the application.
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from PyQt6.QtGui import QColor


@dataclass
class ColorSystem:
    """
    Core color system with 24 semantic variables for comprehensive theming.
    
    Variables are organized into logical groups:
    - Primary/Secondary: Main brand colors
    - Backgrounds: Various background shades
    - Text: Text colors for different contexts
    - Interactive: Buttons, links, and interactive elements
    - Status: Success, warning, error, info colors
    - Borders: Border and separator colors
    """
    
    # Primary brand colors
    primary: str = "#4CAF50"           # Main brand color (green)
    primary_hover: str = "#45a049"     # Primary color on hover
    secondary: str = "#2196F3"         # Secondary accent color (blue)
    secondary_hover: str = "#1976D2"   # Secondary color on hover
    
    # Background colors
    background_primary: str = "#1a1a1a"     # Main background
    background_secondary: str = "#2a2a2a"   # Secondary panels
    background_tertiary: str = "#3a3a3a"    # Cards, elevated surfaces
    background_overlay: str = "#000000cc"   # Modal overlays (with alpha)
    
    # Text colors
    text_primary: str = "#ffffff"      # Primary text (high contrast)
    text_secondary: str = "#cccccc"    # Secondary text (medium contrast)
    text_tertiary: str = "#888888"     # Tertiary text (low contrast)
    text_disabled: str = "#555555"     # Disabled text
    
    # Interactive elements
    interactive_normal: str = "#4a4a4a"     # Normal interactive elements
    interactive_hover: str = "#5a5a5a"      # Hover state
    interactive_active: str = "#6a6a6a"     # Active/pressed state
    interactive_disabled: str = "#333333"   # Disabled interactive elements
    
    # Status colors
    status_success: str = "#4CAF50"    # Success states
    status_warning: str = "#FF9800"    # Warning states
    status_error: str = "#F44336"      # Error states
    status_info: str = "#2196F3"       # Info states
    
    # Border and separator colors
    border_primary: str = "#444444"    # Main borders
    border_secondary: str = "#333333"  # Secondary borders
    border_focus: str = "#4CAF50"      # Focus indicators
    separator: str = "#2a2a2a"         # Separators and dividers
    
    # Tab colors
    tab_text_color: str = "#cccccc"     # Inactive tab text color
    tab_background_color: str = "#3a3a3a"   # Inactive tab background color
    tab_active_text_color: str = "#ffffff"  # Active tab text color
    tab_active_background_color: str = "#4CAF50"  # Active tab background color
    
    def to_dict(self) -> Dict[str, str]:
        """Convert color system to dictionary for serialization."""
        return {
            'primary': self.primary,
            'primary_hover': self.primary_hover,
            'secondary': self.secondary,
            'secondary_hover': self.secondary_hover,
            'background_primary': self.background_primary,
            'background_secondary': self.background_secondary,
            'background_tertiary': self.background_tertiary,
            'background_overlay': self.background_overlay,
            'text_primary': self.text_primary,
            'text_secondary': self.text_secondary,
            'text_tertiary': self.text_tertiary,
            'text_disabled': self.text_disabled,
            'interactive_normal': self.interactive_normal,
            'interactive_hover': self.interactive_hover,
            'interactive_active': self.interactive_active,
            'interactive_disabled': self.interactive_disabled,
            'status_success': self.status_success,
            'status_warning': self.status_warning,
            'status_error': self.status_error,
            'status_info': self.status_info,
            'border_primary': self.border_primary,
            'border_secondary': self.border_secondary,
            'border_focus': self.border_focus,
            'separator': self.separator,
            'tab_text_color': self.tab_text_color,
            'tab_background_color': self.tab_background_color,
            'tab_active_text_color': self.tab_active_text_color,
            'tab_active_background_color': self.tab_active_background_color,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ColorSystem':
        """Create color system from dictionary."""
        return cls(**data)
    
    def get_color(self, name: str) -> str:
        """Get color by name with fallback to primary if not found."""
        return getattr(self, name, self.primary)
    
    def get_qcolor(self, name: str) -> QColor:
        """Get QColor object for the specified color name."""
        color_hex = self.get_color(name)
        return QColor(color_hex)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Enhanced validation for accessibility and consistency with WCAG 2.1 compliance.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check that all colors are valid hex values
        for name, color in self.to_dict().items():
            if not self._is_valid_hex_color(color):
                issues.append(f"Invalid hex color for {name}: {color}")
        
        # Enhanced contrast ratio checks for WCAG 2.1 AA compliance
        contrast_checks = [
            ('text_primary', 'background_primary', 'Primary text readability'),
            ('text_secondary', 'background_secondary', 'Secondary text readability'),
            ('text_tertiary', 'background_tertiary', 'Tertiary text readability'),
            ('text_primary', 'background_secondary', 'Primary text on panels'),
            ('text_primary', 'background_tertiary', 'Primary text on cards'),
            ('status_error', 'background_primary', 'Error text visibility'),
            ('status_warning', 'background_primary', 'Warning text visibility'),
            ('status_success', 'background_primary', 'Success text visibility'),
        ]
        
        for text_color, bg_color, description in contrast_checks:
            contrast = self._calculate_contrast_ratio(
                self.get_color(text_color),
                self.get_color(bg_color)
            )
            if contrast < 4.5:  # WCAG AA standard for normal text
                issues.append(
                    f"{description}: Low contrast ratio ({contrast:.2f}) - recommend 4.5+ for accessibility"
                )
            elif contrast < 7.0:  # WCAG AAA standard
                # This is a suggestion, not an error
                pass
        
        # Check for sufficient color differentiation
        similar_color_checks = [
            ('primary', 'secondary', 'Brand colors should be visually distinct'),
            ('status_success', 'status_info', 'Success and info colors should be distinguishable'),
            ('status_warning', 'status_error', 'Warning and error colors should be distinguishable'),
        ]
        
        for color1, color2, description in similar_color_checks:
            if self._colors_too_similar(self.get_color(color1), self.get_color(color2)):
                issues.append(f"{description}: Colors are too similar for accessibility")
        
        # Check for color-only communication issues
        status_colors = [self.status_success, self.status_warning, self.status_error, self.status_info]
        if len(set(status_colors)) < 4:
            issues.append("Status colors should all be unique to avoid confusion")
        
        return len(issues) == 0, issues
    
    def _colors_too_similar(self, color1: str, color2: str, threshold: float = 3.0) -> bool:
        """Check if two colors are too similar for accessibility."""
        # Calculate color difference using delta E approximation
        qcolor1 = QColor(color1)
        qcolor2 = QColor(color2)
        
        # Simple RGB distance calculation
        r_diff = abs(qcolor1.red() - qcolor2.red())
        g_diff = abs(qcolor1.green() - qcolor2.green())
        b_diff = abs(qcolor1.blue() - qcolor2.blue())
        
        # Weighted difference (human eye is more sensitive to green)
        distance = (2 * r_diff**2 + 4 * g_diff**2 + 3 * b_diff**2) ** 0.5
        
        return distance < (threshold * 100)  # Scale threshold appropriately
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Check if string is a valid hex color."""
        if not color.startswith('#'):
            return False
        
        hex_part = color[1:]
        if len(hex_part) not in [3, 6, 8]:  # Support 3, 6, or 8 digit hex
            return False
        
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors."""
        def get_luminance(color: str) -> float:
            """Calculate relative luminance of a color."""
            # Simple approximation - in production you'd want a more accurate calculation
            qcolor = QColor(color)
            r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
            
            # Apply gamma correction
            r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
            g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
            b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
            
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        lum1 = get_luminance(color1)
        lum2 = get_luminance(color2)
        
        # Ensure lighter color is in numerator
        if lum1 < lum2:
            lum1, lum2 = lum2, lum1
        
        return (lum1 + 0.05) / (lum2 + 0.05)


class ColorUtils:
    """Utility functions for color manipulation and analysis."""
    
    @staticmethod
    def lighten(color: str, factor: float = 0.1) -> str:
        """Lighten a color by the specified factor (0.0 to 1.0)."""
        qcolor = QColor(color)
        h, s, l, a = qcolor.getHsl()
        l = min(255, int(l + (255 - l) * factor))
        qcolor.setHsl(h, s, l, a)
        return qcolor.name()
    
    @staticmethod
    def darken(color: str, factor: float = 0.1) -> str:
        """Darken a color by the specified factor (0.0 to 1.0)."""
        qcolor = QColor(color)
        h, s, l, a = qcolor.getHsl()
        l = max(0, int(l - l * factor))
        qcolor.setHsl(h, s, l, a)
        return qcolor.name()
    
    @staticmethod
    def with_alpha(color: str, alpha: float) -> str:
        """Add alpha channel to color (0.0 to 1.0)."""
        qcolor = QColor(color)
        qcolor.setAlphaF(alpha)
        return qcolor.name(QColor.NameFormat.HexArgb)
    
    @staticmethod
    def blend(color1: str, color2: str, ratio: float = 0.5) -> str:
        """Blend two colors with the specified ratio (0.0 = color1, 1.0 = color2)."""
        qcolor1 = QColor(color1)
        qcolor2 = QColor(color2)
        
        r = int(qcolor1.red() * (1 - ratio) + qcolor2.red() * ratio)
        g = int(qcolor1.green() * (1 - ratio) + qcolor2.green() * ratio)
        b = int(qcolor1.blue() * (1 - ratio) + qcolor2.blue() * ratio)
        
        result = QColor(r, g, b)
        return result.name()
    
    @staticmethod
    def get_high_contrast_text_color_for_background(background_color: str, 
                                                  theme_colors: 'ColorSystem' = None,
                                                  min_ratio: float = 4.5) -> Tuple[str, float]:
        """
        Find the best high-contrast text color for the given background.
        
        Uses the same smart algorithm as titlebar buttons to ensure maximum readability
        for search result counts and other UI elements.
        
        Args:
            background_color: Background color (hex string)
            theme_colors: ColorSystem instance to provide theme-aware candidates
            min_ratio: Minimum WCAG contrast ratio (default 4.5 for AA compliance)
            
        Returns:
            Tuple of (best_color, contrast_ratio)
        """
        def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
            """Calculate WCAG contrast ratio between two hex colors."""
            try:
                qcolor1 = QColor(color1_hex)
                qcolor2 = QColor(color2_hex)
                
                def get_luminance(qcolor):
                    r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                    r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                    g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                    b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                    return 0.2126 * r + 0.7152 * g + 0.0722 * b
                
                lum1 = get_luminance(qcolor1)
                lum2 = get_luminance(qcolor2)
                
                if lum1 < lum2:
                    lum1, lum2 = lum2, lum1
                
                return (lum1 + 0.05) / (lum2 + 0.05)
            except:
                return 0.0
        
        # Start with theme-aware candidates if available
        text_candidates = []
        
        if theme_colors:
            # Try theme colors first (may provide better visual integration)
            text_candidates.extend([
                theme_colors.text_primary,
                theme_colors.text_secondary,
                theme_colors.background_primary,  # Sometimes main bg works well as text
                theme_colors.border_primary,      # Border colors often have good contrast
                theme_colors.secondary,           # Accent colors can work
            ])
        
        # Always add high-contrast fallbacks
        text_candidates.extend([
            "#ffffff",  # Pure white
            "#000000",  # Pure black
            "#f8f8f2",  # Near white (popular in dark themes)
            "#2d2d2d",  # Dark gray
            "#e6e6e6",  # Light gray
            "#333333",  # Medium dark gray
        ])
        
        # Find the best contrast
        best_color = text_candidates[0]
        best_ratio = 0.0
        
        for candidate in text_candidates:
            try:
                ratio = calculate_contrast_ratio(candidate, background_color)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_color = candidate
                    
                # If we found excellent contrast, we can stop early
                if ratio >= 7.0:  # WCAG AAA level
                    break
                    
            except:
                continue
        
        # If we still don't have adequate contrast, force high contrast
        if best_ratio < min_ratio:
            # Determine if background is dark or light
            try:
                bg_qcolor = QColor(background_color)
                bg_luminance = (bg_qcolor.red() + bg_qcolor.green() + bg_qcolor.blue()) / (3 * 255.0)
                
                if bg_luminance > 0.5:
                    # Light background - force black text
                    best_color = "#000000"
                    best_ratio = calculate_contrast_ratio("#000000", background_color)
                else:
                    # Dark background - force white text
                    best_color = "#ffffff"
                    best_ratio = calculate_contrast_ratio("#ffffff", background_color)
            except:
                # Fallback to white text
                best_color = "#ffffff"
                best_ratio = calculate_contrast_ratio("#ffffff", background_color)
        
        return best_color, best_ratio