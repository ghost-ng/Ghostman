"""Main prompt and response interface window."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QTextCursor, QColor
from ui.components.overlay_base import OverlayBaseWindow
import logging
from typing import List, Optional

class MessageWidget(QFrame):
    """Individual message display widget."""
    
    def __init__(self, message: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_user = is_user
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the message UI."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        # Default colors (will be overridden by theme)
        user_color = "rgba(70, 130, 180, 180)" if self.is_user else "rgba(60, 60, 60, 180)"
        border_color = "rgba(135, 206, 235, 120)" if self.is_user else "rgba(120, 120, 120, 120)"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {user_color};
                border: 1px solid {border_color};
                border-radius: 12px;
                margin: 8px;
                padding: 0px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        # Message text
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            QLabel {{
                color: {'white' if self.is_user else '#e8e8e8'};
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
                line-height: 1.4;
                background-color: transparent;
                border: none;
            }}
        """)
        
        # Header with role
        role_label = QLabel("You:" if self.is_user else "AI:")
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {'#87CEEB' if self.is_user else '#FFB347'};
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                background-color: transparent;
                border: none;
                margin-bottom: 6px;
            }}
        """)
        
        layout.addWidget(role_label)
        layout.addWidget(message_label)
    
    def apply_theme_colors(self, colors, fonts, spacing):
        """Apply theme colors to this message widget."""
        try:
            # Choose colors based on message type
            if self.is_user:
                bg_color = colors.user_message_bg
                text_color = colors.user_message_text
                role_color = colors.accent
                border_color = colors.border_hover
            else:
                bg_color = colors.ai_message_bg
                text_color = colors.ai_message_text
                role_color = colors.warning
                border_color = colors.border
            
            # Update frame styling
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: {spacing.border_width}px solid {border_color};
                    border-radius: {spacing.border_radius}px;
                    margin: {spacing.margin_small}px;
                    padding: 0px;
                }}
            """)
            
            # Update text labels
            for child in self.findChildren(QLabel):
                if ":" in child.text():  # Role label
                    child.setStyleSheet(f"""
                        QLabel {{
                            color: {role_color};
                            font-weight: bold;
                            font-size: {fonts.size_normal}px;
                            font-family: '{fonts.family}';
                            background-color: transparent;
                            border: none;
                            margin-bottom: 6px;
                        }}
                    """)
                else:  # Message label
                    child.setStyleSheet(f"""
                        QLabel {{
                            color: {text_color};
                            font-size: {fonts.size_normal}px;
                            font-family: '{fonts.family}';
                            line-height: 1.4;
                            background-color: transparent;
                            border: none;
                        }}
                    """)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error applying theme to message widget: {e}")

class TypingIndicator(QFrame):
    """Animated typing indicator widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_dots)
        self.dot_count = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the typing indicator UI."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setFixedHeight(50)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(60, 60, 60, 160);
                border: 1px solid rgba(120, 120, 120, 120);
                border-radius: 12px;
                margin: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # AI label
        ai_label = QLabel("AI:")
        ai_label.setStyleSheet("""
            QLabel {
                color: #FFB347;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                background-color: transparent;
                border: none;
            }
        """)
        
        # Typing text with animated dots
        self.typing_label = QLabel("thinking")
        self.typing_label.setStyleSheet("""
            QLabel {
                color: #e8e8e8;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
                font-style: italic;
                background-color: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(ai_label)
        layout.addWidget(self.typing_label)
        layout.addStretch()
    
    def start_animation(self):
        """Start the typing animation."""
        self.animation_timer.start(600)  # Update every 600ms
    
    def stop_animation(self):
        """Stop the typing animation."""
        self.animation_timer.stop()
        self.dot_count = 0
    
    def animate_dots(self):
        """Animate the typing dots."""
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.typing_label.setText(f"thinking{dots}")
    
    def apply_theme_colors(self, colors, fonts, spacing):
        """Apply theme colors to the typing indicator."""
        try:
            # Update frame styling
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.ai_message_bg};
                    border: {spacing.border_width}px solid {colors.border};
                    border-radius: {spacing.border_radius}px;
                    margin: {spacing.margin_small}px;
                }}
            """)
            
            # Update AI label
            ai_labels = [child for child in self.findChildren(QLabel) if child.text() == "AI:"]
            if ai_labels:
                ai_labels[0].setStyleSheet(f"""
                    QLabel {{
                        color: {colors.warning};
                        font-weight: bold;
                        font-size: {fonts.size_normal}px;
                        font-family: '{fonts.family}';
                        background-color: transparent;
                        border: none;
                    }}
                """)
            
            # Update typing label
            self.typing_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors.ai_message_text};
                    font-size: {fonts.size_normal}px;
                    font-family: '{fonts.family}';
                    font-style: italic;
                    background-color: transparent;
                    border: none;
                }}
            """)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error applying theme to typing indicator: {e}")

class PromptInterface(OverlayBaseWindow):
    """Main prompt and response interface."""
    
    # Signals
    message_sent = pyqtSignal(str)
    minimize_requested = pyqtSignal()
    window_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.messages: List[MessageWidget] = []
        
        # Animation properties
        self.fade_in_animation = None
        self.fade_out_animation = None
        self.typing_indicator = None
        self.is_typing = False
        
        self.setup_ui()
        self.setup_animations()
        self.resize(420, 620)
        
        # Auto-scroll timer
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.scroll_to_bottom)
        self.scroll_timer.setSingleShot(True)
    
    def setup_ui(self):
        """Setup the interface UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Add window shadow effect
        window_shadow = QGraphicsDropShadowEffect()
        window_shadow.setBlurRadius(25)
        window_shadow.setXOffset(0)
        window_shadow.setYOffset(5)
        window_shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(window_shadow)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # Title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Messages area
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messages_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.messages_scroll.setStyleSheet("""
            QScrollArea {
                background-color: rgba(30, 30, 35, 220);
                border: 1px solid rgba(135, 206, 235, 80);
                border-radius: 12px;
            }
            QScrollBar:vertical {
                background: rgba(50, 50, 55, 180);
                width: 14px;
                border-radius: 7px;
                margin: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(135, 206, 235, 160);
                border-radius: 7px;
                min-height: 25px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(135, 206, 235, 200);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(100, 180, 220, 200);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Messages container
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()  # Push messages to top
        self.messages_scroll.setWidget(self.messages_widget)
        
        main_layout.addWidget(self.messages_scroll, 1)  # Take most space
        
        # Input area
        input_area = self.create_input_area()
        main_layout.addWidget(input_area)
        
        self.logger.info("Prompt interface UI setup complete")
    
    def setup_animations(self):
        """Setup window animations."""
        try:
            # Fade-in animation for window appearance
            self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_in_animation.setDuration(400)
            self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.fade_in_animation.setStartValue(0.0)
            self.fade_in_animation.setEndValue(0.95)
            
            # Fade-out animation for window hiding
            self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_out_animation.setDuration(300)
            self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self.fade_out_animation.setStartValue(0.95)
            self.fade_out_animation.setEndValue(0.0)
            self.fade_out_animation.finished.connect(self._complete_hide)
            
            self.logger.debug("Prompt interface animations setup complete")
        except Exception as e:
            self.logger.error(f"Error setting up animations: {e}")
    
    def show(self):
        """Override show to add fade-in animation."""
        super().show()
        if self.fade_in_animation and self.fade_in_animation.state() != QPropertyAnimation.State.Running:
            self.setWindowOpacity(0.0)
            self.fade_in_animation.start()
            self.logger.debug("Started window fade-in animation")
    
    def hide_with_animation(self):
        """Hide window with fade-out animation."""
        if self.fade_out_animation and self.fade_out_animation.state() != QPropertyAnimation.State.Running:
            self.fade_out_animation.start()
            self.logger.debug("Started window fade-out animation")
        else:
            self.hide()
    
    def _complete_hide(self):
        """Complete the hide operation after animation."""
        super().hide()
    
    def create_title_bar(self) -> QWidget:
        """Create the title bar."""
        title_frame = QFrame()
        title_frame.setFixedHeight(40)
        title_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 55, 220);
                border-radius: 10px;
                border: 1px solid rgba(135, 206, 235, 80);
            }
        """)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(15, 8, 15, 8)
        
        # Title
        title_label = QLabel("Ghostman AI Assistant")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 16px;
                background-color: transparent;
                border: none;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Minimize button
        minimize_btn = QPushButton("–")
        minimize_btn.setFixedSize(30, 25)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 150);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(130, 130, 130, 180);
            }
            QPushButton:pressed {
                background-color: rgba(80, 80, 80, 180);
            }
        """)
        minimize_btn.clicked.connect(self.minimize_requested.emit)
        title_layout.addWidget(minimize_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 25)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 60, 60, 150);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(220, 80, 80, 180);
            }
            QPushButton:pressed {
                background-color: rgba(180, 40, 40, 180);
            }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        return title_frame
    
    def create_input_area(self) -> QWidget:
        """Create the input area."""
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 55, 220);
                border-radius: 10px;
                border: 1px solid rgba(135, 206, 235, 80);
            }
        """)
        
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        # Text input
        self.prompt_input = QTextEdit()
        self.prompt_input.setMaximumHeight(100)
        self.prompt_input.setPlaceholderText("Type your message here...")
        self.prompt_input.setStyleSheet("""
            QTextEdit {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                font-size: 13px;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 1px solid rgba(100, 150, 200, 200);
            }
        """)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedHeight(35)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 130, 180, 180);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: rgba(90, 150, 200, 200);
            }
            QPushButton:pressed {
                background-color: rgba(50, 110, 160, 180);
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        
        # Clear button  
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(35)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(120, 120, 120, 150);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: rgba(140, 140, 140, 180);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 150);
            }
        """)
        clear_btn.clicked.connect(self.clear_conversation)
        
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(self.send_btn)
        
        input_layout.addWidget(self.prompt_input)
        input_layout.addLayout(button_layout)
        
        # Connect Enter key to send
        self.prompt_input.installEventFilter(self)
        
        return input_frame
    
    def eventFilter(self, obj, event):
        """Handle key events for input area."""
        if obj == self.prompt_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    # Ctrl+Enter for new line
                    cursor = self.prompt_input.textCursor()
                    cursor.insertText('\n')
                    return True
                else:
                    # Enter to send
                    self.send_message()
                    return True
        return super().eventFilter(obj, event)
    
    def send_message(self):
        """Send the current message."""
        try:
            message_text = self.prompt_input.toPlainText().strip()
            if not message_text:
                return
            
            # Validate message length
            if len(message_text) > 5000:  # Reasonable limit
                self.logger.warning("Message too long, truncating")
                message_text = message_text[:5000] + "..."
            
            # Add user message
            self.add_message(message_text, is_user=True)
            
            # Clear input
            self.prompt_input.clear()
            
            # Show typing indicator
            self.show_typing_indicator()
            
            # Emit signal for processing
            self.message_sent.emit(message_text)
            
            # AI service will handle the response via signal connections
            
            self.logger.info(f"User message sent: {message_text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            # Hide typing indicator if there was an error
            self.hide_typing_indicator()
            self.add_ai_response("Sorry, there was an error processing your message. Please try again.")
    
    def show_typing_indicator(self):
        """Show the typing indicator."""
        if not self.is_typing:
            self.typing_indicator = TypingIndicator()
            # Insert before the stretch item
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.typing_indicator)
            self.typing_indicator.start_animation()
            self.is_typing = True
            self.scroll_timer.start(100)
            self.logger.debug("Typing indicator shown")
    
    def hide_typing_indicator(self):
        """Hide the typing indicator."""
        if self.is_typing and self.typing_indicator:
            self.typing_indicator.stop_animation()
            self.typing_indicator.deleteLater()
            self.typing_indicator = None
            self.is_typing = False
            self.logger.debug("Typing indicator hidden")
    
    def add_message(self, message: str, is_user: bool = True):
        """Add a message to the conversation."""
        message_widget = MessageWidget(message, is_user)
        
        # Insert before the stretch item (keep stretch at bottom)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)
        self.messages.append(message_widget)
        
        # Auto-scroll to bottom
        self.scroll_timer.start(100)
        
        self.logger.debug(f"Added {'user' if is_user else 'AI'} message")
    
    def add_ai_response(self, response: str):
        """Add an AI response to the conversation."""
        # Hide typing indicator if it's showing
        self.hide_typing_indicator()
        self.add_message(response, is_user=False)
    
    def clear_conversation(self):
        """Clear all messages."""
        # Hide typing indicator first
        self.hide_typing_indicator()
        
        for message_widget in self.messages:
            message_widget.deleteLater()
        
        self.messages.clear()
        self.logger.info("Conversation cleared")
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the messages."""
        scrollbar = self.messages_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle close event."""
        try:
            # Clean up typing indicator
            self.hide_typing_indicator()
            
            # Stop any running animations
            if self.fade_in_animation and self.fade_in_animation.state() == QPropertyAnimation.State.Running:
                self.fade_in_animation.stop()
            if self.fade_out_animation and self.fade_out_animation.state() == QPropertyAnimation.State.Running:
                self.fade_out_animation.stop()
            
            # Stop timers
            if self.scroll_timer.isActive():
                self.scroll_timer.stop()
            
            self.window_closed.emit()
            self.logger.info("Prompt interface closing")
        except Exception as e:
            self.logger.error(f"Error during close event: {e}")
        finally:
            super().closeEvent(event)
    
    def apply_theme_colors(self, colors, fonts, spacing):
        """Apply theme colors to the prompt interface."""
        try:
            # Update main window background and styling via theme manager stylesheet
            # This will be handled by the application's theme system
            
            # Update all existing message widgets
            for message_widget in self.messages:
                if hasattr(message_widget, 'apply_theme_colors'):
                    message_widget.apply_theme_colors(colors, fonts, spacing)
            
            # Update typing indicator if it exists
            if self.typing_indicator and hasattr(self.typing_indicator, 'apply_theme_colors'):
                self.typing_indicator.apply_theme_colors(colors, fonts, spacing)
            
            # Update input area elements with theme colors
            self.update_input_area_theme(colors, fonts, spacing)
            self.update_title_bar_theme(colors, fonts, spacing)
            
            self.logger.debug("Prompt interface theme colors applied successfully")
            
        except Exception as e:
            self.logger.error(f"Error applying theme colors to prompt interface: {e}")
    
    def update_input_area_theme(self, colors, fonts, spacing):
        """Update input area styling with theme colors."""
        try:
            # Update text input
            if hasattr(self, 'prompt_input'):
                self.prompt_input.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {colors.background};
                        color: {colors.text_primary};
                        border: {spacing.border_width}px solid {colors.border};
                        border-radius: {spacing.border_radius}px;
                        font-size: {fonts.size_normal}px;
                        font-family: '{fonts.family}';
                        padding: {spacing.padding_small}px;
                    }}
                    QTextEdit:focus {{
                        border: {spacing.border_width}px solid {colors.border_hover};
                    }}
                """)
            
            # Update send button
            if hasattr(self, 'send_btn'):
                self.send_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {colors.primary};
                        color: {colors.text_primary};
                        border: none;
                        border-radius: {spacing.border_radius}px;
                        font-weight: {fonts.weight_bold};
                        font-size: {fonts.size_normal}px;
                        font-family: '{fonts.family}';
                        padding: {spacing.padding_small}px {spacing.padding_normal}px;
                    }}
                    QPushButton:hover {{
                        background-color: {colors.primary_hover};
                    }}
                    QPushButton:pressed {{
                        background-color: {colors.primary_pressed};
                    }}
                    QPushButton:disabled {{
                        background-color: {colors.background_light};
                        color: {colors.text_disabled};
                    }}
                """)
                
        except Exception as e:
            self.logger.error(f"Error updating input area theme: {e}")
    
    def update_title_bar_theme(self, colors, fonts, spacing):
        """Update title bar styling with theme colors."""
        try:
            # Title bar updates would go here if we want to customize beyond the main stylesheet
            # For now, the main theme stylesheet handles most of this
            pass
        except Exception as e:
            self.logger.error(f"Error updating title bar theme: {e}")