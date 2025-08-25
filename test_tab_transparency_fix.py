#!/usr/bin/env python3
"""
Test script to verify the tab frame transparency fix.

This script creates a standalone test of the REPL widget to verify that
the tab frame remains transparent even when theme colors are applied.
"""

import sys
import os

# Add the ghostman source to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

# Import the REPL widget and theme system
try:
    from presentation.widgets.repl_widget import REPLWidget
    from ui.themes.theme_manager import theme_manager
    from ui.themes.preset_themes import PresetThemes
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Make sure you're running this from the Ghostman root directory")
    sys.exit(1)


class TestWindow(QMainWindow):
    """Test window to verify tab frame transparency."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab Frame Transparency Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add instructions
        instructions = QLabel("""
Tab Frame Transparency Test

Instructions:
1. Look at the tab bar area (should be transparent, not showing theme color #2A2030)
2. Change themes using Ctrl+T to verify transparency persists
3. Adjust opacity using the opacity slider to verify transparency persists

Expected behavior: 
- Tab frame should always be transparent regardless of theme
- Theme color should only appear in the main REPL panel background
- Tab frame should never inherit the theme panel background color

Press Escape to close this test window.
        """)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: rgba(255,255,200,0.8); border: 1px solid gray;")
        layout.addWidget(instructions)
        
        # Create REPL widget for testing
        try:
            self.repl_widget = REPLWidget()
            layout.addWidget(self.repl_widget)
        except Exception as e:
            error_label = QLabel(f"Failed to create REPL widget: {e}")
            error_label.setStyleSheet("color: red; padding: 10px;")
            layout.addWidget(error_label)
            return
        
        # Schedule theme changes to test the fix
        self.setup_theme_cycling()
    
    def setup_theme_cycling(self):
        """Set up automatic theme cycling to test transparency persistence."""
        self.current_theme_index = 0
        self.themes = ["dark", "light", "midnight", "forest", "ocean"]
        
        # Start cycling themes every 3 seconds
        self.theme_timer = QTimer()
        self.theme_timer.timeout.connect(self.cycle_theme)
        self.theme_timer.start(3000)  # 3 second intervals
        
        print("Started automatic theme cycling - watch the tab frame transparency")
    
    def cycle_theme(self):
        """Cycle through different themes to test transparency persistence."""
        theme_name = self.themes[self.current_theme_index]
        
        try:
            # Apply the theme
            theme_manager.set_theme(theme_name)
            print(f"Applied theme: {theme_name}")
            
            # Test opacity changes as well
            if hasattr(self.repl_widget, 'set_panel_opacity'):
                opacity_values = [1.0, 0.8, 0.6, 0.4, 1.0]
                opacity = opacity_values[self.current_theme_index % len(opacity_values)]
                self.repl_widget.set_panel_opacity(opacity)
                print(f"Set opacity to: {opacity}")
            
        except Exception as e:
            print(f"Failed to apply theme {theme_name}: {e}")
        
        # Move to next theme
        self.current_theme_index = (self.current_theme_index + 1) % len(self.themes)
    
    def keyPressEvent(self, event):
        """Handle key presses."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.cycle_theme()
        else:
            super().keyPressEvent(event)


def main():
    """Main test function."""
    print("Starting tab frame transparency test...")
    
    app = QApplication(sys.argv)
    
    # Set a colorful background to make transparency issues more visible
    app.setStyleSheet("""
        QMainWindow {
            background-color: qradialgradient(
                cx: 0.5, cy: 0.5, radius: 1.0,
                stop: 0 #ff6b6b,
                stop: 0.5 #4ecdc4, 
                stop: 1 #45b7d1
            );
        }
    """)
    
    window = TestWindow()
    window.show()
    
    print("\nTest Instructions:")
    print("- Look for the tab frame area at the top of the REPL widget")
    print("- The tab frame should be transparent (not showing #2A2030 theme color)")
    print("- Themes will cycle automatically every 3 seconds")
    print("- Press Ctrl+T to manually cycle themes")
    print("- Press Escape to close")
    print("\nIf you see the theme color (#2A2030) in the tab frame area, the fix is not working.")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())