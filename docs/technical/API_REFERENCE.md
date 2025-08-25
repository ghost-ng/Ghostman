# Ghostman API Reference

## Core Services

### AI Service Interface
```python
class AIService:
    def send_message(message: str, save_conversation: bool = True) -> str
    def get_current_conversation_id() -> Optional[str]
    def set_current_conversation(conversation_id: str) -> None
    def clear_context() -> None
```

### Conversation Manager
```python
class ConversationManager:
    def create_conversation(title: str = None) -> Conversation
    def get_conversation(id: str) -> Optional[Conversation]
    def update_conversation(id: str, **kwargs) -> bool
    def delete_conversation(id: str) -> bool
    def list_conversations(status: str = None) -> List[Conversation]
```

### Theme Manager
```python
class ThemeManager:
    @property
    def current_theme() -> ColorSystem
    def set_theme(theme_name: str) -> bool
    def get_available_themes() -> List[str]
    def create_custom_theme(name: str, colors: ColorSystem) -> bool
```

## Widget APIs

### AvatarWidget
```python
class AvatarWidget(QWidget):
    # Signals
    avatar_clicked = pyqtSignal()
    minimize_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    conversations_requested = pyqtSignal()
    help_requested = pyqtSignal()
    quit_requested = pyqtSignal()
```

### ReplWidget
```python
class ReplWidget(QWidget):
    # Signals
    message_sent = pyqtSignal(str)
    conversation_changed = pyqtSignal(str)
    
    # Methods
    def append_output(text: str, style: str = "default") -> None
    def clear_output() -> None
    def set_processing_mode(processing: bool) -> None
```

### TabConversationManager
```python
class TabConversationManager(QObject):
    # Signals
    tab_switched = pyqtSignal(str)
    tab_created = pyqtSignal(str)
    tab_closed = pyqtSignal(str)
    
    # Methods
    def create_tab(title: str = "New Conversation") -> str
    def close_tab(tab_id: str) -> bool
    def switch_to_tab(tab_id: str) -> None
    def update_tab_title(tab_id: str, title: str) -> None
```

## Data Models

### Conversation
```python
@dataclass
class Conversation:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    status: ConversationStatus
    messages: List[Message]
    summary: Optional[str]
```

### Message
```python
@dataclass
class Message:
    id: str
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    timestamp: datetime
    conversation_id: str
```

### ColorSystem
```python
@dataclass
class ColorSystem:
    # Background colors
    background_primary: str
    background_secondary: str
    background_tertiary: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_tertiary: str
    
    # Brand colors
    primary: str
    primary_hover: str
    secondary: str
    accent: str
    
    # Status colors
    status_success: str
    status_warning: str
    status_error: str
    status_info: str
    
    # Interactive colors
    interactive_hover: str
    interactive_active: str
    
    # Border colors
    border_primary: str
    border_secondary: str
    border_focus: str
    
    # Other
    separator: str
```

## Event System

### Signal/Slot Connections
```python
# Example: Connecting avatar click to REPL toggle
avatar_widget.avatar_clicked.connect(main_window.toggle_repl)

# Example: Handling conversation changes
repl_widget.conversation_changed.connect(
    lambda id: conversation_manager.load_conversation(id)
)
```

## Extension Points

### Custom AI Provider
```python
class CustomAIProvider(AIService):
    def __init__(self, api_key: str):
        super().__init__()
        # Custom initialization
    
    def send_message(self, message: str, **kwargs) -> str:
        # Custom implementation
        pass
```

### Custom Theme
```python
def register_custom_theme():
    colors = ColorSystem(
        background_primary="#1a1a1a",
        text_primary="#ffffff",
        # ... other colors
    )
    theme_manager.create_custom_theme("my_theme", colors)
```

## For More Information
- [Architecture Overview](ARCHITECTURE.md)
- [Component Documentation](components/)
- [User Guide](../../USER_GUIDE.md)