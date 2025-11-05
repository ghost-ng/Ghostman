# Ghostman Feature Roadmap

This roadmap outlines planned enhancements and improvements for the Ghostman AI assistant application.

---

## Priority 1: Essential User Experience Features

1. **Search Functionality** - Search conversation history by keywords, dates, or AI provider with advanced filters (title, message content, file names). Include regex support and saved search queries.

2. **Filtering System** - Multi-level filtering: status (active/archived), date range (today, this week, this month, custom), AI model used, conversations with file attachments, by tags/labels. Combine multiple filters with AND/OR logic.

3. **Sorting Options** - Comprehensive sorting: date created (newest/oldest), date last modified, title alphabetically (A-Z/Z-A), message count (high/low), total tokens used, number of files attached. Multi-column sorting support.

5. **Bulk Operations** - Multi-select conversations for batch operations: delete, export (JSON/TXT/MD), archive, tag, change model settings. Include "Select All" and filter-based selection.

7. **Auto-Cleanup Settings** - Settings dialog option to configure automatic conversation cleanup:
   - Enable/disable auto-cleanup
   - Cleanup interval (days): 30, 60, 90, 180, 365, custom
   - What to clean: empty conversations, conversations older than X days, archived conversations
   - Confirmation before cleanup
   - Exclude pinned/favorited conversations from cleanup

10. **Export Dialog with Options** - Rich export dialog with format selection (JSON, Markdown, TXT, HTML), options to include/exclude metadata (timestamps, model info, tokens), date range selection, file attachment handling (embed/link/exclude), syntax highlighting in HTML exports.

11. **Conversation Favorites/Pinning** - Star/pin system with visual indicators (star icon, pin icon). Pinned conversations always appear at top of list regardless of sort order. Quick-pin from conversation header and context menu.

12. **File Collections Manager** - Create and manage file collections for reusable context:
   - Create named collections (e.g., "Project Docs", "Python Utils", "Research Papers")
   - Add/remove files from collections with drag-drop
   - Collection browser with search and filter
   - Attach entire collection to conversation with one click
   - Collection templates for common use cases
   - Import/export collections for sharing
   - Collection size limits and warnings
   - Per-collection RAG settings (chunk size, overlap)

13. **Conversation Branching** - Fork conversations at any message to explore different paths:
   - Right-click any message → "Branch from here"
   - Creates new conversation with history up to that point
   - Visual indicator showing parent conversation
   - Option to merge insights back to parent (copy messages)
   - Branch tree visualization showing all branches from a conversation

14. **Message Actions** - Right-click context menu on any message:
   - Copy message text
   - Copy as Markdown/Plain Text
   - Regenerate response (for AI messages)
   - Edit and regenerate (for user messages)
   - Delete message (and optionally all after it)
   - Pin/bookmark message
   - Search for similar messages
   - Export single message

15. **Code Block Enhancements** - Improve code display in conversations:
   - One-click copy button (top-right of code block)
   - Automatic language detection and syntax highlighting
   - Syntax theme matches current app theme
   - Line numbers toggle
   - "Run in terminal" button for shell commands
   - "Save to file" button
   - Diff view for code changes

---

## Priority 2: AI Capabilities

16. **Image Upload Support** - Send images to vision-capable models (GPT-4V, Claude 3.5 Sonnet):
   - Drag-drop images into chat
   - Paste images from clipboard
   - Image preview with zoom
   - Multiple images per message
   - Image annotation/markup before sending
   - Image format conversion (HEIC→JPG, etc.)

17. **Model Comparison Mode** - Send same prompt to multiple models side-by-side:
   - Select 2-4 models to compare
   - Split-pane view showing responses
   - Response time comparison
   - Token usage comparison
   - Quality rating for each response
   - "Use this response" to continue conversation with preferred model

18. **Streaming Token Count** - Real-time token usage display during streaming:
   - Live counter showing tokens streamed so far
   - Estimated cost (based on model pricing)
   - Warning when approaching max_tokens limit
   - Total conversation token count
   - Per-message token breakdown

---

## Priority 3: Productivity & Quality of Life

19. **Keyboard Navigation** - Full keyboard shortcuts for all major actions:
   - Ctrl+N: New conversation
   - Ctrl+K: Search conversations
   - Ctrl+Tab: Next conversation tab
   - Ctrl+Shift+Tab: Previous conversation tab
   - Ctrl+W: Close current tab
   - Ctrl+Shift+F: Focus file upload
   - Ctrl+Enter: Send message
   - Escape: Cancel streaming response
   - All shortcuts shown in tooltips

20. **Auto-Save Drafts** - Save unsent messages across sessions:
   - Auto-save input as you type (debounced)
   - Per-conversation draft storage
   - Restore drafts on app restart
   - Draft indicator in conversation list
   - "Discard draft" option

21. **Message History Navigation** - Navigate previous sent messages with up/down arrows:
   - Press Up arrow in empty input to load previous message
   - Continue pressing Up to go further back
   - Press Down to go forward in history
   - Edit and re-send previous messages
   - Clear history option

22. **Smart Notifications** - Desktop notifications when long-running responses complete:
   - Notify only when app is minimized or in background
   - Show first 100 characters of response in notification
   - Click notification to restore and focus app
   - Sound notification toggle
   - Do Not Disturb mode

---

## Priority 4: Advanced Features (Future)

23. **Conversation Templates** - Save conversation starters with pre-configured system prompts and file collections
24. **Voice Input** - Speech-to-text for hands-free input (Whisper API integration)
25. **Voice Output** - Text-to-speech for AI responses (OpenAI TTS or ElevenLabs)
26. **AI Model Profiles** - Save preset configurations (model + system prompt + temperature) for different use cases
27. **Cost Tracking** - Track API costs per conversation with budget alerts
28. **Custom System Prompts Library** - Save and manage multiple system prompts with descriptions
29. **Conversation Import** - Import conversations from ChatGPT/Claude exports
30. **Browser Extension** - Capture web content directly into Ghostman with one click
31. **VS Code Extension** - Send code selections to Ghostman with context

---

## Recommended Implementation Order

### Phase 1: Foundation (Weeks 1-2)
1. Search Functionality (#1)
2. Filtering System (#2)
3. Sorting Options (#3)
4. Auto-Cleanup Settings (#7)

### Phase 2: Power User Features (Weeks 3-4)
5. Bulk Operations (#5)
6. Export Dialog (#10)
7. Conversation Favorites/Pinning (#11)
8. File Collections Manager (#12)

### Phase 3: Interaction Enhancements (Weeks 5-6)
9. Message Actions (#14)
10. Code Block Enhancements (#15)
11. Conversation Branching (#13)

### Phase 4: Productivity (Weeks 7-8)
12. Keyboard Navigation (#19)
13. Auto-Save Drafts (#20)
14. Message History Navigation (#21)
15. Smart Notifications (#22)

### Phase 5: AI Capabilities (Weeks 9-10)
16. Image Upload Support (#16)
17. Streaming Token Count (#18)
18. Model Comparison Mode (#17)

---

## Top 5 User Experience Tasks to Start NOW

Based on immediate impact and user value:

**1. Code Block Enhancements (#15)**
   - **Why First:** Developers use code blocks constantly, copy button saves time every single day
   - **Effort:** Medium (2-3 days)
   - **Impact:** Immediate productivity boost for every code-related conversation
   - **Location:** `ghostman/src/presentation/widgets/repl_widget.py` - enhance Pygments code rendering

**2. Search Functionality (#1)**
   - **Why Second:** Users with 10+ conversations need this desperately
   - **Effort:** Medium-High (3-4 days)
   - **Impact:** Makes app usable for power users with many conversations
   - **Location:** `ghostman/src/infrastructure/conversation_management/ui/conversation_browser.py` - add search bar and filtering logic

**3. Message Actions (#14)**
   - **Why Third:** Copy message text is requested by users frequently
   - **Effort:** Medium (2-3 days)
   - **Impact:** Better message management and workflow
   - **Location:** `ghostman/src/presentation/widgets/repl_widget.py` - add context menu to messages

**4. Auto-Save Drafts (#20)**
   - **Why Fourth:** Prevents frustration from lost work if app crashes
   - **Effort:** Low-Medium (1-2 days)
   - **Impact:** Safety net that users appreciate daily
   - **Location:** `ghostman/src/presentation/widgets/repl_widget.py` + `ghostman/src/infrastructure/storage/settings_manager.py`

**5. Keyboard Navigation (#19)** ✅ COMPLETE
   - **Status:** Implemented in `ghostman/src/presentation/widgets/repl_widget.py`
   - **Shortcuts Added:**
     - `Ctrl+K` - Open conversation browser (search conversations)
     - `Ctrl+N` - Create new tab
     - `Ctrl+X` - Close current tab
     - `Ctrl+Tab` - Switch to next tab
     - `Ctrl+Shift+Tab` - Switch to previous tab
     - `Ctrl+T` - Toggle always on top
     - `Ctrl+S` - Save/export conversation
     - `Ctrl+M` - Minimize to tray
     - `Ctrl+,` - Open settings
     - `Ctrl+F` - Search within conversation
     - `Ctrl+U` - Toggle file browser
     - `Ctrl+Enter` - Send message
     - `Escape` - Cancel streaming response / close search / close file browser
   - **Tooltips Updated:** All buttons now show keyboard shortcuts in tooltips
   - **Help Documentation:** Complete keyboard shortcuts section added to help HTML

---

## Implementation Notes

- Focus on Priority 1 features first - these are the core UX improvements users need most
- Each feature should include comprehensive error handling and user feedback
- Add tooltips and help text for all new UI elements
- Include keyboard shortcuts wherever applicable
- Test with large datasets (100+ conversations, 1000+ messages)
- Maintain backward compatibility with existing conversations database
- Add migration logic if database schema changes are needed
- Document all new features in user-facing help/tooltips
