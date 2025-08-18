#!/usr/bin/env python3
"""
Test script to verify pin button unified styling like move button
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

def test_pin_unified_styling():
    """Test that pin button uses unified styling like move button."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    
    # Create a simple window to test the widget
    window = QMainWindow()
    window.setWindowTitle("Pin Button Unified Styling Test")
    
    # Initialize theme manager
    theme_manager = get_theme_manager()
    
    # Create REPL widget (this will create the pin button)
    repl_widget = REPLWidget()
    window.setCentralWidget(repl_widget)
    
    # Show window
    window.show()
    window.resize(800, 600)
    
    def test_button_styling():
        """Test the pin button styling matches move button pattern."""
        if hasattr(repl_widget, 'pin_btn') and hasattr(repl_widget, 'move_btn'):
            pin_btn = repl_widget.pin_btn
            move_btn = repl_widget.move_btn
            
            print(f"🔍 Testing pin button unified styling...")
            print(f"🔍 Pin button text: '{pin_btn.text()}'")
            print(f"🔍 Pin button icon null: {pin_btn.icon().isNull()}")
            print(f"🔍 Pin button checked: {pin_btn.isChecked()}")
            
            # Test normal state
            pin_btn.setChecked(False)
            repl_widget._update_pin_button_state()
            print(f"🔍 Normal state - Pin button text after update: '{pin_btn.text()}'")
            
            # Test active state (should show amber like move button)
            pin_btn.setChecked(True)
            repl_widget._update_pin_button_state()
            print(f"🔍 Active state - Pin button text after update: '{pin_btn.text()}'")
            
            if pin_btn.text():
                print(f"❌ ERROR: Pin button has text content: '{pin_btn.text()}'")
            elif pin_btn.icon().isNull():
                print(f"❌ ERROR: Pin button has null icon")
            else:
                print(f"✅ SUCCESS: Pin button using unified styling with icon (no text)")
                
            print(f"🔍 Move button for comparison - text: '{move_btn.text()}', icon null: {move_btn.icon().isNull()}")
        else:
            print("❌ ERROR: Pin button or move button not found")
        
        # Exit after test
        QTimer.singleShot(100, app.quit)
    
    # Test after UI loads
    QTimer.singleShot(1000, test_button_styling)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_pin_unified_styling()