"""
Email Search Skill - Search local Outlook cache for emails.

This skill searches the local Outlook email cache using COM automation.
It NEVER queries the server - all searches are local-only for privacy and speed.
"""

import logging
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

logger = logging.getLogger("ghostman.skills.email_search")


class EmailSearchSkill(BaseSkill):
    """
    Skill for searching emails in local Outlook cache.

    Searches locally cached emails only - no server queries.
    Returns list of matching emails with metadata.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation

    Example:
        >>> skill = EmailSearchSkill()
        >>> result = await skill.execute(
        ...     from_address="boss@company.com",
        ...     subject_contains="budget",
        ...     days_back=7
        ... )
        >>> for email in result.data['emails']:
        ...     print(f"{email['subject']} from {email['sender']}")
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="email_search",
            name="Email Search",
            description="Search local Outlook cache for emails",
            category=SkillCategory.COMMUNICATION,
            icon="🔍",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="1.0.0",
            author="Ghostman"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        return [
            SkillParameter(
                name="from_address",
                type=str,
                required=False,
                description="Filter by sender email address",
                default=None
            ),
            SkillParameter(
                name="subject_contains",
                type=str,
                required=False,
                description="Filter by subject keyword",
                default=None
            ),
            SkillParameter(
                name="days_back",
                type=int,
                required=False,
                description="Search last N days",
                default=7,
                constraints={"min": 1, "max": 365}
            ),
            SkillParameter(
                name="has_attachments",
                type=bool,
                required=False,
                description="Filter by attachment presence",
                default=None
            ),
            SkillParameter(
                name="max_results",
                type=int,
                required=False,
                description="Maximum results to return",
                default=50,
                constraints={"min": 1, "max": 500}
            ),
        ]

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the email search skill.

        Searches local Outlook cache for emails matching criteria.

        Args:
            **params: Validated parameters

        Returns:
            SkillResult with list of matching emails
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

            # Connect to Outlook
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
            except Exception as e:
                logger.error(f"Failed to connect to Outlook: {e}")
                return SkillResult(
                    success=False,
                    message="Could not connect to Outlook",
                    error=f"Outlook not installed or not configured: {str(e)}"
                )

            # Get Inbox folder (6 = olFolderInbox)
            try:
                inbox = namespace.GetDefaultFolder(6)
                items = inbox.Items
            except Exception as e:
                return SkillResult(
                    success=False,
                    message="Could not access Inbox",
                    error=str(e)
                )

            # Build filter string using DASL syntax
            filters = []

            # Date range filter
            days_back = params.get("days_back", 7)
            start_date = datetime.now() - timedelta(days=days_back)
            filters.append(f"[ReceivedTime] >= '{start_date.strftime('%m/%d/%Y')}'")

            # Sender filter
            if params.get("from_address"):
                from_addr = params["from_address"]
                filters.append(f"[SenderEmailAddress] = '{from_addr}'")

            # Subject filter
            if params.get("subject_contains"):
                keyword = params["subject_contains"]
                # Escape single quotes
                keyword = keyword.replace("'", "''")
                filters.append(f"[Subject] LIKE '%{keyword}%'")

            # Attachment filter
            if params.get("has_attachments") is not None:
                has_attach = params["has_attachments"]
                filters.append(f"[Attachments] {'>' if has_attach else '='} 0")

            # Combine filters with AND
            filter_str = " AND ".join(filters)

            logger.debug(f"Email search filter: {filter_str}")

            # Apply filter
            try:
                filtered_items = items.Restrict(filter_str)
            except Exception as e:
                logger.error(f"Filter failed: {e}")
                return SkillResult(
                    success=False,
                    message="Search filter failed",
                    error=f"Invalid filter syntax: {str(e)}"
                )

            # Extract results
            results = []
            max_results = params.get("max_results", 50)

            for i, item in enumerate(filtered_items):
                if i >= max_results:
                    break

                try:
                    results.append({
                        "subject": item.Subject,
                        "sender": item.SenderEmailAddress,
                        "sender_name": item.SenderName,
                        "received_time": item.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S"),
                        "has_attachments": item.Attachments.Count > 0,
                        "size_kb": item.Size / 1024,
                    })
                except Exception as e:
                    logger.warning(f"Failed to extract email data: {e}")
                    continue

            logger.info(f"✓ Email search found {len(results)} results")

            return SkillResult(
                success=True,
                message=f"Found {len(results)} email(s)",
                data={
                    "emails": results,
                    "total_found": len(results),
                    "search_criteria": {
                        "from_address": params.get("from_address"),
                        "subject_contains": params.get("subject_contains"),
                        "days_back": days_back,
                        "has_attachments": params.get("has_attachments"),
                    },
                },
                action_taken=f"Searched Inbox for emails (found {len(results)})",
            )

        except Exception as e:
            logger.error(f"Email search skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Failed to search emails",
                error=str(e)
            )

    async def on_success(self, result: SkillResult) -> None:
        """Log successful email search."""
        logger.info(f"Email search skill succeeded: {result.data['total_found']} results")
