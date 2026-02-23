"""
Theme Applicator for Specter Application.

This module provides centralized theme application functionality that ensures
all widgets and windows in the application receive theme updates properly.
"""

import logging
from typing import List, Optional, Set
from weakref import WeakSet

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject

from .color_system import ColorSystem
from .style_templates import StyleTemplates

logger = logging.getLogger("specter.theme_applicator")


class ThemeApplicator(QObject):
    """
    Centralized theme applicator that manages theme application to all widgets.
    
    Features:
    - Tracks all themeable widgets using weak references
    - Applies theme to all tracked widgets when theme changes
    - Provides specific styling for different widget types
    - Ensures child widgets receive proper styling
    """
    
    def __init__(self):
        super().__init__()
        # Use WeakSet to automatically remove deleted widgets
        self._tracked_widgets: WeakSet = WeakSet()
        self._theme_aware_widgets: WeakSet = WeakSet()  # Widgets with _on_theme_changed method
        self._use_style_registry = True  # Prefer StyleRegistry over direct StyleTemplates
        
        # Initialize StyleRegistry integration
        try:
            from .style_registry import get_style_registry
            self._style_registry = get_style_registry()
            logger.info("ThemeApplicator initialized with StyleRegistry integration")
        except Exception as e:
            self._use_style_registry = False
            self._style_registry = None
            logger.warning(f"StyleRegistry not available, using fallback mode: {e}")
        
    def register_widget(self, widget: QWidget, theme_aware: bool = False, component_id: str = None):
        """
        Register a widget for theme updates.
        
        Args:
            widget: The widget to track
            theme_aware: Whether the widget has its own _on_theme_changed method
            component_id: Optional component ID for StyleRegistry registration
        """
        if theme_aware and hasattr(widget, '_on_theme_changed'):
            self._theme_aware_widgets.add(widget)
            logger.debug(f"Registered theme-aware widget: {widget.__class__.__name__}")
        else:
            self._tracked_widgets.add(widget)
            logger.debug(f"Registered widget for theme tracking: {widget.__class__.__name__}")
        
        # Also register with StyleRegistry if available and component_id provided
        if self._use_style_registry and self._style_registry and component_id:
            try:
                from .style_registry import ComponentCategory
                # Determine category based on widget class
                category = self._determine_widget_category(widget)
                self._style_registry.register_component(widget, component_id, category)
                logger.debug(f"Registered widget {component_id} with StyleRegistry")
            except Exception as e:
                logger.warning(f"Failed to register widget with StyleRegistry: {e}")
    
    def unregister_widget(self, widget: QWidget):
        """
        Unregister a widget from theme updates.
        
        Args:
            widget: The widget to stop tracking
        """
        self._tracked_widgets.discard(widget)
        self._theme_aware_widgets.discard(widget)
        
        # Also unregister from StyleRegistry if available
        if self._use_style_registry and self._style_registry:
            try:
                self._style_registry.unregister_component(widget)
                logger.debug(f"Unregistered widget from StyleRegistry")
            except Exception as e:
                logger.debug(f"Widget not registered with StyleRegistry or error: {e}")
        
        logger.debug(f"Unregistered widget: {widget.__class__.__name__}")
    
    def _determine_widget_category(self, widget: QWidget):
        """
        Determine the StyleRegistry category for a widget based on its class.
        
        Args:
            widget: The widget to categorize
            
        Returns:
            ComponentCategory appropriate for the widget
        """
        try:
            from .style_registry import ComponentCategory
            widget_class = widget.__class__.__name__
            
            # Map widget types to categories
            if 'Dialog' in widget_class or widget_class in ['QDialog']:
                return ComponentCategory.DIALOG
            elif any(x in widget_class for x in ['Tool', 'Button', 'Action']):
                return ComponentCategory.INTERACTIVE
            elif any(x in widget_class for x in ['Tab', 'Menu', 'Nav']):
                return ComponentCategory.NAVIGATION
            elif any(x in widget_class for x in ['Form', 'Input', 'Edit', 'Combo', 'Spin']):
                return ComponentCategory.FORM
            elif any(x in widget_class for x in ['Container', 'Frame', 'Group', 'Box']):
                return ComponentCategory.CONTAINER
            elif 'REPL' in widget_class or any(x in widget_class for x in ['Output', 'Console']):
                return ComponentCategory.REPL
            elif any(x in widget_class for x in ['Toolbar', 'StatusBar']):
                return ComponentCategory.TOOLBAR
            else:
                return ComponentCategory.DISPLAY
                
        except Exception as e:
            logger.debug(f"Error determining widget category: {e}")
            from .style_registry import ComponentCategory
            return ComponentCategory.DISPLAY
    
    def apply_theme_to_all(self, color_system: ColorSystem):
        """
        Apply theme to all tracked widgets.
        
        Args:
            color_system: The color system to apply
        """
        logger.info(f"Applying theme to {len(self._tracked_widgets)} tracked widgets and {len(self._theme_aware_widgets)} theme-aware widgets")
        
        # If StyleRegistry is available, delegate bulk theme updates to it
        if self._use_style_registry and self._style_registry:
            try:
                self._style_registry.apply_theme_to_all_components(color_system)
                logger.info("Bulk theme update delegated to StyleRegistry")
                
                # Still handle theme-aware widgets directly
                for widget in list(self._theme_aware_widgets):
                    try:
                        if hasattr(widget, '_on_theme_changed'):
                            widget._on_theme_changed(color_system)
                            logger.debug(f"Applied theme to theme-aware widget: {widget.__class__.__name__}")
                    except Exception as e:
                        logger.error(f"Failed to apply theme to theme-aware widget {widget.__class__.__name__}: {e}")
                
                return
                
            except Exception as e:
                logger.warning(f"StyleRegistry theme update failed, falling back: {e}")
        
        # Fallback: Apply themes individually
        # Apply to theme-aware widgets (they handle their own styling)
        for widget in list(self._theme_aware_widgets):
            try:
                if hasattr(widget, '_on_theme_changed'):
                    widget._on_theme_changed(color_system)
                    logger.debug(f"Applied theme to theme-aware widget: {widget.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to apply theme to theme-aware widget {widget.__class__.__name__}: {e}")
        
        # Apply to regular tracked widgets
        for widget in list(self._tracked_widgets):
            try:
                self._apply_theme_to_widget(widget, color_system)
            except Exception as e:
                logger.error(f"Failed to apply theme to widget {widget.__class__.__name__}: {e}")
        
        # Apply to all top-level windows
        self._apply_to_all_windows(color_system)
    
    def _apply_theme_to_widget(self, widget: QWidget, color_system: ColorSystem):
        """
        Apply theme to a specific widget based on its type.
        
        Args:
            widget: The widget to style
            color_system: The color system to use
        """
        widget_class = widget.__class__.__name__
        
        # Map widget types to style templates
        style_map = {
            'MainWindow': lambda cs: StyleTemplates.get_main_window_style(cs),
            'SettingsDialog': lambda cs: StyleTemplates.get_settings_dialog_style(cs),
            'QDialog': lambda cs: StyleTemplates.get_dialog_style(cs),
            'QTabWidget': lambda cs: StyleTemplates.get_tab_widget_style(cs),
            'QComboBox': lambda cs: StyleTemplates.get_combo_box_style(cs),
            'QLineEdit': lambda cs: StyleTemplates.get_line_edit_style(cs),
            'QTextEdit': lambda cs: StyleTemplates.get_text_edit_style(cs),
            'QPlainTextEdit': lambda cs: StyleTemplates.get_text_edit_style(cs),
            'QListWidget': lambda cs: StyleTemplates.get_list_widget_style(cs),
            'QTreeWidget': lambda cs: StyleTemplates.get_tree_widget_style(cs),
            'QPushButton': lambda cs: StyleTemplates.get_push_button_style(cs),
            'QToolButton': lambda cs: StyleTemplates.get_tool_button_style(cs),
            'QCheckBox': lambda cs: StyleTemplates.get_checkbox_style(cs),
            'QRadioButton': lambda cs: StyleTemplates.get_radio_button_style(cs),
            'QSlider': lambda cs: StyleTemplates.get_slider_style(cs),
            'QProgressBar': lambda cs: StyleTemplates.get_progress_bar_style(cs),
            'QScrollArea': lambda cs: StyleTemplates.get_scroll_area_style(cs),
            'QGroupBox': lambda cs: StyleTemplates.get_group_box_style(cs),
            'QFrame': lambda cs: StyleTemplates.get_frame_style(cs),
            'QLabel': lambda cs: StyleTemplates.get_label_style(cs),
            'QSpinBox': lambda cs: StyleTemplates.get_spin_box_style(cs),
            'QDoubleSpinBox': lambda cs: StyleTemplates.get_spin_box_style(cs),
        }
        
        # Try to find appropriate style
        style_getter = None
        
        # First check exact class name
        if widget_class in style_map:
            style_getter = style_map[widget_class]
        else:
            # Check parent classes
            for base_class, getter in style_map.items():
                if widget.__class__.__name__.endswith(base_class) or \
                   any(base.__name__ == base_class for base in widget.__class__.__bases__):
                    style_getter = getter
                    break
        
        # Apply style if found
        if style_getter:
            try:
                style = style_getter(color_system)
                widget.setStyleSheet(style)
                logger.debug(f"Applied theme style to {widget_class}")
            except Exception as e:
                logger.error(f"Failed to generate style for {widget_class}: {e}")
        else:
            # Apply generic widget style
            try:
                style = self._get_generic_widget_style(color_system)
                widget.setStyleSheet(style)
                logger.debug(f"Applied generic theme style to {widget_class}")
            except Exception as e:
                logger.error(f"Failed to apply generic style to {widget_class}: {e}")
    
    def _apply_to_all_windows(self, color_system: ColorSystem):
        """
        Apply theme to all top-level windows in the application.
        
        Args:
            color_system: The color system to apply
        """
        app = QApplication.instance()
        if not app:
            return
        
        # Get all top-level widgets
        for widget in app.topLevelWidgets():
            if widget.isVisible():
                # Skip if widget is already tracked
                if widget in self._tracked_widgets or widget in self._theme_aware_widgets:
                    continue
                
                try:
                    # Apply appropriate style based on widget type
                    if widget.__class__.__name__ == 'MainWindow':
                        style = StyleTemplates.get_main_window_style(color_system)
                    elif 'Dialog' in widget.__class__.__name__:
                        style = StyleTemplates.get_dialog_style(color_system)
                    else:
                        style = self._get_generic_widget_style(color_system)
                    
                    widget.setStyleSheet(style)
                    logger.debug(f"Applied theme to top-level window: {widget.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Failed to apply theme to window {widget.__class__.__name__}: {e}")
    
    def _get_generic_widget_style(self, color_system: ColorSystem) -> str:
        """
        Get generic widget style for widgets without specific templates.
        
        NOTE: This intentionally does NOT set font-family to preserve
        existing fonts, especially monospace fonts used in code elements.
        
        Args:
            color_system: The color system to use
            
        Returns:
            CSS style string
        """
        return f"""
        QWidget {{
            background-color: {color_system.background_primary};
            color: {color_system.text_primary};
        }}
        
        QWidget:disabled {{
            color: {color_system.text_disabled};
        }}
        """


# Global theme applicator instance
_theme_applicator = None


def get_theme_applicator() -> ThemeApplicator:
    """Get the global theme applicator instance."""
    global _theme_applicator
    if _theme_applicator is None:
        _theme_applicator = ThemeApplicator()
    return _theme_applicator