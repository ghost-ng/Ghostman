"""Unified Outlook email skill with operation registry and COM sandbox."""

import logging
import difflib
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..interfaces.base_skill import (
    BaseSkill, SkillMetadata, SkillParameter, SkillResult,
    SkillCategory, PermissionType,
)
from ..core.outlook_com_bridge import (
    execute_in_com_thread, preflight_check, OutlookCOMSandbox,
    CodeExecutionResult,
)

logger = logging.getLogger("specter.outlook_email_skill")

ALL_OPERATIONS = [
    "draft_email",
    "search_email",
    "reply_email",
    "forward_email",
    "custom",
]

# Outlook folder constants (olDefaultFolders)
FOLDER_MAP = {
    "inbox": 6, "sent": 5, "drafts": 16, "deleted": 3,
    "junk": 23, "outbox": 4, "all": None,
}


class OutlookEmailSkill(BaseSkill):
    """Unified Outlook email skill with operation registry and COM sandbox."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="outlook_email",
            name="Outlook Email",
            description=(
                "Manage Outlook emails: draft new emails, search the mailbox, "
                "reply to or forward emails, and run custom email operations. "
                "Operations: " + ", ".join(ALL_OPERATIONS)
            ),
            category=SkillCategory.COMMUNICATION,
            icon="\u2709",
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
            # draft_email params
            SkillParameter("to", str, required=False,
                          description="Recipient email(s), comma-separated",
                          constraints={"min_length": 3, "max_length": 500}),
            SkillParameter("subject", str, required=False,
                          description="Email subject line",
                          constraints={"max_length": 255}),
            SkillParameter("body", str, required=False,
                          description="Email body (plain text or HTML)",
                          constraints={"min_length": 1, "max_length": 50000}),
            SkillParameter("cc", str, required=False,
                          description="CC recipients, comma-separated",
                          constraints={"max_length": 500}),
            SkillParameter("bcc", str, required=False,
                          description="BCC recipients, comma-separated",
                          constraints={"max_length": 500}),
            SkillParameter("html", bool, required=False,
                          description="Force HTML format (auto-detected if not set)"),
            SkillParameter("importance", str, required=False,
                          description="Email importance: low, normal, or high"),
            # search_email params
            SkillParameter("sender", str, required=False,
                          description="Filter by sender name or email"),
            SkillParameter("recipient", str, required=False,
                          description="Filter by recipient in To/CC"),
            SkillParameter("body_contains", str, required=False,
                          description="Search email body text"),
            SkillParameter("days_back", int, required=False,
                          description="Search within last N days (1-3650)"),
            SkillParameter("has_attachments", bool, required=False,
                          description="Filter for emails with attachments"),
            SkillParameter("unread_only", bool, required=False,
                          description="Only return unread emails"),
            SkillParameter("folder", str, required=False,
                          description="Mailbox folder: inbox, sent, drafts, deleted, junk, outbox, all"),
            SkillParameter("max_results", int, required=False,
                          description="Maximum results to return (1-500)",
                          constraints={"min_value": 1, "max_value": 500}),
            SkillParameter("semantic_query", str, required=False,
                          description="Natural language query for semantic ranking"),
            SkillParameter("include_body", bool, required=False,
                          description="Include body preview in search results"),
            # reply/forward params
            SkillParameter("reply_subject", str, required=False,
                          description="Subject of email to reply to (finds most recent match)"),
            SkillParameter("forward_to", str, required=False,
                          description="Recipient(s) to forward to"),
            SkillParameter("reply_body", str, required=False,
                          description="Body text for reply or forward"),
            # custom params
            SkillParameter("custom_code", str, required=False,
                          description="Python code for custom Outlook operations (sandboxed)"),
        ]

    async def execute(self, **params) -> SkillResult:
        operation = params.get("operation", "")
        if operation not in ALL_OPERATIONS:
            return SkillResult(
                success=False,
                message="Invalid operation",
                error=f"Unknown operation: '{operation}'. Valid: {', '.join(ALL_OPERATIONS)}"
            )

        try:
            if operation == "draft_email":
                return await self._draft_email(params)
            elif operation == "search_email":
                return await self._search_email(params)
            elif operation == "reply_email":
                return await self._reply_email(params)
            elif operation == "forward_email":
                return await self._forward_email(params)
            elif operation == "custom":
                return await self._execute_custom(params)
        except Exception as e:
            logger.error(f"Operation '{operation}' failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Operation failed",
                error=f"Operation '{operation}' failed: {e}"
            )

    # --- Internal operation methods ---
    # Each method is refactored from the original skill files,
    # using execute_in_com_thread() from outlook_com_bridge.

    async def _draft_email(self, params: dict) -> SkillResult:
        """Create and display an email draft. Refactored from EmailDraftSkill."""
        to = params.get("to", "")
        if not to:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'to' is required for draft_email"
            )
        body = params.get("body", "")
        if not body:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'body' is required for draft_email"
            )

        subject = params.get("subject", "")
        cc = params.get("cc", "")
        bcc = params.get("bcc", "")
        importance = params.get("importance", "normal")
        is_html = params.get("html", None)
        if is_html is None:
            is_html = self._is_html(body)

        def _create_draft(outlook, namespace, **kw):
            mail = outlook.CreateItem(0)  # olMailItem
            mail.To = to
            if cc:
                mail.CC = cc
            if bcc:
                mail.BCC = bcc
            mail.Subject = subject

            if is_html:
                mail.BodyFormat = 2  # olFormatHTML
                html_body = body
                if not body.strip().lower().startswith("<html"):
                    html_body = f"<html><body>{body}</body></html>"
                mail.HTMLBody = html_body
            else:
                mail.Body = body

            importance_map = {"low": 0, "normal": 1, "high": 2}
            mail.Importance = importance_map.get(importance.lower(), 1)

            mail.Display(False)
            return {
                "to": to, "subject": subject, "cc": cc, "bcc": bcc,
                "importance": importance, "format": "html" if is_html else "text",
                "action": "Draft opened in Outlook for review"
            }

        result = execute_in_com_thread(_create_draft, timeout=30)
        if result.success:
            return SkillResult(
                success=True,
                message="Email draft created and opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, message="Operation failed", error=result.error)

    async def _search_email(self, params: dict) -> SkillResult:
        """Search Outlook mailbox. Refactored from EmailSearchSkill."""
        import datetime

        sender = params.get("sender")
        recipient = params.get("recipient")
        subject = params.get("subject")
        body_contains = params.get("body_contains")
        days_back = params.get("days_back")
        has_attachments = params.get("has_attachments")
        unread_only = params.get("unread_only", False)
        importance = params.get("importance")
        folder_name = params.get("folder", "inbox").lower()
        max_results = min(params.get("max_results", 10), 500)
        semantic_query = params.get("semantic_query")
        include_body = params.get("include_body", True)

        # Determine if this is a "get recent" (no filters) or filtered search
        has_filters = any([sender, recipient, subject, body_contains,
                          has_attachments, unread_only, importance, semantic_query])

        if days_back is None:
            days_back = 365 if not has_filters or (sender and not subject and not body_contains) else 90
        days_back = max(1, min(days_back, 3650))

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)

        def _search(outlook, namespace, **kw):
            # Get folder
            if folder_name == "all":
                folders_to_search = [
                    namespace.GetDefaultFolder(6),   # Inbox
                    namespace.GetDefaultFolder(5),   # Sent
                ]
            else:
                folder_id = FOLDER_MAP.get(folder_name, 6)
                folders_to_search = [namespace.GetDefaultFolder(folder_id)]

            all_results = []
            for folder in folders_to_search:
                items = folder.Items

                # Pass 1: Jet filter (boolean/integer fields)
                jet_parts = []
                if unread_only:
                    jet_parts.append("[UnRead] = True")
                if importance:
                    imp_map = {"low": 0, "normal": 1, "high": 2}
                    imp_val = imp_map.get(importance.lower())
                    if imp_val is not None:
                        jet_parts.append(f"[Importance] = {imp_val}")
                if jet_parts:
                    items = items.Restrict(" AND ".join(jet_parts))

                # Pass 2: DASL filter (text fields)
                dasl_parts = []
                if sender:
                    s = sender.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:sendername\" like '%{s}%' OR "
                        f"\"urn:schemas:httpmail:fromemail\" like '%{s}%'"
                    )
                if subject:
                    s = subject.replace("'", "''")
                    dasl_parts.append(f"\"urn:schemas:httpmail:subject\" like '%{s}%'")
                if body_contains:
                    s = body_contains.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:textdescription\" ci_phrasematch '{s}'"
                    )
                if recipient:
                    r = recipient.replace("'", "''")
                    dasl_parts.append(
                        f"\"urn:schemas:httpmail:displayto\" like '%{r}%' OR "
                        f"\"urn:schemas:httpmail:displaycc\" like '%{r}%'"
                    )
                if dasl_parts:
                    dasl_filter = "@SQL=" + " AND ".join(f"({p})" for p in dasl_parts)
                    items = items.Restrict(dasl_filter)

                # Sort descending by date
                is_sent = (folder_name == "sent")
                sort_field = "[SentOn]" if is_sent else "[ReceivedTime]"
                items.Sort(sort_field, True)

                # Iterate with date cutoff
                item = items.GetFirst()
                candidates = []
                while item and len(candidates) < max_results * 3:
                    try:
                        item_time = item.SentOn if is_sent else item.ReceivedTime
                        if item_time and hasattr(item_time, 'year'):
                            item_dt = datetime.datetime(
                                item_time.year, item_time.month, item_time.day,
                                item_time.hour, item_time.minute, item_time.second
                            )
                            if item_dt < cutoff_date:
                                break  # Sorted descending, done

                        # Python-side post-filters
                        if has_attachments is not None:
                            if bool(item.Attachments.Count > 0) != has_attachments:
                                item = items.GetNext()
                                continue

                        # Fuzzy sender matching
                        if sender and not self._fuzzy_match_sender(item, sender):
                            item = items.GetNext()
                            continue

                        candidates.append(self._extract_email_data(
                            item, include_body, is_sent
                        ))
                    except Exception as e:
                        logger.debug(f"Skipping item: {e}")
                    item = items.GetNext()

                all_results.extend(candidates)

            # Semantic ranking if requested
            if semantic_query and all_results:
                all_results = self._semantic_rank(all_results, semantic_query)

            return all_results[:max_results]

        result = execute_in_com_thread(_search, timeout=60)
        if result.success:
            items = result.data or []
            return SkillResult(
                success=True,
                message=f"Found {len(items)} email(s)",
                data={"items": items, "count": len(items), "folder": folder_name}
            )
        return SkillResult(success=False, message="Operation failed", error=result.error)

    async def _reply_email(self, params: dict) -> SkillResult:
        """Reply to the most recent email matching subject."""
        reply_subject = params.get("reply_subject", "")
        if not reply_subject:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'reply_subject' is required for reply_email"
            )
        reply_body = params.get("reply_body", "")

        def _reply(outlook, namespace, **kw):
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            # Find most recent matching email
            subj_lower = reply_subject.lower()
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
                return {"error": f"No email found matching subject: '{reply_subject}'"}

            reply = found.Reply()
            if reply_body:
                if self._is_html(reply_body):
                    reply.HTMLBody = reply_body + reply.HTMLBody
                else:
                    reply.Body = reply_body + "\n\n" + reply.Body
            reply.Display(False)
            return {
                "original_subject": found.Subject,
                "original_sender": getattr(found, 'SenderName', ''),
                "action": "Reply opened in Outlook for review"
            }

        result = execute_in_com_thread(_reply, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(
                    success=False, message="Email not found",
                    error=result.data["error"]
                )
            return SkillResult(
                success=True,
                message="Reply draft opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, message="Operation failed", error=result.error)

    async def _forward_email(self, params: dict) -> SkillResult:
        """Forward the most recent email matching subject."""
        reply_subject = params.get("reply_subject", "") or params.get("subject", "")
        forward_to = params.get("forward_to", "")
        if not reply_subject:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'reply_subject' or 'subject' is required for forward_email"
            )
        if not forward_to:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'forward_to' is required for forward_email"
            )
        reply_body = params.get("reply_body", "")

        def _forward(outlook, namespace, **kw):
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            subj_lower = reply_subject.lower()
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
                return {"error": f"No email found matching subject: '{reply_subject}'"}

            fwd = found.Forward()
            fwd.To = forward_to
            if reply_body:
                if self._is_html(reply_body):
                    fwd.HTMLBody = reply_body + fwd.HTMLBody
                else:
                    fwd.Body = reply_body + "\n\n" + fwd.Body
            fwd.Display(False)
            return {
                "original_subject": found.Subject,
                "forward_to": forward_to,
                "action": "Forward opened in Outlook for review"
            }

        result = execute_in_com_thread(_forward, timeout=30)
        if result.success:
            if "error" in (result.data or {}):
                return SkillResult(
                    success=False, message="Email not found",
                    error=result.data["error"]
                )
            return SkillResult(
                success=True,
                message="Forward draft opened in Outlook",
                data=result.data
            )
        return SkillResult(success=False, message="Operation failed", error=result.error)

    async def _execute_custom(self, params: dict) -> SkillResult:
        """Execute AI-generated custom COM code via sandbox."""
        code = params.get("custom_code", "")
        if not code:
            return SkillResult(
                success=False, message="Missing parameter",
                error="'custom_code' is required for custom operation"
            )

        sandbox = OutlookCOMSandbox()
        exec_result = sandbox.execute_code(code, timeout=30)

        if exec_result.success:
            return SkillResult(
                success=True,
                message=exec_result.message,
                data={"output": str(exec_result.output) if exec_result.output else None}
            )
        return SkillResult(
            success=False,
            message="Custom operation failed",
            error=exec_result.error
        )

    # --- Helper methods (refactored from existing skills) ---

    @staticmethod
    def _is_html(text: str) -> bool:
        """Check if text contains HTML tags."""
        lower = text.lower()
        html_tags = ["<html", "<p>", "<p ", "<div", "<br", "<table", "<ul", "<ol", "<h1", "<h2", "<h3"]
        return any(tag in lower for tag in html_tags)

    @staticmethod
    def _fuzzy_match_sender(item, query: str) -> bool:
        """Fuzzy match sender against query string."""
        try:
            sender_name = getattr(item, 'SenderName', '') or ''
            sender_email = ''
            try:
                if getattr(item, 'SenderEmailType', '') == "EX":
                    try:
                        sender_email = item.Sender.GetExchangeUser().PrimarySmtpAddress or ''
                    except Exception:
                        sender_email = getattr(item, 'SenderEmailAddress', '') or ''
                else:
                    sender_email = getattr(item, 'SenderEmailAddress', '') or ''
            except Exception:
                sender_email = getattr(item, 'SenderEmailAddress', '') or ''

            query_lower = query.lower()
            for field in [sender_name.lower(), sender_email.lower()]:
                if query_lower in field:
                    return True
                ratio = difflib.SequenceMatcher(None, query_lower, field).ratio()
                if ratio >= 0.4:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_email_data(item, include_body: bool, is_sent: bool) -> dict:
        """Extract data from an Outlook mail item."""
        try:
            sender_email = ''
            try:
                if getattr(item, 'SenderEmailType', '') == "EX":
                    try:
                        sender_email = item.Sender.GetExchangeUser().PrimarySmtpAddress or ''
                    except Exception:
                        try:
                            sender_email = item.PropertyAccessor.GetProperty(
                                "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
                            ) or ''
                        except Exception:
                            sender_email = getattr(item, 'SenderEmailAddress', '') or ''
                else:
                    sender_email = getattr(item, 'SenderEmailAddress', '') or ''
            except Exception:
                sender_email = getattr(item, 'SenderEmailAddress', '') or ''

            data = {
                "subject": getattr(item, 'Subject', '') or '',
                "sender_name": getattr(item, 'SenderName', '') or '',
                "sender_email": sender_email,
                "to": getattr(item, 'To', '') or '',
                "cc": getattr(item, 'CC', '') or '',
                "received_time": str(item.SentOn if is_sent else item.ReceivedTime),
                "has_attachments": item.Attachments.Count > 0,
                "attachment_count": item.Attachments.Count,
                "unread": getattr(item, 'UnRead', False),
                "importance": {0: "low", 1: "normal", 2: "high"}.get(
                    getattr(item, 'Importance', 1), "normal"
                ),
            }
            if include_body:
                body = getattr(item, 'Body', '') or ''
                data["body_preview"] = body[:500]

            # Attachment names (up to 10)
            if data["has_attachments"]:
                names = []
                for i in range(1, min(item.Attachments.Count + 1, 11)):
                    try:
                        names.append(item.Attachments.Item(i).FileName)
                    except Exception:
                        pass
                data["attachment_names"] = names

            return data
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _semantic_rank(items: list, query: str) -> list:
        """Rank items by semantic relevance using TF-IDF or word overlap."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts = [
                f"{item.get('subject', '')} {item.get('body_preview', '')} "
                f"{item.get('sender_name', '')}"
                for item in items
            ]
            texts.insert(0, query)
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            ranked = sorted(zip(items, similarities), key=lambda x: x[1], reverse=True)
            return [item for item, _ in ranked]
        except ImportError:
            # Fallback: simple word overlap
            query_words = set(query.lower().split())
            def score(item):
                text = f"{item.get('subject', '')} {item.get('body_preview', '')}".lower()
                return sum(1 for w in query_words if w in text)
            return sorted(items, key=score, reverse=True)

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Outlook email operation succeeded: {result.message}")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Outlook email operation failed: {result.error}")
