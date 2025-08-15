"""
Style Templates for Ghostman Theme System.

Provides reusable style templates that use theme variables for consistent
styling across all components.
"""

from typing import Dict, Any
from .color_system import ColorSystem


class StyleTemplates:
    """
    Collection of style templates for different UI components.
    
    Each template method takes a ColorSystem and returns a CSS string
    that can be applied to PyQt6 widgets.
    """
    
    @staticmethod
    def get_style(template_name: str, colors: ColorSystem, **kwargs) -> str:
        """
        Get a style template by name.
        
        Args:
            template_name: Name of the template
            colors: Color system to use
            **kwargs: Additional parameters for the template
            
        Returns:
            CSS string for the template
        """
        method_name = f"get_{template_name}_style"
        if hasattr(StyleTemplates, method_name):
            method = getattr(StyleTemplates, method_name)
            return method(colors, **kwargs)
        else:
            raise ValueError(f"Unknown style template: {template_name}")
    
    @staticmethod
    def get_main_window_style(colors: ColorSystem) -> str:
        """Style for main application window."""
        return f"""
        QMainWindow {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        """
    
    @staticmethod
    def get_repl_panel_style(colors: ColorSystem, opacity: float = 0.9) -> str:
        """Style for REPL panel with transparency support."""
        # Use original hex color when fully opaque, rgba when transparent
        bg_color = colors.background_secondary
        if opacity >= 1.0:
            # Fully opaque - use original hex color
            panel_bg = bg_color
        elif bg_color.startswith('#'):
            # Transparent - convert to rgba
            r = int(bg_color[1:3], 16)
            g = int(bg_color[3:5], 16)
            b = int(bg_color[5:7], 16)
            panel_bg = f"rgba({r}, {g}, {b}, {opacity})"
        else:
            panel_bg = bg_color
        
        return f"""
        #repl-root {{
            background-color: {panel_bg};
            border-radius: 6px;
            border: 1px solid {colors.border_primary};
        }}
        """
    
    @staticmethod
    def get_title_frame_style(colors: ColorSystem) -> str:
        """Style for title frames and headers."""
        return f"""
        QFrame {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_secondary};
            border-radius: 4px;
            padding: 4px;
        }}
        QLabel {{
            color: {colors.text_primary};
            font-weight: bold;
        }}
        """
    
    @staticmethod
    def get_button_primary_style(colors: ColorSystem) -> str:
        """Style for primary buttons."""
        return f"""
        QPushButton {{
            background-color: {colors.primary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {colors.primary_hover};
            border-color: {colors.border_focus};
        }}
        QPushButton:pressed {{
            background-color: {colors.interactive_active};
        }}
        QPushButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        """
    
    @staticmethod
    def get_button_secondary_style(colors: ColorSystem) -> str:
        """Style for secondary buttons."""
        return f"""
        QPushButton {{
            background-color: {colors.interactive_normal};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {colors.interactive_hover};
            border-color: {colors.border_focus};
        }}
        QPushButton:pressed {{
            background-color: {colors.interactive_active};
        }}
        QPushButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        """
    
    @staticmethod
    def get_tool_button_style(colors: ColorSystem) -> str:
        """Style for tool buttons."""
        return f"""
        QToolButton {{
            background-color: {colors.interactive_normal};
            color: {colors.text_primary};
            border: 1px solid {colors.border_secondary};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QToolButton:hover {{
            background-color: {colors.interactive_hover};
            border-color: {colors.border_focus};
        }}
        QToolButton:pressed {{
            background-color: {colors.interactive_active};
        }}
        QToolButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        QToolButton::menu-button {{
            border: none;
            width: 16px;
        }}
        """
    
    @staticmethod
    def get_input_field_style(colors: ColorSystem) -> str:
        """Style for input fields and text edits."""
        return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 4px;
            selection-background-color: {colors.secondary};
            selection-color: {colors.text_primary};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors.border_focus};
            outline: none;
        }}
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
            border-color: {colors.border_secondary};
        }}
        """
    
    @staticmethod
    def get_combo_box_style(colors: ColorSystem) -> str:
        """Style for combo boxes."""
        return f"""
        QComboBox {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 4px 8px;
            min-width: 80px;
        }}
        QComboBox:hover {{
            border-color: {colors.border_focus};
        }}
        QComboBox:focus {{
            border-color: {colors.border_focus};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid {colors.text_secondary};
            margin-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors.background_secondary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            selection-background-color: {colors.secondary};
            selection-color: {colors.text_primary};
        }}
        """
    
    @staticmethod
    def get_list_widget_style(colors: ColorSystem) -> str:
        """Style for list widgets."""
        return f"""
        QListWidget {{
            background-color: {colors.background_secondary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 2px;
        }}
        QListWidget::item {{
            padding: 4px;
            border-radius: 2px;
            margin: 1px;
        }}
        QListWidget::item:selected {{
            background-color: {colors.secondary};
            color: {colors.text_primary};
        }}
        QListWidget::item:hover {{
            background-color: {colors.interactive_hover};
        }}
        """
    
    @staticmethod
    def get_progress_bar_style(colors: ColorSystem) -> str:
        """Style for progress bars."""
        return f"""
        QProgressBar {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            text-align: center;
            color: {colors.text_primary};
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {colors.primary};
            border-radius: 3px;
            margin: 1px;
        }}
        """
    
    @staticmethod
    def get_scroll_bar_style(colors: ColorSystem) -> str:
        """Style for scroll bars."""
        return f"""
        QScrollBar:vertical {{
            background-color: {colors.background_secondary};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors.interactive_normal};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors.interactive_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar:horizontal {{
            background-color: {colors.background_secondary};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors.interactive_normal};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.interactive_hover};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        """
    
    @staticmethod
    def get_menu_style(colors: ColorSystem) -> str:
        """Style for menus and context menus."""
        return f"""
        QMenu {{
            background-color: {colors.background_secondary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 12px;
            border-radius: 3px;
        }}
        QMenu::item:selected {{
            background-color: {colors.secondary};
            color: {colors.text_primary};
        }}
        QMenu::item:disabled {{
            color: {colors.text_disabled};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {colors.separator};
            margin: 2px;
        }}
        """
    
    @staticmethod
    def get_tab_widget_style(colors: ColorSystem) -> str:
        """Style for tab widgets."""
        return f"""
        QTabWidget::pane {{
            background-color: {colors.background_secondary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background-color: {colors.background_tertiary};
            color: {colors.text_secondary};
            border: 1px solid {colors.border_secondary};
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors.secondary};
            color: {colors.text_primary};
            border-color: {colors.border_focus};
        }}
        QTabBar::tab:hover {{
            background-color: {colors.interactive_hover};
            color: {colors.text_primary};
        }}
        QTabBar::tab:first {{
            border-top-left-radius: 4px;
            border-bottom-left-radius: 4px;
        }}
        QTabBar::tab:last {{
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            margin-right: 0px;
        }}
        """
    
    @staticmethod
    def get_dialog_style(colors: ColorSystem) -> str:
        """Style for dialogs and modal windows."""
        return f"""
        QDialog {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        QDialogButtonBox {{
            background-color: {colors.background_secondary};
            border-top: 1px solid {colors.separator};
        }}
        """
    
    @staticmethod
    def get_label_style(colors: ColorSystem, variant: str = "primary") -> str:
        """Style for labels with different variants."""
        color_map = {
            "primary": colors.text_primary,
            "secondary": colors.text_secondary,
            "tertiary": colors.text_tertiary,
            "success": colors.status_success,
            "warning": colors.status_warning,
            "error": colors.status_error,
            "info": colors.status_info,
        }
        
        text_color = color_map.get(variant, colors.text_primary)
        
        return f"""
        QLabel {{
            color: {text_color};
        }}
        """
    
    @staticmethod
    def get_status_style(colors: ColorSystem, status: str = "info") -> str:
        """Style for status indicators."""
        color_map = {
            "success": colors.status_success,
            "warning": colors.status_warning,
            "error": colors.status_error,
            "info": colors.status_info,
        }
        
        status_color = color_map.get(status, colors.status_info)
        
        return f"""
        color: {status_color};
        font-weight: bold;
        font-size: 10px;
        """
    
    @staticmethod
    def get_search_frame_style(colors: ColorSystem) -> str:
        """Style for search frames."""
        return f"""
        QFrame {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.status_warning};
            border-radius: 4px;
            padding: 4px;
        }}
        """
    
    @staticmethod
    def get_checkbox_style(colors: ColorSystem) -> str:
        """Style for checkboxes."""
        return f"""
        QCheckBox {{
            color: {colors.text_primary};
            spacing: 4px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors.border_primary};
            border-radius: 3px;
            background-color: {colors.background_tertiary};
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors.border_focus};
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors.primary};
            border-color: {colors.primary};
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {colors.primary_hover};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {colors.interactive_disabled};
            border-color: {colors.border_secondary};
        }}
        """
    
    @staticmethod
    def get_system_tray_style(colors: ColorSystem) -> str:
        """Style for system tray components."""
        return f"""
        QMenu {{
            background-color: {colors.background_secondary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
        }}
        QAction {{
            padding: 4px 8px;
        }}
        QAction:selected {{
            background-color: {colors.secondary};
        }}
        """
    
    @staticmethod
    def get_settings_dialog_style(colors: ColorSystem) -> str:
        """Comprehensive style for settings dialog."""
        return f"""
        /* Main dialog styling */
        QDialog {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        
        /* Tab widget styling */
        QTabWidget::pane {{
            border: 1px solid {colors.border_primary};
            background-color: {colors.background_primary};
        }}
        QTabWidget::tab-bar {{
            alignment: left;
        }}
        QTabBar::tab {{
            background-color: {colors.background_secondary};
            color: {colors.text_primary};
            padding: 8px 12px;
            margin-right: 2px;
            border: 1px solid {colors.border_primary};
            border-bottom: none;
        }}
        QTabBar::tab:selected {{
            background-color: {colors.primary};
            color: {colors.text_primary};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {colors.background_tertiary};
        }}
        
        /* Group box styling */
        QGroupBox {{
            color: {colors.text_primary};
            font-weight: bold;
            border: 1px solid {colors.border_primary};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        /* Label styling */
        QLabel {{
            color: {colors.text_primary};
        }}
        
        /* Input field styling */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 5px;
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {colors.border_focus};
            background-color: {colors.background_secondary};
        }}
        QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_tertiary};
        }}
        
        /* ComboBox styling */
        QComboBox {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            padding: 5px;
            min-width: 6em;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 15px;
            border-left-width: 1px;
            border-left-color: {colors.border_primary};
            border-left-style: solid;
        }}
        QComboBox::down-arrow {{
            color: {colors.text_primary};
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            selection-background-color: {colors.primary};
            border: 1px solid {colors.border_primary};
        }}
        QComboBox:hover {{
            border-color: {colors.border_focus};
        }}
        QComboBox:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_tertiary};
        }}
        
        /* CheckBox styling */
        QCheckBox {{
            color: {colors.text_primary};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        QCheckBox::indicator:unchecked {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors.primary};
            border: 1px solid {colors.primary};
            border-radius: 3px;
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors.border_focus};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {colors.interactive_disabled};
            border-color: {colors.border_secondary};
        }}
        
        /* Button styling */
        QPushButton {{
            background-color: {colors.primary};
            color: {colors.text_primary};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {colors.primary_hover};
        }}
        QPushButton:pressed {{
            background-color: {colors.primary_hover};
        }}
        QPushButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_tertiary};
        }}
        
        /* Special button colors */
        QPushButton[objectName="cancel_btn"] {{
            background-color: {colors.secondary};
        }}
        QPushButton[objectName="cancel_btn"]:hover {{
            background-color: {colors.secondary_hover};
        }}
        
        /* List widget styling */
        QListWidget {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
        }}
        QListWidget::item {{
            padding: 5px;
            border-bottom: 1px solid {colors.separator};
        }}
        QListWidget::item:selected {{
            background-color: {colors.primary};
        }}
        QListWidget::item:hover {{
            background-color: {colors.background_secondary};
        }}
        
        /* Splitter styling */
        QSplitter::handle {{
            background-color: {colors.separator};
        }}
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        /* Scroll bar styling */
        QScrollBar:vertical {{
            background-color: {colors.background_secondary};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors.border_secondary};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors.border_primary};
        }}
        QScrollBar:horizontal {{
            background-color: {colors.background_secondary};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors.border_secondary};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.border_primary};
        }}
        """