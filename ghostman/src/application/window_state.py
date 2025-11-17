"""
Simple window state management.

Tracks and saves window positions and sizes to settings.
"""

import logging
from ..infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.window_state")


def save_window_state(window_type: str, x: int, y: int, width: int, height: int):
    """
    Save window position and size to settings.
    
    Args:
        window_type: 'avatar' or 'repl'
        x, y: Window position
        width, height: Window size
    """
    try:
        if window_type == 'avatar':
            settings.set('ui.avatar_position', {'x': x, 'y': y})
            settings.set('ui.avatar_size', {'width': width, 'height': height})
        elif window_type == 'repl':
            settings.set('ui.repl_position', {'x': x, 'y': y})
            settings.set('ui.repl_size', {'width': width, 'height': height})
            # Keep backward compatibility
            settings.set('ui.repl_width', width)
            settings.set('ui.repl_height', height)
        
        settings.save()
        logger.debug(f"Saved {window_type} window state: pos=({x}, {y}), size=({width}, {height})")
        
    except Exception as e:
        logger.error(f"Failed to save {window_type} window state: {e}")


def load_window_state(window_type: str) -> dict:
    """
    Load window position and size from settings.
    
    Args:
        window_type: 'avatar' or 'repl'
        
    Returns:
        Dictionary with 'position' and 'size' keys
    """
    try:
        if window_type == 'avatar':
            # Check if we have saved position, if not return None to trigger bottom-right default
            position = settings.get('ui.avatar_position', None)
            size = settings.get('ui.avatar_size', {'width': 400, 'height': 600})
            
            if position is None:
                # Signal that no saved position exists - main window will use bottom-right default
                logger.debug("No saved avatar position found - will use bottom-right default")
                return {'position': None, 'size': size}
            
        elif window_type == 'repl':
            position = settings.get('ui.repl_position', {'x': 550, 'y': 100})
            size = settings.get('ui.repl_size', {'width': 520, 'height': 650})
        else:
            return {'position': {'x': 100, 'y': 100}, 'size': {'width': 400, 'height': 300}}
        
        logger.debug(f"Loaded {window_type} window state: pos={position}, size={size}")
        return {'position': position, 'size': size}
        
    except Exception as e:
        logger.error(f"Failed to load {window_type} window state: {e}")
        # Return defaults
        if window_type == 'avatar':
            return {'position': None, 'size': {'width': 400, 'height': 600}}  # None triggers bottom-right
        else:
            return {'position': {'x': 550, 'y': 100}, 'size': {'width': 520, 'height': 650}}