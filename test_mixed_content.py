#!/usr/bin/env python3
"""
Test the MixedContentDisplay with EmbeddedCodeSnippetWidget.
Shows how code snippets have solid backgrounds without CSS inheritance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from ghostman.src.presentation.widgets.mixed_content_display import MixedContentDisplay
from ghostman.src.presentation.widgets.embedded_code_widget import EmbeddedCodeSnippetWidget

def test_mixed_content_display():
    """Test the mixed content display with embedded code widgets."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Mixed Content Display Test - Solid Code Backgrounds")
    window.resize(800, 600)
    
    # Central widget and layout
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    window.setCentralWidget(central_widget)
    
    # Create the mixed content display
    display = MixedContentDisplay()
    
    # Set theme colors (solarized dark-like)
    theme_colors = {
        'bg_primary': '#002b36',      # Dark background
        'bg_secondary': '#073642',    # Slightly lighter
        'bg_tertiary': '#094352',     # Solid background for code - slightly lighter than primary
        'text_primary': '#839496',    # Main text
        'text_secondary': '#586e75',  # Secondary text
        'border': '#073642',          # Border color
        'info': '#268bd2',            # Blue
        'warning': '#cb4b16',         # Orange
        'error': '#dc322f',           # Red
        'keyword': '#859900',         # Green
        'string': '#2aa198',          # Cyan
        'comment': '#586e75',         # Gray
        'function': '#b58900',        # Yellow
        'number': '#d33682',          # Magenta
        'interactive': '#073642',
        'interactive_hover': '#094352',
    }
    display.set_theme_colors(theme_colors)
    
    # Add button controls
    button_layout = QHBoxLayout()
    
    add_text_btn = QPushButton("Add Text")
    add_code_btn = QPushButton("Add Code Snippet")
    add_mixed_btn = QPushButton("Add Mixed Content")
    clear_btn = QPushButton("Clear All")
    
    button_layout.addWidget(add_text_btn)
    button_layout.addWidget(add_code_btn)
    button_layout.addWidget(add_mixed_btn)
    button_layout.addWidget(clear_btn)
    button_layout.addStretch()
    
    layout.addLayout(button_layout)
    layout.addWidget(display)
    
    # Button actions
    def add_text():
        display.add_html_content(
            "<h2>Regular Text Content</h2>"
            "<p>This is <b>bold</b>, this is <i>italic</i>, and this is <code>inline code</code>.</p>"
            "<p>Links work too: <a href='https://example.com'>Click here</a></p>",
            "normal"
        )
    
    def add_code():
        code = '''def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Test the function
for i in range(10):
    print(f"F({i}) = {calculate_fibonacci(i)}")'''
        
        display.add_code_snippet(code, "python")
        
    def add_mixed():
        # Add text
        display.add_html_content(
            "<h3>Mixed Content Example</h3>"
            "<p>Here's some text before the code:</p>",
            "normal"
        )
        
        # Add code
        code = '''// JavaScript example
const greeting = (name) => {
    return `Hello, ${name}!`;
};

console.log(greeting("World"));'''
        display.add_code_snippet(code, "javascript")
        
        # Add more text
        display.add_html_content(
            "<p>And here's text after the code. Notice how the code snippet has a "
            "<b>solid background color</b> that fills all the space between lines!</p>",
            "normal"
        )
        
        # Add separator
        display.add_separator()
    
    # Connect buttons
    add_text_btn.clicked.connect(add_text)
    add_code_btn.clicked.connect(add_code)
    add_mixed_btn.clicked.connect(add_mixed)
    clear_btn.clicked.connect(display.clear)
    
    # Add initial content
    display.add_html_content("<h1>🎯 Mixed Content Display Test</h1>", "info")
    display.add_html_content(
        "<p>This demonstrates code snippets with <b>solid background colors</b> "
        "that completely fill the space between lines, without any CSS inheritance issues!</p>",
        "normal"
    )
    display.add_separator()
    
    # Add a code example
    initial_code = '''# Python code with solid background
def main():
    """
    This code snippet should have a solid background color
    that fills ALL the space between lines, including the
    line spacing areas.
    """
    print("Hello, World!")
    
    # Notice how the background is solid
    # between all these comment lines
    # with no gaps or striping
    
    return 0

if __name__ == "__main__":
    main()'''
    
    display.add_code_snippet(initial_code, "python")
    
    display.add_html_content(
        "<p>✅ The code above should have a <b>solid bg_tertiary background</b> "
        f"(color: {theme_colors['bg_tertiary']}) that covers all line spacing!</p>",
        "info"
    )
    
    # Show window
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    test_mixed_content_display()