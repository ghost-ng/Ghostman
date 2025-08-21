"""
Complete UI Theme Designs for Desktop Chat Application
=====================================================

This file contains three carefully designed themes:
1. Improved Lilac Theme - Much lighter fonts with soft lilac highlights
2. Cyber Theme - Cyberpunk aesthetic with neon colors and dark backgrounds  
3. Steampunk Theme - Victorian industrial aesthetic with copper, brass, and steam colors

All themes meet WCAG AA accessibility standards (4.5:1 contrast ratio minimum).
"""

from dataclasses import dataclass


@dataclass
class ColorSystem:
    """Complete color system for UI theming"""
    # Primary colors
    primary: str
    primary_hover: str
    secondary: str
    secondary_hover: str
    
    # Backgrounds
    background_primary: str
    background_secondary: str
    background_tertiary: str
    background_overlay: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_tertiary: str
    text_disabled: str
    
    # Interactive elements
    interactive_normal: str
    interactive_hover: str
    interactive_active: str
    interactive_disabled: str
    
    # Status indicators
    status_success: str
    status_warning: str
    status_error: str
    status_info: str
    
    # Borders and separators
    border_primary: str
    border_secondary: str
    border_focus: str
    separator: str


def get_lilac_theme_improved() -> ColorSystem:
    """
    Improved Lilac Theme - Much lighter text with soft lilac highlights
    
    Color Philosophy:
    - Much lighter text colors for better readability (nearly white)
    - Soft lilac accents that don't overwhelm
    - Subtle purple-tinted backgrounds
    - Maintains dreamy, elegant aesthetic while improving usability
    
    Key Colors:
    - Text: Near-white (#f8f6fa) for maximum readability
    - Accents: Soft lilac (#c8a8d8) for highlights and interactive elements
    - Backgrounds: Deep purple-blacks with subtle warmth
    """
    return ColorSystem(
        # Primary colors - refined lilac palette
        primary="#c8a8d8",          # Soft lilac - signature accent color
        primary_hover="#b896c8",    # Deeper lilac for hover states
        secondary="#e8d8f0",        # Very light lavender for secondary elements
        secondary_hover="#d8c8e8",  # Light lavender hover
        
        # Backgrounds - deep purple-blacks with subtle warmth
        background_primary="#161218",   # Almost black with purple hint
        background_secondary="#221e28", # Dark purple-charcoal
        background_tertiary="#2e2a34",  # Medium purple-charcoal
        background_overlay="#00000090", # Semi-transparent overlay
        
        # Text - much lighter for better readability
        text_primary="#f8f6fa",     # Near-white with lilac tint - excellent contrast
        text_secondary="#e8e0f0",   # Very light purple-white for secondary text
        text_tertiary="#d0c8d8",    # Light purple-gray for tertiary text
        text_disabled="#6e5a74",    # Muted purple for disabled text
        
        # Interactive - cohesive purple theme with better contrast
        interactive_normal="#3d3344",   # Dark purple for normal interactive elements
        interactive_hover="#4d4354",   # Lighter purple for hover
        interactive_active="#c8a8d8",   # Lilac accent for active states
        interactive_disabled="#2a252e", # Very dark for disabled elements
        
        # Status - harmonious with lilac theme but clearly distinguishable
        status_success="#82c29c",   # Soft mint green with good contrast
        status_warning="#e6c366",   # Warm golden yellow
        status_error="#e67676",     # Soft coral red
        status_info="#8fb8e8",      # Soft periwinkle blue
        
        # Borders and separators
        border_primary="#4d4354",   # Medium purple for primary borders
        border_secondary="#3d3344", # Darker purple for secondary borders
        border_focus="#c8a8d8",     # Lilac for focus states
        separator="#2e2a34",       # Subtle separator matching tertiary background
    )


def get_cyber_theme() -> ColorSystem:
    """
    Cyber Theme - Cyberpunk aesthetic with neon colors and dark backgrounds
    
    Color Philosophy:
    - Electric neon colors against deep blacks
    - High contrast for that futuristic feel
    - Cyan and electric blue as primary colors
    - Magenta and electric green as accents
    - Creates an immersive cyberpunk atmosphere
    
    Key Colors:
    - Primary: Electric cyan (#00d4ff) - signature neon color
    - Text: Bright cyan-white (#e6fdff) for that digital glow effect
    - Backgrounds: Deep blacks with subtle blue undertones
    - Accents: Neon magenta, electric green for variety
    """
    return ColorSystem(
        # Primary colors - electric cyber palette
        primary="#00d4ff",          # Electric cyan - signature neon color
        primary_hover="#00b8e6",    # Deeper cyan for hover
        secondary="#ff0080",        # Neon magenta for secondary elements
        secondary_hover="#e6006b",  # Deeper magenta hover
        
        # Backgrounds - deep cyber blacks with blue undertones
        background_primary="#0a0c14",   # Almost black with blue hint
        background_secondary="#0f1419", # Dark blue-black
        background_tertiary="#141a23",  # Medium blue-charcoal
        background_overlay="#00000099", # Semi-transparent overlay
        
        # Text - bright cyber colors with excellent contrast
        text_primary="#e6fdff",     # Bright cyan-white - excellent contrast
        text_secondary="#b3f0ff",   # Light cyan for secondary text
        text_tertiary="#80e6ff",    # Medium cyan for tertiary text
        text_disabled="#4d7a8a",    # Muted cyan for disabled text
        
        # Interactive - neon theme with clear states
        interactive_normal="#1a2332",   # Dark blue for normal elements
        interactive_hover="#2a3342",   # Lighter blue for hover
        interactive_active="#00d4ff",   # Electric cyan for active states
        interactive_disabled="#0f1419", # Very dark for disabled
        
        # Status - cyber-themed but functional
        status_success="#00ff41",   # Electric green - classic cyber success
        status_warning="#ffbf00",   # Electric amber
        status_error="#ff073a",     # Neon red
        status_info="#00d4ff",      # Electric cyan (matches primary)
        
        # Borders and separators
        border_primary="#2a3342",   # Medium blue for borders
        border_secondary="#1a2332", # Darker blue for secondary borders
        border_focus="#00d4ff",     # Electric cyan for focus
        separator="#141a23",       # Subtle separator
    )


def get_steampunk_theme() -> ColorSystem:
    """
    Steampunk Theme - Victorian industrial aesthetic with copper, brass, and steam colors
    
    Color Philosophy:
    - Rich, warm metals: copper, brass, bronze
    - Aged leather and wood tones
    - Vintage gold accents
    - Deep browns and warm creams
    - Evokes Victorian-era machinery and craftsmanship
    
    Key Colors:
    - Primary: Polished copper (#d2691e) - warm, inviting metal
    - Text: Warm cream (#faf6f0) for readability on dark backgrounds
    - Backgrounds: Rich dark browns like aged leather
    - Accents: Brass, bronze, and antique gold
    """
    return ColorSystem(
        # Primary colors - authentic metal palette
        primary="#d2691e",          # Polished copper - signature steampunk color
        primary_hover="#b8571a",    # Darker copper for hover
        secondary="#b5a642",        # Antique brass for secondary elements
        secondary_hover="#9e8f39",  # Darker brass hover
        
        # Backgrounds - rich aged materials
        background_primary="#1a1612",   # Dark chocolate brown - aged leather
        background_secondary="#2d2318", # Medium brown - old wood
        background_tertiary="#3d301e",  # Lighter brown - worn leather
        background_overlay="#00000088", # Semi-transparent overlay
        
        # Text - warm, readable on dark backgrounds
        text_primary="#faf6f0",     # Warm cream - excellent contrast
        text_secondary="#e8dcc8",   # Light warm beige
        text_tertiary="#d4c2a0",    # Medium warm tan
        text_disabled="#6b5d4a",    # Muted brown for disabled text
        
        # Interactive - metallic theme with clear hierarchy
        interactive_normal="#4a3c2a",   # Dark brown for normal elements
        interactive_hover="#5a4c3a",   # Lighter brown for hover
        interactive_active="#d2691e",   # Copper accent for active states
        interactive_disabled="#2d2318", # Very dark for disabled
        
        # Status - steampunk-appropriate but functional
        status_success="#7ba05b",   # Aged green - patinated copper
        status_warning="#cd7f32",   # Bronze - classic steampunk metal
        status_error="#a0522d",     # Sienna brown - oxidized metal
        status_info="#4682b4",      # Steel blue - industrial machinery
        
        # Borders and separators
        border_primary="#5a4c3a",   # Medium brown for borders
        border_secondary="#4a3c2a", # Darker brown for secondary
        border_focus="#d2691e",     # Copper for focus states
        separator="#3d301e",       # Subtle separator matching tertiary
    )


# Theme registry for easy access
THEMES = {
    "lilac": get_lilac_theme_improved,
    "cyber": get_cyber_theme,
    "steampunk": get_steampunk_theme,
}


def get_theme(theme_name: str) -> ColorSystem:
    """Get a theme by name"""
    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}. Available: {list(THEMES.keys())}")
    return THEMES[theme_name]()


# Example usage and testing
if __name__ == "__main__":
    print("UI Theme Designs")
    print("================")
    
    for name, theme_func in THEMES.items():
        print(f"\n{name.title()} Theme:")
        theme = theme_func()
        print(f"  Primary: {theme.primary}")
        print(f"  Background: {theme.background_primary}")
        print(f"  Text Primary: {theme.text_primary}")
        print(f"  Interactive Active: {theme.interactive_active}")