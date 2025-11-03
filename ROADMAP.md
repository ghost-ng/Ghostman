# Ghostman Feature Roadmap

This roadmap outlines planned enhancements and improvements for the Ghostman AI assistant application.

---

## Priority 1: Complete Existing TODOs (Quick Wins)

### Conversation Browser Features (10 incomplete TODOs)
Location: `ghostman/src/infrastructure/conversation_management/ui/conversation_browser.py`

1. **Search Functionality** - Allow users to search through conversation history by keywords, dates, or AI provider
2. **Filtering System** - Filter by status (active/archived), date range, AI model used, or conversations with file attachments
3. **Sorting Options** - Sort by date (newest/oldest), title alphabetically, message count, or last updated
4. **Conversation Archiving** - Move old conversations to archive without deleting them
5. **Bulk Operations** - Delete multiple conversations, export in batch, archive multiple at once
6. **Statistics Dashboard** - Show conversation count, total messages, tokens used, most-used AI models, conversation length trends
7. **Cleanup Dialog** - Auto-delete conversations older than X days, bulk cleanup of empty conversations

### File Management Enhancements
8. **File Content Viewer** - Preview uploaded file contents within the app (code syntax highlighting, PDF viewer, image preview)
   - Location: `ghostman/src/presentation/widgets/repl_widget.py:3421`
9. **File Browser Pagination** - Handle large numbers of uploaded files gracefully with scrolling/pagination
   - Location: `ghostman/src/presentation/widgets/file_browser_bar.py:1870`

### Export Improvements
10. **Export Dialog with Options** - GUI for choosing export format, including/excluding metadata, selecting date ranges
    - Location: `ghostman/src/infrastructure/conversation_management/ui/repl_integration.py:423`

---

## Priority 2: User Experience Enhancements

### Conversation Management
1. **Conversation Favorites/Pinning** - Star/pin important conversations to top of list
2. **Conversation Tags/Labels** - Organize conversations with custom tags (e.g., "work", "research", "coding")
3. **Conversation Templates** - Save conversation starters with pre-configured system prompts and file context
4. **Conversation Branching** - Fork a conversation at any point to explore different paths
5. **Message Editing** - Edit previous messages and regenerate AI responses from that point

### RAG/File Context Improvements
6. **File Format Support Expansion** - Add support for more formats:
   - Office documents (DOCX, XLSX, PPTX)
   - Code files with language-specific parsing
   - Email files (MSG, EML)
   - Web archives (MHTML, HTML)
   - Audio transcription files
7. **RAG Quality Controls** - Show chunk boundaries, adjust chunk size per conversation, see what context is being retrieved
8. **Cross-Conversation RAG** - Option to search across multiple conversations' file contexts
9. **RAG Source Citations** - Show which file chunks were used to generate each AI response

### UI/UX Polish
10. **Message Actions** - Copy, regenerate, edit, delete individual messages with right-click menu
11. **Code Block Enhancements** - One-click copy button, language detection, syntax theme matching app theme
12. **Response Bookmarking** - Save specific AI responses for later reference
13. **Keyboard Navigation** - Full keyboard shortcuts for all major actions (conversation switching, file upload, settings)
14. **Dark/Light Mode Auto-Switch** - Follow system theme automatically
15. **Custom Keyboard Shortcuts** - Let users rebind all shortcuts in settings

---

## Priority 3: AI Capabilities

### Multi-Modal Features
1. **Image Upload Support** - Send images to vision-capable models (GPT-4V, Claude 3.5 Sonnet)
2. **Image Generation Integration** - DALL-E, Stable Diffusion, or Midjourney API integration
3. **Voice Input** - Speech-to-text for hands-free input (Whisper API integration)
4. **Voice Output** - Text-to-speech for AI responses (OpenAI TTS or ElevenLabs)

### Advanced AI Features
5. **Model Comparison Mode** - Send same prompt to multiple models side-by-side
6. **AI Model Profiles** - Save preset configurations (model + system prompt + temperature) for different use cases
7. **Streaming Token Count** - Show token usage in real-time during streaming
8. **Cost Tracking** - Track API costs per conversation with budget alerts
9. **Response Quality Rating** - Thumbs up/down to track which responses were helpful (local analytics)
10. **Custom System Prompts Library** - Save and manage multiple system prompts with descriptions

---

## Priority 4: Collaboration & Sharing

1. **Conversation Sharing** - Generate shareable links/files for conversations (anonymized)
2. **Team/Multi-User Mode** - Share conversation database across team (with sync)
3. **Conversation Import** - Import conversations from ChatGPT/Claude exports
4. **Prompt Library Sharing** - Community-contributed system prompts/templates
5. **Conversation Replay Mode** - Show conversation history in chronological order with timing

---

## Priority 5: Advanced Enterprise Features

### Security & Compliance
1. **Conversation Encryption** - End-to-end encryption for sensitive conversations
2. **Audit Logging** - Track all user actions, API calls, file uploads for compliance
3. **Data Residency Controls** - Configure which regions/servers to use per conversation
4. **PII Detection** - Warn when sensitive data (SSN, credit cards, emails) is being sent

### Administration
5. **Usage Analytics Dashboard** - Detailed metrics on API usage, costs, response times
6. **API Key Rotation** - Schedule automatic rotation of API keys with zero downtime
7. **Centralized Policy Management** - IT admin controls for allowed models, max tokens, file types
8. **SSO Integration** - SAML/OAuth login for enterprise deployments

---

## Priority 6: Productivity Integrations

1. **Browser Extension** - Capture web content directly into Ghostman with one click
2. **VS Code Extension** - Send code selections to Ghostman with context
3. **Clipboard Monitoring** - Auto-capture clipboard content as context (optional)
4. **Calendar Integration** - Schedule reminders based on conversation action items
5. **Task Manager Integration** - Convert AI suggestions into tasks (Todoist, Asana, Jira)
6. **Note-Taking Integration** - Export conversations to Obsidian, Notion, Roam Research
7. **Email Integration** - Draft emails based on conversation context

---

## Priority 7: Performance & Scalability

1. **Database Optimization** - Add indexes for faster conversation search
2. **Lazy Loading** - Load conversation messages on-demand for faster startup
3. **Vector Store Optimization** - Compress FAISS indices, implement incremental updates
4. **Memory Management** - Automatic cleanup of old conversation caches
5. **Background Sync** - Optional cloud backup of conversations (encrypted)

---

## Priority 8: Developer Experience

1. **Plugin System** - Allow third-party plugins for custom AI providers, themes, exporters
2. **REST API Server** - Optional local API server to control Ghostman programmatically
3. **CLI Interface** - Command-line tool for automation/scripting
4. **Webhook Support** - Trigger external actions when conversations meet certain criteria
5. **Custom Themes Editor** - GUI for creating themes without editing JSON

---

## Priority 9: Quality of Life

1. **Auto-Save Drafts** - Save unsent messages across sessions
2. **Message History Navigation** - Navigate previous sent messages with up/down arrows (like terminal)
3. **Conversation Summarization** - Auto-generate multi-paragraph summaries of long conversations
4. **Smart Notifications** - Desktop notifications when long-running responses complete
5. **Idle State Detection** - Pause timers/reduce resources when app is idle
6. **Update Checker** - Notify when new versions available (with changelog)
7. **Onboarding Tutorial** - Interactive first-run tutorial for new users

---

## Priority 10: Fun/Experimental

1. **Avatar Customization** - Multiple avatar options beyond Spector, custom images
2. **Avatar Animations** - React to AI responses (thinking, excited, confused states)
3. **Easter Eggs** - Hidden themes, secret keyboard shortcuts
4. **Conversation Games** - Built-in AI games (20 questions, word association)
5. **AI Personality Modes** - Quick-switch between persona presets (professional, casual, creative)

---

## Recommended Implementation Timeline

### Month 1-2
Complete Priority 1 TODOs (conversation browser, file viewer, export dialog)

### Month 3-4
Priority 2 (UX polish - message actions, code blocks, keyboard shortcuts)

### Month 5-6
Priority 3 (Multi-modal - image upload/generation, voice I/O)

### Month 7-8
Priority 4 (Collaboration - sharing, import/export)

### Month 9-10
Priority 6 (Integrations - browser extension, VS Code, note-taking)

### Month 11-12
Priority 7-9 (Performance, developer experience, QoL)

---

## Top 5 "Must Have" Features
Based on User Impact

1. **Message Actions & Code Block Copy** - Immediate productivity boost for developers
2. **Image Upload Support** - Unlocks entire category of use cases (Claude 3.5 Sonnet vision)
3. **Conversation Search/Filter** - Essential for power users with many conversations
4. **Voice Input/Output** - Game-changer for accessibility and hands-free use
5. **VS Code Extension** - Seamless integration into developer workflow

---

## Implementation Notes

- Start with Priority 1 to finish existing work
- Move to Priority 2-3 for biggest user experience wins
- Balance quick wins with long-term architectural improvements
- Gather user feedback after each priority level completion
- Maintain backward compatibility with existing configurations
