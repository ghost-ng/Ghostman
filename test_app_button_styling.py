#!/usr/bin/env python3
"""
Test button styling in the actual app startup sequence.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def test_app_button_styling():
    """Test button styling in real app context."""
    print("🔍 Testing App Button Styling")
    print("=" * 60)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        app = QApplication([])
        
        from ghostman.src.ui.themes.theme_manager import get_theme_manager
        from ghostman.src.presentation.widgets.repl_widget import REPLWidget
        
        # Set up theme like the real app does
        theme_manager = get_theme_manager()
        theme_manager.set_theme('moonlight')
        
        # Create REPL widget like the real app does
        print("📝 Creating REPL widget...")
        repl = REPLWidget()
        
        # Give it a moment to fully initialize
        def check_button_styling():
            print("🔍 Checking title button styling...")
            
            # Check the help button as an example
            if hasattr(repl, 'title_help_btn'):
                stylesheet = repl.title_help_btn.styleSheet()
                print(f"Help button stylesheet:")
                print("-" * 40)
                print(stylesheet[:500] + "..." if len(stylesheet) > 500 else stylesheet)
                
                # Look for high-contrast rgba colors
                if "rgba(255, 255, 255, 0.15)" in stylesheet:
                    print("\n✅ HIGH-CONTRAST STYLING FOUND!")
                    print("The contrast fix IS being applied correctly.")
                elif "#1e293b" in stylesheet or "#334155" in stylesheet:
                    print("\n❌ STANDARD THEME STYLING FOUND")
                    print("The contrast fix is being overridden somewhere.")
                else:
                    print("\n❓ UNKNOWN STYLING")
                    print("Could not identify the styling pattern.")
            else:
                print("❌ title_help_btn not found on REPL widget")
            
            # Exit the app after checking
            app.quit()
        
        # Schedule the check after a brief delay to allow full initialization
        QTimer.singleShot(100, check_button_styling)
        
        # Run the app briefly
        app.exec()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_app_button_styling()