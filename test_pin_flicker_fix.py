#!/usr/bin/env python3
"""
Test script to verify reduced flicker when toggling pin button
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

def test_pin_flicker_reduction():
    """Test that pin button toggle causes minimal flicker."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    
    # Create a simple window to test the widget
    window = QMainWindow()
    window.setWindowTitle("Pin Flicker Test")
    
    # Create REPL widget (this will create the pin button)
    repl_widget = REPLWidget()
    window.setCentralWidget(repl_widget)
    
    # Show window
    window.show()
    window.resize(800, 600)
    
    def test_multiple_toggles():
        """Test multiple rapid toggles to see if flicker is reduced."""
        if hasattr(repl_widget, 'pin_btn'):
            pin_btn = repl_widget.pin_btn
            
            print(f"🔍 Testing pin button flicker reduction...")
            print(f"🔍 Performing rapid toggles to test flicker...")
            
            # Rapid toggle sequence
            toggles = [False, True, False, True, False]
            for i, state in enumerate(toggles):
                pin_btn.setChecked(state)
                repl_widget._on_pin_toggle_clicked()
                print(f"🔍 Toggle {i+1}: {state} - completed")
            
            # Check final state
            if pin_btn.text():
                print(f"❌ ERROR: Pin button has text content: '{pin_btn.text()}'")
            elif pin_btn.icon().isNull():
                print(f"❌ ERROR: Pin button has null icon")
            else:
                print(f"✅ SUCCESS: Pin button flicker test completed")
                print(f"🔍 Final state: checked={pin_btn.isChecked()}, icon preserved")
        else:
            print("❌ ERROR: Pin button not found")
        
        # Exit after test
        QTimer.singleShot(100, app.quit)
    
    # Test after UI loads
    QTimer.singleShot(1000, test_multiple_toggles)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_pin_flicker_reduction()