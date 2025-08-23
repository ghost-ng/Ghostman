#!/usr/bin/env python3
"""
Comprehensive Search Bar Border Debug Tool for Ghostman

This tool will help identify the exact source of the persistent border on the search bar.
It systematically checks all possible sources of borders and styling.
"""

import sys
import logging
from pathlib import Path

# Add the ghostman directory to Python path
ghostman_root = Path(__file__).parent / "ghostman"
sys.path.insert(0, str(ghostman_root))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFrame, QLineEdit, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SearchBorderDebugger(QMainWindow):
    """Debug tool to identify search border issues."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Border Debug Tool")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test different search bar configurations
        self.create_test_scenarios(layout)
    
    def create_test_scenarios(self, parent_layout):
        """Create various test scenarios to identify border sources."""
        
        # Scenario 1: Minimal QLineEdit with no styling
        self.add_test_section(parent_layout, "1. Minimal QLineEdit (Qt Default)")
        frame1 = QFrame()
        layout1 = QHBoxLayout(frame1)
        
        search_input1 = QLineEdit()
        search_input1.setPlaceholderText("Default Qt styling...")
        layout1.addWidget(QLabel("🔍"))
        layout1.addWidget(search_input1)
        parent_layout.addWidget(frame1)
        
        # Scenario 2: QLineEdit with comprehensive border removal
        self.add_test_section(parent_layout, "2. QLineEdit with Comprehensive Border Removal")
        frame2 = QFrame()
        layout2 = QHBoxLayout(frame2)
        
        search_input2 = QLineEdit()
        search_input2.setPlaceholderText("Comprehensive border removal...")
        search_input2.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none !important;
                border-width: 0px !important;
                border-style: none !important;
                border-color: transparent !important;
                outline: none !important;
                box-shadow: none !important;
                padding: 4px 6px;
                border-radius: 3px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: none !important;
                outline: none !important;
                background-color: #4a4a4a;
            }
            QLineEdit:hover {
                border: none !important;
                outline: none !important;
            }
        """)
        layout2.addWidget(QLabel("🔍"))
        layout2.addWidget(search_input2)
        parent_layout.addWidget(frame2)
        
        # Scenario 3: Frame with border removal
        self.add_test_section(parent_layout, "3. Frame with Border Removal")
        frame3 = QFrame()
        frame3.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border: none !important;
                border-width: 0px !important;
                border-style: none !important;
                border-color: transparent !important;
                border-radius: 4px;
                padding: 4px;
                outline: none !important;
                box-shadow: none !important;
            }
            QFrame:focus {
                border: none !important;
                outline: none !important;
            }
        """)
        layout3 = QHBoxLayout(frame3)
        
        search_input3 = QLineEdit()
        search_input3.setPlaceholderText("Frame and input both no border...")
        search_input3.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #ffffff;
                border: none !important;
                border-width: 0px !important;
                border-style: none !important;
                border-color: transparent !important;
                outline: none !important;
                box-shadow: none !important;
                padding: 4px 6px;
                font-size: 11px;
            }
        """)
        layout3.addWidget(QLabel("🔍"))
        layout3.addWidget(search_input3)
        parent_layout.addWidget(frame3)
        
        # Scenario 4: Check system palette influence
        self.add_test_section(parent_layout, "4. System Palette Override Test")
        frame4 = QFrame()
        layout4 = QHBoxLayout(frame4)
        
        search_input4 = QLineEdit()
        search_input4.setPlaceholderText("Palette override test...")
        
        # Override system palette
        palette = search_input4.palette()
        palette.setBrush(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        palette.setBrush(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        search_input4.setPalette(palette)
        
        search_input4.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
                padding: 4px 6px;
                border-radius: 3px;
            }
        """)
        layout4.addWidget(QLabel("🔍"))
        layout4.addWidget(search_input4)
        parent_layout.addWidget(frame4)
        
        # Scenario 5: Test with setFrame(False)
        self.add_test_section(parent_layout, "5. QLineEdit with setFrame(False)")
        frame5 = QFrame()
        layout5 = QHBoxLayout(frame5)
        
        search_input5 = QLineEdit()
        search_input5.setPlaceholderText("Frame disabled...")
        search_input5.setFrame(False)  # Disable the frame entirely
        search_input5.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none !important;
                padding: 4px 6px;
                border-radius: 3px;
            }
        """)
        layout5.addWidget(QLabel("🔍"))
        layout5.addWidget(search_input5)
        parent_layout.addWidget(frame5)
        
        # Scenario 6: Test focus policy
        self.add_test_section(parent_layout, "6. Focus Policy Test")
        frame6 = QFrame()
        layout6 = QHBoxLayout(frame6)
        
        search_input6 = QLineEdit()
        search_input6.setPlaceholderText("No focus policy...")
        search_input6.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Different focus policy
        search_input6.setFrame(False)
        search_input6.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none !important;
                padding: 4px 6px;
                border-radius: 3px;
            }
        """)
        layout6.addWidget(QLabel("🔍"))
        layout6.addWidget(search_input6)
        parent_layout.addWidget(frame6)
        
        # Print debug information
        self.print_debug_info()
    
    def add_test_section(self, layout, title):
        """Add a test section label."""
        label = QLabel(f"<b>{title}</b>")
        label.setStyleSheet("color: #ffffff; background-color: #2a2a2a; padding: 5px; margin-top: 10px;")
        layout.addWidget(label)
    
    def print_debug_info(self):
        """Print debugging information."""
        logger.info("=== Search Border Debug Information ===")
        logger.info(f"Qt Version: {QApplication.instance().applicationVersion()}")
        logger.info(f"Style: {QApplication.instance().style().objectName()}")
        
        # Check if there are any global stylesheets
        app_stylesheet = QApplication.instance().styleSheet()
        if app_stylesheet:
            logger.info(f"Application stylesheet detected: {len(app_stylesheet)} characters")
        else:
            logger.info("No application-level stylesheet detected")

def main():
    """Run the debug tool."""
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1a1a1a;
            color: #ffffff;
        }
    """)
    
    debugger = SearchBorderDebugger()
    debugger.show()
    
    print("\n" + "="*60)
    print("SEARCH BORDER DEBUG TOOL")
    print("="*60)
    print("This tool shows 6 different search input configurations.")
    print("Compare them to identify which approach eliminates the border.")
    print("Pay attention to:")
    print("- Visual borders around inputs")
    print("- Focus indicators")
    print("- Background/foreground contrast")
    print("="*60)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()