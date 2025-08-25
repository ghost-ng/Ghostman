#!/usr/bin/env python3
"""
Test script for enhanced tab styling improvements.

Tests the new tab styling system across multiple themes to verify:
1. Active tabs use theme primary colors (not purple)
2. Tabs maintain consistent sizing when themes change
3. Text contrast meets accessibility requirements
4. Theme transitions work properly
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "ghostman", "src"))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer

# Import theme system
from ui.themes.preset_themes import get_preset_themes
from ui.themes.color_system import ColorSystem, ColorUtils
from ui.themes.style_templates import StyleTemplates

# Import tab system
from presentation.widgets.tab_conversation_manager import TabConversationManager, ConversationTab

class TabTestWindow(QMainWindow):
    """Test window for enhanced tab styling."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Tab Styling Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Set up UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Theme info label
        self.theme_label = QLabel("Current Theme: openai_like")
        self.theme_label.setStyleSheet("font-weight: bold; padding: 10px; font-size: 14px;")
        layout.addWidget(self.theme_label)
        
        # Tab container
        tab_container = QWidget()
        tab_layout = QHBoxLayout(tab_container)
        
        # Create mock tab system
        self.tab_manager = TabConversationManager(
            parent_repl_widget=self,  # Mock parent
            tab_frame=tab_container,
            tab_layout=tab_layout,
            create_initial_tab=False
        )
        
        # Add some test tabs
        self.tab_manager.create_tab("tab1", "Chat with Claude", activate=True)
        self.tab_manager.create_tab("tab2", "Python Development")
        self.tab_manager.create_tab("tab3", "Design Discussion")
        self.tab_manager.create_tab("tab4", "Long Tab Name That Gets Truncated")
        
        layout.addWidget(tab_container)
        
        # Add stretch to push tabs to top
        layout.addStretch()
        
        # Test info label
        self.info_label = QLabel("Testing enhanced tab styling across themes...\nWatch for consistent sizing and theme-aware colors!")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 20px; color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # Set up theme cycling
        self.themes = list(get_preset_themes().keys())
        self.current_theme_index = 0
        self.theme_manager = MockThemeManager()
        
        # Apply initial theme
        self.apply_theme(self.themes[0])
        
        # Set up timer for theme cycling
        self.theme_timer = QTimer()
        self.theme_timer.timeout.connect(self.cycle_theme)
        self.theme_timer.start(3000)  # Change theme every 3 seconds
        
        print("🎨 Tab styling test started!")
        print(f"🔄 Will cycle through {len(self.themes)} themes every 3 seconds")
        print("👀 Watch for:")
        print("  - Active tabs should use theme primary colors (not purple)")
        print("  - Tabs should maintain consistent size")
        print("  - Text should remain readable across all themes")
    
    def cycle_theme(self):
        """Cycle to the next theme."""
        self.current_theme_index = (self.current_theme_index + 1) % len(self.themes)
        theme_name = self.themes[self.current_theme_index]
        self.apply_theme(theme_name)
    
    def apply_theme(self, theme_name: str):
        """Apply a specific theme."""
        themes = get_preset_themes()
        if theme_name in themes:
            colors = themes[theme_name]
            self.theme_manager.current_theme = colors
            
            # Update theme label
            self.theme_label.setText(f"Current Theme: {theme_name}")
            self.theme_label.setStyleSheet(f"""
                font-weight: bold; 
                padding: 10px; 
                font-size: 14px;
                background-color: {colors.background_secondary};
                color: {colors.text_primary};
                border-radius: 4px;
            """)
            
            # Apply theme to window background
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.background_primary};
                    color: {colors.text_primary};
                }}
            """)
            
            # Refresh tab styles
            if hasattr(self, 'tab_manager') and self.tab_manager:
                self.tab_manager.refresh_tab_styles()
                
            # Update info label styling
            self.info_label.setStyleSheet(f"""
                padding: 20px; 
                color: {colors.text_secondary}; 
                font-size: 12px;
                background-color: {colors.background_tertiary};
                border-radius: 4px;
                margin: 10px;
            """)
            
            print(f"🎨 Applied theme: {theme_name} (Primary: {colors.primary})")

class MockThemeManager:
    """Mock theme manager for testing."""
    
    def __init__(self):
        self.current_theme = None

def test_tab_accessibility():
    """Test tab accessibility features."""
    print("\n🔍 Testing tab accessibility:")
    
    themes = get_preset_themes()
    
    for theme_name, colors in themes.items():
        # Test active tab contrast
        active_text_color, active_contrast = ColorUtils.get_high_contrast_text_color_for_background(
            colors.primary, colors, min_ratio=4.5
        )
        
        # Test inactive tab contrast
        inactive_text_color, inactive_contrast = ColorUtils.get_high_contrast_text_color_for_background(
            colors.background_tertiary, colors, min_ratio=4.5
        )
        
        print(f"  {theme_name}:")
        print(f"    Active tab: {colors.primary} + {active_text_color} (contrast: {active_contrast:.1f})")
        print(f"    Inactive tab: {colors.background_tertiary} + {inactive_text_color} (contrast: {inactive_contrast:.1f})")
        
        # Check if contrast meets accessibility standards
        if active_contrast >= 4.5 and inactive_contrast >= 4.5:
            status = "✅ WCAG AA compliant"
        else:
            status = "⚠️  Contrast may be low"
        print(f"    {status}")

def main():
    """Main test function."""
    app = QApplication(sys.argv)
    
    # Test accessibility first
    test_tab_accessibility()
    
    # Create and show test window
    window = TabTestWindow()
    window.show()
    
    print(f"\n🚀 Tab styling test window opened!")
    print("✨ Themes will cycle automatically every 3 seconds")
    print("🎯 Look for consistent tab sizing and theme-aware colors")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()