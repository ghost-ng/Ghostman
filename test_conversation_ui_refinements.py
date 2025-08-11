"""
Test script for the refined Ghostman conversation management UI.

This script demonstrates the new clean, uncluttered interface features:
1. Clean REPL with styled prompt background
2. Avatar context menu with "Conversations" option
3. Simple conversation browser with restore/export functionality
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt

# Add the ghostman src to path
src_path = Path(__file__).parent / "ghostman" / "src"
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_conversation_ui")


class ConversationUITestWindow(QMainWindow):
    """Test window for demonstrating conversation UI refinements."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ghostman Conversation UI Refinements Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("Ghostman Conversation Management UI Test")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Test components info
        info_label = QLabel("""
        Refinements Implemented:
        
        ✅ 1. Clean REPL Interface:
           - Added background styling under ">>>" prompt
           - Removed toolbar icons for minimal design
           - Focused, uncluttered interface
        
        ✅ 2. Avatar Right-Click Menu:
           - Added "Conversations" option
           - Positioned as primary feature
           - Clean menu organization
        
        ✅ 3. Simple Conversation Browser:
           - Clean dark theme matching Ghostman
           - Essential actions only: Restore and Export
           - Shows current active conversation
           - Export supports TXT, JSON, Markdown formats
        
        ✅ 4. Integrated Actions:
           - Restore conversation to REPL
           - Export with format selection
           - Seamless database integration
        
        To test: Right-click on avatar → "Conversations"
        """)
        info_label.setStyleSheet("padding: 20px; background-color: #f0f0f0; border-radius: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Test buttons
        test_repl_btn = QPushButton("Test Clean REPL Interface")
        test_repl_btn.clicked.connect(self.test_repl)
        layout.addWidget(test_repl_btn)
        
        test_avatar_btn = QPushButton("Test Avatar Widget")
        test_avatar_btn.clicked.connect(self.test_avatar)
        layout.addWidget(test_avatar_btn)
        
        test_browser_btn = QPushButton("Test Simple Conversation Browser")
        test_browser_btn.clicked.connect(self.test_browser)
        layout.addWidget(test_browser_btn)
        
        # Apply styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
    
    def test_repl(self):
        """Test the clean REPL interface."""
        try:
            from presentation.widgets.floating_repl import FloatingREPLWindow
            
            # Create and show floating REPL
            self.repl_window = FloatingREPLWindow()
            self.repl_window.show()
            
            # Position next to test window
            test_pos = self.pos()
            self.repl_window.move(test_pos.x() + self.width() + 20, test_pos.y())
            
            logger.info("✅ Clean REPL interface displayed")
            
        except Exception as e:
            logger.error(f"❌ Failed to test REPL interface: {e}")
    
    def test_avatar(self):
        """Test the avatar widget with context menu."""
        try:
            from presentation.widgets.avatar_widget import AvatarWidget
            from PyQt6.QtWidgets import QDialog, QVBoxLayout
            
            # Create avatar test dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Avatar Widget Test")
            dialog.resize(200, 200)
            
            layout = QVBoxLayout(dialog)
            
            # Add avatar widget
            avatar = AvatarWidget()
            layout.addWidget(avatar)
            
            # Add instruction
            instruction = QLabel("Right-click avatar for context menu\nwith 'Conversations' option")
            instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
            instruction.setStyleSheet("padding: 10px; color: #666;")
            layout.addWidget(instruction)
            
            dialog.show()
            
            logger.info("✅ Avatar widget with conversations menu displayed")
            
        except Exception as e:
            logger.error(f"❌ Failed to test avatar widget: {e}")
    
    def test_browser(self):
        """Test the simple conversation browser."""
        try:
            # Import conversation components
            from infrastructure.conversation_management.integration.conversation_manager import ConversationManager
            from infrastructure.conversation_management.ui.simple_conversation_browser import SimpleConversationBrowser
            
            # Initialize conversation manager
            conv_manager = ConversationManager()
            if not conv_manager.initialize():
                logger.warning("Conversation manager not available - showing empty browser")
                conv_manager = None
            
            # Create and show browser
            self.browser = SimpleConversationBrowser(conv_manager, parent=self)
            self.browser.show()
            
            logger.info("✅ Simple conversation browser displayed")
            
        except Exception as e:
            logger.error(f"❌ Failed to test conversation browser: {e}")
            # Show a mock version
            self._show_mock_browser()
    
    def _show_mock_browser(self):
        """Show a mock browser for demonstration."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Simple Conversation Browser (Mock)")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        mock_label = QLabel("""
        Simple Conversation Browser Features:
        
        🎨 Clean Dark Theme
        📋 Conversation List with:
           - Title, Status, Messages, Updated Time
           - Current active conversation highlighted
        
        🔧 Essential Actions:
           - Restore to REPL
           - Export (TXT, JSON, Markdown)
        
        💾 Database Integration:
           - Loads from SQLite
           - Shows real conversation data
           - Background operations
        
        This is a mock view - actual browser
        would show your conversation data.
        """)
        
        mock_label.setStyleSheet("""
            background-color: rgba(30, 30, 30, 0.95);
            color: #f0f0f0;
            padding: 30px;
            border-radius: 5px;
            font-family: monospace;
        """)
        mock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(mock_label)
        dialog.show()
        
        logger.info("✅ Mock conversation browser displayed")


def main():
    """Main test function."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
    # Create and show test window
    test_window = ConversationUITestWindow()
    test_window.show()
    
    logger.info("🚀 Ghostman Conversation UI Refinements Test Started")
    logger.info("Click buttons to test individual components")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())