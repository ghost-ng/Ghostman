"""Test script to verify font color and search icon fixes."""

import sys
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer

# Add project root to path
sys.path.insert(0, 'C:\\Users\\miguel\\OneDrive\\Documents\\Ghostman')

from ghostman.src.presentation.widgets.repl_widget import REPLWidget
from ghostman.src.ui.themes.theme_manager import get_theme_manager

def test_font_color_fix():
    """Test that font colors apply properly after theme changes."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Font Color Fix Test")
    window.resize(800, 600)
    
    # Create central widget
    central = QWidget()
    layout = QVBoxLayout(central)
    window.setCentralWidget(central)
    
    # Create REPL widget
    repl = REPLWidget()
    layout.addWidget(repl)
    
    # Add test content
    repl.append_output("Testing font color application", "normal")
    repl.append_output("User input text", "input")
    repl.append_output("AI response text", "response")
    repl.append_output("System message", "system")
    repl.append_output("Error message", "error")
    
    # Create theme switch buttons
    theme_manager = get_theme_manager()
    
    status_label = QLabel("Current theme: forest_green")
    layout.addWidget(status_label)
    
    def switch_to_dark():
        theme_manager.set_theme("dark_mode")
        status_label.setText("Current theme: dark_mode")
        # Test that fonts refresh properly
        repl.refresh_fonts()
        print("✓ Switched to dark_mode - font colors should be visible")
    
    def switch_to_light():
        theme_manager.set_theme("light_mode")
        status_label.setText("Current theme: light_mode")
        # Test that fonts refresh properly
        repl.refresh_fonts()
        print("✓ Switched to light_mode - font colors should be visible")
    
    def toggle_search():
        repl._toggle_search()
        if repl.search_frame.isVisible():
            print("✓ Search bar opened - icon should have no border")
            # Check if search icon has proper styling
            if hasattr(repl, 'search_icon_label'):
                style = repl.search_icon_label.styleSheet()
                if 'border: none' in style:
                    print("✓ Search icon border removed successfully")
                else:
                    print("✗ Search icon still has border")
        else:
            print("Search bar closed")
    
    dark_btn = QPushButton("Switch to Dark Theme")
    dark_btn.clicked.connect(switch_to_dark)
    layout.addWidget(dark_btn)
    
    light_btn = QPushButton("Switch to Light Theme")
    light_btn.clicked.connect(switch_to_light)
    layout.addWidget(light_btn)
    
    search_btn = QPushButton("Toggle Search (Check Icon)")
    search_btn.clicked.connect(toggle_search)
    layout.addWidget(search_btn)
    
    # Show window
    window.show()
    
    # Auto-test after window is shown
    def run_auto_test():
        print("\n=== Running automated tests ===")
        
        # Test 1: Check output display has proper font color styling
        output_style = repl.output_display.styleSheet()
        if 'color:' in output_style and '!important' in output_style:
            print("✓ Test 1 PASSED: Output display has enforced font color")
        else:
            print("✗ Test 1 FAILED: Output display missing enforced font color")
        
        # Test 2: Open search and check icon
        repl._toggle_search()
        if hasattr(repl, 'search_icon_label'):
            icon_style = repl.search_icon_label.styleSheet()
            if 'border: none' in icon_style:
                print("✓ Test 2 PASSED: Search icon has no border")
            else:
                print("✗ Test 2 FAILED: Search icon still has border")
        else:
            print("✗ Test 2 FAILED: Search icon label not found")
        
        # Test 3: Theme switch and font refresh
        original_theme = theme_manager.current_theme_name
        theme_manager.set_theme("dark_mode")
        repl.refresh_fonts()
        
        # Check if colors updated
        new_style = repl.output_display.styleSheet()
        if 'color:' in new_style and '!important' in new_style:
            print("✓ Test 3 PASSED: Font colors persist after theme change")
        else:
            print("✗ Test 3 FAILED: Font colors lost after theme change")
        
        # Restore original theme
        theme_manager.set_theme(original_theme)
        
        print("=== Tests completed ===\n")
    
    # Run tests after UI is ready
    QTimer.singleShot(500, run_auto_test)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_font_color_fix()