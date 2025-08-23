#!/usr/bin/env python3
"""
Debug the actual button styling that gets applied.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def debug_button_styling():
    """Debug the actual colors being applied to buttons."""
    print("🔍 Debugging Button Styling")
    print("=" * 60)
    
    try:
        from PyQt6.QtWidgets import QApplication, QToolButton
        app = QApplication([])
        
        from ghostman.src.ui.themes.theme_manager import get_theme_manager
        from ghostman.src.presentation.widgets.repl_widget import REPLWidget
        
        # Create theme manager and set theme
        theme_manager = get_theme_manager()
        theme_manager.set_theme('moonlight')
        colors = theme_manager.current_theme
        
        print(f"🎨 Theme: moonlight")
        print(f"background_tertiary: {colors.background_tertiary}")
        print(f"interactive_normal: {colors.interactive_normal}")
        
        # Create a dummy REPL widget to test button styling
        widget = REPLWidget()
        
        # Create a test button
        test_button = QToolButton()
        
        # Apply the _style_title_button method
        widget._style_title_button(test_button)
        
        # Get the applied stylesheet
        stylesheet = test_button.styleSheet()
        print(f"\n📝 Applied stylesheet:")
        print("-" * 40)
        print(stylesheet)
        
        # Look for rgba values in the stylesheet
        import re
        rgba_matches = re.findall(r'rgba\([^)]+\)', stylesheet)
        hex_matches = re.findall(r'#[0-9a-fA-F]{6}', stylesheet)
        
        print(f"\n🎯 Color values found:")
        print("-" * 40)
        if rgba_matches:
            for match in rgba_matches:
                print(f"RGBA color: {match}")
        if hex_matches:
            for match in hex_matches:
                print(f"Hex color: {match}")
                
        if not rgba_matches and not hex_matches:
            print("❌ No color values found in stylesheet!")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_button_styling()