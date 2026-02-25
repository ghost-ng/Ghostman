"""Unified Outlook calendar skill with operation registry and COM sandbox."""

import datetime
import difflib
import logging
from typing import Any, Dict, List, Optional

from ..interfaces.base_skill import (
    BaseSkill, SkillMetadata, SkillParameter, SkillResult,
    SkillCategory, PermissionType,
)
from ..core.outlook_com_bridge import (
    execute_in_com_thread, OutlookCOMSandbox,
)

logger = logging.getLogger("specter.outlook_calendar_skill")

ALL_OPERATIONS = [
    "create_event",
    "search_events",
    "update_event",
    "cancel_event",
    "custom",
]

# Datetime formats to try when parsing user input
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]

MEETING_STATUS_MAP = {
    0: "nonmeeting", 1: "meeting", 3: "received",
    5: "cancelled", 7: "received_cancelled",
}
BUSY_STATUS_MAP = {
    0: "free", 1: "tentative", 2: "busy", 3: "oof", 4: "working_elsewhere",
}
RECURRENCE_MAP = {
    0: "daily", 1: "weekly", 2: "monthly",
    3: "monthly_nth", 5: "yearly", 6: "yearly_nth",
}


class OutlookCalendarSkill(BaseSkill):
    """Unified Outlook calendar skill with operation registry and COM sandbox."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="outlook_calendar",
            name="Outlook Calendar",
            description=(
                "Manage Outlook calendar: create events, search for appointments, "
                "update or cancel events, and run custom calendar operations. "
                "Operations: " + ", ".join(ALL_OPERATIONS)
            ),
            category=SkillCategory.PRODUCTIVITY,
            icon="\U0001f4c5",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            ai_callable=True,
            version="1.0.0",
        )

    @property
    def parameters(self) -> list:
        return [
            SkillParameter("operation", str, required=True,
                          description=f"Operation to perform. One of: {', '.join(ALL_OPERATIONS)}",
                          constraints={"choices": ALL_OPERATIONS}),
            # create_event / update_event params
            SkillParameter("subject", str, required=False,
                          description="Event subject/title",
                          constraints={"min_length": 1, "max_length": 255}),
            SkillParameter("start", str, required=False,
                          description="Start datetime (e.g., '2026-02-25 14:00')"),
            SkillParameter("end", str, required=False,
                          description="End datetime (e.g., '2026-02-25 15:00')"),
            SkillParameter("location", str, required=False,
                          description="Event location",
                          constraints={"max_length": 255}),
            SkillParameter("body", str, required=False,
                          description="Event notes/description",
                          constraints={"max_length": 10000}),
            SkillParameter("reminder_minutes", int, required=False,
                          description="Reminder minutes before event (0=none, max 10080)"),
            SkillParameter("attendees", str, required=False,
                          description="Comma-separated attendee email addresses",
                          constraints={"max_length": 1000}),
            # search_events params
            SkillParameter("start_date", str, required=False,
                          description="Search start date (YYYY-MM-DD, default: today)"),
            SkillParameter("end_date", str, required=False,
                          description="Search end date (YYYY-MM-DD)"),
            SkillParameter("days_ahead", int, required=False,
                          description="Search N days ahead (1-365, default: 7)"),
            SkillParameter("attendee", str, required=False,
                          description="Filter by attendee name or email"),
            SkillParameter("include_recurring", bool, required=False,
                          description="Include recurring event instances (default: true)"),
            SkillParameter("max_results", int, required=False,
                          description="Maximum results (1-200)",
                          constraints={"min_value": 1, "max_value": 200}),
            # cancel_event params
            SkillParameter("cancel_subject", str, required=False,
                          description="Subject of event to cancel"),
            # custom params
            SkillParameter("custom_code", str, required=False,
                          description="Python code for custom calendar operations (sandboxed)"),
        ]

    async def execute(self, **params) -> SkillResult:
        operation = params.get("operation", "")
        if operation not in ALL_OPERATIONS:
            return SkillResult(
                success=False,
                skill_id=self.metadata.skill_id,
                error=f"Unknown operation: '{operation}'. Valid: {', '.join(ALL_OPERATIONS)}"
            )

        try:
            if operation == "create_event":
                return await self._create_event(params)
            elif operation == "search_events":
                return await self._search_events(params)
            elif operation == "update_event":
                return await self._update_event(params)
            elif operation == "cancel_event":
                return await self._cancel_event(params)
            elif operation == "custom":
                return await self._execute_custom(params)
        except Exception as e:
            logger.error(f"Operation '{operation}' failed: {e}", exc_info=True)
            return SkillResult(
                success=False, skill_id=self.metadata.skill_id,
                error=f"Operation '{operation}' failed: {e}"
            )

    def _parse_datetime(self, dt_str: str) -> Optional[datetime.datetime]:
        """Parse datetime string trying multiple formats."""
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None

    async def _create_event(self, params: dict) -> SkillResult:
        """Create and display a calendar event. Refactored from CalendarEventSkill."""
        subject = params.get("subject", "")
        start_str = params.get("start", "")
        end_str = params.get("end", "")

        if not subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'subject' is required for create_event")
        if not start_str or not end_str:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'start' and 'end' are required for create_event")

        start_dt = self._parse_datetime(start_str)
        end_dt = self._parse_datetime(end_str)
        if not start_dt or not end_dt:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error=f"Cannot parse datetime. Supported formats: YYYY-MM-DD HH:MM")
        if end_dt <= start_dt:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="End time must be after start time")

        location = params.get("location", "")
        body = params.get("body", "")
        reminder_minutes = params.get("reminder_minutes", 15)
        attendees_str = params.get("attendees", "")

        def _create(outlook, namespace, **kw):
            appt = outlook.CreateItem(1)  # olAppointmentItem
            appt.Subject = subject
            appt.Start = start_dt.strftime("%Y-%m-%d %H:%M")
            appt.End = end_dt.strftime("%Y-%m-%d %H:%M")
            if location:
                appt.Location = location
            if body:
                appt.Body = body

            if reminder_minutes and reminder_minutes > 0:
                appt.ReminderSet = True
                appt.ReminderMinutesBeforeStart = min(reminder_minutes, 10080)
            else:
                appt.ReminderSet = False

            attendees_list = []
            if attendees_str:
                for email in attendees_str.split(","):
                    email = email.strip()
                    if email:
                        appt.Recipients.Add(email)
                        attendees_list.append(email)
                appt.MeetingStatus = 1  # olMeeting

            appt.Display(False)

            duration = int((end_dt - start_dt).total_seconds() / 60)
            return {
                "subject": subject,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "location": location,
                "duration_minutes": duration,
                "attendees": attendees_list,
                "is_meeting": bool(attendees_list),
                "reminder_minutes": reminder_minutes,
                "action": "Event opened in Outlook for review"
            }

        result = execute_in_com_thread(_create, timeout=30)
        if result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Calendar event created and opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _search_events(self, params: dict) -> SkillResult:
        """Search Outlook calendar. Refactored from CalendarSearchSkill."""
        subject = params.get("subject")
        location = params.get("location")
        attendee = params.get("attendee")
        days_ahead = max(1, min(params.get("days_ahead", 7), 365))
        include_recurring = params.get("include_recurring", True)
        max_results = min(params.get("max_results", 25), 200)

        # Parse date range
        today = datetime.date.today()
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")

        if start_date_str:
            try:
                start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                start_dt = datetime.datetime.combine(today, datetime.time.min)
        else:
            start_dt = datetime.datetime.combine(today, datetime.time.min)

        if end_date_str:
            try:
                end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_dt = start_dt + datetime.timedelta(days=days_ahead)
        else:
            end_dt = start_dt + datetime.timedelta(days=days_ahead)

        def _search(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)  # olFolderCalendar
            items = calendar.Items

            # Sort MUST happen before IncludeRecurrences (Microsoft docs)
            items.Sort("[Start]")
            if include_recurring:
                items.IncludeRecurrences = True

            # DASL filter for subject/location (no date filter — locale issues)
            dasl_parts = []
            if subject:
                s = subject.replace("'", "''")
                dasl_parts.append(f"\"urn:schemas:httpmail:subject\" like '%{s}%'")
            if location:
                loc = location.replace("'", "''")
                dasl_parts.append(f"\"urn:schemas:calendar:location\" like '%{loc}%'")
            if dasl_parts:
                items = items.Restrict("@SQL=" + " AND ".join(f"({p})" for p in dasl_parts))

            # Python-side date iteration (locale-independent)
            results = []
            candidate_limit = max_results * 5 if attendee else max_results
            item = items.GetFirst()
            skip_count = 0
            max_skip = 50000

            while item and len(results) < candidate_limit and skip_count < max_skip:
                try:
                    item_start = item.Start
                    if not item_start or not hasattr(item_start, 'year'):
                        item = items.GetNext()
                        skip_count += 1
                        continue

                    item_start_dt = datetime.datetime(
                        item_start.year, item_start.month, item_start.day,
                        item_start.hour, item_start.minute, item_start.second
                    )

                    if item_start_dt < start_dt:
                        item = items.GetNext()
                        skip_count += 1
                        continue
                    if item_start_dt > end_dt:
                        break  # Sorted ascending, done

                    # Attendee filter
                    if attendee and not self._fuzzy_match_attendee(item, attendee):
                        item = items.GetNext()
                        continue

                    results.append(self._extract_event_data(item))
                except Exception as e:
                    logger.debug(f"Skipping calendar item: {e}")

                item = items.GetNext()
                skip_count += 1

            return results[:max_results]

        result = execute_in_com_thread(_search, timeout=60)
        if result.success:
            items = result.data or []
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=f"Found {len(items)} calendar event(s)",
                data={"items": items, "count": len(items)}
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _update_event(self, params: dict) -> SkillResult:
        """Find an event by subject and open it for editing."""
        subject = params.get("subject", "") or params.get("cancel_subject", "")
        if not subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'subject' is required for update_event")

        def _update(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)
            items = calendar.Items
            items.Sort("[Start]", True)  # Most recent first

            subj_lower = subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No event found matching subject: '{subject}'"}

            found.Display(False)
            return {
                "subject": found.Subject,
                "start": str(found.Start),
                "action": "Event opened in Outlook for editing"
            }

        result = execute_in_com_thread(_update, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Event opened for editing",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _cancel_event(self, params: dict) -> SkillResult:
        """Find an event and open it for user to cancel/delete."""
        cancel_subject = params.get("cancel_subject", "") or params.get("subject", "")
        if not cancel_subject:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'cancel_subject' or 'subject' is required for cancel_event")

        def _cancel(outlook, namespace, **kw):
            calendar = namespace.GetDefaultFolder(9)
            items = calendar.Items
            items.Sort("[Start]", True)

            subj_lower = cancel_subject.lower()
            item = items.GetFirst()
            found = None
            checked = 0
            while item and checked < 500:
                try:
                    if subj_lower in (item.Subject or "").lower():
                        found = item
                        break
                except Exception:
                    pass
                item = items.GetNext()
                checked += 1

            if not found:
                return {"error": f"No event found matching subject: '{cancel_subject}'"}

            # Open for user review — never auto-delete
            found.Display(False)
            return {
                "subject": found.Subject,
                "start": str(found.Start),
                "action": "Event opened in Outlook — user can cancel/delete manually"
            }

        result = execute_in_com_thread(_cancel, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(success=False, skill_id=self.metadata.skill_id,
                                 error=result.data["error"])
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message="Event opened for cancellation review",
                data=result.data
            )
        return SkillResult(success=False, skill_id=self.metadata.skill_id, error=result.error)

    async def _execute_custom(self, params: dict) -> SkillResult:
        """Execute AI-generated custom COM code via sandbox."""
        code = params.get("custom_code", "")
        if not code:
            return SkillResult(success=False, skill_id=self.metadata.skill_id,
                             error="'custom_code' is required for custom operation")

        sandbox = OutlookCOMSandbox()
        exec_result = sandbox.execute_code(code, timeout=30)

        if exec_result.success:
            return SkillResult(
                success=True, skill_id=self.metadata.skill_id,
                message=exec_result.message,
                data={"output": str(exec_result.output) if exec_result.output else None}
            )
        return SkillResult(
            success=False, skill_id=self.metadata.skill_id,
            error=exec_result.error
        )

    # --- Helper methods ---

    @staticmethod
    def _fuzzy_match_attendee(item, query: str) -> bool:
        """Fuzzy match against organizer and all attendees."""
        try:
            query_lower = query.lower()
            # Check organizer
            organizer = getattr(item, 'Organizer', '') or ''
            if query_lower in organizer.lower():
                return True
            if difflib.SequenceMatcher(None, query_lower, organizer.lower()).ratio() >= 0.4:
                return True

            # Check recipients
            for i in range(1, item.Recipients.Count + 1):
                try:
                    recip = item.Recipients.Item(i)
                    name = recip.Name or ''
                    email = ''
                    try:
                        addr_entry = recip.AddressEntry
                        if addr_entry.Type == "EX":
                            try:
                                email = addr_entry.GetExchangeUser().PrimarySmtpAddress or ''
                            except Exception:
                                email = addr_entry.Address or ''
                        else:
                            email = addr_entry.Address or ''
                    except Exception:
                        pass

                    for field in [name.lower(), email.lower()]:
                        if query_lower in field:
                            return True
                        if difflib.SequenceMatcher(None, query_lower, field).ratio() >= 0.4:
                            return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_event_data(item) -> dict:
        """Extract data from an Outlook appointment item."""
        try:
            # Attendees
            attendees = []
            try:
                for i in range(1, item.Recipients.Count + 1):
                    try:
                        recip = item.Recipients.Item(i)
                        email = ''
                        try:
                            addr_entry = recip.AddressEntry
                            if addr_entry.Type == "EX":
                                try:
                                    email = addr_entry.GetExchangeUser().PrimarySmtpAddress or ''
                                except Exception:
                                    email = addr_entry.Address or ''
                            else:
                                email = addr_entry.Address or ''
                        except Exception:
                            pass
                        response_map = {0: "none", 1: "organizer", 2: "tentative",
                                       3: "accepted", 4: "declined"}
                        attendees.append({
                            "name": recip.Name or '',
                            "email": email,
                            "response_status": response_map.get(recip.MeetingResponseStatus, "unknown")
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            # Recurrence
            is_recurring = getattr(item, 'IsRecurring', False)
            recurrence_pattern = ""
            if is_recurring:
                try:
                    rp = item.GetRecurrencePattern()
                    recurrence_pattern = RECURRENCE_MAP.get(rp.RecurrenceType, "unknown")
                except Exception:
                    recurrence_pattern = "unknown"

            # Duration
            start_time = item.Start
            end_time = item.End
            duration = 0
            try:
                start_dt = datetime.datetime(
                    start_time.year, start_time.month, start_time.day,
                    start_time.hour, start_time.minute
                )
                end_dt = datetime.datetime(
                    end_time.year, end_time.month, end_time.day,
                    end_time.hour, end_time.minute
                )
                duration = int((end_dt - start_dt).total_seconds() / 60)
            except Exception:
                pass

            body = getattr(item, 'Body', '') or ''

            return {
                "subject": getattr(item, 'Subject', '') or '',
                "start": str(start_time),
                "end": str(end_time),
                "duration_minutes": duration,
                "location": getattr(item, 'Location', '') or '',
                "organizer": getattr(item, 'Organizer', '') or '',
                "attendees": attendees,
                "body_preview": body[:300],
                "is_recurring": is_recurring,
                "recurrence_pattern": recurrence_pattern,
                "categories": getattr(item, 'Categories', '') or '',
                "is_all_day": getattr(item, 'AllDayEvent', False),
                "meeting_status": MEETING_STATUS_MAP.get(
                    getattr(item, 'MeetingStatus', 0), "nonmeeting"
                ),
                "busy_status": BUSY_STATUS_MAP.get(
                    getattr(item, 'BusyStatus', 2), "busy"
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Outlook calendar operation succeeded: {result.message}")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Outlook calendar operation failed: {result.error}")
