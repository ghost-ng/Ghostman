"""
Style Templates for Ghostman Theme System.

Provides reusable style templates that use theme variables for consistent
styling across all components.
"""
import logging
from typing import Dict, Any
from .color_system import ColorSystem
logger = logging.getLogger("ghostman.style_templates")

class ButtonStyleManager:
    """
    Unified button styling manager that ensures consistency across all button types.
    
    Provides a single source of truth for button styling with:
    - Consistent 8px padding for all buttons
    - Consistent 4px border-radius for all buttons
    - Theme-aware color management
    - Support for all button states (normal, hover, pressed, disabled, toggle)
    """
    
    # Global button constants - ALL buttons must use these
    PADDING = "8px"
    BORDER_RADIUS = "4px"
    FONT_SIZE = "12px"
    DEFAULT_ICON_SIZE = 10  # Default icon size in pixels (compact)
    
    @staticmethod
    def get_icon_size():
        """Get unified icon size from settings, with fallback to default."""
        try:
            from ghostman.src.infrastructure.storage.settings_manager import settings
            # Try new simplified setting first, then old nested setting, then default
            return settings.get("icon_size", 
                   settings.get("icon_sizing.title_bar_icon_size", 
                   ButtonStyleManager.DEFAULT_ICON_SIZE))
        except:
            return ButtonStyleManager.DEFAULT_ICON_SIZE
    
    @staticmethod
    def get_computed_sizes():
        """Get computed icon and button sizes for debugging/documentation."""
        icon_size = ButtonStyleManager.get_icon_size()
        # Use same smart padding calculation as apply_unified_button_style
        if icon_size <= 10:
            padding_total = 2  # Minimal padding for tiny icons (8-10px)
        elif icon_size <= 16:
            padding_total = 4  # Small padding for small icons (11-16px)
        else:
            padding_total = 6  # Standard padding for larger icons (17px+)
        
        button_size = icon_size + padding_total
        padding_each_side = padding_total // 2
        
        return {
            "icon_size": icon_size,
            "button_size": button_size,
            "padding_total": padding_total,
            "padding_each_side": padding_each_side
        }
    
    @staticmethod
    def get_dynamic_css_padding():
        """Get CSS padding value based on icon size."""
        sizes = ButtonStyleManager.get_computed_sizes()
        return f"{sizes['padding_each_side']}px"
    
    @staticmethod
    def get_unified_button_style(colors, 
                               button_type: str = "push",
                               size: str = "medium",
                               state: str = "normal",
                               special_colors: dict = None) -> str:
        """
        Generate unified button styling that ensures ALL buttons look identical.
        
        Args:
            colors: ColorSystem instance
            button_type: "push", "tool", or "icon"
            size: "small", "medium", "large", or "icon"
            state: "normal", "toggle", "danger", "success", "warning"
            special_colors: Optional dict to override default colors for special states
            
        Returns:
            Complete CSS string for the button
        """
        # Size configurations with CONSISTENT padding and border-radius
        # ALL buttons use the same 8px padding and 4px border-radius
        size_configs = {
            "icon_button": {"min_width": "10px", "min_height": "10px"},
            "extra_small": {"min_width": "48px", "min_height": "28px"},
            "small": {"min_width": "60px", "min_height": "32px"},
            "medium": {"min_width": "80px", "min_height": "32px"},
            "large": {"min_width": "100px", "min_height": "36px"},
            "icon": {"min_width": "32px", "min_height": "32px"}
        }
        logger.debug(f"ButtonStyleManager: Generating style for {button_type} button of size {size} in state {state}")
        config = size_configs.get(size, size_configs["medium"])
        
        # Handle fallback colors when theme system is not available
        if colors is None:
            # Fallback colors for systems without theme support
            if state == "toggle":
                bg_color = "#FFA500"
                text_color = "#000000"
                hover_color = "#FFB733"
                active_color = "#E6940B"
            elif state == "danger":
                bg_color = "#F44336"
                text_color = "#FFFFFF"
                hover_color = "#F66356"
                active_color = "#D32F2F"
            elif state == "success":
                bg_color = "#4CAF50"
                text_color = "#FFFFFF"
                hover_color = "#66BB6A"
                active_color = "#388E3C"
            elif state == "warning":
                bg_color = "#FF9800"
                text_color = "#000000"
                hover_color = "#FFB74D"
                active_color = "#F57C00"
            else:  # normal
                bg_color = "rgba(255, 255, 255, 0.15)"
                text_color = "white"
                hover_color = "rgba(255, 255, 255, 0.25)"
                active_color = "rgba(255, 255, 255, 0.35)"
            
            border_color = "none" if button_type == "tool" else "rgba(255, 255, 255, 0.2)"
            disabled_bg = "rgba(255, 255, 255, 0.05)"
            disabled_text = "#666"
        else:
            # Determine base colors based on state
            if special_colors:
                bg_color = special_colors.get("background", colors.interactive_normal)
                text_color = special_colors.get("text", colors.text_primary)
                hover_color = special_colors.get("hover", colors.interactive_hover)
                active_color = special_colors.get("active", colors.interactive_active)
                border_color = special_colors.get("border", "none" if button_type == "tool" else colors.border_primary)
            else:
                # Default state colors
                if state == "toggle":
                    bg_color = colors.primary
                    text_color = colors.background_primary
                    hover_color = colors.primary_hover
                    active_color = colors.primary_hover
                elif state == "danger":
                    bg_color = colors.status_error
                    text_color = colors.text_primary
                    hover_color = colors.status_error  # Should be lighter in real implementation
                    active_color = colors.status_error
                elif state == "success":
                    bg_color = colors.status_success
                    text_color = colors.background_primary
                    hover_color = colors.status_success  # Should be lighter
                    active_color = colors.status_success
                elif state == "warning":
                    bg_color = colors.status_warning
                    text_color = colors.background_primary
                    hover_color = colors.status_warning  # Should be lighter
                    active_color = colors.status_warning
                else:  # normal
                    bg_color = colors.interactive_normal
                    text_color = colors.text_primary
                    hover_color = colors.interactive_hover
                    active_color = colors.interactive_active
                
                border_color = "none" if button_type == "tool" else colors.border_primary
            
            disabled_bg = colors.interactive_disabled
            disabled_text = colors.text_disabled
        
        # Widget selector based on button type
        widget_selector = "QToolButton" if button_type in ["tool", "icon"] else "QPushButton"
        border_style = "border: none;" if button_type == "tool" else f"border: 1px solid {border_color};"
        
        # Get dynamic CSS padding based on icon size
        css_padding = ButtonStyleManager.get_dynamic_css_padding()
        
        return f"""
        {widget_selector} {{
            background-color: {bg_color};
            color: {text_color};
            {border_style}
            border-radius: {ButtonStyleManager.BORDER_RADIUS};
            padding: {css_padding};
            margin: 0px;
            min-width: {config["min_width"]};
            min-height: {config["min_height"]};
            font-size: {ButtonStyleManager.FONT_SIZE};
            font-weight: normal;
        }}
        {widget_selector}:hover {{
            background-color: {hover_color};
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        {widget_selector}:pressed {{
            background-color: {active_color};
            border: 1px solid rgba(255, 255, 255, 0.5);
        }}
        {widget_selector}:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
        }}
        """
    
    @staticmethod
    def apply_unified_button_style(button, colors,
                                 button_type: str = "push",
                                 size: str = "medium", 
                                 state: str = "normal",
                                 special_colors: dict = None,
                                 emoji_font: str = None):
        """
        Apply unified styling to any button widget.
        
        This is the ONLY method that should be used to style buttons.
        
        Args:
            button: Qt button widget (QPushButton or QToolButton)
            colors: ColorSystem instance
            button_type: "push", "tool", or "icon" 
            size: "icon","extra_small","small", "medium", "large"
            state: "normal", "toggle", "danger", "success", "warning"
            special_colors: Optional dict for custom colors
            emoji_font: Optional font family for emoji buttons
        """
        # Get base style
        style = ButtonStyleManager.get_unified_button_style(
            colors, button_type, size, state, special_colors
        )
        
        # Add emoji font if specified
        if emoji_font:
            # Insert font-family into the base selector
            widget_selector = "QToolButton" if button_type in ["tool", "icon"] else "QPushButton"
            style = style.replace(
                f"{widget_selector} {{",
                f"{widget_selector} {{\n            font-family: {emoji_font};"
            )
        
        # Apply both CSS and Qt size constraints for reliable sizing
        # Get configurable icon size and calculate proportional button size
        icon_size = ButtonStyleManager.get_icon_size()
        # Use smarter padding calculation for better proportions with small icons
        if icon_size <= 10:
            padding = 2  # Minimal padding for tiny icons (8-10px)
        elif icon_size <= 16:
            padding = 4  # Small padding for small icons (11-16px)
        else:
            padding = 6  # Standard padding for larger icons (17px+)
        
        icon_button_size = icon_size + padding
        
        size_configs = {
            "icon": {"min_width": icon_button_size, "min_height": icon_button_size, "max_width": icon_button_size, "max_height": icon_button_size},
            "extra_small": {"min_width": 48, "min_height": 28},
            "small": {"min_width": 60, "min_height": 32},
            "medium": {"min_width": 80, "min_height": 32},
            "large": {"min_width": 100, "min_height": 36},
        }
        
        config = size_configs.get(size, size_configs["medium"])
        
        # Apply Qt size constraints for reliable sizing
        button.setMinimumSize(config["min_width"], config["min_height"])
        button.setMaximumSize(config.get("max_width", 16777215), config.get("max_height", 16777215))
        
        # Set icon size for buttons that have icons
        from PyQt6.QtCore import QSize
        icon_size = ButtonStyleManager.get_icon_size()
        button.setIconSize(QSize(icon_size, icon_size))
        
        # Apply the unified style
        button.setStyleSheet(style)
    
    @staticmethod
    def apply_plus_button_style(button, colors, emoji_font: str = None):
        """
        Apply special styling for plus button with asymmetric padding.
        
        Args:
            button: Qt button widget (QToolButton)
            colors: ColorSystem instance
            emoji_font: Optional font family for emoji buttons
        """
        # Get base style for icon button
        style = ButtonStyleManager.get_unified_button_style(
            colors, "tool", "icon", "normal", None
        )
        
        # Override padding for plus button (more padding on left for better visual balance)
        sizes = ButtonStyleManager.get_computed_sizes()
        base_padding = sizes['padding_each_side']
        right_padding = base_padding * 5  # Extra padding on right to create space before dropdown arrow
        left_padding = base_padding * 5  # More padding on left for visual balance
        
        old_padding = f"padding: {base_padding}px;"
        new_padding = f"padding: {base_padding}px {right_padding}px {base_padding}px {left_padding}px;"
        style = style.replace(old_padding, new_padding)
        
        # Adjust width for asymmetric padding
        base_width = sizes['button_size']
        new_width = base_width + (left_padding - base_padding) + (right_padding - base_padding)
        style = style.replace(f"min-width: {base_width}px;", f"min-width: {new_width}px;")
        
        # Add emoji font if specified
        if emoji_font:
            style = style.replace("QToolButton {", f"QToolButton {{\n            font-family: {emoji_font};")
        
        # Apply the style (no menu indicator CSS needed since we don't use menus)
        button.setStyleSheet(style)
        
        # Set icon size for consistency with other buttons
        from PyQt6.QtCore import QSize
        icon_size = ButtonStyleManager.get_icon_size()
        button.setIconSize(QSize(icon_size, icon_size))
        
        # Set same size constraints as other icon buttons for consistency
        sizes = ButtonStyleManager.get_computed_sizes()
        icon_size = sizes['icon_size']
        button_size = sizes['button_size'] + (left_padding - base_padding) + (right_padding - base_padding)  # Account for asymmetric padding
        
        button.setMinimumSize(button_size, sizes['button_size'])
        button.setMaximumSize(button_size, sizes['button_size'])


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
        """Style for REPL panel - NO opacity applied to root (only output display gets opacity)."""
        # Root panel always fully opaque to keep UI controls visible
        panel_bg = colors.background_secondary
        border_color = colors.border_primary
        
        return f"""
        #repl-root {{
            background-color: {panel_bg} !important;
            border-radius: 10px 10px 0px 0px;
            border: 1px solid {border_color};
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
            padding: 0px;
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
            border: none;
            border-radius: 4px;
            padding: 0px;
            margin-bottom: 2px;
        }}
        QToolButton:hover {{
            background-color: {colors.interactive_hover};
        }}
        QToolButton:pressed {{
            background-color: {colors.interactive_active};
        }}
        QToolButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
        }}
        QToolButton::menu-button {{
            border: none;
            width: 16px;
        }}
        """
    
    @staticmethod
    def get_uniform_button_style(colors: ColorSystem, size="medium") -> str:
        """
        DEPRECATED: Use ButtonStyleManager.get_unified_button_style() instead.
        Legacy wrapper for backward compatibility.
        """
        return ButtonStyleManager.get_unified_button_style(colors, "push", size)
    
    @staticmethod
    def get_uniform_tool_button_style(colors: ColorSystem, size="medium") -> str:
        """
        DEPRECATED: Use ButtonStyleManager.get_unified_button_style() instead.
        Legacy wrapper for backward compatibility.
        """
        return ButtonStyleManager.get_unified_button_style(colors, "tool", size)
    
    @staticmethod
    def get_icon_button_style(colors: ColorSystem, variant="normal") -> str:
        """
        Style for icon-only buttons with square dimensions.
        Uses the unified ButtonStyleManager for consistency.
        
        Args:
            colors: Color system to use
            variant: "normal", "primary", "danger", or "minimal"
        """
        # Map variants to states
        state_map = {
            "primary": "toggle",
            "danger": "danger", 
            "minimal": "normal",
            "normal": "normal"
        }
        
        state = state_map.get(variant, "normal")
        
        # Special handling for minimal variant
        if variant == "minimal":
            special_colors = {
                "background": "transparent",
                "text": colors.text_secondary,
                "hover": colors.interactive_hover,
                "active": colors.interactive_active
            }
            return ButtonStyleManager.get_unified_button_style(colors, "push", "icon", state, special_colors)
        
        return ButtonStyleManager.get_unified_button_style(colors, "push", "icon", state)
    
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
            padding: 8px 16px;
            margin-right: 3px;
            border-radius: 8px;
            min-width: 80px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors.primary};
            color: {colors.background_primary};
            border-color: {colors.primary};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {colors.interactive_hover};
            color: {colors.text_primary};
            border-color: {colors.border_focus};
        }}
        QTabBar::tab:first {{
            margin-left: 3px;
        }}
        QTabBar::tab:last {{
            margin-right: 3px;
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
            padding: 8px 16px;
            margin-right: 3px;
            border: 1px solid {colors.border_primary};
            border-radius: 8px 8px 0px 0px;
            border-bottom: none;
            min-width: 80px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors.primary};
            color: {colors.background_primary};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {colors.interactive_hover};
            color: {colors.text_primary};
            border-color: {colors.border_focus};
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
        
        /* Modern scroll bar styling */
        QScrollBar:vertical {{
            background-color: {colors.background_secondary};
            width: 12px;
            border: none;
            border-radius: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors.border_primary};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors.secondary};
        }}
        QScrollBar::handle:vertical:pressed {{
            background-color: {colors.primary};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
            height: 0px;
            width: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background-color: {colors.background_secondary};
            height: 12px;
            border: none;
            border-radius: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors.border_primary};
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.secondary};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background-color: {colors.primary};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
            height: 0px;
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
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
            color: {colors.background_primary};
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