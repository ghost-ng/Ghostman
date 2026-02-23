"""
Integration helpers for the frameless window resize system.

Provides utility functions for easily integrating resize functionality 
into existing Specter widgets with proper settings integration.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QWidget

from .resize_mixin import add_resize_to_widget, ResizeManager
from .constraints import SizeConstraints

logger = logging.getLogger("specter.resize.integration")


def setup_avatar_resize(avatar_widget: QWidget, settings_manager=None) -> Optional[ResizeManager]:
    """
    Setup resize functionality for an avatar widget using settings.
    
    Args:
        avatar_widget: The avatar widget to add resize functionality to
        settings_manager: Settings manager instance (optional)
        
    Returns:
        ResizeManager instance or None if setup failed
    """
    try:
        # Get settings
        if settings_manager:
            enabled = settings_manager.is_resize_enabled('avatar')
            if not enabled:
                logger.debug("Avatar resize disabled in settings")
                return None
            
            config = settings_manager.get_resize_config('avatar')
            
            # Create size constraints from settings
            min_size = config.get('min_size', {'width': 80, 'height': 80})
            max_size = config.get('max_size', {'width': 200, 'height': 200})
            
            constraints = SizeConstraints(
                min_width=min_size['width'],
                min_height=min_size['height'],
                max_width=max_size['width'],
                max_height=max_size['height'],
                maintain_aspect_ratio=config.get('maintain_aspect_ratio', True)
            )
            
            # Create config dict for resize manager
            resize_config = {
                'border_width': config.get('border_width', 6),
                'enable_cursor_changes': config.get('enable_cursor_changes', True)
            }
        else:
            # Use defaults
            constraints = SizeConstraints.for_avatar()
            resize_config = {'border_width': 6, 'enable_cursor_changes': True}
        
        # Add resize functionality
        resize_manager = add_resize_to_widget(
            avatar_widget,
            constraints=constraints,
            config=resize_config
        )
        
        logger.info("Avatar resize functionality setup successfully")
        return resize_manager
        
    except Exception as e:
        logger.error(f"Failed to setup avatar resize: {e}")
        return None


def setup_repl_resize(repl_widget: QWidget, settings_manager=None) -> Optional[ResizeManager]:
    """
    Setup resize functionality for a REPL widget using settings.
    
    Args:
        repl_widget: The REPL widget to add resize functionality to
        settings_manager: Settings manager instance (optional)
        
    Returns:
        ResizeManager instance or None if setup failed
    """
    try:
        # Get settings
        if settings_manager:
            enabled = settings_manager.is_resize_enabled('repl')
            if not enabled:
                logger.debug("REPL resize disabled in settings")
                return None
            
            config = settings_manager.get_resize_config('repl')
            
            # Create size constraints from settings
            min_size = config.get('min_size', {'width': 360, 'height': 320})
            max_size = config.get('max_size', {'width': None, 'height': None})
            
            constraints = SizeConstraints(
                min_width=min_size['width'],
                min_height=min_size['height'],
                max_width=max_size['width'],
                max_height=max_size['height']
            )
            
            # Create config dict for resize manager
            resize_config = {
                'border_width': config.get('border_width', 8),
                'enable_cursor_changes': config.get('enable_cursor_changes', True)
            }
        else:
            # Use defaults
            constraints = SizeConstraints.for_repl()
            resize_config = {'border_width': 8, 'enable_cursor_changes': True}
        
        # Add resize functionality
        resize_manager = add_resize_to_widget(
            repl_widget,
            constraints=constraints,
            config=resize_config
        )
        
        logger.info("REPL resize functionality setup successfully")
        return resize_manager
        
    except Exception as e:
        logger.error(f"Failed to setup REPL resize: {e}")
        return None


def update_resize_settings(resize_manager: ResizeManager, settings_manager, widget_type: str):
    """
    Update a resize manager's settings from the settings manager.
    
    Args:
        resize_manager: The resize manager to update
        settings_manager: Settings manager instance
        widget_type: 'avatar' or 'repl'
    """
    try:
        # Check if resize is still enabled
        if not settings_manager.is_resize_enabled(widget_type):
            resize_manager.set_enabled(False)
            logger.debug(f"{widget_type.title()} resize disabled via settings")
            return
        
        # Get updated config
        config = settings_manager.get_resize_config(widget_type)
        
        # Update border width
        border_width = config.get('border_width', 8)
        resize_manager.set_border_width(border_width)
        
        # Update constraints if settings changed
        min_size = config.get('min_size', {})
        max_size = config.get('max_size', {})
        
        if min_size or max_size:
            constraints = SizeConstraints(
                min_width=min_size.get('width'),
                min_height=min_size.get('height'),
                max_width=max_size.get('width'),
                max_height=max_size.get('height'),
                maintain_aspect_ratio=config.get('maintain_aspect_ratio', widget_type == 'avatar')
            )
            resize_manager.set_constraints(constraints)
        
        # Re-enable if it was disabled
        resize_manager.set_enabled(True)
        
        logger.debug(f"{widget_type.title()} resize settings updated")
        
    except Exception as e:
        logger.error(f"Failed to update {widget_type} resize settings: {e}")


def get_resize_status_info(widget: QWidget) -> Dict[str, Any]:
    """
    Get comprehensive status information about a widget's resize functionality.
    
    Args:
        widget: Widget to check
        
    Returns:
        Dictionary with status information
    """
    info = {
        'has_resize': False,
        'enabled': False,
        'resizing': False,
        'managers': [],
        'error': None
    }
    
    try:
        # Check for resize managers
        if hasattr(widget, '_resize_managers'):
            info['has_resize'] = True
            info['managers'] = len(widget._resize_managers)
            
            if widget._resize_managers:
                manager = widget._resize_managers[0]  # Use first manager
                status = manager.get_status()
                info.update(status)
        
        # Check for mixin methods
        elif hasattr(widget, 'get_resize_status'):
            info['has_resize'] = True
            status = widget.get_resize_status()
            info.update(status)
        
    except Exception as e:
        info['error'] = str(e)
    
    return info