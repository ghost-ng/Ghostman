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
        "moonlight": get_moonlight_theme(),
        "fireswamp": get_fireswamp_theme(),
        "cyber": get_cyber_theme(),
        "steampunk": get_steampunk_theme(),
    }



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
    """Soft lilac purple theme with much lighter text and lilac highlights."""
    return ColorSystem(
        # Primary colors - soft lilac and lavender
        primary="#c8a8d8",  # Soft lilac
        primary_hover="#b896c8",  # Slightly darker lilac
        secondary="#d8c8e8",  # Very light lavender
        secondary_hover="#c8b8d8",  # Light lavender
        
        # Backgrounds - very dark with subtle purple tints
        background_primary="#1a1520",  # Very dark purple-black
        background_secondary="#2a2030",  # Dark purple-gray
        background_tertiary="#3a3040",  # Medium purple-gray
        background_overlay="#00000080",
        
        # Text - much lighter for better readability
        text_primary="#f8f6fa",  # Near-white with slight purple tint
        text_secondary="#e8e0f0",  # Very light purple-white
        text_tertiary="#d0c8d8",  # Light purple-gray
        text_disabled="#605860",  # Dark purple-gray
        
        # Interactive - cohesive purple theme
        interactive_normal="#4a3050",  # Dark purple
        interactive_hover="#5a4060",  # Medium purple
        interactive_active="#c8a8d8",  # Lilac accent
        interactive_disabled="#2a2030",
        
        # Status - purple-tinted variants
        status_success="#8fb996",  # Soft mint green
        status_warning="#d4b06a",  # Warm gold
        status_error="#d67b7b",   # Soft red
        status_info="#a8c8d8",    # Soft blue
        
        # Borders
        border_primary="#5a4060",
        border_secondary="#3a3040", 
        border_focus="#c8a8d8",  # Lilac highlight
        separator="#3a3040",
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
        
        # Text - improved contrast for readability
        text_primary="#073642",
        text_secondary="#2c5866",  # Darker for better contrast against light bg
        text_tertiary="#405a63",
        text_disabled="#93a1a1",
        
        # Interactive - Enhanced hover distinction
        interactive_normal="#d3d0c8",
        interactive_hover="#b8b5ad",  # More distinct hover
        interactive_active="#a3a09a",  # More distinct active
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
        
        # Text - improved contrast for REPL readability
        text_primary="#b3c5c7",
        text_secondary="#c5d7d9",  # Lighter for better contrast
        text_tertiary="#839496",
        text_disabled="#073642",
        
        # Interactive - using Solarized base01/base1 for better button visibility
        interactive_normal="rgba(147, 161, 161, 0.4)",  # Solarized base1 with transparency
        interactive_hover="rgba(88, 110, 117, 0.3)",  # Solarized base01 with transparency
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
        
        # Text - improved contrast for REPL messages
        text_primary="#f8f8f2",
        text_secondary="#f0f0ea",  # Lighter for better contrast against #6272a4 bg
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
    """OpenAI-inspired clean theme with enhanced accessibility compliance."""
    return ColorSystem(
        # Primary colors - Enhanced distinction and accessibility
        primary="#0d8a68",           # Darker green for better contrast
        primary_hover="#0a6b52",     # More distinct hover
        secondary="#4a5568",         # Darker gray for better contrast
        secondary_hover="#2d3748",   # Much more distinct hover
        
        # Backgrounds - Very clean whites and light grays
        background_primary="#ffffff",
        background_secondary="#f7f7f8",
        background_tertiary="#ececf1",
        background_overlay="#00000020",
        
        # Text - Enhanced contrast for accessibility
        text_primary="#1a202c",      # Much darker for better contrast
        text_secondary="#2d3748",    # Darker secondary text
        text_tertiary="#4a5568",     # Darker tertiary text
        text_disabled="#a0aec0",     # Lighter disabled text
        
        # Interactive - More distinct hover states
        interactive_normal="#f7fafc",    # Slightly more tinted
        interactive_hover="#edf2f7",     # More distinct hover
        interactive_active="#cbd5e0",    # Much more distinct active
        interactive_disabled="#f7fafc",
        
        # Status - Enhanced distinction and accessibility
        status_success="#198754",    # Darker green for better contrast
        status_warning="#d97706",    # Amber/orange for better contrast than yellow
        status_error="#dc3545",      # Distinct red
        status_info="#0d6efd",       # Bright blue, distinct from others
        
        # Borders
        border_primary="#d1d5db",
        border_secondary="#e5e7eb",
        border_focus="#0d8a68",      # Updated to match new primary
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
    """OpenWebUI inspired dark theme with authentic chat interface design."""
    return ColorSystem(
        # Primary colors - Modern blue accent (typical OpenWebUI style)
        primary="#3b82f6",  # Blue primary (more typical for OpenWebUI)
        primary_hover="#2563eb",  # Darker blue on hover
        secondary="#6b7280",  # Neutral gray
        secondary_hover="#4b5563",  # Darker gray
        
        # Backgrounds - Modern dark chat interface
        background_primary="#111827",  # Dark gray (not pure black)
        background_secondary="#1f2937",  # Slightly lighter sidebar
        background_tertiary="#374151",  # Input/card backgrounds
        background_overlay="#00000080",  # Semi-transparent overlay
        
        # Text - Optimized for chat readability
        text_primary="#f9fafb",  # Near white for main text
        text_secondary="#d1d5db",  # Light gray for secondary
        text_tertiary="#9ca3af",  # Medium gray for placeholders
        text_disabled="#6b7280",  # Muted gray for disabled
        
        # Interactive - Subtle and modern
        interactive_normal="#374151",  # Neutral dark gray
        interactive_hover="#4b5563",  # Slightly lighter on hover
        interactive_active="#3b82f6",  # Blue accent for active states
        interactive_disabled="#1f2937",  # Very dark for disabled
        
        # Status - Clean and professional
        status_success="#10b981",  # Emerald green
        status_warning="#f59e0b",  # Amber
        status_error="#ef4444",   # Red
        status_info="#3b82f6",    # Blue (matches primary)
        
        # Borders - Subtle contrast
        border_primary="#4b5563",  # Medium gray border
        border_secondary="#374151",  # Darker border
        border_focus="#3b82f6",  # Blue focus border
        separator="#374151",  # Separator lines
    )


def get_moonlight_theme() -> ColorSystem:
    """Elegant moonlight theme with dark blues, purples, and silver accents."""
    return ColorSystem(
        # Primary colors - Cool moonlight blues and purples
        primary="#7dd3fc",  # Light sky blue (moonbeam)
        primary_hover="#38bdf8",  # Slightly deeper blue
        secondary="#c084fc",  # Light purple (moon glow)
        secondary_hover="#a855f7",  # Deeper purple
        
        # Backgrounds - Deep night blues with subtle purple tints
        background_primary="#0f1419",  # Very deep blue-black
        background_secondary="#1e293b",  # Slate blue
        background_tertiary="#334155",  # Lighter slate
        background_overlay="#0f141980",  # Semi-transparent deep blue
        
        # Text - Silver and light blue tones
        text_primary="#f1f5f9",  # Bright silver-white
        text_secondary="#cbd5e1",  # Light silver-blue
        text_tertiary="#b8bcc8",  # Medium silver-blue (improved contrast)
        text_disabled="#64748b",  # Muted slate
        
        # Interactive - Subtle blues with moonlight glow
        interactive_normal="#1e293b",  # Dark slate
        interactive_hover="#334155",  # Medium slate
        interactive_active="#475569",  # Light slate
        interactive_disabled="#0f1419",  # Very dark
        
        # Status - Cool tones matching the moonlight theme
        status_success="#22d3ee",  # Cyan (cool success)
        status_warning="#fbbf24",  # Warm amber (contrast)
        status_error="#f87171",  # Soft red
        status_info="#7dd3fc",  # Light blue (matches primary)
        
        # Borders - Subtle silver-blue tones
        border_primary="#475569",  # Medium slate
        border_secondary="#334155",  # Dark slate
        border_focus="#7dd3fc",  # Light blue focus
        separator="#1e293b",  # Dark separator
    )


def get_fireswamp_theme() -> ColorSystem:
    """Warm fireswamp theme with earthy oranges, reds, and browns inspired by fantasy."""
    return ColorSystem(
        # Primary colors - Warm fire and ember tones
        primary="#f97316",  # Bright orange (flame)
        primary_hover="#ea580c",  # Deeper orange
        secondary="#dc2626",  # Rich red (ember)
        secondary_hover="#b91c1c",  # Deep red
        
        # Backgrounds - Deep earth and shadow tones
        background_primary="#1c1917",  # Very dark brown (rich earth)
        background_secondary="#292524",  # Dark brown
        background_tertiary="#44403c",  # Medium brown
        background_overlay="#1c191780",  # Semi-transparent dark brown
        
        # Text - Warm light tones like firelight
        text_primary="#fef7ed",  # Warm white (firelight)
        text_secondary="#fed7aa",  # Light orange (warm glow)
        text_tertiary="#fdba74",  # Medium orange
        text_disabled="#78716c",  # Muted brown
        
        # Interactive - Warm earth tones with fire accents
        interactive_normal="#44403c",  # Medium brown
        interactive_hover="#57534e",  # Lighter brown
        interactive_active="#6b7280",  # Gray-brown (ash)
        interactive_disabled="#292524",  # Dark brown
        
        # Status - Warm earthy status colors
        status_success="#65a30d",  # Forest green (nature)
        status_warning="#f59e0b",  # Amber (warm warning)
        status_error="#dc2626",  # Red (matches secondary)
        status_info="#2563eb",  # Blue (cool contrast)
        
        # Borders - Earthy brown tones
        border_primary="#78716c",  # Light brown
        border_secondary="#57534e",  # Medium brown
        border_focus="#f97316",  # Orange focus (matches primary)
        separator="#44403c",  # Dark brown separator
    )


def get_cyber_theme() -> ColorSystem:
    """Cyberpunk theme with neon colors and digital aesthetic."""
    return ColorSystem(
        # Primary colors - electric cyan and neon magenta
        primary="#00d4ff",  # Electric cyan
        primary_hover="#00b8e6",  # Darker cyan
        secondary="#ff0080",  # Neon magenta
        secondary_hover="#e6006b",  # Darker magenta
        
        # Backgrounds - deep blacks with blue undertones
        background_primary="#0a0a0f",  # Deep black with blue hint
        background_secondary="#141420",  # Dark blue-black
        background_tertiary="#1e1e30",  # Medium blue-black
        background_overlay="#000000d0",  # Dark overlay
        
        # Text - bright cyan-white for digital glow
        text_primary="#e6fdff",  # Bright cyan-white
        text_secondary="#b3f0ff",  # Light cyan
        text_tertiary="#80e6ff",  # Medium cyan
        text_disabled="#334d66",  # Dark blue-gray
        
        # Interactive - cyberpunk button states
        interactive_normal="#1a2332",  # Dark blue-gray
        interactive_hover="#2d3a4f",  # Medium blue-gray
        interactive_active="#00d4ff",  # Electric cyan active
        interactive_disabled="#0f1419",  # Very dark
        
        # Status - neon accent colors
        status_success="#00ff41",  # Electric green
        status_warning="#ffbf00",  # Electric amber
        status_error="#ff2d6d",   # Electric red
        status_info="#00d4ff",    # Electric cyan
        
        # Borders - neon blue tones
        border_primary="#004d66",  # Dark cyan
        border_secondary="#1a2332",  # Dark blue-gray
        border_focus="#00d4ff",  # Electric cyan focus
        separator="#1a2332",  # Dark separator
    )


def get_steampunk_theme() -> ColorSystem:
    """Victorian industrial steampunk theme with copper and brass tones."""
    return ColorSystem(
        # Primary colors - polished copper and antique brass
        primary="#d2691e",  # Polished copper
        primary_hover="#b8550c",  # Darker copper
        secondary="#b5a642",  # Antique brass
        secondary_hover="#9c8f38",  # Darker brass
        
        # Backgrounds - aged leather and dark wood
        background_primary="#1a1612",  # Dark aged leather
        background_secondary="#2a211a",  # Medium brown leather
        background_tertiary="#3d2f22",  # Light brown leather
        background_overlay="#00000099",  # Warm dark overlay
        
        # Text - warm cream and aged paper
        text_primary="#faf6f0",  # Warm cream
        text_secondary="#e6d7c3",  # Aged paper
        text_tertiary="#d4c0a1",  # Old parchment
        text_disabled="#5c4a38",  # Dark brown
        
        # Interactive - aged metal states
        interactive_normal="#4a3b2a",  # Dark aged bronze
        interactive_hover="#5c4833",  # Medium bronze
        interactive_active="#d2691e",  # Copper active
        interactive_disabled="#2a211a",  # Very dark brown
        
        # Status - vintage industrial colors
        status_success="#6b8e23",  # Olive green (oxidized copper)
        status_warning="#daa520",  # Goldenrod (polished brass)
        status_error="#b22222",   # Fire brick red
        status_info="#4682b4",    # Steel blue
        
        # Borders - oxidized metal tones
        border_primary="#8b6914",  # Dark brass
        border_secondary="#4a3b2a",  # Dark bronze
        border_focus="#d2691e",  # Copper focus
        separator="#3d2f22",  # Dark brown separator
    )