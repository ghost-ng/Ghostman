#!/usr/bin/env python3
"""
Test script to debug AI response handling in the REPL widget.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ghostman.src.presentation.widgets.repl_widget import REPLWidget

def test_response_handling():
    """Test AI response handling with mock responses."""
    print("=== Testing AI Response Handling ===\n")
    
    # Create QApplication for PyQt6 widgets
    app = QApplication(sys.argv)
    
    try:
        # Create REPL widget
        repl = REPLWidget()
        repl.show()
        
        print("1. Testing response handling with mock content...")
        
        # Test successful response
        print("   - Testing successful response...")
        repl._on_ai_response("This is a test AI response with markdown **bold** text.", True)
        
        # Test empty response
        print("   - Testing empty response...")
        repl._on_ai_response("", True)
        
        # Test null response
        print("   - Testing null response...")
        repl._on_ai_response(None, True)
        
        # Test error response
        print("   - Testing error response...")
        repl._on_ai_response("This is an error message", False)
        
        # Close after testing
        QTimer.singleShot(1000, app.quit)
        
        print("   - Running GUI test for 1 second...")
        app.exec()
        
    except Exception as e:
        print(f"❌ Error during response handling test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n=== Response Handling Test Complete ===")
    return True

if __name__ == "__main__":
    test_response_handling()