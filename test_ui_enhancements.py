#!/usr/bin/env python3
"""
Test script to verify UI enhancements for divider and spinner functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ghostman.src.presentation.widgets.repl_widget import REPLWidget

def test_ui_enhancements():
    """Test the UI enhancements: divider and spinner."""
    print("=== Testing UI Enhancements ===\n")
    
    # Create QApplication for PyQt6 widgets
    app = QApplication(sys.argv)
    
    try:
        # Create REPL widget
        repl = REPLWidget()
        repl.show()
        
        print("1. Testing divider and spinner functionality...")
        
        # Test divider display
        print("   - Adding divider to output...")
        repl.append_output("--------------------------------------------------", "divider")
        repl.append_output(">>> test command", "input")
        
        # Test spinner activation
        print("   - Activating spinner mode...")
        repl._set_processing_mode(True)
        
        # Create timer to test spinner animation for a few seconds
        def test_spinner_animation():
            print("   - Spinner should be animating...")
            
            # After 3 seconds, restore normal mode
            QTimer.singleShot(3000, lambda: repl._set_processing_mode(False))
            QTimer.singleShot(3100, lambda: print("   - Spinner restored to normal prompt"))
            QTimer.singleShot(3200, lambda: app.quit())
        
        QTimer.singleShot(1000, test_spinner_animation)
        
        print("   - Starting GUI test (will run for ~4 seconds)...")
        app.exec()
        
        print("\n2. Testing color scheme update...")
        # Test that divider color is available
        if hasattr(repl, '_markdown_renderer'):
            renderer = repl._markdown_renderer
            divider_color = renderer.color_scheme.get('divider', None)
            if divider_color:
                print(f"   ✅ Divider color configured: {divider_color}")
            else:
                print("   ❌ Divider color not found in color scheme")
        
        print("\n3. Testing prompt label functionality...")
        # Test prompt label exists and has correct properties
        if hasattr(repl, 'prompt_label'):
            prompt_text = repl.prompt_label.text()
            print(f"   ✅ Prompt label accessible with text: '{prompt_text}'")
        else:
            print("   ❌ Prompt label not accessible")
        
    except Exception as e:
        print(f"❌ Error during UI enhancement test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n=== UI Enhancement Test Complete ===")
    return True

if __name__ == "__main__":
    test_ui_enhancements()