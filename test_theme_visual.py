"""Visual test to confirm theme changes work in Settings Dialog."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ghostman.src.presentation.dialogs.settings_dialog import SettingsDialog
from ghostman.src.infrastructure.storage.settings_manager import SettingsManager
from ghostman.src.ui.themes.theme_manager import get_theme_manager

def main():
    app = QApplication(sys.argv)
    
    # Initialize theme manager
    theme_manager = get_theme_manager()
    
    # Test with different themes
    themes_to_test = ["arctic_white", "dark_matrix", "cyberpunk", "sunset"]
    
    for theme_name in themes_to_test:
        print(f"\n=== Testing theme: {theme_name} ===")
        
        # Set the theme
        if theme_manager.set_theme(theme_name):
            print(f"✅ Theme '{theme_name}' set successfully")
            
            # Create and show settings dialog
            settings_manager = SettingsManager()
            dialog = SettingsDialog(settings_manager)
            dialog.setWindowTitle(f"Settings - Theme: {theme_name}")
            
            # Show the dialog
            result = dialog.exec()
            
            if result:
                print(f"Dialog closed with OK for theme: {theme_name}")
            else:
                print(f"Dialog cancelled for theme: {theme_name}")
                break  # Exit if user cancels
        else:
            print(f"❌ Failed to set theme: {theme_name}")
    
    print("\n=== Theme test completed ===")

if __name__ == "__main__":
    main()