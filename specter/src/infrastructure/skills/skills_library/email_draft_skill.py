"""
Email Draft Skill - Create email drafts using Outlook COM automation.

Creates email drafts in the local Outlook client and displays them
for user review. Supports plain text and HTML body. NEVER sends automatically.
"""

import logging
import threading
import queue as q_module
from typing import List, Any, Dict

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

logger = logging.getLogger("specter.skills.email_draft")


class EmailDraftSkill(BaseSkill):
    """
    Skill for drafting emails using Microsoft Outlook.

    Creates email drafts and displays them for user review. Never sends
    emails automatically - user must click Send in the Outlook window.

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="email_draft",
            name="Email Drafting",
            description=(
                "Create email drafts in Outlook for review and sending. "
                "Supports plain text and HTML body, CC/BCC, and importance. "
                "The draft opens in Outlook for the user to review — it is NEVER sent automatically."
            ),
            category=SkillCategory.COMMUNICATION,
            icon="📧",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="2.0.0",
            author="Specter",
            ai_callable=True,
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="to",
                type=str,
                required=True,
                description="Recipient email address(es), comma-separated for multiple",
                constraints={"min_length": 3, "max_length": 500},
            ),
            SkillParameter(
                name="subject",
                type=str,
                required=False,
                description="Email subject line",
                default="",
                constraints={"max_length": 255},
            ),
            SkillParameter(
                name="body",
                type=str,
                required=True,
                description="Email body text (plain text or HTML)",
                constraints={"min_length": 1, "max_length": 50000},
            ),
            SkillParameter(
                name="cc",
                type=str,
                required=False,
                description="CC recipients (comma-separated)",
                default="",
                constraints={"max_length": 500},
            ),
            SkillParameter(
                name="bcc",
                type=str,
                required=False,
                description="BCC recipients (comma-separated)",
                default="",
                constraints={"max_length": 500},
            ),
            SkillParameter(
                name="html",
                type=bool,
                required=False,
                description="If true, body is treated as HTML. Auto-detected if body contains HTML tags.",
                default=False,
            ),
            SkillParameter(
                name="importance",
                type=str,
                required=False,
                description="Email importance: high, normal, or low",
                default="normal",
            ),
        ]

    @staticmethod
    def _is_html(body: str) -> bool:
        """Check if body looks like HTML content."""
        body_lower = body.lower().strip()
        html_indicators = ("<html", "<p>", "<p ", "<div", "<br", "<table", "<ul", "<ol", "<h1", "<h2", "<h3")
        return any(tag in body_lower for tag in html_indicators)

    @staticmethod
    def _draft_in_thread(params: Dict[str, Any], result_queue: q_module.Queue) -> None:
        """Create email draft in a dedicated COM thread."""
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
                        "support COM automation. Email drafting requires classic "
                        "Outlook (outlook.exe). Please install or switch to classic "
                        "Outlook, or keep it installed alongside New Outlook."
                    ),
                ))
                return

            import win32com.client

            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)  # 0 = MailItem

            mail.To = params["to"]

            if params.get("cc"):
                mail.CC = params["cc"]
            if params.get("bcc"):
                mail.BCC = params["bcc"]

            mail.Subject = params.get("subject", "")

            # Set body — HTML or plain text
            body = params["body"]
            use_html = params.get("html", False) or EmailDraftSkill._is_html(body)

            if use_html:
                mail.BodyFormat = 2  # olFormatHTML
                # Wrap in HTML if not already a full document
                if not body.lower().strip().startswith("<html"):
                    body = f"<html><body>{body}</body></html>"
                mail.HTMLBody = body
            else:
                mail.Body = body

            # Set importance
            importance = (params.get("importance") or "normal").lower()
            importance_map = {"low": 0, "normal": 1, "high": 2}
            if importance in importance_map:
                mail.Importance = importance_map[importance]

            # CRITICAL: Display draft window - DO NOT SEND
            mail.Display(False)

            logger.info(f"Email draft created for: {params['to']}")

            result_queue.put(SkillResult(
                success=True,
                message="Email draft created and opened for review",
                data={
                    "to": params["to"],
                    "subject": params.get("subject", ""),
                    "has_cc": bool(params.get("cc")),
                    "has_bcc": bool(params.get("bcc")),
                    "body_length": len(params["body"]),
                    "is_html": use_html,
                    "importance": importance,
                },
                action_taken=f"Opened email draft to {params['to']}",
            ))
        except ImportError:
            result_queue.put(SkillResult(
                success=False,
                message="Outlook integration not available",
                error="pywin32 package not installed. Run: pip install pywin32",
            ))
        except Exception as e:
            logger.error(f"Email draft COM thread failed: {e}", exc_info=True)
            result_queue.put(SkillResult(
                success=False,
                message="Failed to create email draft",
                error=str(e),
            ))
        finally:
            pythoncom.CoUninitialize()

    async def execute(self, **params: Any) -> SkillResult:
        """Execute the email draft skill."""
        try:
            result_queue = q_module.Queue()
            thread = threading.Thread(
                target=self._draft_in_thread,
                args=(params, result_queue),
                daemon=True,
            )
            thread.start()
            thread.join(timeout=30)

            if thread.is_alive():
                return SkillResult(
                    success=False,
                    message="Email draft timed out",
                    error="Outlook COM operation took too long (>30s)",
                )
            if not result_queue.empty():
                return result_queue.get_nowait()
            return SkillResult(
                success=False,
                message="Failed to create email draft",
                error="No result from COM thread",
            )
        except Exception as e:
            logger.error(f"Email draft skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False, message="Failed to create email draft", error=str(e),
            )

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Email draft skill succeeded: {result.data}")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Email draft skill failed: {result.error}")
