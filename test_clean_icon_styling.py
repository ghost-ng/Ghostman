"""
Test script to verify clean icon styling for save and plus buttons across all redesigned themes.

This script creates a simple test interface that demonstrates the clean icon styling
system working with different themes, ensuring save and plus buttons are clearly
visible and distinct.
"""

import sys
import os

# Add the ghostman source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QLabel, QComboBox, QPushButton, 
                                 QToolButton, QGroupBox, QTextEdit)
    from PyQt6.QtCore import QSize, Qt
    from PyQt6.QtGui import QFont, QIcon
    
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    from ghostman.src.ui.themes.improved_preset_themes import get_improved_preset_themes
    from ghostman.src.ui.themes.icon_styling import (apply_clean_icon_styling, apply_save_button_styling, 
                                       apply_plus_button_styling)
    from ghostman.src.ui.themes.style_templates import ButtonStyleManager
    
    class CleanIconTestWindow(QMainWindow):
        """Test window for clean icon styling system."""
        
        def __init__(self):
            super().__init__()
            self.theme_manager = get_theme_manager()
            self.improved_themes = get_improved_preset_themes()
            self.setup_ui()
            self.connect_signals()
            
            # Start with the first improved theme
            first_theme = list(self.improved_themes.keys())[0]
            self.apply_test_theme(first_theme)
        
        def setup_ui(self):
            """Set up the test interface."""
            self.setWindowTitle("Clean Icon Styling Test - Save & Plus Buttons")
            self.setMinimumSize(800, 600)
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Theme selector
            theme_group = QGroupBox("Theme Selection")
            theme_layout = QHBoxLayout(theme_group)
            
            theme_layout.addWidget(QLabel("Test Theme:"))
            self.theme_combo = QComboBox()
            self.theme_combo.addItems(list(self.improved_themes.keys()))
            theme_layout.addWidget(self.theme_combo)
            
            layout.addWidget(theme_group)
            
            # Icon test area
            icon_group = QGroupBox("Clean Icon Styling Test")
            icon_layout = QVBoxLayout(icon_group)
            
            # Instructions
            instructions = QLabel(
                "These buttons demonstrate clean icon styling without special effects.\n"
                "Save buttons should show in success green (when contrast allows).\n"
                "Plus buttons should show in primary theme color (when contrast allows).\n"
                "All buttons should be clearly visible against theme backgrounds."
            )
            instructions.setWordWrap(True)
            instructions.setStyleSheet("font-style: italic; margin: 10px;")
            icon_layout.addWidget(instructions)
            
            # Button test rows
            self.create_button_test_row(icon_layout, "Save Buttons", "save")
            self.create_button_test_row(icon_layout, "Plus Buttons", "plus") 
            self.create_button_test_row(icon_layout, "Standard Buttons", "normal")
            
            layout.addWidget(icon_group)
            
            # Theme info area
            info_group = QGroupBox("Theme Information")
            info_layout = QVBoxLayout(info_group)
            
            self.theme_info = QTextEdit()
            self.theme_info.setMaximumHeight(150)
            self.theme_info.setReadOnly(True)
            info_layout.addWidget(self.theme_info)
            
            layout.addWidget(info_group)
        
        def create_button_test_row(self, parent_layout, label_text: str, icon_type: str):
            """Create a row of test buttons for the specified icon type."""
            row_layout = QHBoxLayout()
            
            # Label
            label = QLabel(f"{label_text}:")
            label.setMinimumWidth(120)
            row_layout.addWidget(label)
            
            # Different button types
            self.create_test_button(row_layout, "QPushButton", QPushButton, icon_type)
            self.create_test_button(row_layout, "QToolButton", QToolButton, icon_type)
            
            # Size variants
            for size in [12, 16, 20, 24]:
                btn = QToolButton()
                btn.setText(f"{size}px")
                btn.setToolTip(f"{icon_type} button at {size}px")
                
                # Apply clean styling
                apply_clean_icon_styling(btn, self.theme_manager.current_theme, icon_type, size)
                
                # Store for theme updates
                setattr(btn, '_icon_type', icon_type)
                setattr(btn, '_icon_size', size)
                
                row_layout.addWidget(btn)
            
            row_layout.addStretch()
            parent_layout.addLayout(row_layout)
        
        def create_test_button(self, layout, button_name: str, button_class, icon_type: str):
            """Create a test button of the specified class."""
            btn = button_class()
            btn.setText(button_name)
            btn.setToolTip(f"{icon_type} - {button_name}")
            
            # Apply clean styling
            apply_clean_icon_styling(btn, self.theme_manager.current_theme, icon_type)
            
            # Store for theme updates
            setattr(btn, '_icon_type', icon_type)
            setattr(btn, '_icon_size', 16)
            
            layout.addWidget(btn)
        
        def connect_signals(self):
            """Connect UI signals."""
            self.theme_combo.currentTextChanged.connect(self.apply_test_theme)
        
        def apply_test_theme(self, theme_name: str):
            """Apply the selected theme and update all buttons."""
            if theme_name not in self.improved_themes:
                return
            
            # Apply theme
            color_system = self.improved_themes[theme_name]
            self.theme_manager.set_custom_theme(color_system, theme_name)
            
            # Update all test buttons
            self.update_all_buttons()
            
            # Update theme info
            self.update_theme_info(theme_name, color_system)
            
            # Apply theme to main window
            self.apply_window_theme(color_system)
        
        def update_all_buttons(self):
            """Update styling for all test buttons."""
            # Find all buttons with icon styling
            for widget in self.findChildren(QPushButton) + self.findChildren(QToolButton):
                if hasattr(widget, '_icon_type'):
                    icon_type = getattr(widget, '_icon_type')
                    icon_size = getattr(widget, '_icon_size', 16)
                    apply_clean_icon_styling(widget, self.theme_manager.current_theme, icon_type, icon_size)
        
        def update_theme_info(self, theme_name: str, color_system):
            """Update the theme information display."""
            info_text = f"""
Theme: {theme_name}
            
Key Colors:
• Primary: {color_system.primary} (Plus buttons)
• Success: {color_system.status_success} (Save buttons)  
• Background Secondary: {color_system.background_secondary} (Button backgrounds)
• Text Primary: {color_system.text_primary}

Interface Areas:
• Background Primary: {color_system.background_primary} (REPL area)
• Background Secondary: {color_system.background_secondary} (Titlebar/Secondary bar)  
• Background Tertiary: {color_system.background_tertiary} (Input bar)

Border & Focus:
• Border Secondary: {color_system.border_secondary}
• Border Focus: {color_system.border_focus}

This theme uses clean icon styling without special effects for maximum visibility.
            """.strip()
            
            self.theme_info.setPlainText(info_text)
        
        def apply_window_theme(self, color_system):
            """Apply theme colors to the main window."""
            window_style = f"""
            QMainWindow {{
                background-color: {color_system.background_primary};
                color: {color_system.text_primary};
            }}
            
            QGroupBox {{
                background-color: {color_system.background_secondary};
                color: {color_system.text_primary};
                border: 1px solid {color_system.border_secondary};
                border-radius: 4px;
                font-weight: bold;
                padding-top: 10px;
                margin-top: 5px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            
            QLabel {{
                color: {color_system.text_primary};
            }}
            
            QComboBox {{
                background-color: {color_system.interactive_normal};
                color: {color_system.text_primary};
                border: 1px solid {color_system.border_secondary};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QComboBox:hover {{
                background-color: {color_system.interactive_hover};
                border-color: {color_system.border_focus};
            }}
            
            QTextEdit {{
                background-color: {color_system.background_primary};
                color: {color_system.text_primary};
                border: 1px solid {color_system.border_secondary};
                border-radius: 4px;
            }}
            """
            
            self.setStyleSheet(window_style)


    def main():
        """Run the clean icon styling test."""
        app = QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("Clean Icon Styling Test")
        app.setApplicationVersion("1.0.0")
        
        # Create and show test window
        window = CleanIconTestWindow()
        window.show()
        
        print("Clean Icon Styling Test")
        print("=" * 50)
        print("This test demonstrates clean icon styling for save and plus buttons")
        print("across all redesigned themes. The styling focuses on:")
        print("• Maximum visibility and contrast")
        print("• Clear distinction between save and plus buttons")
        print("• No special effects - just clean, accessible styling")
        print("• Theme-aware colors that work across all themes")
        print("\nUse the dropdown to test different improved themes.")
        
        sys.exit(app.exec())


    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the Ghostman directory")
    print("and that all dependencies are installed.")