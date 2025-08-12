"""
Test script for the frameless window resize system.

This script provides basic validation and testing for the resize components.
"""

import sys
import logging
from typing import Optional
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("resize_test")


class TestWidget(QWidget):
    """Simple test widget for validating resize functionality."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_resize()
        
    def init_ui(self):
        """Initialize the test UI."""
        self.setWindowTitle("Resize System Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Make window frameless
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Create layout
        layout = QVBoxLayout()
        
        # Title label
        title = QLabel("Frameless Window Resize Test")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info label
        info = QLabel(
            "This is a test window for the frameless resize system.\n\n"
            "Try resizing by dragging the edges and corners:\n"
            "• Move cursor to edges to see resize cursors\n"
            "• Drag to resize the window\n"
            "• Size constraints should be enforced"
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Status label
        self.status_label = QLabel("Resize system initializing...")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        self.toggle_resize_btn = QPushButton("Disable Resize")
        self.toggle_resize_btn.clicked.connect(self.toggle_resize)
        button_layout.addWidget(self.toggle_resize_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Style the window
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
                border: 2px solid #555;
            }
            QLabel {
                border: none;
                padding: 10px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px;
                margin: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
    def setup_resize(self):
        """Setup resize functionality."""
        try:
            from . import add_resize_to_widget, SizeConstraints
            
            # Create constraints for testing
            constraints = SizeConstraints(
                min_width=200,
                min_height=150,
                max_width=800,
                max_height=600
            )
            
            # Add resize functionality
            self.resize_manager = add_resize_to_widget(
                self,
                constraints=constraints,
                config={'border_width': 10, 'enable_cursor_changes': True}
            )
            
            # Connect signals
            if hasattr(self.resize_manager, 'resize_started'):
                self.resize_manager.resize_started.connect(self.on_resize_started)
            if hasattr(self.resize_manager, 'resize_finished'):
                self.resize_manager.resize_finished.connect(self.on_resize_finished)
            
            self.resize_enabled = True
            self.status_label.setText("✅ Resize system active")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            logger.info("Resize system initialized successfully")
            
        except Exception as e:
            self.status_label.setText(f"❌ Resize system failed: {e}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            logger.error(f"Failed to initialize resize system: {e}")
            self.resize_manager = None
            self.resize_enabled = False
    
    def toggle_resize(self):
        """Toggle resize functionality."""
        if not self.resize_manager:
            return
            
        try:
            if self.resize_enabled:
                self.resize_manager.set_enabled(False)
                self.toggle_resize_btn.setText("Enable Resize")
                self.status_label.setText("⏸️ Resize disabled")
                self.status_label.setStyleSheet("color: orange; font-weight: bold;")
                self.resize_enabled = False
            else:
                self.resize_manager.set_enabled(True)
                self.toggle_resize_btn.setText("Disable Resize")
                self.status_label.setText("✅ Resize system active")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.resize_enabled = True
                
        except Exception as e:
            logger.error(f"Failed to toggle resize: {e}")
    
    def on_resize_started(self, zone):
        """Handle resize started."""
        zone_name = zone.value if hasattr(zone, 'value') else str(zone)
        self.status_label.setText(f"🔄 Resizing from {zone_name}")
        self.status_label.setStyleSheet("color: cyan; font-weight: bold;")
        logger.debug(f"Resize started in zone: {zone_name}")
    
    def on_resize_finished(self, zone, width, height):
        """Handle resize finished."""
        zone_name = zone.value if hasattr(zone, 'value') else str(zone)
        self.status_label.setText(f"✅ Resize complete ({width}x{height})")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        logger.debug(f"Resize finished: {zone_name} -> {width}x{height}")
        
        # Reset status after a delay
        QTimer.singleShot(2000, lambda: self.status_label.setText("✅ Resize system active"))
    
    def closeEvent(self, event):
        """Handle close event."""
        if self.resize_manager:
            try:
                self.resize_manager.cleanup()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")
        super().closeEvent(event)


def main():
    """Run the resize system test."""
    app = QApplication(sys.argv)
    
    # Create and show test widget
    test_widget = TestWidget()
    test_widget.show()
    
    logger.info("Resize system test started")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()