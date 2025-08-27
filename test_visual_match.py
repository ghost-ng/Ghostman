#!/usr/bin/env python3
"""
Visual test to verify the code snippet matches the target design exactly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel
from ghostman.src.presentation.widgets.code_snippet_widget import CodeSnippetWidget

def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("Code Snippet - Target Design Match")
    window.resize(500, 300)
    window.setStyleSheet("background-color: #f6f8fa; padding: 20px;")
    
    layout = QVBoxLayout(window)
    
    # Target code exactly like in your screenshot
    target_code = '''def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))'''
    
    # Create widget exactly as in target
    snippet = CodeSnippetWidget(target_code, "python", "Python Snippet")
    layout.addWidget(snippet)
    
    # Status
    status = QLabel("This should match your target screenshot exactly!")
    status.setStyleSheet("color: #24292e; font-weight: bold; text-align: center;")
    layout.addWidget(status)
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    main()