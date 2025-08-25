# Ghostman User Guide

Welcome to Ghostman, your intelligent desktop AI companion. Meet Spector, your friendly AI assistant with beautiful themes, tabbed conversations, and professional desktop integration.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Features](#core-features)
3. [Keyboard Shortcuts](#keyboard-shortcuts)
4. [Themes (26 Total)](#themes-26-total)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

**Requirements**: Python 3.12+ and Windows 10/11, macOS, or Linux

1. **Download and Setup**:
   ```bash
   git clone https://github.com/ghost-ng/Ghostman.git
   cd Ghostman
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Get Your API Key**:
   - **OpenAI**: Get your key from [OpenAI Platform](https://platform.openai.com/)
   - **Anthropic**: Visit [Anthropic Console](https://console.anthropic.com/)
   - **Google**: Access [Google AI Studio](https://makersuite.google.com/)

3. **Run Ghostman**:
   ```bash
   python -m ghostman
   ```

### First Time Setup

1. **Configure Your AI Model**: 
   - Click the gear icon and enter your API key in the AI Model tab
   - Choose your provider (OpenAI, Anthropic, Google, or Local)
   - Select your preferred model

2. **Choose a Theme**: 
   - Pick from 26 beautiful themes in the Interface tab
   - Preview themes before applying

3. **Start Chatting**: 
   - Click on Spector (the floating avatar) to open the chat window
   - Type your first message and press Ctrl+Enter

4. **Create New Conversations**: 
   - Use the "+" button to create new tabs for separate conversations
   - Each tab maintains its own conversation context

---

## Core Features

### Floating Avatar (Spector)

**Spector** is your desktop AI companion that floats on your screen:

- **Click to Open**: Single-click Spector to open the chat interface
- **Drag and Drop**: Move Spector anywhere on your screen
- **Visual States**: 
  - Idle: Gentle floating animation
  - Thinking: Processing your input
  - Speaking: Displaying AI response
- **Always on Top**: Stays above other windows for easy access

### Tabbed Conversation System

**Professional multi-conversation management**:

- **New Tab**: Click the "+" button and select "New Tab" for fresh conversations
- **Switch Tabs**: Click any tab to switch between different conversations
- **Tab Management**: Right-click tabs for rename and close options
- **Auto-Save**: All conversations are automatically saved
- **Context Isolation**: Each tab maintains separate conversation state

### Enhanced Save Functionality

- **Title Bar Save Button**: Dedicated save button for instant access
- **Theme-Aware Icons**: Automatic dark/light icon selection
- **Quick Save**: Save conversations without menu navigation

### Chat Interface Features

- **Real-time Streaming**: Watch AI responses appear in real-time
- **Message History**: Scroll to see previous messages
- **Formatted Text**: Full markdown support with code highlighting
- **Copy Messages**: Right-click any message to copy
- **Multi-line Input**: Press Shift+Enter for new lines without sending

### Window Management

- **Always on Top**: Keep chat window above other applications (Alt+H)
- **Opacity Control**: Adjust transparency from 20% to 100%
- **Minimize to Tray**: Hide avatar while keeping Ghostman running
- **Flexible Resizing**: Drag corners or edges to resize chat window
- **System Tray Integration**: Right-click tray icon for full menu access

### Conversation Management

#### Status System
- **Active (🔥)**: Currently selected conversation
- **Pinned (⭐)**: Important conversations marked for easy access
- **Archived (📦)**: Older conversations moved to archive
- **Deleted (🗑️)**: Removed conversations

#### Organization Features
- **Full-Text Search**: Search across all conversation content
- **Date Filters**: Find conversations from specific time periods
- **Status Filters**: Show only active, pinned, or archived conversations
- **Bulk Operations**: Manage multiple conversations at once

#### Export Options
- **JSON**: Technical format with all metadata
- **TXT**: Plain text for simple sharing
- **Markdown**: Formatted text with structure
- **HTML**: Web-ready format with styling

---

## Keyboard Shortcuts

### Chat Interface
- `Ctrl+Enter` - Send message
- `Shift+Enter` - New line (without sending)
- `Ctrl+N` - New conversation
- `Ctrl+T` - New tab
- `Ctrl+S` - Save conversation
- `Ctrl+F` - Search conversations

### Window Management
- `Ctrl+,` - Open settings
- `Alt+H` - Toggle always on top
- `Escape` - Close current dialog
- **Click Spector** - Show/hide chat
- **Right-click tray** - Access menu

### Text Editing
- `Ctrl+A` - Select all text in input
- `Ctrl+Z` - Undo in text input
- `Ctrl+Y` - Redo in text input
- `Up/Down arrows` - Navigate message history

### Conversation Browser
- `Enter` - Open selected conversation
- `Delete` - Delete selected conversation
- `Ctrl+E` - Export conversation

---

## Themes (26 Total)

Choose from 26 professionally designed themes with smart icon adaptation and optimal contrast ratios.

### Dark Themes (21)

**Tech & Programming**
- **dark_matrix** - Matrix-inspired green on black
- **cyberpunk** - Neon green and blue tech aesthetic
- **cyber** - Full cyberpunk neon aesthetic
- **ocean_deep** - Deep sea blues
- **midnight_blue** - Deep blue professional theme

**Creative & Artistic**
- **sunset_orange** - Warm orange and red tones
- **royal_purple** - Elegant purple theme
- **lilac** - Soft purple with excellent contrast
- **fireswamp** - Warm reds and oranges
- **steampunk** - Victorian copper and brass

**Nature & Environment**
- **forest_green** - Natural green tones
- **forest** - Rich forest greens
- **earth_tones** - Brown and warm natural colors
- **ocean** - Ocean blue theme
- **mintly** - Fresh mint colors

**Popular & Standardized**
- **solarized_dark** - Popular developer theme
- **dracula** - Purple vampire theme
- **moonlight** - Silver and blue night theme
- **openwebui_like** - Web UI inspired design

**Special Effects**
- **firefly** - Warm yellow-green glow
- **pulse** - Dynamic blue theme

### Light Themes (5)

**Professional**
- **arctic_white** - Clean professional look
- **openai_like** - OpenAI-inspired design
- **openui_like** - Modern UI theme

**Warm & Energetic**
- **sunburst** - Golden orange theme
- **solarized_light** - Popular light developer theme

### Theme Selection Guide

#### By Use Case
- **Programming**: dark_matrix, ocean_deep, solarized_dark, cyber
- **Professional Work**: midnight_blue, arctic_white, openai_like
- **Creative Projects**: sunset_orange, cyberpunk, royal_purple, steampunk
- **Long Work Sessions**: forest_green, earth_tones, moonlight

#### By Environment
- **Bright Office**: arctic_white, openai_like, sunburst
- **Evening/Night**: midnight_blue, forest_green, moonlight
- **Dark Room**: dark_matrix, ocean_deep, cyber

#### By Personal Style
- **Minimalist**: arctic_white, openai_like, solarized_light
- **Tech Enthusiast**: dark_matrix, cyberpunk, cyber
- **Nature Lover**: forest_green, earth_tones, forest
- **Artistic**: royal_purple, sunset_orange, fireswamp

#### Applying Themes
1. **Open Settings**: Click gear icon or right-click avatar → Settings
2. **Interface Tab**: Click on "Interface" tab
3. **Theme Selection**: Browse available themes in the dropdown
4. **Apply**: Select and apply immediately with live preview

---

## Advanced Features

### AI Model Configuration

#### Supported Providers

**OpenAI**
- GPT-4: Latest flagship model with advanced reasoning
- GPT-3.5-turbo: Fast and efficient for most tasks
- Custom models if available

**Anthropic (Claude)**
- Claude-3: Latest model with enhanced capabilities
- Claude-2: Reliable general-purpose model
- Claude Instant: Faster responses for simple tasks

**Google AI**
- Gemini Pro: Advanced multimodal capabilities
- Gemini Ultra: Most capable model
- Gemini Nano: Lightweight option

**Local Models**
- Ollama: Local LLM serving
- OpenAI-compatible APIs: Local servers
- Custom endpoints: Any OpenAI-format API

#### Model Settings
- **Temperature Control**: Adjust creativity (0.0-2.0)
- **Max Tokens**: Control response length
- **Streaming**: Real-time response display
- **System Prompts**: Custom AI behavior instructions
- **Context Window**: Conversation memory length

### Customization Options

#### Interface Settings
- **Opacity**: Window transparency (20-100%)
- **Window Behavior**: Always on top, start minimized, close to tray
- **Animation Speed**: Control transition effects
- **Status Indicators**: Show/hide conversation icons

#### Font Customization
- **AI Response Font**: Choose font family, size, and style
- **User Input Font**: Customize your message appearance
- **Line Spacing**: Adjust readability
- **Monospace Option**: Perfect for technical discussions

#### Advanced Settings
- **Logging Levels**: DEBUG, INFO, WARNING, ERROR
- **Performance Options**: Memory limits, cache settings
- **Network Settings**: Timeout, retry logic
- **Development Mode**: Debug features and metrics

### Security Features

#### PKI Authentication
Enterprise-grade security for organizational use:
- **Certificate Management**: Import and manage certificates
- **Auto-Renewal**: Automatic certificate updates
- **Secure Storage**: Encrypted certificate storage
- **Audit Trails**: Track access and usage

#### Data Security
- **Local Storage**: Conversation data encrypted at rest
- **Secure API Keys**: Protected credential storage
- **No Data Transmission**: No data sent to Ghostman servers
- **TLS/SSL**: All API communication encrypted

---

## Troubleshooting

### Common Issues

#### Connection Problems

**"API connection failed"**
- Check internet connection
- Verify API key is correct and has credits
- Confirm AI service is available
- Check firewall/proxy settings
- Try different AI provider

**"Authentication failed"**
- Regenerate API key from provider
- Check API key permissions
- Verify account has credits/access
- Test with different model

#### Performance Issues

**Slow responses**
- Check network speed
- Try different AI model (GPT-3.5 vs GPT-4)
- Reduce conversation length
- Clear application cache
- Restart application

**High memory usage**
- Restart Ghostman periodically
- Reduce conversation history in settings
- Adjust memory limits in Advanced settings
- Close other resource-intensive applications

#### Interface Problems

**Avatar not visible**
- Check if minimized to system tray
- Verify avatar didn't move off-screen
- Reset window positions in settings
- Restart application

**Theme not applying**
- Restart Ghostman after theme change
- Try different theme first
- Reset to default theme
- Check theme file integrity

**Conversations not saving**
- Check write permissions to app data folder
- Restart application to reinitialize database
- Try "Reset Database" in Advanced settings
- Verify sufficient disk space

#### Model-Specific Issues

**"Temperature not supported by this model"**
- Normal for some models (GPT-o1 reasoning models)
- Use preset model profiles for automatic settings
- Claude models: Use temperature 0.0-1.0
- OpenAI models: Use temperature 0-2
- Reasoning models: Fixed temperature at 1.0

### Log Files

#### Log Locations
- **Windows**: `%APPDATA%\Ghostman\logs\`
- **macOS**: `~/Library/Application Support/Ghostman/logs/`
- **Linux**: `~/.config/Ghostman/logs\`

#### Using Logs for Troubleshooting
1. **Reproduce Issue**: Trigger the problem
2. **Find Recent Logs**: Check latest log entries
3. **Look for Errors**: Search for ERROR or WARNING
4. **Note Timestamps**: Match with when issue occurred

### Getting Help

#### Self-Help Resources
- This comprehensive user guide
- Built-in settings tooltips
- GitHub repository documentation

#### Reporting Issues
1. **Collect Information**:
   - Ghostman version
   - Operating system
   - AI provider used
   - Error messages
   - Log files

2. **Create Issue**:
   - Visit [GitHub Issues](https://github.com/ghost-ng/Ghostman/issues)
   - Search for existing reports
   - Create new issue with complete details
   - Include screenshots if helpful

### Best Practices

#### Optimal Usage
- **Use Descriptive Titles**: Rename conversations for easy finding
- **Pin Important Chats**: Mark frequently accessed conversations
- **Regular Archives**: Move old conversations to keep interface clean
- **Export Backups**: Save important conversations externally

#### Performance Optimization
- **Choose Right Model**: Match model capability to task complexity
- **Manage Context**: Clear long conversations when context becomes irrelevant
- **Monitor Resources**: Watch memory and CPU usage
- **Regular Restarts**: Restart Ghostman periodically for optimal performance

#### Security Best Practices
- **Secure API Keys**: Never share API keys
- **Regular Key Rotation**: Change keys periodically
- **Monitor Usage**: Track API consumption
- **Review Conversations**: Understand what data is sent to AI providers
- **Follow Policies**: Adhere to your organization's AI usage guidelines

---

## Configuration Files

### Settings Location
- **Windows**: `%APPDATA%\Ghostman\configs\`
- **macOS**: `~/Library/Application Support/Ghostman/configs\`
- **Linux**: `~/.config/Ghostman/configs\`

### Key Files
- `settings.json` - Main application settings
- `themes.json` - Custom theme definitions  
- `conversations.db` - Conversation database
- `certificates/` - PKI certificates directory

### Backup and Restore
1. **Backup**: Copy entire configs directory
2. **Restore**: Replace configs directory and restart
3. **Migration**: Move configs between computers
4. **Reset**: Delete configs to restore defaults

---

**Meet Spector, your AI companion for desktop productivity and creativity with professional tabbed conversation management and beautiful theming.**

*For the latest updates and technical documentation, visit the [GitHub repository](https://github.com/ghost-ng/Ghostman/).*