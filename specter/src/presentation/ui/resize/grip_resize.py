"""
Edge Grip Resize System - Thin grips on edges/corners only.

This provides resize functionality using small grip widgets positioned only
on the edges and corners, leaving the content area completely click-through.
"""

import logging
from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QEvent
from PyQt6.QtGui import QMouseEvent, QCursor

from .constraints import SizeConstraints

logger = logging.getLogger("specter.grip_resize")


class EdgeGrip(QLabel):
    """Small grip widget for edge/corner resizing."""
    
    # Signals for resize operations
    drag_started = pyqtSignal(str, QPoint)  # direction, start_pos
    drag_moved = pyqtSignal(str, QPoint)    # direction, current_pos
    drag_ended = pyqtSignal(str, QPoint)    # direction, end_pos
    
    def __init__(self, direction: str, parent=None):
        super().__init__(parent)
        self.direction = direction
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the grip widget UI."""
        # Set size based on grip type (edges only)
        if self.direction in ['top', 'bottom']:
            self.setFixedSize(20, 6)  # Horizontal edge
        elif self.direction in ['left', 'right']:
            self.setFixedSize(6, 20)  # Vertical edge
        
        # Set cursor for resize direction
        cursor_map = {
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor
        }
        self.setCursor(cursor_map.get(self.direction, Qt.CursorShape.ArrowCursor))
        
        # Styling for visibility
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(70, 130, 180, 0.3);
                border: 1px solid rgba(70, 130, 180, 0.6);
            }
            QLabel:hover {
                background-color: rgba(255, 215, 0, 0.5);
                border: 1px solid rgba(255, 215, 0, 0.8);
            }
        """)
        
        # Set tooltip
        self.setToolTip(f"Drag to resize {self.direction}")
        
        logger.debug(f"Created {self.direction} grip")
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press to start drag."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            
            # Highlight grip during drag
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 140, 0, 0.7);
                    border: 2px solid rgba(255, 140, 0, 1.0);
                }
            """)
            
            self.drag_started.emit(self.direction, self.drag_start_pos)
            logger.debug(f"Started dragging {self.direction} grip")
            
        event.accept()  # Always accept to prevent propagation
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move during drag."""
        if self.is_dragging:
            current_pos = event.globalPosition().toPoint()
            self.drag_moved.emit(self.direction, current_pos)
            
        event.accept()
        
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end drag."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            end_pos = event.globalPosition().toPoint()
            
            # Reset styling
            self.setStyleSheet("""
                QLabel {
                    background-color: rgba(70, 130, 180, 0.3);
                    border: 1px solid rgba(70, 130, 180, 0.6);
                }
                QLabel:hover {
                    background-color: rgba(255, 215, 0, 0.5);
                    border: 1px solid rgba(255, 215, 0, 0.8);
                }
            """)
            
            self.drag_ended.emit(self.direction, end_pos)
            logger.debug(f"Finished dragging {self.direction} grip")
                
        event.accept()


class GripResizeManager(QWidget):
    """Manager for edge grip resize system."""
    
    # Signals for resize operations
    resize_started = pyqtSignal(str)        # direction
    resize_updated = pyqtSignal(str, int, int)  # direction, width, height
    resize_finished = pyqtSignal(str, int, int)  # direction, width, height
    
    def __init__(self, parent_widget: QWidget, constraints: Optional[SizeConstraints] = None):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.constraints = constraints or SizeConstraints()
        self.grips: Dict[str, EdgeGrip] = {}
        self.visible = False
        
        # Resize state
        self.is_resizing = False
        self.resize_direction = None
        self.resize_start_geometry = QRect()
        self.drag_start_pos = QPoint()  # Mouse global position at drag start
        
        self._create_grips()
        self._setup_positioning()
        
    def _create_grips(self):
        """Create grip widgets for edges only."""
        # 4 grips: edges only (no corners)
        directions = ['top', 'bottom', 'left', 'right']
        
        for direction in directions:
            # Make grips direct children of the parent widget
            grip = EdgeGrip(direction, self.parent_widget)
            grip.drag_started.connect(self._on_drag_started)
            grip.drag_moved.connect(self._on_drag_moved)
            grip.drag_ended.connect(self._on_drag_ended)
            grip.hide()  # Start hidden
            
            self.grips[direction] = grip
            
        logger.debug(f"Created {len(directions)} edge grips")
        
    def _setup_positioning(self):
        """Setup automatic positioning when parent resizes."""
        if self.parent_widget:
            # Install event filter but NEVER return True (always let events pass through)
            self.parent_widget.installEventFilter(self)
            
    def _update_grip_positions(self):
        """Update grip positions based on parent widget size."""
        if not self.parent_widget:
            return
            
        parent_size = self.parent_widget.size()
        w, h = parent_size.width(), parent_size.height()
        
        # Position grips on edges only
        positions = {
            'top': QPoint(w//2 - 10, 0),
            'bottom': QPoint(w//2 - 10, h - 6),
            'left': QPoint(0, h//2 - 10),
            'right': QPoint(w - 6, h//2 - 10)
        }
        
        # Position grips
        for direction, pos in positions.items():
            if direction in self.grips:
                grip = self.grips[direction]
                grip.move(pos)
                logger.debug(f"Positioned {direction} grip at {pos}")
                
        logger.debug(f"Updated grip positions for {parent_size} widget")
        
    def show_grips(self):
        """Show all grips."""
        self.visible = True
        self._update_grip_positions()
        
        for grip in self.grips.values():
            grip.show()
            grip.raise_()  # Ensure grips are on top
            
        logger.debug("Grips shown")
        
    def hide_grips(self):
        """Hide all grips."""
        self.visible = False
        
        for grip in self.grips.values():
            grip.hide()
            
        logger.debug("Grips hidden")
        
    def eventFilter(self, obj, event):
        """Handle parent widget events - NEVER return True."""
        if obj == self.parent_widget:
            if event.type() == QEvent.Type.Resize:
                if self.visible:
                    self._update_grip_positions()
        
        # CRITICAL: Always return False to let events pass through
        return False
        
    def _on_drag_started(self, direction: str, start_pos: QPoint):
        """Handle drag start."""
        self.is_resizing = True
        self.resize_direction = direction
        self.resize_start_geometry = self.parent_widget.geometry()
        self.drag_start_pos = start_pos  # Mouse global position at drag start

        self.resize_started.emit(direction)
        logger.debug(f"Grip resize started - direction: {direction}")
        
    def _on_drag_moved(self, direction: str, current_pos: QPoint):
        """Handle drag movement with resize logic."""
        if not self.is_resizing or direction != self.resize_direction:
            return

        # Calculate delta from the mouse's drag start position (NOT window position).
        # Both current_pos and drag_start_pos are global screen coordinates.
        delta = current_pos - self.drag_start_pos
        
        # Calculate new geometry based on direction
        new_geometry = self._calculate_new_geometry(direction, delta)
        
        # Apply constraints
        constrained_geometry = self._apply_constraints(new_geometry, direction)
        
        # Update widget geometry
        self.parent_widget.setGeometry(constrained_geometry)
        
        # Emit update signal
        self.resize_updated.emit(
            direction,
            constrained_geometry.width(),
            constrained_geometry.height()
        )
        
    def _on_drag_ended(self, direction: str, end_pos: QPoint):
        """Handle drag end."""
        if not self.is_resizing or direction != self.resize_direction:
            return
            
        final_geometry = self.parent_widget.geometry()
        
        self.resize_finished.emit(
            direction,
            final_geometry.width(),
            final_geometry.height()
        )
        
        self.is_resizing = False
        self.resize_direction = None
        self.resize_start_geometry = QRect()
        self.drag_start_pos = QPoint()

        logger.debug(f"Grip resize finished - direction: {direction}")
        
    def _calculate_new_geometry(self, direction: str, delta: QPoint) -> QRect:
        """Calculate new geometry based on resize direction."""
        start_geo = self.resize_start_geometry
        
        x, y = start_geo.x(), start_geo.y()
        w, h = start_geo.width(), start_geo.height()
        
        # Handle different grip directions
        if 'left' in direction:
            x = start_geo.x() + delta.x()
            w = start_geo.width() - delta.x()
        if 'right' in direction:
            w = start_geo.width() + delta.x()
        if 'top' in direction:
            y = start_geo.y() + delta.y()
            h = start_geo.height() - delta.y()
        if 'bottom' in direction:
            h = start_geo.height() + delta.y()
            
        return QRect(x, y, w, h)
        
    def _apply_constraints(self, geometry: QRect, direction: str) -> QRect:
        """Apply size constraints to geometry."""
        # Apply size constraints
        constrained_w, constrained_h = self.constraints.constrain_size(
            geometry.width(), geometry.height()
        )
        
        # Adjust position for left/top edge resizing
        x, y = geometry.x(), geometry.y()
        
        if constrained_w != geometry.width() and 'left' in direction:
            x = geometry.right() - constrained_w
            
        if constrained_h != geometry.height() and 'top' in direction:
            y = geometry.bottom() - constrained_h
            
        return QRect(x, y, constrained_w, constrained_h)
        
    def cleanup(self):
        """Clean up resources."""
        if self.parent_widget:
            self.parent_widget.removeEventFilter(self)
        self.hide_grips()
        
    # Compatibility methods for existing code
    def show_arrows(self, auto_hide: bool = False):
        """Compatibility method - show grips."""
        self.show_grips()
        
    def hide_arrows(self):
        """Compatibility method - hide grips."""
        self.hide_grips()
        
    def set_always_visible(self, always_visible: bool):
        """Compatibility method - set grips visibility."""
        if always_visible:
            self.show_grips()
        else:
            self.hide_grips()
            
    @property
    def arrows(self):
        """Compatibility property - return grips as arrows."""
        return self.grips