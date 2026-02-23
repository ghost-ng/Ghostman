"""
Calendar Event Skill - Create calendar appointments using Outlook COM automation.

This skill creates calendar appointments in the local Outlook client and displays them
for user review. It NEVER saves appointments automatically - user must click Save.
"""

import logging
import threading
import queue as q_module
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

logger = logging.getLogger("specter.skills.calendar_event")


class CalendarEventSkill(BaseSkill):
    """
    Skill for creating calendar appointments using Microsoft Outlook.

    Creates appointment drafts and displays them for user review. Never saves
    appointments automatically - respects draft-only mode for user safety.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="calendar_event",
            name="Calendar Event",
            description=(
                "Create calendar appointments/meetings in Outlook. "
                "Opens the draft in Outlook for user review — NEVER saves automatically. "
                "Requires subject, start (YYYY-MM-DD HH:MM), and end. "
                "Supports location, body, reminder_minutes, and attendees (comma-separated emails)."
            ),
            category=SkillCategory.PRODUCTIVITY,
            icon="📅",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="1.1.0",
            author="Specter",
            ai_callable=True,
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
                constraints={"min": 0, "max": 10080}
            ),
            SkillParameter(
                name="attendees",
                type=str,
                required=False,
                description="Attendees email addresses (comma-separated)",
                default="",
                constraints={"max_length": 1000}
            ),
        ]

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """Parse datetime string to datetime object."""
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid datetime format: {dt_str}. Use YYYY-MM-DD HH:MM")

    @staticmethod
    def _create_in_thread(params: Dict[str, Any], result_queue: q_module.Queue) -> None:
        """Create calendar appointment in a dedicated COM thread."""
        import pythoncom
        pythoncom.CoInitialize()
        try:
            # Pre-flight: check COM availability
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CLASSES_ROOT, r"Outlook.Application\CLSID"
                )
                winreg.CloseKey(key)
            except FileNotFoundError:
                result_queue.put(SkillResult(
                    success=False,
                    message="New Outlook detected — COM automation not supported",
                    error=(
                        "You are using the New Outlook (olk.exe) which does not "
                        "support COM automation. Calendar operations require classic "
                        "Outlook (outlook.exe). Please install or switch to classic "
                        "Outlook, or keep it installed alongside New Outlook."
                    ),
                ))
                return

            import win32com.client

            # Parse datetime strings
            try:
                start_dt = CalendarEventSkill._parse_datetime(params["start"])
                end_dt = CalendarEventSkill._parse_datetime(params["end"])

                if end_dt <= start_dt:
                    result_queue.put(SkillResult(
                        success=False,
                        message="Invalid time range",
                        error="End time must be after start time"
                    ))
                    return
            except ValueError as e:
                result_queue.put(SkillResult(
                    success=False,
                    message="Invalid date/time format",
                    error=str(e)
                ))
                return

            outlook = win32com.client.Dispatch("Outlook.Application")

            # Create appointment item (1 = AppointmentItem)
            appointment = outlook.CreateItem(1)

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

            # Add attendees — converts to meeting request
            attendee_list = []
            if params.get("attendees"):
                for email in params["attendees"].split(","):
                    email = email.strip()
                    if email:
                        appointment.Recipients.Add(email)
                        attendee_list.append(email)
                if attendee_list:
                    appointment.MeetingStatus = 1  # olMeeting

            # Display draft window - DO NOT SAVE
            appointment.Display(False)

            logger.info(f"Calendar appointment created: {params['subject']}")

            result_queue.put(SkillResult(
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
                    "attendees": attendee_list,
                    "is_meeting": bool(attendee_list),
                },
                action_taken=f"Opened appointment draft: {params['subject']}",
            ))

        except ImportError:
            result_queue.put(SkillResult(
                success=False,
                message="Outlook integration not available",
                error="pywin32 package not installed. Run: pip install pywin32"
            ))
        except Exception as e:
            logger.error(f"Calendar event COM thread failed: {e}", exc_info=True)
            result_queue.put(SkillResult(
                success=False,
                message="Failed to create calendar appointment",
                error=str(e)
            ))
        finally:
            pythoncom.CoUninitialize()

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the calendar event skill.

        Creates a calendar appointment in Outlook and displays it for user review.
        NEVER saves the appointment automatically. COM calls run in a dedicated thread.
        """
        try:
            result_queue = q_module.Queue()
            thread = threading.Thread(
                target=self._create_in_thread,
                args=(params, result_queue),
                daemon=True,
            )
            thread.start()
            thread.join(timeout=30)

            if thread.is_alive():
                return SkillResult(
                    success=False,
                    message="Calendar event timed out",
                    error="Outlook COM operation took too long (>30s)"
                )

            if not result_queue.empty():
                return result_queue.get_nowait()

            return SkillResult(
                success=False,
                message="Failed to create calendar appointment",
                error="No result from COM thread"
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
