"""
Recall Memory Service for the MemGPT-style memory system.

Provides searchable access to the full conversation history stored
in the SQLite database. Supports text search (SQL LIKE) and
date-range queries with pagination.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("specter.memory.recall")

# Page size for paginated search results
_PAGE_SIZE = 5


class RecallMemoryService:
    """
    Searchable conversation history backed by the existing SQLite DB.

    Uses the existing ``messages`` table via direct SQL queries for
    text and date-range searches. Falls back to LIKE when FTS is
    not available.
    """

    def __init__(self):
        self._db_path: Optional[str] = None
        self._resolve_db_path()

    def _resolve_db_path(self) -> None:
        """Find the conversations database path."""
        import os
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            from pathlib import Path
            db = Path(appdata) / "Specter" / "db" / "conversations.db"
            if db.exists():
                self._db_path = str(db)
                return
        logger.warning("Could not resolve conversations database path")

    def search_by_text(self, query: str, page: int = 0) -> List[Dict]:
        """
        Search messages by text content.

        Returns a paginated list of matching messages with timestamp,
        role, and content (truncated to 300 chars).
        """
        if not self._db_path or not query.strip():
            return []

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            offset = page * _PAGE_SIZE
            # Use LIKE for compatibility (FTS would be faster but may not exist)
            cursor.execute(
                """
                SELECT id, conversation_id, role, content, timestamp
                FROM messages
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (f"%{query}%", _PAGE_SIZE, offset),
            )

            results = []
            for row in cursor.fetchall():
                content = row["content"] or ""
                results.append({
                    "message_id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": content[:300],
                    "timestamp": row["timestamp"],
                })

            conn.close()
            logger.debug(f"Recall search '{query}' page={page}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Recall memory search failed: {e}")
            return []

    def search_by_date(
        self, start_date: str, end_date: str, page: int = 0
    ) -> List[Dict]:
        """
        Search messages within a date range.

        Dates should be ISO 8601 format (e.g., "2026-03-01").
        """
        if not self._db_path:
            return []

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            offset = page * _PAGE_SIZE
            cursor.execute(
                """
                SELECT id, conversation_id, role, content, timestamp
                FROM messages
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (start_date, end_date + "T23:59:59", _PAGE_SIZE, offset),
            )

            results = []
            for row in cursor.fetchall():
                content = row["content"] or ""
                results.append({
                    "message_id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": content[:300],
                    "timestamp": row["timestamp"],
                })

            conn.close()
            logger.debug(f"Recall date search {start_date}..{end_date} page={page}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Recall memory date search failed: {e}")
            return []

    def get_message_count(self) -> int:
        """Return total number of messages in the database."""
        if not self._db_path:
            return 0
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def format_results(self, results: List[Dict]) -> str:
        """Format search results as a readable string for the LLM."""
        if not results:
            return "No results found."
        lines = []
        for r in results:
            ts = r.get("timestamp", "?")
            role = r.get("role", "?")
            content = r.get("content", "")
            lines.append(f"[{ts}] {role}: {content}")
        return "\n".join(lines)
