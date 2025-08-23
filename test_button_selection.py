#!/usr/bin/env python3
"""
Test the button color selection logic directly.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ghostman.src.ui.themes.theme_manager import get_theme_manager

def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    try:
        from PyQt6.QtGui import QColor
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
        return 1.0

def test_button_selection():
    """Simulate the actual button color selection logic from _style_title_button."""
    print("🎯 Testing Button Color Selection Logic")
    print("=" * 60)
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        
        theme_manager = get_theme_manager()
        theme_manager.set_theme('moonlight')  # Test with moonlight theme
        colors = theme_manager.current_theme
        
        print(f"🎨 Testing with moonlight theme")
        print(f"titlebar background (background_tertiary): {colors.background_tertiary}")
        
        # Simulate the candidate selection logic
        titlebar_bg = colors.background_tertiary
        candidates = [
            colors.interactive_normal,    # Standard interactive background
            colors.border_primary,        # Border color (often good contrast)
            colors.background_primary,    # Primary background (darkest/lightest)
            colors.primary + "40",        # Primary with 25% opacity
            colors.secondary + "40",      # Secondary with 25% opacity
            "rgba(255, 255, 255, 0.15)", # Light semi-transparent for dark themes
            "rgba(0, 0, 0, 0.2)",        # Dark semi-transparent for light themes
        ]
        
        print(f"\nCandidate selection:")
        print("-" * 40)
        
        best_bg = colors.interactive_normal
        best_contrast = 0
        
        for i, candidate in enumerate(candidates):
            try:
                # For RGBA colors, extract RGB values for contrast calculation
                test_color = candidate
                if "rgba" in candidate.lower():
                    # Extract RGB values from rgba(r,g,b,a) format
                    rgba_parts = candidate.lower().replace("rgba(", "").replace(")", "").split(",")
                    if len(rgba_parts) >= 3:
                        r, g, b = int(rgba_parts[0].strip()), int(rgba_parts[1].strip()), int(rgba_parts[2].strip())
                        test_color = f"#{r:02x}{g:02x}{b:02x}"
                        print(f"{i+1}. {candidate} -> {test_color} for contrast calc")
                    else:
                        print(f"{i+1}. {candidate} -> [FAILED TO PARSE]")
                        continue
                else:
                    print(f"{i+1}. {candidate}")
                
                contrast = calculate_contrast_ratio(test_color, titlebar_bg)
                status = "🟢 GOOD" if contrast >= 3.0 else "🔴 POOR"
                
                print(f"    Contrast vs titlebar: {contrast:.2f} {status}")
                
                if contrast > best_contrast:
                    best_contrast = contrast
                    best_bg = candidate
                    print(f"    ⭐ NEW BEST CANDIDATE!")
                    
            except Exception as e:
                print(f"{i+1}. {candidate} -> ERROR: {e}")
                continue
        
        print(f"\n✅ Final selection:")
        print(f"Selected background: {best_bg}")
        print(f"Best contrast ratio: {best_contrast:.2f}")
        print(f"Meets WCAG minimum (3.0): {'✅ YES' if best_contrast >= 3.0 else '❌ NO'}")
        
        # Test if fallback logic would trigger
        if best_contrast < 3.0:
            print(f"\n🔧 Fallback logic would trigger (contrast < 3.0)")
            # Determine theme brightness
            from PyQt6.QtGui import QColor
            bg_color = QColor(colors.background_tertiary)
            luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
            theme_type = "dark" if luminance < 0.5 else "light"
            fallback_color = "rgba(255, 255, 255, 0.2)" if luminance < 0.5 else "rgba(0, 0, 0, 0.15)"
            print(f"Theme luminance: {luminance:.3f} -> {theme_type} theme")
            print(f"Fallback color: {fallback_color}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    test_button_selection()