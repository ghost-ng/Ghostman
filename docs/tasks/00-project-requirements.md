# Project Requirements and Specifications

## Project Overview

**Project Name**: Ghostman  
**Type**: Desktop AI Overlay Assistant  
**Platform**: Cross-platform (Windows primary)  
**Technology Stack**: Python, PyQt6, tkinter (toasts only)  

## Core Vision

Ghostman is a desktop overlay application that provides instant AI assistance while users work in any application. The app floats over all other windows, offering seamless AI interactions without disrupting the user's workflow.

## Critical Constraints

### ⚠️ NO ADMIN PERMISSIONS REQUIRED
- **Must work with standard user permissions only**
- Cannot require administrator privileges for installation or execution
- Must respect Windows UAC limitations
- Should work in corporate environments with restricted permissions

### Technology Requirements
- **Primary UI**: PyQt6 only (no tkinter for main interface)
- **Toast Notifications**: tkinter or system native notifications
- **AI Integration**: OpenAI-compatible API support
- **Packaging**: Single executable file with PyInstaller

## Functional Requirements

### 1. UI States and Behavior

#### Avatar State (Minimized)
- Small avatar widget shown when main interface is closed
- Draggable to any position on screen
- Always visible on top of other applications
- **Left Click**: Opens prompt/response interface
- **Right Click**: Shows context menu with slide-in animation

#### Main Interface State
- Prompt/response interface for AI interactions
- Chat-like interface showing conversation history
- Input field for user messages
- Draggable window that stays on top
- Can be minimized back to avatar state

### 2. Menu System

#### Context Menu (Right-click on Avatar)
- **File Menu**:
  - Save conversation
  - Close application
  - Help documentation
  - About dialog
- Slide-in animation for menu appearance

#### Main Window Menu Bar
- Same File menu structure as context menu
- Standard window controls

### 3. Settings System

#### Configuration Options
- **OpenAI Compatible URL**: Configurable API endpoint
- **Model**: Selectable AI model
- **API Key**: Secure storage of authentication credentials
- **Additional Settings**:
  - Window opacity
  - Auto-hide timeout
  - Conversation token limits
  - Toast notification preferences

#### Settings Storage
- Local configuration file (JSON/TOML)
- Secure credential storage
- User-configurable paths

### 4. Conversation Management

#### Memory System
- **Token-based conversation limits** (not message count)
- Intelligent conversation trimming when approaching limits
- Persistent conversation storage across sessions
- Conversation history search and retrieval

#### Features
- Real-time streaming responses from AI
- Conversation context preservation
- Export/import conversation history
- Multiple conversation threads support

### 5. Toast Notification Framework

#### Requirements
- Cross-platform toast notifications
- Non-intrusive status updates
- Configurable display duration
- Multiple toast types (info, warning, error, success)

#### Implementation
- tkinter-based custom toasts OR
- System native notifications (preferred)
- Integration with PyQt6 main application

### 6. System Integration

#### System Tray
- Minimize to system tray/taskbar
- System tray icon with context menu
- Notification area integration
- Restore from tray functionality

#### Window Management
- Always-on-top behavior (without admin rights)
- Screen edge snapping
- Multi-monitor support
- Window position persistence

## Non-Functional Requirements

### Performance
- Fast startup time (< 3 seconds)
- Responsive UI during AI interactions
- Minimal memory footprint
- Efficient conversation storage

### Security
- Local data encryption for sensitive information
- Secure API key storage
- No admin permissions required
- Safe for corporate environments

### Usability
- Intuitive drag-and-drop functionality
- Keyboard shortcuts for common actions
- Accessible design principles
- Minimal learning curve

### Reliability
- Graceful error handling
- Network failure recovery
- Conversation data backup
- Crash recovery mechanisms
- Comprehensive logging for debugging and support
- Performance monitoring and alerting
- Automatic log rotation and cleanup

## Technical Architecture

### Application Structure
```
Presentation Layer (PyQt6)
├── Avatar Widget (minimized state)
├── Main Interface (chat window)
├── Settings Dialog
├── Toast Manager (tkinter)
└── System Tray Integration

Application Layer
├── Window State Manager
├── Conversation Manager
├── Settings Manager
└── AI Service Coordinator

Domain Layer
├── Conversation Models
├── AI Provider Abstraction
├── Memory Management
└── Configuration Models

Infrastructure Layer
├── Local Storage (JSON/SQLite)
├── HTTP Client (AI API)
├── Encryption Services
└── Comprehensive Logging System
    ├── Structured JSON Logging
    ├── Performance Monitoring
    ├── Security Event Logging
    ├── Error Tracking & Analysis
    └── Log Rotation & Management
```

### Data Flow
1. User interacts with Avatar or Main Interface
2. Window Manager handles state transitions
3. Conversation Manager processes user input
4. AI Service makes API calls
5. Response streamed back through UI
6. Memory Manager handles conversation storage
7. Toast notifications for status updates

## Deployment Requirements

### Packaging
- **Single executable file** created with PyInstaller
- **Spec file** for advanced PyInstaller configuration
- **No installer required** - direct executable launch
- **Portable application** - no registry modifications

### Distribution
- Executable size optimization (< 150MB target)
- Code signing for Windows (optional but recommended)
- Cross-platform builds (Windows, macOS, Linux)
- Automatic update mechanism (future consideration)

## Development Guidelines

### Code Organization
- Clean architecture with clear layer separation
- Domain-driven design principles
- Dependency injection for testability
- Event-driven architecture for loose coupling

### Quality Standards
- Type hints throughout codebase
- Comprehensive error handling
- Unit and integration testing
- Documentation for all public APIs

### Development Workflow
- Git-based version control
- Feature branch workflow
- Code review requirements
- Automated testing pipeline

## Success Criteria

### MVP (Minimum Viable Product)
1. ✅ Avatar widget that stays on top without admin permissions
2. ✅ Main chat interface with AI integration
3. ✅ Basic settings configuration
4. ✅ Conversation persistence
5. ✅ Toast notifications
6. ✅ System tray integration
7. ✅ Comprehensive logging system
8. ✅ Single executable packaging

### Enhanced Features (Post-MVP)
- Advanced conversation search
- Multiple AI provider support
- Plugin/extension system
- Custom themes and styling
- Advanced keyboard shortcuts
- Cloud synchronization options

## Risk Mitigation

### Technical Risks
- **UAC Limitations**: Extensive testing on restricted Windows environments
- **PyQt6 Packaging**: Comprehensive PyInstaller configuration and testing
- **Always-on-top**: Fallback strategies for different window managers
- **Performance**: Profiling and optimization during development

### User Experience Risks
- **Obtrusiveness**: Careful UX design to minimize workflow interruption
- **Learning Curve**: Intuitive design and comprehensive help documentation
- **Reliability**: Robust error handling and graceful degradation

This specification serves as the foundation for all development work on the Ghostman project, ensuring alignment with user needs while respecting technical constraints and security requirements.