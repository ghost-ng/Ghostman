# UI/UX Behavior Implementation Plan

## Overview

This document outlines the comprehensive UI/UX behavior implementation for Ghostman, covering the avatar system, menu animations, window transitions, and user interaction patterns. The design focuses on intuitive, non-intrusive interactions while maintaining always-on-top functionality without admin permissions.

## Core UI/UX Principles

### Design Philosophy
1. **Minimal Disruption**: Never interfere with user's primary workflow
2. **Intuitive Interactions**: Common patterns that users expect
3. **Visual Feedback**: Clear indication of system state and actions
4. **Accessibility**: Keyboard navigation and screen reader compatibility
5. **Performance**: Smooth animations and responsive interactions

### Interaction Model
```
State Flow:
Avatar (Minimized) ←→ Main Interface (Expanded) ←→ Hidden (System Tray)
     ↕                    ↕                           ↕
Context Menu         File Menu                   Tray Menu
```

## Detailed Behavior Specifications

### 1. Avatar Widget Behavior

**File**: `ghostman/src/ui/behaviors/avatar_behavior.py`

```python
from PyQt6.QtCore import QObject, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QMenu
from PyQt6.QtGui import QCursor
from typing import Optional
import time

class AvatarBehaviorManager(QObject):
    """Manages avatar widget behavior and interactions."""
    
    # Signals
    avatar_clicked = pyqtSignal()
    context_menu_requested = pyqtSignal()
    hover_state_changed = pyqtSignal(bool)  # True = entered, False = left
    
    def __init__(self, avatar_widget):
        super().__init__()
        self.avatar_widget = avatar_widget
        
        # Animation properties
        self.hover_animation = None
        self.pulse_animation = None
        self.slide_animation = None
        
        # State tracking
        self.is_hovered = False
        self.last_click_time = 0
        self.click_threshold = 300  # ms for distinguishing click from drag
        self.double_click_threshold = 500  # ms for double-click detection
        
        # Activity monitoring
        self.activity_timer = QTimer()
        self.activity_timer.timeout.connect(self.check_activity)
        self.activity_timer.start(1000)  # Check every second
        
        self.idle_time = 0
        self.pulse_when_idle = True
        
        self.setup_animations()
        self.connect_signals()
    
    def setup_animations(self):
        """Setup animation objects."""
        # Hover scale animation
        self.hover_animation = QPropertyAnimation(self.avatar_widget, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity effect for pulse
        self.opacity_effect = QGraphicsOpacityEffect()
        self.avatar_widget.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_animation.setDuration(2000)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        self.pulse_animation.setStartValue(0.7)
        self.pulse_animation.setEndValue(1.0)
    
    def connect_signals(self):
        """Connect widget signals to behavior handlers."""
        self.avatar_widget.enterEvent = self.on_enter_event
        self.avatar_widget.leaveEvent = self.on_leave_event
        self.avatar_widget.mousePressEvent = self.on_mouse_press
        self.avatar_widget.mouseReleaseEvent = self.on_mouse_release
        self.avatar_widget.contextMenuEvent = self.on_context_menu
    
    def on_enter_event(self, event):
        """Handle mouse enter (hover start)."""
        if not self.is_hovered:
            self.is_hovered = True
            self.hover_state_changed.emit(True)
            self.start_hover_animation()
            
            # Stop pulse animation when hovering
            if self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()
                self.opacity_effect.setOpacity(1.0)
        
        # Call original event handler if it exists
        super(type(self.avatar_widget), self.avatar_widget).enterEvent(event)
    
    def on_leave_event(self, event):
        """Handle mouse leave (hover end)."""
        if self.is_hovered:
            self.is_hovered = False
            self.hover_state_changed.emit(False)
            self.end_hover_animation()
            
            # Resume pulse animation if idle
            if self.idle_time > 10 and self.pulse_when_idle:
                self.start_pulse_animation()
        
        super(type(self.avatar_widget), self.avatar_widget).leaveEvent(event)
    
    def on_mouse_press(self, event):
        """Handle mouse press event."""
        from PyQt6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_time = time.time() * 1000
            self.press_position = event.globalPosition().toPoint()
            
            # Visual feedback for press
            self.show_press_feedback()
        
        # Call original handler for drag functionality
        super(type(self.avatar_widget), self.avatar_widget).mousePressEvent(event)
    
    def on_mouse_release(self, event):
        """Handle mouse release event."""
        from PyQt6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton:
            release_time = time.time() * 1000
            release_position = event.globalPosition().toPoint()
            
            # Check if this was a click (not a drag)
            time_diff = release_time - self.press_time
            distance = (self.press_position - release_position).manhattanLength()
            
            if time_diff < self.click_threshold and distance < 5:
                # This is a click
                self.handle_click(time_diff)
            
            self.hide_press_feedback()
        
        super(type(self.avatar_widget), self.avatar_widget).mouseReleaseEvent(event)
    
    def handle_click(self, click_duration):
        """Handle click events with double-click detection."""
        current_time = time.time() * 1000
        
        # Check for double-click
        if current_time - self.last_click_time < self.double_click_threshold:
            self.handle_double_click()
        else:
            # Single click - trigger after delay to allow for double-click
            QTimer.singleShot(self.double_click_threshold, self.handle_single_click)
        
        self.last_click_time = current_time
    
    def handle_single_click(self):
        """Handle single click - open main interface."""
        # Only trigger if no double-click occurred
        current_time = time.time() * 1000
        if current_time - self.last_click_time >= self.double_click_threshold:
            self.avatar_clicked.emit()
    
    def handle_double_click(self):
        """Handle double click - special action (e.g., quick prompt)."""
        # Implement special double-click behavior
        pass
    
    def on_context_menu(self, event):
        """Handle right-click context menu."""
        self.context_menu_requested.emit()
        event.accept()
    
    def start_hover_animation(self):
        """Start hover animation (slight scale up)."""
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
        
        current_geometry = self.avatar_widget.geometry()
        enlarged_geometry = current_geometry.adjusted(-5, -5, 5, 5)
        
        self.hover_animation.setStartValue(current_geometry)
        self.hover_animation.setEndValue(enlarged_geometry)
        self.hover_animation.start()
    
    def end_hover_animation(self):
        """End hover animation (scale back to normal)."""
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
        
        current_geometry = self.avatar_widget.geometry()
        normal_geometry = current_geometry.adjusted(5, 5, -5, -5)
        
        self.hover_animation.setStartValue(current_geometry)
        self.hover_animation.setEndValue(normal_geometry)
        self.hover_animation.start()
    
    def start_pulse_animation(self):
        """Start idle pulse animation."""
        if not self.is_hovered and self.pulse_when_idle:
            self.pulse_animation.start()
    
    def stop_pulse_animation(self):
        """Stop pulse animation."""
        if self.pulse_animation.state() == QPropertyAnimation.State.Running:
            self.pulse_animation.stop()
            self.opacity_effect.setOpacity(1.0)
    
    def show_press_feedback(self):
        """Show visual feedback for button press."""
        # Temporarily reduce opacity to show press
        self.opacity_effect.setOpacity(0.7)
    
    def hide_press_feedback(self):
        """Hide visual feedback for button press."""
        self.opacity_effect.setOpacity(1.0)
    
    def check_activity(self):
        """Monitor user activity for idle detection."""
        if not self.is_hovered:
            self.idle_time += 1
            
            # Start pulsing after 10 seconds of inactivity
            if self.idle_time == 10 and self.pulse_when_idle:
                self.start_pulse_animation()
        else:
            self.idle_time = 0
            if self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()
                self.opacity_effect.setOpacity(1.0)
```

### 2. Slide-in Menu Animation System

**File**: `ghostman/src/ui/behaviors/menu_animations.py`

```python
from PyQt6.QtCore import QObject, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PyQt6.QtWidgets import QMenu, QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import QCursor
from typing import Optional, Tuple

class SlideInMenu(QMenu):
    """Custom menu with slide-in animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slide_animation = None
        self.opacity_effect = None
        self.setup_animations()
        self.setup_style()
    
    def setup_animations(self):
        """Setup slide and fade animations."""
        # Slide animation
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(200)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity effect for fade
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Fade animation
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def setup_style(self):
        """Setup menu visual style."""
        self.setStyleSheet("""
            QMenu {
                background-color: rgba(45, 45, 45, 240);
                border: 1px solid rgba(80, 80, 80, 180);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(70, 130, 180, 150);
            }
            QMenu::item:pressed {
                background-color: rgba(70, 130, 180, 200);
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(80, 80, 80, 100);
                margin: 4px 8px;
            }
        """)
    
    def show_with_animation(self, position: Tuple[int, int], direction: str = "right"):
        """Show menu with slide-in animation from specified direction."""
        # Calculate final geometry
        self.adjustSize()
        final_rect = QRect(position[0], position[1], self.width(), self.height())
        
        # Calculate starting geometry based on direction
        if direction == "right":
            start_rect = QRect(position[0] - self.width(), position[1], 0, self.height())
        elif direction == "left":
            start_rect = QRect(position[0] + self.width(), position[1], 0, self.height())
        elif direction == "up":
            start_rect = QRect(position[0], position[1] + self.height(), self.width(), 0)
        else:  # down
            start_rect = QRect(position[0], position[1] - self.height(), self.width(), 0)
        
        # Set starting state
        self.setGeometry(start_rect)
        self.opacity_effect.setOpacity(0.0)
        self.show()
        
        # Animate to final position
        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(final_rect)
        self.slide_animation.start()
        
        # Fade in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def hide_with_animation(self, direction: str = "right"):
        """Hide menu with slide-out animation."""
        current_rect = self.geometry()
        
        # Calculate end geometry
        if direction == "right":
            end_rect = QRect(current_rect.right(), current_rect.y(), 0, current_rect.height())
        elif direction == "left":
            end_rect = QRect(current_rect.left() - current_rect.width(), current_rect.y(), 0, current_rect.height())
        elif direction == "up":
            end_rect = QRect(current_rect.x(), current_rect.y() - current_rect.height(), current_rect.width(), 0)
        else:  # down
            end_rect = QRect(current_rect.x(), current_rect.bottom(), current_rect.width(), 0)
        
        # Animate out
        self.slide_animation.setStartValue(current_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.finished.connect(self.hide)
        self.slide_animation.start()
        
        # Fade out
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()

class MenuAnimationManager(QObject):
    """Manages menu animations and behavior."""
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.current_menu = None
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.timeout.connect(self.auto_hide_menu)
        self.auto_hide_delay = 3000  # 3 seconds
    
    def show_context_menu(self, actions: list, position: Optional[Tuple[int, int]] = None):
        """Show context menu with animation at specified position."""
        if self.current_menu:
            self.hide_current_menu()
        
        # Create menu
        self.current_menu = SlideInMenu(self.parent_widget)
        
        # Add actions
        for action_data in actions:
            if action_data is None:
                self.current_menu.addSeparator()
            else:
                action = self.current_menu.addAction(action_data['text'])
                if 'callback' in action_data:
                    action.triggered.connect(action_data['callback'])
                if 'icon' in action_data:
                    action.setIcon(action_data['icon'])
                if 'enabled' in action_data:
                    action.setEnabled(action_data['enabled'])
        
        # Show with animation
        if position is None:
            position = QCursor.pos()
        
        # Determine animation direction based on screen position
        screen = self.parent_widget.screen().geometry()
        direction = self.calculate_slide_direction(position, screen, self.current_menu.sizeHint())
        
        self.current_menu.show_with_animation(position, direction)
        
        # Start auto-hide timer
        self.auto_hide_timer.start(self.auto_hide_delay)
        
        # Connect menu events
        self.current_menu.aboutToHide.connect(self.on_menu_hiding)
    
    def calculate_slide_direction(self, position: Tuple[int, int], screen_rect: QRect, menu_size) -> str:
        """Calculate optimal slide direction based on available screen space."""
        x, y = position
        
        # Check available space in each direction
        space_right = screen_rect.right() - x
        space_left = x - screen_rect.left()
        space_down = screen_rect.bottom() - y
        space_up = y - screen_rect.top()
        
        # Prefer right if there's space, otherwise left
        if space_right >= menu_size.width():
            return "right"
        elif space_left >= menu_size.width():
            return "left"
        elif space_down >= menu_size.height():
            return "down"
        else:
            return "up"
    
    def hide_current_menu(self):
        """Hide current menu with animation."""
        if self.current_menu and self.current_menu.isVisible():
            self.current_menu.hide_with_animation()
            self.auto_hide_timer.stop()
    
    def auto_hide_menu(self):
        """Auto-hide menu after timeout."""
        self.hide_current_menu()
    
    def on_menu_hiding(self):
        """Handle menu hiding event."""
        self.auto_hide_timer.stop()
        self.current_menu = None
```

### 3. Window Transition System

**File**: `ghostman/src/ui/behaviors/window_transitions.py`

```python
from PyQt6.QtCore import QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, pyqtSignal
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap, QPainter
from typing import Optional
import time

class TransitionType:
    FADE = "fade"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SCALE = "scale"
    MORPH = "morph"

class WindowTransitionManager(QObject):
    """Manages smooth transitions between different window states."""
    
    # Signals
    transition_started = pyqtSignal(str, str)  # from_state, to_state
    transition_finished = pyqtSignal(str, str)  # from_state, to_state
    
    def __init__(self, window_manager):
        super().__init__()
        self.window_manager = window_manager
        self.current_animation_group = None
        self.transition_duration = 300
        self.is_transitioning = False
    
    def transition_to_main_interface(self, transition_type: str = TransitionType.MORPH):
        """Transition from avatar to main interface."""
        if self.is_transitioning:
            return
        
        self.is_transitioning = True
        self.transition_started.emit("avatar", "main_interface")
        
        avatar_widget = self.window_manager.avatar_widget
        main_window = self.window_manager.prompt_window
        
        if transition_type == TransitionType.MORPH:
            self._morph_transition(avatar_widget, main_window)
        elif transition_type == TransitionType.FADE:
            self._fade_transition(avatar_widget, main_window)
        elif transition_type == TransitionType.SCALE:
            self._scale_transition(avatar_widget, main_window)
        else:
            # Default: just show/hide
            avatar_widget.hide()
            main_window.show()
            self._finish_transition("avatar", "main_interface")
    
    def transition_to_avatar(self, transition_type: str = TransitionType.MORPH):
        """Transition from main interface to avatar."""
        if self.is_transitioning:
            return
        
        self.is_transitioning = True
        self.transition_started.emit("main_interface", "avatar")
        
        avatar_widget = self.window_manager.avatar_widget
        main_window = self.window_manager.prompt_window
        
        if transition_type == TransitionType.MORPH:
            self._reverse_morph_transition(main_window, avatar_widget)
        elif transition_type == TransitionType.FADE:
            self._fade_transition(main_window, avatar_widget)
        elif transition_type == TransitionType.SCALE:
            self._reverse_scale_transition(main_window, avatar_widget)
        else:
            # Default: just show/hide
            main_window.hide()
            avatar_widget.show()
            self._finish_transition("main_interface", "avatar")
    
    def _morph_transition(self, from_widget, to_widget):
        """Smooth morph transition between widgets."""
        # Position target widget at source location initially
        from_geometry = from_widget.geometry()
        to_geometry = to_widget.geometry()
        
        # Create animation group
        self.current_animation_group = QParallelAnimationGroup()
        
        # Fade out source widget
        from_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
        from_fade_out.setDuration(self.transition_duration // 2)
        from_fade_out.setStartValue(1.0)
        from_fade_out.setEndValue(0.0)
        from_fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Setup target widget
        to_widget.setGeometry(from_geometry)
        to_opacity_effect = QGraphicsOpacityEffect()
        to_widget.setGraphicsEffect(to_opacity_effect)
        to_opacity_effect.setOpacity(0.0)
        to_widget.show()
        
        # Animate target widget geometry
        to_geometry_anim = QPropertyAnimation(to_widget, b"geometry")
        to_geometry_anim.setDuration(self.transition_duration)
        to_geometry_anim.setStartValue(from_geometry)
        to_geometry_anim.setEndValue(to_geometry)
        to_geometry_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade in target widget
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.transition_duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Add animations to group
        self.current_animation_group.addAnimation(from_fade_out)
        self.current_animation_group.addAnimation(to_geometry_anim)
        self.current_animation_group.addAnimation(to_fade_in)
        
        # Connect finished signal
        self.current_animation_group.finished.connect(
            lambda: self._finish_morph_transition(from_widget, to_widget, "avatar", "main_interface")
        )
        
        # Start animation
        self.current_animation_group.start()
    
    def _reverse_morph_transition(self, from_widget, to_widget):
        """Reverse morph transition (main interface to avatar)."""
        from_geometry = from_widget.geometry()
        to_geometry = to_widget.geometry()
        
        # Create animation group
        self.current_animation_group = QParallelAnimationGroup()
        
        # Animate source widget geometry to target position
        from_geometry_anim = QPropertyAnimation(from_widget, b"geometry")
        from_geometry_anim.setDuration(self.transition_duration)
        from_geometry_anim.setStartValue(from_geometry)
        from_geometry_anim.setEndValue(to_geometry)
        from_geometry_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # Fade out source widget
        from_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
        from_fade_out.setDuration(self.transition_duration)
        from_fade_out.setStartValue(1.0)
        from_fade_out.setEndValue(0.0)
        from_fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # Setup target widget
        to_widget.setGeometry(to_geometry)
        to_opacity_effect = QGraphicsOpacityEffect()
        to_widget.setGraphicsEffect(to_opacity_effect)
        to_opacity_effect.setOpacity(0.0)
        to_widget.show()
        
        # Fade in target widget
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.transition_duration // 2)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Delay target fade-in
        to_fade_in.setStartDelay(self.transition_duration // 2)
        
        # Add animations to group
        self.current_animation_group.addAnimation(from_geometry_anim)
        self.current_animation_group.addAnimation(from_fade_out)
        self.current_animation_group.addAnimation(to_fade_in)
        
        # Connect finished signal
        self.current_animation_group.finished.connect(
            lambda: self._finish_morph_transition(from_widget, to_widget, "main_interface", "avatar")
        )
        
        # Start animation
        self.current_animation_group.start()
    
    def _fade_transition(self, from_widget, to_widget):
        """Simple fade transition between widgets."""
        self.current_animation_group = QParallelAnimationGroup()
        
        # Fade out current widget
        from_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        from_fade = QPropertyAnimation(from_opacity_effect, b"opacity")
        from_fade.setDuration(self.transition_duration // 2)
        from_fade.setStartValue(1.0)
        from_fade.setEndValue(0.0)
        
        # Setup and fade in target widget
        to_opacity_effect = QGraphicsOpacityEffect()
        to_widget.setGraphicsEffect(to_opacity_effect)
        to_opacity_effect.setOpacity(0.0)
        to_widget.show()
        
        to_fade = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade.setDuration(self.transition_duration // 2)
        to_fade.setStartValue(0.0)
        to_fade.setEndValue(1.0)
        to_fade.setStartDelay(self.transition_duration // 2)
        
        self.current_animation_group.addAnimation(from_fade)
        self.current_animation_group.addAnimation(to_fade)
        
        self.current_animation_group.finished.connect(
            lambda: self._finish_fade_transition(from_widget, to_widget)
        )
        
        self.current_animation_group.start()
    
    def _scale_transition(self, from_widget, to_widget):
        """Scale transition - expand from source to target."""
        from_geometry = from_widget.geometry()
        to_geometry = to_widget.geometry()
        
        # Start target widget at center of source widget
        center_x = from_geometry.center().x() - to_geometry.width() // 2
        center_y = from_geometry.center().y() - to_geometry.height() // 2
        start_geometry = from_geometry  # Start small
        
        to_widget.setGeometry(start_geometry)
        to_widget.show()
        
        # Create scale animation
        self.current_animation_group = QParallelAnimationGroup()
        
        # Scale geometry
        scale_anim = QPropertyAnimation(to_widget, b"geometry")
        scale_anim.setDuration(self.transition_duration)
        scale_anim.setStartValue(start_geometry)
        scale_anim.setEndValue(to_geometry)
        scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Fade out source
        from_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
        fade_out.setDuration(self.transition_duration // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        
        self.current_animation_group.addAnimation(scale_anim)
        self.current_animation_group.addAnimation(fade_out)
        
        self.current_animation_group.finished.connect(
            lambda: self._finish_scale_transition(from_widget, to_widget)
        )
        
        self.current_animation_group.start()
    
    def _finish_morph_transition(self, from_widget, to_widget, from_state, to_state):
        """Finish morph transition cleanup."""
        from_widget.hide()
        from_widget.setGraphicsEffect(None)  # Remove opacity effect
        to_widget.setGraphicsEffect(None)   # Remove opacity effect
        
        self._finish_transition(from_state, to_state)
    
    def _finish_fade_transition(self, from_widget, to_widget):
        """Finish fade transition cleanup."""
        from_widget.hide()
        from_widget.setGraphicsEffect(None)
        to_widget.setGraphicsEffect(None)
        
        self._finish_transition("fade", "fade")
    
    def _finish_scale_transition(self, from_widget, to_widget):
        """Finish scale transition cleanup."""
        from_widget.hide()
        from_widget.setGraphicsEffect(None)
        
        self._finish_transition("scale", "scale")
    
    def _finish_transition(self, from_state, to_state):
        """Generic transition cleanup."""
        self.is_transitioning = False
        self.current_animation_group = None
        self.transition_finished.emit(from_state, to_state)
    
    def cancel_current_transition(self):
        """Cancel any running transition."""
        if self.current_animation_group and self.current_animation_group.state() == QPropertyAnimation.State.Running:
            self.current_animation_group.stop()
            self.is_transitioning = False
            self.current_animation_group = None
```

### 4. Accessibility and Keyboard Navigation

**File**: `ghostman/src/ui/behaviors/accessibility.py`

```python
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QKeySequence, QShortcut, QAccessible
from typing import Dict, Callable, List

class AccessibilityManager(QObject):
    """Manages accessibility features and keyboard navigation."""
    
    # Signals
    shortcut_activated = pyqtSignal(str)  # shortcut name
    focus_changed = pyqtSignal(QWidget, QWidget)  # old, new
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.shortcuts: Dict[str, QShortcut] = {}
        self.focus_chain: List[QWidget] = []
        self.current_focus_index = 0
        
        self.setup_shortcuts()
        self.setup_accessibility()
        self.setup_focus_management()
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        shortcuts_config = {
            'toggle_visibility': ('Ctrl+Shift+G', self.toggle_main_window),
            'minimize_to_avatar': ('Escape', self.minimize_to_avatar),
            'show_context_menu': ('F10', self.show_context_menu),
            'focus_input': ('Ctrl+L', self.focus_input_field),
            'clear_conversation': ('Ctrl+Shift+C', self.clear_conversation),
            'new_conversation': ('Ctrl+N', self.new_conversation),
            'save_conversation': ('Ctrl+S', self.save_conversation),
            'show_settings': ('Ctrl+Comma', self.show_settings),
            'show_help': ('F1', self.show_help),
            'next_control': ('Tab', self.focus_next_control),
            'previous_control': ('Shift+Tab', self.focus_previous_control),
        }
        
        for name, (key_sequence, callback) in shortcuts_config.items():
            shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
            shortcut.activated.connect(callback)
            shortcut.activated.connect(lambda n=name: self.shortcut_activated.emit(n))
            self.shortcuts[name] = shortcut
    
    def setup_accessibility(self):
        """Setup accessibility properties for screen readers."""
        # Set accessible names and descriptions
        widgets_accessibility = {
            'main_window': {
                'name': 'Ghostman AI Assistant',
                'description': 'Desktop AI assistant overlay window'
            },
            'conversation_display': {
                'name': 'Conversation History',
                'description': 'Chat history between user and AI assistant'
            },
            'message_input': {
                'name': 'Message Input',
                'description': 'Type your message to the AI assistant here'
            },
            'send_button': {
                'name': 'Send Message',
                'description': 'Send your message to the AI assistant'
            }
        }
        
        # Apply accessibility properties
        for widget_name, props in widgets_accessibility.items():
            widget = getattr(self.main_window, widget_name, None)
            if widget:
                widget.setAccessibleName(props['name'])
                widget.setAccessibleDescription(props['description'])
    
    def setup_focus_management(self):
        """Setup focus management for keyboard navigation."""
        # Connect to focus change events
        QApplication.instance().focusChanged.connect(self.on_focus_changed)
        
        # Build focus chain
        self.rebuild_focus_chain()
    
    def rebuild_focus_chain(self):
        """Rebuild the focus chain for tab navigation."""
        self.focus_chain = []
        
        # Add focusable widgets in logical order
        focusable_widgets = [
            'message_input',
            'send_button',
            'minimize_button',
            'opacity_button',
            'conversation_display'  # Last, as it's read-only
        ]
        
        for widget_name in focusable_widgets:
            widget = getattr(self.main_window, widget_name, None)
            if widget and widget.isEnabled() and widget.isVisible():
                self.focus_chain.append(widget)
    
    def on_focus_changed(self, old_widget: QWidget, new_widget: QWidget):
        """Handle focus change events."""
        self.focus_changed.emit(old_widget, new_widget)
        
        # Update current focus index
        if new_widget in self.focus_chain:
            self.current_focus_index = self.focus_chain.index(new_widget)
    
    def focus_next_control(self):
        """Focus next control in tab order."""
        if not self.focus_chain:
            self.rebuild_focus_chain()
        
        if self.focus_chain:
            self.current_focus_index = (self.current_focus_index + 1) % len(self.focus_chain)
            self.focus_chain[self.current_focus_index].setFocus()
    
    def focus_previous_control(self):
        """Focus previous control in tab order."""
        if not self.focus_chain:
            self.rebuild_focus_chain()
        
        if self.focus_chain:
            self.current_focus_index = (self.current_focus_index - 1) % len(self.focus_chain)
            self.focus_chain[self.current_focus_index].setFocus()
    
    def toggle_main_window(self):
        """Toggle main window visibility."""
        if self.main_window.isVisible():
            self.minimize_to_avatar()
        else:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
    
    def minimize_to_avatar(self):
        """Minimize to avatar state."""
        # Emit signal to window manager
        if hasattr(self.main_window, 'minimize_requested'):
            self.main_window.minimize_requested.emit()
    
    def show_context_menu(self):
        """Show context menu at current position."""
        if hasattr(self.main_window, 'show_context_menu'):
            self.main_window.show_context_menu()
    
    def focus_input_field(self):
        """Focus the message input field."""
        if hasattr(self.main_window, 'message_input'):
            self.main_window.message_input.setFocus()
            self.main_window.message_input.selectAll()
    
    def clear_conversation(self):
        """Clear conversation history."""
        # Implementation depends on conversation manager
        pass
    
    def new_conversation(self):
        """Start new conversation."""
        # Implementation depends on conversation manager
        pass
    
    def save_conversation(self):
        """Save current conversation."""
        # Implementation depends on conversation manager
        pass
    
    def show_settings(self):
        """Show settings dialog."""
        if hasattr(self.main_window, 'show_settings'):
            self.main_window.show_settings()
    
    def show_help(self):
        """Show help dialog."""
        if hasattr(self.main_window, 'show_help'):
            self.main_window.show_help()
    
    def announce_to_screen_reader(self, message: str, priority: str = "polite"):
        """Announce message to screen readers."""
        # Use QAccessible to announce messages
        if priority == "assertive":
            QAccessible.updateAccessibility(
                QAccessible.Event.Alert, 
                self.main_window, 
                0, 
                message
            )
        else:
            QAccessible.updateAccessibility(
                QAccessible.Event.StatusChanged, 
                self.main_window, 
                0, 
                message
            )
    
    def set_shortcut_enabled(self, shortcut_name: str, enabled: bool):
        """Enable or disable specific shortcut."""
        if shortcut_name in self.shortcuts:
            self.shortcuts[shortcut_name].setEnabled(enabled)
    
    def get_shortcuts_help(self) -> str:
        """Get formatted help text for all shortcuts."""
        help_text = "Keyboard Shortcuts:\n\n"
        
        shortcut_descriptions = {
            'toggle_visibility': 'Toggle window visibility',
            'minimize_to_avatar': 'Minimize to avatar',
            'show_context_menu': 'Show context menu',
            'focus_input': 'Focus input field',
            'clear_conversation': 'Clear conversation',
            'new_conversation': 'Start new conversation',
            'save_conversation': 'Save conversation',
            'show_settings': 'Show settings',
            'show_help': 'Show help',
            'next_control': 'Next control',
            'previous_control': 'Previous control',
        }
        
        for name, shortcut in self.shortcuts.items():
            description = shortcut_descriptions.get(name, name.replace('_', ' ').title())
            key_sequence = shortcut.key().toString()
            help_text += f"{key_sequence:<20} {description}\n"
        
        return help_text
```

### 5. Integration with Main Application

**File**: `ghostman/src/app/application.py` (UI behavior integration)

```python
class GhostmanApplication:
    def __init__(self):
        # ... other initialization
        self.setup_ui_behaviors()
    
    def setup_ui_behaviors(self):
        """Initialize UI behavior managers."""
        # Avatar behavior
        self.avatar_behavior = AvatarBehaviorManager(self.window_manager.avatar_widget)
        self.avatar_behavior.avatar_clicked.connect(self.window_manager.show_main_interface)
        self.avatar_behavior.context_menu_requested.connect(self.show_avatar_context_menu)
        
        # Menu animations
        self.menu_manager = MenuAnimationManager(self.window_manager.avatar_widget)
        
        # Window transitions
        self.transition_manager = WindowTransitionManager(self.window_manager)
        
        # Accessibility
        self.accessibility_manager = AccessibilityManager(self.window_manager.prompt_window)
        
        # Connect transition signals to window manager
        self.window_manager.state_changed.connect(self.on_window_state_changed)
    
    def show_avatar_context_menu(self):
        """Show context menu for avatar widget."""
        menu_actions = [
            {'text': 'Open AI Assistant', 'callback': self.window_manager.show_main_interface},
            None,  # Separator
            {'text': 'Settings', 'callback': self.show_settings_dialog},
            {'text': 'Help', 'callback': self.show_help_dialog},
            {'text': 'About', 'callback': self.show_about_dialog},
            None,  # Separator
            {'text': 'Quit', 'callback': self.quit_application}
        ]
        
        self.menu_manager.show_context_menu(menu_actions)
    
    def on_window_state_changed(self, old_state, new_state):
        """Handle window state changes with smooth transitions."""
        from .app.window_manager import WindowState
        
        # Use appropriate transition based on state change
        if old_state == WindowState.AVATAR and new_state == WindowState.MAIN_INTERFACE:
            # Don't use transition manager here as window manager already handles visibility
            # Just announce to screen reader
            self.accessibility_manager.announce_to_screen_reader("AI Assistant window opened")
        elif old_state == WindowState.MAIN_INTERFACE and new_state == WindowState.AVATAR:
            self.accessibility_manager.announce_to_screen_reader("AI Assistant minimized to avatar")
```

## Testing and Quality Assurance

### Behavior Testing Plan

```python
# ghostman/tests/test_ui_behaviors.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer
import time

class TestAvatarBehavior:
    def test_hover_animation(self, avatar_widget):
        """Test hover animation triggers correctly."""
        behavior = AvatarBehaviorManager(avatar_widget)
        
        # Simulate mouse enter
        QTest.mouseMove(avatar_widget, avatar_widget.rect().center())
        
        # Check that hover state changed
        assert behavior.is_hovered
    
    def test_click_detection(self, avatar_widget):
        """Test click vs drag detection."""
        behavior = AvatarBehaviorManager(avatar_widget)
        
        # Simulate quick click
        QTest.mouseClick(avatar_widget, Qt.MouseButton.LeftButton)
        
        # Should emit avatar_clicked signal
        # Implementation depends on signal testing framework

class TestMenuAnimations:
    def test_slide_in_animation(self, parent_widget):
        """Test slide-in menu animation."""
        menu_manager = MenuAnimationManager(parent_widget)
        
        actions = [{'text': 'Test Action', 'callback': lambda: None}]
        menu_manager.show_context_menu(actions, (100, 100))
        
        # Check menu is visible and animating
        assert menu_manager.current_menu is not None
        assert menu_manager.current_menu.isVisible()

class TestWindowTransitions:
    def test_morph_transition(self, window_manager):
        """Test morph transition between avatar and main interface."""
        transition_manager = WindowTransitionManager(window_manager)
        
        # Start transition
        transition_manager.transition_to_main_interface()
        
        # Check transition started
        assert transition_manager.is_transitioning

class TestAccessibility:
    def test_keyboard_shortcuts(self, main_window):
        """Test keyboard shortcuts work correctly."""
        accessibility = AccessibilityManager(main_window)
        
        # Test focus input shortcut
        QTest.keyClick(main_window, Qt.Key_L, Qt.KeyboardModifier.ControlModifier)
        
        # Should focus input field
        assert main_window.message_input.hasFocus()
```

This comprehensive UI/UX behavior system provides smooth, intuitive interactions while maintaining accessibility and performance standards for the Ghostman desktop AI assistant.