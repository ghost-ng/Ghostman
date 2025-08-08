"""Settings domain models with validation."""

from pydantic import BaseModel, Field, validator, SecretStr
from typing import Optional, Tuple
from enum import Enum
import re

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

class ToastPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"

class AIProviderSettings(BaseModel):
    """AI provider configuration with validation."""
    
    name: str = Field(default="OpenAI", description="Provider name")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API base URL"
    )
    model: str = Field(default="gpt-3.5-turbo", description="Model name")
    api_key: SecretStr = Field(default=SecretStr(""), description="API key")
    
    # Request parameters
    max_tokens: int = Field(default=1000, ge=1, le=32000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Response randomness")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Connection settings
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Retry attempts")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        """Validate API base URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        """Validate model name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Model name cannot be empty')
        return v.strip()

class WindowSettings(BaseModel):
    """Window behavior and positioning settings."""
    
    always_on_top: bool = Field(default=True, description="Keep windows always on top")
    remember_position: bool = Field(default=True, description="Remember window positions")
    auto_hide_delay: int = Field(default=30, ge=0, le=300, description="Auto-hide delay in seconds (0 = disabled)")
    
    # Opacity settings
    active_opacity: float = Field(default=0.95, ge=0.1, le=1.0, description="Window opacity when active")
    inactive_opacity: float = Field(default=0.8, ge=0.1, le=1.0, description="Window opacity when inactive")
    
    # Positioning
    avatar_position: Optional[Tuple[int, int]] = Field(default=None, description="Avatar widget position")
    main_window_position: Optional[Tuple[int, int]] = Field(default=None, description="Main window position")
    
    # Behavior
    start_minimized: bool = Field(default=False, description="Start application minimized")
    minimize_to_tray: bool = Field(default=True, description="Minimize to system tray")

class ConversationSettings(BaseModel):
    """Conversation management settings."""
    
    max_tokens: int = Field(default=4000, ge=1000, le=32000, description="Maximum tokens per conversation")
    auto_save: bool = Field(default=True, description="Automatically save conversations")
    backup_frequency: int = Field(default=24, ge=1, le=168, description="Backup frequency in hours")
    
    # Memory management
    trim_strategy: str = Field(default="sliding_window", description="Memory trimming strategy")
    summary_enabled: bool = Field(default=True, description="Enable conversation summarization")
    
    # Data retention
    max_conversations: int = Field(default=100, ge=10, le=1000, description="Maximum stored conversations")
    auto_delete_after_days: int = Field(default=90, ge=7, le=365, description="Auto-delete conversations after days")

class UISettings(BaseModel):
    """User interface preferences."""
    
    theme: Theme = Field(default=Theme.SYSTEM, description="Application theme")
    font_family: str = Field(default="Segoe UI", description="Font family")
    font_size: int = Field(default=10, ge=8, le=18, description="Font size")
    
    # Toast notifications
    toast_enabled: bool = Field(default=True, description="Enable toast notifications")
    toast_position: ToastPosition = Field(default=ToastPosition.BOTTOM_RIGHT, description="Toast position")
    toast_duration: int = Field(default=3000, ge=1000, le=10000, description="Toast duration in milliseconds")
    
    # Animations
    animations_enabled: bool = Field(default=True, description="Enable UI animations")
    animation_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Animation speed multiplier")

class PrivacySettings(BaseModel):
    """Privacy and security settings."""
    
    encrypt_conversations: bool = Field(default=False, description="Encrypt stored conversations")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    anonymous_analytics: bool = Field(default=False, description="Enable anonymous usage analytics")
    
    # Data handling
    clear_on_exit: bool = Field(default=False, description="Clear conversation data on exit")
    secure_delete: bool = Field(default=True, description="Secure deletion of files")

class HotkeySettings(BaseModel):
    """Keyboard shortcuts configuration."""
    
    toggle_visibility: str = Field(default="Ctrl+Shift+G", description="Toggle main window visibility")
    quick_prompt: str = Field(default="Ctrl+Shift+P", description="Quick prompt hotkey")
    emergency_hide: str = Field(default="Escape", description="Emergency hide hotkey")

class AppSettings(BaseModel):
    """Complete application settings."""
    
    # Core settings
    ai_provider: AIProviderSettings = Field(default_factory=AIProviderSettings)
    window: WindowSettings = Field(default_factory=WindowSettings)
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    ui: UISettings = Field(default_factory=UISettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)
    
    # Metadata
    version: str = Field(default="0.1.0", description="Settings version")
    created_at: Optional[str] = Field(default=None, description="Settings creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    
    class Config:
        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on assignment
        use_enum_values = True  # Use enum values instead of enum objects
        
    def update_timestamp(self):
        """Update the timestamp when settings change."""
        from datetime import datetime
        self.updated_at = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = self.updated_at