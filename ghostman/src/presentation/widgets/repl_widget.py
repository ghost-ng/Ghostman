"""
REPL Widget for Ghostman.

Provides a Read-Eval-Print-Loop interface for interacting with the AI.
"""

import logging
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QColor, QPalette

logger = logging.getLogger("ghostman.repl_widget")


class REPLWidget(QWidget):
    """
    REPL interface for chat interaction with the AI.
    
    Features:
    - Command input with history
    - Scrollable output display
    - Support for multiline input
    - Command history navigation
    """
    
    # Signals
    command_entered = pyqtSignal(str)
    minimize_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_history: List[str] = []
        self.history_index = -1
        self.current_input = ""
        
        self._init_ui()
        self._setup_style()
        
        logger.info("REPLWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title bar
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Ghostman REPL")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        minimize_btn = QPushButton("_")
        minimize_btn.setMaximumSize(20, 20)
        minimize_btn.clicked.connect(self.minimize_requested.emit)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        title_layout.addWidget(minimize_btn)
        
        layout.addLayout(title_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2);")
        layout.addWidget(separator)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output_display, 1)
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Prompt label
        prompt_label = QLabel(">>>")
        prompt_label.setStyleSheet("color: #00ff00; font-family: Consolas; font-size: 11px;")
        input_layout.addWidget(prompt_label)
        
        # Command input
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont("Consolas", 10))
        self.command_input.returnPressed.connect(self._on_command_entered)
        self.command_input.installEventFilter(self)
        input_layout.addWidget(self.command_input)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._on_command_entered)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # Initial welcome message
        self.append_output("Ghostman REPL v1.0", "system")
        self.append_output("Type 'help' for available commands", "system")
        self.append_output("-" * 40, "system")
        
        # Focus on input
        self.command_input.setFocus()
    
    def _setup_style(self):
        """Setup the widget style."""
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.95);
                border-radius: 10px;
            }
            QTextEdit {
                background-color: rgba(20, 20, 20, 0.8);
                color: #f0f0f0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit {
                background-color: rgba(40, 40, 40, 0.8);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
    
    def eventFilter(self, obj, event):
        """Event filter for command input navigation."""
        if obj == self.command_input and event.type() == event.Type.KeyPress:
            key_event = event
            
            # Up arrow - previous command
            if key_event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            
            # Down arrow - next command
            elif key_event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        
        return super().eventFilter(obj, event)
    
    def _navigate_history(self, direction: int):
        """Navigate through command history."""
        if not self.command_history:
            return
        
        # Save current input if starting to navigate
        if self.history_index == -1:
            self.current_input = self.command_input.text()
        
        # Update index
        self.history_index += direction
        
        # Clamp index
        if self.history_index < -1:
            self.history_index = -1
        elif self.history_index >= len(self.command_history):
            self.history_index = len(self.command_history) - 1
        
        # Update input
        if self.history_index == -1:
            self.command_input.setText(self.current_input)
        else:
            self.command_input.setText(self.command_history[self.history_index])
    
    def _on_command_entered(self):
        """Handle command entry."""
        command = self.command_input.text().strip()
        
        if not command:
            return
        
        # Add to history
        if not self.command_history or command != self.command_history[-1]:
            self.command_history.append(command)
        
        # Reset history navigation
        self.history_index = -1
        self.current_input = ""
        
        # Display command in output
        self.append_output(f">>> {command}", "input")
        
        # Clear input
        self.command_input.clear()
        
        # Process command
        self._process_command(command)
        
        # Emit signal for external processing
        self.command_entered.emit(command)
    
    def _process_command(self, command: str):
        """Process built-in commands."""
        command_lower = command.lower()
        
        if command_lower == "help":
            self.append_output("Available commands:", "info")
            self.append_output("  help     - Show this help message", "info")
            self.append_output("  clear    - Clear the output display", "info")
            self.append_output("  history  - Show command history", "info")
            self.append_output("  exit     - Minimize to system tray", "info")
            self.append_output("  quit     - Exit the application", "info")
            self.append_output("\nAny other input will be sent to the AI assistant.", "info")
        
        elif command_lower == "clear":
            self.clear_output()
            self.append_output("Output cleared", "system")
        
        elif command_lower == "history":
            if self.command_history:
                self.append_output("Command history:", "info")
                for i, cmd in enumerate(self.command_history[-10:], 1):
                    self.append_output(f"  {i}. {cmd}", "info")
            else:
                self.append_output("No command history", "info")
        
        elif command_lower == "exit":
            self.minimize_requested.emit()
        
        elif command_lower == "quit":
            # Would need to connect to app quit
            self.append_output("Use system tray menu to quit application", "warning")
        
        else:
            # This would be sent to AI
            self.append_output("Processing with AI...", "system")
            # Placeholder for AI response
            QTimer.singleShot(500, lambda: self.append_output(
                f"AI: I received your message: '{command}'", "response"
            ))
    
    def append_output(self, text: str, style: str = "normal"):
        """
        Append text to the output display with styling.
        
        Args:
            text: Text to append
            style: Style type (normal, input, response, system, info, warning, error)
        """
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Set color based on style
        colors = {
            "normal": "#f0f0f0",
            "input": "#00ff00",
            "response": "#00bfff",
            "system": "#808080",
            "info": "#ffff00",
            "warning": "#ffa500",
            "error": "#ff0000"
        }
        
        color = colors.get(style, "#f0f0f0")
        
        # Insert formatted text
        cursor.insertHtml(f'<span style="color: {color};">{text}</span><br>')
        
        # Auto-scroll to bottom
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
    
    def clear_output(self):
        """Clear the output display."""
        self.output_display.clear()