"""
Calendar Event Skill - Create calendar appointments using Outlook COM automation.

This skill creates calendar appointments in the local Outlook client and displays them
for user review. It NEVER saves appointments automatically - user must click Save.
"""

import logging
from typing import List, Any, Dict
from datetime import datetime

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

logger = logging.getLogger("ghostman.skills.calendar_event")


class CalendarEventSkill(BaseSkill):
    """
    Skill for creating calendar appointments using Microsoft Outlook.

    Creates appointment drafts and displays them for user review. Never saves
    appointments automatically - respects draft-only mode for user safety.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation

    Example:
        >>> skill = CalendarEventSkill()
        >>> result = await skill.execute(
        ...     subject="Team Meeting",
        ...     start="2025-01-15 10:00",
        ...     end="2025-01-15 11:00",
        ...     location="Conference Room A"
        ... )
        >>> print(result.message)
        "Calendar appointment created and opened for review"
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="calendar_event",
            name="Calendar Event",
            description="Create calendar appointments in Outlook for review and saving",
            category=SkillCategory.PRODUCTIVITY,
            icon="📅",
            enabled_by_default=True,
            requires_confirmation=False,  # Safe operation - just opens draft
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="1.0.0",
            author="Ghostman"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        return [
            SkillParameter(
                name="subject",
                type=str,
                required=True,
                description="Appointment subject/title",
                constraints={"min_length": 1, "max_length": 255}
            ),
            SkillParameter(
                name="start",
                type=str,
                required=True,
                description="Start date/time (YYYY-MM-DD HH:MM format)",
                constraints={"min_length": 10, "max_length": 50}
            ),
            SkillParameter(
                name="end",
                type=str,
                required=True,
                description="End date/time (YYYY-MM-DD HH:MM format)",
                constraints={"min_length": 10, "max_length": 50}
            ),
            SkillParameter(
                name="location",
                type=str,
                required=False,
                description="Meeting location",
                default="",
                constraints={"max_length": 255}
            ),
            SkillParameter(
                name="body",
                type=str,
                required=False,
                description="Appointment notes/description",
                default="",
                constraints={"max_length": 10000}
            ),
            SkillParameter(
                name="reminder_minutes",
                type=int,
                required=False,
                description="Reminder time in minutes before event",
                default=15,
                constraints={"min": 0, "max": 10080}  # 0 to 1 week
            ),
        ]

    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Parse datetime string to datetime object.

        Supports formats:
        - YYYY-MM-DD HH:MM
        - YYYY-MM-DD HH:MM:SS
        - MM/DD/YYYY HH:MM
        """
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid datetime format: {dt_str}. Use YYYY-MM-DD HH:MM")

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the calendar event skill.

        Creates a calendar appointment in Outlook and displays it for user review.
        NEVER saves the appointment automatically.

        Args:
            **params: Validated parameters (subject, start, end, location, body, reminder_minutes)

        Returns:
            SkillResult with success status and appointment window information
        """
        try:
            # Import win32com (only when needed)
            try:
                import win32com.client
            except ImportError:
                return SkillResult(
                    success=False,
                    message="Outlook integration not available",
                    error="pywin32 package not installed. Run: pip install pywin32"
                )

            # Parse datetime strings
            try:
                start_dt = self._parse_datetime(params["start"])
                end_dt = self._parse_datetime(params["end"])

                # Validate end is after start
                if end_dt <= start_dt:
                    return SkillResult(
                        success=False,
                        message="Invalid time range",
                        error="End time must be after start time"
                    )

            except ValueError as e:
                return SkillResult(
                    success=False,
                    message="Invalid date/time format",
                    error=str(e)
                )

            # Connect to Outlook
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
            except Exception as e:
                logger.error(f"Failed to connect to Outlook: {e}")
                return SkillResult(
                    success=False,
                    message="Could not connect to Outlook",
                    error=f"Outlook not installed or not configured: {str(e)}"
                )

            # Create appointment item (1 = AppointmentItem)
            appointment = outlook.CreateItem(1)

            # Set appointment properties
            appointment.Subject = params["subject"]
            appointment.Start = start_dt
            appointment.End = end_dt

            if params.get("location"):
                appointment.Location = params["location"]

            if params.get("body"):
                appointment.Body = params["body"]

            # Set reminder
            reminder_min = params.get("reminder_minutes", 15)
            if reminder_min > 0:
                appointment.ReminderSet = True
                appointment.ReminderMinutesBeforeStart = reminder_min
            else:
                appointment.ReminderSet = False

            # CRITICAL: Display draft window - DO NOT SAVE
            # False = non-modal window (user can interact with other windows)
            appointment.Display(False)

            logger.info(f"✓ Calendar appointment created: {params['subject']}")

            return SkillResult(
                success=True,
                message="Calendar appointment created and opened for review",
                data={
                    "subject": params["subject"],
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "location": params.get("location", ""),
                    "has_notes": bool(params.get("body")),
                    "reminder_minutes": reminder_min,
                    "duration_minutes": int((end_dt - start_dt).total_seconds() / 60),
                },
                action_taken=f"Opened appointment draft: {params['subject']}",
            )

        except Exception as e:
            logger.error(f"Calendar event skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Failed to create calendar appointment",
                error=str(e)
            )

    async def on_success(self, result: SkillResult) -> None:
        """Log successful appointment creation."""
        logger.info(f"Calendar event skill succeeded: {result.data}")

    async def on_error(self, result: SkillResult) -> None:
        """Log appointment creation failure."""
        logger.warning(f"Calendar event skill failed: {result.error}")
