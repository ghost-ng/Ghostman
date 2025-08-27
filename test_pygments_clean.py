#!/usr/bin/env python3
"""
Test the PygmentsRenderer with clean white styling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTextEdit, QLabel
from PyQt6.QtCore import Qt

try:
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    
    def test_pygments_clean_styling():
        """Test that our PygmentsRenderer generates clean white HTML."""
        app = QApplication(sys.argv)
        
        # Create a minimal REPL widget to get the renderer
        try:
            repl = REPLWidget()
            renderer = repl._create_enhanced_renderer()
            
            # Test code samples
            test_cases = [
                ('python', '''def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))'''),
                ('json', '''{"name": "test", "version": 1, "features": ["bold", "italic", "code"]}'''),
                ('yaml', '''server:
  host: localhost
  port: 8080''')
            ]
            
            # Create test window
            window = QWidget()
            window.setWindowTitle("Clean PygmentsRenderer Test")
            window.resize(700, 600)
            window.setStyleSheet("background-color: #f6f8fa; padding: 20px;")
            
            layout = QVBoxLayout(window)
            
            header = QLabel("Clean Code Rendering Test - Should be White Background!")
            header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 20px; color: #24292e;")
            layout.addWidget(header)
            
            # Create text display
            text_display = QTextEdit()
            text_display.setReadOnly(True)
            
            # Generate HTML for each test case
            html_content = []
            for language, code in test_cases:
                print(f"\\nTesting {language} code...")
                html = renderer.block_code(code, language)
                print(f"Generated HTML length: {len(html)} characters")
                
                # Check for clean white background
                if '#ffffff' in html:
                    print(f"✅ {language}: Clean white background found")
                else:
                    print(f"❌ {language}: White background missing")
                
                # Check for light borders
                if '#e1e5e9' in html:
                    print(f"✅ {language}: Light borders found")
                else:
                    print(f"❌ {language}: Light borders missing")
                
                html_content.append(html)
            
            # Display all rendered HTML
            full_html = f"""
            <html>
            <head>
                <style>
                    body {{ 
                        background-color: #f6f8fa; 
                        margin: 20px; 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; 
                    }}
                </style>
            </head>
            <body>
                <h2>Clean Code Snippet Rendering</h2>
                <p>These should all have clean white backgrounds with light borders:</p>
                {''.join(html_content)}
            </body>
            </html>
            """
            
            text_display.setHtml(full_html)
            layout.addWidget(text_display)
            
            # Status
            status = QLabel("✅ If snippets have white backgrounds and light borders, the fix worked!")
            status.setStyleSheet("color: #24292e; font-weight: bold; padding: 10px; background: white; border-radius: 6px;")
            layout.addWidget(status)
            
            window.show()
            print("\\n🎯 Clean PygmentsRenderer test window opened!")
            print("Check if the code snippets have clean white backgrounds.")
            
            return app.exec()
            
        except Exception as e:
            print(f"Failed to create REPL renderer: {e}")
            return False
            
except ImportError as e:
    print(f"Import failed: {e}")
    print("Running without REPL integration test")

def main():
    return test_pygments_clean_styling()

if __name__ == "__main__":
    main()