"""
Configuration paths utilities for Ghostman.

Provides centralized path management for all application data.
"""

import os
from pathlib import Path
from typing import Optional

def get_user_data_dir() -> Path:
    """
    Get the user data directory for Ghostman.
    
    Returns:
        Path to the user data directory (AppData/Roaming/Ghostman on Windows)
    """
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / "Ghostman"
    
    # Fallback for other platforms
    # Use XDG standard on Linux/Mac
    xdg_data_home = os.environ.get('XDG_DATA_HOME')
    if xdg_data_home:
        return Path(xdg_data_home) / "ghostman"
    
    # Default XDG location
    return Path.home() / ".local" / "share" / "ghostman"

def get_themes_dir() -> Path:
    """Get the themes directory."""
    themes_dir = get_user_data_dir() / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)
    return themes_dir

def get_configs_dir() -> Path:
    """Get the configs directory."""
    configs_dir = get_user_data_dir() / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    return configs_dir

def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs_dir = get_user_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def get_db_dir() -> Path:
    """Get the database directory."""
    db_dir = get_user_data_dir() / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir

def cleanup_old_files():
    """Clean up old/unused configuration files."""
    data_dir = get_user_data_dir()
    
    # List of files to remove (old/duplicate files)
    files_to_remove = [
        data_dir / "ai_config.json",
        data_dir / "themes.json",
        data_dir / "configs" / "ai_config.json",
        data_dir / "configs" / "app_settings.json",
        data_dir / "configs" / "application_state.json",
        data_dir / "configs" / "config.json",
        data_dir / "configs" / "conversations.json",
        data_dir / "configs" / "theme_config.json",
        data_dir / "configs" / "themes.json",
        data_dir / "configs" / "user_preferences.json",
        data_dir / "configs" / "window_config.json",
        data_dir / "configs" / "window_positions.json",
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"Removed: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")
    
    # Remove empty conversations directory if it exists
    conv_dir = data_dir / "configs" / "conversations"
    if conv_dir.exists() and conv_dir.is_dir():
        try:
            if not any(conv_dir.iterdir()):  # Check if directory is empty
                conv_dir.rmdir()
                print(f"Removed empty directory: {conv_dir}")
                removed_count += 1
        except Exception as e:
            print(f"Failed to remove directory {conv_dir}: {e}")
    
    return removed_count