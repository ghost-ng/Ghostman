# Slash Command Autocomplete Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "/" autocomplete popup for slash commands and skills in the REPL input.

**Architecture:** Extend the existing QCompleter pattern (used for @mention autocomplete) to handle "/" triggers. A new `_slash_completer` filters commands/skills as the user types.

**Tech Stack:** PyQt6 QCompleter, QStringListModel

---

## Design

### Trigger Behavior

- "/" at the start of input (or after whitespace) triggers the popup
- Popup lists all built-in commands + "skills"
- Filters in real-time as user types (e.g., "/sk" shows "skills")
- Selecting inserts full text (e.g., "/skills") — user presses Enter to execute
- Debug commands only appear when debug mode is enabled

### Items

- `help` — Show help message
- `clear` — Clear output display
- `history` — Show command history
- `resend` — Resend last failed message
- `exit` — Minimize to tray
- `skills` — Show available skills
- Debug-only: `quit`, `context`, `render_stats`, `test_markdown`, `test_themes`

### Styling

- Popup themed via `_apply_theme()` using `colors.background_secondary`, `colors.text_primary`, `colors.primary`

---

## Implementation Plan

### Task 1: Add slash autocomplete methods

**Files:**
- Modify: `specter/src/presentation/widgets/repl_widget.py`

**Step 1: Add `_check_slash_autocomplete` method**

After `_check_mention_autocomplete`, add a method that detects "/" at start of input and shows the slash completer.

**Step 2: Add `_show_slash_autocomplete` method**

Creates/updates `_slash_completer` QCompleter with command list, filtered by prefix.

**Step 3: Add `_on_slash_completed` method**

Handles selection — replaces text from "/" to cursor with "/completion".

**Step 4: Hook into `_on_input_text_changed`**

Add slash check before the existing @mention check.

**Step 5: Theme the popup**

In `_apply_theme()`, style the slash completer popup.

### Task 2: Verify

Run the application and test "/" autocomplete triggers, filtering, selection, and theming.
