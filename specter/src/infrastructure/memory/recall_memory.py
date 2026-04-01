"""
Recall Memory Service for the MemGPT-style memory system.

Provides searchable access to the full conversation history using
the existing SQLAlchemy models and DatabaseManager singleton.
Supports text search and date-range queries with pagination.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("specter.memory.recall")

_PAGE_SIZE = 5


class RecallMemoryService:
    """
    Searchable conversation history using the existing SQLAlchemy ORM.

    Uses ``DatabaseManager`` (singleton) and ``MessageModel`` to query
    the conversations database without raw SQL.
    """

    def __init__(self):
        self._db_manager = None

    def _ensure_db(self) -> bool:
        """Lazy-initialize the database manager."""
        if self._db_manager is not None:
            return True
        try:
            from ..conversation_management.repositories.database import DatabaseManager
            self._db_manager = DatabaseManager()
            self._db_manager.initialize()
            return True
        except Exception as e:
            logger.warning(f"Could not initialize database for recall memory: {e}")
            return False

    def search_by_text(self, query: str, page: int = 0) -> List[Dict]:
        """
        Search messages by text content using SQLAlchemy LIKE.

        Returns paginated results with timestamp, role, and content.
        """
        if not query.strip() or not self._ensure_db():
            return []

        try:
            from ..conversation_management.models.database_models import MessageModel

            session = self._db_manager.get_session()
            try:
                offset = page * _PAGE_SIZE
                rows = (
                    session.query(MessageModel)
                    .filter(MessageModel.content.ilike(f"%{query}%"))
                    .order_by(MessageModel.timestamp.desc())
                    .limit(_PAGE_SIZE)
                    .offset(offset)
                    .all()
                )

                results = []
                for row in rows:
                    content = row.content or ""
                    results.append({
                        "message_id": row.id,
                        "conversation_id": row.conversation_id,
                        "role": row.role,
                        "content": content[:300],
                        "timestamp": str(row.timestamp) if row.timestamp else "",
                    })
            finally:
                session.close()

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
        if not self._ensure_db():
            return []

        try:
            from ..conversation_management.models.database_models import MessageModel

            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)

            session = self._db_manager.get_session()
            try:
                offset = page * _PAGE_SIZE
                rows = (
                    session.query(MessageModel)
                    .filter(
                        MessageModel.timestamp >= start_dt,
                        MessageModel.timestamp <= end_dt,
                    )
                    .order_by(MessageModel.timestamp.desc())
                    .limit(_PAGE_SIZE)
                    .offset(offset)
                    .all()
                )

                results = []
                for row in rows:
                    content = row.content or ""
                    results.append({
                        "message_id": row.id,
                        "conversation_id": row.conversation_id,
                        "role": row.role,
                        "content": content[:300],
                        "timestamp": str(row.timestamp) if row.timestamp else "",
                    })
            finally:
                session.close()

            logger.debug(f"Recall date search {start_date}..{end_date} page={page}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Recall memory date search failed: {e}")
            return []

    def get_message_count(self) -> int:
        """Return total number of messages in the database."""
        if not self._ensure_db():
            return 0
        try:
            from ..conversation_management.models.database_models import MessageModel
            from sqlalchemy import func

            session = self._db_manager.get_session()
            try:
                count = session.query(func.count(MessageModel.id)).scalar() or 0
            finally:
                session.close()
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
