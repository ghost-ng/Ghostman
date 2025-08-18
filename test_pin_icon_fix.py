#!/usr/bin/env python3
"""
Test script to verify pin button icon loading
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

def test_pin_icon():
    """Test that pin button shows custom icon, not emoji."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    
    # Create a simple window to test the widget
    window = QMainWindow()
    window.setWindowTitle("Pin Icon Test")
    
    # Initialize theme manager
    theme_manager = get_theme_manager()
    
    # Create REPL widget (this will create the pin button)
    repl_widget = REPLWidget()
    window.setCentralWidget(repl_widget)
    
    # Show window
    window.show()
    window.resize(800, 600)
    
    def check_pin_button():
        """Check the pin button after UI is fully loaded."""
        if hasattr(repl_widget, 'pin_btn'):
            pin_btn = repl_widget.pin_btn
            
            print(f"🔍 Pin button text: '{pin_btn.text()}'")
            print(f"🔍 Pin button icon null: {pin_btn.icon().isNull()}")
            print(f"🔍 Pin button style: {pin_btn.toolButtonStyle()}")
            
            if pin_btn.text():
                print(f"❌ ERROR: Pin button has text content: '{pin_btn.text()}'")
            elif pin_btn.icon().isNull():
                print(f"❌ ERROR: Pin button has null icon")
            else:
                print(f"✅ SUCCESS: Pin button using icon (no text)")
        else:
            print("❌ ERROR: Pin button not found")
        
        # Exit after check
        QTimer.singleShot(100, app.quit)
    
    # Check after UI loads
    QTimer.singleShot(1000, check_pin_button)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_pin_icon()