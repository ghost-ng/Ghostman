"""
Resource path resolution utilities for Specter.

Provides centralized path resolution for application resources like help files,
icons, and other assets based on how the application is running (development,
installed, bundled, etc.).
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger("specter.resource_resolver")


class ResourceResolver:
    """
    Centralized resource path resolver for Specter application.
    
    Handles different deployment scenarios:
    - Development mode (running from source)
    - Installed package mode (pip install)
    - Bundled executable mode (PyInstaller)
    - Relative path fallbacks
    """
    
    def __init__(self):
        self._cache = {}  # Cache resolved paths to avoid repeated filesystem checks
    
    def resolve_help_file(self, filename: str = "index.html") -> Optional[Path]:
        """
        Resolve path to help documentation files.
        
        Args:
            filename: The help file to find (default: "index.html")
            
        Returns:
            Path to the help file if found, None otherwise
        """
        cache_key = f"help:{filename}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Define possible paths for help documentation
        possible_paths = [
            # Development mode - relative to this file
            Path(__file__).parent.parent.parent.parent / "assets" / "help" / filename,
            # Installed package mode
            Path(sys.prefix) / "share" / "specter" / "help" / filename,
            # Bundled executable mode (PyInstaller)
            Path(getattr(sys, '_MEIPASS', Path.cwd())) / "specter" / "assets" / "help" / filename,
            # Relative to current working directory
            Path.cwd() / "specter" / "assets" / "help" / filename,
        ]
        
        result = self._find_existing_path(possible_paths, f"help file '{filename}'")
        self._cache[cache_key] = result
        return result
    
    def resolve_icon(self, icon_name: str, theme_suffix: str = "") -> Optional[Path]:
        """
        Resolve path to icon files.
        
        Args:
            icon_name: Base name of the icon (without extension)
            theme_suffix: Theme suffix like "_dark" or "_lite" (default: "")
            
        Returns:
            Path to the icon file if found, None otherwise
        """
        cache_key = f"icon:{icon_name}:{theme_suffix}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Construct full icon filename
        if theme_suffix and not theme_suffix.startswith('_'):
            theme_suffix = f"_{theme_suffix}"
        full_icon_name = f"{icon_name}{theme_suffix}.png"
        
        # Define possible paths for icons
        possible_paths = [
            # Development mode - relative to this file
            Path(__file__).parent.parent.parent.parent / "assets" / "icons" / full_icon_name,
            # Alternative development path
            Path(__file__).parent.parent.parent / "assets" / "icons" / full_icon_name,
            # Installed package mode
            Path(sys.prefix) / "share" / "specter" / "icons" / full_icon_name,
            # Bundled executable mode
            Path(getattr(sys, '_MEIPASS', Path.cwd())) / "specter" / "assets" / "icons" / full_icon_name,
            # Relative to current working directory
            Path.cwd() / "specter" / "assets" / "icons" / full_icon_name,
        ]
        
        # Special case for avatar, icon, and ghost - also check in main assets directory
        if icon_name in ["avatar", "icon", "ghost"] and not theme_suffix:
            # Add paths for icons in the main assets directory
            possible_paths.extend([
                # Development mode - relative to this file
                Path(__file__).parent.parent.parent.parent / "assets" / full_icon_name,
                # Alternative development path
                Path(__file__).parent.parent.parent / "assets" / full_icon_name,
                # Installed package mode
                Path(sys.prefix) / "share" / "specter" / full_icon_name,
                # Bundled executable mode
                Path(getattr(sys, '_MEIPASS', Path.cwd())) / "specter" / "assets" / full_icon_name,
                # Relative to current working directory
                Path.cwd() / "specter" / "assets" / full_icon_name,
            ])
        
        result = self._find_existing_path(possible_paths, f"icon '{full_icon_name}'")
        self._cache[cache_key] = result
        return result
    
    def resolve_asset(self, asset_path: str) -> Optional[Path]:
        """
        Resolve path to generic asset files.
        
        Args:
            asset_path: Relative path within the assets directory
            
        Returns:
            Path to the asset file if found, None otherwise
        """
        cache_key = f"asset:{asset_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Define possible paths for generic assets
        possible_paths = [
            # Development mode - relative to this file
            Path(__file__).parent.parent.parent.parent / "assets" / asset_path,
            # Installed package mode
            Path(sys.prefix) / "share" / "specter" / asset_path,
            # Bundled executable mode
            Path(getattr(sys, '_MEIPASS', Path.cwd())) / "specter" / "assets" / asset_path,
            # Relative to current working directory
            Path.cwd() / "specter" / "assets" / asset_path,
        ]
        
        result = self._find_existing_path(possible_paths, f"asset '{asset_path}'")
        self._cache[cache_key] = result
        return result
    
    def resolve_multiple_icons(self, icon_names: List[str], theme_suffix: str = "") -> Optional[Path]:
        """
        Resolve path to the first existing icon from a list of icon names.
        
        Args:
            icon_names: List of icon names to try (without extension)
            theme_suffix: Theme suffix like "_dark" or "_lite" (default: "")
            
        Returns:
            Path to the first existing icon file, None if none found
        """
        for icon_name in icon_names:
            icon_path = self.resolve_icon(icon_name, theme_suffix)
            if icon_path:
                return icon_path
        
        logger.warning(f"None of the icon names found: {icon_names} (theme: {theme_suffix})")
        return None
    
    def _find_existing_path(self, possible_paths: List[Path], resource_description: str) -> Optional[Path]:
        """
        Find the first existing path from a list of possible paths.
        
        Args:
            possible_paths: List of paths to check
            resource_description: Description for logging
            
        Returns:
            First existing path, or None if none exist
        """
        for path in possible_paths:
            try:
                if path.exists():
                    logger.debug(f"Found {resource_description} at: {path}")
                    return path
            except (OSError, PermissionError) as e:
                logger.debug(f"Error checking path {path}: {e}")
                continue
        
        logger.warning(f"{resource_description} not found in any expected location")
        logger.debug(f"Searched paths: {[str(p) for p in possible_paths]}")
        return None
    
    def clear_cache(self):
        """Clear the internal path cache."""
        self._cache.clear()
        logger.debug("Resource path cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get statistics about the cache."""
        return {
            'cached_items': len(self._cache),
            'cache_keys': list(self._cache.keys())
        }


# Global instance for easy access
_resolver = ResourceResolver()


def resolve_help_file(filename: str = "index.html") -> Optional[Path]:
    """Convenience function to resolve help file paths."""
    return _resolver.resolve_help_file(filename)


def resolve_icon(icon_name: str, theme_suffix: str = "") -> Optional[Path]:
    """Convenience function to resolve icon paths."""
    return _resolver.resolve_icon(icon_name, theme_suffix)


def resolve_asset(asset_path: str) -> Optional[Path]:
    """Convenience function to resolve generic asset paths."""
    return _resolver.resolve_asset(asset_path)


def resolve_multiple_icons(icon_names: List[str], theme_suffix: str = "") -> Optional[Path]:
    """Convenience function to resolve the first existing icon from a list."""
    return _resolver.resolve_multiple_icons(icon_names, theme_suffix)


def get_resource_resolver() -> ResourceResolver:
    """Get the global resource resolver instance."""
    return _resolver


def resolve_themed_icon(icon_name: str) -> Optional[Path]:
    """
    Convenience function to resolve icon with automatic theme-aware suffix selection.
    
    This function integrates with the theme system to automatically choose the
    appropriate icon variant based on the current theme mode.
    
    Args:
        icon_name: Base name of the icon (without suffix/extension)
        
    Returns:
        Path to the appropriate themed icon file, or None if not found
    """
    try:
        # Import here to avoid circular imports
        from ..ui.themes.theme_manager import get_theme_manager
        
        theme_manager = get_theme_manager()
        suffix = theme_manager.current_icon_suffix
        
        # Try themed icon first
        icon_path = _resolver.resolve_icon(icon_name, suffix)
        if icon_path and icon_path.exists():
            return icon_path
        
        # Fallback to opposite theme
        fallback_suffix = '_dark' if suffix == '_lite' else '_lite'
        fallback_path = _resolver.resolve_icon(icon_name, fallback_suffix)
        if fallback_path and fallback_path.exists():
            return fallback_path
        
        # Final fallback to generic
        return _resolver.resolve_icon(icon_name, "")
        
    except ImportError:
        # Theme system not available, use generic icon
        return _resolver.resolve_icon(icon_name, "")


# For backward compatibility and migration
def get_help_path(filename: str = "index.html") -> Optional[Path]:
    """Legacy function name for help path resolution."""
    return resolve_help_file(filename)


if __name__ == "__main__":
    # Test the resource resolver
    resolver = ResourceResolver()
    
    print("Testing ResourceResolver...")
    
    # Test help file resolution
    help_path = resolver.resolve_help_file()
    print(f"Help file: {help_path}")
    
    # Test icon resolution
    icon_path = resolver.resolve_icon("chat", "_dark")
    print(f"Chat icon: {icon_path}")
    
    # Test multiple icon resolution
    avatar_icons = ["avatar", "icon", "ghost"]
    avatar_path = resolver.resolve_multiple_icons(avatar_icons)
    print(f"Avatar icon: {avatar_path}")
    
    # Show cache stats
    print(f"Cache stats: {resolver.get_cache_stats()}")