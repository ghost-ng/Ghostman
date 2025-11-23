"""
Email Draft Skill - Create email drafts using Outlook COM automation.

This skill creates email drafts in the local Outlook client and displays them
for user review. It NEVER sends emails automatically - user must click Send.
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

logger = logging.getLogger("ghostman.skills.email_draft")


class EmailDraftSkill(BaseSkill):
    """
    Skill for drafting emails using Microsoft Outlook.

    Creates email drafts and displays them for user review. Never sends
    emails automatically - respects draft-only mode for user safety.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation

    Example:
        >>> skill = EmailDraftSkill()
        >>> result = await skill.execute(
        ...     to="user@example.com",
        ...     subject="Meeting Follow-up",
        ...     body="Thank you for the productive meeting today."
        ... )
        >>> print(result.message)
        "Email draft created and opened for review"
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="email_draft",
            name="Email Drafting",
            description="Create email drafts in Outlook for review and sending",
            category=SkillCategory.COMMUNICATION,
            icon="📧",
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
                name="to",
                type=str,
                required=True,
                description="Recipient email address",
                constraints={"min_length": 3, "max_length": 255}
            ),
            SkillParameter(
                name="subject",
                type=str,
                required=False,
                description="Email subject line",
                default="",
                constraints={"max_length": 255}
            ),
            SkillParameter(
                name="body",
                type=str,
                required=True,
                description="Email body text",
                constraints={"min_length": 1, "max_length": 10000}
            ),
            SkillParameter(
                name="cc",
                type=str,
                required=False,
                description="CC recipients (comma-separated)",
                default="",
                constraints={"max_length": 500}
            ),
            SkillParameter(
                name="bcc",
                type=str,
                required=False,
                description="BCC recipients (comma-separated)",
                default="",
                constraints={"max_length": 500}
            ),
        ]

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the email draft skill.

        Creates an email draft in Outlook and displays it for user review.
        NEVER sends the email automatically.

        Args:
            **params: Validated parameters (to, subject, body, cc, bcc)

        Returns:
            SkillResult with success status and draft window information
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
            except Exception as e:
                logger.error(f"Failed to connect to Outlook: {e}")
                return SkillResult(
                    success=False,
                    message="Could not connect to Outlook",
                    error=f"Outlook not installed or not configured: {str(e)}"
                )

            # Create email item (0 = MailItem)
            mail = outlook.CreateItem(0)

            # Set recipients
            mail.To = params["to"]

            if params.get("cc"):
                mail.CC = params["cc"]

            if params.get("bcc"):
                mail.BCC = params["bcc"]

            # Set subject and body
            mail.Subject = params.get("subject", "")
            mail.Body = params["body"]

            # CRITICAL: Display draft window - DO NOT SEND
            # False = non-modal window (user can interact with other windows)
            mail.Display(False)

            logger.info(f"✓ Email draft created for: {params['to']}")

            return SkillResult(
                success=True,
                message="Email draft created and opened for review",
                data={
                    "to": params["to"],
                    "subject": params.get("subject", ""),
                    "has_cc": bool(params.get("cc")),
                    "has_bcc": bool(params.get("bcc")),
                    "body_length": len(params["body"]),
                },
                action_taken=f"Opened email draft to {params['to']}",
            )

        except Exception as e:
            logger.error(f"Email draft skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Failed to create email draft",
                error=str(e)
            )

    async def on_success(self, result: SkillResult) -> None:
        """Log successful email draft creation."""
        logger.info(f"Email draft skill succeeded: {result.data}")

    async def on_error(self, result: SkillResult) -> None:
        """Log email draft creation failure."""
        logger.warning(f"Email draft skill failed: {result.error}")
