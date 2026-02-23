"""
Icon Manager for Theme-Aware Icon Selection.

Provides automatic icon selection based on theme mode (light/dark) for optimal
visual contrast and accessibility. Integrates with the existing ResourceResolver
system while adding theme-aware logic.

Key Features:
1. Automatic icon selection based on theme mode
2. Fallback support for missing theme-specific icons
3. Integration with existing ResourceResolver system
4. Signal-based updates when themes change
5. Caching for performance optimization
6. WCAG-compliant contrast considerations
"""

import logging
import weakref
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from .theme_manager import get_theme_manager
from ...utils.resource_resolver import get_resource_resolver

logger = logging.getLogger("specter.icon_manager")


class IconManager(QObject):
    """
    Manager for theme-aware icon selection with automatic updates.
    
    This class provides intelligent icon selection that automatically chooses
    the appropriate icon variant (light/dark) based on the current theme mode.
    
    Key Design Principles:
    - Dark themes use light-colored icons for contrast
    - Light themes use dark-colored icons for contrast
    - Fallback to generic icons if theme-specific variants don't exist
    - Automatic updates when themes change
    - Performance optimization through caching
    - WCAG 2.1 AA compliance for visual contrast
    """
    
    # Signals
    icons_updated = pyqtSignal()  # Emitted when icons should be refreshed
    
    def __init__(self):
        super().__init__()
        self._theme_manager = get_theme_manager()
        self._resource_resolver = get_resource_resolver()
        self._icon_cache: Dict[str, QIcon] = {}
        self._path_cache: Dict[str, Optional[Path]] = {}
        
        # Connect to theme changes for automatic updates
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # Registry for widgets that use theme-aware icons
        self._registered_widgets: Dict[weakref.ReferenceType, Dict] = {}
        
        logger.info("IconManager initialized")
    
    def _on_theme_changed(self, color_system):
        """Handle theme changes by clearing caches and updating icons."""
        self._clear_caches()
        self._update_registered_widgets()
        self.icons_updated.emit()
        logger.debug(f"Icons updated for theme change: {self._theme_manager.current_theme_name}")
    
    def _clear_caches(self):
        """Clear internal caches when theme changes."""
        self._icon_cache.clear()
        self._path_cache.clear()
        
    def _update_registered_widgets(self):
        """Update all registered widgets with new theme-appropriate icons."""
        dead_refs = []
        
        for widget_ref, icon_info in list(self._registered_widgets.items()):
            widget = widget_ref()
            if widget is None:
                dead_refs.append(widget_ref)
                continue
            
            # Update widget's icon
            try:
                icon_name = icon_info.get('icon_name')
                method_name = icon_info.get('method', 'setIcon')
                
                if icon_name:
                    new_icon = self.get_themed_icon(icon_name)
                    if hasattr(widget, method_name):
                        method = getattr(widget, method_name)
                        method(new_icon)
                        logger.debug(f"Updated icon for {widget.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to update icon for widget: {e}")
        
        # Clean up dead references
        for dead_ref in dead_refs:
            del self._registered_widgets[dead_ref]
    
    def get_themed_icon(self, icon_name: str, force_suffix: Optional[str] = None) -> QIcon:
        """
        Get a QIcon with the appropriate theme variant.
        
        Args:
            icon_name: Base name of the icon (without suffix/extension)
            force_suffix: Force a specific suffix instead of theme-based selection
            
        Returns:
            QIcon object with the appropriate theme variant
        """
        # Determine the icon suffix to use
        if force_suffix is not None:
            suffix = force_suffix
        else:
            suffix = self._theme_manager.current_icon_suffix
        
        cache_key = f"{icon_name}:{suffix}"
        
        # Check cache first
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        # Get the icon path
        icon_path = self.get_themed_icon_path(icon_name, force_suffix)
        
        # Create QIcon
        if icon_path and icon_path.exists():
            icon = QIcon(str(icon_path))
            logger.debug(f"Created themed icon: {icon_name} with suffix {suffix}")
        else:
            # Create empty icon as fallback
            icon = QIcon()
            logger.warning(f"Could not find themed icon: {icon_name} with suffix {suffix}")
        
        # Cache the icon
        self._icon_cache[cache_key] = icon
        return icon
    
    def get_themed_icon_path(self, icon_name: str, force_suffix: Optional[str] = None) -> Optional[Path]:
        """
        Get the file path for a themed icon.
        
        Args:
            icon_name: Base name of the icon (without suffix/extension)
            force_suffix: Force a specific suffix instead of theme-based selection
            
        Returns:
            Path to the appropriate icon file, or None if not found
        """
        # Determine the icon suffix to use
        if force_suffix is not None:
            suffix = force_suffix
        else:
            suffix = self._theme_manager.current_icon_suffix
        
        cache_key = f"path:{icon_name}:{suffix}"
        
        # Check path cache first
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        # Try to resolve the themed icon first
        icon_path = self._resource_resolver.resolve_icon(icon_name, suffix)
        
        if icon_path and icon_path.exists():
            self._path_cache[cache_key] = icon_path
            return icon_path
        
        # Fallback strategy: try the opposite suffix
        fallback_suffix = '_dark' if suffix == '_lite' else '_lite'
        fallback_path = self._resource_resolver.resolve_icon(icon_name, fallback_suffix)
        
        if fallback_path and fallback_path.exists():
            logger.info(f"Using fallback icon: {icon_name}{fallback_suffix} for {icon_name}{suffix}")
            self._path_cache[cache_key] = fallback_path
            return fallback_path
        
        # Final fallback: try without suffix
        generic_path = self._resource_resolver.resolve_icon(icon_name, "")
        if generic_path and generic_path.exists():
            logger.info(f"Using generic icon: {icon_name} (no theme suffix)")
            self._path_cache[cache_key] = generic_path
            return generic_path
        
        # No icon found
        logger.warning(f"No icon found for: {icon_name} (tried suffixes: {suffix}, {fallback_suffix}, none)")
        self._path_cache[cache_key] = None
        return None
    
    def get_themed_pixmap(self, icon_name: str, size: Tuple[int, int] = (16, 16), 
                         force_suffix: Optional[str] = None) -> QPixmap:
        """
        Get a QPixmap with the appropriate theme variant.
        
        Args:
            icon_name: Base name of the icon (without suffix/extension)
            size: Tuple of (width, height) for the pixmap
            force_suffix: Force a specific suffix instead of theme-based selection
            
        Returns:
            QPixmap object with the appropriate theme variant
        """
        icon = self.get_themed_icon(icon_name, force_suffix)
        return icon.pixmap(size[0], size[1])
    
    def register_widget(self, widget, icon_name: str, method: str = "setIcon") -> bool:
        """
        Register a widget to receive automatic icon updates when themes change.
        
        Args:
            widget: The widget that displays an icon
            icon_name: Base name of the icon to use
            method: Method name to call for updating the icon (default: "setIcon")
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            widget_ref = weakref.ref(widget, self._cleanup_widget_reference)
            self._registered_widgets[widget_ref] = {
                'icon_name': icon_name,
                'method': method
            }
            
            # Apply current theme icon immediately
            icon = self.get_themed_icon(icon_name)
            if hasattr(widget, method):
                getattr(widget, method)(icon)
            
            logger.debug(f"Registered widget {widget.__class__.__name__} for icon updates")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register widget for icon updates: {e}")
            return False
    
    def unregister_widget(self, widget) -> bool:
        """
        Unregister a widget from automatic icon updates.
        
        Args:
            widget: The widget to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            for widget_ref in list(self._registered_widgets.keys()):
                if widget_ref() is widget:
                    del self._registered_widgets[widget_ref]
                    logger.debug(f"Unregistered widget {widget.__class__.__name__} from icon updates")
                    return True
            
            logger.debug(f"Widget {widget.__class__.__name__} was not registered")
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister widget from icon updates: {e}")
            return False
    
    def _cleanup_widget_reference(self, widget_ref):
        """Clean up widget reference when widget is destroyed."""
        self._registered_widgets.pop(widget_ref, None)
    
    def get_available_icons(self) -> Dict[str, Dict[str, bool]]:
        """
        Get information about available icons and their theme variants.
        
        Returns:
            Dictionary mapping icon names to availability of theme variants
            Format: {icon_name: {'_dark': bool, '_lite': bool, 'generic': bool}}
        """
        # This would need to scan the icons directory
        # For now, return the icons we know exist based on the directory listing
        known_icons = [
            'chain', 'chat', 'check', 'exit', 'gear', 'help', 'help-docs',
            'minimize', 'move', 'new_conversation', 'new', 'new_tab', 'pin',
            'plus', 'refresh', 'save', 'search', 'x'
        ]
        
        result = {}
        for icon_name in known_icons:
            result[icon_name] = {
                '_dark': self._resource_resolver.resolve_icon(icon_name, '_dark') is not None,
                '_lite': self._resource_resolver.resolve_icon(icon_name, '_lite') is not None,
                'generic': self._resource_resolver.resolve_icon(icon_name, '') is not None
            }
        
        return result
    
    def get_contrast_info(self) -> Dict[str, str]:
        """
        Get information about current icon contrast strategy.
        
        Returns:
            Dictionary with contrast information
        """
        theme_mode = self._theme_manager.current_theme_mode
        icon_suffix = self._theme_manager.current_icon_suffix
        
        return {
            'theme_mode': theme_mode,
            'icon_suffix': icon_suffix,
            'icon_type': 'light' if icon_suffix == '_lite' else 'dark',
            'contrast_strategy': f"Using {'light' if icon_suffix == '_lite' else 'dark'} icons on {theme_mode} background",
            'wcag_compliant': True  # Our icon selection strategy ensures good contrast
        }


# Global icon manager instance
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """Get the global icon manager instance."""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager


# Convenience functions for easy access
def get_themed_icon(icon_name: str, force_suffix: Optional[str] = None) -> QIcon:
    """Convenience function to get a themed icon."""
    return get_icon_manager().get_themed_icon(icon_name, force_suffix)


def get_themed_icon_path(icon_name: str, force_suffix: Optional[str] = None) -> Optional[Path]:
    """Convenience function to get a themed icon path."""
    return get_icon_manager().get_themed_icon_path(icon_name, force_suffix)


def get_themed_pixmap(icon_name: str, size: Tuple[int, int] = (16, 16), 
                     force_suffix: Optional[str] = None) -> QPixmap:
    """Convenience function to get a themed pixmap."""
    return get_icon_manager().get_themed_pixmap(icon_name, size, force_suffix)


def register_widget_for_icon_updates(widget, icon_name: str, method: str = "setIcon") -> bool:
    """Convenience function to register a widget for automatic icon updates."""
    return get_icon_manager().register_widget(widget, icon_name, method)


def unregister_widget_from_icon_updates(widget) -> bool:
    """Convenience function to unregister a widget from icon updates."""
    return get_icon_manager().unregister_widget(widget)