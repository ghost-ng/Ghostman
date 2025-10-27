"""
Test script to check if messages are being saved to conversations.

This script queries the database to check message counts in conversations.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_message_saving():
    """Check if messages are being saved in the database."""
    try:
        from ghostman.src.infrastructure.conversation_management.services.conversation_service import ConversationService
        from ghostman.src.infrastructure.conversation_management.repositories.conversation_repository import ConversationRepository
        from ghostman.src.infrastructure.conversation_management.repositories.database import DatabaseManager

        # Initialize database
        db_manager = DatabaseManager()

        # Initialize repository and service
        repo = ConversationRepository(db_manager)
        service = ConversationService(repo)

        logger.info("=" * 80)
        logger.info("CONVERSATION MESSAGE COUNT TEST")
        logger.info("=" * 80)

        # Get all conversations
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            conversations = loop.run_until_complete(service.list_conversations())

            logger.info(f"\nFound {len(conversations)} conversations:\n")

            for i, conv in enumerate(conversations, 1):
                # Get full conversation with messages
                full_conv = loop.run_until_complete(service.get_conversation(conv.id, include_messages=True))

                if full_conv:
                    message_count = len(full_conv.messages) if full_conv.messages else 0
                    cached_count = full_conv._message_count if hasattr(full_conv, '_message_count') else 'N/A'

                    logger.info(f"{i}. Conversation: {conv.id[:8]}...")
                    logger.info(f"   Title: {conv.title}")
                    logger.info(f"   Status: {conv.status}")
                    logger.info(f"   Created: {conv.created_at}")
                    logger.info(f"   Updated: {conv.updated_at}")
                    logger.info(f"   Messages (from DB): {message_count}")
                    logger.info(f"   Cached count: {cached_count}")

                    if message_count > 0:
                        logger.info(f"   ✓ HAS MESSAGES")
                        for j, msg in enumerate(full_conv.messages[:5], 1):  # Show first 5 messages
                            preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                            logger.info(f"     Message {j} [{msg.role}]: {preview}")
                        if message_count > 5:
                            logger.info(f"     ... and {message_count - 5} more messages")
                    else:
                        logger.info(f"   ✗ NO MESSAGES FOUND")

                    logger.info("")

            logger.info("=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)

            convs_with_messages = sum(1 for c in conversations if len(loop.run_until_complete(service.get_conversation(c.id, include_messages=True)).messages) > 0)
            convs_without_messages = len(conversations) - convs_with_messages

            logger.info(f"Total conversations: {len(conversations)}")
            logger.info(f"Conversations with messages: {convs_with_messages}")
            logger.info(f"Conversations without messages: {convs_without_messages}")

            if convs_without_messages > 0:
                logger.warning("\n⚠ WARNING: Some conversations have NO messages!")
                logger.warning("This indicates messages are not being saved to the database.")
                logger.warning("Check the application logs for '💾' to see save attempts.")
            else:
                logger.info("\n✓ All conversations have messages saved correctly!")

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error checking message saving: {e}", exc_info=True)

if __name__ == "__main__":
    test_message_saving()
