#!/usr/bin/env python3
"""
Analyze titlebar button contrast ratios across all Ghostman themes.
Identifies themes with poor contrast and calculates WCAG compliance.
"""

import sys
import os
from pathlib import Path

# Add the ghostman module to the path
ghostman_path = Path(__file__).parent / "ghostman" / "src"
sys.path.insert(0, str(ghostman_path))

try:
    # Simple color system simulation
    import re
    
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (128, 128, 128)  # fallback gray
    
    # Load themes manually from the preset_themes.py file
    preset_themes_path = Path(__file__).parent / "ghostman" / "src" / "ui" / "themes" / "preset_themes.py"
    themes_data = {}
    
    if preset_themes_path.exists():
        with open(preset_themes_path, 'r') as f:
            content = f.read()
            
        # Extract theme data using regex
        theme_pattern = r'def get_(\w+)_theme\(\).*?return ColorSystem\((.*?)\)'
        for match in re.finditer(theme_pattern, content, re.DOTALL):
            theme_name = match.group(1)
            theme_def = match.group(2)
            
            # Extract color values
            color_pattern = r'(\w+)="([^"]+)"'
            colors = {}
            for color_match in re.finditer(color_pattern, theme_def):
                color_name = color_match.group(1)
                color_value = color_match.group(2)
                colors[color_name] = color_value
            
            if colors:
                themes_data[theme_name] = colors
    
except Exception as e:
    print(f"Error setting up analysis: {e}")
    sys.exit(1)

def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    def get_luminance(color_hex: str) -> float:
        """Calculate relative luminance of a color."""
        r, g, b = hex_to_rgb(color_hex)
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        
        # Apply gamma correction
        r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
        g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
        b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    lum1 = get_luminance(color1_hex)
    lum2 = get_luminance(color2_hex)
    
    # Ensure lighter color is in numerator
    if lum1 < lum2:
        lum1, lum2 = lum2, lum1
    
    return (lum1 + 0.05) / (lum2 + 0.05)

def analyze_theme_contrast(theme_name: str, theme: dict):
    """Analyze titlebar button contrast for a specific theme."""
    print(f"\n=== {theme_name} ===")
    
    # Current titlebar button colors (from _style_title_button method)
    button_bg = theme.get('background_tertiary', '#333333')  # Current background
    button_text = theme.get('text_primary', '#ffffff')       # Current text color
    titlebar_bg = theme.get('background_secondary', '#222222')  # Titlebar background
    
    print(f"Titlebar background: {titlebar_bg}")
    print(f"Button background:   {button_bg}")
    print(f"Button text:         {button_text}")
    
    # Calculate key contrast ratios
    button_vs_titlebar = calculate_contrast_ratio(button_bg, titlebar_bg)
    text_vs_button = calculate_contrast_ratio(button_text, button_bg)
    
    print(f"Button vs Titlebar contrast: {button_vs_titlebar:.2f}")
    print(f"Text vs Button contrast:     {text_vs_button:.2f}")
    
    # WCAG compliance check
    button_visibility = "GOOD" if button_vs_titlebar >= 3.0 else "POOR"
    text_readability = "GOOD" if text_vs_button >= 4.5 else "POOR" if text_vs_button >= 3.0 else "FAIL"
    
    print(f"Button visibility: {button_visibility}")
    print(f"Text readability:  {text_readability}")
    
    # Overall assessment
    if button_vs_titlebar < 1.5:
        overall = "CRITICAL - Buttons nearly invisible"
    elif button_vs_titlebar < 3.0:
        overall = "POOR - Buttons hard to see"
    elif text_vs_button < 4.5:
        overall = "FAIR - Buttons visible but text may be hard to read"
    else:
        overall = "GOOD - Meets accessibility standards"
    
    print(f"Overall: {overall}")
    
    return {
        'theme_name': theme_name,
        'button_vs_titlebar': button_vs_titlebar,
        'text_vs_button': text_vs_button,
        'button_visibility': button_visibility,
        'text_readability': text_readability,
        'overall': overall,
        'colors': {
            'titlebar_bg': titlebar_bg,
            'button_bg': button_bg,
            'button_text': button_text
        }
    }

def suggest_better_colors(theme: dict) -> dict:
    """Suggest better color combinations for titlebar buttons."""
    # Try different background options
    candidates = [
        theme.get('interactive_normal', '#444444'),
        theme.get('interactive_hover', '#555555'), 
        theme.get('border_primary', '#666666'),
        theme.get('background_primary', '#111111'),
    ]
    
    best_contrast = 0
    best_bg = theme.get('background_tertiary', '#333333')
    
    for candidate in candidates:
        try:
            contrast = calculate_contrast_ratio(candidate, theme.get('background_secondary', '#222222'))
            if contrast > best_contrast:
                best_contrast = contrast
                best_bg = candidate
        except:
            continue
    
    return {
        'suggested_bg': best_bg,
        'contrast': best_contrast
    }

def main():
    print("Ghostman Titlebar Button Contrast Analysis")
    print("=" * 50)
    
    # Get all preset themes  
    themes = themes_data
    
    poor_contrast_themes = []
    analysis_results = []
    
    # Analyze each theme
    for theme_name, theme in themes.items():
        result = analyze_theme_contrast(theme_name, theme)
        analysis_results.append(result)
        
        if result['button_vs_titlebar'] < 3.0:
            poor_contrast_themes.append(theme_name)
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Total themes analyzed: {len(themes)}")
    print(f"Themes with poor button contrast: {len(poor_contrast_themes)}")
    
    if poor_contrast_themes:
        print(f"\nThemes needing improvement:")
        for theme_name in poor_contrast_themes:
            result = next(r for r in analysis_results if r['theme_name'] == theme_name)
            print(f"  - {theme_name}: {result['button_vs_titlebar']:.2f} contrast ratio")
    
    # Generate recommendations
    print(f"\n{'='*50}")
    print("RECOMMENDATIONS")
    print(f"{'='*50}")
    
    print("\nCurrent issue:")
    print("- Titlebar buttons use 'background_tertiary' which often matches titlebar background")
    print("- This makes buttons nearly invisible in many themes")
    
    print("\nRecommended fixes:")
    print("1. Use 'interactive_normal' with transparency for better distinction")
    print("2. Add border styling to create visual separation")
    print("3. Use hover/active colors that provide sufficient contrast")
    print("4. Consider theme-aware color selection based on contrast ratios")
    
    # Show worst offenders
    worst_themes = sorted(analysis_results, key=lambda x: x['button_vs_titlebar'])[:5]
    print(f"\nWorst contrast ratios (button vs titlebar):")
    for result in worst_themes:
        print(f"  {result['theme_name']}: {result['button_vs_titlebar']:.2f}")

if __name__ == "__main__":
    main()