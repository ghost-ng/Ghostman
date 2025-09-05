# Ghostman Technical Documentation

## Recent Technical Enhancements

### Enhanced Theme System (v2.0)
- **39 Professional Themes**: Expanded theme collection with comprehensive JSON-based configuration
- **Theme Properties**:
  - `tab_text_color` and `tab_background_color` for conversation tabs
  - `default_ai_font` and `default_user_font` specifications
  - Theme mode (`light`/`dark`) for automatic icon selection
  - Complete color system with 32 color properties per theme

### Advanced Font Management System
- **FontService Architecture**: Centralized font management with caching
- **Theme-Specific Defaults**: Each theme includes optimized font specifications
- **Font Configuration**:
  - AI Response fonts (11-14pt range)
  - User Input fonts (10-13pt range)
  - Code Snippet fonts with monospace preferences
- **Reset Functionality**: One-click restoration to theme defaults
- **CSS Generation**: Semantic CSS variables for reliable font targeting

### SSL & Certificate Management
- **SSLVerificationService**: Unified SSL handling across all HTTP requests
- **Features**:
  - Custom CA chain support for enterprise environments
  - PKI certificate integration
  - Ignore SSL option for development
  - Automatic certificate validation
- **Implementation**: `ghostman/src/infrastructure/ssl/ssl_service.py`

### Debug Command System
- **Conditional Command Visibility**: Debug commands only appear when enabled
- **Settings Integration**: `advanced.enable_debug_commands` checkbox
- **Available Debug Commands**:
  - `quit` - Application termination
  - `context` - AI context status display
  - `render_stats` - Markdown rendering statistics
  - `test_markdown` - Markdown rendering tests
  - `test_themes` - Theme switching validation

### Theme Color System Enhancements
- **ColorSystem Class Updates**:
  - Added `tab_text_color` and `tab_background_color` properties
  - Enhanced `to_dict()` and `from_dict()` methods
  - Backward compatibility with legacy themes
- **Style Template Updates**:
  - Dynamic tab styling with theme colors
  - Automatic contrast validation
  - Fallback mechanisms for missing properties

## Architecture Overview

### Component Structure
```
ghostman/
├── src/
│   ├── application/
│   │   ├── font_service.py         # Font management system
│   │   └── ssl_service.py          # SSL verification service
│   ├── presentation/
│   │   ├── widgets/
│   │   │   ├── repl_widget.py      # Main REPL interface
│   │   │   └── mixed_content_display.py # Content rendering
│   │   └── dialogs/
│   │       └── settings_dialog.py   # Settings interface
│   └── ui/
│       └── themes/
│           ├── theme_manager.py     # Theme management system
│           ├── color_system.py      # Color system implementation
│           ├── style_templates.py   # Style generation
│           └── json/                # 39 theme JSON files
```

### Key Systems

#### Theme Loading Pipeline
1. JSON files loaded from `themes/json/` directory
2. ColorSystem objects created with full property sets
3. Metadata including mode and default fonts attached
4. Theme manager broadcasts changes via signals
5. Widgets update styles through connected slots

#### Font Application Flow
1. FontService reads configuration from settings
2. Theme defaults provide fallback values
3. CSS generation creates semantic styles
4. Widgets apply fonts through style sheets
5. Cache system optimizes performance

#### SSL Verification Chain
1. SSLVerificationService initialized at startup
2. Settings checked for SSL ignore flag
3. PKI certificates loaded if configured
4. Custom CA chains merged with system trust
5. All HTTP requests use unified verification

## Performance Optimizations

### Caching Strategies
- **Font Cache**: QFont objects cached per configuration
- **CSS Cache**: Generated CSS stored to avoid regeneration
- **Theme Cache**: Color dictionaries cached for rapid access
- **Markdown Cache**: Rendered HTML cached by content hash

### Debouncing Mechanisms
- **Theme Switching**: 100ms debounce prevents rapid switches
- **Font Updates**: Batch updates with 50ms delay
- **Widget Refresh**: Consolidated refresh cycles

## API Integration

### Supported Providers
- **OpenAI**: GPT-3.5, GPT-4, GPT-4 Turbo
- **Anthropic**: Claude 2, Claude 3 (Opus, Sonnet, Haiku)
- **Google**: Gemini Pro, Gemini Ultra
- **Local**: Ollama, OpenAI-compatible endpoints

### Request Handling
- Streaming responses with real-time display
- Cancellation support via threading events
- Automatic retry with exponential backoff
- Rate limiting compliance

## Development Guidelines

### Adding New Themes
1. Create JSON file in `themes/json/`
2. Include all required color properties
3. Add tab colors and default fonts
4. Set appropriate mode (`light`/`dark`)
5. Test with theme switching validation

### Extending Font System
1. Add font category to FontService
2. Update settings dialog UI
3. Create CSS generation method
4. Implement widget application
5. Add reset functionality

### Debug Command Addition
1. Add command to `_process_command()` method
2. Gate with `_is_debug_mode_enabled()`
3. Update help text in both modes
4. Implement command handler
5. Add appropriate logging

## Testing Procedures

### Theme Validation
```python
python -m ghostman
# Type: test_themes
# Validates all 39 themes for proper switching
```

### Font System Testing
1. Change fonts in Settings > Interface > Fonts
2. Click "Reset to Theme Default" buttons
3. Switch themes and verify font updates
4. Check log for font refresh messages

### SSL Certificate Testing
1. Configure custom CA in Settings > Advanced
2. Enable/disable SSL verification
3. Test with self-signed certificates
4. Verify PKI integration

## Troubleshooting

### Common Issues
- **Fonts not updating**: Clear font cache via settings
- **Theme colors incorrect**: Check JSON file validity
- **SSL errors**: Verify CA chain format (PEM)
- **Debug commands missing**: Enable in Settings > Advanced

### Log Locations
- Windows: `%APPDATA%\Ghostman\logs\`
- macOS: `~/Library/Application Support/Ghostman/logs/`
- Linux: `~/.config/Ghostman/logs/`

## Contributing

### Code Style
- Python 3.12+ type hints
- Black formatting (line length: 100)
- Comprehensive docstrings
- Error handling with logging

### Pull Request Process
1. Create feature branch from main
2. Implement with tests
3. Update documentation
4. Submit PR with description
5. Address review feedback

## License

See LICENSE file in repository root.

## Support

- GitHub Issues: [github.com/ghost-ng/Ghostman/issues](https://github.com/ghost-ng/Ghostman/issues)
- Documentation: This file and linked guides
- User Help: [ghostman/assets/help/index.html](ghostman/assets/help/index.html)