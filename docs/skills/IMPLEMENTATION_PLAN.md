# Skills System Implementation Plan

## Overview

This document outlines the complete implementation plan for Ghostman's skills system, focusing on the top 5 priority skills plus screen capture and local task tracking.

## Priority Skills

1. **Email Drafting** - Outlook COM automation, draft-only mode
2. **Email Search** - Local Outlook search, no network queries
3. **Calendar Management** - Outlook integration, draft appointments
4. **File Search** - Windows Search API integration
5. **Screen Capture** - Camera icon in title bar, shapes, borders
6. **Task Tracker** - 100% local task management with SQLite

## Architecture Summary

See full details in:
- `TECHNICAL_ARCHITECTURE_PLAN.md` - Complete technical design
- `UI_UX_SPECIFICATION.md` - Complete UI/UX design
- `INTERFACE_DESIGN.md` - Type-safe interfaces and contracts

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Base skill framework (BaseSkill, SkillRegistry, SkillExecutor)
- Intent detection (pattern matching + AI fallback)
- Settings storage integration
- Wizard framework (base dialog, navigation, progress)

### Phase 2: Email & Calendar (Week 3-4)
- Outlook COM wrapper
- Email draft skill + 4-step wizard
- Email search skill + filter UI
- Calendar event skill + datetime pickers

### Phase 3: Screen Capture (Week 4-5)
- Full-screen capture overlay
- Shape selection (rectangle, circle, freeform)
- Border rendering
- OCR integration
- Title bar camera button

### Phase 4: Task Tracker (Week 5-6)
- SQLite schema + repository
- Slide-out task panel UI
- Quick add + full detail dialog
- Reminders + notifications

### Phase 5: File Search (Week 6-7)
- Windows Search API integration
- Search criteria UI
- Results display with actions

### Phase 6: Polish & Testing (Week 7-8)
- Theme integration for all widgets
- Error handling + validation
- Unit + integration tests
- Documentation

## Key Requirements

### From User
1. **Outlook-Only Email** - No IMAP, Gmail API, or other clients
2. **Draft-Only Mode** - ALL Outlook operations display drafts, never send/save automatically
3. **No External Queries** - Email search uses local cache only
4. **Local Task Storage** - 100% local SQLite, no cloud sync
5. **Screen Capture** - Camera icon in title bar with shape selector

### Technical Constraints
- Windows-only (win32com for Outlook)
- PyQt6 widgets
- Theme-aware (ColorSystem compliance)
- WCAG AA contrast (all 39 themes)
- AppData storage (%APPDATA%\Ghostman\)

## Next Steps

1. **Review Planning Documents** - Get user approval on architecture
2. **Create Directory Structure** - Set up skill framework folders
3. **Implement Phase 1** - Build foundation (BaseSkill, registry, etc.)
4. **Iterate** - Build one skill at a time with testing

## References

- See `TECHNICAL_ARCHITECTURE_PLAN.md` for complete code examples
- See `UI_UX_SPECIFICATION.md` for wireframes and user flows
- See `INTERFACE_DESIGN.md` for type annotations and contracts
