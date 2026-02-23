"""
Two-State Machine for Specter Application.

Manages state transitions between Avatar mode and Tray mode with
proper validation, event handling, and persistence.
"""

import logging
from typing import Callable, List, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from ..models.app_state import AppState, StateTransition, StateChangeEvent

logger = logging.getLogger("specter.state_machine")


class TwoStateMachine(QObject):
    """
    State machine managing transitions between Avatar and Tray modes.
    
    Features:
    - Two primary states: AVATAR (maximized) and TRAY (minimized)
    - Validated state transitions
    - Event emission for UI updates
    - State persistence through settings
    - Transition history for debugging
    """
    
    # Signals for state changes
    state_changed = pyqtSignal(StateChangeEvent)
    before_state_change = pyqtSignal(AppState, AppState)
    after_state_change = pyqtSignal(AppState)
    
    # Valid transitions mapping
    VALID_TRANSITIONS = {
        AppState.AVATAR: {
            AppState.TRAY: StateTransition.AVATAR_TO_TRAY
        },
        AppState.TRAY: {
            AppState.AVATAR: StateTransition.TRAY_TO_AVATAR
        }
    }
    
    def __init__(self, settings_manager=None):
        super().__init__()
        self._settings = settings_manager
        self._current_state = AppState.TRAY  # Start in tray mode
        self._previous_state = None
        self._transition_history: List[StateChangeEvent] = []
        self._state_change_callbacks: List[Callable[[StateChangeEvent], None]] = []
        
        # Load initial state from settings
        if self._settings:
            saved_state = self._settings.get('app.current_state', 'tray')
            try:
                self._current_state = AppState(saved_state)
                logger.info(f"Loaded initial state: {self._current_state.value}")
            except ValueError:
                logger.warning(f"Invalid saved state '{saved_state}', defaulting to TRAY")
                self._current_state = AppState.TRAY
    
    @property
    def current_state(self) -> AppState:
        """Get the current application state."""
        return self._current_state
    
    @property
    def previous_state(self) -> Optional[AppState]:
        """Get the previous application state."""
        return self._previous_state
    
    @property
    def is_avatar_mode(self) -> bool:
        """Check if currently in avatar (maximized) mode."""
        return self._current_state == AppState.AVATAR
    
    @property
    def is_tray_mode(self) -> bool:
        """Check if currently in tray (minimized) mode."""
        return self._current_state == AppState.TRAY
    
    def can_transition_to(self, target_state: AppState) -> bool:
        """
        Check if transition to target state is valid.
        
        Args:
            target_state: The state to transition to
            
        Returns:
            True if transition is valid, False otherwise
        """
        if target_state == self._current_state:
            return False  # No transition needed
            
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, {})
    
    def transition_to(self, target_state: AppState, trigger: str = "user_action", 
                      metadata: Optional[dict] = None) -> bool:
        """
        Transition to the target state.
        
        Args:
            target_state: The state to transition to
            trigger: What triggered this transition
            metadata: Additional data about the transition
            
        Returns:
            True if transition was successful, False otherwise
        """
        # Validate transition
        if not self.can_transition_to(target_state):
            if target_state == self._current_state:
                logger.debug(f"Already in state {target_state.value}, no transition needed")
                return True
            else:
                logger.warning(f"Invalid transition from {self._current_state.value} to {target_state.value}")
                return False
        
        # Get transition type
        transition = self.VALID_TRANSITIONS[self._current_state][target_state]
        
        # Emit before state change signal
        self.before_state_change.emit(self._current_state, target_state)
        
        # Create state change event
        event = StateChangeEvent(
            from_state=self._current_state,
            to_state=target_state,
            transition=transition,
            timestamp=datetime.now(),
            trigger=trigger,
            metadata=metadata or {}
        )
        
        # Perform the transition
        self._previous_state = self._current_state
        self._current_state = target_state
        
        # Save to settings
        if self._settings:
            self._settings.set('app.current_state', target_state.value)
        
        # Add to history
        self._transition_history.append(event)
        
        # Keep only last 100 transitions
        if len(self._transition_history) > 100:
            self._transition_history = self._transition_history[-100:]
        
        # Emit signals
        self.state_changed.emit(event)
        self.after_state_change.emit(target_state)
        
        # Call registered callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
        
        logger.info(f"State transition: {self._previous_state.value} -> {target_state.value} ({trigger})")
        return True
    
    def toggle_state(self, trigger: str = "toggle") -> bool:
        """
        Toggle between Avatar and Tray modes.
        
        Args:
            trigger: What triggered this toggle
            
        Returns:
            True if toggle was successful, False otherwise
        """
        target_state = AppState.TRAY if self._current_state == AppState.AVATAR else AppState.AVATAR
        return self.transition_to(target_state, trigger)
    
    def to_avatar_mode(self, trigger: str = "show_avatar") -> bool:
        """Transition to Avatar (maximized) mode."""
        return self.transition_to(AppState.AVATAR, trigger)
    
    def to_tray_mode(self, trigger: str = "minimize_to_tray") -> bool:
        """Transition to Tray (minimized) mode."""
        return self.transition_to(AppState.TRAY, trigger)
    
    def add_state_change_callback(self, callback: Callable[[StateChangeEvent], None]):
        """Add a callback to be called on state changes."""
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[StateChangeEvent], None]):
        """Remove a state change callback."""
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
    
    def get_transition_history(self, limit: int = 10) -> List[StateChangeEvent]:
        """Get recent transition history."""
        return self._transition_history[-limit:]
    
    def clear_history(self):
        """Clear transition history."""
        self._transition_history.clear()
        logger.debug("Transition history cleared")
    
    def get_state_info(self) -> dict:
        """Get comprehensive state information for debugging."""
        return {
            'current_state': self._current_state.value,
            'previous_state': self._previous_state.value if self._previous_state else None,
            'is_avatar_mode': self.is_avatar_mode,
            'is_tray_mode': self.is_tray_mode,
            'transition_count': len(self._transition_history),
            'last_transition': self._transition_history[-1] if self._transition_history else None
        }