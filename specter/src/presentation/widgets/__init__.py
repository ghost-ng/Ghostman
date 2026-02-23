"""
UI widgets for Specter presentation layer.
"""

# File context UI components 
try:
    from .file_browser_bar import (
        FileBrowserBar,
        FileContextItem,
        FileStatusIndicator
    )
    
    __all__ = [
        "FileBrowserBar",
        "FileContextItem",
        "FileStatusIndicator"
    ]
except ImportError:
    # File context widgets not available
    __all__ = []