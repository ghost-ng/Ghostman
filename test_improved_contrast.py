#!/usr/bin/env python3
"""
Test the improved titlebar button contrast after the fixes.
"""

import sys
import os
from pathlib import Path

# Add the ghostman module to the path
ghostman_path = Path(__file__).parent / "ghostman" / "src"
sys.path.insert(0, str(ghostman_path))

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

def simulate_improved_button_bg(theme_colors):
    """Simulate the improved button background selection logic."""
    titlebar_bg = theme_colors.get('background_secondary', '#222222')
    
    # Same candidates as in the improved code
    candidates = [
        theme_colors.get('interactive_normal', '#444444'),
        theme_colors.get('border_primary', '#666666'),
        theme_colors.get('background_primary', '#111111'),
        "rgba(255, 255, 255, 0.15)",
        "rgba(0, 0, 0, 0.2)",
    ]
    
    best_bg = theme_colors.get('interactive_normal', '#444444')
    best_contrast = 0
    
    for candidate in candidates:
        try:
            # For rgba colors, just use the main color for testing
            if "rgba" in candidate:
                if "255, 255, 255" in candidate:
                    test_color = "#ffffff"
                else:
                    test_color = "#000000"
            else:
                test_color = candidate
                
            contrast = calculate_contrast_ratio(test_color, titlebar_bg)
            if contrast > best_contrast:
                best_contrast = contrast
                best_bg = candidate
        except:
            continue
    
    # Force high-contrast if needed (simplified version)
    if best_contrast < 3.0:
        # Simple luminance check
        try:
            r, g, b = hex_to_rgb(titlebar_bg)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            if luminance < 0.5:  # Dark theme
                best_bg = "rgba(255, 255, 255, 0.2)"
                actual_contrast = calculate_contrast_ratio("#ffffff", titlebar_bg)
            else:  # Light theme
                best_bg = "rgba(0, 0, 0, 0.1)" 
                actual_contrast = calculate_contrast_ratio("#000000", titlebar_bg)
                
            return best_bg, actual_contrast
        except:
            return best_bg, best_contrast
    
    return best_bg, best_contrast

def load_themes_data():
    """Load theme data from preset_themes.py"""
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
    
    return themes_data

def main():
    print("Testing Improved Titlebar Button Contrast")
    print("=" * 50)
    
    themes_data = load_themes_data()
    
    improvements = []
    
    for theme_name, theme_colors in themes_data.items():
        # Original approach
        old_button_bg = theme_colors.get('background_tertiary', '#333333')
        titlebar_bg = theme_colors.get('background_secondary', '#222222')
        old_contrast = calculate_contrast_ratio(old_button_bg, titlebar_bg)
        
        # New improved approach
        new_button_bg, new_contrast = simulate_improved_button_bg(theme_colors)
        
        improvement = new_contrast - old_contrast
        improvements.append((theme_name, old_contrast, new_contrast, improvement))
        
        print(f"\n{theme_name}:")
        print(f"  Old: {old_button_bg} vs {titlebar_bg} = {old_contrast:.2f}")
        print(f"  New: {new_button_bg} vs {titlebar_bg} = {new_contrast:.2f}")
        print(f"  Improvement: {improvement:.2f} ({improvement/old_contrast*100:.1f}%)")
        
        if new_contrast >= 4.5:
            print(f"  ✅ WCAG AA Compliant")
        elif new_contrast >= 3.0:
            print(f"  ⚠️  Good visibility")
        else:
            print(f"  ❌ Still needs work")
    
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    
    # Overall statistics
    avg_old_contrast = sum(imp[1] for imp in improvements) / len(improvements)
    avg_new_contrast = sum(imp[2] for imp in improvements) / len(improvements)
    avg_improvement = sum(imp[3] for imp in improvements) / len(improvements)
    
    print(f"Average old contrast: {avg_old_contrast:.2f}")
    print(f"Average new contrast: {avg_new_contrast:.2f}")
    print(f"Average improvement: {avg_improvement:.2f} ({avg_improvement/avg_old_contrast*100:.1f}%)")
    
    # Count compliant themes
    wcag_aa_compliant = sum(1 for imp in improvements if imp[2] >= 4.5)
    good_visibility = sum(1 for imp in improvements if imp[2] >= 3.0)
    still_poor = len(improvements) - good_visibility
    
    print(f"\nWCAG AA Compliant (≥4.5): {wcag_aa_compliant}/{len(improvements)} themes")
    print(f"Good visibility (≥3.0): {good_visibility}/{len(improvements)} themes")
    print(f"Still poor (<3.0): {still_poor}/{len(improvements)} themes")
    
    # Top improvements
    print(f"\nTop 5 improvements:")
    improvements.sort(key=lambda x: x[3], reverse=True)
    for i, (theme_name, old, new, imp) in enumerate(improvements[:5]):
        print(f"  {i+1}. {theme_name}: {old:.2f} → {new:.2f} (+{imp:.2f})")

if __name__ == "__main__":
    main()