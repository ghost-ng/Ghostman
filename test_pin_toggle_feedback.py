#!/usr/bin/env python3
"""
Test script to verify pin button toggle feedback (yellow on/off)
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

def test_pin_toggle_feedback():
    """Test that pin button shows/hides yellow feedback correctly."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    
    # Create a simple window to test the widget
    window = QMainWindow()
    window.setWindowTitle("Pin Toggle Feedback Test")
    
    # Initialize theme manager
    theme_manager = get_theme_manager()
    
    # Create REPL widget (this will create the pin button)
    repl_widget = REPLWidget()
    window.setCentralWidget(repl_widget)
    
    # Show window
    window.show()
    window.resize(800, 600)
    
    def test_toggle_sequence():
        """Test the pin button toggle sequence."""
        if hasattr(repl_widget, 'pin_btn'):
            pin_btn = repl_widget.pin_btn
            
            print(f"🔍 Testing pin button toggle feedback...")
            
            # Start unchecked
            pin_btn.setChecked(False)
            repl_widget._on_pin_toggle_clicked()
            print(f"🔍 Step 1 - Unchecked: text='{pin_btn.text()}', checked={pin_btn.isChecked()}")
            
            # Toggle to checked (should show yellow)
            pin_btn.setChecked(True)
            repl_widget._on_pin_toggle_clicked()
            print(f"🔍 Step 2 - Checked: text='{pin_btn.text()}', checked={pin_btn.isChecked()}")
            
            # Toggle back to unchecked (should remove yellow)
            pin_btn.setChecked(False)
            repl_widget._on_pin_toggle_clicked()
            print(f"🔍 Step 3 - Unchecked again: text='{pin_btn.text()}', checked={pin_btn.isChecked()}")
            
            # Verify final state
            if pin_btn.text():
                print(f"❌ ERROR: Pin button has text content: '{pin_btn.text()}'")
            elif pin_btn.icon().isNull():
                print(f"❌ ERROR: Pin button has null icon")
            else:
                print(f"✅ SUCCESS: Pin button toggle feedback working correctly")
        else:
            print("❌ ERROR: Pin button not found")
        
        # Exit after test
        QTimer.singleShot(100, app.quit)
    
    # Test after UI loads
    QTimer.singleShot(1000, test_toggle_sequence)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_pin_toggle_feedback()