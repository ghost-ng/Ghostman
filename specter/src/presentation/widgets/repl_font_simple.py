"""
Simple font configuration for REPL widget.
"""

def get_default_fonts():
    """Get default fonts for REPL."""
    return {
        'text': "font-family: 'Tahoma', 'Segoe UI', sans-serif; font-size: 10pt;",
        'code': "font-family: 'Courier', 'Courier New', monospace; font-size: 9pt;"
    }

def refresh_fonts(output_display):
    """No-op - using fixed fonts."""
    pass

def update_existing_fonts(output_display):
    """No-op - using fixed fonts."""
    pass