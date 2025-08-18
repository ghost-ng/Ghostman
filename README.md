# ghost-ng

A sleek, AI-powered desktop assistant with floating widgets and conversation management.

## Features

- 🤖 **AI-Powered Chat**: Integrated OpenAI API support with streaming responses
- 👻 **Floating Avatar**: Moveable avatar widget with personality animations
- 💬 **Conversation Management**: Persistent conversation history with browser interface
- 🎨 **Rich Theming**: 23+ built-in themes including OpenAI-like, Arctic White, Cyberpunk, and more
- 🪟 **Frameless Windows**: Modern borderless UI with custom resize handles
- ⚙️ **Comprehensive Settings**: Font customization, opacity controls, and advanced configuration
- 📌 **System Tray Integration**: Minimize to tray with quick access controls
- 🔄 **Real-time Sync**: Live conversation updates and status management

## Installation

### Prerequisites

- Python 3.12+
- Windows 10/11, macOS, or Linux

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ghost-ng/ghost-ng.git
   cd ghost-ng
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API:**
   - Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
   - Run ghost-ng and enter your API key in settings

5. **Run ghost-ng:**
   ```bash
   python -m ghostman
   # or
   ghost-ng
   ```

## Usage

### Basic Operation

- **Start**: Launch via system tray or avatar mode
- **Chat**: Type in the REPL window for AI conversations
- **Settings**: Access via gear icon or system tray menu
- **Themes**: Choose from 23+ themes in Settings > Appearance

### Keyboard Shortcuts

- `Ctrl+Enter`: Send message
- `Ctrl+N`: New conversation
- `Ctrl+,`: Open settings
- `Alt+H`: Toggle always on top

### Conversation Management

- **Active Conversations**: Only one conversation active at a time
- **Status Types**: Active (🔥), Pinned (📌), Archived (📦)
- **Search**: Full-text search across all conversations
- **Export**: JSON, TXT, Markdown, HTML formats

## Configuration

### Settings Location

- Windows: `%APPDATA%/Ghostman/configs/`
- macOS: `~/Library/Application Support/Ghostman/configs/`
- Linux: `~/.config/Ghostman/configs/`
- Config file: `settings.json`
- Logs: `logs/` subdirectory

### Theme Customization

Themes can be customized in Settings > Appearance. Built-in themes include:

- **OpenAI-like**: Clean minimal design inspired by ChatGPT
- **Arctic White**: High-contrast light theme
- **Cyberpunk**: Neon-accented dark theme
- **Dracula**: Popular purple-accented theme
- **Solarized**: Classic developer themes (light/dark)

## Architecture

```
ghostman/
├── src/
│   ├── application/           # App coordination & services
│   ├── domain/               # Business logic & models  
│   ├── infrastructure/       # External services & storage
│   │   ├── ai/              # OpenAI integration
│   │   ├── conversation_management/  # Chat persistence
│   │   ├── logging/         # Logging configuration
│   │   └── storage/         # Settings management
│   ├── presentation/        # UI components
│   │   ├── dialogs/         # Settings, browsers
│   │   ├── ui/              # Main windows, resize system
│   │   └── widgets/         # Avatar, REPL, floating windows
│   └── ui/                  # Themes & styling
│       └── themes/          # Color systems & templates
├── assets/                  # Icons, animations, sprites
├── docs/                   # Documentation
├── tests/                  # Test suites
└── requirements.txt        # Dependencies
```

## Development

### Setting Up Development Environment

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   python -m pytest tests/
   ```

3. Build executable:
   ```bash
   python build.py
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Releases

Releases are automatically built and published when version tags are pushed:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This triggers automated builds for:
- Windows executable (PyInstaller)
- Python wheel package
- Source distribution

## Documentation

- [Theme System Guide](docs/guides/THEME_SYSTEM_GUIDE.md)
- [Conversation Management](docs/guides/CONVERSATION_MANAGEMENT_GUIDE.md)
- [Color Reference](docs/guides/COLOR_VARIABLE_REFERENCE.md)
- [Architecture Analysis](docs/analysis/)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/ghost-ng/ghost-ng/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/ghost-ng/ghost-ng/discussions) for questions
- **Documentation**: Check the `docs/` directory for detailed guides

---

**Made with 👻 and ❤️ by the ghost-ng team**