"""Debug script to check what's happening with code fonts."""

import sys
from pathlib import Path

# Add the ghostman src to path
sys.path.insert(0, str(Path(__file__).parent))

from ghostman.src.application.font_service import font_service

def debug_font_service():
    """Debug the font service."""
    print("=== Font Service Debug ===")
    
    try:
        # Test getting available fonts
        available_fonts = font_service.get_available_fonts()
        print(f"Available fonts: {len(available_fonts)} found")
        print(f"First 10: {available_fonts[:10]}")
        
        # Test monospace fonts
        try:
            monospace_fonts = font_service.get_monospace_fonts()
            print(f"Monospace fonts: {len(monospace_fonts)} found")
            print(f"Monospace fonts: {monospace_fonts}")
        except Exception as e:
            print(f"Error getting monospace fonts: {e}")
        
        # Test font configs
        print("\nFont Configurations:")
        for font_type in ['ai_response', 'user_input', 'code_snippets']:
            try:
                config = font_service.get_font_config(font_type)
                css = font_service.get_css_font_style(font_type)
                print(f"{font_type}: {config}")
                print(f"  CSS: {css}")
            except Exception as e:
                print(f"Error with {font_type}: {e}")
    
    except Exception as e:
        print(f"Font service error: {e}")

def test_html_rendering():
    """Test HTML rendering with code fonts."""
    print("\n=== HTML Rendering Test ===")
    
    try:
        # Get code font settings
        code_config = font_service.get_font_config('code_snippets')
        code_css = font_service.get_css_font_style('code_snippets')
        
        print(f"Code font config: {code_config}")
        print(f"Code CSS: {code_css}")
        
        # Generate test HTML
        test_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
            body {{ font-family: 'Segoe UI'; font-size: 12pt; }}
            code, pre {{ {code_css} !important; font-family: '{code_config['family']}' !important; }}
            </style>
        </head>
        <body>
            <p>Regular text</p>
            <code>inline code</code>
            <pre>code block</pre>
        </body>
        </html>
        """
        
        print(f"\nGenerated HTML:\n{test_html}")
        
    except Exception as e:
        print(f"HTML test error: {e}")

if __name__ == "__main__":
    debug_font_service()
    test_html_rendering()