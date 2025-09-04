"""
Preset Themes for Ghostman Application.

This module is now deprecated. All built-in themes are loaded from JSON files
in the 'json' subdirectory for better maintainability and modularity.

The theme manager auto-discovers all themes from:
- ghostman/src/ui/themes/json/ (built-in themes)
- User data directory/themes/ (custom themes)
"""

from typing import Dict
from .color_system import ColorSystem


def get_preset_themes() -> Dict[str, ColorSystem]:
    """
    Legacy function for backward compatibility.
    
    Returns an empty dict as themes are now loaded from JSON files.
    This function is kept to avoid breaking imports in other modules.
    
    Returns:
        Empty dictionary (themes are loaded from JSON now)
    """
    return {}


# The following theme functions are kept as stubs for backward compatibility
# but they all return None since themes are loaded from JSON files now

def get_dark_matrix_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_midnight_blue_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_forest_green_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_sunset_orange_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_royal_purple_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_arctic_white_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_cyberpunk_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_earth_tones_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_ocean_deep_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_lilac_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_sunburst_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_forest_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_firefly_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_mintly_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_ocean_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_pulse_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_solarized_light_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_solarized_dark_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_dracula_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_openai_like_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_openui_like_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_openwebui_like_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_moonlight_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_fireswamp_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_cyber_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_steampunk_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_winter_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_birthday_cake_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_dawn_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_dusk_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_jade_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_gryffindor_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_hufflepuff_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_slytherin_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_ravenclaw_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_sith_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_jedi_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_republic_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None

def get_empire_theme() -> ColorSystem:
    """Deprecated - loaded from JSON."""
    return None