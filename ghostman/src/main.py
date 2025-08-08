#!/usr/bin/env python3
"""Main entry point for Ghostman application."""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Enable high DPI support before creating QApplication
try:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
except AttributeError:
    # Older Qt versions don't have these attributes
    pass

def main():
    """Main entry point for the application."""
    from app.application import GhostmanApplication, setup_logging
    
    # Setup logging first
    setup_logging()
    
    try:
        # Create and run application
        app = GhostmanApplication()
        return app.run()
        
    except KeyboardInterrupt:
        print("Application interrupted by user")
        return 0
    except Exception as e:
        print(f"Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())