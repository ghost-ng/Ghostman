"""Theme management system for Ghostman."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging
from enum import Enum

class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"

@dataclass
class ThemeColors:
    """Color palette for a theme."""
    # Primary colors
    primary: str = "#4A90E2"
    primary_hover: str = "#5A9FEF"
    primary_pressed: str = "#3A80D2"
    
    # Background colors
    background: str = "rgba(40, 40, 40, 200)"
    background_light: str = "rgba(60, 60, 60, 200)"
    background_dark: str = "rgba(30, 30, 30, 200)"
    
    # Text colors
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#E0E0E0"
    text_disabled: str = "rgba(255, 255, 255, 100)"
    
    # Message colors
    user_message_bg: str = "rgba(100, 150, 200, 150)"
    ai_message_bg: str = "rgba(80, 80, 80, 150)"
    user_message_text: str = "#FFFFFF"
    ai_message_text: str = "#E0E0E0"
    
    # Border and accent colors
    border: str = "rgba(255, 255, 255, 50)"
    border_hover: str = "rgba(255, 255, 255, 100)"
    accent: str = "#87CEEB"
    warning: str = "#FFB347"
    error: str = "#FF6B6B"
    success: str = "#4CAF50"
    
    # Avatar colors
    avatar_glow: str = "rgba(135, 206, 235, 100)"
    avatar_border: str = "#4A90E2"
    avatar_notification: str = "rgba(255, 215, 0, 200)"

@dataclass
class ThemeFonts:
    """Font configuration for a theme."""
    family: str = "Segoe UI"
    size_small: int = 11
    size_normal: int = 13
    size_large: int = 16
    size_title: int = 18
    weight_normal: int = 400
    weight_bold: int = 700

@dataclass
class ThemeSpacing:
    """Spacing configuration for a theme."""
    padding_small: int = 5
    padding_normal: int = 10
    padding_large: int = 15
    margin_small: int = 5
    margin_normal: int = 10
    margin_large: int = 20
    border_radius: int = 8
    border_width: int = 1

@dataclass
class Theme:
    """Complete theme configuration."""
    name: str
    mode: ThemeMode
    colors: ThemeColors
    fonts: ThemeFonts
    spacing: ThemeSpacing
    custom_css: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary."""
        return {
            'name': self.name,
            'mode': self.mode.value,
            'colors': self.colors.__dict__,
            'fonts': self.fonts.__dict__,
            'spacing': self.spacing.__dict__,
            'custom_css': self.custom_css
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create theme from dictionary."""
        colors = ThemeColors(**data.get('colors', {}))
        fonts = ThemeFonts(**data.get('fonts', {}))
        spacing = ThemeSpacing(**data.get('spacing', {}))
        
        return cls(
            name=data.get('name', 'Custom'),
            mode=ThemeMode(data.get('mode', 'custom')),
            colors=colors,
            fonts=fonts,
            spacing=spacing,
            custom_css=data.get('custom_css', '')
        )

class ThemeManager:
    """Manages application themes."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        
        if config_path:
            self.config_path = config_path
        else:
            # Use APPDATA on Windows, fallback to home on other systems
            import os
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.config_path = Path(appdata) / "Ghostman" / "themes.json"
            else:
                self.config_path = Path.home() / ".ghostman" / "themes.json"
        
        self.current_theme: Theme = self.get_dark_theme()
        self.custom_themes: Dict[str, Theme] = {}
        self.load_themes()
    
    def get_dark_theme(self) -> Theme:
        """Get the default dark theme."""
        return Theme(
            name="Dark",
            mode=ThemeMode.DARK,
            colors=ThemeColors(),  # Default values are dark theme
            fonts=ThemeFonts(),
            spacing=ThemeSpacing()
        )
    
    def get_light_theme(self) -> Theme:
        """Get the light theme."""
        return Theme(
            name="Light",
            mode=ThemeMode.LIGHT,
            colors=ThemeColors(
                primary="#2196F3",
                primary_hover="#42A5F5",
                primary_pressed="#1976D2",
                background="rgba(255, 255, 255, 240)",
                background_light="rgba(245, 245, 245, 240)",
                background_dark="rgba(230, 230, 230, 240)",
                text_primary="#212121",
                text_secondary="#616161",
                text_disabled="rgba(0, 0, 0, 100)",
                user_message_bg="rgba(33, 150, 243, 180)",
                ai_message_bg="rgba(224, 224, 224, 200)",
                user_message_text="#FFFFFF",
                ai_message_text="#212121",
                border="rgba(0, 0, 0, 50)",
                border_hover="rgba(0, 0, 0, 100)",
                accent="#2196F3",
                warning="#FF9800",
                error="#F44336",
                success="#4CAF50",
                avatar_glow="rgba(33, 150, 243, 100)",
                avatar_border="#2196F3",
                avatar_notification="rgba(255, 152, 0, 200)"
            ),
            fonts=ThemeFonts(),
            spacing=ThemeSpacing()
        )
    
    def get_neon_theme(self) -> Theme:
        """Get a neon/cyberpunk theme."""
        return Theme(
            name="Neon",
            mode=ThemeMode.CUSTOM,
            colors=ThemeColors(
                primary="#FF00FF",
                primary_hover="#FF33FF",
                primary_pressed="#CC00CC",
                background="rgba(10, 10, 30, 230)",
                background_light="rgba(20, 20, 50, 230)",
                background_dark="rgba(5, 5, 20, 230)",
                text_primary="#00FFFF",
                text_secondary="#00CCCC",
                text_disabled="rgba(0, 255, 255, 100)",
                user_message_bg="rgba(255, 0, 255, 150)",
                ai_message_bg="rgba(0, 255, 255, 100)",
                user_message_text="#FFFFFF",
                ai_message_text="#000000",
                border="rgba(0, 255, 255, 100)",
                border_hover="rgba(255, 0, 255, 150)",
                accent="#FFFF00",
                warning="#FFA500",
                error="#FF0000",
                success="#00FF00",
                avatar_glow="rgba(0, 255, 255, 150)",
                avatar_border="#FF00FF",
                avatar_notification="rgba(255, 255, 0, 255)"
            ),
            fonts=ThemeFonts(family="Consolas"),
            spacing=ThemeSpacing(border_radius=4)
        )
    
    def get_ocean_theme(self) -> Theme:
        """Get an ocean/aqua theme."""
        return Theme(
            name="Ocean",
            mode=ThemeMode.CUSTOM,
            colors=ThemeColors(
                primary="#00ACC1",
                primary_hover="#00BCD4",
                primary_pressed="#0097A7",
                background="rgba(0, 50, 70, 200)",
                background_light="rgba(0, 70, 90, 200)",
                background_dark="rgba(0, 30, 50, 200)",
                text_primary="#E0F7FA",
                text_secondary="#B2EBF2",
                text_disabled="rgba(178, 235, 242, 100)",
                user_message_bg="rgba(0, 188, 212, 150)",
                ai_message_bg="rgba(0, 77, 107, 150)",
                user_message_text="#FFFFFF",
                ai_message_text="#E0F7FA",
                border="rgba(0, 188, 212, 100)",
                border_hover="rgba(0, 188, 212, 200)",
                accent="#00E5FF",
                warning="#FFB300",
                error="#FF5252",
                success="#69F0AE",
                avatar_glow="rgba(0, 188, 212, 150)",
                avatar_border="#00ACC1",
                avatar_notification="rgba(255, 179, 0, 200)"
            ),
            fonts=ThemeFonts(),
            spacing=ThemeSpacing(border_radius=12)
        )
    
    def get_forest_theme(self) -> Theme:
        """Get a forest/nature theme."""
        return Theme(
            name="Forest",
            mode=ThemeMode.CUSTOM,
            colors=ThemeColors(
                primary="#4CAF50",
                primary_hover="#66BB6A",
                primary_pressed="#388E3C",
                background="rgba(33, 47, 33, 220)",
                background_light="rgba(46, 64, 46, 220)",
                background_dark="rgba(20, 30, 20, 220)",
                text_primary="#E8F5E9",
                text_secondary="#C8E6C9",
                text_disabled="rgba(200, 230, 201, 100)",
                user_message_bg="rgba(76, 175, 80, 150)",
                ai_message_bg="rgba(62, 89, 62, 150)",
                user_message_text="#FFFFFF",
                ai_message_text="#E8F5E9",
                border="rgba(139, 195, 74, 100)",
                border_hover="rgba(139, 195, 74, 200)",
                accent="#8BC34A",
                warning="#FFC107",
                error="#D32F2F",
                success="#689F38",
                avatar_glow="rgba(76, 175, 80, 150)",
                avatar_border="#4CAF50",
                avatar_notification="rgba(255, 193, 7, 200)"
            ),
            fonts=ThemeFonts(),
            spacing=ThemeSpacing(border_radius=10)
        )
    
    def get_all_builtin_themes(self) -> Dict[str, Theme]:
        """Get all built-in themes."""
        return {
            'dark': self.get_dark_theme(),
            'light': self.get_light_theme(),
            'neon': self.get_neon_theme(),
            'ocean': self.get_ocean_theme(),
            'forest': self.get_forest_theme()
        }
    
    def load_themes(self):
        """Load custom themes from config file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Load current theme
                    current_theme_name = data.get('current_theme', 'dark')
                    current_theme_data = data.get('current_theme_data')
                    
                    if current_theme_data:
                        self.current_theme = Theme.from_dict(current_theme_data)
                    else:
                        # Load from built-in themes
                        builtin = self.get_all_builtin_themes()
                        self.current_theme = builtin.get(current_theme_name, self.get_dark_theme())
                    
                    # Load custom themes
                    custom_themes_data = data.get('custom_themes', {})
                    for name, theme_data in custom_themes_data.items():
                        self.custom_themes[name] = Theme.from_dict(theme_data)
                    
                    self.logger.info(f"Loaded {len(self.custom_themes)} custom themes")
            else:
                self.save_themes()  # Save default configuration
                
        except Exception as e:
            self.logger.error(f"Error loading themes: {e}")
    
    def save_themes(self):
        """Save themes to config file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data
            custom_themes_data = {
                name: theme.to_dict() 
                for name, theme in self.custom_themes.items()
            }
            
            data = {
                'current_theme': self.current_theme.name.lower(),
                'current_theme_data': self.current_theme.to_dict(),
                'custom_themes': custom_themes_data
            }
            
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info("Themes saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving themes: {e}")
    
    def apply_theme(self, theme_name: str) -> bool:
        """Apply a theme by name."""
        try:
            # Check built-in themes
            builtin = self.get_all_builtin_themes()
            if theme_name.lower() in builtin:
                self.current_theme = builtin[theme_name.lower()]
                self.save_themes()
                self.logger.info(f"Applied built-in theme: {theme_name}")
                return True
            
            # Check custom themes
            if theme_name in self.custom_themes:
                self.current_theme = self.custom_themes[theme_name]
                self.save_themes()
                self.logger.info(f"Applied custom theme: {theme_name}")
                return True
            
            self.logger.warning(f"Theme not found: {theme_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error applying theme: {e}")
            return False
    
    def create_custom_theme(self, name: str, base_theme: Optional[str] = None) -> Theme:
        """Create a new custom theme."""
        # Start with base theme or current theme
        if base_theme:
            builtin = self.get_all_builtin_themes()
            base = builtin.get(base_theme.lower(), self.current_theme)
        else:
            base = self.current_theme
        
        # Create new theme with custom name
        custom_theme = Theme(
            name=name,
            mode=ThemeMode.CUSTOM,
            colors=ThemeColors(**base.colors.__dict__),
            fonts=ThemeFonts(**base.fonts.__dict__),
            spacing=ThemeSpacing(**base.spacing.__dict__),
            custom_css=base.custom_css
        )
        
        # Save to custom themes
        self.custom_themes[name] = custom_theme
        self.save_themes()
        
        self.logger.info(f"Created custom theme: {name}")
        return custom_theme
    
    def delete_custom_theme(self, name: str) -> bool:
        """Delete a custom theme."""
        if name in self.custom_themes:
            del self.custom_themes[name]
            self.save_themes()
            self.logger.info(f"Deleted custom theme: {name}")
            return True
        return False
    
    def get_stylesheet(self, widget_type: str = "general") -> str:
        """Generate Qt stylesheet for current theme."""
        theme = self.current_theme
        colors = theme.colors
        fonts = theme.fonts
        spacing = theme.spacing
        
        # Base stylesheet components
        base_styles = {
            'general': f"""
                QWidget {{
                    font-family: {fonts.family};
                    font-size: {fonts.size_normal}px;
                    color: {colors.text_primary};
                }}
                QPushButton {{
                    background-color: {colors.primary};
                    color: {colors.text_primary};
                    border: none;
                    border-radius: {spacing.border_radius}px;
                    padding: {spacing.padding_normal}px;
                    font-weight: {fonts.weight_bold};
                }}
                QPushButton:hover {{
                    background-color: {colors.primary_hover};
                }}
                QPushButton:pressed {{
                    background-color: {colors.primary_pressed};
                }}
                QPushButton:disabled {{
                    background-color: {colors.background_light};
                    color: {colors.text_disabled};
                }}
                QLineEdit, QTextEdit {{
                    background-color: {colors.background};
                    border: {spacing.border_width}px solid {colors.border};
                    border-radius: {spacing.border_radius}px;
                    padding: {spacing.padding_small}px;
                    color: {colors.text_primary};
                }}
                QLineEdit:focus, QTextEdit:focus {{
                    border: {spacing.border_width}px solid {colors.border_hover};
                }}
            """,
            
            'prompt_interface': f"""
                QFrame {{
                    background-color: {colors.background};
                    border-radius: {spacing.border_radius}px;
                }}
                QScrollArea {{
                    background-color: {colors.background_dark};
                    border: {spacing.border_width}px solid {colors.border};
                    border-radius: {spacing.border_radius}px;
                }}
                QLabel {{
                    color: {colors.text_primary};
                }}
            """,
            
            'avatar': f"""
                QWidget {{
                    background-color: transparent;
                }}
                QLabel {{
                    border-radius: 30px;
                }}
            """,
            
            'settings': f"""
                QDialog {{
                    background-color: {colors.background_light};
                }}
                QTabWidget::pane {{
                    background-color: {colors.background};
                    border: {spacing.border_width}px solid {colors.border};
                    border-radius: {spacing.border_radius}px;
                }}
                QTabBar::tab {{
                    background-color: {colors.background_light};
                    color: {colors.text_secondary};
                    padding: {spacing.padding_normal}px;
                    margin-right: {spacing.margin_small}px;
                    border-top-left-radius: {spacing.border_radius}px;
                    border-top-right-radius: {spacing.border_radius}px;
                }}
                QTabBar::tab:selected {{
                    background-color: {colors.primary};
                    color: {colors.text_primary};
                }}
                QGroupBox {{
                    border: {spacing.border_width}px solid {colors.border};
                    border-radius: {spacing.border_radius}px;
                    margin-top: {spacing.margin_normal}px;
                    padding-top: {spacing.padding_normal}px;
                    font-weight: {fonts.weight_bold};
                }}
                QGroupBox::title {{
                    color: {colors.accent};
                }}
            """
        }
        
        # Combine requested styles
        if widget_type in base_styles:
            stylesheet = base_styles[widget_type]
        else:
            stylesheet = base_styles['general']
        
        # Add custom CSS if present
        if theme.custom_css:
            stylesheet += "\n" + theme.custom_css
        
        return stylesheet
    
    def export_theme(self, theme_name: str, export_path: Path) -> bool:
        """Export a theme to a file."""
        try:
            theme = None
            
            # Find theme
            builtin = self.get_all_builtin_themes()
            if theme_name.lower() in builtin:
                theme = builtin[theme_name.lower()]
            elif theme_name in self.custom_themes:
                theme = self.custom_themes[theme_name]
            
            if not theme:
                return False
            
            # Export to file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(theme.to_dict(), f, indent=2)
            
            self.logger.info(f"Exported theme {theme_name} to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting theme: {e}")
            return False
    
    def import_theme(self, import_path: Path) -> Optional[Theme]:
        """Import a theme from a file."""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            theme = Theme.from_dict(theme_data)
            
            # Add to custom themes with unique name
            base_name = theme.name
            counter = 1
            while theme.name in self.custom_themes:
                theme.name = f"{base_name} ({counter})"
                counter += 1
            
            self.custom_themes[theme.name] = theme
            self.save_themes()
            
            self.logger.info(f"Imported theme: {theme.name}")
            return theme
            
        except Exception as e:
            self.logger.error(f"Error importing theme: {e}")
            return None