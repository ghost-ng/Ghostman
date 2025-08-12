# Ghostman Conversation Management System

## Complete Implementation Guide

### Overview

This comprehensive conversation management system provides persistent conversation storage, search capabilities, AI-powered summaries, export functionality, and advanced features for the Ghostman AI assistant application.

### 🎯 Key Features

- **Persistent Storage**: SQLite database with full conversation history
- **Multiple Conversations**: Support for concurrent conversation threads
- **Full-Text Search**: Advanced search with filtering and sorting
- **AI Integration**: Seamless integration with existing AIService
- **Export Capabilities**: JSON, TXT, Markdown, and HTML formats
- **Smart Summaries**: AI-powered conversation summaries
- **Advanced Features**: Templates, favorites, analytics, and more
- **User-Friendly UI**: Enhanced REPL and conversation browser

---

## 📁 Architecture Overview

```
conversation_management/
├── models/                  # Data models and schemas
│   ├── conversation.py      # Core conversation models
│   ├── search.py           # Search models
│   └── enums.py            # Enumerations
├── repositories/           # Data access layer
│   ├── database.py         # SQLite database manager
│   └── conversation_repository.py
├── services/               # Business logic
│   ├── conversation_service.py
│   ├── summary_service.py
│   └── export_service.py
├── integration/            # AI service integration
│   ├── ai_service_integration.py
│   └── conversation_manager.py
├── ui/                     # UI components
│   ├── repl_integration.py
│   └── conversation_browser.py
└── advanced/               # Advanced features
    └── advanced_features.py
```

---

## 🚀 Quick Start Implementation

### 1. Basic Integration

Replace your existing REPL widget with the enhanced conversation-aware version:

```python
# In your main application file
from ghostman.src.infrastructure.conversation_management import ConversationManager
from ghostman.src.infrastructure.conversation_management.ui import ConversationREPLWidget

# Initialize conversation manager
conversation_manager = ConversationManager()
if conversation_manager.initialize():
    # Replace existing REPL widget
    enhanced_repl = ConversationREPLWidget(conversation_manager)
    
    # Get AI service with conversation support
    ai_service = conversation_manager.get_ai_service()
```

### 2. Full Integration with Existing AIService

Modify your existing AI service initialization:

```python
# Instead of using AIService directly, use ConversationAIService
from ghostman.src.infrastructure.conversation_management.integration import ConversationAIService

# Initialize conversation-aware AI service
ai_service = ConversationAIService()
if ai_service.initialize():
    # Enable features
    ai_service.set_auto_save(True)
    ai_service.set_auto_generate_titles(True)
    ai_service.set_auto_generate_summaries(True)
    
    # Start a new conversation
    conversation_id = await ai_service.start_new_conversation(
        title="My First Conversation",
        tags={"python", "ai"},
        category="development"
    )
```

---

## 🔧 Detailed Integration Steps

### Step 1: Database Initialization

The system automatically creates and manages the SQLite database:

```python
from ghostman.src.infrastructure.conversation_management.repositories import DatabaseManager

# Database will be created in your settings directory
# Default location: ~/.ghostman/conversations.db or AppData equivalent
db_manager = DatabaseManager()
db_manager.initialize()
```

### Step 2: Basic Conversation Operations

```python
from ghostman.src.infrastructure.conversation_management import ConversationManager

async def basic_operations():
    manager = ConversationManager()
    manager.initialize()
    
    # Create a new conversation
    conversation = await manager.create_conversation(
        title="My Conversation",
        tags={"important", "work"},
        category="business"
    )
    
    # List recent conversations
    recent = await manager.get_recent_conversations(limit=10)
    
    # Search conversations
    from ghostman.src.infrastructure.conversation_management.models import SearchQuery
    query = SearchQuery.create_simple_text_search("python coding")
    results = await manager.search_conversations(query)
    
    # Export conversation
    await manager.export_conversation(
        conversation.id,
        "markdown",
        "/path/to/export.md"
    )
```

### Step 3: UI Integration

#### Enhanced REPL Widget

```python
from ghostman.src.infrastructure.conversation_management.ui import ConversationREPLWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager()
        self.conversation_manager.initialize()
        
        # Create enhanced REPL
        self.repl = ConversationREPLWidget(self.conversation_manager)
        
        # Connect signals
        self.repl.conversation_created.connect(self.on_conversation_created)
        self.repl.conversation_switched.connect(self.on_conversation_switched)
        self.repl.export_requested.connect(self.on_export_requested)
        
        self.setCentralWidget(self.repl)
    
    def on_conversation_created(self, conversation_id: str):
        print(f"New conversation created: {conversation_id}")
    
    def on_conversation_switched(self, conversation_id: str):
        print(f"Switched to conversation: {conversation_id}")
    
    def on_export_requested(self, conversation_id: str, format: str):
        # Handle export request
        self.export_conversation(conversation_id, format)
```

#### Conversation Browser Dialog

```python
from ghostman.src.infrastructure.conversation_management.ui import ConversationBrowserDialog

def show_conversation_browser():
    dialog = ConversationBrowserDialog(conversation_manager)
    dialog.conversation_loaded.connect(load_conversation_in_repl)
    dialog.exec()

def load_conversation_in_repl(conversation_id: str):
    # Load conversation in the main REPL
    repl.load_conversation(conversation_id)
```

### Step 4: Advanced Features Integration

```python
from ghostman.src.infrastructure.conversation_management.advanced import AdvancedFeaturesManager

async def setup_advanced_features():
    # Initialize advanced features
    settings_dir = Path("~/.ghostman").expanduser()
    advanced = AdvancedFeaturesManager(repository, settings_dir)
    
    # Get conversation templates
    templates = advanced.get_templates()
    
    # Create conversation from template
    conversation = advanced.create_from_template("coding_help", "Debug Python Code")
    
    # Manage favorites
    advanced.add_favorite(conversation.id)
    favorites = await advanced.get_favorites()
    
    # Get analytics
    analytics = await advanced.get_analytics()
    print(f"Total conversations: {analytics.total_conversations}")
    print(f"Average messages per conversation: {analytics.avg_messages_per_conversation}")
```

---

## 🎨 Customization Options

### 1. Custom System Prompts per Template

```python
custom_template = ConversationTemplate(
    id="custom_assistant",
    name="Custom Assistant",
    description="My personalized AI assistant",
    system_prompt="You are my personal AI assistant with deep knowledge of my preferences...",
    initial_tags={"personal", "custom"},
    category="personal"
)
```

### 2. Custom Export Formats

Extend the ExportService to add new formats:

```python
class CustomExportService(ExportService):
    async def _export_custom_format(self, conversations, file_path, include_metadata):
        # Implement your custom export format
        pass
```

### 3. Advanced Search Queries

```python
# Complex search with multiple filters
query = SearchQuery(
    text="python debugging",
    tags={"coding", "python"},
    category="development",
    created_after=datetime(2024, 1, 1),
    min_messages=5,
    sort_order=SortOrder.UPDATED_DESC,
    limit=20
)

results = await manager.search_conversations(query)
```

---

## 📊 Performance Considerations

### Database Optimization

1. **Indexing**: The system includes proper indexing on frequently queried columns
2. **Full-Text Search**: Uses SQLite FTS5 for efficient text search
3. **Connection Pooling**: Thread-local connections for concurrent access
4. **WAL Mode**: Write-Ahead Logging for better concurrency

### Memory Management

1. **Lazy Loading**: Messages loaded only when needed
2. **Pagination**: Large result sets are paginated
3. **Connection Management**: Proper cleanup of database connections

### Async Operations

All database operations are designed to be async-compatible:

```python
# Non-blocking conversation loading
conversation = await manager.get_conversation(conversation_id)

# Async search
results = await manager.search_conversations(query)

# Background export
await manager.export_conversation(conv_id, "json", "export.json")
```

---

## 🔒 Security Considerations

### Data Encryption

- Sensitive conversation data can be encrypted using the existing SettingsManager encryption
- API keys and tokens are automatically encrypted
- Database file permissions are restricted

### Privacy

- Local storage only - no data sent to external services
- Configurable data retention policies
- Secure deletion options

---

## 🧪 Testing Strategy

### Unit Tests

```python
import pytest
from ghostman.src.infrastructure.conversation_management import ConversationService

@pytest.mark.asyncio
async def test_conversation_creation():
    service = ConversationService()
    conversation = await service.create_conversation("Test Conversation")
    assert conversation is not None
    assert conversation.title == "Test Conversation"

@pytest.mark.asyncio
async def test_message_persistence():
    service = ConversationService()
    conversation = await service.create_conversation("Test")
    
    message = await service.add_message_to_conversation(
        conversation.id,
        MessageRole.USER,
        "Hello, AI!"
    )
    
    assert message is not None
    
    # Reload conversation and verify message persistence
    reloaded = await service.get_conversation(conversation.id)
    assert len(reloaded.messages) == 2  # system + user message
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_conversation_flow():
    manager = ConversationManager()
    manager.initialize()
    
    # Create conversation
    conversation = await manager.create_conversation("Integration Test")
    
    # Add messages
    ai_service = manager.get_ai_service()
    result = ai_service.send_message("Hello, how are you?")
    
    # Verify persistence
    reloaded = await manager.get_conversation(conversation.id)
    assert len(reloaded.messages) >= 2
    
    # Test export
    export_path = "/tmp/test_export.json"
    success = await manager.export_conversation(conversation.id, "json", export_path)
    assert success
    assert Path(export_path).exists()
```

---

## 🚨 Error Handling

The system includes comprehensive error handling:

```python
try:
    conversation = await manager.create_conversation("Test")
except ConversationServiceError as e:
    logger.error(f"Conversation service error: {e}")
    # Handle gracefully
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    # Attempt recovery
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Fallback behavior
```

### Graceful Degradation

- If database is unavailable, fall back to in-memory conversations
- If AI service fails, maintain conversation history
- Export functionality has multiple format fallbacks

---

## 📈 Monitoring and Analytics

### Built-in Analytics

```python
# Get comprehensive analytics
analytics = await manager.get_conversation_statistics()

print(f"Database stats: {analytics['database_stats']}")
print(f"Conversation stats: {analytics['conversation_stats']}")
print(f"AI service stats: {analytics['ai_service_stats']}")
```

### Custom Metrics

You can extend the analytics service to track custom metrics:

```python
class CustomAnalyticsService(ConversationAnalyticsService):
    async def get_custom_metrics(self):
        # Track custom application-specific metrics
        return {
            'feature_usage': await self.track_feature_usage(),
            'user_engagement': await self.calculate_engagement_metrics()
        }
```

---

## 🔄 Migration and Upgrades

### Database Migrations

The system includes automatic schema migration:

```python
# Migrations are handled automatically
db_manager = DatabaseManager()
db_manager.initialize()  # Will run migrations if needed
```

### Data Import/Export for Migration

```python
# Export all conversations for backup/migration
all_conversations = await manager.list_conversations(limit=None)
all_ids = [conv.id for conv in all_conversations]

await manager.export_conversations(
    all_ids,
    "json",
    "backup_all_conversations.json"
)
```

---

## 🎯 Integration Checklist

- [ ] Initialize ConversationManager in your main application
- [ ] Replace existing REPL widget with ConversationREPLWidget
- [ ] Update AI service initialization to use ConversationAIService
- [ ] Add conversation browser dialog to your UI
- [ ] Configure automatic conversation saving
- [ ] Set up export functionality
- [ ] Enable AI-powered summaries
- [ ] Configure conversation templates
- [ ] Set up analytics dashboard
- [ ] Add error handling and logging
- [ ] Test conversation persistence
- [ ] Test search functionality
- [ ] Test export functionality
- [ ] Verify UI integration
- [ ] Performance test with large datasets

---

## 🚀 Next Steps

1. **Implement Basic Integration**: Start with the ConversationManager and enhanced REPL
2. **Test Thoroughly**: Ensure all conversation operations work correctly
3. **Add UI Components**: Integrate the conversation browser and search functionality
4. **Enable Advanced Features**: Add templates, favorites, and analytics
5. **Optimize Performance**: Monitor and optimize for your specific usage patterns
6. **Customize**: Adapt the system to your specific requirements

---

## 📞 Support and Troubleshooting

### Common Issues

1. **Database Initialization Fails**
   - Check file permissions in settings directory
   - Ensure SQLite is available
   - Check disk space

2. **Conversation Not Saving**
   - Verify auto-save is enabled
   - Check database connection
   - Review error logs

3. **Search Not Working**
   - Verify FTS index is built
   - Check search query syntax
   - Rebuild search index if needed

4. **Export Failures**
   - Check target directory permissions
   - Verify conversation exists
   - Check available disk space

### Debugging

Enable debug logging for detailed information:

```python
import logging
logging.getLogger("ghostman.conversation_manager").setLevel(logging.DEBUG)
logging.getLogger("ghostman.conversation_service").setLevel(logging.DEBUG)
logging.getLogger("ghostman.ai_integration").setLevel(logging.DEBUG)
```

---

This comprehensive conversation management system transforms Ghostman into a powerful AI assistant with persistent memory, intelligent organization, and advanced conversation management capabilities. The modular architecture ensures easy integration while maintaining high performance and reliability.