# Ghostman Technical Architecture

## Overview
Ghostman is a PyQt6-based desktop AI assistant with a modular architecture designed for extensibility and maintainability.

## Architecture Layers

### 1. Presentation Layer (`ghostman/src/presentation/`)
- **UI Components**: Avatar widget, REPL window, system tray
- **Dialogs**: Settings, conversations, theme editor
- **Widgets**: Custom UI elements and controls

### 2. Application Layer (`ghostman/src/application/`)
- **AppCoordinator**: Central orchestrator for application lifecycle
- **Event Management**: Signal/slot connections between components
- **State Management**: Application state and context

### 3. Infrastructure Layer (`ghostman/src/infrastructure/`)
- **Conversation Management**: SQLite database with migrations
- **Storage**: Settings and data persistence
- **PKI**: Certificate-based authentication
- **AI Services**: Integration with OpenAI, Anthropic, Google AI

### 4. Domain Layer (`ghostman/src/domain/`)
- **Models**: Core business entities
- **Services**: Business logic implementation
- **Value Objects**: Immutable domain concepts

## Key Components

### Theme System
- **ColorSystem**: Type-safe color definitions
- **ThemeManager**: Runtime theme switching
- **StyleTemplates**: Reusable QSS templates
- See: [Theme System Documentation](components/theme-system.md)

### Conversation Management
- **SQLite Database**: Local conversation storage
- **Migration System**: Database schema versioning
- **Repository Pattern**: Data access abstraction
- See: [Conversation Management](components/conversation-management.md)

### Tab System
- **TabConversationManager**: Multi-conversation support
- **State Isolation**: Per-tab conversation context
- **Dynamic UI Updates**: Real-time tab synchronization
- See: [Tab System](components/tab-system.md)

## Technology Stack
- **Framework**: PyQt6
- **Language**: Python 3.12+
- **Database**: SQLite
- **AI Services**: OpenAI, Anthropic, Google AI APIs
- **Styling**: QSS (Qt Style Sheets)

## Design Patterns
- **MVC/MVP**: Separation of concerns
- **Observer**: PyQt signals/slots
- **Repository**: Data access layer
- **Singleton**: Theme and settings managers
- **Factory**: AI service creation

## Development Guidelines
- Follow PEP 8 for Python code style
- Use type hints for all public methods
- Document complex logic with docstrings
- Write unit tests for business logic
- Keep UI and business logic separated

## For More Information
- [Contributing Guidelines](../CONTRIBUTING.md)
- [API Reference](API_REFERENCE.md)
- Component-specific documentation in `components/`