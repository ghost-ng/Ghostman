"""
Calendar Search Skill - Search Outlook calendar appointments.

Searches the local Outlook calendar using COM automation with DASL filters.
Supports date range searches, subject/location keyword matching, fuzzy
attendee matching, recurring appointment expansion, and availability checks.

NOTE: Requires classic Outlook (outlook.exe) with COM support. The "New Outlook"
(olk.exe, WebView2-based) does NOT support COM automation.
"""

import difflib
import logging
import threading
import queue as q_module
from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

logger = logging.getLogger("specter.skills.calendar_search")

# Meeting status constants
MEETING_STATUS_MAP = {
    0: "nonmeeting",
    1: "meeting",
    3: "received",
    5: "cancelled",
    7: "received_cancelled",
}

# Busy status constants
BUSY_STATUS_MAP = {
    0: "free",
    1: "tentative",
    2: "busy",
    3: "oof",
    4: "working_elsewhere",
}

# Response status constants
RESPONSE_STATUS_MAP = {
    0: "none",
    1: "organized",
    2: "tentative",
    3: "accepted",
    4: "declined",
    5: "not_responded",
}

# Recurrence type constants
RECURRENCE_TYPE_MAP = {
    0: "daily",
    1: "weekly",
    2: "monthly",
    3: "monthly_nth",
    5: "yearly",
    6: "yearly_nth",
}


def _safe_str(item: Any, attr: str, default: str = "") -> str:
    """Safely get a string attribute from a COM object."""
    try:
        val = getattr(item, attr, default)
        return str(val) if val is not None else default
    except Exception:
        return default


class CalendarSearchSkill(BaseSkill):
    """
    Skill for searching Outlook calendar appointments.

    Supports date range queries, subject/location keyword matching,
    fuzzy attendee matching, recurring appointment expansion, and
    availability checking. All COM operations run in a dedicated thread.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="calendar_search",
            name="Calendar Search",
            description=(
                "Search Outlook calendar events or retrieve upcoming meetings. "
                "Call with NO filters to see upcoming events for the next 7 days. "
                "For example: 'what meetings do I have today' → days_ahead=1; "
                "'meetings this week' → days_ahead=7; 'am I free at 3pm tomorrow' "
                "→ days_ahead=2. Supports subject, attendee (fuzzy), location, "
                "start_date, end_date, days_ahead, include_recurring, max_results."
            ),
            category=SkillCategory.PRODUCTIVITY,
            icon="🗓️",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="1.0.0",
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
                required=False,
                description="Subject keyword (substring match)",
                default=None,
            ),
            SkillParameter(
                name="start_date",
                type=str,
                required=False,
                description="Start of date range (YYYY-MM-DD format)",
                default=None,
            ),
            SkillParameter(
                name="end_date",
                type=str,
                required=False,
                description="End of date range (YYYY-MM-DD format)",
                default=None,
            ),
            SkillParameter(
                name="days_ahead",
                type=int,
                required=False,
                description="Days ahead to search (used if no start/end dates)",
                default=7,
                constraints={"min": 1, "max": 365},
            ),
            SkillParameter(
                name="attendee",
                type=str,
                required=False,
                description="Attendee name or email (fuzzy matched)",
                default=None,
            ),
            SkillParameter(
                name="location",
                type=str,
                required=False,
                description="Location keyword",
                default=None,
            ),
            SkillParameter(
                name="include_recurring",
                type=bool,
                required=False,
                description="Include recurring appointment instances",
                default=True,
            ),
            SkillParameter(
                name="max_results",
                type=int,
                required=False,
                description="Maximum results to return",
                default=25,
                constraints={"min": 1, "max": 200},
            ),
        ]

    # ── Date range parsing ────────────────────────────────────────────
    #
    # Date filtering is done in Python during iteration because:
    #   - Jet date format is Windows-locale-dependent → silent 0-result failures
    #   - DASL calendar URNs cause "Condition is not valid" errors
    #   - Items sorted ascending by [Start], so we skip items before start
    #     and stop at items after end — bounded iteration
    #
    # Subject/location use DASL @SQL= filter on the collection.

    @staticmethod
    def _parse_date_range(params: Dict[str, Any]) -> tuple:
        """Parse start/end date range from params. Returns (start_dt, end_dt)."""
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")

        if start_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date_str}")
                start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if end_date_str:
            try:
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date_str}")
                days_ahead = params.get("days_ahead", 7)
                end_dt = datetime.now() + timedelta(days=days_ahead)
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
        else:
            days_ahead = params.get("days_ahead", 7)
            end_dt = datetime.now() + timedelta(days=days_ahead)
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        return start_dt, end_dt

    @staticmethod
    def _build_subject_location_filter(params: Dict[str, Any]) -> Optional[str]:
        """Build an optional second-pass DASL filter for subject/location keywords.

        Returns None if no subject or location filter is needed.
        """
        clauses = []

        subject = params.get("subject")
        if subject:
            escaped = subject.replace("'", "''")
            clauses.append(
                f"\"urn:schemas:httpmail:subject\" like '%{escaped}%'"
            )

        location = params.get("location")
        if location:
            escaped = location.replace("'", "''")
            clauses.append(
                f"\"urn:schemas:calendar:location\" like '%{escaped}%'"
            )

        if not clauses:
            return None

        return "@SQL=" + " AND ".join(clauses)

    # ── Data extraction ──────────────────────────────────────────────

    @staticmethod
    def _extract_appointment_data(item: Any) -> Optional[Dict[str, Any]]:
        """Extract structured data from a single Outlook appointment item."""
        try:
            # Start/End times
            try:
                start = item.Start
                start_str = start.strftime("%Y-%m-%dT%H:%M:%S") if start else ""
            except Exception:
                start_str = ""

            try:
                end = item.End
                end_str = end.strftime("%Y-%m-%dT%H:%M:%S") if end else ""
            except Exception:
                end_str = ""

            # Duration
            try:
                duration = item.Duration  # in minutes
            except Exception:
                duration = 0

            # Organizer
            organizer = _safe_str(item, "Organizer")

            # Attendees
            attendees = []
            try:
                recipients = item.Recipients
                for i in range(1, recipients.Count + 1):
                    try:
                        recip = recipients.Item(i)
                        name = str(recip.Name) if recip.Name else ""
                        email = ""
                        try:
                            # Try to get SMTP address
                            addr_entry = recip.AddressEntry
                            if addr_entry.Type == "EX":
                                try:
                                    ex_user = addr_entry.GetExchangeUser()
                                    if ex_user:
                                        email = str(ex_user.PrimarySmtpAddress or "")
                                except Exception:
                                    email = str(addr_entry.Address or "")
                            else:
                                email = str(addr_entry.Address or "")
                        except Exception:
                            email = str(recip.Address) if recip.Address else ""

                        response = RESPONSE_STATUS_MAP.get(
                            getattr(recip, "MeetingResponseStatus", 0), "none"
                        )
                        attendees.append({
                            "name": name,
                            "email": email,
                            "response_status": response,
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            # Recurring info
            is_recurring = False
            recurrence_pattern = ""
            try:
                is_recurring = bool(item.IsRecurring)
                if is_recurring:
                    try:
                        pattern = item.GetRecurrencePattern()
                        recurrence_pattern = RECURRENCE_TYPE_MAP.get(
                            pattern.RecurrenceType, "unknown"
                        )
                    except Exception:
                        recurrence_pattern = "unknown"
            except Exception:
                pass

            # Categories
            try:
                cats = item.Categories
                categories = [c.strip() for c in cats.split(",")] if cats else []
            except Exception:
                categories = []

            # Meeting status
            try:
                meeting_status = MEETING_STATUS_MAP.get(item.MeetingStatus, "nonmeeting")
            except Exception:
                meeting_status = "nonmeeting"

            # Busy status
            try:
                busy_status = BUSY_STATUS_MAP.get(item.BusyStatus, "busy")
            except Exception:
                busy_status = "busy"

            # Body preview
            try:
                body = item.Body or ""
                body_preview = body[:300].strip()
            except Exception:
                body_preview = ""

            # All day event
            try:
                is_all_day = bool(item.AllDayEvent)
            except Exception:
                is_all_day = False

            # Importance
            try:
                imp_val = item.Importance
                importance = {0: "low", 1: "normal", 2: "high"}.get(imp_val, "normal")
            except Exception:
                importance = "normal"

            return {
                "subject": _safe_str(item, "Subject"),
                "start": start_str,
                "end": end_str,
                "duration_minutes": duration,
                "location": _safe_str(item, "Location"),
                "organizer": organizer,
                "attendees": attendees,
                "body_preview": body_preview,
                "is_recurring": is_recurring,
                "recurrence_pattern": recurrence_pattern,
                "categories": categories,
                "importance": importance,
                "is_all_day": is_all_day,
                "meeting_status": meeting_status,
                "busy_status": busy_status,
            }

        except Exception as e:
            logger.debug(f"Failed to extract appointment data: {e}")
            return None

    # ── Fuzzy attendee matching ──────────────────────────────────────

    @staticmethod
    def _fuzzy_filter_attendees(
        results: List[Dict[str, Any]],
        attendee_query: str,
        threshold: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Filter appointments by fuzzy attendee name/email match."""
        if not attendee_query:
            return results

        query_lower = attendee_query.lower()
        filtered = []

        for appt in results:
            best_score = 0.0

            # Check organizer
            organizer = (appt.get("organizer") or "").lower()
            if organizer:
                score = difflib.SequenceMatcher(None, query_lower, organizer).ratio()
                if query_lower in organizer:
                    score += 0.3
                best_score = max(best_score, score)

            # Check each attendee
            for att in appt.get("attendees", []):
                name = (att.get("name") or "").lower()
                email = (att.get("email") or "").lower()

                name_score = difflib.SequenceMatcher(None, query_lower, name).ratio()
                email_score = difflib.SequenceMatcher(None, query_lower, email).ratio()

                if query_lower in name or query_lower in email:
                    name_score += 0.3
                    email_score += 0.3

                best_score = max(best_score, name_score, email_score)

            if best_score >= threshold:
                appt["_attendee_match_score"] = round(best_score, 3)
                filtered.append(appt)

        return filtered

    # ── COM thread worker ────────────────────────────────────────────

    @staticmethod
    def _execute_com_search(params: Dict[str, Any], result_queue: q_module.Queue) -> None:
        """Run Outlook calendar search in a dedicated thread with CoInitialize.

        Order: Sort("[Start]") → IncludeRecurrences = True → optional DASL filter.
        Date filtering is done in Python during iteration (locale-independent).
        Subject/location use DASL @SQL= filter.
        Never use .Count with IncludeRecurrences — iterate with GetFirst/GetNext.
        """
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
                        "support COM automation. Calendar search requires classic "
                        "Outlook (outlook.exe). Please install or switch to classic "
                        "Outlook, or keep it installed alongside New Outlook."
                    ),
                ))
                return

            import win32com.client

            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")

            # Log Outlook version for diagnostics
            try:
                outlook_ver = outlook.Version
                logger.info(f"Connected to Outlook COM version: {outlook_ver}")
            except Exception:
                pass

            # Get Calendar folder (9 = olFolderCalendar)
            try:
                calendar = namespace.GetDefaultFolder(9)
            except Exception as e:
                result_queue.put(SkillResult(
                    success=False,
                    message="Could not access Calendar folder",
                    error=str(e),
                ))
                return

            items = calendar.Items

            # Sort by Start ascending (required for recurrence expansion
            # and for Python-side date filtering to work with early-stop)
            items.Sort("[Start]")

            # Enable recurrence expansion
            include_recurring = params.get("include_recurring", True)
            items.IncludeRecurrences = include_recurring

            # NOTE: Jet date Restrict is NOT used here because its date format
            # is locale-dependent and silently returns 0 on non-US systems.
            # Date filtering is done in Python during iteration instead.

            # Optional DASL filter for subject/location
            dasl_filter = CalendarSearchSkill._build_subject_location_filter(params)
            if dasl_filter:
                logger.debug(f"Calendar DASL filter: {dasl_filter}")
                try:
                    items = items.Restrict(dasl_filter)
                except Exception as e:
                    logger.warning(f"Calendar DASL filter failed, using Python filter: {e}")

            # Parse date range for Python-side filtering
            start_dt, end_dt = CalendarSearchSkill._parse_date_range(params)
            logger.debug(f"Calendar search: start={start_dt.isoformat()}, "
                         f"end={end_dt.isoformat()}")

            # Determine candidate limit
            attendee = params.get("attendee")
            max_results = params.get("max_results", 25)
            candidate_limit = max(max_results * 5, 100) if attendee else max_results

            # Extract appointment data — use GetFirst/GetNext (never .Count).
            # Items sorted ascending by Start, so:
            #   - Skip items before start_dt (unlimited — calendar may span years)
            #   - Collect items between start_dt and end_dt
            #   - Stop when we pass end_dt (all remaining are later)
            #
            # With IncludeRecurrences=True, recurring items expand to individual
            # instances which can number in the thousands. The skip phase (items
            # before start_dt) uses a separate generous limit so we don't exhaust
            # the scan budget on old recurring instances.
            results = []
            count = 0
            items_in_range = 0
            items_skipped = 0
            max_skip = 50000  # generous limit for items before date range
            max_in_range = candidate_limit * 5  # safety for items within/after range
            try:
                appt = items.GetFirst()
                while appt is not None and count < candidate_limit:
                    # Python-side date filtering (locale-independent)
                    try:
                        appt_start = appt.Start
                        if hasattr(appt_start, 'year'):
                            item_start = datetime(
                                appt_start.year, appt_start.month, appt_start.day,
                                appt_start.hour, appt_start.minute, appt_start.second
                            )
                            if item_start > end_dt:
                                # Sorted ascending — all remaining are later
                                break
                            if item_start < start_dt:
                                items_skipped += 1
                                if items_skipped >= max_skip:
                                    logger.warning(
                                        f"Calendar skip limit reached ({max_skip}); "
                                        f"could not reach date range starting {start_dt}"
                                    )
                                    break
                                appt = items.GetNext()
                                continue
                    except Exception:
                        pass  # If we can't read date, include the item

                    items_in_range += 1
                    if items_in_range > max_in_range:
                        break

                    appt_data = CalendarSearchSkill._extract_appointment_data(appt)
                    if appt_data is not None:
                        results.append(appt_data)
                        count += 1
                    appt = items.GetNext()
            except Exception as e:
                logger.debug(f"Iteration stopped: {e}")

            logger.debug(
                f"Calendar search: {count} extracted, "
                f"{items_skipped} skipped (before range), "
                f"{items_in_range} scanned in range"
            )

            # Fuzzy attendee filter
            if attendee:
                results = CalendarSearchSkill._fuzzy_filter_attendees(
                    results, attendee, threshold=0.4
                )

            # Trim to max_results
            results = results[:max_results]

            logger.info(f"Calendar search found {len(results)} appointments")

            result_queue.put(SkillResult(
                success=True,
                message=f"Found {len(results)} appointment(s)",
                data={
                    "appointments": results,
                    "total_found": len(results),
                    "search_criteria": {
                        k: v for k, v in params.items()
                        if v is not None
                    },
                },
                action_taken=f"Searched calendar (found {len(results)} appointments)",
            ))

        except ImportError:
            result_queue.put(SkillResult(
                success=False,
                message="Outlook integration not available",
                error="pywin32 package not installed. Run: pip install pywin32",
            ))
        except Exception as e:
            logger.error(f"Calendar search COM thread failed: {e}", exc_info=True)
            error_msg = str(e)
            if "0x800401F3" in error_msg or "Invalid class string" in error_msg:
                error_msg = (
                    "Outlook COM server not found. This usually means only the "
                    "New Outlook (olk.exe) is installed, which does not support "
                    "COM automation. Please install classic Outlook (outlook.exe)."
                )
            result_queue.put(SkillResult(
                success=False,
                message="Failed to search calendar",
                error=error_msg,
            ))
        finally:
            pythoncom.CoUninitialize()

    # ── Main execute ─────────────────────────────────────────────────

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the calendar search skill.

        All COM operations run in a dedicated thread with pythoncom.CoInitialize().
        Supports date range, subject, location, and fuzzy attendee matching.
        """
        try:
            result_queue = q_module.Queue()
            thread = threading.Thread(
                target=self._execute_com_search,
                args=(params, result_queue),
                daemon=True,
            )
            thread.start()
            thread.join(timeout=60)

            if thread.is_alive():
                return SkillResult(
                    success=False,
                    message="Calendar search timed out",
                    error="Outlook COM operation took too long (>60s)",
                )

            if not result_queue.empty():
                return result_queue.get_nowait()

            return SkillResult(
                success=False,
                message="Failed to search calendar",
                error="No result from COM thread",
            )

        except Exception as e:
            logger.error(f"Calendar search skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Failed to search calendar",
                error=str(e),
            )

    async def on_success(self, result: SkillResult) -> None:
        """Log successful calendar search."""
        logger.info(f"Calendar search succeeded: {result.data.get('total_found', 0)} results")

    async def on_error(self, result: SkillResult) -> None:
        """Log calendar search failure."""
        logger.warning(f"Calendar search failed: {result.error}")
