#!/usr/bin/env python3
"""
Test script to validate theme compatibility and check for HTML artifacts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt, QTimer
from ghostman.src.presentation.widgets.mixed_content_display import MixedContentDisplay

def test_html_artifact_cleanup():
    """Test HTML artifact cleanup functionality."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("HTML Artifact & Theme Compatibility Test")
    window.resize(900, 700)
    
    # Central widget and layout
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    window.setCentralWidget(central_widget)
    
    # Create test display
    display = MixedContentDisplay()
    
    # Test theme colors (Solarized Dark)
    theme_colors = {
        'bg_primary': '#002b36',
        'bg_secondary': '#073642',
        'bg_tertiary': '#094352',
        'text_primary': '#839496',
        'text_secondary': '#586e75',
        'border': '#073642',
        'info': '#268bd2',
        'warning': '#cb4b16',
        'error': '#dc322f',
        'keyword': '#859900',
        'string': '#2aa198',
        'comment': '#586e75',
        'function': '#b58900',
        'number': '#d33682',
        'builtin': '#cb4b16',
        'interactive': '#073642',
        'interactive_hover': '#094352',
    }
    display.set_theme_colors(theme_colors)
    
    # Control buttons
    button_layout = QHBoxLayout()
    
    test_artifact_btn = QPushButton("Test Artifact Cleanup")
    test_copy_btn = QPushButton("Test Copy Button")
    clear_btn = QPushButton("Clear Display")
    
    button_layout.addWidget(test_artifact_btn)
    button_layout.addWidget(test_copy_btn)
    button_layout.addWidget(clear_btn)
    button_layout.addStretch()
    
    layout.addLayout(button_layout)
    
    # Status label
    status_label = QLabel("Ready to test HTML artifact cleanup and copy functionality")
    status_label.setStyleSheet("color: #268bd2; padding: 5px; background: #073642; border-radius: 3px;")
    layout.addWidget(status_label)
    
    layout.addWidget(display)
    
    def test_artifacts():
        """Test HTML content with potential artifacts."""
        status_label.setText("Testing HTML artifact cleanup...")
        
        # This HTML contains the artifacts you mentioned
        problematic_html = '''
        <p>Here's some text before a code block:</p>
        
        <div style="background-color: #094352; border: 1px solid #073642; border-radius: 6px; margin: 8px 0; overflow: hidden;">
            <div style="background-color: #073642; padding: 12px 16px; border-bottom: 1px solid #073642;">
                <span>Python Snippet</span>
                <span>PYTHON</span>
                <span>Copy</span>
            </div>
            <div style="background-color: #094352; padding: 16px;">
                <pre style="margin: 0; white-space: pre-wrap; background-color: #094352;">def example():
    print("Hello, World!")
    return 42</pre>
            </div>
        </div>
        
        </div>
        </div><br>
        
        <p>This text should appear cleanly after the code block without artifacts.</p>
        '''
        
        display.add_html_content(problematic_html, "normal")
        
        # Update status after a delay
        QTimer.singleShot(1000, lambda: status_label.setText("✅ Artifact cleanup test complete. Check for stray HTML tags."))
    
    def test_copy():
        """Test copy button functionality.""" 
        status_label.setText("Testing copy button functionality...")
        
        display.add_html_content("<h3>Code Snippet with Copy Button</h3>", "info")
        
        # Add a code snippet to test copy functionality
        code = '''import requests
from typing import Dict, Any

def fetch_data(url: str) -> Dict[str, Any]:
    """Fetch JSON data from URL with error handling."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return {}

# Example usage
data = fetch_data("https://api.example.com/data")
print(f"Retrieved {len(data)} items")'''
        
        display.add_code_snippet(code, "python")
        
        display.add_html_content(
            "<p><b>Hover over the code block above to see the copy button!</b></p>"
            "<p>The copy button should:</p>"
            "<ul>"
            "<li>Appear on hover in the top-right corner</li>"
            "<li>Have theme-appropriate styling</li>"
            "<li>Show 'Copied!' feedback when clicked</li>"
            "<li>Copy the code to clipboard</li>"
            "</ul>", 
            "normal"
        )
        
        QTimer.singleShot(1000, lambda: status_label.setText("✅ Copy button test complete. Hover over code to test!"))
    
    def clear_display():
        display.clear()
        status_label.setText("Display cleared. Ready for next test.")
    
    # Connect buttons
    test_artifact_btn.clicked.connect(test_artifacts)
    test_copy_btn.clicked.connect(test_copy)
    clear_btn.clicked.connect(clear_display)
    
    # Add initial content
    display.add_html_content("<h1>🧪 Theme Compatibility & Artifact Test</h1>", "info")
    display.add_html_content(
        "<p>This test validates:</p>"
        "<ol>"
        "<li><b>HTML artifact cleanup</b> - No stray &lt;/div&gt;&lt;/div&gt;&lt;br&gt; tags</li>"
        "<li><b>Copy button functionality</b> - Hover-triggered copy with feedback</li>"
        "<li><b>Theme compatibility</b> - Colors work with current theme</li>"
        "<li><b>Syntax highlighting</b> - Universal colors for all themes</li>"
        "</ol>", 
        "normal"
    )
    
    # Show window
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    test_html_artifact_cleanup()