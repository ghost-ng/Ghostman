"""
Icon Styling System for Specter Application.

Provides optimized styling for save/plus icons and other interface icons
with enhanced visibility and accessibility across all themes.

Key Features:
1. High-contrast icon backgrounds for maximum visibility
2. Consistent icon sizing and spacing
3. Theme-aware icon colors with fallback support
4. Special handling for titlebar icons (save, plus, minimize, close)
5. Accessibility compliance for icon contrast ratios
"""

from typing import Dict, Tuple
from .color_system import ColorSystem, ColorUtils


class IconStyleManager:
    """
    Manager for clean, distinct icon styling with maximum visibility and accessibility.
    
    Provides clean icon styling without special effects for save/plus icons and other 
    interface elements. Focuses on clarity, accessibility, and consistent appearance
    across all themes.
    
    Key Design Principles:
    - No special effects or animations - clean and simple
    - Maximum contrast for visibility
    - Clear distinction between save and plus icons 
    - Theme-aware colors that work across all redesigned themes
    - WCAG 2.1 AA compliance for accessibility
    """
    
    @staticmethod
    def get_clean_icon_style(
        colors: ColorSystem, 
        icon_type: str = "normal",
        size: int = 16
    ) -> str:
        """
        Generate clean, distinct CSS for save and plus icons without special effects.
        
        This method provides the cleanest possible styling for maximum visibility
        and distinction between different icon types. No gradients, shadows, or
        other visual effects - just clean, accessible styling.
        
        Args:
            colors: Current theme colors
            icon_type: Type of icon - "save", "plus", "normal", "minimize", "close"
            size: Icon size in pixels
            
        Returns:
            Clean CSS styling string for the icon button
        """
        # Get the most contrasting background for icon visibility
        bg_color = colors.background_secondary
        
        # Calculate the best text color for maximum contrast
        text_color, contrast_ratio = ColorUtils.get_high_contrast_text_color_for_background(
            bg_color, colors, min_ratio=4.5
        )
        
        # Apply clean, distinct colors for different icon types
        # These colors are chosen for maximum distinction and accessibility
        if icon_type == "save":
            # Use success color for save - universally understood
            if IconStyleManager._calculate_contrast(colors.status_success, bg_color) >= 4.5:
                text_color = colors.status_success
                icon_description = "Save - Success Green"
            else:
                # Fallback to high contrast if success color isn't visible enough
                text_color = text_color
                icon_description = "Save - High Contrast"
                
        elif icon_type == "plus":
            # Use primary color for plus - indicates primary action
            if IconStyleManager._calculate_contrast(colors.primary, bg_color) >= 4.5:
                text_color = colors.primary
                icon_description = "Plus - Primary Blue"
            else:
                # Fallback to high contrast
                text_color = text_color
                icon_description = "Plus - High Contrast"
                
        elif icon_type == "close":
            # Use error color for close - universally understood as negative action
            if IconStyleManager._calculate_contrast(colors.status_error, bg_color) >= 4.5:
                text_color = colors.status_error
                icon_description = "Close - Error Red"
            else:
                text_color = text_color
                icon_description = "Close - High Contrast"
        else:
            icon_description = "Standard Icon"
        
        # Clean hover state - subtle but noticeable
        hover_bg = IconStyleManager._get_clean_hover_color(bg_color)
        
        # Clean active state - clear feedback without being jarring
        active_bg = IconStyleManager._get_clean_active_color(bg_color)
        
        # Generate clean CSS with no special effects
        return f"""
        /* Clean {icon_description} Styling - No Special Effects */
        QPushButton, QToolButton {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {colors.border_secondary};
            border-radius: 4px;
            padding: 4px;
            min-width: {size + 8}px;
            min-height: {size + 8}px;
            max-width: {size + 8}px;
            max-height: {size + 8}px;
            font-size: {max(10, size - 4)}px;
            font-weight: normal;
            /* No box-shadow, no gradients, no special effects */
        }}
        
        QPushButton:hover, QToolButton:hover {{
            background-color: {hover_bg};
            color: {text_color};
            border-color: {colors.border_focus};
            /* Clean hover - just background change */
        }}
        
        QPushButton:pressed, QToolButton:pressed {{
            background-color: {active_bg};
            color: {text_color};
            border-color: {colors.border_focus};
            /* Clean pressed state - no special effects */
        }}
        
        QPushButton:disabled, QToolButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
            opacity: 0.6;
        }}
        
        /* Clean icon sizing - proportional and clear */
        QPushButton::icon, QToolButton::icon {{
            width: {size}px;
            height: {size}px;
        }}
        """
    
    @staticmethod
    def get_titlebar_icon_style(
        colors: ColorSystem, 
        icon_type: str = "normal",
        size: int = 16
    ) -> str:
        """
        Generate optimized CSS for titlebar icons (save, plus, minimize, close).
        
        Args:
            colors: Current theme colors
            icon_type: Type of icon - "save", "plus", "minimize", "close", or "normal"
            size: Icon size in pixels
            
        Returns:
            CSS styling string for the icon button
        """
        # Get high contrast background and text colors
        bg_color = colors.background_secondary
        text_color, contrast_ratio = ColorUtils.get_high_contrast_text_color_for_background(
            bg_color, colors, min_ratio=4.5
        )
        
        # Special colors for different icon types
        if icon_type == "save":
            # Use success color for save button if it has good contrast
            success_contrast = IconStyleManager._calculate_contrast(
                colors.status_success, bg_color
            )
            if success_contrast >= 4.5:
                text_color = colors.status_success
        elif icon_type == "plus":
            # Use primary color for plus button if it has good contrast
            primary_contrast = IconStyleManager._calculate_contrast(
                colors.primary, bg_color
            )
            if primary_contrast >= 4.5:
                text_color = colors.primary
        elif icon_type == "close":
            # Use error color for close button if it has good contrast
            error_contrast = IconStyleManager._calculate_contrast(
                colors.status_error, bg_color
            )
            if error_contrast >= 4.5:
                text_color = colors.status_error
        
        # Enhanced hover states for better UX
        hover_bg = ColorUtils.lighten(bg_color, 0.1) if IconStyleManager._is_dark_color(bg_color) else ColorUtils.darken(bg_color, 0.1)
        hover_text = text_color  # Keep text color consistent on hover
        
        # Active (pressed) state
        active_bg = ColorUtils.lighten(bg_color, 0.2) if IconStyleManager._is_dark_color(bg_color) else ColorUtils.darken(bg_color, 0.15)
        
        return f"""
        QPushButton, QToolButton {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {colors.border_secondary};
            border-radius: 4px;
            padding: 4px;
            min-width: {size + 8}px;
            min-height: {size + 8}px;
            max-width: {size + 8}px;
            max-height: {size + 8}px;
            font-size: {max(10, size - 4)}px;
            font-weight: bold;
        }}
        
        QPushButton:hover, QToolButton:hover {{
            background-color: {hover_bg};
            color: {hover_text};
            border-color: {colors.border_focus};
        }}
        
        QPushButton:pressed, QToolButton:pressed {{
            background-color: {active_bg};
            color: {hover_text};
            border-color: {colors.border_focus};
        }}
        
        QPushButton:disabled, QToolButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        
        /* Icon-specific styling */
        QPushButton::icon, QToolButton::icon {{
            width: {size}px;
            height: {size}px;
        }}
        """
    
    @staticmethod
    def get_interface_area_styling(colors: ColorSystem, area: str) -> Dict[str, str]:
        """
        Get styling for the 4 main interface areas with clear visual hierarchy.
        
        Args:
            colors: Current theme colors
            area: Interface area - "titlebar", "repl", "search_bar", "input_bar"
            
        Returns:
            Dictionary of CSS properties for the area
        """
        if area == "titlebar":
            return {
                "background-color": colors.background_secondary,
                "border-bottom": f"1px solid {colors.border_primary}",
                "padding": "4px 8px",
                "min-height": "32px"
            }
        elif area == "repl":
            return {
                "background-color": colors.background_primary,
                "color": colors.text_primary,
                "border": f"1px solid {colors.border_secondary}",
                "border-radius": "4px",
                "padding": "8px"
            }
        elif area == "search_bar":
            # Medium contrast between titlebar and REPL
            search_bg = ColorUtils.blend(colors.background_secondary, colors.background_primary, 0.5)
            return {
                "background-color": search_bg,
                "border": f"1px solid {colors.border_secondary}",
                "border-radius": "4px",
                "padding": "4px 8px",
                "margin": "4px"
            }
        elif area == "input_bar":
            return {
                "background-color": colors.background_tertiary,
                "color": colors.text_primary,
                "border": f"2px solid {colors.border_focus}",  # Thicker border for prominence
                "border-radius": "6px",
                "padding": "8px 12px",
                "margin": "4px"
            }
        
        return {}
    
    @staticmethod
    def get_optimized_button_style(
        colors: ColorSystem,
        button_type: str = "normal",
        size: str = "medium"
    ) -> str:
        """
        Get optimized button styling with enhanced visibility.
        
        Args:
            colors: Current theme colors
            button_type: Type of button - "primary", "secondary", "danger", "normal"
            size: Button size - "small", "medium", "large"
            
        Returns:
            CSS styling string for the button
        """
        # Size configurations
        size_config = {
            "small": {"padding": "4px 8px", "font_size": "12px", "border_radius": "3px"},
            "medium": {"padding": "6px 12px", "font_size": "14px", "border_radius": "4px"},
            "large": {"padding": "8px 16px", "font_size": "16px", "border_radius": "6px"}
        }
        
        config = size_config.get(size, size_config["medium"])
        
        # Button type configurations
        if button_type == "primary":
            bg_color = colors.primary
            text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(bg_color, colors)
            hover_bg = colors.primary_hover
        elif button_type == "secondary":
            bg_color = colors.secondary
            text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(bg_color, colors)
            hover_bg = colors.secondary_hover
        elif button_type == "danger":
            bg_color = colors.status_error
            text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(bg_color, colors)
            hover_bg = ColorUtils.darken(colors.status_error, 0.1)
        else:  # normal
            bg_color = colors.interactive_normal
            text_color, _ = ColorUtils.get_high_contrast_text_color_for_background(bg_color, colors)
            hover_bg = colors.interactive_hover
        
        return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {colors.border_secondary};
            border-radius: {config['border_radius']};
            padding: {config['padding']};
            font-size: {config['font_size']};
            font-weight: 500;
            min-height: 24px;
        }}
        
        QPushButton:hover {{
            background-color: {hover_bg};
            border-color: {colors.border_focus};
        }}
        
        QPushButton:pressed {{
            background-color: {ColorUtils.darken(hover_bg, 0.1)};
            border-color: {colors.border_focus};
        }}
        
        QPushButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        """
    
    @staticmethod
    def _calculate_contrast(color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors."""
        try:
            from PyQt6.QtGui import QColor
            
            def get_luminance(hex_color: str) -> float:
                qcolor = QColor(hex_color)
                r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                
                # Apply gamma correction
                r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            lum1 = get_luminance(color1)
            lum2 = get_luminance(color2)
            
            if lum1 < lum2:
                lum1, lum2 = lum2, lum1
            
            return (lum1 + 0.05) / (lum2 + 0.05)
        except:
            return 4.5  # Default to acceptable contrast
    
    @staticmethod
    def _is_dark_color(hex_color: str) -> bool:
        """Determine if a color is dark (luminance < 0.5)."""
        try:
            from PyQt6.QtGui import QColor
            qcolor = QColor(hex_color)
            luminance = (qcolor.red() + qcolor.green() + qcolor.blue()) / (3 * 255.0)
            return luminance < 0.5
        except:
            return True  # Default to dark
    
    @staticmethod
    def _get_clean_hover_color(bg_color: str) -> str:
        """
        Generate clean hover color without special effects.
        
        Simply lightens or darkens the background by a small amount
        for subtle but clear hover feedback.
        """
        try:
            if IconStyleManager._is_dark_color(bg_color):
                return ColorUtils.lighten(bg_color, 0.15)  # Subtle lightening for dark themes
            else:
                return ColorUtils.darken(bg_color, 0.1)   # Subtle darkening for light themes
        except:
            # Fallback to a universally safe hover color
            return "#404040" if IconStyleManager._is_dark_color(bg_color) else "#e0e0e0"
    
    @staticmethod
    def _get_clean_active_color(bg_color: str) -> str:
        """
        Generate clean active (pressed) color without special effects.
        
        Provides clear feedback that the button is pressed without
        jarring visual effects.
        """
        try:
            if IconStyleManager._is_dark_color(bg_color):
                return ColorUtils.lighten(bg_color, 0.25)  # More noticeable for pressed state
            else:
                return ColorUtils.darken(bg_color, 0.15)   # Clear darkening for light themes
        except:
            # Fallback to universally safe active colors
            return "#505050" if IconStyleManager._is_dark_color(bg_color) else "#cccccc"


def apply_clean_icon_styling(widget, colors: ColorSystem, icon_type: str = "normal", size: int = 16):
    """
    Apply clean, distinct icon styling to a widget without special effects.
    
    This is the recommended function for styling save and plus buttons
    to ensure maximum visibility and distinction across all themes.
    
    Args:
        widget: Qt widget to style
        colors: Current theme colors
        icon_type: Type of icon - "save", "plus", "normal", etc.
        size: Icon size in pixels
    """
    style = IconStyleManager.get_clean_icon_style(colors, icon_type, size)
    widget.setStyleSheet(style)


def apply_enhanced_icon_styling(widget, colors: ColorSystem, icon_type: str = "normal"):
    """
    Apply enhanced icon styling to a widget.
    
    Note: For save and plus buttons, use apply_clean_icon_styling() instead
    for better visibility and cleaner appearance.
    
    Args:
        widget: Qt widget to style
        colors: Current theme colors
        icon_type: Type of icon for special handling
    """
    style = IconStyleManager.get_titlebar_icon_style(colors, icon_type)
    widget.setStyleSheet(style)


def apply_interface_area_styling(widget, colors: ColorSystem, area: str):
    """
    Apply interface area styling to a widget.
    
    Args:
        widget: Qt widget to style
        colors: Current theme colors
        area: Interface area type
    """
    properties = IconStyleManager.get_interface_area_styling(colors, area)
    style_parts = [f"{prop}: {value};" for prop, value in properties.items()]
    widget.setStyleSheet(" ".join(style_parts))


def apply_save_button_styling(widget, colors: ColorSystem, size: int = 16):
    """
    Apply optimized styling specifically for save buttons.
    
    Uses clean styling with success color for clear identification
    as a save action. No special effects, just clean visibility.
    
    Args:
        widget: Save button widget to style
        colors: Current theme colors
        size: Icon size in pixels
    """
    apply_clean_icon_styling(widget, colors, "save", size)


def apply_plus_button_styling(widget, colors: ColorSystem, size: int = 16):
    """
    Apply optimized styling specifically for plus buttons.
    
    Uses clean styling with primary color for clear identification
    as an add/new action. No special effects, just clean visibility.
    
    Args:
        widget: Plus button widget to style
        colors: Current theme colors
        size: Icon size in pixels
    """
    apply_clean_icon_styling(widget, colors, "plus", size)