"""
Simple, bulletproof conversation status management.
No complex logic, just works.
"""

import logging
from typing import Optional
from sqlalchemy import text
from ..models.enums import ConversationStatus
from ..repositories.database import DatabaseManager

logger = logging.getLogger("ghostman.simple_status")


class SimpleStatusService:
    """Dead simple status management - just works."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def set_conversation_active(self, conversation_id: str) -> bool:
        """
        Make one conversation active, all others pinned.
        Simple, atomic, bulletproof.
        """
        try:
            with self.db.get_session() as session:
                # Step 1: Set ALL conversations to pinned (except deleted/archived)
                session.execute(text("""
                    UPDATE conversations 
                    SET status = 'pinned', updated_at = CURRENT_TIMESTAMP
                    WHERE status NOT IN ('deleted', 'archived')
                """))
                
                # Step 2: Set target conversation to active
                result = session.execute(text("""
                    UPDATE conversations 
                    SET status = 'active', updated_at = CURRENT_TIMESTAMP
                    WHERE id = :conv_id
                """), {"conv_id": conversation_id})
                
                session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"✅ Set conversation {conversation_id[:8]}... as ACTIVE")
                    return True
                else:
                    logger.warning(f"⚠️  Conversation {conversation_id} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to set conversation active: {e}")
            return False
    
    def get_active_conversation_id(self) -> Optional[str]:
        """Get the ID of the currently active conversation."""
        try:
            with self.db.get_session() as session:
                result = session.execute(text("""
                    SELECT id FROM conversations 
                    WHERE status = 'active' 
                    ORDER BY updated_at DESC 
                    LIMIT 1
                """))
                
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"❌ Failed to get active conversation: {e}")
            return None
    
    def get_conversation_status(self, conversation_id: str) -> Optional[ConversationStatus]:
        """Get status of a specific conversation."""
        try:
            with self.db.get_session() as session:
                result = session.execute(text("""
                    SELECT status FROM conversations 
                    WHERE id = :conv_id
                """), {"conv_id": conversation_id})
                
                row = result.fetchone()
                if row:
                    return ConversationStatus(row[0])
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversation status: {e}")
            return None
    
    def count_conversations_by_status(self) -> dict:
        """Debug helper: count conversations by status."""
        try:
            with self.db.get_session() as session:
                result = session.execute(text("""
                    SELECT status, COUNT(*) as count 
                    FROM conversations 
                    GROUP BY status
                """))
                
                return {row[0]: row[1] for row in result.fetchall()}
                
        except Exception as e:
            logger.error(f"❌ Failed to count conversations: {e}")
            return {}