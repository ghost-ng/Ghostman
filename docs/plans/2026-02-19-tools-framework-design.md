# Tools Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing skills framework with AI tool-calling support (OpenAI + Anthropic), add WebSearchSkill and DocxFormatterSkill, and a Tools settings tab for enable/disable with immediate effect.

**Architecture:** ToolCallingBridge converts enabled `ai_callable` skills into provider-specific tool definitions. AIService gets a tool-call execution loop. Two new skills register as both user-triggered and AI-callable. Settings tab provides per-tool configuration with immediate effect via SettingsManager observer.

**Tech Stack:** python-docx, pyspellchecker, BeautifulSoup4, requests (via session_manager)

---

## Components

### 1. ToolCallingBridge (`infrastructure/skills/core/tool_bridge.py`)
- Converts BaseSkill metadata + parameters → OpenAI/Anthropic tool definitions
- Parses tool_call responses from either provider format
- Formats SkillResult back into tool_result messages
- Reads settings to determine which tools are enabled
- Provider detection from model config (anthropic in base_url → Anthropic format)

### 2. WebSearchSkill (`skills_library/web_search_skill.py`)
- `ai_callable=True`, category=PRODUCTIVITY
- Parameters: query (str, required), num_results (int, optional, default 5)
- Reads provider URL template from settings
- Fetches via session_manager, parses HTML with BeautifulSoup
- Returns structured results: [{title, url, snippet}, ...]
- Intent patterns: "search for", "look up", "find online"

### 3. DocxFormatterSkill (`skills_library/docx_formatter_skill.py`)
- `ai_callable=True`, category=FILE_MANAGEMENT
- Parameters: file_path (str, required), operations (list, optional)
- Operations: standardize_fonts, fix_margins, normalize_spacing, fix_bullets, fix_spelling, fix_case, normalize_headings
- Saves as filename_formatted.docx (never overwrites original)
- Returns change summary
- Intent patterns: "reformat document", "fix formatting", "standardize doc"

### 4. Tools Settings Tab (`presentation/dialogs/settings_dialog.py`)
- New tab between Advanced and PKI Auth
- Global toggle: Enable AI Tool Calling + max iterations
- Per-tool: enabled checkbox, tool-specific config
- Web Search: provider list with add/remove, URL templates, max results
- DocxFormatter: default font/size, margins, line spacing, operation checkboxes
- Changes via SettingsManager.set() → immediate effect

### 5. AIService Integration (`infrastructure/ai/ai_service.py`)
- send_message() gets tools from ToolCallingBridge
- Tool-call loop: detect tool_calls in response, execute via SkillExecutor, append results, re-call API
- Max 5 iterations (configurable)
- Provider-agnostic: bridge handles format differences

### 6. Settings Schema (`infrastructure/storage/settings_manager.py`)
- Add `tools` key to DEFAULT_SETTINGS with web_search and docx_formatter config

### 7. Skill Registration (`infrastructure/skills/core/skill_manager.py`)
- Register WebSearchSkill and DocxFormatterSkill on initialization
- BaseSkill metadata gets `ai_callable: bool = False` field

---

## Settings Schema

```json
{
  "tools": {
    "enabled": true,
    "max_tool_iterations": 5,
    "web_search": {
      "enabled": true,
      "providers": [
        {"name": "Google", "url_template": "https://www.google.com/search?q={query}", "active": true}
      ],
      "max_results": 5
    },
    "docx_formatter": {
      "enabled": true,
      "default_font": "Calibri",
      "default_font_size": 11,
      "line_spacing": 1.15,
      "margins": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
      "default_operations": [
        "standardize_fonts", "fix_margins", "normalize_spacing",
        "fix_bullets", "fix_spelling", "fix_case", "normalize_headings"
      ]
    }
  }
}
```
