# Skill UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix AI tool awareness, enable cross-message copy-paste, add clickable URLs, and provide skills discovery.

**Architecture:** Inject dynamic tool descriptions into the AI system prompt so the model knows its capabilities. Refactor MixedContentDisplay from separate QLabel widgets to a single QTextBrowser for seamless text selection. Add URL click handling with confirmation dialog. Add "skills" intent to the classifier for instant help.

**Tech Stack:** PyQt6 (QTextBrowser, QDesktopServices, QMessageBox), Python regex, OpenAI/Anthropic tool calling

---

## Task 1: Dynamic Tool Awareness in System Prompt

**Files:**
- Modify: `specter/src/infrastructure/ai/ai_service.py:370-394`
- Modify: `specter/src/infrastructure/skills/core/tool_bridge.py` (add helper method)

The AI model receives tool definitions via the `tools` API parameter but the system prompt never mentions them. The model doesn't know it has local file access, web search, etc. This causes it to refuse file paths and suggest cloud uploads.

**Step 1: Add `build_tool_awareness_prompt()` to tool_bridge.py**

Add a new method to the `ToolBridge` class that generates a human-readable summary of available tools for the system prompt. Place it after the existing `get_tool_definitions()` method (after line ~126).

```python
def build_tool_awareness_prompt(self, registry: "SkillRegistry") -> str:
    """
    Build a system prompt section describing available tools.

    This is injected into the system prompt so the AI model knows what
    tools it has and when to use them. Without this, models often refuse
    file paths or suggest cloud uploads instead of using their tools.
    """
    from ...storage.settings_manager import settings

    if not settings.get("tools.enabled", True):
        return ""

    # Usage examples keyed by skill_id
    USAGE_EXAMPLES = {
        "web_search": "User asks 'search for penguins' or 'what is quantum computing' → call web_search with the query.",
        "docx_formatter": "User says 'format my report.docx' or provides a .docx file path → call docx_formatter with the file_path.",
        "screen_capture": "User says 'take a screenshot' or 'capture my screen' → call screen_capture.",
        "task_tracker": "User says 'add a task' or 'show my tasks' → call task_tracker.",
        "email_draft": "User says 'draft an email to John' → call email_draft.",
        "email_search": "User says 'find emails from Sarah' → call email_search.",
        "calendar_event": "User says 'schedule a meeting tomorrow at 3pm' → call calendar_event.",
        "file_search": "User says 'find files named report' → call file_search.",
    }

    lines = [
        "\n## Your Tools",
        "You have access to tools that let you perform actions on the user's local computer.",
        "When a user asks about files, searching the web, formatting documents, or capturing the screen — USE your tools.",
        "IMPORTANT: You CAN access local files on the user's computer through your tools. When a user provides a file path (like C:/Users/.../file.docx), use the appropriate tool. Do NOT say you cannot access local files.",
        "",
        "Available tools:",
    ]

    for metadata in registry.list_all():
        if not metadata.ai_callable:
            continue
        tool_enabled = settings.get(f"tools.{metadata.skill_id}.enabled", True)
        if not tool_enabled:
            continue

        example = USAGE_EXAMPLES.get(metadata.skill_id, "")
        example_text = f" Example: {example}" if example else ""
        lines.append(f"- **{metadata.skill_id}**: {metadata.description}.{example_text}")

    lines.append("")
    return "\n".join(lines)
```

**Step 2: Inject tool awareness into system prompt in ai_service.py**

In `ai_service.py`, after the tool definitions are generated (line ~387), inject the tool awareness text into the first system message. Find the section at lines 374-394 where tool definitions are attached and add the injection right after.

```python
# After line 388 (api_params['tools'] = tool_definitions), add:
                    # Inject tool awareness into system prompt
                    tool_awareness = tool_bridge.build_tool_awareness_prompt(
                        skill_manager.registry
                    )
                    if tool_awareness:
                        # Prepend to existing system message in api_messages
                        for msg in api_messages:
                            if msg.get("role") == "system":
                                msg["content"] = tool_awareness + "\n\n" + msg["content"]
                                break
                        else:
                            # No system message exists; insert one
                            api_messages.insert(0, {
                                "role": "system",
                                "content": tool_awareness
                            })
```

**Step 3: Test manually**

Run the app, type "can you analyze file:///C:/Users/miguel/Downloads/321-Ribs.docx" and verify:
- The AI recognizes the file path and calls `docx_formatter` (or asks relevant questions about it)
- The AI does NOT say "I can't access files on your computer"

**Step 4: Commit**

```bash
git add specter/src/infrastructure/ai/ai_service.py specter/src/infrastructure/skills/core/tool_bridge.py
git commit -m "feat: inject dynamic tool awareness into AI system prompt"
```

---

## Task 2: Skills Help Intent (Instant Display)

**Files:**
- Modify: `specter/src/infrastructure/skills/core/intent_classifier.py:71-108`
- Modify: `specter/src/presentation/widgets/repl_widget.py:8327-8349` (help command)
- Modify: `specter/src/presentation/widgets/repl_widget.py:8415-8467` (intent handling)

Add a "skills" intent pattern so users can type "show me my skills", "what tools do you have", etc. and get an instant formatted list.

**Step 1: Add skills_help intent to DEFAULT_PATTERNS**

In `intent_classifier.py`, add a new entry to `DEFAULT_PATTERNS` (after line ~108):

```python
"skills_help": [
    r"\b(?:show|list|display)\s+(?:my\s+)?(?:skills|tools|capabilities)\b",
    r"\b(?:what|which)\s+(?:skills|tools|capabilities)\s+(?:do\s+(?:you|i)\s+have|are\s+available)\b",
    r"\b(?:available|enabled)\s+(?:skills|tools)\b",
    r"\bhow\s+do\s+(?:skills|tools)\s+work\b",
    r"\btell\s+me\s+about\s+(?:your\s+)?(?:skills|tools|capabilities)\b",
    r"\bhelp\s+(?:with\s+)?skills\b",
    r"\bskills?\s+help\b",
    r"\bmy\s+skills\b",
],
```

Also add a confidence boost for skills_help at line ~175:

```python
confidence_boost = 0.30 if skill_id in ["screen_capture", "task_tracker", "skills_help"] else 0.0
```

**Step 2: Handle skills_help in REPL widget**

In `repl_widget.py`, in the intent detection section (around line 8429-8441), add special handling for `skills_help` before the generic skill execution:

```python
# After intent detection (line 8429), before generic execution:
if intent and intent.skill_id == "skills_help":
    self._show_skills_help()
    return
```

**Step 3: Add `_show_skills_help()` method to REPLWidget**

Add near the existing help command handler (after line ~8349):

```python
def _show_skills_help(self):
    """Display a formatted list of available skills."""
    try:
        from specter.src.infrastructure.skills.core.skill_manager import skill_manager
        from specter.src.infrastructure.storage.settings_manager import settings

        skills = skill_manager.list_skills()
        if not skills:
            self.append_output("No skills are currently registered.", "info")
            return

        lines = ["## Available Skills\n"]
        for meta in skills:
            # Check if enabled
            enabled = settings.get(f"tools.{meta.skill_id}.enabled", True)
            status = "Enabled" if enabled else "Disabled"
            icon = "✅" if enabled else "⬚"
            lines.append(f"- {icon} **{meta.name}** — {meta.description}")

        lines.append("")
        lines.append("*Ask me about any skill for more details, e.g. \"how does web search work?\"*")
        self.append_output("\n".join(lines), "system")
    except Exception as e:
        logger.error(f"Failed to show skills help: {e}")
        self.append_output("Could not load skills list.", "error")
```

**Step 4: Also add skills to the `help` command output**

In the help command handler (lines 8327-8349), add a skills section after the commands list:

```python
# After line 8349, add:
    self.append_output("", "info")
    self.append_output("Skills commands:", "info")
    self.append_output("  skills   - Show available AI skills and tools", "info")
```

Also add `"skills"` as a recognized command at line ~8327:

```python
elif command_lower in ("skills", "show skills"):
    self._show_skills_help()
    return
```

**Step 5: Test manually**

Run the app and type:
- `skills` → should show formatted skills list
- `show me my skills` → should show same list (via intent detection)
- `help` → should now list the `skills` command
- `what tools do you have` → should show skills list

**Step 6: Commit**

```bash
git add specter/src/infrastructure/skills/core/intent_classifier.py specter/src/presentation/widgets/repl_widget.py
git commit -m "feat: add skills help command and intent detection"
```

---

## Task 3: QTextBrowser Refactor (Copy-Paste + Clickable URLs)

**Files:**
- Modify: `specter/src/presentation/widgets/mixed_content_display.py` (major refactor)
- Modify: `specter/src/presentation/widgets/repl_widget.py` (minor: adapt any direct widget access)

This is the largest task. Replace the QLabel-per-message architecture with a single QTextBrowser. This enables cross-message text selection and native link handling.

### Step 1: Replace QLabel creation with QTextBrowser

In `mixed_content_display.py`, modify the `__init__` method (lines ~39-73):

**Replace** the `content_layout` + `content_widgets` list approach with a single `QTextBrowser`:

```python
# In __init__, REPLACE the QVBoxLayout + content_widgets approach:

# Single text browser for all content (enables cross-message selection)
self.text_browser = QTextBrowser()
self.text_browser.setOpenLinks(False)  # We handle links ourselves
self.text_browser.setOpenExternalLinks(False)
self.text_browser.setReadOnly(True)
self.text_browser.anchorClicked.connect(self._handle_anchor_clicked)
self.text_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
self.text_browser.customContextMenuRequested.connect(self._show_context_menu)

# Style the browser
self.text_browser.setStyleSheet("""
    QTextBrowser {
        border: none;
        background-color: transparent;
    }
""")

# Set as the scroll area's widget
self.setWidget(self.text_browser)
self.setWidgetResizable(True)

# Floating copy button for code blocks
self._copy_button = QPushButton("Copy")
self._copy_button.setParent(self.text_browser)
self._copy_button.setVisible(False)
self._copy_button.setFixedSize(60, 28)
self._copy_button.clicked.connect(self._copy_hovered_code_block)
self._copy_button.setStyleSheet("""
    QPushButton {
        background-color: rgba(100, 100, 100, 0.8);
        color: white;
        border: 1px solid rgba(150, 150, 150, 0.5);
        border-radius: 4px;
        font-size: 11px;
        padding: 2px 8px;
    }
    QPushButton:hover {
        background-color: rgba(130, 130, 130, 0.9);
    }
""")

# Track hovered code block for copy
self._hovered_code_block = None
self.text_browser.setMouseTracking(True)
self.text_browser.mouseMoveEvent = self._on_browser_mouse_move

# Content history for theme re-rendering
self.content_history: List[tuple] = []
```

### Step 2: Rewrite `_add_html_content_internal()`

Replace the current method that creates QLabels with one that appends HTML to the QTextBrowser:

```python
def _add_html_content_internal(self, html_text: str, message_style: str = "normal"):
    """Append HTML content to the text browser."""
    color = self._get_message_style_color(message_style)

    # Auto-linkify URLs in the content
    html_text = self._linkify_urls(html_text)

    # Extract code blocks and replace with styled <pre> tags
    processed_html, code_blocks = self._extract_code_blocks(html_text)

    # Re-insert code blocks as styled <pre> elements
    for code, language in code_blocks:
        bg = self.theme_colors.get("background_tertiary", "#1a1a2e")
        border = self.theme_colors.get("border", "#333")
        code_html = (
            f'<pre style="background-color:{bg}; border:1px solid {border}; '
            f'padding:12px; margin:8px 0; border-radius:6px; '
            f'font-family:Consolas,Monaco,monospace; font-size:13px; '
            f'color:{color}; white-space:pre-wrap; word-wrap:break-word;">'
            f'{code}</pre>'
        )
        processed_html = processed_html.replace(
            "[CODE_BLOCK_PLACEHOLDER]", code_html, 1
        )

    # Wrap in a styled div for the message
    wrapped = (
        f'<div style="color:{color}; margin:4px 0; padding:2px 0;">'
        f'{processed_html}</div>'
    )

    # Append to browser
    cursor = self.text_browser.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    self.text_browser.setTextCursor(cursor)
    self.text_browser.insertHtml(wrapped)

    # Auto-scroll to bottom
    self.scroll_to_bottom()
```

### Step 3: Add URL linkification method

```python
import re

_URL_PATTERN = re.compile(
    r'(?<!href=["\'])(?<!src=["\'])'  # Not already in an href/src attribute
    r'(https?://[^\s<>"\')\]]+)',
    re.IGNORECASE,
)

def _linkify_urls(self, html: str) -> str:
    """Convert plain-text URLs in HTML to clickable <a> links."""
    # Don't linkify URLs already inside <a> tags
    # Simple approach: split on existing <a> tags, only linkify outside them
    parts = re.split(r'(<a\b[^>]*>.*?</a>)', html, flags=re.DOTALL | re.IGNORECASE)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside an <a> tag, leave as-is
            result.append(part)
        else:
            # Outside <a> tags, linkify URLs
            accent = self.theme_colors.get("accent", "#00d4ff")
            result.append(self._URL_PATTERN.sub(
                rf'<a href="\1" style="color:{accent}; text-decoration:underline;">\1</a>',
                part,
            ))
    return "".join(result)
```

### Step 4: Add anchor click handler with confirmation dialog

```python
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QMessageBox

def _handle_anchor_clicked(self, url: QUrl):
    """Handle link clicks with a confirmation dialog."""
    url_string = url.toString()
    if not url_string:
        return

    reply = QMessageBox.question(
        self,
        "Open Link",
        f"Do you want to visit:\n\n{url_string}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        QDesktopServices.openUrl(url)
```

### Step 5: Add code block hover detection and copy

```python
def _on_browser_mouse_move(self, event):
    """Detect when mouse hovers over a <pre> code block."""
    # Call the original mouseMoveEvent
    QTextBrowser.mouseMoveEvent(self.text_browser, event)

    cursor = self.text_browser.cursorForPosition(event.pos())
    block = cursor.block()

    # Check if current block is inside a <pre> element
    fragment = cursor.charFormat()
    # QTextBrowser formats <pre> blocks with a specific font family
    font = fragment.fontFamily()
    is_code = font and any(
        mono in font.lower()
        for mono in ("consolas", "monaco", "monospace", "courier")
    )

    if is_code:
        # Position copy button at top-right of the code block
        block_rect = self.text_browser.cursorRect(cursor)
        btn_x = self.text_browser.viewport().width() - self._copy_button.width() - 10
        btn_y = max(block_rect.top() - 5, 0)
        self._copy_button.move(btn_x, btn_y)
        self._copy_button.setVisible(True)
        # Store the code block text
        self._hovered_code_block = block.text()
    else:
        self._copy_button.setVisible(False)
        self._hovered_code_block = None

def _copy_hovered_code_block(self):
    """Copy the hovered code block to clipboard."""
    if self._hovered_code_block:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._hovered_code_block)
        # Visual feedback
        self._copy_button.setText("Copied!")
        QTimer.singleShot(1500, lambda: self._copy_button.setText("Copy"))
```

### Step 6: Update `clear()` method

```python
def clear(self):
    """Clear all content from the browser."""
    self.text_browser.clear()
    self.content_history.clear()
    self._copy_button.setVisible(False)
    self._hovered_code_block = None
```

### Step 7: Update `scroll_to_bottom()`

```python
def scroll_to_bottom(self):
    """Scroll the text browser to the bottom."""
    scrollbar = self.text_browser.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
```

### Step 8: Update theme application

```python
def set_theme_colors(self, colors: Dict[str, str]):
    """Update theme colors and re-render all content."""
    self.theme_colors = colors
    bg = colors.get("background_secondary", "#1a1a2e")
    text = colors.get("text_primary", "#ffffff")
    accent = colors.get("accent", "#00d4ff")

    self.text_browser.setStyleSheet(f"""
        QTextBrowser {{
            background-color: {bg};
            color: {text};
            border: none;
            selection-background-color: {accent};
            selection-color: {bg};
            padding: 8px;
        }}
    """)

    # Re-render all content with new colors
    self.text_browser.clear()
    for content, style, _ in self.content_history:
        self._add_html_content_internal(content, style)
```

### Step 9: Update `manage_content_size()`

```python
def manage_content_size(self, max_widgets: int = 500):
    """Trim oldest content if history exceeds limit."""
    if len(self.content_history) > max_widgets:
        # Keep only the newest entries
        self.content_history = self.content_history[-(max_widgets - 100):]
        # Re-render
        self.text_browser.clear()
        for content, style, _ in self.content_history:
            self._add_html_content_internal(content, style)
```

### Step 10: Add context menu with "Copy All"

```python
def _show_context_menu(self, pos):
    """Show custom context menu with Copy All option."""
    menu = self.text_browser.createStandardContextMenu(pos)

    # Add "Copy All" action
    menu.addSeparator()
    copy_all_action = menu.addAction("Copy All Messages")
    copy_all_action.triggered.connect(self._copy_all_text)

    menu.exec(self.text_browser.mapToGlobal(pos))

def _copy_all_text(self):
    """Copy all text content to clipboard."""
    from PyQt6.QtWidgets import QApplication
    text = self.text_browser.toPlainText()
    QApplication.clipboard().setText(text)
```

### Step 11: Test manually

Run the app and verify:
- Text selection works across user prompts and AI responses (drag-select)
- Ctrl+A selects all text, Ctrl+C copies
- Code blocks are styled with monospace font and background
- Hovering over code blocks shows "Copy" button
- URLs in AI responses are clickable with underline styling
- Clicking a URL shows "Do you want to visit \<url\>?" dialog
- Yes opens browser, No does nothing
- Right-click shows standard menu + "Copy All Messages"
- Theme switching re-renders all content correctly
- Auto-scroll to bottom works after each message

### Step 12: Commit

```bash
git add specter/src/presentation/widgets/mixed_content_display.py
git commit -m "feat: refactor MixedContentDisplay to single QTextBrowser for cross-message selection"
```

---

## Execution Order

1. **Task 1** (system prompt) — independent, highest impact, quickest fix
2. **Task 2** (skills help) — independent, small
3. **Task 3** (QTextBrowser) — largest task, depends on nothing but takes time

Tasks 1 and 2 can be done in parallel. Task 3 should be done last as it's the biggest refactor.
