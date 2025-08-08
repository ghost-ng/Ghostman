# Ghostman AI Desktop Assistant

A sleek, privacy-focused AI desktop overlay that brings AI assistance directly to your desktop without requiring admin permissions.

![Ghostman Logo](ghostman/assets/avatar.png)

## Features

✨ **Desktop Overlay**: Float anywhere on your desktop without interrupting your workflow  
🔐 **Privacy First**: All conversations stored locally, no cloud dependency except AI API calls  
⚙️ **No Admin Required**: Runs with standard user permissions  
🎨 **Beautiful UI**: Modern, translucent interface with smooth animations  
💬 **Smart Conversations**: Context-aware AI chat with conversation memory  
📱 **System Tray Integration**: Quick access from your taskbar  
💾 **Conversation Persistence**: Your conversations are automatically saved and can be resumed  

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Keep it handy for setup

### 3. Run Ghostman
```bash
# From the project root
python ghostman/src/main.py
```

### 4. Configure AI Settings
1. Right-click the ghost avatar in your system tray or desktop
2. Select "Settings"
3. Enter your OpenAI API key
4. Optionally adjust model settings and parameters
5. Click "Test API Key" to verify it works
6. Save settings

## How to Use

### Basic Usage
1. **Avatar Mode**: The ghost avatar sits in the bottom-right corner of your screen
2. **Click to Chat**: Left-click the avatar to open the AI chat interface
3. **Type & Send**: Type your message and press Enter or click Send
4. **Minimize**: Click the "–" button to return to avatar mode

### System Tray
- **Left-click tray icon**: Show/hide main interface
- **Right-click tray icon**: Access settings, about, or quit

### Keyboard Shortcuts
- **Enter**: Send message
- **Ctrl+Enter**: New line in message
- **Escape**: Minimize to avatar mode (when interface is focused)

### Features

#### 🤖 AI Chat
- Context-aware conversations that remember your chat history
- Supports all OpenAI models (GPT-3.5, GPT-4, etc.)
- Automatic conversation length management
- Real-time typing indicators

#### 💾 Conversation Management
- Conversations are automatically saved locally
- Resume previous conversations anytime
- Export conversation history
- Clear conversations when needed

#### ⚙️ Customizable Settings
- Choose your preferred AI model
- Adjust creativity (temperature) settings
- Set response length limits
- Configure timeout preferences
- Test API key functionality

## Configuration

### AI Models
- **gpt-3.5-turbo** (Default): Fast and cost-effective
- **gpt-4**: More capable, higher quality responses
- **gpt-4-turbo-preview**: Latest GPT-4 model with larger context

### Files & Directories
```
%USERPROFILE%/.ghostman/
├── ai_config.json          # AI service configuration
├── conversations.json      # Saved conversations
├── window_positions.json   # Window positioning
└── ghostman.log           # Application logs
```

## Privacy & Security

🔒 **Local Storage**: All conversations are stored locally on your machine  
🌐 **API Calls Only**: Only your messages and AI responses are sent to OpenAI  
🚫 **No Telemetry**: No usage data is collected or transmitted  
🔐 **Secure Config**: API keys are stored locally in your user directory  

## Troubleshooting

### Common Issues

**"AI service not configured"**
- Open Settings and enter your OpenAI API key
- Test the key to ensure it's working

**"Invalid API key"**
- Verify your OpenAI API key is correct
- Check that your OpenAI account has credit/usage available

**"Network error"**
- Check your internet connection
- Verify firewall isn't blocking the application

**Avatar not visible**
- Try right-clicking in the bottom-right corner of your screen
- Check system tray for the Ghostman icon

### Logs
Check `%USERPROFILE%/.ghostman/ghostman.log` for detailed error information.

## Development

### Project Structure
```
ghostman/
├── src/
│   ├── app/                    # Application core
│   │   ├── application.py      # Main app class
│   │   └── window_manager.py   # Window state management
│   ├── domain/
│   │   └── models/             # Data models
│   ├── services/
│   │   ├── ai_service.py       # OpenAI integration
│   │   └── conversation_storage.py # Persistence
│   ├── ui/
│   │   └── components/         # UI components
│   └── main.py                 # Entry point
├── assets/
│   └── avatar.png             # App icon/avatar
└── tests/                     # Test suite
```

### Requirements
- Python 3.10+
- PyQt6
- OpenAI Python SDK
- Additional dependencies in `requirements.txt`

## Building Executable

To create a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
python scripts/build.py
```

The executable will be created in the `dist/` directory.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source. See LICENSE file for details.

## Support

- **Issues**: Report bugs or request features
- **Discussions**: Join the community discussion
- **Documentation**: Check the docs/ directory for detailed guides

---

**Made with ❤️ for productivity enthusiasts who want AI assistance without the bloat.**