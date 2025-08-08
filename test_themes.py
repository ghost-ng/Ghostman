#!/usr/bin/env python3
"""
Test script to validate theme integration in Ghostman application.
"""

import sys
import os
from pathlib import Path

# Add the src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / "ghostman" / "src"
sys.path.insert(0, str(src_dir))

from PyQt6.QtWidgets import QApplication
from ui.themes.theme_manager import ThemeManager

def test_theme_manager():
    """Test theme manager functionality."""
    print("🧪 Testing Theme Manager...")
    
    # Create theme manager
    theme_manager = ThemeManager()
    
    # Test getting built-in themes
    builtin_themes = theme_manager.get_all_builtin_themes()
    print(f"✅ Found {len(builtin_themes)} built-in themes: {list(builtin_themes.keys())}")
    
    # Test applying different themes
    for theme_name in builtin_themes.keys():
        success = theme_manager.apply_theme(theme_name)
        print(f"{'✅' if success else '❌'} Applied theme: {theme_name}")
        
        # Generate stylesheet for each component type
        for widget_type in ['general', 'avatar', 'prompt_interface', 'settings']:
            stylesheet = theme_manager.get_stylesheet(widget_type)
            print(f"  📝 Generated {widget_type} stylesheet: {len(stylesheet)} characters")
    
    print("🎨 Theme Manager tests completed!\n")

def test_theme_colors():
    """Test theme color variations."""
    print("🌈 Testing Theme Colors...")
    
    theme_manager = ThemeManager()
    builtin_themes = theme_manager.get_all_builtin_themes()
    
    for theme_name, theme in builtin_themes.items():
        print(f"🎨 Theme: {theme.name}")
        colors = theme.colors
        print(f"  Primary: {colors.primary}")
        print(f"  Background: {colors.background}")
        print(f"  Text Primary: {colors.text_primary}")
        print(f"  User Message: {colors.user_message_bg}")
        print(f"  AI Message: {colors.ai_message_bg}")
        print(f"  Avatar Glow: {colors.avatar_glow}")
        print()

def test_theme_persistence():
    """Test theme saving and loading."""
    print("💾 Testing Theme Persistence...")
    
    # Create temporary theme manager
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    theme_config = temp_dir / "test_themes.json"
    
    theme_manager = ThemeManager(theme_config)
    
    # Apply a theme and save
    theme_manager.apply_theme('neon')
    print(f"✅ Applied and saved neon theme")
    
    # Create new instance and check if theme persisted
    theme_manager2 = ThemeManager(theme_config)
    current_theme = theme_manager2.current_theme.name
    print(f"✅ Loaded theme: {current_theme}")
    
    # Clean up
    if theme_config.exists():
        theme_config.unlink()
    temp_dir.rmdir()
    
    print("💾 Theme persistence tests completed!\n")

def test_custom_theme():
    """Test custom theme creation."""
    print("🛠️ Testing Custom Theme Creation...")
    
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    theme_config = temp_dir / "test_themes.json"
    
    theme_manager = ThemeManager(theme_config)
    
    # Create custom theme
    custom_theme = theme_manager.create_custom_theme("Test Theme", "dark")
    print(f"✅ Created custom theme: {custom_theme.name}")
    
    # Modify some colors
    custom_theme.colors.primary = "#FF5733"
    custom_theme.colors.background = "rgba(50, 0, 50, 200)"
    
    # Apply the custom theme
    success = theme_manager.apply_theme("Test Theme")
    print(f"{'✅' if success else '❌'} Applied custom theme")
    
    # Test export
    export_path = temp_dir / "test_theme.json"
    exported = theme_manager.export_theme("Test Theme", export_path)
    print(f"{'✅' if exported else '❌'} Exported custom theme")
    
    if export_path.exists():
        print(f"  📄 Export file size: {export_path.stat().st_size} bytes")
    
    # Test import
    imported_theme = theme_manager.import_theme(export_path)
    if imported_theme:
        print(f"✅ Imported theme: {imported_theme.name}")
    else:
        print("❌ Failed to import theme")
    
    # Clean up
    if export_path.exists():
        export_path.unlink()
    if theme_config.exists():
        theme_config.unlink()
    temp_dir.rmdir()
    
    print("🛠️ Custom theme tests completed!\n")

def main():
    """Run all theme tests."""
    print("🚀 Starting Ghostman Theme Integration Tests\n")
    
    # Create QApplication for GUI components
    app = QApplication(sys.argv)
    
    try:
        test_theme_manager()
        test_theme_colors()
        test_theme_persistence()
        test_custom_theme()
        
        print("🎉 All theme tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        app.quit()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)