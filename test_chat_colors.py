"""Test script to debug chat bubble colors."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from ghostman.src.ui.themes.theme_manager import get_theme_manager
from ghostman.src.presentation.widgets.repl_widget import MarkdownRenderer

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Colors Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        
        # Get theme manager
        self.theme_manager = get_theme_manager()
        
        # Create markdown renderer
        self.markdown_renderer = MarkdownRenderer(self.theme_manager)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)
        
        # Test different message types
        test_btn = QPushButton("Test Message Colors")
        test_btn.clicked.connect(self.test_colors)
        layout.addWidget(test_btn)
        
        # Theme info
        colors = self.theme_manager.current_theme
        info_text = f"""
Theme: {self.theme_manager.current_theme_name}
Primary: {colors.primary}
Text Primary: {colors.text_primary}
Text Secondary: {colors.text_secondary}
Status Info: {colors.status_info}
"""
        layout.addWidget(QTextEdit(info_text))
    
    def test_colors(self):
        """Test rendering different message types."""
        self.text_display.clear()
        
        # Test different message types
        test_messages = [
            ("Hello! This is a **normal** message with *emphasis*", "normal"),
            ("User input message", "input"),
            ("AI response with `code` and **bold** text", "response"),
            ("System message", "system"),
            ("Info message", "info"),
            ("Warning message", "warning"),
            ("Error message", "error"),
        ]
        
        for text, style in test_messages:
            html = self.markdown_renderer.render(text, style)
            self.text_display.insertHtml(f"<p><strong>{style.upper()}:</strong> {html}</p>")
        
        # Debug color scheme
        print("Current color scheme:")
        for key, value in self.markdown_renderer.color_scheme.items():
            print(f"  {key}: {value}")

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()