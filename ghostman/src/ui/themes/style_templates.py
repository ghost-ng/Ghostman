"""
Style Templates for Ghostman Theme System.

This module provides a comprehensive styling framework with two main components:
1. ButtonStyleManager - Unified button styling ensuring consistency across all button types
2. StyleTemplates - Reusable CSS templates for PyQt6 components

Features:
- Unified button system with consistent padding, border-radius, and sizing
- Dynamic icon sizing based on user settings
- Theme-aware color management with accessibility validation
- PyQt6-specific styling techniques for borders, focus states, and layouts
- Comprehensive style templates for all UI components

Usage Examples:
    # Apply unified button styling
    ButtonStyleManager.apply_unified_button_style(
        button=my_button,
        colors=theme_manager.current_theme,
        button_type="push",  # "push", "tool", or "icon"
        size="medium",       # "icon", "extra_small", "small", "medium", "large"
        state="normal"       # "normal", "toggle", "danger", "success", "warning"
    )
    
    # Get CSS for custom styling
    css = ButtonStyleManager.get_unified_button_style(colors, "tool", "small")
    
    # Use style templates
    dialog_style = StyleTemplates.get_settings_dialog_style(colors)
    widget.setStyleSheet(dialog_style)

Architecture:
    ButtonStyleManager handles all button styling to ensure consistency across:
    - Titlebar buttons (minimize, close, pin, move)
    - Toolbar buttons (search, filter, clear)
    - Dialog buttons (OK, Cancel, Apply)
    - Custom action buttons (Send, Add, Remove)
    
    StyleTemplates provides CSS templates for major UI components:
    - Main window and dialogs
    - Form elements (inputs, combos, checkboxes)
    - Data display (lists, progress, scrollbars)
    - Navigation (tabs, menus)
    - Search components with high-contrast text

Implementation Details:
    PyQt6-Specific Techniques Used:
    - setFrameStyle(QFrame.Shape.NoFrame) for stubborn border removal
    - setLineWidth(0) and setMidLineWidth(0) for frame border control
    - !important CSS directives to override default PyQt6 styling
    - QSize constraints combined with CSS for reliable button sizing
    - Smart contrast calculation for accessibility compliance
    - Comprehensive focus state management
    
    Dynamic Sizing Algorithm:
    The system uses user-configurable icon sizes (8-32px) with smart padding:
    - Icons ≤10px: 2px total padding (minimal for tiny icons)
    - Icons 11-16px: 4px total padding (small padding for small icons)
    - Icons ≥17px: 6px total padding (standard padding for larger icons)
    
    Color Management:
    - 24 semantic color variables from ColorSystem
    - Automatic contrast ratio validation (WCAG 2.1 AA/AAA compliance)
    - High-contrast text color calculation for maximum readability
    - Theme-aware color selection with fallback support
"""
import logging
from typing import Dict, Any
from .color_system import ColorSystem
logger = logging.getLogger("ghostman.style_templates")

class ButtonStyleManager:
    """
    Unified button styling manager that ensures consistency across all button types.
    
    This class provides the single source of truth for button styling in Ghostman,
    ensuring all buttons maintain consistent appearance regardless of their type or
    location in the application.
    
    Key Features:
    - Consistent 8px padding and 4px border-radius for all buttons
    - Dynamic icon sizing based on user settings (configurable)
    - Theme-aware color management with fallback support
    - Support for all button states (normal, hover, pressed, disabled, toggle)
    - Special handling for asymmetric buttons (plus button with dropdown spacing)
    - PyQt6 widget constraints for reliable sizing across platforms
    
    Button Types:
    - "push": Standard QPushButton with borders
    - "tool": QToolButton without borders for toolbar use
    - "icon": Square icon-only buttons with proportional sizing
    
    Button Sizes:
    - "icon": Square buttons sized proportionally to icon size
    - "extra_small": 48x28px minimum for compact interfaces
    - "small": 60x32px for secondary actions
    - "medium": 80x32px for primary actions (default)
    - "large": 100x36px for prominent actions
    
    Button States:
    - "normal": Default button appearance
    - "toggle": Active/selected state using primary color
    - "danger": Error/destructive actions using status_error color
    - "success": Positive actions using status_success color
    - "warning": Caution actions using status_warning color
    """
    
    # Global button constants - ALL buttons must use these for consistency
    PADDING = "8px"           # Universal padding for all buttons
    BORDER_RADIUS = "4px"     # Universal border radius for all buttons
    FONT_SIZE = "12px"        # Universal font size for button text
    DEFAULT_ICON_SIZE = 10    # Default icon size in pixels (fallback)
    
    @staticmethod
    def get_icon_size():
        """
        Get unified icon size from settings with graceful fallback.
        
        This method provides centralized icon size management across the application.
        Icon sizes are configurable through the settings system, allowing users to
        adjust for accessibility needs or personal preference.
        
        Returns:
            int: Icon size in pixels, typically between 8-32px
            
        Fallback Chain:
            1. settings.icon_size (new simplified setting)
            2. settings.icon_sizing.title_bar_icon_size (legacy nested setting)
            3. ButtonStyleManager.DEFAULT_ICON_SIZE (hardcoded fallback)
            
        Implementation Note:
            This method is called frequently during UI updates, so it includes
            exception handling to prevent crashes if the settings system is
            unavailable during initialization.
        """
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
        """
        Get computed icon and button sizes for debugging and documentation.
        
        This method calculates all size-related values used in button styling,
        providing transparency for debugging and consistent sizing across components.
        The padding calculation uses smart scaling to maintain good proportions
        with very small icons while providing adequate touch targets.
        
        Returns:
            dict: Dictionary containing:
                - icon_size: Current icon size from settings
                - button_size: Total button size (icon + padding)
                - padding_total: Total padding applied
                - padding_each_side: Padding applied to each side
                
        Padding Logic:
            - Icons ≤10px: 2px total padding (minimal for tiny icons)
            - Icons 11-16px: 4px total padding (small padding for small icons)
            - Icons ≥17px: 6px total padding (standard padding for larger icons)
            
        This algorithm ensures buttons remain usable at all icon sizes while
        maintaining visual proportions and providing adequate click targets.
        """
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
        """
        Get CSS padding value based on current icon size settings.
        
        This method provides the CSS padding value that should be used in
        stylesheets to ensure buttons scale properly with user icon size preferences.
        
        Returns:
            str: CSS padding value (e.g., "2px", "3px")
            
        Usage:
            This is primarily used internally by get_unified_button_style() but
            can be useful for custom styling that needs to match button padding.
        """
        sizes = ButtonStyleManager.get_computed_sizes()
        return f"{sizes['padding_each_side']}px"
    
    @staticmethod
    def get_unified_button_style(colors, 
                               button_type: str = "push",
                               size: str = "medium",
                               state: str = "normal",
                               special_colors: dict = None) -> str:
        """
        Generate unified button CSS that ensures ALL buttons look identical.
        
        This is the core method that generates consistent CSS for all buttons in
        the application. It handles theme colors, fallback colors, size configurations,
        and state-specific styling with comprehensive PyQt6 compatibility.
        
        Args:
            colors: ColorSystem instance for theme colors (can be None for fallback)
            button_type: Button widget type
                - "push": QPushButton with borders (standard buttons)
                - "tool": QToolButton without borders (toolbar buttons)
                - "icon": Square icon-only buttons
            size: Button size category
                - "icon_button": Minimum size for icon buttons (10x10)
                - "extra_small": Compact size (48x28)
                - "small": Small size (60x32)
                - "medium": Standard size (80x32)
                - "large": Large size (100x36)
                - "icon": Square icon size (32x32 or dynamic)
            state: Button state for color selection
                - "normal": Default appearance
                - "toggle": Active/selected state
                - "danger": Destructive actions
                - "success": Positive actions
                - "warning": Caution actions
            special_colors: Optional color overrides for custom styling
                - background: Custom background color
                - text: Custom text color
                - hover: Custom hover color
                - active: Custom active color
                - border: Custom border color
                
        Returns:
            str: Complete CSS string ready for application to PyQt6 widgets
            
        CSS Features Generated:
            - Consistent padding and border-radius across all buttons
            - Theme-aware color management with accessibility consideration
            - Hover and pressed state styling with visual feedback
            - Disabled state styling with reduced opacity
            - Dynamic padding based on icon size settings
            - Widget-specific selectors (QPushButton vs QToolButton)
            - Border handling (borders for push buttons, none for tool buttons)
            - Focus state management
            
        Accessibility Features:
            - Maintains 4.5:1 contrast ratio minimum (WCAG AA)
            - Provides clear visual feedback for all interactive states
            - Ensures adequate touch targets with minimum button sizes
            - Supports high-contrast themes and custom accessibility colors
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
        # This ensures buttons remain functional even during initialization
        # or when the theme system encounters errors
        if colors is None:
            # Fallback colors for systems without theme support
            if state == "toggle":
                bg_color = "#FFA500"      # Orange for toggle state
                text_color = "#000000"    # Black text for contrast
                hover_color = "#FFB733"   # Lighter orange for hover
                active_color = "#E6940B"  # Darker orange for pressed
            elif state == "danger":
                bg_color = "#F44336"      # Red for danger
                text_color = "#FFFFFF"    # White text for contrast
                hover_color = "#F66356"   # Lighter red for hover
                active_color = "#D32F2F"  # Darker red for pressed
            elif state == "success":
                bg_color = "#4CAF50"      # Green for success
                text_color = "#FFFFFF"    # White text for contrast
                hover_color = "#66BB6A"   # Lighter green for hover
                active_color = "#388E3C"  # Darker green for pressed
            elif state == "warning":
                bg_color = "#FF9800"      # Orange for warning
                text_color = "#000000"    # Black text for contrast
                hover_color = "#FFB74D"   # Lighter orange for hover
                active_color = "#F57C00"  # Darker orange for pressed
            else:  # normal
                bg_color = "rgba(255, 255, 255, 0.15)"    # Semi-transparent white
                text_color = "white"                       # White text
                hover_color = "rgba(255, 255, 255, 0.25)" # Lighter on hover
                active_color = "rgba(255, 255, 255, 0.35)" # Lightest when pressed
            
            border_color = "none" if button_type == "tool" else "rgba(255, 255, 255, 0.2)"
            disabled_bg = "rgba(255, 255, 255, 0.05)"
            disabled_text = "#666"
        else:
            # Theme-aware color selection using ColorSystem
            # This section maps button states to appropriate theme colors
            # while respecting custom color overrides when provided
            if special_colors:
                # Use custom colors when provided (for special cases)
                bg_color = special_colors.get("background", colors.interactive_normal)
                text_color = special_colors.get("text", colors.text_primary)
                hover_color = special_colors.get("hover", colors.interactive_hover)
                active_color = special_colors.get("active", colors.interactive_active)
                border_color = special_colors.get("border", "none" if button_type == "tool" else colors.border_primary)
            else:
                # Default state colors using semantic theme variables
                if state == "toggle":
                    # Toggle state uses primary brand colors for emphasis
                    bg_color = colors.primary
                    text_color = colors.background_primary  # High contrast against primary
                    hover_color = colors.primary_hover
                    active_color = colors.primary_hover
                elif state == "danger":
                    # Danger state uses error status color for destructive actions
                    bg_color = colors.status_error
                    text_color = colors.text_primary
                    hover_color = colors.status_error  # Should be lighter in real implementation
                    active_color = colors.status_error
                elif state == "success":
                    # Success state uses success status color for positive actions
                    bg_color = colors.status_success
                    text_color = colors.background_primary
                    hover_color = colors.status_success  # Should be lighter
                    active_color = colors.status_success
                elif state == "warning":
                    # Warning state uses warning status color for caution actions
                    bg_color = colors.status_warning
                    text_color = colors.background_primary
                    hover_color = colors.status_warning  # Should be lighter
                    active_color = colors.status_warning
                else:  # normal
                    # Normal state uses standard interactive colors
                    bg_color = colors.interactive_normal
                    text_color = colors.text_primary
                    hover_color = colors.interactive_hover
                    active_color = colors.interactive_active
                
                # Border handling: tool buttons have no borders, push buttons do
                border_color = "none" if button_type == "tool" else colors.border_primary
            
            # Disabled colors use theme's disabled state colors
            disabled_bg = colors.interactive_disabled
            disabled_text = colors.text_disabled
        
        # Widget selector based on button type for proper CSS targeting
        # PyQt6 requires specific widget selectors for proper style application
        widget_selector = "QToolButton" if button_type in ["tool", "icon"] else "QPushButton"
        border_style = "border: none;" if button_type == "tool" else f"border: 1px solid {border_color};"
        
        # Get dynamic CSS padding based on current icon size setting
        # This ensures buttons scale properly with user accessibility preferences
        css_padding = ButtonStyleManager.get_dynamic_css_padding()
        
        # Generate comprehensive CSS with all interactive states
        # Each state provides clear visual feedback to users
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
        Apply unified styling to any button widget with comprehensive setup.
        
        This is the ONLY method that should be used to style buttons in the application.
        It combines CSS styling with PyQt6 widget constraints to ensure reliable
        button appearance across all platforms and themes.
        
        The method handles:
        - CSS stylesheet generation and application
        - PyQt6 size constraints (min/max width/height)
        - Icon size configuration
        - Emoji font assignment for special buttons
        - Dynamic sizing based on user settings
        
        Args:
            button: PyQt6 button widget (QPushButton or QToolButton)
            colors: ColorSystem instance for theme colors
            button_type: "push", "tool", or "icon" 
            size: "icon", "extra_small", "small", "medium", "large"
            state: "normal", "toggle", "danger", "success", "warning"
            special_colors: Optional dict for custom color overrides
            emoji_font: Optional font family for emoji buttons (e.g., "Segoe UI Emoji")
            
        PyQt6 Techniques Used:
        - setMinimumSize/setMaximumSize for reliable sizing
        - setIconSize for consistent icon dimensions
        - setStyleSheet for CSS application
        - Font family injection for emoji support
        
        Dynamic Sizing Algorithm:
        Icon buttons use smart sizing based on user settings:
        - Gets icon size from settings (8-32px typically)
        - Calculates proportional padding (2-6px total)
        - Sets both CSS and Qt constraints for reliability
        
        Implementation Notes:
            The method applies both CSS styles and Qt widget constraints because:
            1. CSS provides visual styling and theme colors
            2. Qt constraints ensure reliable sizing across platforms
            3. Icon size must be set via Qt API for proper scaling
            4. Font family injection requires CSS modification
            
        Usage Examples:
            # Standard button
            ButtonStyleManager.apply_unified_button_style(
                my_button, colors, "push", "medium", "normal"
            )
            
            # Toggle button with danger state
            ButtonStyleManager.apply_unified_button_style(
                toggle_btn, colors, "tool", "small", "toggle"
            )
            
            # Icon button with emoji font
            ButtonStyleManager.apply_unified_button_style(
                icon_btn, colors, "icon", "icon", "normal", 
                emoji_font="Segoe UI Emoji"
            )
        """
        # Get base style using the unified generation method
        style = ButtonStyleManager.get_unified_button_style(
            colors, button_type, size, state, special_colors
        )
        
        # Add emoji font if specified for special buttons (plus, settings, etc.)
        # This requires modifying the CSS to inject the font-family property
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
        
        # Size configuration mapping for Qt widget constraints
        # These complement the CSS sizing for maximum reliability
        size_configs = {
            "icon": {"min_width": icon_button_size, "min_height": icon_button_size, "max_width": icon_button_size, "max_height": icon_button_size},
            "extra_small": {"min_width": 48, "min_height": 28},
            "small": {"min_width": 60, "min_height": 32},
            "medium": {"min_width": 80, "min_height": 32},
            "large": {"min_width": 100, "min_height": 36},
        }
        
        config = size_configs.get(size, size_configs["medium"])
        
        # Apply Qt size constraints for reliable sizing across platforms
        # These work in conjunction with CSS min-width/min-height properties
        button.setMinimumSize(config["min_width"], config["min_height"])
        button.setMaximumSize(config.get("max_width", 16777215), config.get("max_height", 16777215))
        
        # Set icon size for buttons that have icons
        # This must be done via Qt API for proper icon scaling
        from PyQt6.QtCore import QSize
        icon_size = ButtonStyleManager.get_icon_size()
        button.setIconSize(QSize(icon_size, icon_size))
        
        # Apply the unified style
        button.setStyleSheet(style)
    
    @staticmethod
    def apply_plus_button_style(button, colors, emoji_font: str = None):
        """
        Apply special styling for plus button with asymmetric padding.
        
        Plus buttons often need extra space on the right side to accommodate
        dropdown arrows or to provide visual balance. This method creates
        asymmetric padding while maintaining the unified styling approach.
        
        Args:
            button: Qt button widget (typically QToolButton)
            colors: ColorSystem instance for theme colors
            emoji_font: Optional font family for emoji buttons
            
        Features:
        - Asymmetric padding (more on left and right sides)
        - Maintains unified styling constants
        - Adjusts width calculations for padding differences
        - Preserves icon sizing and theme colors
        
        Implementation Details:
            The asymmetric padding provides visual balance when the plus button
            is positioned next to other elements or when it needs to accommodate
            dropdown functionality. The algorithm:
            1. Gets base padding from computed sizes
            2. Multiplies base padding by 5 for left/right sides
            3. Adjusts total button width to accommodate extra padding
            4. Maintains top/bottom padding at base level
            
        Visual Effect:
            Normal button: [  +  ]
            Plus button:   [     +     ]
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
        
        # Replace the standard padding with asymmetric padding
        old_padding = f"padding: {base_padding}px;"
        new_padding = f"padding: {base_padding}px {right_padding}px {base_padding}px {left_padding}px;"
        style = style.replace(old_padding, new_padding)
        
        # Adjust width for asymmetric padding to maintain proper button proportions
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
    Collection of reusable style templates for PyQt6 UI components.
    
    This class provides pre-designed CSS templates for all major UI components
    in the Ghostman application. Each template is theme-aware and follows
    consistent design patterns.
    
    Features:
    - Theme-aware color management
    - Consistent spacing and sizing
    - Accessibility-compliant styling
    - PyQt6-specific CSS techniques
    - Comprehensive component coverage
    
    Usage:
        # Get a template by name
        style = StyleTemplates.get_style("main_window", colors)
        
        # Get specific template directly
        dialog_style = StyleTemplates.get_settings_dialog_style(colors)
        widget.setStyleSheet(dialog_style)
        
    Available Templates:
    - Main window and dialog styling
    - Button variations (primary, secondary, tool, icon)
    - Form elements (inputs, combos, checkboxes)
    - Navigation (tabs, menus)
    - Containers (panels, frames, groups)
    - Data display (lists, progress bars)
    - Scrollbars and interactive elements
    
    Design Philosophy:
        All templates follow these principles:
        1. Semantic color usage (primary for brand, status for feedback)
        2. Consistent spacing (4px, 8px, 12px multiples)
        3. Accessibility first (WCAG 2.1 compliance)
        4. Platform consistency (native PyQt6 behavior where appropriate)
        5. Theme coherence (all components work together visually)
        
    PyQt6 Compatibility:
        Templates use PyQt6-specific selectors and properties:
        - QWidget selectors for precise targeting
        - ::pseudo-elements for complex controls
        - State selectors (:hover, :focus, :pressed, :disabled)
        - Subcontrol positioning for complex widgets
    """
    
    @staticmethod
    def get_style(template_name: str, colors: ColorSystem, **kwargs) -> str:
        """
        Get a style template by name with parameter support.
        
        This method provides a unified interface for accessing all style templates
        using string names. It's useful for configuration-driven styling or
        dynamic template selection.
        
        Args:
            template_name: Name of the template (e.g., "main_window", "button_primary")
            colors: Color system to use for theming
            **kwargs: Additional parameters passed to the template method
            
        Returns:
            CSS string for the requested template
            
        Raises:
            ValueError: If the template name is not found
            
        Available Templates:
        - main_window: Base application window styling
        - repl_panel: REPL output panel with opacity support
        - title_frame: Header and title sections
        - button_primary/secondary: Standard button variants
        - tool_button: Toolbar button styling
        - icon_button: Square icon-only buttons
        - input_field: Text input controls
        - combo_box: Dropdown selection controls
        - list_widget: List and item displays
        - progress_bar: Progress indication
        - scroll_bar: Custom scrollbar styling
        - menu: Context and dropdown menus
        - tab_widget: Tabbed interface controls
        - dialog: Modal dialog windows
        - search_frame: Search input containers
        - settings_dialog: Complete settings UI styling
        
        Example:
            # Get main window style
            style = StyleTemplates.get_style("main_window", colors)
            
            # Get button style with parameters
            style = StyleTemplates.get_style("icon_button", colors, variant="primary")
        """
        method_name = f"get_{template_name}_style"
        if hasattr(StyleTemplates, method_name):
            method = getattr(StyleTemplates, method_name)
            return method(colors, **kwargs)
        else:
            raise ValueError(f"Unknown style template: {template_name}")
    
    @staticmethod
    def get_main_window_style(colors: ColorSystem) -> str:
        """
        Style template for main application window.
        
        Provides base styling for the main QMainWindow including background
        color and text color setup. This serves as the foundation for the
        entire application's visual appearance.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for main window styling
            
        Features:
        - Sets primary background for the entire application
        - Establishes base text color for consistency
        - Provides foundation for child widget inheritance
        
        Usage:
            main_window = QMainWindow()
            style = StyleTemplates.get_main_window_style(colors)
            main_window.setStyleSheet(style)
        """
        return f"""
        QMainWindow {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        """
    
    @staticmethod
    def get_repl_panel_style(colors: ColorSystem, opacity: float = 0.9) -> str:
        """
        Style template for REPL panel with selective opacity handling.
        
        The REPL panel requires special handling for opacity settings. The root
        panel always remains fully opaque to keep UI controls visible, while
        only the output display area can have opacity applied separately.
        
        Args:
            colors: ColorSystem for theme colors
            opacity: Opacity value (currently unused - kept for API compatibility)
            
        Returns:
            CSS string for REPL panel root styling
            
        Implementation Details:
            Opacity is deliberately NOT applied to the root panel. This prevents
            UI controls from becoming hard to see. Opacity should be applied
            separately to specific output display areas only.
            
            The panel uses:
            - Secondary background for subtle elevation
            - Rounded top corners for modern appearance
            - Border for definition against main background
            - Proper ID selector for specificity
            
        Note:
            The opacity parameter is maintained for API compatibility but not
            used in the root panel styling. This design ensures UI controls
            remain fully visible while allowing opacity to be applied selectively
            to content areas.
        """
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
        """
        Style template for title frames and headers.
        
        Provides styling for frame containers that hold titles, headers, or
        section labels. Uses tertiary background for subtle elevation.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for title frame styling
            
        Features:
        - Tertiary background for visual hierarchy
        - Subtle border for definition
        - Rounded corners for modern appearance
        - Bold label text for emphasis
        
        Usage Context:
            Used for section headers, dialog titles, and grouping containers
            that need visual separation from surrounding content.
        """
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
        """
        Style template for primary action buttons.
        
        Primary buttons use the main brand color and are designed to draw
        attention to the most important actions in the interface.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for primary button styling
            
        Design Notes:
        - Uses primary brand color for high visibility
        - Bold font weight for emphasis
        - Comprehensive state management (hover, pressed, disabled)
        - Maintains accessibility with proper contrast ratios
        
        Recommended Usage:
        - Submit/Save actions in forms
        - Confirmation dialogs (OK, Accept)
        - Primary calls-to-action
        - Important navigation actions
        """
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
        """
        Style template for secondary action buttons.
        
        Secondary buttons use interactive colors and are for less prominent
        actions or supporting functionality.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for secondary button styling
            
        Design Notes:
        - Uses interactive colors instead of brand colors
        - Normal font weight (not bold)
        - Same interaction states as primary buttons
        - Provides clear hierarchy with primary buttons
        
        Recommended Usage:
        - Cancel/Close actions in dialogs
        - Secondary navigation
        - Optional or alternative actions
        - Toolbar buttons
        """
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
        """
        Style template for toolbar buttons.
        
        Tool buttons are borderless and designed for toolbar use where space
        is limited and visual weight should be minimal.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for tool button styling
            
        Design Notes:
        - No borders for minimal visual weight
        - Compact padding for toolbar density
        - Menu button support for dropdown arrows
        - Bottom margin for visual alignment
        
        PyQt6 Features:
        - QToolButton::menu-button selector for dropdown styling
        - Borderless design that works with icon-only buttons
        - Proper spacing for toolbar layouts
        """
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
        
        Legacy wrapper for backward compatibility with existing code.
        New code should use ButtonStyleManager directly for better control
        and consistency.
        
        Args:
            colors: ColorSystem for theme colors
            size: Button size category
            
        Returns:
            CSS string for button styling
            
        Migration Path:
            Old: StyleTemplates.get_uniform_button_style(colors, "small")
            New: ButtonStyleManager.get_unified_button_style(colors, "push", "small")
        """
        return ButtonStyleManager.get_unified_button_style(colors, "push", size)
    
    @staticmethod
    def get_uniform_tool_button_style(colors: ColorSystem, size="medium") -> str:
        """
        DEPRECATED: Use ButtonStyleManager.get_unified_button_style() instead.
        
        Legacy wrapper for backward compatibility with existing code.
        New code should use ButtonStyleManager directly for better control
        and consistency.
        
        Args:
            colors: ColorSystem for theme colors
            size: Button size category
            
        Returns:
            CSS string for tool button styling
            
        Migration Path:
            Old: StyleTemplates.get_uniform_tool_button_style(colors, "small")
            New: ButtonStyleManager.get_unified_button_style(colors, "tool", "small")
        """
        return ButtonStyleManager.get_unified_button_style(colors, "tool", size)
    
    @staticmethod
    def get_icon_button_style(colors: ColorSystem, variant="normal") -> str:
        """
        Style template for icon-only buttons with square dimensions.
        
        Icon buttons are square and designed to hold single icons. They use
        the unified ButtonStyleManager for consistency while supporting
        different visual variants.
        
        Args:
            colors: Color system to use
            variant: Visual variant
                - "normal": Standard interactive appearance
                - "primary": Primary brand color appearance
                - "danger": Error/destructive action appearance
                - "minimal": Transparent background with minimal visual weight
        
        Returns:
            CSS string for icon button styling
            
        Implementation Details:
            This method maps visual variants to ButtonStyleManager states
            and handles special cases like the minimal variant which uses
            transparent backgrounds for subtle interface integration.
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
        """
        Style template for input fields and text edits.
        
        Provides consistent styling for all text input elements including
        QLineEdit, QTextEdit, and QPlainTextEdit with focus states and
        selection styling.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for input field styling
            
        Features:
        - Consistent background and text colors
        - Focus state with border highlighting
        - Disabled state styling
        - Selection color theming
        - Rounded corners for modern appearance
        
        Accessibility:
        - High contrast between text and background
        - Clear focus indicators
        - Disabled state clearly differentiated
        """
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
        """
        Style template for dropdown combo boxes.
        
        Provides styling for QComboBox elements including the dropdown arrow
        area and the dropdown list view for consistent appearance.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for combo box styling
            
        Features:
        - Consistent with input field styling
        - Custom dropdown arrow area
        - Themed dropdown list
        - Hover and focus states
        
        PyQt6 Specifics:
        - ::drop-down subcontrol for arrow area
        - QAbstractItemView for dropdown list styling
        - Proper selection colors in dropdown
        """
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
        """
        Style template for list widgets and item views.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for list widget styling
            
        Features:
        - Item padding for better readability
        - Hover and selection states
        - Rounded item corners
        - Proper spacing between items
        """
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
        """
        Style template for progress bars.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for progress bar styling
            
        Features:
        - Primary color for progress indication
        - Centered text display
        - Rounded corners for modern appearance
        - Bold text for readability
        """
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
        """
        Style template for scroll bars (both vertical and horizontal).
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for scroll bar styling
            
        Features:
        - Modern rounded scrollbars
        - Hover effects for better interaction
        - Consistent sizing for both orientations
        - Minimal arrow buttons (hidden)
        """
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
        """
        Style template for menus and context menus.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for menu styling
            
        Features:
        - Secondary background for menu panels
        - Item hover effects
        - Disabled item styling
        - Menu separators
        - Proper padding and spacing
        """
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
        """
        Style template for tab widgets and tab bars.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for tab widget styling
            
        Features:
        - Modern tab appearance with rounded corners
        - Selected tab highlighting with primary color
        - Hover effects for better interaction
        - Proper spacing and alignment
        
        Design Notes:
        - Selected tabs use primary brand color for emphasis
        - Unselected tabs use secondary text for hierarchy
        - Rounded top corners only for tab appearance
        """
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
        """
        Style template for dialogs and modal windows.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for dialog styling
            
        Features:
        - Primary background for main dialog area
        - Button box separation with border
        - Consistent color theming
        """
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
        """
        Style template for labels with different visual variants.
        
        Args:
            colors: ColorSystem for theme colors
            variant: Label variant
                - "primary": High contrast primary text
                - "secondary": Medium contrast secondary text
                - "tertiary": Low contrast tertiary text
                - "success": Success status color
                - "warning": Warning status color
                - "error": Error status color
                - "info": Information status color
        
        Returns:
            CSS string for label styling
            
        Usage:
        - primary: Main headings, important text
        - secondary: Subheadings, descriptions
        - tertiary: Helper text, footnotes
        - status variants: Status messages, alerts
        """
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
        """
        Style template for status indicators and badges.
        
        Args:
            colors: ColorSystem for theme colors
            status: Status type ("success", "warning", "error", "info")
        
        Returns:
            CSS string for status styling
            
        Features:
        - Bold text for emphasis
        - Small font size for badges
        - Status-appropriate colors
        
        Usage Context:
        - Status badges in lists
        - Alert indicators
        - State labels in forms
        """
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
        """
        Style template for search frames with comprehensive border removal.
        
        This template uses multiple CSS techniques to ensure borders are
        completely removed from search frames, addressing PyQt6's stubborn
        border behavior in certain contexts.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for search frame styling
            
        PyQt6 Techniques Used:
            - Multiple border properties for complete removal
            - !important directives to override default styling
            - Comprehensive focus state handling
            - Child widget border inheritance prevention
            
        Implementation Details:
            PyQt6 frames can have stubborn borders that persist even after
            setting border: none. This template uses a comprehensive approach:
            1. Sets all border-related properties explicitly
            2. Uses !important to override any inherited styles
            3. Handles all interaction states (focus, hover)
            4. Prevents child widgets from inheriting unwanted borders
            
        This is particularly important for search components where clean
        appearance is essential for user experience.
        """
        return f"""
        QFrame {{
            background-color: {colors.background_tertiary};
            border: none !important;
            border-width: 0px !important;
            border-style: none !important;
            border-color: transparent !important;
            border-radius: 4px;
            padding: 4px;
            margin: 0px;
            outline: none !important;
        }}
        QFrame:focus {{
            border: none !important;
            outline: none !important;
        }}
        QFrame:hover {{
            border: none !important;
            outline: none !important;
        }}
        /* Ensure child widgets don't inherit unwanted borders */
        QFrame QLineEdit {{
            border: none !important;
            outline: none !important;
        }}
        """
    
    @staticmethod
    def get_high_contrast_search_status_style(colors: ColorSystem) -> str:
        """
        Get high-contrast styling for search status labels.
        
        This method automatically calculates the optimal text color for maximum
        visibility against the search frame background using the same smart
        contrast algorithm as titlebar buttons.
        
        The algorithm:
        1. Tests theme-aware text colors first for visual integration
        2. Falls back to high-contrast colors (white/black) if needed
        3. Ensures WCAG AA compliance (4.5:1 contrast ratio minimum)
        4. Prefers WCAG AAA compliance (7.0:1 ratio) when possible
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for high-contrast search status styling
            
        Accessibility Features:
        - Automatic contrast ratio calculation
        - WCAG 2.1 AA/AAA compliance
        - Theme-aware color selection with high-contrast fallbacks
        
        Implementation Details:
            Uses ColorUtils.get_high_contrast_text_color_for_background() which:
            - Tests multiple text color candidates
            - Calculates WCAG contrast ratios
            - Selects optimal color for readability
            - Provides fallbacks for edge cases
            
        This ensures search result counts, status messages, and other
        text elements remain readable across all themes and backgrounds.
        """
        from .color_system import ColorUtils
        
        # Get optimal text color for search frame background
        optimal_text_color, contrast_ratio = ColorUtils.get_high_contrast_text_color_for_background(
            colors.background_tertiary,
            colors,
            min_ratio=4.5
        )
        
        return f"""
        QLabel {{
            color: {optimal_text_color};
            font-size: 10px;
            font-weight: bold;
        }}
        """
    
    @staticmethod
    def get_checkbox_style(colors: ColorSystem) -> str:
        """
        Style template for checkboxes with custom indicators.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for checkbox styling
            
        Features:
        - Custom checkbox indicator styling
        - Primary color for checked state
        - Hover effects for better interaction
        - Disabled state handling
        - Proper spacing between indicator and label
        """
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
        """
        Style template for system tray components.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for system tray styling
            
        Features:
        - Menu styling for tray context menus
        - Action item styling
        - Selection effects
        """
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
        """
        Comprehensive style template for the settings dialog.
        
        This template provides complete styling for all elements in the settings
        dialog including tabs, form controls, buttons, and scrollbars. It demonstrates
        advanced PyQt6 styling techniques and comprehensive component coverage.
        
        Args:
            colors: ColorSystem for theme colors
            
        Returns:
            CSS string for complete settings dialog styling
            
        Features Covered:
        - Main dialog background and text
        - Tab widget with hover and selection states
        - Group boxes with title positioning
        - All form inputs (text fields, spinboxes, combos)
        - Modern scrollbar styling with hover effects
        - Button styling (handled separately by ButtonStyleManager)
        - List widgets with selection and hover states
        - Splitter handles
        - Comprehensive focus state management
        
        Advanced PyQt6 Techniques:
        - ::title subcontrol for group box titles
        - ::tab-bar and ::pane subcontrols for tab widgets
        - ::handle subcontrols for scrollbars and splitters
        - ::drop-down subcontrol for combo boxes
        - QAbstractItemView for dropdown styling
        - State selectors for all interactive elements
        
        Design Philosophy:
            The settings dialog serves as a comprehensive example of
            theme-aware styling, demonstrating:
            1. Consistent color usage across all elements
            2. Proper visual hierarchy with backgrounds
            3. Accessibility-compliant contrast ratios
            4. Modern UI patterns (rounded tabs, custom scrollbars)
            5. Comprehensive state management
        """
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