# Tabbed Conversation Interface Implementation Guide

## Overview

The Ghostman REPL interface now supports tabbed conversations, allowing users to manage multiple AI conversations simultaneously. Each tab represents a separate conversation context with full isolation and proper state management.

## Architecture

### Key Components

1. **TabConversationManager** (`tab_conversation_manager.py`)
   - Central coordinator for all tab operations
   - Manages tab-to-conversation mapping
   - Handles context switching between conversations
   - Provides event signals for UI integration

2. **ConversationTab** (Dataclass within TabConversationManager)
   - Represents individual tab state
   - Manages QPushButton styling and behavior
   - Tracks conversation association and metadata

3. **Enhanced REPLWidget**
   - Integrated tab management methods
   - Context switching logic
   - Plus button dropdown integration
   - Proper cleanup and shutdown handling

## Usage Instructions

### Creating New Tabs

**Option 1: Plus Button Dropdown**
1. Click the plus (➕) button in the title bar or toolbar
2. Select "New Tab" from the dropdown menu
3. A new tab will be created with a fresh conversation

**Option 2: Programmatic Creation**
```python
# In REPLWidget instance
self._create_new_tab()
```

### Tab Operations

**Switching Between Tabs**
- Click any tab button to switch to that conversation
- Context automatically switches to the selected conversation
- Previous conversation state is preserved

**Closing Tabs**
1. Right-click on any tab button
2. Select "Close Tab" from context menu
3. Cannot close the last remaining tab
4. Active tab switches to adjacent tab if closed

**Additional Context Menu Options**
- "Close Other Tabs": Closes all tabs except the selected one
- "Rename Tab": Placeholder for future implementation

### State Management

**Conversation Isolation**
- Each tab maintains separate conversation context
- Messages, history, and AI state are fully isolated
- Switching tabs preserves all conversation state

**Title Synchronization**
- Tab titles automatically sync with conversation titles
- Long titles are truncated with ellipsis for display
- Full title shown in tooltip

**Dirty State Tracking**
- Tabs show visual indicator (•) for unsaved changes
- Prevents accidental data loss

## Technical Implementation

### Class Relationships

```
REPLWidget
├── TabConversationManager
│   ├── Dict[str, ConversationTab]
│   └── ConversationManager integration
└── Enhanced UI Methods
    ├── _create_new_tab()
    ├── _on_tab_switched()
    ├── _on_conversation_context_switched()
    └── _sync_tab_with_conversation()
```

### Signal Flow

```
User Action → Tab Manager → REPL Widget → Conversation Manager → AI Service
     ↓              ↓            ↓               ↓              ↓
Tab Button → context_switched → _on_context_switched → load_conversation → update_context
```

### Memory Management

**Efficient Design**
- Single REPLWidget instance shared across tabs
- Conversation data stored in database, not memory
- Only active conversation context loaded in AI service
- Proper cleanup on tab closure and shutdown

## Integration Points

### Existing Systems

**ConversationManager Integration**
- Uses existing conversation creation/retrieval methods
- Maintains conversation database consistency  
- Integrates with AI service context switching

**Theme System Compatibility**
- Tab buttons respect current theme colors
- Active/inactive states use theme-appropriate styling
- Hover effects follow theme guidelines

**Resize System Compatibility**
- Tab bar positioning works with existing resize grips
- No interference with window drag/resize operations
- Proper layout management during window operations

### Event Handling

**Signals Emitted**
- `tab_created(tab_id, title)` - New tab created
- `tab_switched(old_tab_id, new_tab_id)` - Tab switched
- `tab_closed(tab_id)` - Tab closed
- `context_switched(conversation_id)` - Conversation context changed

**Slots Connected**
- Tab button clicks → `switch_to_tab()`
- Context menu actions → various tab operations
- Conversation updates → tab title sync

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**: Only load conversation when tab becomes active
2. **Memory Efficient**: Single widget instance, database-backed state
3. **Event Batching**: Minimize unnecessary UI updates during switching
4. **Resource Cleanup**: Proper disposal of tab resources on closure

### Scalability

- Handles unlimited number of tabs (within memory constraints)
- Database-backed conversation storage for persistence
- Efficient context switching without UI recreation
- Minimal performance impact on existing functionality

## Error Handling

### Graceful Degradation

**Tab System Unavailable**
- Falls back to placeholder tabs for UI consistency
- Logs warning but maintains core functionality
- No impact on existing conversation features

**Conversation Manager Unavailable**
- Tab creation disabled gracefully
- Existing tabs remain functional
- Clear error messages to user

**Individual Tab Failures**
- Failed tab creation doesn't affect existing tabs
- Context switch failures are logged and recovered
- UI remains responsive during error conditions

## Future Enhancements

### Potential Extensions

1. **Tab Reordering**: Drag-and-drop tab repositioning
2. **Tab Groups**: Organize related conversations
3. **Tab Persistence**: Restore open tabs on application restart
4. **Tab Thumbnails**: Preview conversation content on hover
5. **Keyboard Shortcuts**: Ctrl+T for new tab, Ctrl+W for close tab
6. **Tab Duplication**: Copy conversation to new tab
7. **Advanced Context Menu**: More tab management options

### Implementation Notes

The current implementation provides a solid foundation for these future enhancements while maintaining clean, maintainable code that integrates seamlessly with the existing Ghostman architecture.

## Troubleshooting

### Common Issues

**"Tab system unavailable" Warning**
- Check TabConversationManager import in repl_widget.py
- Verify conversation_manager is properly initialized
- Check for import errors in tab_conversation_manager.py

**Tabs Not Responding**
- Verify signal connections in _init_tab_bar()
- Check tab_manager initialization
- Review error logs for context switching failures

**Memory Leaks**
- Ensure proper cleanup in shutdown()
- Verify tab button deleteLater() calls
- Check conversation reference clearing

### Debug Commands

```python
# Check tab manager state
if hasattr(repl_widget, 'tab_manager'):
    print(f"Active tabs: {len(repl_widget.tab_manager.tabs)}")
    print(f"Active tab: {repl_widget.tab_manager.active_tab_id}")
    
# Check conversation context
if repl_widget.current_conversation:
    print(f"Current conversation: {repl_widget.current_conversation.id}")
```

This implementation provides a robust, user-friendly tabbed interface that enhances the Ghostman experience while maintaining the architectural principles and performance characteristics of the existing system.