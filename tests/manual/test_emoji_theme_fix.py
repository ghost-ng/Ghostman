#!/usr/bin/env python3
"""
Test script to verify emoji preservation during theme changes.

This script creates a minimal PyQt6 application with emoji buttons
and tests theme switching to ensure emojis remain visible.
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QToolButton, QPushButton, QComboBox, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmojiTestWindow(QMainWindow):
    """Test window for emoji theme switching."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_theme = "light"
        
    def setup_ui(self):
        """Setup the test UI."""
        self.setWindowTitle("Emoji Theme Switch Test")
        self.setGeometry(100, 100, 500, 300)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Info label
        info_label = QLabel("Test emoji preservation during theme changes:")
        layout.addWidget(info_label)
        
        # Theme selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Blue", "Green"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        # Emoji buttons
        button_layout = QHBoxLayout()
        
        # Create test emoji buttons
        self.emoji_buttons = []
        emojis = ["💬", "🔍", "⚙️", "📋", "📤", "🔗", "❓", "➕"]
        
        for emoji in emojis:
            btn = QToolButton()
            btn.setText(emoji)
            btn.setToolTip(f"Button with {emoji}")
            btn.setMaximumSize(40, 30)
            self.style_emoji_button(btn)
            self.emoji_buttons.append(btn)
            button_layout.addWidget(btn)
            
        layout.addLayout(button_layout)
        
        # Refresh button
        refresh_btn = QPushButton("Manually Refresh Emojis")
        refresh_btn.clicked.connect(self.refresh_emojis)
        layout.addWidget(refresh_btn)
        
        # Status label
        self.status_label = QLabel("Ready. Switch themes to test emoji preservation.")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
    def get_emoji_font_stack(self) -> str:
        """Get a font stack that supports emoji rendering on Windows."""
        emoji_fonts = [
            "Segoe UI Emoji",      
            "Segoe UI Symbol",     
            "Segoe UI",           
            "Microsoft YaHei",     
            "Apple Color Emoji",   
            "Noto Color Emoji",    
            "Noto Emoji",         
            "Arial Unicode MS",    
            "sans-serif"          
        ]
        
        font_stack = ", ".join(f'"{font}"' for font in emoji_fonts)
        logger.debug(f"Generated emoji font stack: {font_stack}")
        return font_stack
        
    def style_emoji_button(self, button: QToolButton):
        """Apply emoji-safe styling to a button."""
        emoji_font_stack = self.get_emoji_font_stack()
        
        # Get theme colors
        if self.current_theme == "light":
            bg_color = "#f0f0f0"
            text_color = "#333333"
            border_color = "#cccccc"
            hover_color = "#e0e0e0"
        elif self.current_theme == "dark":
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            border_color = "#555555"
            hover_color = "#3b3b3b"
        elif self.current_theme == "blue":
            bg_color = "#1e3a8a"
            text_color = "#ffffff"
            border_color = "#3b82f6"
            hover_color = "#2563eb"
        else:  # green
            bg_color = "#166534"
            text_color = "#ffffff"
            border_color = "#22c55e"
            hover_color = "#16a34a"
        
        button.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                font-family: {emoji_font_stack};
                font-size: 14px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_color};
            }}
            QToolButton:pressed {{
                background-color: {hover_color};
                border-width: 2px;
            }}
        """)
        
    def restore_button_emoji(self, button: QToolButton, emoji_text: str):
        """Restore emoji text using multiple strategies."""
        try:
            # Strategy 1: Force font and text refresh
            emoji_font = QFont()
            emoji_font.setFamily("Segoe UI Emoji")
            emoji_font.setPointSize(14)
            
            # Clear and restore text with font context
            button.setText("")  
            button.setFont(emoji_font)  
            button.setText(emoji_text)  
            
            # Strategy 2: Force widget update
            button.update()
            button.repaint()
            
            logger.debug(f"Restored emoji: {emoji_text}")
            
        except Exception as e:
            logger.warning(f"Failed to restore emoji {emoji_text}: {e}")
            try:
                button.setText(emoji_text)
            except Exception as fallback_error:
                logger.error(f"Fallback emoji restoration failed: {fallback_error}")
        
    def change_theme(self, theme_name: str):
        """Change the theme and test emoji preservation."""
        self.current_theme = theme_name.lower()
        logger.info(f"Changing theme to: {self.current_theme}")
        
        # Apply new styles to all buttons
        for button in self.emoji_buttons:
            original_text = button.text()
            self.style_emoji_button(button)
            
            # Restore emoji using enhanced method
            if original_text:
                self.restore_button_emoji(button, original_text)
        
        # Update window background
        if self.current_theme == "light":
            self.setStyleSheet("QMainWindow { background-color: #ffffff; }")
        elif self.current_theme == "dark":
            self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")
        elif self.current_theme == "blue":
            self.setStyleSheet("QMainWindow { background-color: #0f172a; }")
        else:  # green
            self.setStyleSheet("QMainWindow { background-color: #052e16; }")
            
        self.status_label.setText(f"Theme changed to {theme_name}. Check if emojis are still visible!")
        
    def refresh_emojis(self):
        """Manually refresh all emoji buttons."""
        logger.info("Manually refreshing emojis")
        
        emoji_list = ["💬", "🔍", "⚙️", "📋", "📤", "🔗", "❓", "➕"]
        
        for i, button in enumerate(self.emoji_buttons):
            if i < len(emoji_list):
                self.restore_button_emoji(button, emoji_list[i])
                
        self.status_label.setText("Emojis manually refreshed!")


def main():
    """Run the emoji test application."""
    app = QApplication(sys.argv)
    
    # Set application-wide emoji font for better compatibility
    app.setFont(QFont("Segoe UI Emoji", 10))
    
    window = EmojiTestWindow()
    window.show()
    
    logger.info("Emoji theme test application started")
    logger.info("Instructions:")
    logger.info("1. Note the emoji buttons displayed")
    logger.info("2. Change themes using the dropdown")
    logger.info("3. Check if emojis remain visible after theme changes")
    logger.info("4. Use 'Manually Refresh Emojis' button if needed")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()