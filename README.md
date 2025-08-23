# Ghostman

A beautiful AI chat application featuring Spector, your friendly desktop AI assistant. Chat with multiple AI providers through an elegant floating interface with extensive customization options.

## Features

- **Advanced REPL Interface** - Enhanced multiline input with Shift+Enter, dynamic field expansion, and stop button functionality
- **Floating Chat Interface** - Moveable avatar window that opens into a full chat interface
- **Multiple AI Providers** - Support for OpenAI, Anthropic, Google, and local models
- **26 Built-in Themes** - From Matrix green to Arctic white, cyberpunk to steampunk
- **Conversation Management** - Save, load, and browse all your conversations
- **Enterprise Security** - PKI authentication for secure environments
- **Full Customization** - Fonts, opacity, window behavior, and more
- **System Tray Integration** - Always accessible, minimize to tray
- **Professional Features** - Settings profiles, advanced logging, SSL support

## Quick Start

### Installation

1. **Requirements**: Python 3.12+ and Windows 10/11, macOS, or Linux

2. **Download and Setup**:
   ```bash
   git clone https://github.com/ghost-ng/Ghostman.git
   cd Ghostman
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

3. **Get Your API Key**:
   - OpenAI: Get your key from [OpenAI Platform](https://platform.openai.com/)
   - Anthropic: Visit [Anthropic Console](https://console.anthropic.com/)
   - Google: Access [Google AI Studio](https://makersuite.google.com/)

4. **Run Ghostman**:
   ```bash
   python -m ghostman
   ```

### First Time Setup

1. **Configure Your AI Model**: Click the gear icon and enter your API key in the AI Model tab
2. **Choose a Theme**: Pick from 26 beautiful themes in the Interface tab
3. **Start Chatting**: Click on Spector (the avatar) to open the chat window

## Usage Basics

### Enhanced Chat Interface

#### Advanced Input Features
- **Multiline Support**: Press `Shift+Enter` to create new lines without sending your message
- **Dynamic Field Expansion**: Input field automatically grows as you type longer messages
- **Smart Text Wrapping**: Long lines wrap automatically and expand the field height
- **Stop Functionality**: Cancel AI queries in progress with the stop button
- **Perfect Alignment**: Input field maintains consistent visual alignment

#### Sending Messages
- **Send**: Type your message and press `Ctrl+Enter` or click the send button
- **Multiline Composition**: Use `Shift+Enter` for complex messages with multiple paragraphs
- **Cancel Queries**: Click the red "Stop" button to cancel active AI responses

### Window Controls
- **Move Around**: Drag Spector's avatar anywhere on your screen
- **Always on Top**: Keep the chat window above other applications
- **Adjust Opacity**: Make windows semi-transparent
- **Minimize to Tray**: Hide completely but keep running in the background

### Themes

Choose from 26 professionally designed themes:

**Dark Themes**: Dark Matrix, Midnight Blue, Forest Green, Sunset Orange, Royal Purple, Cyberpunk, Earth Tones, Ocean Deep, Lilac, Forest, Firefly, Mintly, Ocean, Pulse, Solarized Dark, Dracula, OpenWebUI-like, Moonlight, Fireswamp, Cyber, Steampunk

**Light Themes**: Arctic White, Sunburst, Solarized Light, OpenAI-like, OpenUI-like

Each theme is carefully designed for different moods and environments - from professional work to creative projects.

## Recent Enhancements

### REPL Interface Improvements
The latest update includes comprehensive enhancements to the chat interface:

- **Multiline Input Support**: Full Shift+Enter functionality with dynamic field expansion
- **Enhanced Markdown Rendering**: Migrated to mistune v3 for 2-3x better performance
- **Stop Button Functionality**: Cancel active AI queries with proper thread management
- **Perfect UI Alignment**: Fixed height and alignment issues for a polished experience
- **Smart Input Behavior**: Field expands with both manual line breaks and text wrapping

For detailed technical documentation, see [REPL Enhancements Guide](docs/guides/REPL_ENHANCEMENTS_GUIDE.md).

## Documentation

- **Complete User Guide**: [docs/help.md](docs/help.md) - Comprehensive help covering all features including the new REPL enhancements
- **Technical Implementation**: [docs/guides/REPL_ENHANCEMENTS_GUIDE.md](docs/guides/REPL_ENHANCEMENTS_GUIDE.md) - Detailed technical documentation for developers
- **GitHub Repository**: [https://github.com/ghost-ng/Ghostman/](https://github.com/ghost-ng/Ghostman/)

## Settings Overview

- **Interface**: Themes, opacity, window behavior
- **AI Model**: Provider selection, API keys, response settings
- **Fonts**: Customize text appearance for AI responses and user input
- **Advanced**: Logging levels, SSL settings, debugging options
- **PKI Auth**: Enterprise certificate authentication

## Keyboard Shortcuts

- `Ctrl+Enter` - Send message
- `Shift+Enter` - New line in message (multiline support)
- `Ctrl+N` - New conversation
- `Ctrl+,` - Open settings
- `Alt+H` - Toggle always on top

## Support

Having trouble? Check the [complete help guide](docs/help.md) for detailed instructions on every feature, troubleshooting tips, and advanced configuration options including the new REPL interface capabilities.

---

**Meet Spector, your AI companion for desktop productivity and creativity.**