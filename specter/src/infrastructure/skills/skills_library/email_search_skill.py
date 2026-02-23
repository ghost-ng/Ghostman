"""
Email Search Skill - Search Outlook emails with fuzzy matching and semantic search.

Searches local Outlook cache using COM automation. Supports simple "get recent"
mode, fuzzy sender matching, body search, TF-IDF semantic ranking, multi-folder
search, and Exchange DN resolution.

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

logger = logging.getLogger("specter.skills.email_search")

# Outlook folder constants (olDefaultFolders enum)
FOLDER_MAP = {
    "inbox": 6, "sent": 5, "sent items": 5, "sent mail": 5,
    "drafts": 16, "deleted": 3, "deleted items": 3, "trash": 3,
    "junk": 23, "spam": 23, "outbox": 4, "all": None,
}

IMPORTANCE_MAP = {"low": 0, "normal": 1, "high": 2}
IMPORTANCE_REVERSE = {0: "low", 1: "normal", 2: "high"}

# Outlook item class constants
OL_MAIL_ITEM_CLASS = 43
OL_MEETING_ITEM_CLASS = 53  # Meeting request/response items


def _safe_str(item: Any, attr: str, default: str = "") -> str:
    """Safely get a string attribute from a COM object."""
    try:
        val = getattr(item, attr, default)
        return str(val) if val is not None else default
    except Exception:
        return default


class EmailSearchSkill(BaseSkill):
    """
    Skill for searching emails in Outlook.

    When called with NO search criteria it works in "get recent" mode,
    simply returning the N most recent items from the requested folder.
    This enables natural requests like "show my last email" or
    "recall what I sent yesterday".

    Requirements:
        - Microsoft Outlook installed and configured
        - pywin32 package for COM automation
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="email_search",
            name="Email Search",
            description=(
                "Search Outlook emails or retrieve recent messages. "
                "Call with NO filters to get the most recent emails from a folder. "
                "For example: 'show my last email' → folder='inbox', max_results=1; "
                "'recall my last sent email' → folder='sent', max_results=1. "
                "Supports sender (fuzzy), recipient, subject, body_contains, "
                "days_back, has_attachments, unread_only, importance, folder, "
                "semantic_query, max_results."
            ),
            category=SkillCategory.COMMUNICATION,
            icon="🔍",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.OUTLOOK_ACCESS],
            version="3.0.0",
            author="Specter",
            ai_callable=True,
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="sender",
                type=str,
                required=False,
                description="Sender name or email address (fuzzy matched)",
                default=None,
            ),
            SkillParameter(
                name="recipient",
                type=str,
                required=False,
                description="To/CC recipient name or email address",
                default=None,
            ),
            SkillParameter(
                name="subject",
                type=str,
                required=False,
                description="Subject keyword (substring match)",
                default=None,
            ),
            SkillParameter(
                name="body_contains",
                type=str,
                required=False,
                description="Body text to search for",
                default=None,
            ),
            SkillParameter(
                name="days_back",
                type=int,
                required=False,
                description=(
                    "Search last N days. Default 7 for filtered searches, "
                    "365 when no filters (get-recent mode). Use 365 for broad searches."
                ),
                default=None,
                constraints={"min": 1, "max": 3650},
            ),
            SkillParameter(
                name="has_attachments",
                type=bool,
                required=False,
                description="Filter for emails with attachments",
                default=None,
            ),
            SkillParameter(
                name="unread_only",
                type=bool,
                required=False,
                description="Only return unread emails",
                default=False,
            ),
            SkillParameter(
                name="importance",
                type=str,
                required=False,
                description="Filter by importance: high, normal, or low",
                default=None,
            ),
            SkillParameter(
                name="folder",
                type=str,
                required=False,
                description=(
                    "Folder to search: inbox, sent, drafts, deleted, junk, outbox, "
                    "or 'all' to search inbox+sent together"
                ),
                default="inbox",
            ),
            SkillParameter(
                name="max_results",
                type=int,
                required=False,
                description="Maximum results to return (use 1 for 'last email')",
                default=10,
                constraints={"min": 1, "max": 500},
            ),
            SkillParameter(
                name="semantic_query",
                type=str,
                required=False,
                description="Natural language search (TF-IDF ranking)",
                default=None,
            ),
            SkillParameter(
                name="include_body",
                type=bool,
                required=False,
                description="Include body text preview in results",
                default=True,
            ),
        ]

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _has_search_criteria(params: Dict[str, Any]) -> bool:
        """Check if any search filter was provided (vs get-recent mode)."""
        search_keys = (
            "sender", "recipient", "subject", "body_contains",
            "has_attachments", "importance", "semantic_query",
        )
        for key in search_keys:
            val = params.get(key)
            if val is not None and val != "" and val is not False:
                return True
        if params.get("unread_only"):
            return True
        return False

    # ── Filter builders ──────────────────────────────────────────────

    @staticmethod
    def _build_jet_filter(params: Dict[str, Any]) -> Optional[str]:
        """Build Jet filter for boolean/integer fields only."""
        clauses = []
        if params.get("unread_only"):
            clauses.append("[UnRead] = True")
        importance = params.get("importance")
        if importance and importance.lower() in IMPORTANCE_MAP:
            clauses.append(f"[Importance] = {IMPORTANCE_MAP[importance.lower()]}")
        return " AND ".join(clauses) if clauses else None

    @staticmethod
    def _build_dasl_filter(params: Dict[str, Any]) -> Optional[str]:
        """Build DASL @SQL= filter for string fields.

        Sender IS included using broad LIKE '%name%' on both sendername
        and fromemail. This pre-filters at the Outlook level for
        efficiency (critical for large inboxes). The Python-side fuzzy
        matcher still runs afterward for ranking and stricter matching.
        """
        clauses = []

        sender = params.get("sender")
        if sender:
            escaped = sender.replace("'", "''").replace('"', '""')
            clauses.append(
                f"(\"urn:schemas:httpmail:sendername\" like '%{escaped}%'"
                f" OR \"urn:schemas:httpmail:fromemail\" like '%{escaped}%')"
            )

        subject = params.get("subject")
        if subject:
            escaped = subject.replace("'", "''").replace('"', '""')
            clauses.append(f"\"urn:schemas:httpmail:subject\" like '%{escaped}%'")

        body_contains = params.get("body_contains")
        if body_contains:
            escaped = body_contains.replace("'", "''").replace('"', '""')
            clauses.append(
                f"\"urn:schemas:httpmail:textdescription\" ci_phrasematch '{escaped}'"
            )

        recipient = params.get("recipient")
        if recipient:
            escaped = recipient.replace("'", "''").replace('"', '""')
            clauses.append(
                f"(\"urn:schemas:httpmail:displayto\" like '%{escaped}%'"
                f" OR \"urn:schemas:httpmail:displaycc\" like '%{escaped}%')"
            )

        if not clauses:
            return None
        return "@SQL=" + " AND ".join(clauses)

    # ── Exchange DN resolution ───────────────────────────────────────

    @staticmethod
    def _resolve_smtp_address(item: Any) -> str:
        """Resolve sender SMTP address, handling Exchange DNs."""
        try:
            email_type = _safe_str(item, "SenderEmailType")
            if email_type == "EX":
                try:
                    sender = item.Sender
                    if sender:
                        exchange_user = sender.GetExchangeUser()
                        if exchange_user:
                            smtp = exchange_user.PrimarySmtpAddress
                            if smtp:
                                return str(smtp)
                except Exception:
                    pass
                try:
                    PR_SMTP = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
                    return str(item.PropertyAccessor.GetProperty(PR_SMTP))
                except Exception:
                    pass
            return _safe_str(item, "SenderEmailAddress")
        except Exception:
            return _safe_str(item, "SenderEmailAddress")

    # ── Data extraction ──────────────────────────────────────────────

    @staticmethod
    def _extract_email_data(
        item: Any, include_body: bool = True, strict_mail_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract structured data from an Outlook item.

        When strict_mail_only is False (default), meeting-related items are
        included but flagged with item_type. This prevents the "0 results"
        problem when Sent Items contains mostly meeting responses.
        """
        try:
            try:
                item_class = item.Class
            except Exception:
                item_class = None

            if strict_mail_only and item_class != OL_MAIL_ITEM_CLASS:
                return None

            # Determine item type
            if item_class == OL_MAIL_ITEM_CLASS:
                item_type = "email"
            elif item_class == OL_MEETING_ITEM_CLASS:
                item_type = "meeting"
            else:
                item_type = "other"

            sender_name = _safe_str(item, "SenderName")
            sender_email = EmailSearchSkill._resolve_smtp_address(item)

            try:
                received = item.ReceivedTime
                received_str = received.strftime("%Y-%m-%dT%H:%M:%S") if received else ""
            except Exception:
                # Sent items may use SentOn instead
                try:
                    sent = item.SentOn
                    received_str = sent.strftime("%Y-%m-%dT%H:%M:%S") if sent else ""
                except Exception:
                    received_str = ""

            try:
                att_count = item.Attachments.Count
                att_names = []
                for i in range(1, min(att_count + 1, 11)):
                    try:
                        att_names.append(item.Attachments.Item(i).FileName)
                    except Exception:
                        pass
            except Exception:
                att_count = 0
                att_names = []

            try:
                imp_val = item.Importance
                importance_str = IMPORTANCE_REVERSE.get(imp_val, "normal")
            except Exception:
                importance_str = "normal"

            try:
                cats = item.Categories
                categories = [c.strip() for c in cats.split(",")] if cats else []
            except Exception:
                categories = []

            result = {
                "item_type": item_type,
                "subject": _safe_str(item, "Subject"),
                "sender_name": sender_name,
                "sender_email": sender_email,
                "to": _safe_str(item, "To"),
                "cc": _safe_str(item, "CC"),
                "received_time": received_str,
                "has_attachments": att_count > 0,
                "attachment_count": att_count,
                "attachment_names": att_names,
                "unread": False,
                "importance": importance_str,
                "categories": categories,
                "size_kb": round(getattr(item, "Size", 0) / 1024, 1),
                "conversation_topic": _safe_str(item, "ConversationTopic"),
            }

            try:
                result["unread"] = bool(item.UnRead)
            except Exception:
                pass

            if include_body:
                try:
                    body = item.Body or ""
                    result["body_preview"] = body[:500].strip()
                except Exception:
                    result["body_preview"] = ""

            return result

        except Exception as e:
            logger.debug(f"Failed to extract email data: {e}")
            return None

    # ── Fuzzy sender matching ────────────────────────────────────────

    @staticmethod
    def _fuzzy_filter_results(
        results: List[Dict[str, Any]],
        sender_query: str,
        threshold: float = 0.4,
    ) -> List[Dict[str, Any]]:
        if not sender_query:
            return results
        query_lower = sender_query.lower()
        scored = []
        for email_data in results:
            name = (email_data.get("sender_name") or "").lower()
            addr = (email_data.get("sender_email") or "").lower()
            name_score = difflib.SequenceMatcher(None, query_lower, name).ratio()
            addr_score = difflib.SequenceMatcher(None, query_lower, addr).ratio()
            best_score = max(name_score, addr_score)
            if query_lower in name or query_lower in addr:
                best_score += 0.3
            if best_score >= threshold:
                email_data["_match_score"] = round(best_score, 3)
                scored.append((best_score, email_data))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    # ── Semantic search (TF-IDF) ─────────────────────────────────────

    @staticmethod
    def _semantic_search(
        results: List[Dict[str, Any]], query: str, max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        if not results or not query:
            return results[:max_results]
        documents = []
        for email_data in results:
            doc = (email_data.get("subject", "") + " " +
                   email_data.get("body_preview", ""))
            documents.append(doc)

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            all_texts = documents + [query]
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            query_vec = tfidf_matrix[-1]
            doc_vecs = tfidf_matrix[:-1]
            similarities = cosine_similarity(query_vec, doc_vecs).flatten()
            scored = []
            for i, score in enumerate(similarities):
                if score > 0:
                    results[i]["semantic_score"] = round(float(score), 4)
                    scored.append((score, results[i]))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in scored[:max_results]]
        except ImportError:
            logger.debug("scikit-learn not available, using keyword fallback")
            query_words = set(query.lower().split())
            scored = []
            for email_data in results:
                doc = (email_data.get("subject", "") + " " +
                       email_data.get("body_preview", "")).lower()
                doc_words = set(doc.split())
                overlap = len(query_words & doc_words)
                if overlap > 0:
                    score = overlap / max(len(query_words), 1)
                    email_data["semantic_score"] = round(score, 4)
                    scored.append((score, email_data))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in scored[:max_results]]

    # ── Single-folder COM search ─────────────────────────────────────

    @staticmethod
    def _search_folder(
        namespace: Any,
        folder_id: int,
        folder_name: str,
        params: Dict[str, Any],
        candidate_limit: int,
        cutoff_date: datetime,
        include_body: bool,
    ) -> List[Dict[str, Any]]:
        """Search a single Outlook folder and return extracted items."""
        try:
            folder = namespace.GetDefaultFolder(folder_id)
        except Exception as e:
            logger.warning(f"Could not access folder {folder_name}: {e}")
            return []

        items = folder.Items
        try:
            total_count = items.Count
            logger.info(f"Folder '{folder_name}' has {total_count} total items")
        except Exception:
            logger.debug(f"Could not get item count for folder '{folder_name}'")

        # Use SentOn for sent folder, ReceivedTime for others
        sort_field = "[SentOn]" if folder_id == 5 else "[ReceivedTime]"
        items.Sort(sort_field, True)

        # Apply Jet filter
        jet_filter = EmailSearchSkill._build_jet_filter(params)
        if jet_filter:
            try:
                items = items.Restrict(jet_filter)
            except Exception as e:
                logger.warning(f"Jet filter failed on {folder_name}: {e}")

        # Apply DASL filter
        dasl_filter = EmailSearchSkill._build_dasl_filter(params)
        if dasl_filter:
            logger.info(f"DASL filter for '{folder_name}': {dasl_filter}")
            try:
                items = items.Restrict(dasl_filter)
                try:
                    filtered_count = items.Count
                    logger.info(
                        f"DASL filter narrowed '{folder_name}' to "
                        f"{filtered_count} items"
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"DASL filter failed on {folder_name}: {e}")

        results = []
        count = 0
        skipped = 0
        try:
            item = items.GetFirst()
            while item is not None and count < candidate_limit:
                # Date cutoff (locale-independent, in Python)
                try:
                    # Try ReceivedTime first, fall back to SentOn
                    received = getattr(item, "ReceivedTime", None)
                    if received is None:
                        received = getattr(item, "SentOn", None)
                    if received and hasattr(received, "year"):
                        item_date = datetime(
                            received.year, received.month, received.day,
                            received.hour, received.minute, received.second,
                        )
                        if item_date < cutoff_date:
                            break  # Sorted descending — all remaining older
                except Exception:
                    pass

                email_data = EmailSearchSkill._extract_email_data(
                    item, include_body, strict_mail_only=False,
                )
                if email_data is not None:
                    results.append(email_data)
                    count += 1
                else:
                    skipped += 1
                item = items.GetNext()
        except Exception as e:
            logger.debug(f"Iteration stopped on {folder_name}: {e}")

        logger.debug(
            f"Folder '{folder_name}': {count} extracted, {skipped} skipped"
        )
        return results

    # ── COM availability check ────────────────────────────────────────

    @staticmethod
    def _check_outlook_com() -> Dict[str, Any]:
        """Check if classic Outlook COM is available (vs New Outlook only)."""
        import winreg
        info: Dict[str, Any] = {
            "classic_com_available": False,
            "new_outlook_only": False,
        }
        # Check classic Outlook COM registration
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT, r"Outlook.Application\CLSID"
            )
            winreg.CloseKey(key)
            info["classic_com_available"] = True
        except FileNotFoundError:
            pass

        # Check if New Outlook (olk.exe) is installed
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\App Paths\olk.exe",
            )
            winreg.CloseKey(key)
            if not info["classic_com_available"]:
                info["new_outlook_only"] = True
        except FileNotFoundError:
            pass

        return info

    # ── COM thread worker ────────────────────────────────────────────

    @staticmethod
    def _execute_com_search(params: Dict[str, Any], result_queue: q_module.Queue) -> None:
        """Run Outlook COM search in a dedicated thread."""
        import pythoncom
        pythoncom.CoInitialize()
        try:
            # Pre-flight: check COM availability
            com_info = EmailSearchSkill._check_outlook_com()
            if com_info["new_outlook_only"]:
                result_queue.put(SkillResult(
                    success=False,
                    message="New Outlook detected — COM automation not supported",
                    error=(
                        "You are using the New Outlook (olk.exe) which does not "
                        "support COM automation. Email search requires classic "
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
                logger.info("Connected to Outlook COM (version unknown)")

            folder_name = (params.get("folder") or "inbox").lower().strip()
            max_results = params.get("max_results", 10)
            include_body = params.get("include_body", True)
            sender = params.get("sender")
            semantic_query = params.get("semantic_query")

            # Determine if this is "get recent" (no search criteria) or filtered
            has_criteria = EmailSearchSkill._has_search_criteria(params)

            # Smart days_back: generous for get-recent and sender-only searches
            days_back = params.get("days_back")
            if days_back is None:
                if not has_criteria:
                    days_back = 365  # Get-recent mode
                elif sender and not any(
                    params.get(k) for k in (
                        "subject", "body_contains", "recipient",
                        "importance", "semantic_query",
                    )
                ) and not params.get("unread_only"):
                    days_back = 365  # Sender-only: search wider window
                else:
                    days_back = 90  # Filtered search
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Candidate limit: pull more when post-filtering will trim
            # With DASL pre-filtering the candidates are already narrowed,
            # but we keep generous limits as safety net
            if semantic_query:
                candidate_limit = max(max_results * 10, 500)
            elif sender:
                candidate_limit = max(max_results * 10, 500)
            elif not has_criteria:
                candidate_limit = max_results  # Get-recent: exact count
            else:
                candidate_limit = max(max_results * 2, 50)

            logger.debug(
                f"Email search: folder={folder_name}, days_back={days_back}, "
                f"has_criteria={has_criteria}, candidate_limit={candidate_limit}"
            )

            # Multi-folder search for "all"
            if folder_name == "all":
                folders_to_search = [
                    (6, "inbox"), (5, "sent"),
                ]
            else:
                folder_id = FOLDER_MAP.get(folder_name, 6)
                folders_to_search = [(folder_id, folder_name)]

            all_results = []
            for fid, fname in folders_to_search:
                folder_results = EmailSearchSkill._search_folder(
                    namespace, fid, fname, params,
                    candidate_limit, cutoff_date, include_body,
                )
                all_results.extend(folder_results)

            # Sort combined results by date descending
            if len(folders_to_search) > 1:
                all_results.sort(
                    key=lambda e: e.get("received_time", ""),
                    reverse=True,
                )

            # Python-side post-filters
            has_attachments = params.get("has_attachments")
            if has_attachments is not None:
                all_results = [
                    e for e in all_results
                    if e.get("has_attachments") == has_attachments
                ]

            if sender:
                # The DASL filter already pre-filtered by sender at the
                # Outlook search index level. Only apply fuzzy filtering
                # if the results actually have sender data (some Outlook
                # builds return empty SenderName via COM).
                has_sender_data = any(
                    r.get("sender_name") or r.get("sender_email")
                    for r in all_results[:5]
                )
                if has_sender_data:
                    all_results = EmailSearchSkill._fuzzy_filter_results(
                        all_results, sender, threshold=0.4
                    )
                else:
                    # SenderName/SenderEmailAddress inaccessible (common
                    # with New Outlook COM bridge). Trust the DASL filter
                    # and populate sender from the query for display.
                    logger.info(
                        "Sender properties inaccessible via COM; "
                        "trusting DASL pre-filter for sender='%s'", sender
                    )
                    for r in all_results:
                        if not r.get("sender_name"):
                            r["sender_name"] = sender
                            r["sender_note"] = "matched by search filter"

            if semantic_query:
                all_results = EmailSearchSkill._semantic_search(
                    all_results, semantic_query, max_results
                )

            all_results = all_results[:max_results]
            searched = ", ".join(f[1] for f in folders_to_search)

            logger.info(
                f"Email search found {len(all_results)} results in {searched}"
            )

            result_queue.put(SkillResult(
                success=True,
                message=f"Found {len(all_results)} email(s) in {searched}",
                data={
                    "emails": all_results,
                    "total_found": len(all_results),
                    "folder": searched,
                    "search_criteria": {
                        k: v for k, v in params.items()
                        if v is not None and k != "include_body"
                    },
                },
                action_taken=f"Searched {searched} (found {len(all_results)})",
            ))

        except ImportError:
            result_queue.put(SkillResult(
                success=False,
                message="Outlook integration not available",
                error="pywin32 package not installed. Run: pip install pywin32",
            ))
        except Exception as e:
            logger.error(f"Email search COM thread failed: {e}", exc_info=True)
            error_msg = str(e)
            # Detect "Invalid class string" — COM server not registered
            if "0x800401F3" in error_msg or "Invalid class string" in error_msg:
                error_msg = (
                    "Outlook COM server not found. This usually means only the "
                    "New Outlook (olk.exe) is installed, which does not support "
                    "COM automation. Please install classic Outlook (outlook.exe)."
                )
            result_queue.put(SkillResult(
                success=False,
                message="Failed to search emails",
                error=error_msg,
            ))
        finally:
            pythoncom.CoUninitialize()

    # ── Main execute ─────────────────────────────────────────────────

    async def execute(self, **params: Any) -> SkillResult:
        """Execute the email search skill."""
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
                    message="Email search timed out",
                    error="Outlook COM operation took too long (>60s)",
                )
            if not result_queue.empty():
                return result_queue.get_nowait()
            return SkillResult(
                success=False,
                message="Failed to search emails",
                error="No result from COM thread",
            )
        except Exception as e:
            logger.error(f"Email search skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False, message="Failed to search emails", error=str(e),
            )

    async def on_success(self, result: SkillResult) -> None:
        logger.info(f"Email search succeeded: {result.data.get('total_found', 0)} results")

    async def on_error(self, result: SkillResult) -> None:
        logger.warning(f"Email search failed: {result.error}")
