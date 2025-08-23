#!/usr/bin/env python3
"""
Test script to verify button contrast fix with opacity changes.
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

def test_contrast_fix():
    """Test the contrast fix with a few key themes."""
    print("🔧 Testing Button Contrast Fix for Opacity Issues")
    print("=" * 60)
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        
        theme_manager = get_theme_manager()
        theme_names = ['moonlight', 'openai_like', 'dark_mode', 'light_mode', 'forest']
        
        for theme_name in theme_names:
            if theme_name in theme_manager.get_available_themes():
                theme_manager.set_theme(theme_name)
                colors = theme_manager.current_theme
                
                print(f"\n🎨 Theme: {theme_name}")
                print("-" * 30)
                
                # Test OLD vs NEW approach
                old_titlebar_bg = colors.background_secondary  # Old incorrect reference
                new_titlebar_bg = colors.background_tertiary   # New correct reference (matches get_title_frame_style)
                
                # Button background (what the contrast calculation picks)
                button_bg = colors.interactive_normal
                
                old_contrast = calculate_contrast_ratio(button_bg, old_titlebar_bg)
                new_contrast = calculate_contrast_ratio(button_bg, new_titlebar_bg)
                
                print(f"Old titlebar reference: {old_titlebar_bg}")
                print(f"New titlebar reference: {new_titlebar_bg}")
                print(f"Button background:      {button_bg}")
                print(f"Old contrast ratio:     {old_contrast:.2f} {'✓' if old_contrast >= 3.0 else '✗'}")
                print(f"New contrast ratio:     {new_contrast:.2f} {'✓' if new_contrast >= 3.0 else '✗'}")
                
                improvement = ((new_contrast - old_contrast) / old_contrast * 100) if old_contrast > 0 else 0
                print(f"Improvement:            {improvement:+.1f}%")
        
        print(f"\n✅ Contrast fix verification complete!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    test_contrast_fix()