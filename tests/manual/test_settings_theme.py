"""Test script to verify that Settings Dialog uses the current theme."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QPushButton, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLabel
from PyQt6.QtCore import Qt
from ghostman.src.presentation.dialogs.settings_dialog import SettingsDialog
from ghostman.src.infrastructure.storage.settings_manager import SettingsManager
from ghostman.src.ui.themes.theme_manager import get_theme_manager
import logging

logging.basicConfig(level=logging.DEBUG)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Theme Test for Settings Dialog")
        self.setGeometry(100, 100, 400, 200)
        
        # Central widget
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        
        # Theme selector
        self.theme_manager = get_theme_manager()
        self.theme_selector = QComboBox()
        themes = self.theme_manager.get_available_themes()
        self.theme_selector.addItems(themes)
        self.theme_selector.setCurrentText(self.theme_manager.current_theme_name)
        self.theme_selector.currentTextChanged.connect(self.on_theme_changed)
        
        layout.addWidget(QLabel("Select Theme:"))
        layout.addWidget(self.theme_selector)
        
        # Button to open settings
        self.open_settings_btn = QPushButton("Open Settings Dialog")
        self.open_settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(self.open_settings_btn)
        
        # Status label
        self.status_label = QLabel(f"Current Theme: {self.theme_manager.current_theme_name}")
        layout.addWidget(self.status_label)
        
        # Apply initial theme
        self.apply_main_window_theme()
    
    def on_theme_changed(self, theme_name):
        """Handle theme selection change."""
        if self.theme_manager.set_theme(theme_name):
            self.status_label.setText(f"✅ Theme changed to: {theme_name}")
            self.apply_main_window_theme()
        else:
            self.status_label.setText(f"❌ Failed to set theme: {theme_name}")
    
    def apply_main_window_theme(self):
        """Apply theme to main window."""
        try:
            from ghostman.src.ui.themes.style_templates import StyleTemplates
            colors = self.theme_manager.current_theme
            
            # Basic window style
            style = f"""
            QMainWindow {{
                background-color: {colors.background_primary};
                color: {colors.text_primary};
            }}
            QWidget {{
                background-color: {colors.background_primary};
                color: {colors.text_primary};
            }}
            QPushButton {{
                background-color: {colors.primary};
                color: {colors.text_primary};
                border: none;
                padding: 8px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.primary_hover};
            }}
            QComboBox {{
                background-color: {colors.background_tertiary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_primary};
                padding: 4px;
            }}
            QLabel {{
                color: {colors.text_primary};
            }}
            """
            self.setStyleSheet(style)
        except Exception as e:
            print(f"Failed to apply theme: {e}")
    
    def open_settings(self):
        """Open the settings dialog."""
        settings_manager = SettingsManager()
        dialog = SettingsDialog(settings_manager, self)
        
        # Connect to see when settings are applied
        dialog.settings_applied.connect(self.on_settings_applied)
        
        result = dialog.exec()
        
        if result:
            self.status_label.setText("✅ Settings dialog closed with OK")
        else:
            self.status_label.setText("Settings dialog cancelled")
    
    def on_settings_applied(self, config):
        """Handle settings applied signal."""
        print(f"Settings applied: {config.keys()}")
        self.status_label.setText("✅ Settings applied successfully")

def main():
    app = QApplication(sys.argv)
    
    # Test with different themes
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()