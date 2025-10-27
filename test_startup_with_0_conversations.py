"""
Test script to debug startup crash with 0 conversations.

This script will:
1. Clear all conversations from the database
2. Start the app with detailed logging
3. Help identify where the hang/crash occurs
"""

import sys
import os
import logging
from pathlib import Path

# Add Ghostman to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up enhanced logging before importing ghostman
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('startup_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def clear_all_conversations():
    """Clear all conversations from the database."""
    logger.info("="*80)
    logger.info("STEP 1: Clearing all conversations from database")
    logger.info("="*80)

    try:
        from ghostman.src.infrastructure.conversation_management.repositories.database import ConversationDatabase
        from ghostman.src.infrastructure.conversation_management.repositories.conversation_repository import ConversationRepository
        import asyncio

        # Initialize database
        db = ConversationDatabase()
        if not db.initialize():
            logger.error("Failed to initialize database")
            return False

        repo = ConversationRepository(db)

        # Get all conversations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        conversations = loop.run_until_complete(repo.list_conversations(include_deleted=True, limit=None))
        logger.info(f"Found {len(conversations)} conversations in database")

        # Delete all conversations (hard delete)
        for conv in conversations:
            logger.info(f"Deleting conversation: {conv.id[:8]}... - {conv.title}")
            success = loop.run_until_complete(repo.delete_conversation(conv.id, soft_delete=False))
            if success:
                logger.info(f"  ✓ Deleted: {conv.id[:8]}")
            else:
                logger.error(f"  ✗ Failed to delete: {conv.id[:8]}")

        # Verify deletion
        remaining = loop.run_until_complete(repo.list_conversations(include_deleted=True, limit=None))
        logger.info(f"Remaining conversations: {len(remaining)}")

        loop.close()

        if len(remaining) == 0:
            logger.info("✓ All conversations successfully deleted")
            return True
        else:
            logger.warning(f"⚠ {len(remaining)} conversations remaining after deletion")
            return False

    except Exception as e:
        logger.error(f"Failed to clear conversations: {e}", exc_info=True)
        return False

def start_app_with_monitoring():
    """Start the app with detailed monitoring."""
    logger.info("="*80)
    logger.info("STEP 2: Starting Ghostman with monitoring")
    logger.info("="*80)

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        import signal

        # Create QApplication
        app = QApplication(sys.argv)
        logger.info("✓ QApplication created")

        # Set up watchdog timer to detect hangs
        hang_detected = [False]
        last_checkpoint = ["startup"]

        def watchdog_check():
            """Check if app is still responding."""
            if not hang_detected[0]:
                logger.info(f"⏱ Watchdog: App is responding (last checkpoint: {last_checkpoint[0]})")
                QTimer.singleShot(2000, watchdog_check)  # Check every 2 seconds

        QTimer.singleShot(2000, watchdog_check)
        logger.info("✓ Watchdog timer started")

        # Import and initialize Ghostman
        logger.info("Importing Ghostman modules...")
        from ghostman.src.application.app_coordinator import AppCoordinator
        from ghostman.src.infrastructure.storage.settings_manager import settings

        logger.info("✓ Imports successful")
        last_checkpoint[0] = "imports"

        # Create app coordinator
        logger.info("Creating AppCoordinator...")
        coordinator = AppCoordinator()
        logger.info("✓ AppCoordinator created")
        last_checkpoint[0] = "coordinator_created"

        # Initialize app
        logger.info("Initializing application...")
        if not coordinator.initialize(settings):
            logger.error("✗ Failed to initialize application")
            return False
        logger.info("✓ Application initialized")
        last_checkpoint[0] = "initialized"

        # Show app
        logger.info("Showing application...")
        coordinator.show()
        logger.info("✓ Application shown")
        last_checkpoint[0] = "shown"

        # Set up signal handler for clean shutdown
        def signal_handler(sig, frame):
            logger.info("Interrupt received, shutting down...")
            hang_detected[0] = True
            app.quit()

        signal.signal(signal.SIGINT, signal_handler)

        # Start event loop
        logger.info("Starting Qt event loop...")
        logger.info("="*80)
        logger.info("APP IS RUNNING - Press Ctrl+C to stop")
        logger.info("="*80)
        last_checkpoint[0] = "event_loop_started"

        exit_code = app.exec()
        logger.info(f"App exited with code: {exit_code}")
        return True

    except Exception as e:
        logger.error(f"Failed to start app: {e}", exc_info=True)
        hang_detected[0] = True
        return False

def main():
    """Main test function."""
    logger.info("="*80)
    logger.info("GHOSTMAN STARTUP DEBUG TEST")
    logger.info("Testing startup with 0 conversations in database")
    logger.info("="*80)

    # Step 1: Clear all conversations
    if not clear_all_conversations():
        logger.error("Failed to clear conversations, aborting test")
        return 1

    logger.info("")
    input("Press Enter to start the app...")
    logger.info("")

    # Step 2: Start app with monitoring
    if not start_app_with_monitoring():
        logger.error("App failed to start or hang detected")
        return 1

    logger.info("="*80)
    logger.info("TEST COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
