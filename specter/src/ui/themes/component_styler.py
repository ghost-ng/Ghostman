"""
Component-Based Styling System for Specter.

This module provides specialized stylers for different types of UI components,
offering semantic, type-safe interfaces that replace inline CSS generation.

Key Features:
- Type-safe component styling with semantic APIs
- Automatic style lifecycle management
- Built-in accessibility validation
- Performance-optimized rendering
- Integration with the centralized style registry
"""

import logging
from typing import Dict, Any, Optional, List, Protocol, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QTextEdit, QLabel, QFrame, QComboBox
from PyQt6.QtCore import QObject, pyqtSignal

from .color_system import ColorSystem
from .style_registry import get_style_registry, ComponentCategory
from .repl_style_registry import REPLComponent, StyleConfig

logger = logging.getLogger("specter.component_styler")

T = TypeVar('T', bound=QWidget)


class StyleableComponent(Protocol):
    """Protocol for components that can be styled."""
    def setStyleSheet(self, stylesheet: str) -> None: ...


class ComponentState(Enum):
    """Common component states for styling."""
    NORMAL = "normal"
    HOVER = "hover"
    FOCUSED = "focused" 
    DISABLED = "disabled"
    ACTIVE = "active"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"


@dataclass
class ComponentTheme:
    """Theme configuration for a component."""
    primary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    border_color: Optional[str] = None
    accent_color: Optional[str] = None
    state_colors: Optional[Dict[ComponentState, str]] = None


class BaseComponentStyler(ABC, Generic[T]):
    """
    Abstract base class for component stylers.
    
    Provides the foundation for type-safe, semantic component styling
    with automatic lifecycle management and performance optimization.
    """
    
    def __init__(self, widget: T, component_id: str):
        self.widget = widget
        self.component_id = component_id
        self.registry = get_style_registry()
        self.current_state = ComponentState.NORMAL
        self.custom_theme: Optional[ComponentTheme] = None
        
        # Register with style registry
        self.registry.register_component(
            widget, component_id, self.get_component_category()
        )
    
    @abstractmethod
    def get_component_category(self) -> ComponentCategory:
        """Get the component category for registry organization."""
        pass
    
    @abstractmethod
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply styling to the component."""
        pass
    
    def set_state(self, state: ComponentState) -> bool:
        """
        Set component state and update styling.
        
        Args:
            state: New component state
            
        Returns:
            True if state was set successfully
        """
        if state != self.current_state:
            self.current_state = state
            return self.apply_style()
        return True
    
    def set_custom_theme(self, theme: ComponentTheme) -> bool:
        """
        Apply custom theming to the component.
        
        Args:
            theme: Custom theme configuration
            
        Returns:
            True if theme was applied successfully
        """
        self.custom_theme = theme
        return self.apply_style()
    
    def cleanup(self):
        """Clean up resources and unregister from style registry."""
        self.registry.unregister_component(self.widget)


class ButtonStyler(BaseComponentStyler[QPushButton]):
    """
    Specialized styler for button components.
    
    Provides semantic APIs for button styling with support for different
    button types, sizes, and states.
    """
    
    def __init__(self, button: QPushButton, component_id: str):
        super().__init__(button, component_id)
        self.button_type = "push"  # push, tool, icon
        self.size = "medium"       # icon, extra_small, small, medium, large
        self.variant = "primary"   # primary, secondary, danger, success
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.INTERACTIVE
    
    def set_button_type(self, button_type: str) -> 'ButtonStyler':
        """Set button type (push, tool, icon) - fluent interface."""
        self.button_type = button_type
        return self
    
    def set_size(self, size: str) -> 'ButtonStyler':
        """Set button size - fluent interface."""
        self.size = size
        return self
    
    def set_variant(self, variant: str) -> 'ButtonStyler':
        """Set button variant - fluent interface."""
        self.variant = variant
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply button styling using ButtonStyleManager."""
        # Map variant to state
        state_map = {
            "primary": "normal",
            "secondary": "normal", 
            "danger": "danger",
            "success": "success",
            "warning": "warning"
        }
        
        # Override with current state if applicable
        if self.current_state in [ComponentState.ACTIVE, ComponentState.FOCUSED]:
            state = "toggle"
        elif self.current_state == ComponentState.ERROR:
            state = "danger"
        elif self.current_state == ComponentState.SUCCESS:
            state = "success"
        elif self.current_state == ComponentState.WARNING:
            state = "warning"
        else:
            state = state_map.get(self.variant, "normal")
        
        return self.registry.apply_button_style(
            self.widget, self.button_type, self.size, state, colors
        )
    
    def make_primary(self) -> 'ButtonStyler':
        """Make this a primary action button - fluent interface."""
        return self.set_variant("primary").set_size("medium")
    
    def make_secondary(self) -> 'ButtonStyler':
        """Make this a secondary action button - fluent interface."""
        return self.set_variant("secondary").set_size("small")
    
    def make_danger(self) -> 'ButtonStyler':
        """Make this a danger action button - fluent interface."""
        return self.set_variant("danger")
    
    def make_icon_button(self) -> 'ButtonStyler':
        """Make this an icon-only button - fluent interface."""
        return self.set_button_type("icon").set_size("icon")
    
    def make_toolbar_button(self) -> 'ButtonStyler':
        """Make this a toolbar button - fluent interface."""
        return self.set_button_type("tool").set_size("small")


class InputFieldStyler(BaseComponentStyler[QLineEdit]):
    """
    Specialized styler for input field components.
    
    Provides semantic APIs for input field styling with validation states
    and accessibility features.
    """
    
    def __init__(self, input_field: QLineEdit, component_id: str):
        super().__init__(input_field, component_id)
        self.field_type = "text"  # text, password, search, number
        self.validation_state = None  # None, error, success, warning
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.FORM
    
    def set_field_type(self, field_type: str) -> 'InputFieldStyler':
        """Set field type - fluent interface."""
        self.field_type = field_type
        return self
    
    def set_validation_state(self, state: Optional[ComponentState]) -> 'InputFieldStyler':
        """Set validation state - fluent interface."""
        self.validation_state = state
        if state:
            self.set_state(state)
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply input field styling."""
        # Use specialized input field template
        template_name = "input_field"
        
        # Apply special styling for validation states
        if self.validation_state == ComponentState.ERROR:
            template_name = "input_field_error"
        elif self.validation_state == ComponentState.SUCCESS:
            template_name = "input_field_success"
        elif self.validation_state == ComponentState.WARNING:
            template_name = "input_field_warning"
        
        return self.registry.apply_style(self.widget, template_name, colors)
    
    def make_search_field(self) -> 'InputFieldStyler':
        """Style as search field - fluent interface."""
        return self.set_field_type("search")
    
    def show_error(self, message: Optional[str] = None) -> 'InputFieldStyler':
        """Show error state - fluent interface."""
        return self.set_validation_state(ComponentState.ERROR)
    
    def show_success(self) -> 'InputFieldStyler':
        """Show success state - fluent interface."""
        return self.set_validation_state(ComponentState.SUCCESS)
    
    def clear_validation(self) -> 'InputFieldStyler':
        """Clear validation state - fluent interface."""
        return self.set_validation_state(None)


class TextEditStyler(BaseComponentStyler[QTextEdit]):
    """
    Specialized styler for text edit components.
    
    Handles both plain text and rich text editors with special considerations
    for preserving font families (especially monospace).
    """
    
    def __init__(self, text_edit: QTextEdit, component_id: str):
        super().__init__(text_edit, component_id)
        self.preserve_font = True  # Preserve existing font family
        self.editor_type = "plain"  # plain, rich, code
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.FORM
    
    def set_editor_type(self, editor_type: str) -> 'TextEditStyler':
        """Set editor type - fluent interface."""
        self.editor_type = editor_type
        return self
    
    def preserve_font_family(self, preserve: bool = True) -> 'TextEditStyler':
        """Set whether to preserve existing font family - fluent interface."""
        self.preserve_font = preserve
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply text edit styling."""
        template_name = "text_edit"
        
        if self.editor_type == "code":
            template_name = "code_editor"
        elif self.editor_type == "rich":
            template_name = "rich_text_editor"
        
        return self.registry.apply_style(self.widget, template_name, colors)
    
    def make_code_editor(self) -> 'TextEditStyler':
        """Style as code editor - fluent interface."""
        return self.set_editor_type("code").preserve_font_family(True)
    
    def make_rich_editor(self) -> 'TextEditStyler':
        """Style as rich text editor - fluent interface."""
        return self.set_editor_type("rich").preserve_font_family(False)


class REPLComponentStyler(BaseComponentStyler[QWidget]):
    """
    Specialized styler for REPL components.
    
    Uses the high-performance REPL style registry for optimal theme switching
    performance in the most commonly used components.
    """
    
    def __init__(self, widget: QWidget, component_id: str, repl_component: REPLComponent):
        super().__init__(widget, component_id)
        self.repl_component = repl_component
        self.style_config = StyleConfig()
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.REPL
    
    def set_opacity(self, opacity: float) -> 'REPLComponentStyler':
        """Set component opacity - fluent interface."""
        self.style_config.opacity = opacity
        return self
    
    def set_border_radius(self, radius: int) -> 'REPLComponentStyler':
        """Set border radius - fluent interface."""
        self.style_config.border_radius = radius
        return self
    
    def set_padding(self, padding: int) -> 'REPLComponentStyler':
        """Set padding - fluent interface."""
        self.style_config.padding = padding
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply REPL component styling using optimized registry."""
        return self.registry.apply_repl_style(
            self.widget, self.repl_component, self.style_config, colors
        )
    
    def make_output_panel(self, opacity: float = 1.0) -> 'REPLComponentStyler':
        """Configure as output panel - fluent interface."""
        self.repl_component = REPLComponent.OUTPUT_PANEL
        return self.set_opacity(opacity)
    
    def make_input_field(self) -> 'REPLComponentStyler':
        """Configure as input field - fluent interface."""
        self.repl_component = REPLComponent.INPUT_FIELD
        return self
    
    def make_toolbar(self) -> 'REPLComponentStyler':
        """Configure as toolbar - fluent interface."""
        self.repl_component = REPLComponent.TOOLBAR
        return self


class LabelStyler(BaseComponentStyler[QLabel]):
    """
    Specialized styler for label components.
    
    Supports different label variants (primary, secondary, status) and
    automatic contrast optimization.
    """
    
    def __init__(self, label: QLabel, component_id: str):
        super().__init__(label, component_id)
        self.variant = "primary"  # primary, secondary, tertiary, status
        self.status_type = None   # success, warning, error, info
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.DISPLAY
    
    def set_variant(self, variant: str) -> 'LabelStyler':
        """Set label variant - fluent interface."""
        self.variant = variant
        return self
    
    def set_status_type(self, status_type: str) -> 'LabelStyler':
        """Set status type for status labels - fluent interface."""
        self.status_type = status_type
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply label styling."""
        if self.variant == "status" and self.status_type:
            template_name = f"label_status_{self.status_type}"
        else:
            template_name = f"label_{self.variant}"
        
        return self.registry.apply_style(self.widget, template_name, colors)
    
    def make_heading(self) -> 'LabelStyler':
        """Style as heading text - fluent interface."""
        return self.set_variant("primary")
    
    def make_subtitle(self) -> 'LabelStyler':
        """Style as subtitle text - fluent interface."""
        return self.set_variant("secondary")
    
    def make_caption(self) -> 'LabelStyler':
        """Style as caption text - fluent interface."""
        return self.set_variant("tertiary")
    
    def show_success(self) -> 'LabelStyler':
        """Show success status - fluent interface."""
        return self.set_variant("status").set_status_type("success")
    
    def show_error(self) -> 'LabelStyler':
        """Show error status - fluent interface."""
        return self.set_variant("status").set_status_type("error")
    
    def show_warning(self) -> 'LabelStyler':
        """Show warning status - fluent interface."""
        return self.set_variant("status").set_status_type("warning")


class ComponentStylerFactory:
    """
    Factory for creating appropriate component stylers.
    
    Automatically detects widget type and returns the optimal styler.
    """
    
    @staticmethod
    def create_styler(widget: QWidget, component_id: str, **kwargs) -> BaseComponentStyler:
        """
        Create appropriate styler for widget type.
        
        Args:
            widget: Widget to create styler for
            component_id: Unique component identifier
            **kwargs: Additional configuration for specific stylers
            
        Returns:
            Appropriate styler instance
        """
        if isinstance(widget, QPushButton):
            return ButtonStyler(widget, component_id)
        
        elif isinstance(widget, QLineEdit):
            return InputFieldStyler(widget, component_id)
        
        elif isinstance(widget, QTextEdit):
            return TextEditStyler(widget, component_id)
        
        elif isinstance(widget, QLabel):
            return LabelStyler(widget, component_id)
        
        elif 'repl_component' in kwargs:
            return REPLComponentStyler(widget, component_id, kwargs['repl_component'])
        
        else:
            # Generic styler for other widget types
            return GenericComponentStyler(widget, component_id)


class GenericComponentStyler(BaseComponentStyler[QWidget]):
    """Generic styler for widgets without specialized stylers."""
    
    def __init__(self, widget: QWidget, component_id: str):
        super().__init__(widget, component_id)
        self.template_name = "main_window"
    
    def get_component_category(self) -> ComponentCategory:
        return ComponentCategory.DISPLAY
    
    def set_template(self, template_name: str) -> 'GenericComponentStyler':
        """Set style template - fluent interface."""
        self.template_name = template_name
        return self
    
    def apply_style(self, colors: Optional[ColorSystem] = None) -> bool:
        """Apply generic styling."""
        return self.registry.apply_style(self.widget, self.template_name, colors)


# Convenience functions for quick styling

def style_button(button: QPushButton, component_id: str) -> ButtonStyler:
    """Create and return a button styler."""
    return ButtonStyler(button, component_id)

def style_input(input_field: QLineEdit, component_id: str) -> InputFieldStyler:
    """Create and return an input field styler."""
    return InputFieldStyler(input_field, component_id)

def style_repl_component(widget: QWidget, component_id: str, 
                        repl_component: REPLComponent) -> REPLComponentStyler:
    """Create and return a REPL component styler."""
    return REPLComponentStyler(widget, component_id, repl_component)

def style_label(label: QLabel, component_id: str) -> LabelStyler:
    """Create and return a label styler."""
    return LabelStyler(label, component_id)