# Ghostman TODO

## 🚀 Current Sprint
- [x] Review and merge PR #2 (grip-based resize system)
- [x] Clean up test files from resize development
- [x] Test full application workflow with new resize system
- [x] Set REPL preamble to empty when opening app for first time
- [x] Test API connection on app start, show error in REPL if not working
- [ ] Fix conversation export options and test each format
- [ ] Add search feature in saved conversations dialog
- [ ] Add search feature in main REPL widget

## ✅ Recently Completed
- [x] Fix conversation status management (bulletproof active/pinned status)
- [x] Add comprehensive cleanup system for app shutdown
- [x] Save unsaved messages to active conversation on exit
- [x] Implement SimpleStatusService for direct SQL status updates
- [x] Add database indexing for performance
- [x] Fix user-friendly confirmation dialogs
- [x] Implement grip-based resize system for frameless windows
- [x] Add move toggle button (✥) to REPL title bar
- [x] Fix click-blocking issues with resize overlays
- [x] Simplify to 4 edge grips (removed corner grips)
- [x] Create visual conversation UI with markdown support
- [x] Implement conversation persistence with SQLAlchemy
- [x] Add AI context management and memory system

## 🎯 High Priority
### Core Functionality
- [ ] Fix any remaining UI responsiveness issues
- [ ] Improve error handling for API failures
- [ ] Add retry logic for network requests
- [ ] Implement conversation export/import

### User Experience
- [ ] Add keyboard shortcuts for common actions
- [ ] Implement conversation search functionality
- [ ] Add conversation tagging/categorization
- [ ] Create onboarding/first-run experience

### Settings & Configuration
- [ ] Create settings UI dialog
- [ ] Add color theming options for user customization
- [ ] Add font size increase/decrease setting option
- [ ] Split system prompt: user-modifiable + hard-coded base prompt
- [ ] Implement hotkey configuration
- [ ] Add backup/restore settings functionality

## 📋 Medium Priority
### Performance
- [ ] Optimize startup time (target < 3 seconds)
- [ ] Reduce memory usage for long conversations
- [ ] Implement conversation archiving
- [ ] Add conversation pruning options

### Integration
- [ ] Add support for multiple AI providers
- [ ] Implement plugin system for extensions
- [ ] Add system clipboard integration
- [ ] Create API for third-party integrations

### Documentation
- [ ] Write user guide for new features
- [ ] Update README with current functionality
- [ ] Create video tutorials
- [ ] Document API configuration options

## 💡 Nice to Have
### Advanced Features
- [ ] Voice input/output support
- [ ] Image generation integration
- [ ] Code execution sandbox
- [ ] Multi-language support

### Analytics
- [ ] Usage statistics dashboard
- [ ] Token usage tracking
- [ ] Performance metrics
- [ ] Error reporting system

### Community
- [ ] Create Discord/community server
- [ ] Set up feature request system
- [ ] Implement telemetry (opt-in)
- [ ] Create contributor guidelines

## 🐛 Known Issues
- [ ] Window positioning on multi-monitor setups needs refinement
- [ ] Some markdown rendering edge cases
- [ ] Conversation scrolling can be jumpy with long messages
- [ ] Settings changes require restart for some options

## 📝 Notes
- Focus on stability and user experience before adding new features
- Keep the app lightweight and responsive
- Maintain backwards compatibility with settings
- Test thoroughly on Windows 10 and 11

## 🗓️ Version Roadmap
### v1.0 (Current Focus)
- Core chat functionality
- Settings management
- Conversation persistence
- Resize system

### v1.1
- Plugin system
- Advanced search
- Keyboard shortcuts
- Settings UI

### v1.2
- Multi-provider support
- Voice features
- Export/Import
- Themes

### v2.0
- Major UI redesign
- Advanced AI features
- Team collaboration
- Cloud sync

---
*Last updated: Today*
*Priority: 🚀 Current Sprint > 🎯 High > 📋 Medium > 💡 Nice to Have*