"""
Skills Library - Built-in skills for Specter.

Each skill implements the BaseSkill interface and can be registered with the SkillManager.
"""

# Outlook skills (unified)
from .outlook_email_skill import OutlookEmailSkill
from .outlook_calendar_skill import OutlookCalendarSkill

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

__all__ = [
    "OutlookEmailSkill",
    "OutlookCalendarSkill",
    "FileSearchSkill",
    "ScreenCaptureSkill",
    "TaskTrackerSkill",
    "WebSearchSkill",
    "DocxFormatterSkill",
]
