#!/usr/bin/env python3
"""
Example showing how to integrate the new theme-aware icon system
into existing Ghostman components.

This demonstrates both simple usage and advanced patterns for
automatic theme updates and fallback handling.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QPushButton, QToolButton, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QPixmap

# Example imports (adjust paths as needed in actual usage)
# from ghostman.src.ui.themes.icon_manager import (
#     get_themed_icon, get_themed_icon_path, register_widget_for_icon_updates
# )
# from ghostman.src.ui.themes.theme_manager import get_theme_manager


class ModernSaveButton(QPushButton):
    """
    Example of a save button that automatically uses theme-appropriate icons.
    
    This demonstrates how to create widgets that integrate seamlessly
    with the theme-aware icon system.
    """
    
    def __init__(self, text: str = "Save", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        
        # Set up the button with theme-aware icon
        self._setup_themed_icon()
        
        # Register for automatic updates when theme changes
        self._register_for_theme_updates()
    
    def _setup_themed_icon(self):
        """Set up the button with appropriate themed icon."""
        try:
            # Get theme-appropriate icon
            save_icon = get_themed_icon('save')
            self.setIcon(save_icon)
            
            # Apply theme-aware styling (optional)
            # You can also use the existing icon styling system
            from ghostman.src.ui.themes.icon_styling import apply_save_button_styling
            from ghostman.src.ui.themes.theme_manager import get_theme_manager
            
            theme_manager = get_theme_manager()
            apply_save_button_styling(self, theme_manager.current_theme, size=16)
            
        except ImportError:
            # Fallback if theme system not available
            self.setText("💾 Save")  # Unicode fallback
    
    def _register_for_theme_updates(self):
        """Register this widget to receive automatic icon updates."""
        try:
            register_widget_for_icon_updates(self, 'save', 'setIcon')
        except ImportError:
            # Theme system not available - no automatic updates
            pass


class ThemeAwareTitleBar(QWidget):
    """
    Example titlebar that uses multiple theme-aware icons.
    
    Demonstrates handling multiple icons and automatic updates
    in a complex component.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.minimize_button = None
        self.close_button = None
        self.help_button = None
        
        self._setup_ui()
        self._setup_themed_icons()
        self._register_all_widgets()
    
    def _setup_ui(self):
        """Create the UI elements."""
        layout = QVBoxLayout(self)
        
        # Create buttons
        self.minimize_button = QToolButton()
        self.minimize_button.setToolTip("Minimize")
        
        self.close_button = QToolButton()
        self.close_button.setToolTip("Close")
        
        self.help_button = QToolButton() 
        self.help_button.setToolTip("Help")
        
        # Add to layout
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.help_button)
        layout.addWidget(self.close_button)
    
    def _setup_themed_icons(self):
        """Set up all buttons with theme-appropriate icons."""
        icon_mappings = {
            self.minimize_button: 'minimize',
            self.close_button: 'exit', 
            self.help_button: 'help'
        }
        
        for button, icon_name in icon_mappings.items():
            try:
                icon = get_themed_icon(icon_name)
                button.setIcon(icon)
            except ImportError:
                # Fallback text
                fallback_text = {'minimize': '−', 'exit': '×', 'help': '?'}
                button.setText(fallback_text.get(icon_name, '?'))
    
    def _register_all_widgets(self):
        """Register all widgets for automatic theme updates."""
        try:
            register_widget_for_icon_updates(self.minimize_button, 'minimize')
            register_widget_for_icon_updates(self.close_button, 'exit')
            register_widget_for_icon_updates(self.help_button, 'help')
        except ImportError:
            pass


class SmartIconLabel(QLabel):
    """
    Example label that displays icons with automatic theme updates and fallbacks.
    
    Shows advanced usage including custom fallback handling and
    multiple icon preferences.
    """
    
    def __init__(self, icon_name: str, size: tuple = (24, 24), 
                 fallback_icons: Optional[list] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.icon_name = icon_name
        self.size = size
        self.fallback_icons = fallback_icons or []
        
        self._setup_icon()
        self._register_for_updates()
    
    def _setup_icon(self):
        """Set up the icon with smart fallback handling."""
        try:
            # Try primary icon
            icon_path = get_themed_icon_path(self.icon_name)
            
            if icon_path and icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                pixmap = pixmap.scaled(self.size[0], self.size[1])
                self.setPixmap(pixmap)
                return
            
            # Try fallback icons
            for fallback_name in self.fallback_icons:
                fallback_path = get_themed_icon_path(fallback_name)
                if fallback_path and fallback_path.exists():
                    pixmap = QPixmap(str(fallback_path))
                    pixmap = pixmap.scaled(self.size[0], self.size[1])
                    self.setPixmap(pixmap)
                    return
            
            # No icon found - show text fallback
            self.setText(f"[{self.icon_name}]")
            
        except ImportError:
            # Theme system not available
            self.setText(f"[{self.icon_name}]")
    
    def _register_for_updates(self):
        """Register for theme updates with custom update method."""
        try:
            register_widget_for_icon_updates(self, self.icon_name, '_update_icon')
        except ImportError:
            pass
    
    def _update_icon(self, new_icon: QIcon):
        """Custom update method that handles QIcon to QPixmap conversion."""
        if not new_icon.isNull():
            pixmap = new_icon.pixmap(self.size[0], self.size[1])
            self.setPixmap(pixmap)
        else:
            # Fallback to text
            self.setText(f"[{self.icon_name}]")


class ManualThemeHandler:
    """
    Example of manual theme handling for components that need
    more control over the icon update process.
    
    Useful for complex components or when automatic registration
    isn't sufficient.
    """
    
    def __init__(self, widget_dict: dict):
        """
        Initialize with a dictionary of widgets and their icon names.
        
        Args:
            widget_dict: {widget: icon_name} mapping
        """
        self.widgets = widget_dict
        self._theme_timer = None
        
        # Connect to theme changes manually
        self._connect_to_theme_changes()
        
        # Set up initial icons
        self.update_all_icons()
    
    def _connect_to_theme_changes(self):
        """Connect to theme manager signals for updates."""
        try:
            from ghostman.src.ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            theme_manager.theme_changed.connect(self._on_theme_changed)
        except ImportError:
            pass
    
    def _on_theme_changed(self, color_system):
        """Handle theme changes with debouncing."""
        # Debounce rapid theme changes
        if self._theme_timer:
            self._theme_timer.stop()
        
        self._theme_timer = QTimer()
        self._theme_timer.setSingleShot(True)
        self._theme_timer.timeout.connect(self.update_all_icons)
        self._theme_timer.start(100)  # 100ms delay
    
    def update_all_icons(self):
        """Update all registered widgets with new icons."""
        for widget, icon_name in self.widgets.items():
            try:
                new_icon = get_themed_icon(icon_name)
                
                # Handle different widget types
                if hasattr(widget, 'setIcon'):
                    widget.setIcon(new_icon)
                elif hasattr(widget, 'setPixmap'):
                    pixmap = new_icon.pixmap(16, 16)  # Default size
                    widget.setPixmap(pixmap)
                    
            except Exception as e:
                print(f"Failed to update icon for {widget}: {e}")


def demonstration_usage():
    """
    Demonstration of various usage patterns.
    This shows how the icon system would be used in practice.
    """
    
    print("=== Ghostman Theme-Aware Icon System Usage Examples ===")
    
    # Example 1: Simple icon usage
    print("\n1. Simple Icon Usage:")
    print("   save_icon = get_themed_icon('save')")
    print("   button.setIcon(save_icon)")
    
    # Example 2: Path-based usage
    print("\n2. Path-Based Usage:")
    print("   help_path = get_themed_icon_path('help')")
    print("   if help_path:")
    print("       pixmap = QPixmap(str(help_path))")
    
    # Example 3: Widget registration
    print("\n3. Automatic Updates:")
    print("   register_widget_for_icon_updates(button, 'save')")
    print("   # Button automatically updates when theme changes")
    
    # Example 4: Theme information
    print("\n4. Theme Information:")
    print("   theme_manager = get_theme_manager()")
    print("   print(f'Current mode: {theme_manager.current_theme_mode}')")
    print("   print(f'Icon suffix: {theme_manager.current_icon_suffix}')")
    
    # Example 5: Fallback handling
    print("\n5. Smart Fallback:")
    print("   # Try primary icon, then fallbacks")
    print("   for icon_name in ['custom_save', 'save', 'plus']:")
    print("       path = get_themed_icon_path(icon_name)")
    print("       if path: break")
    
    print("\n=== Integration Benefits ===")
    benefits = [
        "✅ Automatic theme-appropriate icon selection",
        "✅ WCAG 2.1 AA contrast compliance", 
        "✅ Seamless theme switching without restart",
        "✅ Intelligent fallback handling",
        "✅ Performance optimized with caching",
        "✅ Memory safe with weak references"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")


if __name__ == "__main__":
    demonstration_usage()