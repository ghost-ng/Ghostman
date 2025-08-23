# Ghostman Complete User Guide

Welcome to Ghostman, your intelligent desktop AI companion. This comprehensive guide covers everything you need to know about using Ghostman effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Chat Interface](#chat-interface)
3. [Avatar and Window Management](#avatar-and-window-management)
4. [Conversation Management](#conversation-management)
5. [Themes and Customization](#themes-and-customization)
6. [Settings Guide](#settings-guide)
7. [AI Models and Providers](#ai-models-and-providers)
8. [Security Features](#security-features)
9. [Troubleshooting](#troubleshooting)
10. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### First Launch

When you first run Ghostman, you'll see:
- **Spector's Avatar**: A floating character on your screen
- **System Tray Icon**: Ghostman icon in your system tray (bottom-right on Windows)

### Essential First Steps

1. **Set Up Your AI Provider**:
   - Right-click Spector or use the system tray menu
   - Select "Settings"
   - Go to the "AI Model" tab
   - Choose your provider (OpenAI, Anthropic, Google, or Local)
   - Enter your API key

2. **Choose Your Theme**:
   - In Settings, go to the "Interface" tab
   - Browse through 26 available themes
   - Preview and select your favorite

3. **Start Chatting**:
   - Click on Spector's avatar to open the chat window
   - Type your first message and press Ctrl+Enter

---

## Chat Interface

### Opening the Chat Window

There are several ways to open the chat interface:
- **Click Spector's Avatar**: Single-click anywhere on the floating avatar
- **System Tray**: Right-click the system tray icon and select "Open Chat"
- **Keyboard**: If the avatar is focused, press Enter

### Sending Messages

#### Basic Message Input
- **Type Your Message**: Click in the input area and type your message
- **Send**: Press `Ctrl+Enter` or click the send button
- **Clear Input**: Clear the input field without sending

#### Advanced Multiline Support
The input field now supports sophisticated multiline message composition:

- **Multiline Messages**: Press `Shift+Enter` to create new lines without sending
- **Dynamic Expansion**: The input field automatically grows as you type longer messages or add line breaks
- **Text Wrapping**: Long lines automatically wrap and expand the input field height
- **Smart Height**: Field expands up to 5 lines, then becomes scrollable for very long messages
- **Perfect Alignment**: Input field maintains proper visual alignment with buttons and labels

#### Input Field Features
- **Automatic Height**: Field starts at single-line height and expands based on content
- **Visual Line Counting**: Accurately tracks both manual line breaks and wrapped text
- **Smooth Transitions**: Height changes are animated for a polished experience
- **Baseline Alignment**: Always maintains consistent alignment with the send button

### Message Features

#### AI Response Display
- **Real-time Streaming**: Watch AI responses appear in real-time as they're generated
- **Enhanced Markdown**: AI responses support rich formatting including:
  - Headers, emphasis (bold/italic), and code blocks
  - Tables, lists, and links
  - Strikethrough (~~text~~) and highlights (==text==)
  - Improved parsing performance with mistune v3
- **Message History**: Scroll up to see previous messages in the conversation
- **Copy Messages**: Right-click any message to copy text to clipboard

#### Query Control Features
- **Stop Button**: Cancel active AI queries in progress
  - Red "Stop" button appears during AI processing
  - Click to immediately cancel the current query
  - Clean state restoration after cancellation
  - No memory leaks or zombie processes
- **Processing Indicators**: Visual spinner and status changes during AI communication
- **Error Recovery**: Automatic retry options for failed queries

### Chat Controls

- **New Conversation**: Click the "+" button or press `Ctrl+N`
- **Conversation Browser**: Click the browse icon to see all conversations
- **Settings**: Click the gear icon to open settings
- **Clear**: Start fresh without creating a new conversation

### Enhanced User Experience

#### Input Interaction
- **Smart Enter Handling**: 
  - `Enter` alone sends the message
  - `Shift+Enter` adds a new line
  - Works intuitively whether you're typing single or multiline content
- **History Navigation**: Use up/down arrow keys to navigate previous messages (when at start/end of input)
- **Text Selection**: Full text selection and editing capabilities within the input field

#### Visual Polish
- **Consistent Styling**: All interface elements maintain visual consistency across themes
- **Responsive Design**: Interface adapts smoothly to window resizing
- **Performance Optimized**: Fast response times and smooth animations

---

## Avatar and Window Management

### Moving the Avatar

- **Drag and Drop**: Click and drag Spector anywhere on your screen
- **Stays on Top**: Avatar floats above other windows
- **Edge Snapping**: Avatar gently snaps to screen edges for convenience

### Window Behaviors

#### Always on Top
- **Enable**: Right-click avatar → "Always on Top" or press `Alt+H`
- **Purpose**: Keep chat window above all other applications
- **Toggle**: Can be turned on/off anytime

#### Opacity Control
- **Adjust Transparency**: Settings → Interface → Opacity slider
- **Range**: 20% (very transparent) to 100% (completely opaque)
- **Use Cases**: Overlay on other work, subtle presence

#### Minimize to Tray
- **Hide Avatar**: Right-click → "Hide" or close chat window
- **System Tray Access**: Right-click system tray icon to restore
- **Background Running**: Ghostman stays active even when hidden

### Window Resizing

- **Chat Window**: Drag corners or edges to resize
- **Avatar Size**: Fixed size for consistency
- **Responsive Design**: Interface adapts to different window sizes

---

## Conversation Management

### Creating Conversations

- **New Conversation**: Click "+" button or `Ctrl+N`
- **Automatic Saving**: Every conversation is automatically saved
- **Unique Sessions**: Each conversation maintains its own context

### Browsing Conversations

#### Conversation Browser
- **Access**: Click the browse icon in the chat window
- **View Options**: List view with conversation summaries
- **Search**: Find conversations by content or date
- **Status Icons**: See conversation status at a glance

#### Conversation Status Types

- **Active (🔥)**: Currently selected conversation
- **Pinned (📌)**: Important conversations marked for easy access
- **Archived (📦)**: Older conversations moved to archive

### Managing Conversations

#### Search and Filter
- **Full-Text Search**: Search across all conversation content
- **Date Filters**: Find conversations from specific time periods
- **Status Filters**: Show only active, pinned, or archived conversations

#### Export Options
- **JSON**: Technical format with all metadata
- **TXT**: Plain text for simple sharing
- **Markdown**: Formatted text with structure
- **HTML**: Web-ready format with styling

#### Conversation Actions
- **Pin/Unpin**: Mark important conversations
- **Archive**: Move old conversations to archive
- **Delete**: Permanently remove conversations
- **Rename**: Give conversations meaningful titles

---

## Themes and Customization

### Available Themes (26 Total)

#### Dark Themes (21)
1. **dark_matrix** - Matrix-inspired green on black
2. **midnight_blue** - Deep blue professional theme
3. **forest_green** - Natural green tones
4. **sunset_orange** - Warm orange and red
5. **royal_purple** - Elegant purple theme
6. **cyberpunk** - Neon green and blue
7. **earth_tones** - Brown and warm colors
8. **ocean_deep** - Deep sea blues
9. **lilac** - Soft purple with light text
10. **forest** - Rich forest greens
11. **firefly** - Warm yellow-green glow
12. **mintly** - Fresh mint colors
13. **ocean** - Ocean blue theme
14. **pulse** - Dynamic blue theme
15. **solarized_dark** - Popular dark theme
16. **dracula** - Purple vampire theme
17. **openwebui_like** - Web UI inspired
18. **moonlight** - Silver and blue night theme
19. **fireswamp** - Warm reds and oranges
20. **cyber** - Full cyberpunk neon aesthetic
21. **steampunk** - Victorian copper and brass

#### Light Themes (5)
1. **arctic_white** - Clean light theme
2. **sunburst** - Golden orange theme
3. **solarized_light** - Popular light theme
4. **openai_like** - OpenAI-inspired design
5. **openui_like** - Modern UI theme

### Theme Selection Guide

#### By Use Case
- **Programming**: dark_matrix, ocean_deep, solarized_dark
- **Professional Work**: midnight_blue, arctic_white, openai_like
- **Creative Projects**: sunset_orange, cyberpunk, royal_purple
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

### Applying Themes

1. **Open Settings**: Click gear icon or right-click avatar → Settings
2. **Interface Tab**: Click on "Interface" tab
3. **Theme Selection**: Browse available themes in the dropdown
4. **Preview**: Many themes show a preview
5. **Apply**: Select and click OK to apply immediately

---

## Settings Guide

### Interface Tab

#### Theme Settings
- **Theme Selection**: Choose from 26 built-in themes
- **Custom Themes**: Import or create custom color schemes

#### Window Behavior
- **Opacity**: Adjust window transparency (20-100%)
- **Always on Top**: Keep windows above other applications
- **Start Minimized**: Begin in system tray
- **Close to Tray**: Minimize instead of exit when closing

#### Visual Preferences
- **Animation Speed**: Control transition animations
- **Window Borders**: Toggle window decorations
- **Status Indicators**: Show/hide conversation status icons

### AI Model Tab

#### Provider Selection
- **OpenAI**: GPT-3.5, GPT-4, and newer models
- **Anthropic**: Claude models
- **Google**: Gemini and other Google AI models
- **Local Models**: Connect to local AI instances

#### API Configuration
- **API Key**: Enter your provider's API key
- **Base URL**: Custom endpoint for local or alternative services
- **Model Selection**: Choose specific model version
- **Temperature**: Control response creativity (0.0-2.0)
- **Max Tokens**: Limit response length

#### Response Settings
- **Streaming**: Enable real-time response display
- **System Prompts**: Custom instructions for AI behavior
- **Context Window**: Control conversation memory length

### Fonts Tab

#### AI Response Font
- **Font Family**: Choose font for AI messages
- **Size**: Adjust text size for readability
- **Weight**: Normal, bold, or custom weights
- **Color**: Override theme text color if needed

#### User Input Font
- **Font Family**: Set font for your messages
- **Size**: Customize input text size
- **Style**: Italic, bold, or normal styling
- **Monospace Option**: Use coding fonts for technical discussions

#### Display Options
- **Line Spacing**: Adjust space between lines
- **Letter Spacing**: Fine-tune character spacing
- **Preview**: See changes before applying

### Advanced Tab

#### Logging Settings
- **Log Level**: DEBUG, INFO, WARNING, ERROR
- **Log Location**: View current log file location
- **Max Log Size**: Automatic log rotation settings
- **Export Logs**: Save logs for troubleshooting

#### Performance Options
- **Memory Limit**: Control maximum memory usage
- **Cache Settings**: Conversation caching preferences
- **Network Timeout**: API request timeout settings
- **Retry Logic**: Automatic retry on failures

#### Development Options
- **Debug Mode**: Enable additional debugging features
- **API Logging**: Log all API requests and responses
- **Performance Metrics**: Show timing and usage stats
- **Experimental Features**: Access beta functionality

### PKI Auth Tab

#### Certificate Management
- **Import Certificate**: Load your organization's certificates
- **Certificate Status**: View current certificate validity
- **Auto-Renewal**: Automatic certificate updates
- **Backup Certificates**: Export certificates for backup

#### Security Settings
- **Require Authentication**: Enforce certificate validation
- **Certificate Pinning**: Lock to specific certificates
- **Revocation Checking**: Verify certificate validity
- **Secure Storage**: Encrypted certificate storage

---

## AI Models and Providers

### OpenAI Integration

#### Supported Models
- **GPT-4**: Latest flagship model with advanced reasoning
- **GPT-3.5-turbo**: Fast and efficient for most tasks
- **Custom Models**: Fine-tuned models if available

#### Setup Process
1. **Get API Key**: Visit [OpenAI Platform](https://platform.openai.com/)
2. **Create Account**: Sign up or log in
3. **Generate Key**: Go to API Keys section
4. **Add to Ghostman**: Settings → AI Model → Enter key

#### Best Practices
- **Monitor Usage**: Keep track of API costs
- **Choose Right Model**: GPT-3.5 for speed, GPT-4 for complexity
- **Set Token Limits**: Control response length and costs

### Anthropic (Claude) Integration

#### Claude Models
- **Claude-3**: Latest model with enhanced capabilities
- **Claude-2**: Reliable general-purpose model
- **Claude Instant**: Faster responses for simple tasks

#### Setup Process
1. **Get API Key**: Visit [Anthropic Console](https://console.anthropic.com/)
2. **Account Setup**: Create and verify account
3. **API Access**: Generate API key
4. **Configure**: Settings → AI Model → Select Anthropic

### Google AI Integration

#### Gemini Models
- **Gemini Pro**: Advanced multimodal capabilities
- **Gemini Ultra**: Most capable model
- **Gemini Nano**: Lightweight option

#### Setup Process
1. **Google AI Studio**: Visit [Google AI Studio](https://makersuite.google.com/)
2. **Project Setup**: Create new project
3. **API Key**: Generate API credentials
4. **Integration**: Settings → AI Model → Select Google

### Local Models

#### Supported Frameworks
- **Ollama**: Local LLM serving
- **OpenAI-compatible APIs**: Local servers
- **Custom Endpoints**: Any OpenAI-format API

#### Configuration
1. **Base URL**: Enter your local server URL
2. **Model Name**: Specify model identifier
3. **Authentication**: Add tokens if required
4. **Test Connection**: Verify setup works

---

## Security Features

### PKI Authentication

#### Overview
PKI (Public Key Infrastructure) authentication provides enterprise-grade security for organizational use.

#### Use Cases
- **Corporate Environments**: Secure access control
- **Compliance Requirements**: Meet security standards
- **Identity Verification**: Confirm user identity
- **Audit Trails**: Track access and usage

#### Setup Process
1. **Obtain Certificate**: Get certificate from your IT department
2. **Import Certificate**: Settings → PKI Auth → Import
3. **Configure Settings**: Set authentication requirements
4. **Test Access**: Verify certificate works correctly

#### Certificate Management
- **Validity Checking**: Automatic certificate validation
- **Renewal Alerts**: Notifications before expiration
- **Backup/Restore**: Safe certificate storage
- **Multiple Certificates**: Support for different roles

### Data Security

#### Local Storage
- **Encrypted Data**: Conversation data encrypted at rest
- **Secure Settings**: API keys stored securely
- **User Privacy**: No data transmitted to Ghostman servers

#### Network Security
- **TLS/SSL**: All API communication encrypted
- **Certificate Validation**: Verify server authenticity
- **Proxy Support**: Work through corporate firewalls
- **Offline Mode**: Function without internet when possible

---

## Troubleshooting

### Common Issues

#### Connection Problems

**Problem**: "API connection failed"
**Solutions**:
- Check internet connection
- Verify API key is correct
- Confirm API service is available
- Check firewall/proxy settings

**Problem**: "Authentication failed"
**Solutions**:
- Regenerate API key
- Check API key permissions
- Verify account has credits/access
- Try different AI provider

#### Performance Issues

**Problem**: "Slow responses"
**Solutions**:
- Check network speed
- Try different AI model
- Reduce conversation length
- Clear application cache

**Problem**: "High memory usage"
**Solutions**:
- Restart application
- Reduce conversation history
- Adjust memory limits in settings
- Close other applications

#### Interface Problems

**Problem**: "Avatar not visible"
**Solutions**:
- Check if hidden in system tray
- Verify not moved off-screen
- Reset window positions
- Restart application

**Problem**: "Theme not applying"
**Solutions**:
- Restart Ghostman
- Check theme file integrity
- Try different theme first
- Reset to default theme

**Problem**: "Input field not expanding properly"
**Solutions**:
- Try typing longer text to trigger expansion
- Check if window is too small for expansion
- Restart application to reset input state
- Verify theme compatibility

**Problem**: "Stop button not working"
**Solutions**:
- Wait a moment for thread cancellation
- Check if query is actually running
- Restart application if stop button remains visible
- Check network connection for timeout issues

### Log Files

#### Accessing Logs
- **Windows**: `%APPDATA%/Ghostman/logs/`
- **macOS**: `~/Library/Application Support/Ghostman/logs/`
- **Linux**: `~/.config/Ghostman/logs/`

#### Log Levels
- **DEBUG**: Detailed technical information
- **INFO**: General application events
- **WARNING**: Potential issues
- **ERROR**: Actual problems

#### Using Logs
1. **Reproduce Issue**: Trigger the problem
2. **Find Recent Logs**: Check latest log entries
3. **Look for Errors**: Search for ERROR or WARNING
4. **Note Timestamps**: Match with when issue occurred

### Getting Help

#### Self-Help Resources
- **This Guide**: Comprehensive documentation
- **Settings**: Built-in help tooltips
- **GitHub Issues**: Search existing problems
- **Community**: User discussions

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
   - Create new issue with details
   - Include screenshots if helpful

---

## Tips and Best Practices

### Optimal Usage

#### Conversation Management
- **Use Descriptive Titles**: Rename conversations for easy finding
- **Pin Important Chats**: Mark frequently accessed conversations
- **Regular Archives**: Move old conversations to keep interface clean
- **Export Backups**: Save important conversations externally

#### Performance Optimization
- **Choose Right Model**: Match model capability to task complexity
- **Manage Context**: Clear long conversations when context becomes irrelevant
- **Monitor Resources**: Watch memory and CPU usage
- **Regular Restarts**: Restart Ghostman periodically for optimal performance

#### Productivity Tips
- **Keyboard Shortcuts**: Learn and use shortcuts for efficiency
- **Multiple Conversations**: Use different conversations for different topics
- **Theme Switching**: Change themes based on time of day or task
- **System Tray**: Keep Ghostman accessible but unobtrusive
- **Multiline Composition**: Use `Shift+Enter` to compose complex messages with multiple paragraphs
- **Stop Queries**: Don't hesitate to stop AI queries that are taking too long

### Advanced Features

#### Custom Workflows
- **Template Messages**: Save common prompts for reuse
- **Context Management**: Use conversation titles to organize topics
- **Export Integration**: Use exported conversations in other tools
- **Multi-Provider**: Switch between AI providers for different tasks

#### Organization Tips
- **Project-Based Conversations**: One conversation per project
- **Time-Based Archives**: Archive conversations monthly
- **Topic Tags**: Use descriptive conversation names as tags
- **Search Strategies**: Use specific keywords for better search results

### Security Best Practices

#### API Key Management
- **Secure Storage**: Never share API keys
- **Regular Rotation**: Change keys periodically
- **Monitor Usage**: Track API consumption
- **Revoke Unused**: Remove old or unused keys

#### Data Privacy
- **Review Conversations**: Understand what data is sent to AI providers
- **Local Storage**: Keep sensitive data in local-only conversations
- **Export Control**: Be careful when exporting conversations
- **Corporate Policies**: Follow your organization's AI usage guidelines

---

## Keyboard Shortcuts Quick Reference

### Global Shortcuts
- `Ctrl+Enter` - Send message
- `Ctrl+N` - New conversation
- `Ctrl+,` - Open settings
- `Alt+H` - Toggle always on top
- `Escape` - Close current dialog

### Chat Window
- `Shift+Enter` - New line in message (multiline support)
- `Enter` - Send message (when not in multiline mode)
- `Ctrl+A` - Select all text in input
- `Ctrl+Z` - Undo in text input
- `Ctrl+Y` - Redo in text input
- `Up/Down Arrow` - Navigate message history (when cursor at start/end)

### Conversation Browser
- `Ctrl+F` - Search conversations
- `Enter` - Open selected conversation
- `Delete` - Delete selected conversation
- `Ctrl+E` - Export conversation

---

## Configuration Files

### Settings Location
- **Windows**: `%APPDATA%/Ghostman/configs/`
- **macOS**: `~/Library/Application Support/Ghostman/configs/`
- **Linux**: `~/.config/Ghostman/configs/`

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

*This guide covers all aspects of using Ghostman effectively. For the latest updates and additional resources, visit the [GitHub repository](https://github.com/ghost-ng/Ghostman/).*