# Ghostman

A beautiful AI chat application featuring Spector, your friendly desktop AI assistant. Chat with multiple AI providers through an elegant floating interface with extensive customization options and professional tabbed conversation management.

## Key Features

- **Advanced REPL Interface** - Enhanced multiline input with Shift+Enter, dynamic field expansion, and stop button functionality
- **Floating Chat Interface** - Moveable avatar window that opens into a full chat interface
- **Multiple AI Providers** - Support for OpenAI, Anthropic, Google, and local models
- **26 Built-in Themes** - From Matrix green to Arctic white, cyberpunk to steampunk
- **Enhanced Save Functionality** - Dedicated title bar save button for quick access
- **Conversation Management** - Save, load, and browse all conversations with organization features
- **Smart Icon System** - Automatic theme-aware icon selection for consistent visibility
- **Enterprise Security** - PKI authentication for secure environments
- **System Tray Integration** - Always accessible, minimize to tray
- **Professional Features** - Settings profiles, advanced logging, SSL support

## Quick Installation

**Requirements**: Python 3.12+ and Windows 10/11, macOS, or Linux

```bash
git clone https://github.com/ghost-ng/Ghostman.git
cd Ghostman
python -m venv venv
venv\Scripts\activate  # Windows (use source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
python -m ghostman
```

**Get Your API Key**: Visit [OpenAI Platform](https://platform.openai.com/), [Anthropic Console](https://console.anthropic.com/), or [Google AI Studio](https://makersuite.google.com/) to obtain your API key.

## Getting Started

1. **Configure AI Model**: Click the gear icon, enter your API key in the AI Model tab
2. **Choose Theme**: Pick from 26 beautiful themes in the Interface tab  
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

📖 **[Complete User Guide](USER_GUIDE.md)** - Comprehensive documentation covering all features, shortcuts, themes, troubleshooting, and best practices

### Developer Documentation

- **[Styling System Guide](docs/guides/STYLING_SYSTEM_GUIDE.md)** - Theme integration and customization
- **[Tabbed Conversation Guide](docs/guides/TABBED_CONVERSATION_GUIDE.md)** - Technical implementation details
- **Built-in Help**: [ghostman/assets/help/index.html](ghostman/assets/help/index.html)

- `Ctrl+Enter` - Send message
- `Shift+Enter` - New line in message (multiline support)
- `Ctrl+N` - New conversation
- `Ctrl+,` - Open settings
- `Alt+H` - Toggle always on top

We welcome contributions! Please see our contributing guidelines and development setup instructions in the [GitHub repository](https://github.com/ghost-ng/Ghostman/).

Having trouble? Check the [complete help guide](docs/help.md) for detailed instructions on every feature, troubleshooting tips, and advanced configuration options including the new REPL interface capabilities.

---

**Meet Spector, your AI companion for desktop productivity and creativity with professional tabbed conversation management.**