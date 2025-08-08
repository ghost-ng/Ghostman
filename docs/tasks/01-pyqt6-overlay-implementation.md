# PyQt6 Overlay Implementation Plan

## Overview

This document outlines the comprehensive implementation plan for creating a PyQt6-based desktop overlay system for Ghostman that works without administrator permissions. Based on extensive research, this plan provides concrete steps to implement always-on-top functionality, draggable windows, and system integration.

## Technical Foundation

### Key PyQt6 Window Flags
```python
Qt.WindowType.WindowStaysOnTopHint  # Always-on-top behavior
Qt.WindowType.FramelessWindowHint   # Remove window decorations
Qt.WindowType.Tool                  # Prevents taskbar appearance
Qt.WindowType.WindowDoesNotAcceptFocus  # Non-intrusive behavior
```

### Core Limitations (No Admin Rights)
- Cannot overlay elevated (admin) applications
- `WindowStaysOnTopHint` is a hint, not guarantee
- UAC security boundaries prevent cross-process interaction
- Must work within standard user integrity levels

## Implementation Strategy

### 1. Base Overlay Window Class

**File**: `ghostman/src/ui/components/overlay_base.py`

```python
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from typing import Tuple, Optional

class OverlayBaseWindow(QMainWindow):
    """Base class for overlay windows with common functionality."""
    
    # Signals
    position_changed = pyqtSignal(QPoint)
    focus_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_position = QPoint()
        self.setup_overlay_behavior()
        self.setup_drag_functionality()
    
    def setup_overlay_behavior(self):
        """Configure window for overlay behavior."""
        # Core overlay flags
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Non-intrusive behavior
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        # Transparency support
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.95)
    
    def setup_drag_functionality(self):
        """Enable window dragging."""
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            event.accept()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.position_changed.emit(new_pos)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
        super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effects."""
        self.setWindowOpacity(1.0)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effects."""
        self.setWindowOpacity(0.95)
        super().leaveEvent(event)
```

### 2. Avatar Widget Implementation

**File**: `ghostman/src/ui/components/avatar_widget.py`

```python
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QContextMenuEvent, QMouseEvent
from .overlay_base import OverlayBaseWindow

class AvatarWidget(OverlayBaseWindow):
    """Minimized avatar widget for the AI assistant."""
    
    # Signals
    left_clicked = pyqtSignal()
    right_clicked = pyqtSignal(QPoint)
    avatar_hovered = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_animations()
        self.resize(80, 80)  # Compact avatar size
    
    def setup_ui(self):
        """Setup the avatar UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Avatar image/icon
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet("""
            QLabel {
                background-color: rgba(70, 130, 180, 200);
                border-radius: 30px;
                border: 2px solid rgba(255, 255, 255, 100);
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.avatar_label.setText("AI")  # Placeholder - use icon in production
        self.avatar_label.setFixedSize(60, 60)
        
        layout.addWidget(self.avatar_label)
    
    def setup_animations(self):
        """Setup hover and interaction animations."""
        self.scale_animation = QPropertyAnimation(self, b"windowOpacity")
        self.scale_animation.setDuration(200)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.dragging:
                # Differentiate between click and drag
                self.click_position = event.globalPosition().toPoint()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.dragging:
                # Check if this was a click (not drag)
                current_pos = event.globalPosition().toPoint()
                if (self.click_position - current_pos).manhattanLength() < 10:
                    self.left_clicked.emit()
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle right-click context menu."""
        self.right_clicked.emit(event.globalPos())
        event.accept()
    
    def enterEvent(self, event):
        """Handle mouse enter with animation."""
        self.avatar_hovered.emit(True)
        self.animate_opacity(1.0)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave with animation."""
        self.avatar_hovered.emit(False)
        self.animate_opacity(0.8)
        super().leaveEvent(event)
    
    def animate_opacity(self, target_opacity: float):
        """Animate opacity change."""
        self.scale_animation.setStartValue(self.windowOpacity())
        self.scale_animation.setEndValue(target_opacity)
        self.scale_animation.start()
```

### 3. Main Interface Window

**File**: `ghostman/src/ui/components/prompt_window.py`

```python
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QLineEdit, QPushButton, QMenuBar, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QFont
from .overlay_base import OverlayBaseWindow

class PromptWindow(OverlayBaseWindow):
    """Main AI interaction window."""
    
    # Signals
    message_sent = pyqtSignal(str)
    window_closed = pyqtSignal()
    minimize_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_menu()
        self.resize(400, 600)
        
        # Auto-hide functionality
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.timeout.connect(self.check_auto_hide)
        self.auto_hide_timer.start(1000)  # Check every second
        
        self.last_interaction = 0
        self.auto_hide_delay = 30000  # 30 seconds
    
    def setup_ui(self):
        """Setup the main interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Conversation display
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setFont(QFont("Segoe UI", 10))
        self.conversation_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(40, 40, 40, 230);
                color: white;
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.conversation_display, stretch=1)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Ask me anything...")
        self.message_input.setFont(QFont("Segoe UI", 10))
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(60, 60, 60, 230);
                color: white;
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(70, 130, 180, 200);
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 130, 180, 200);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(70, 130, 180, 255);
            }
            QPushButton:pressed {
                background-color: rgba(60, 120, 170, 255);
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input, stretch=1)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.minimize_button = QPushButton("Minimize")
        self.minimize_button.clicked.connect(self.minimize_requested.emit)
        
        self.opacity_button = QPushButton("Toggle Opacity")
        self.opacity_button.clicked.connect(self.toggle_opacity)
        
        control_layout.addWidget(self.minimize_button)
        control_layout.addWidget(self.opacity_button)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
    
    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        save_action = file_menu.addAction('Save Conversation')
        save_action.triggered.connect(self.save_conversation)
        
        file_menu.addSeparator()
        
        close_action = file_menu.addAction('Close')
        close_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        help_action = help_menu.addAction('Help')
        help_action.triggered.connect(self.show_help)
        
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about)
    
    def send_message(self):
        """Send user message."""
        message = self.message_input.text().strip()
        if message:
            self.add_user_message(message)
            self.message_input.clear()
            self.message_sent.emit(message)
            self.update_interaction_time()
    
    def add_user_message(self, message: str):
        """Add user message to conversation display."""
        self.conversation_display.append(f"<b>You:</b> {message}")
        self.conversation_display.ensureCursorVisible()
    
    def add_ai_message(self, message: str):
        """Add AI message to conversation display."""
        self.conversation_display.append(f"<b>AI:</b> {message}")
        self.conversation_display.ensureCursorVisible()
    
    def show_typing_indicator(self):
        """Show typing indicator."""
        self.conversation_display.append("<i>AI is thinking...</i>")
        self.conversation_display.ensureCursorVisible()
    
    def hide_typing_indicator(self):
        """Remove typing indicator."""
        cursor = self.conversation_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        if "AI is thinking..." in cursor.selectedText():
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove the newline
    
    def toggle_opacity(self):
        """Toggle window opacity."""
        current_opacity = self.windowOpacity()
        new_opacity = 0.7 if current_opacity > 0.8 else 0.95
        self.setWindowOpacity(new_opacity)
    
    def update_interaction_time(self):
        """Update last interaction time."""
        import time
        self.last_interaction = time.time() * 1000  # Convert to milliseconds
    
    def check_auto_hide(self):
        """Check if window should auto-hide."""
        import time
        current_time = time.time() * 1000
        
        if (self.last_interaction > 0 and 
            current_time - self.last_interaction > self.auto_hide_delay and
            self.isVisible()):
            self.minimize_requested.emit()
    
    def mousePressEvent(self, event):
        """Handle mouse events and update interaction time."""
        self.update_interaction_time()
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """Handle key events and update interaction time."""
        self.update_interaction_time()
        super().keyPressEvent(event)
    
    def save_conversation(self):
        """Save current conversation."""
        # Implement conversation saving
        pass
    
    def show_help(self):
        """Show help dialog."""
        # Implement help dialog
        pass
    
    def show_about(self):
        """Show about dialog."""
        # Implement about dialog
        pass
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.window_closed.emit()
        event.accept()
```

### 4. Window State Manager

**File**: `ghostman/src/app/window_manager.py`

```python
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication
from typing import Tuple, Optional
from enum import Enum
import json
from pathlib import Path

class WindowState(Enum):
    AVATAR = "avatar"
    MAIN_INTERFACE = "main_interface"
    HIDDEN = "hidden"

class WindowManager(QObject):
    """Manages window states and positioning."""
    
    # Signals
    state_changed = pyqtSignal(WindowState, WindowState)  # old_state, new_state
    
    def __init__(self, avatar_widget, prompt_window, settings_path: Path):
        super().__init__()
        self.avatar_widget = avatar_widget
        self.prompt_window = prompt_window
        self.settings_path = settings_path
        self.current_state = WindowState.AVATAR
        
        # Position management
        self.default_avatar_pos = None
        self.default_prompt_pos = None
        self.load_window_positions()
        
        # Setup connections
        self.setup_connections()
        
        # Screen change detection
        self.screen_timer = QTimer()
        self.screen_timer.timeout.connect(self.check_screen_changes)
        self.screen_timer.start(5000)  # Check every 5 seconds
        
    def setup_connections(self):
        """Setup signal connections."""
        # Avatar widget signals
        self.avatar_widget.left_clicked.connect(self.show_main_interface)
        self.avatar_widget.position_changed.connect(self.save_avatar_position)
        
        # Prompt window signals
        self.prompt_window.minimize_requested.connect(self.show_avatar)
        self.prompt_window.window_closed.connect(self.show_avatar)
        self.prompt_window.position_changed.connect(self.save_prompt_position)
    
    def set_state(self, new_state: WindowState):
        """Change window state."""
        if new_state == self.current_state:
            return
        
        old_state = self.current_state
        self.current_state = new_state
        
        # Hide all windows first
        self.avatar_widget.hide()
        self.prompt_window.hide()
        
        # Show appropriate window
        if new_state == WindowState.AVATAR:
            self.position_avatar_widget()
            self.avatar_widget.show()
            self.avatar_widget.raise_()
        elif new_state == WindowState.MAIN_INTERFACE:
            self.position_prompt_window()
            self.prompt_window.show()
            self.prompt_window.raise_()
            self.prompt_window.activateWindow()
        
        self.state_changed.emit(old_state, new_state)
    
    def show_avatar(self):
        """Show avatar widget."""
        self.set_state(WindowState.AVATAR)
    
    def show_main_interface(self):
        """Show main interface."""
        self.set_state(WindowState.MAIN_INTERFACE)
    
    def position_avatar_widget(self):
        """Position avatar widget on screen."""
        if self.default_avatar_pos:
            pos = QPoint(*self.default_avatar_pos)
            if self.is_position_on_screen(pos):
                self.avatar_widget.move(pos)
                return
        
        # Default positioning (top-right corner)
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.avatar_widget.width() - 20
        y = 20
        self.avatar_widget.move(x, y)
    
    def position_prompt_window(self):
        """Position prompt window on screen."""
        if self.default_prompt_pos:
            pos = QPoint(*self.default_prompt_pos)
            if self.is_position_on_screen(pos):
                self.prompt_window.move(pos)
                return
        
        # Default positioning (center-right)
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.prompt_window.width() - 50
        y = (screen.height() - self.prompt_window.height()) // 2
        self.prompt_window.move(x, y)
    
    def is_position_on_screen(self, pos: QPoint) -> bool:
        """Check if position is visible on any screen."""
        for screen in QApplication.screens():
            if screen.geometry().contains(pos):
                return True
        return False
    
    def save_avatar_position(self, pos: QPoint):
        """Save avatar position."""
        self.default_avatar_pos = (pos.x(), pos.y())
        self.save_window_positions()
    
    def save_prompt_position(self, pos: QPoint):
        """Save prompt window position."""
        self.default_prompt_pos = (pos.x(), pos.y())
        self.save_window_positions()
    
    def load_window_positions(self):
        """Load saved window positions."""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    
                avatar_pos = data.get('avatar_position')
                if avatar_pos:
                    self.default_avatar_pos = tuple(avatar_pos)
                    
                prompt_pos = data.get('prompt_position')
                if prompt_pos:
                    self.default_prompt_pos = tuple(prompt_pos)
        except Exception as e:
            print(f"Error loading window positions: {e}")
    
    def save_window_positions(self):
        """Save window positions to file."""
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            if self.default_avatar_pos:
                data['avatar_position'] = list(self.default_avatar_pos)
            if self.default_prompt_pos:
                data['prompt_position'] = list(self.default_prompt_pos)
            
            with open(self.settings_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving window positions: {e}")
    
    def check_screen_changes(self):
        """Check for screen configuration changes."""
        # Ensure windows are still visible after screen changes
        if self.current_state == WindowState.AVATAR:
            if not self.is_position_on_screen(self.avatar_widget.pos()):
                self.position_avatar_widget()
        elif self.current_state == WindowState.MAIN_INTERFACE:
            if not self.is_position_on_screen(self.prompt_window.pos()):
                self.position_prompt_window()
    
    def refresh_always_on_top(self):
        """Refresh always-on-top status (Windows workaround)."""
        # This is a workaround for Windows losing always-on-top status
        current_widget = None
        
        if self.current_state == WindowState.AVATAR and self.avatar_widget.isVisible():
            current_widget = self.avatar_widget
        elif self.current_state == WindowState.MAIN_INTERFACE and self.prompt_window.isVisible():
            current_widget = self.prompt_window
        
        if current_widget:
            # Temporarily remove and re-add always-on-top flag
            current_widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            current_widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            current_widget.show()
```

### 5. System Tray Integration

**File**: `ghostman/src/ui/components/system_tray.py`

```python
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtCore import QObject, pyqtSignal

class SystemTrayManager(QObject):
    """Manages system tray integration."""
    
    # Signals
    show_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.tray_icon = None
        self.setup_tray()
    
    def setup_tray(self):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray is not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon (placeholder - use proper icon file)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.blue)
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Setup context menu
        self.setup_tray_menu()
        
        # Connect signals
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def setup_tray_menu(self):
        """Setup tray context menu."""
        tray_menu = QMenu()
        
        # Show action
        show_action = QAction("Show Ghostman", self)
        show_action.triggered.connect(self.show_requested.emit)
        tray_menu.addAction(show_action)
        
        # Hide action
        hide_action = QAction("Hide Ghostman", self)
        hide_action.triggered.connect(self.hide_requested.emit)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        # settings_action.triggered.connect(self.settings_requested.emit)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()
    
    def show_message(self, title: str, message: str, timeout: int = 5000):
        """Show tray notification message."""
        if self.tray_icon:
            self.tray_icon.showMessage(
                title, 
                message, 
                QSystemTrayIcon.MessageIcon.Information,
                timeout
            )
    
    def set_tooltip(self, tooltip: str):
        """Set tray icon tooltip."""
        if self.tray_icon:
            self.tray_icon.setToolTip(tooltip)
```

## Integration and Testing Plan

### 1. Development Phases

#### Phase 1: Basic Overlay (Week 1)
- [ ] Implement `OverlayBaseWindow` with basic always-on-top functionality
- [ ] Create minimal `AvatarWidget` with drag support
- [ ] Test on Windows without admin permissions
- [ ] Verify positioning and screen boundary handling

#### Phase 2: Full UI Components (Week 2)
- [ ] Complete `AvatarWidget` with hover effects and context menu
- [ ] Implement `PromptWindow` with chat interface
- [ ] Add `WindowManager` for state transitions
- [ ] Test dragging, resizing, and opacity controls

#### Phase 3: System Integration (Week 3)
- [ ] Add system tray integration
- [ ] Implement auto-hide functionality
- [ ] Add keyboard shortcuts
- [ ] Test multi-monitor support

#### Phase 4: Polish and Testing (Week 4)
- [ ] Add animations and visual effects
- [ ] Implement comprehensive error handling
- [ ] Performance optimization
- [ ] Cross-platform testing

### 2. Testing Strategy

#### Manual Testing Checklist
- [ ] Always-on-top behavior across different applications
- [ ] Window dragging and positioning
- [ ] State transitions (avatar ↔ main interface)
- [ ] Context menu functionality
- [ ] System tray integration
- [ ] Multi-monitor positioning
- [ ] Auto-hide functionality
- [ ] Opacity controls

#### Automated Testing
```python
# ghostman/tests/test_overlay.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ghostman.ui.components.avatar_widget import AvatarWidget

class TestAvatarWidget:
    def test_always_on_top_flag(self):
        app = QApplication([])
        widget = AvatarWidget()
        
        flags = widget.windowFlags()
        assert flags & Qt.WindowType.WindowStaysOnTopHint
        assert flags & Qt.WindowType.FramelessWindowHint
        assert flags & Qt.WindowType.Tool
    
    def test_drag_functionality(self):
        app = QApplication([])
        widget = AvatarWidget()
        
        # Test drag state initialization
        assert not widget.dragging
        assert widget.drag_position.isNull()
    
    def test_opacity_control(self):
        app = QApplication([])
        widget = AvatarWidget()
        
        initial_opacity = widget.windowOpacity()
        widget.animate_opacity(0.5)
        # Test that animation was started
```

### 3. Platform-Specific Considerations

#### Windows Implementation
```python
def setup_windows_workarounds(self):
    """Windows-specific workarounds."""
    import sys
    
    if sys.platform == "win32":
        # Periodic refresh of always-on-top status
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_always_on_top)
        self.refresh_timer.start(10000)  # Every 10 seconds
        
        # Handle Windows sleep/wake events
        self.installEventFilter(self)

def eventFilter(self, obj, event):
    """Handle Windows-specific events."""
    # Handle resume from sleep/hibernate
    if event.type() == QEvent.Type.ApplicationActivate:
        self.refresh_always_on_top()
    
    return super().eventFilter(obj, event)
```

#### macOS Considerations
```python
def setup_macos_specific(self):
    """macOS-specific setup."""
    import sys
    
    if sys.platform == "darwin":
        # macOS may need different window level
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        # Consider using native Cocoa calls for better control
```

This comprehensive implementation plan provides the foundation for creating a robust PyQt6 overlay system that works reliably without administrator permissions across different platforms and scenarios.