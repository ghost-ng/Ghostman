# Specter

A PyQt6-based desktop AI assistant featuring a floating avatar interface, multi-provider AI chat, tabbed conversations, RAG file context, 39 themes, and integrated tool calling.

## Features

- **Multi-Provider AI Chat**: Works with OpenAI, Anthropic, Google, and any OpenAI-compatible API (local models via LM Studio, Ollama, etc.)
- **Floating Avatar**: Draggable desktop avatar with animated personas — choose from multiple characters
- **Tabbed Conversations**: Organize chats in tabs with per-tab file context isolation
- **39 Themes**: Full theme system with WCAG-compliant contrast and per-theme font matching
- **RAG File Context**: Drag-and-drop files for AI-aware context via FAISS vector search
- **Document Studio**: Batch DOCX formatting with recipes (APA, MLA, Corporate Memo, etc.)
- **AI Tool Calling**: Web search, Outlook email/calendar, screen capture, file search, task tracking, DOCX formatting
- **PKI Authentication**: Enterprise certificate-based auth via Windows certificate store
- **Conversation Persistence**: SQLite-backed conversation history with Alembic migrations

## Quick Start

**Requirements**: Python 3.12+ and Windows 10/11

```bash
git clone https://github.com/ghost-ng/Ghostman.git
cd Ghostman
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m specter
```

### API Key Setup
1. Click the gear icon to open Settings
2. Go to the **AI Settings** tab
3. Select a provider preset or enter a custom base URL
4. Paste your API key
5. Click **Apply**

Supported providers:
- [OpenAI](https://platform.openai.com/) (GPT-4, GPT-4o, etc.)
- [Anthropic](https://console.anthropic.com/) (Claude)
- [Google](https://makersuite.google.com/) (Gemini)
- Any OpenAI-compatible endpoint (LM Studio, Ollama, vLLM, etc.)

## Usage

### Chat
- **Send**: `Ctrl+Enter`
- **New line**: `Shift+Enter`
- **Stop response**: Click the Stop button
- **New conversation**: `Ctrl+N`

### File Context (RAG)
- Drag and drop files onto the chat window
- Supported: `.docx`, `.pdf`, `.txt`, `.py`, `.json`, `.csv`, and more
- Files are embedded and used as context for AI responses

### Document Studio
- Upload `.docx` files to apply batch formatting recipes
- Built-in recipes: Clean & Professional, APA, MLA, Corporate Memo, Quick Cleanup, Presentation Ready
- Create custom recipes with the recipe editor

### Tools
When enabled in Settings > Tools, the AI can:
- **Web Search**: Search the web via DuckDuckGo (free) or Tavily
- **Outlook Email**: Draft, search, reply, and forward emails via COM automation
- **Outlook Calendar**: Create, search, update, and cancel calendar events
- **Screen Capture**: Take screenshots
- **File Search**: Find files on your local system
- **Task Tracker**: Manage tasks
- **DOCX Formatter**: Format Word documents programmatically

### Keyboard Shortcuts
| Shortcut | Action |
|---|---|
| `Ctrl+Enter` | Send message |
| `Shift+Enter` | New line |
| `Ctrl+N` | New conversation |
| `Ctrl+,` | Open settings |
| `Ctrl+Shift+D` | Toggle Document Studio |

## Building

### Windows Executable
```bash
pip install pyinstaller
pyinstaller specter.spec --noconfirm
```

The executable is output to `dist/specter.exe`.

### Automated Release
Push a version tag to trigger the GitHub Actions build:
```bash
git tag v0.5.0
git push origin v0.5.0
```
This builds a Windows x64 binary and creates a GitHub Release automatically.

## Architecture

```
specter/
  src/
    presentation/     # PyQt6 UI (REPL widget, settings, avatar, Document Studio)
    application/      # App coordinator, font service
    infrastructure/   # AI service, RAG pipeline, skills, PKI, storage
    domain/           # Models, avatar personas
    ui/               # Themes, color system, style templates
```

All user data stored in `%APPDATA%\Specter\` (configs, database, logs, PKI certs, RAG data).

## License

MIT
