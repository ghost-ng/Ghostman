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
        # New custom themes now built-in
        "lilac": get_lilac_theme(),
        "sunburst": get_sunburst_theme(),
        "forest": get_forest_theme(),
        "firefly": get_firefly_theme(),
        "mintly": get_mintly_theme(),
        "ocean": get_ocean_theme(),
        "pulse": get_pulse_theme(),
        "solarized_light": get_solarized_light_theme(),
        "solarized_dark": get_solarized_dark_theme(),
        "dracula": get_dracula_theme(),
        "openai_like": get_openai_like_theme(),
        "openui_like": get_openui_like_theme(),
        "openwebui_like": get_openwebui_like_theme(),
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
        primary="#66bb6a",
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
        primary="#ce93d8",
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
    """Clean arctic white light theme with improved readability."""
    return ColorSystem(
        # Primary colors
        primary="#1565c0",
        primary_hover="#1976d2",
        secondary="#1e88e5",
        secondary_hover="#2196f3",
        
        # Backgrounds
        background_primary="#ffffff",
        background_secondary="#f8f9fa",
        background_tertiary="#e9ecef",
        background_overlay="#00000080",
        
        # Text - Much darker for better readability in REPL
        text_primary="#111111",
        text_secondary="#333333",
        text_tertiary="#555555",
        text_disabled="#999999",
        
        # Interactive - improved for better button visibility
        interactive_normal="#f0f4f8",  # Light blue-gray for button backgrounds
        interactive_hover="#e3f2fd",   # Slightly more blue on hover
        interactive_active="#bbdefb",  # Even more blue when pressed
        interactive_disabled="#f8f9fa",
        
        # Status
        status_success="#28a745",
        status_warning="#fd7e14",
        status_error="#dc3545",
        status_info="#1565c0",
        
        # Borders
        border_primary="#6c757d",
        border_secondary="#dee2e6",
        border_focus="#1565c0",
        separator="#e9ecef",
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
        primary="#bcaaa4",
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
        primary="#26a69a",
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


def get_lilac_theme() -> ColorSystem:
    """Soft lilac purple theme with elegant pastel accents."""
    return ColorSystem(
        # Primary colors
        primary="#a176b6",
        primary_hover="#9461a8",
        secondary="#b894c7",
        secondary_hover="#c4a3d1",
        
        # Backgrounds
        background_primary="#1a0f1d",
        background_secondary="#2b1830",
        background_tertiary="#3d2142",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#f0e6f3",
        text_secondary="#dcc8e0",
        text_tertiary="#c8aacf",
        text_disabled="#5a4960",
        
        # Interactive
        interactive_normal="#4a3350",
        interactive_hover="#5c4063",
        interactive_active="#6e4d75",
        interactive_disabled="#2b1830",
        
        # Status
        status_success="#7cb342",
        status_warning="#ffb74d",
        status_error="#e57373",
        status_info="#64b5f6",
        
        # Borders
        border_primary="#5a4960",
        border_secondary="#4a3350",
        border_focus="#a176b6",
        separator="#3d2142",
    )


def get_sunburst_theme() -> ColorSystem:
    """Warm sunburst theme with golden orange and deep coral tones."""
    return ColorSystem(
        # Primary colors
        primary="#f16a1f",
        primary_hover="#e85d0e",
        secondary="#ff8c42",
        secondary_hover="#ff7b2b",
        
        # Backgrounds
        background_primary="#1a0e08",
        background_secondary="#2e1b0f",
        background_tertiary="#4a2f1c",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#fff3e0",
        text_secondary="#ffe0b2",
        text_tertiary="#ffcc80",
        text_disabled="#6b4423",
        
        # Interactive
        interactive_normal="#5d3317",
        interactive_hover="#7a4420",
        interactive_active="#96552a",
        interactive_disabled="#2e1b0f",
        
        # Status
        status_success="#66bb6a",
        status_warning="#ffb74d",
        status_error="#ef5350",
        status_info="#42a5f5",
        
        # Borders
        border_primary="#6b4423",
        border_secondary="#5d3317",
        border_focus="#f16a1f",
        separator="#4a2f1c",
    )


def get_forest_theme() -> ColorSystem:
    """Deep forest theme with rich greens and earth tones."""
    return ColorSystem(
        # Primary colors
        primary="#7ba572",
        primary_hover="#5a8a52",
        secondary="#6d9865",
        secondary_hover="#7ba572",
        
        # Backgrounds
        background_primary="#0f1b0d",
        background_secondary="#1a2e18",
        background_tertiary="#2a4a26",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#e8f2e5",
        text_secondary="#c8dfc2",
        text_tertiary="#a8cc9f",
        text_disabled="#4a5948",
        
        # Interactive
        interactive_normal="#1e3a1c",
        interactive_hover="#2d5128",
        interactive_active="#3c6835",
        interactive_disabled="#1a2e18",
        
        # Status
        status_success="#66bb6a",
        status_warning="#ff8f00",
        status_error="#e53935",
        status_info="#29b6f6",
        
        # Borders
        border_primary="#4a5948",
        border_secondary="#3c6835",
        border_focus="#4e7c47",
        separator="#2a4a26",
    )


def get_firefly_theme() -> ColorSystem:
    """Magical firefly theme with glowing yellow-green lights against deep night sky."""
    return ColorSystem(
        # Primary colors
        primary="#adff2f",
        primary_hover="#9aed1f",
        secondary="#c7ff58",
        secondary_hover="#b8f542",
        
        # Backgrounds
        background_primary="#080025",
        background_secondary="#15143d",
        background_tertiary="#242455",
        background_overlay="#000000dd",
        
        # Text
        text_primary="#fefdf2",
        text_secondary="#e8e6d3",
        text_tertiary="#d2cfb4",
        text_disabled="#4e4c66",
        
        # Interactive
        interactive_normal="#1e1d3a",
        interactive_hover="#2e2c51",
        interactive_active="#3e3b68",
        interactive_disabled="#15143d",
        
        # Status
        status_success="#adff2f",
        status_warning="#ffc107",
        status_error="#ff6b6b",
        status_info="#74c0fc",
        
        # Borders
        border_primary="#4e4c66",
        border_secondary="#3e3b68",
        border_focus="#adff2f",
        separator="#242455",
    )


def get_mintly_theme() -> ColorSystem:
    """Fresh minty green theme with cool mint accents."""
    return ColorSystem(
        # Primary colors
        primary="#26D0CE",
        primary_hover="#1fb3b1",
        secondary="#4ECDC4",
        secondary_hover="#3db8b0",
        
        # Backgrounds
        background_primary="#0a1717",
        background_secondary="#0f2a2a",
        background_tertiary="#1a4040",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#e0f7fa",
        text_secondary="#b2ebf2",
        text_tertiary="#80deea",
        text_disabled="#37474f",
        
        # Interactive
        interactive_normal="#004d40",
        interactive_hover="#00695c",
        interactive_active="#00796b",
        interactive_disabled="#0a1717",
        
        # Status
        status_success="#4caf50",
        status_warning="#ff9800",
        status_error="#f44336",
        status_info="#26D0CE",
        
        # Borders
        border_primary="#00695c",
        border_secondary="#004d40",
        border_focus="#26D0CE",
        separator="#1a4040",
    )


def get_ocean_theme() -> ColorSystem:
    """Deep ocean blues with aqua accents, calming and professional."""
    return ColorSystem(
        # Primary colors
        primary="#0EA5E9",
        primary_hover="#38BDF8",
        secondary="#06B6D4",
        secondary_hover="#22D3EE",
        
        # Backgrounds
        background_primary="#0C1222",
        background_secondary="#1E293B",
        background_tertiary="#334155",
        background_overlay="#0C1222dd",
        
        # Text
        text_primary="#F1F5F9",
        text_secondary="#CBD5E1",
        text_tertiary="#B4C6D3",
        text_disabled="#64748B",
        
        # Interactive
        interactive_normal="#1E293B",
        interactive_hover="#334155",
        interactive_active="#0EA5E9",
        interactive_disabled="#0F172A",
        
        # Status
        status_success="#059669",
        status_warning="#D97706",
        status_error="#EF4444",
        status_info="#0EA5E9",
        
        # Borders
        border_primary="#475569",
        border_secondary="#334155",
        border_focus="#0EA5E9",
        separator="#1E293B",
    )


def get_pulse_theme() -> ColorSystem:
    """Energetic purple/magenta theme with electric vibes."""
    return ColorSystem(
        # Primary colors
        primary="#8B5CF6",
        primary_hover="#7C3AED",
        secondary="#EC4899",
        secondary_hover="#DB2777",
        
        # Backgrounds
        background_primary="#0F0B1A",
        background_secondary="#1E1B3A",
        background_tertiary="#2D2A4A",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#F8F4FF",
        text_secondary="#E0D9FF",
        text_tertiary="#C8B9FF",
        text_disabled="#5A5570",
        
        # Interactive - enhanced visibility with transparency
        interactive_normal="rgba(139, 92, 246, 0.15)",  # Primary with low transparency
        interactive_hover="rgba(139, 92, 246, 0.25)",   # Primary with more transparency
        interactive_active="rgba(236, 72, 153, 0.3)",   # Secondary with transparency
        interactive_disabled="#1E1B3A",
        
        # Status
        status_success="#10B981",
        status_warning="#F59E0B",
        status_error="#EF4444",
        status_info="#3B82F6",
        
        # Borders
        border_primary="#5A5570",
        border_secondary="#4A4468",
        border_focus="#8B5CF6",
        separator="#2D2A4A",
    )


def get_solarized_light_theme() -> ColorSystem:
    """Light variant of the popular Solarized theme."""
    return ColorSystem(
        # Primary colors
        primary="#1565c0",
        primary_hover="#2AA198",
        secondary="#859900",
        secondary_hover="#B58900",
        
        # Backgrounds
        background_primary="#fdf6e3",
        background_secondary="#eee8d5",
        background_tertiary="#e3dcc6",
        background_overlay="#00000080",
        
        # Text
        text_primary="#073642",
        text_secondary="#586e75",
        text_tertiary="#405a63",
        text_disabled="#93a1a1",
        
        # Interactive
        interactive_normal="#d3d0c8",
        interactive_hover="#c8c5bd",
        interactive_active="#bdb9b1",
        interactive_disabled="#eee8d5",
        
        # Status
        status_success="#859900",
        status_warning="#B58900",
        status_error="#DC322F",
        status_info="#268BD2",
        
        # Borders
        border_primary="#93a1a1",
        border_secondary="#d3d0c8",
        border_focus="#268BD2",
        separator="#e3dcc6",
    )


def get_solarized_dark_theme() -> ColorSystem:
    """Dark variant of the popular Solarized theme."""
    return ColorSystem(
        # Primary colors
        primary="#42a5f5",
        primary_hover="#2AA198",
        secondary="#859900",
        secondary_hover="#B58900",
        
        # Backgrounds
        background_primary="#002b36",
        background_secondary="#073642",
        background_tertiary="#0e4853",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#b3c5c7",
        text_secondary="#93a1a1",
        text_tertiary="#839496",
        text_disabled="#073642",
        
        # Interactive - using Solarized base01/base1 for better button visibility
        interactive_normal="rgba(88, 110, 117, 0.3)",  # Solarized base01 with transparency
        interactive_hover="rgba(147, 161, 161, 0.4)",  # Solarized base1 with transparency
        interactive_active="rgba(42, 161, 152, 0.5)",  # Solarized cyan with transparency
        interactive_disabled="#073642",
        
        # Status
        status_success="#859900",
        status_warning="#B58900",
        status_error="#DC322F",
        status_info="#268BD2",
        
        # Borders
        border_primary="#586e75",
        border_secondary="#0e4853",
        border_focus="#268BD2",
        separator="#073642",
    )


def get_dracula_theme() -> ColorSystem:
    """Popular Dracula theme with purple accents."""
    return ColorSystem(
        # Primary colors
        primary="#bd93f9",
        primary_hover="#9580d4",
        secondary="#ff79c6",
        secondary_hover="#e066b3",
        
        # Backgrounds
        background_primary="#282a36",
        background_secondary="#44475a",
        background_tertiary="#6272a4",
        background_overlay="#000000cc",
        
        # Text
        text_primary="#f8f8f2",
        text_secondary="#e6e6e1",
        text_tertiary="#d4d4cf",
        text_disabled="#6272a4",
        
        # Interactive
        interactive_normal="#44475a",
        interactive_hover="#565869",
        interactive_active="#6272a4",
        interactive_disabled="#282a36",
        
        # Status
        status_success="#50fa7b",
        status_warning="#f1fa8c",
        status_error="#ff5555",
        status_info="#8be9fd",
        
        # Borders
        border_primary="#6272a4",
        border_secondary="#44475a",
        border_focus="#bd93f9",
        separator="#44475a",
    )


def get_openai_like_theme() -> ColorSystem:
    """OpenAI-inspired clean minimal theme with subtle grays."""
    return ColorSystem(
        # Primary colors - OpenAI uses very subtle, professional colors
        primary="#10a37f",  # OpenAI's green accent
        primary_hover="#0d8968",
        secondary="#6f7780",  # Muted gray
        secondary_hover="#5c646e",
        
        # Backgrounds - Very clean whites and light grays
        background_primary="#ffffff",
        background_secondary="#f7f7f8",
        background_tertiary="#ececf1",
        background_overlay="#00000020",
        
        # Text - Clean, readable grays
        text_primary="#2d333a",
        text_secondary="#6f7780",
        text_tertiary="#9ca3af",
        text_disabled="#d1d5db",
        
        # Interactive - Subtle, clean backgrounds
        interactive_normal="#f9fafb",
        interactive_hover="#f3f4f6",
        interactive_active="#e5e7eb",
        interactive_disabled="#f9fafb",
        
        # Status
        status_success="#10a37f",
        status_warning="#f59e0b",
        status_error="#ef4444",
        status_info="#3b82f6",
        
        # Borders
        border_primary="#d1d5db",
        border_secondary="#e5e7eb",
        border_focus="#10a37f",
        separator="#e5e7eb",
    )


def get_openui_like_theme() -> ColorSystem:
    """Open UI inspired theme with green accents and professional grays."""
    return ColorSystem(
        # Primary colors - Based on Open UI's green theme
        primary="#00a453",  # Open UI green
        primary_hover="#007a3d",
        secondary="#555555",
        secondary_hover="#444444",
        
        # Backgrounds
        background_primary="#ffffff",
        background_secondary="#f2f2f2",
        background_tertiary="#e8e8e8",
        background_overlay="#00000040",
        
        # Text
        text_primary="#333333",
        text_secondary="#555555",
        text_tertiary="#777777",
        text_disabled="#cccccc",
        
        # Interactive
        interactive_normal="#f8f9fa",
        interactive_hover="#e9ecef",
        interactive_active="#dee2e6",
        interactive_disabled="#f8f9fa",
        
        # Status
        status_success="#00a453",
        status_warning="#ff8800",
        status_error="#dc3545",
        status_info="#007a3d",
        
        # Borders
        border_primary="#cccccc",
        border_secondary="#e6e6e6",
        border_focus="#00a453",
        separator="#e6e6e6",
    )


def get_openwebui_like_theme() -> ColorSystem:
    """Open WebUI inspired dark theme with purple accents and chat-like design."""
    return ColorSystem(
        # Primary colors - OpenWebUI style with purple/violet accents
        primary="#8b5cf6",  # Violet primary (typical OpenWebUI accent)
        primary_hover="#7c3aed",
        secondary="#64748b",  # Slate gray
        secondary_hover="#475569",
        
        # Backgrounds - Very dark like modern chat apps
        background_primary="#0f0f0f",  # Almost black main background
        background_secondary="#1a1a1a",  # Dark sidebar/secondary areas
        background_tertiary="#262626",  # Slightly lighter for inputs/cards
        background_overlay="#00000090",
        
        # Text - High contrast for readability
        text_primary="#ffffff",  # Pure white for main text
        text_secondary="#e5e5e5",  # Light gray for secondary text
        text_tertiary="#a3a3a3",  # Medium gray for hints
        text_disabled="#737373",  # Darker gray for disabled
        
        # Interactive - Purple-tinted dark backgrounds
        interactive_normal="#2a2a2a",
        interactive_hover="#3a3a3a",
        interactive_active="#4a4a4a",
        interactive_disabled="#1a1a1a",
        
        # Status - Modern, vibrant colors
        status_success="#22c55e",  # Green
        status_warning="#f59e0b",  # Orange
        status_error="#ef4444",   # Red
        status_info="#8b5cf6",    # Violet (matches primary)
        
        # Borders - Subtle but visible
        border_primary="#404040",
        border_secondary="#2a2a2a",
        border_focus="#8b5cf6",
        separator="#2a2a2a",
    )