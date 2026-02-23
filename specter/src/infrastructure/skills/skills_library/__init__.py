"""
Skills Library - Built-in skills for Specter.

This package contains all pre-built skills including:
- Email management (draft, search)
- Calendar management
- File search
- Screen capture
- Task tracking
- Web search

Each skill implements the BaseSkill interface and can be registered with the SkillManager.
"""

# Email skills
from .email_draft_skill import EmailDraftSkill
from .email_search_skill import EmailSearchSkill

# Calendar skill
from .calendar_event_skill import CalendarEventSkill

# File operations
from .file_search_skill import FileSearchSkill

# Screen capture
from .screen_capture_skill import ScreenCaptureSkill

# Task tracking
from .task_tracker_skill import TaskTrackerSkill

# Web search
from .web_search_skill import WebSearchSkill

# Document formatting
from .docx_formatter_skill import DocxFormatterSkill

# Calendar search
from .calendar_search_skill import CalendarSearchSkill

__all__ = [
    "EmailDraftSkill",
    "EmailSearchSkill",
    "CalendarEventSkill",
    "CalendarSearchSkill",
    "FileSearchSkill",
    "ScreenCaptureSkill",
    "TaskTrackerSkill",
    "WebSearchSkill",
    "DocxFormatterSkill",
]
