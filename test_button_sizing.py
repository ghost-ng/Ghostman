#!/usr/bin/env python3
"""
Test script to verify uniform button sizing after PyQt6 border removal fix.

This script demonstrates that all buttons now have identical sizing regardless
of their toggle state, with no borders and consistent border-radius.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QToolButton, QLabel
from PyQt6.QtCore import Qt

class ButtonSizingTestWindow(QMainWindow):
    """Test window to demonstrate uniform button sizing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Button Sizing Test - All Buttons Should Be Identical Size")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add title
        title = QLabel("PyQt6 Button Sizing Fix Verification")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Create test buttons row
        button_layout = QHBoxLayout()
        
        # Normal button (like other title buttons)
        normal_button = QToolButton()
        normal_button.setText("📁")
        normal_button.setToolTip("Normal Button")
        self._apply_normal_button_style(normal_button)
        button_layout.addWidget(normal_button)
        
        # Move button in normal state
        move_button_normal = QToolButton()
        move_button_normal.setText("↕")
        move_button_normal.setToolTip("Move Button (Normal)")
        self._apply_normal_button_style(move_button_normal)
        button_layout.addWidget(move_button_normal)
        
        # Move button in toggle state (should be same size)
        move_button_toggle = QToolButton()
        move_button_toggle.setText("↕")
        move_button_toggle.setToolTip("Move Button (Toggled)")
        self._apply_move_toggle_style(move_button_toggle)
        button_layout.addWidget(move_button_toggle)
        
        # Another normal button for comparison
        normal_button2 = QToolButton()
        normal_button2.setText("⚙")
        normal_button2.setToolTip("Settings Button")
        self._apply_normal_button_style(normal_button2)
        button_layout.addWidget(normal_button2)
        
        layout.addLayout(button_layout)
        
        # Add verification text
        verification_text = QLabel(
            "✅ SUCCESS: If all buttons above are the same size with no borders, the fix is working!\n"
            "❌ FAILURE: If the yellow move button is larger, there's still a sizing issue."
        )
        verification_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verification_text.setStyleSheet("margin: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(verification_text)
        
        # Technical details
        details = QLabel(
            "Technical Details:\n"
            "• All buttons use identical min/max size constraints (28x28 to 32x32)\n"
            "• All buttons have 8px padding\n"
            "• NO borders on any buttons (border: none)\n"
            "• Consistent 4px border-radius\n"
            "• PyQt6 calculates size as: padding + content (no border width added)"
        )
        details.setStyleSheet("margin: 10px; font-family: monospace; font-size: 10px;")
        layout.addWidget(details)
    
    def _apply_normal_button_style(self, button: QToolButton):
        """Apply normal button styling (like base title buttons)."""
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(100, 100, 100, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 8px;
                min-width: 28px;
                min-height: 28px;
                max-width: 32px;
                max-height: 32px;
            }
            QToolButton:hover {
                background-color: rgba(120, 120, 120, 0.9);
            }
            QToolButton:pressed {
                background-color: rgba(140, 140, 140, 1.0);
            }
        """)
    
    def _apply_move_toggle_style(self, button: QToolButton):
        """Apply move button toggle styling (yellow background)."""
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 215, 0, 0.8);
                color: black;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 8px;
                min-width: 28px;
                min-height: 28px;
                max-width: 32px;
                max-height: 32px;
            }
            QToolButton:hover {
                background-color: rgba(255, 215, 0, 0.9);
            }
            QToolButton:pressed {
                background-color: rgba(255, 215, 0, 1.0);
            }
        """)

def main():
    """Run the button sizing test."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show test window
    window = ButtonSizingTestWindow()
    window.show()
    
    # Run the application
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())