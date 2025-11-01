"""
Main Entry Point for Ghostman Application.

Initializes the PyQt6 application, sets up logging, and starts the app coordinator.
"""

import sys
import os
import logging
import argparse
import signal
import atexit
from typing import Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ghostman.src.infrastructure.logging.logging_config import setup_logging, get_performance_logger
from ghostman.src.application.app_coordinator import AppCoordinator

logger = logging.getLogger("ghostman.main")
perf_logger = get_performance_logger()


class GhostmanApplication:
    """
    Main application class that manages the Qt application lifecycle.
    """
    
    def __init__(self):
        self.app: Optional[QApplication] = None
        self.coordinator: Optional[AppCoordinator] = None
        self._setup_signal_handlers()
    
    def setup_qt_application(self) -> QApplication:
        """Setup and configure the Qt application."""
        # Enable high DPI scaling (if available)
        try:
            from PyQt6.QtCore import Qt
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except (AttributeError, ImportError):
            logger.debug("High DPI scaling attributes not available")
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("GhostmanApp")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Ghostman")
        app.setQuitOnLastWindowClosed(False)  # Keep running when main window closes
        
        # Set up Qt message handling to suppress CSS warnings unless in debug mode
        self._setup_qt_message_handler()
        
        # Set application icon (if available)
        try:
            # Try avatar first, then icon
            avatar_path = os.path.join(os.path.dirname(__file__), "..", "assets", "avatar.png")
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
            
            if os.path.exists(avatar_path):
                app.setWindowIcon(QIcon(avatar_path))
            elif os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            logger.debug(f"Could not load application icon: {e}")
        
        logger.info("Qt application configured")
        return app
    
    def _setup_qt_message_handler(self):
        """Setup Qt message handler to suppress CSS warnings unless in debug mode."""
        try:
            from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
            
            # Check if we're in debug mode
            debug_mode = False
            try:
                from ghostman.src.infrastructure.storage.settings_manager import settings
                log_mode = settings.get("advanced.log_level", "Standard")
                debug_mode = (log_mode == "Detailed")
            except Exception:
                # If we can't check settings, assume not debug
                pass
            
            def qt_message_handler(msg_type, context, message):
                """Custom Qt message handler to filter CSS warnings."""
                # Suppress CSS property warnings unless in debug mode
                if not debug_mode and "Unknown property" in message and "cursor" in message:
                    return  # Suppress this message
                
                # Suppress other common Qt warnings that aren't useful in production
                if not debug_mode:
                    suppress_keywords = ["Unknown property", "QPixmap::scaled", "Qt::AA_EnableHighDpiScaling"]
                    if any(keyword in message for keyword in suppress_keywords):
                        return
                
                # Convert Qt message type to Python logging
                if msg_type == QtMsgType.QtDebugMsg:
                    if debug_mode:
                        logger.debug(f"Qt: {message}")
                elif msg_type == QtMsgType.QtInfoMsg:
                    logger.info(f"Qt: {message}")  
                elif msg_type == QtMsgType.QtWarningMsg:
                    if debug_mode:
                        logger.warning(f"Qt: {message}")
                elif msg_type == QtMsgType.QtCriticalMsg:
                    logger.error(f"Qt Critical: {message}")
                elif msg_type == QtMsgType.QtFatalMsg:
                    logger.critical(f"Qt Fatal: {message}")
            
            qInstallMessageHandler(qt_message_handler)
            logger.debug("Qt message handler installed")
            
        except ImportError:
            logger.debug("Could not install Qt message handler - PyQt6 not available")
        except Exception as e:
            logger.debug(f"Failed to install Qt message handler: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if self.coordinator:
                self.coordinator.shutdown()
            sys.exit(0)
        
        def cleanup_handler():
            """Final cleanup on exit."""
            logger.debug("Performing final cleanup on exit...")
            if self.coordinator:
                self.coordinator.shutdown()
        
        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            if hasattr(signal, 'SIGHUP'):  # Unix only
                signal.signal(signal.SIGHUP, signal_handler)
            
            # Register atexit handler as final fallback
            atexit.register(cleanup_handler)
            
            logger.debug("Signal handlers registered for graceful shutdown")
        except Exception as e:
            logger.debug(f"Could not register signal handlers: {e}")
    
    def initialize_coordinator(self) -> bool:
        """Initialize the application coordinator."""
        try:
            self.coordinator = AppCoordinator()
            
            # Connect application shutdown signal
            self.coordinator.app_shutdown.connect(self.app.quit)
            
            # Initialize the coordinator
            if not self.coordinator.initialize():
                logger.error("Failed to initialize app coordinator")
                return False
            
            logger.info("App coordinator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing coordinator: {e}")
            return False
    
    def run(self) -> int:
        """
        Run the Ghostman application.
        
        Returns:
            Exit code (0 for success)
        """
        try:
            logger.info("Starting Ghostman application...")
            
            # Setup Qt application
            self.app = self.setup_qt_application()

            # Initialize coordinator
            if not self.initialize_coordinator():
                logger.error("Failed to initialize application")
                return 1

            # Make coordinator accessible from QApplication for widgets
            self.app.coordinator = self.coordinator
            
            # Start in tray mode
            self.coordinator.start_in_tray_mode()
            
            # Show system tray notification (if implemented)
            logger.info("Ghostman started successfully - running in system tray")
            
            # Start the Qt event loop
            exit_code = self.app.exec()
            
            logger.info(f"Application exited with code: {exit_code}")
            return exit_code
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            return 0
        except Exception as e:
            logger.error(f"Unhandled exception in main application: {e}", exc_info=True)
            return 1
        finally:
            # Cleanup
            if self.coordinator:
                self.coordinator.shutdown()


def erase_all_local_data():
    """
    Erase all Ghostman local data (AppData on Windows, ~ on Linux/Mac).

    This removes:
    - All configuration files
    - All database files
    - All RAG data
    - All PKI certificates
    - All logs
    """
    import shutil
    from pathlib import Path

    print("=" * 60)
    print("GHOSTMAN DATA ERASURE")
    print("=" * 60)
    print("\nThis will delete ALL Ghostman data including:")
    print("  - Configuration files")
    print("  - Conversation history")
    print("  - RAG documents")
    print("  - PKI certificates")
    print("  - All logs")
    print("\nThis action CANNOT be undone!")
    print("=" * 60)

    # Ask for confirmation
    confirmation = input("\nType 'DELETE' to confirm: ").strip()
    if confirmation != "DELETE":
        print("Aborted - no data was deleted")
        return False

    print("\nErasing data...")

    # Get data directories based on platform
    if sys.platform == "win32":
        # Windows: %APPDATA%\Ghostman
        appdata = os.environ.get('APPDATA')
        if appdata:
            data_dirs = [Path(appdata) / "Ghostman"]
        else:
            print("ERROR: Could not find APPDATA environment variable")
            return False
    else:
        # Linux/Mac: ~/.Ghostman
        home = Path.home()
        data_dirs = [home / ".Ghostman", home / ".ghostman"]

    # Delete each directory
    deleted_count = 0
    for data_dir in data_dirs:
        if data_dir.exists():
            try:
                print(f"  Removing: {data_dir}")
                shutil.rmtree(data_dir)
                deleted_count += 1
                print(f"    ✓ Deleted")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        else:
            print(f"  Skipping: {data_dir} (not found)")

    print("\n" + "=" * 60)
    if deleted_count > 0:
        print(f"✓ Successfully deleted {deleted_count} data director{'y' if deleted_count == 1 else 'ies'}")
        print("Ghostman will start fresh on next run")
    else:
        print("No data directories found to delete")
    print("=" * 60)

    return True


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Ghostman - AI Desktop Assistant")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        help="Custom directory for log files"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Ghostman 1.0.0"
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Erase all local data and start fresh (removes AppData/~ files)"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()

    # Handle --new flag (erase all data and exit)
    if args.new:
        if erase_all_local_data():
            print("\nGhostman data has been erased.")
            print("Run Ghostman normally to start fresh.")
            return 0
        else:
            return 1

    # Setup logging - check settings for detailed mode first
    debug_mode = args.debug
    log_retention_days = 10  # default
    custom_log_dir = None
    try:
        from ghostman.src.infrastructure.storage.settings_manager import settings
        log_mode = settings.get("advanced.log_level", "Standard")
        if log_mode == "Detailed":
            debug_mode = True
        
        # Load log retention days
        log_retention_days = settings.get("advanced.log_retention_days", 10)
        if not isinstance(log_retention_days, int) or log_retention_days < 1:
            log_retention_days = 10
        
        # Load custom log location (override CLI arg if set in config)
        config_log_location = settings.get("advanced.log_location", "").strip()
        if config_log_location and not args.log_dir:  # Only use config if CLI not specified
            custom_log_dir = config_log_location
            
    except Exception:
        pass  # Use defaults if settings unavailable
    
    # Use CLI log_dir if specified, otherwise use config log location, otherwise use default
    final_log_dir = args.log_dir or custom_log_dir
    
    setup_logging(debug=debug_mode, log_dir=final_log_dir, retention_days=log_retention_days)
    
    logger.info("=" * 60)
    logger.info("GHOSTMAN APPLICATION STARTING")
    logger.info("=" * 60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Debug mode: {debug_mode} (CLI: {args.debug})")
    
    # Create and run application
    app = GhostmanApplication()
    exit_code = app.run()
    
    logger.info("=" * 60)
    logger.info("GHOSTMAN APPLICATION SHUTDOWN")
    logger.info("=" * 60)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()