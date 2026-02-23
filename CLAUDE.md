# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Specter is a PyQt6-based desktop AI assistant featuring a floating avatar interface ("Spector"), multi-provider AI chat, tabbed conversations, RAG file context, and 39 themes. Windows AppData storage for all configuration, databases, and logs.

## Running the Application

```bash
# Development run
python -m specter

# Or via entry point
specter

# Run with debug logging
python -m specter --debug
```

## Architecture

### Layered Architecture (Clean Architecture Pattern)

**Presentation Layer** (`src/presentation/`)
- `widgets/repl_widget.py` - Main chat interface (7000+ lines, core UI logic)
- `widgets/avatar_widget.py` - Floating Spector avatar with drag/drop
- `dialogs/settings_dialog.py` - 39 themes, AI model config, PKI setup
- `ui/main_window.py` - Container window with tab management

**Application Layer** (`src/application/`)
- `app_coordinator.py` - Orchestrates startup, system tray, window lifecycle
- `font_service.py` - Theme-aware font management

**Infrastructure Layer** (`src/infrastructure/`)
- `ai/` - AI service integration, session management, streaming
- `conversation_management/` - SQLAlchemy ORM, migrations, repositories
- `rag_pipeline/` - FAISS-only RAG with embeddings and semantic search
- `pki/` - PKI certificate management for enterprise authentication
- `ssl/` - Centralized SSL verification configuration
- `storage/` - Settings manager (all settings in one JSON file)

### Key Data Flows

**1. Conversation Flow:**
```
User Input (REPL) → AIService → OpenAI/Anthropic API → Stream Handler →
→ ConversationManager → SQLite DB → Display in REPL
```

**2. File Upload Flow (RAG):**
```
File Drop/Upload → File Browser Bar → RAG Coordinator → Document Loader →
→ Text Splitter → Embedding Service → FAISS Vector Store →
→ Badge Display with Status
```

**3. Theme Application:**
```
Settings Dialog → ThemeManager → ColorSystem validation →
→ REPLWidget.apply_theme() → All child widgets recursively
```

### Critical Design Patterns

**Session Management (Centralized)**
- ALL HTTP requests MUST go through `infrastructure/ai/session_manager.py`
- SSL verification configured ONLY in `ssl/ssl_service.py` (single source of truth)
- PKI certificates applied globally via `pki/pki_service.py`
- Never create raw `requests.Session()` objects

**Settings Storage (Windows-Aware)**
- ALL settings in `%APPDATA%\Specter\configs\settings.json`
- Database: `%APPDATA%\Specter\db\conversations.db`
- RAG data: `%APPDATA%\Specter\rag\`
- PKI certs: `%APPDATA%\Specter\pki\`
- Never use home directory (`~`) for data storage on Windows

**Conversation Lifecycle**
- In-memory only until first message sent (no empty conversations in DB)
- Auto-save after each message exchange
- Per-tab file context isolation
- Repository checks `_is_empty_conversation()` before persisting

**Theme System**
- 39 themes in `ui/themes/improved_preset_themes.py`
- Each theme uses `ColorSystem` dataclass (type-safe colors)
- WCAG contrast validation required for all themes
- Buttons use `ButtonStyleManager` for unified styling
- Never hardcode colors - always use theme properties

## Common Development Commands

### Database Migrations

```bash
# Create new migration
cd specter/src/infrastructure/conversation_management
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1
```

**Important:** Migrations use `%APPDATA%\Specter\db\conversations.db`. The `migrations/env.py` has fallback logic to find the database.

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest specter/tests/test_conversation_service.py

# Run with coverage
pytest --cov=specter --cov-report=html

# Run Qt tests (requires display)
pytest -v specter/tests/test_repl_widget.py
```

### Code Quality

```bash
# No formal linter configured - manual review
# Focus on:
# - Type hints for public APIs
# - Docstrings for complex methods
# - Logger statements for async operations
```

## Critical Implementation Rules

### 1. File Browser Bar (File Context)
- All file operations isolated per conversation (tab)
- Badge colors: Green (ready), Yellow (processing), Red (failed), Gray (disabled)
- Support drag-and-drop AND upload button
- Never save file context across conversations
- Error tooltips show multi-line context (up to 3 lines)

### 2. REPL Widget State Management
- `_uploaded_files` dict tracks files per conversation
- `_pending_conversation_id` for files uploaded before conversation exists
- Migration function `_migrate_pending_files_to_conversation()`
- File browser bar MUST hide when switching conversations without files

### 3. Theme Application
- REPLWidget must call `_apply_theme()` on all child widgets
- Font preview labels in settings MUST update on theme change
- System tray menu MUST refresh on theme change
- Use `colors.background_secondary` for text areas (matches REPL)

### 4. Toolbar Button Colors
- Attach button (enabled): Use `colors.primary` NOT `status_success`
- Pin/Move buttons (enabled): Use `colors.status_warning` NOT hardcoded gold
- Never use hardcoded `rgba()` values for toggle states
- All button colors adapt to theme

### 5. Conversation Saving
- NEVER save conversations with 0 messages
- Create conversation in-memory first (`start_new_conversation`)
- Persist to DB only when `_save_current_conversation()` has messages
- Check `if not conversation:` in save method and create then

## Project-Specific Gotchas

**Windows Path Handling:**
- Always use `os.environ.get('APPDATA')` not `Path.home()` for data
- Database URLs need forward slashes: `str(path).replace(chr(92), '/')`

**Async/Qt Integration:**
- Qt slots can't be async - use `asyncio.run()` or `QTimer.singleShot()`
- File operations are async - wrap in `asyncio.new_event_loop()`

**Theme Colors:**
- Matrix theme has `#00ff66` - very bright, avoid for buttons
- Always check WCAG contrast ratio >= 4.5 for text

**Database Constraints:**
- Conversation IDs are UUIDs (strings)
- Messages have `conversation_id` foreign key
- `force_create=True` bypasses empty check - use sparingly

**PKI Certificate Paths:**
- All PKI settings now in main `settings.json` under `pki` key
- Old `pki/pki_config.json` migrated automatically
- Client cert + key in `%APPDATA%\Specter\pki\`

## File Locations Reference

```
%APPDATA%\Specter\
├── configs\
│   └── settings.json          # All settings (including PKI)
├── db\
│   └── conversations.db       # SQLite database
├── logs\
│   ├── specter.log            # Main application log (rotates daily)
│   └── crash.log              # C-level crash traces (faulthandler)
├── pki\
│   ├── client.crt
│   ├── client.pem
│   └── ca_chain.pem
├── captures\                  # Screen capture screenshots
└── rag\
    ├── rag_pipeline.log
    └── faiss_db\
        └── [vector store files]
```

## Viewing App Logs

```bash
# View recent log entries (last 10 minutes)
python -c "
from pathlib import Path; import os, time
log = Path(os.environ['APPDATA']) / 'Specter' / 'logs' / 'specter.log'
cutoff = time.time() - 600
for line in log.read_text(encoding='utf-8', errors='replace').splitlines():
    print(line)
" 2>NUL

# Tail the main log (live)
tail -f "%APPDATA%\Specter\logs\specter.log"

# Check for C-level crashes (segfaults)
cat "%APPDATA%\Specter\logs\crash.log"

# Quick PowerShell: last 10 minutes of logs
powershell -c "Get-Content \"$env:APPDATA\Specter\logs\specter.log\" -Tail 100"
```

## Recent Architectural Changes

**Settings Consolidation (October 2025):**
- Removed unused `ai` settings key from DEFAULT_SETTINGS
- Merged PKI config from separate file into main settings.json
- Database files always in `db/` folder (no more root-level duplicates)
- RAG data moved from `~/.Specter` to `%APPDATA%\Specter\rag`

**Button Color System (October 2025):**
- Replaced hardcoded `rgba(255, 215, 0, 0.8)` with theme colors
- Attach button uses `primary`, Pin/Move use `status_warning`
- All buttons now theme-aware across 39 themes

**Empty Conversation Prevention (October 2025):**
- Conversations no longer saved on creation
- In-memory until first message sent
- `_save_current_conversation()` checks and creates in DB if needed

## Performance Considerations

- REPL widget is 11,000+ lines - changes trigger full recompilation
- Theme changes re-style entire widget tree (can take 100-300ms)
- File uploads process in background (don't block UI)
- Conversation loading uses async to prevent UI freeze
- System tray toast delayed 200ms after full startup (prevents race condition)
