"""
Resizable Mixin for Frameless Windows.

Provides a clean mixin interface for adding resize functionality to existing widgets.
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from .resize_manager import ResizeManager
from .constraints import SizeConstraints
from .hit_zones import HitZone

if TYPE_CHECKING:
    pass

logger = logging.getLogger("specter.resize.mixin")


class ResizableMixin:
    """
    Mixin to add resize functionality to frameless widgets.
    
    This mixin provides a clean interface for integrating the resize system
    with existing widget hierarchies without disrupting inheritance patterns.
    """
    
    # Signals (these will be added to the widget when mixed in)
    resize_started: pyqtSignal = pyqtSignal(HitZone)
    resize_updated: pyqtSignal = pyqtSignal(HitZone, int, int)
    resize_finished: pyqtSignal = pyqtSignal(HitZone, int, int)
    
    def __init_resize__(
        self, 
        constraints: Optional[SizeConstraints] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize resize functionality.
        
        This method should be called during widget initialization.
        
        Args:
            constraints: Size constraints for the widget
            config: Configuration options for resize behavior
        """
        if not isinstance(self, QWidget):
            raise TypeError("ResizableMixin can only be used with QWidget subclasses")
        
        self._resize_manager: Optional[ResizeManager] = None
        self._resize_constraints = constraints
        self._resize_config = config or {}
        self._resize_enabled = True
        
        # Store reference for cleanup
        self._resize_initialized = True
        
        logger.debug(f"ResizableMixin initialized for {type(self).__name__}")
    
    def enable_resize(self):
        """Enable resize functionality."""
        if not hasattr(self, '_resize_initialized'):
            logger.warning("Resize not initialized. Call __init_resize__() first.")
            return
        
        try:
            if self._resize_manager is None:
                # Create resize manager
                self._resize_manager = ResizeManager(
                    widget=self,
                    constraints=self._resize_constraints,
                    config=self._resize_config
                )
                
                # Connect signals if widget has them
                if hasattr(self, 'resize_started'):
                    self._resize_manager.resize_started.connect(self.resize_started.emit)
                if hasattr(self, 'resize_updated'):
                    self._resize_manager.resize_updated.connect(self.resize_updated.emit)
                if hasattr(self, 'resize_finished'):
                    self._resize_manager.resize_finished.connect(self.resize_finished.emit)
                
                logger.debug(f"Resize enabled for {type(self).__name__}")
            else:
                self._resize_manager.set_enabled(True)
                
        except Exception as e:
            logger.error(f"Failed to enable resize: {e}")
            raise
    
    def disable_resize(self):
        """Disable resize functionality temporarily."""
        if self._resize_manager:
            self._resize_manager.set_enabled(False)
            logger.debug(f"Resize disabled for {type(self).__name__}")
    
    def cleanup_resize(self):
        """Clean up resize resources."""
        if self._resize_manager:
            self._resize_manager.cleanup()
            self._resize_manager = None
            logger.debug(f"Resize cleaned up for {type(self).__name__}")
    
    def set_resize_constraints(self, constraints: SizeConstraints):
        """Update resize constraints."""
        self._resize_constraints = constraints
        if self._resize_manager:
            self._resize_manager.set_constraints(constraints)
    
    def set_resize_border_width(self, width: int):
        """Set the resize border width."""
        if self._resize_manager:
            self._resize_manager.set_border_width(width)
        else:
            # Store in config for later
            self._resize_config['border_width'] = width
    
    def is_resize_enabled(self) -> bool:
        """Check if resize is currently enabled."""
        return (self._resize_manager is not None and 
                self._resize_manager.is_enabled)
    
    def is_currently_resizing(self) -> bool:
        """Check if currently in a resize operation."""
        return (self._resize_manager is not None and 
                self._resize_manager.is_resizing())
    
    def get_resize_status(self) -> Dict[str, Any]:
        """Get detailed resize status."""
        if self._resize_manager:
            return self._resize_manager.get_status()
        else:
            return {
                'enabled': False,
                'resizing': False,
                'initialized': hasattr(self, '_resize_initialized')
            }
    
    def _get_resize_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to default."""
        return self._resize_config.get(key, default)


class AvatarResizableMixin(ResizableMixin):
    """Specialized mixin for avatar widgets with aspect ratio preservation."""
    
    def __init_avatar_resize__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize avatar-specific resize functionality.
        
        Args:
            config: Additional configuration options
        """
        # Create avatar-specific constraints
        constraints = SizeConstraints.for_avatar()
        
        # Avatar-specific configuration
        avatar_config = {
            'border_width': 6,  # Smaller border for avatar
            'enable_cursor_changes': True,
        }
        avatar_config.update(config or {})
        
        self.__init_resize__(constraints=constraints, config=avatar_config)


class REPLResizableMixin(ResizableMixin):
    """Specialized mixin for REPL windows with minimum size requirements."""
    
    def __init_repl_resize__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize REPL-specific resize functionality.
        
        Args:
            config: Additional configuration options
        """
        # Create REPL-specific constraints
        constraints = SizeConstraints.for_repl()
        
        # REPL-specific configuration
        repl_config = {
            'border_width': 8,  # Standard border for REPL
            'enable_cursor_changes': True,
        }
        repl_config.update(config or {})
        
        self.__init_resize__(constraints=constraints, config=repl_config)


def add_resize_to_widget(
    widget: QWidget,
    constraints: Optional[SizeConstraints] = None,
    config: Optional[Dict[str, Any]] = None,
    auto_enable: bool = True
) -> ResizeManager:
    """
    Add resize functionality to an existing widget without inheritance.
    
    This is a functional approach for cases where mixin inheritance isn't suitable.
    
    Args:
        widget: Widget to add resize functionality to
        constraints: Size constraints
        config: Configuration options
        auto_enable: Whether to automatically enable resize functionality
        
    Returns:
        ResizeManager instance for the widget
    """
    try:
        # Create and configure resize manager
        resize_manager = ResizeManager(widget, constraints, config)
        
        if auto_enable:
            resize_manager.set_enabled(True)
        
        # Store reference on widget for cleanup
        if not hasattr(widget, '_resize_managers'):
            widget._resize_managers = []
        widget._resize_managers.append(resize_manager)
        
        logger.debug(f"Resize functionality added to {type(widget).__name__}")
        return resize_manager
        
    except Exception as e:
        logger.error(f"Failed to add resize to widget: {e}")
        raise


def remove_resize_from_widget(widget: QWidget):
    """Remove all resize functionality from a widget."""
    if hasattr(widget, '_resize_managers'):
        for manager in widget._resize_managers:
            manager.cleanup()
        widget._resize_managers.clear()
        logger.debug(f"Resize functionality removed from {type(widget).__name__}")