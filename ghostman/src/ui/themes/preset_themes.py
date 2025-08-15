"""
Preset Themes for Ghostman Application.

Provides 10 carefully designed preset themes with distinct color schemes
and accessibility considerations.
"""

from typing import Dict
from .color_system import ColorSystem


def get_preset_themes() -> Dict[str, ColorSystem]:
    """
    Get all preset themes.
    
    Returns:
        Dictionary mapping theme names to ColorSystem objects
    """
    return {
        "default": get_default_theme(),
        "dark_matrix": get_dark_matrix_theme(),
        "midnight_blue": get_midnight_blue_theme(),
        "forest_green": get_forest_green_theme(),
        "sunset_orange": get_sunset_orange_theme(),
        "royal_purple": get_royal_purple_theme(),
        "arctic_white": get_arctic_white_theme(),
        "cyberpunk": get_cyberpunk_theme(),
        "earth_tones": get_earth_tones_theme(),
        "ocean_deep": get_ocean_deep_theme(),
    }


def get_default_theme() -> ColorSystem:
    """Default dark theme with green accents."""
    return ColorSystem(
        # Primary colors
        primary="#4CAF50",
        primary_hover="#45a049",
        secondary="#2196F3",
        secondary_hover="#1976D2",
        
        # Backgrounds
        background_primary="#1a1a1a",
        background_secondary="#2a2a2a",
        background_tertiary="#3a3a3a",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#ffffff",
        text_secondary="#cccccc",
        text_tertiary="#888888",
        text_disabled="#555555",
        
        # Interactive
        interactive_normal="#4a4a4a",
        interactive_hover="#5a5a5a",
        interactive_active="#6a6a6a",
        interactive_disabled="#333333",
        
        # Status
        status_success="#4CAF50",
        status_warning="#FF9800",
        status_error="#F44336",
        status_info="#2196F3",
        
        # Borders
        border_primary="#444444",
        border_secondary="#333333",
        border_focus="#4CAF50",
        separator="#2a2a2a",
    )


def get_dark_matrix_theme() -> ColorSystem:
    """Matrix-inspired dark theme with green highlights."""
    return ColorSystem(
        # Primary colors
        primary="#00ff41",
        primary_hover="#00e03a",
        secondary="#00cc33",
        secondary_hover="#00b82e",
        
        # Backgrounds
        background_primary="#0d0d0d",
        background_secondary="#1a1a1a",
        background_tertiary="#2d2d2d",
        background_overlay="#000000dd",
        
        # Text
        text_primary="#00ff41",
        text_secondary="#00cc33",
        text_tertiary="#009929",
        text_disabled="#003d0f",
        
        # Interactive
        interactive_normal="#1a3d1a",
        interactive_hover="#267326",
        interactive_active="#339933",
        interactive_disabled="#0d1a0d",
        
        # Status
        status_success="#00ff41",
        status_warning="#ffcc00",
        status_error="#ff3333",
        status_info="#00ccff",
        
        # Borders
        border_primary="#004d1a",
        border_secondary="#003d14",
        border_focus="#00ff41",
        separator="#1a3d1a",
    )


def get_midnight_blue_theme() -> ColorSystem:
    """Sophisticated midnight blue theme."""
    return ColorSystem(
        # Primary colors
        primary="#1e88e5",
        primary_hover="#1976d2",
        secondary="#42a5f5",
        secondary_hover="#2196f3",
        
        # Backgrounds
        background_primary="#0a0e1a",
        background_secondary="#131b2e",
        background_tertiary="#1e2742",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#e3f2fd",
        text_secondary="#bbdefb",
        text_tertiary="#90caf9",
        text_disabled="#37474f",
        
        # Interactive
        interactive_normal="#263238",
        interactive_hover="#34495e",
        interactive_active="#455a64",
        interactive_disabled="#1c2833",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff9800",
        status_error="#f44336",
        status_info="#2196f3",
        
        # Borders
        border_primary="#34495e",
        border_secondary="#263238",
        border_focus="#1e88e5",
        separator="#1e2742",
    )


def get_forest_green_theme() -> ColorSystem:
    """Natural forest green theme."""
    return ColorSystem(
        # Primary colors
        primary="#2e7d32",
        primary_hover="#388e3c",
        secondary="#66bb6a",
        secondary_hover="#4caf50",
        
        # Backgrounds
        background_primary="#0d1b0f",
        background_secondary="#1b2e1f",
        background_tertiary="#2e4a33",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#e8f5e8",
        text_secondary="#c8e6c9",
        text_tertiary="#a5d6a7",
        text_disabled="#2e4a33",
        
        # Interactive
        interactive_normal="#1b5e20",
        interactive_hover="#2e7d32",
        interactive_active="#388e3c",
        interactive_disabled="#0d1b0f",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff8f00",
        status_error="#d32f2f",
        status_info="#1976d2",
        
        # Borders
        border_primary="#2e4a33",
        border_secondary="#1b5e20",
        border_focus="#2e7d32",
        separator="#1b2e1f",
    )


def get_sunset_orange_theme() -> ColorSystem:
    """Warm sunset orange theme."""
    return ColorSystem(
        # Primary colors
        primary="#f57c00",
        primary_hover="#ef6c00",
        secondary="#ff9800",
        secondary_hover="#f57c00",
        
        # Backgrounds
        background_primary="#1a0f08",
        background_secondary="#2e1b0f",
        background_tertiary="#4a2c1a",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#fff3e0",
        text_secondary="#ffe0b2",
        text_tertiary="#ffcc80",
        text_disabled="#4a2c1a",
        
        # Interactive
        interactive_normal="#5d4037",
        interactive_hover="#6d4c41",
        interactive_active="#795548",
        interactive_disabled="#3e2723",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff9800",
        status_error="#f44336",
        status_info="#2196f3",
        
        # Borders
        border_primary="#5d4037",
        border_secondary="#4a2c1a",
        border_focus="#f57c00",
        separator="#2e1b0f",
    )


def get_royal_purple_theme() -> ColorSystem:
    """Elegant royal purple theme."""
    return ColorSystem(
        # Primary colors
        primary="#7b1fa2",
        primary_hover="#8e24aa",
        secondary="#9c27b0",
        secondary_hover="#ab47bc",
        
        # Backgrounds
        background_primary="#12081a",
        background_secondary="#1f0f2e",
        background_tertiary="#331a4a",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#f3e5f5",
        text_secondary="#e1bee7",
        text_tertiary="#ce93d8",
        text_disabled="#331a4a",
        
        # Interactive
        interactive_normal="#4a148c",
        interactive_hover="#6a1b9a",
        interactive_active="#7b1fa2",
        interactive_disabled="#2e0845",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff9800",
        status_error="#f44336",
        status_info="#2196f3",
        
        # Borders
        border_primary="#4a148c",
        border_secondary="#331a4a",
        border_focus="#7b1fa2",
        separator="#1f0f2e",
    )


def get_arctic_white_theme() -> ColorSystem:
    """Clean arctic white light theme."""
    return ColorSystem(
        # Primary colors
        primary="#1976d2",
        primary_hover="#1565c0",
        secondary="#2196f3",
        secondary_hover="#1e88e5",
        
        # Backgrounds
        background_primary="#fafafa",
        background_secondary="#f5f5f5",
        background_tertiary="#eeeeee",
        background_overlay="#00000080",
        
        # Text
        text_primary="#212121",
        text_secondary="#424242",
        text_tertiary="#757575",
        text_disabled="#bdbdbd",
        
        # Interactive
        interactive_normal="#e0e0e0",
        interactive_hover="#d5d5d5",
        interactive_active="#cccccc",
        interactive_disabled="#f5f5f5",
        
        # Status
        status_success="#388e3c",
        status_warning="#f57c00",
        status_error="#d32f2f",
        status_info="#1976d2",
        
        # Borders
        border_primary="#bdbdbd",
        border_secondary="#e0e0e0",
        border_focus="#1976d2",
        separator="#eeeeee",
    )


def get_cyberpunk_theme() -> ColorSystem:
    """Futuristic cyberpunk theme with neon accents."""
    return ColorSystem(
        # Primary colors
        primary="#ff0080",
        primary_hover="#e6006b",
        secondary="#00ffff",
        secondary_hover="#00e6e6",
        
        # Backgrounds
        background_primary="#0a0a0a",
        background_secondary="#1a1a2e",
        background_tertiary="#16213e",
        background_overlay="#000000dd",
        
        # Text
        text_primary="#ffffff",
        text_secondary="#ff00ff",
        text_tertiary="#00ffff",
        text_disabled="#4a4a4a",
        
        # Interactive
        interactive_normal="#0f3460",
        interactive_hover="#16537e",
        interactive_active="#1a6b99",
        interactive_disabled="#0a0a0a",
        
        # Status
        status_success="#00ff00",
        status_warning="#ffff00",
        status_error="#ff0040",
        status_info="#00ffff",
        
        # Borders
        border_primary="#ff0080",
        border_secondary="#0f3460",
        border_focus="#00ffff",
        separator="#16213e",
    )


def get_earth_tones_theme() -> ColorSystem:
    """Warm earth tones theme."""
    return ColorSystem(
        # Primary colors
        primary="#8d6e63",
        primary_hover="#795548",
        secondary="#a1887f",
        secondary_hover="#8d6e63",
        
        # Backgrounds
        background_primary="#1c1611",
        background_secondary="#2e2419",
        background_tertiary="#4a3728",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#efebe9",
        text_secondary="#d7ccc8",
        text_tertiary="#bcaaa4",
        text_disabled="#4a3728",
        
        # Interactive
        interactive_normal="#5d4037",
        interactive_hover="#6d4c41",
        interactive_active="#795548",
        interactive_disabled="#3e2723",
        
        # Status
        status_success="#689f38",
        status_warning="#f57c00",
        status_error="#d32f2f",
        status_info="#1976d2",
        
        # Borders
        border_primary="#5d4037",
        border_secondary="#4a3728",
        border_focus="#8d6e63",
        separator="#2e2419",
    )


def get_ocean_deep_theme() -> ColorSystem:
    """Deep ocean theme with blue-green tones."""
    return ColorSystem(
        # Primary colors
        primary="#00695c",
        primary_hover="#00796b",
        secondary="#26a69a",
        secondary_hover="#00897b",
        
        # Backgrounds
        background_primary="#0d1117",
        background_secondary="#161b22",
        background_tertiary="#21262d",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#e0f2f1",
        text_secondary="#b2dfdb",
        text_tertiary="#80cbc4",
        text_disabled="#37474f",
        
        # Interactive
        interactive_normal="#263238",
        interactive_hover="#34495e",
        interactive_active="#455a64",
        interactive_disabled="#1c2833",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff9800",
        status_error="#f44336",
        status_info="#00bcd4",
        
        # Borders
        border_primary="#34495e",
        border_secondary="#263238",
        border_focus="#00695c",
        separator="#161b22",
    )