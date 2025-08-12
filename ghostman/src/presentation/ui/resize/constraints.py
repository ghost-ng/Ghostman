"""
Size Constraints System for Resizable Windows.

Provides flexible size constraint validation and enforcement.
"""

from typing import Optional, Tuple
from PyQt6.QtCore import QSize


class SizeConstraints:
    """
    Manages size constraints for resizable windows.
    
    Provides validation and enforcement of minimum/maximum sizes
    with optional aspect ratio preservation.
    """
    
    def __init__(
        self,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        maintain_aspect_ratio: bool = False,
        aspect_ratio: Optional[float] = None
    ):
        """
        Initialize size constraints.
        
        Args:
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels
            max_width: Maximum width in pixels (None = unlimited)
            max_height: Maximum height in pixels (None = unlimited)
            maintain_aspect_ratio: Whether to maintain aspect ratio during resize
            aspect_ratio: Specific aspect ratio to maintain (width/height)
        """
        self.min_width = min_width
        self.min_height = min_height
        self.max_width = max_width
        self.max_height = max_height
        self.maintain_aspect_ratio = maintain_aspect_ratio
        self.aspect_ratio = aspect_ratio
        
        # Validate constraints
        self._validate_constraints()
    
    def _validate_constraints(self):
        """Validate that constraints are logical."""
        if (self.min_width is not None and self.max_width is not None 
            and self.min_width > self.max_width):
            raise ValueError("min_width cannot be greater than max_width")
        
        if (self.min_height is not None and self.max_height is not None 
            and self.min_height > self.max_height):
            raise ValueError("min_height cannot be greater than max_height")
        
        if self.aspect_ratio is not None and self.aspect_ratio <= 0:
            raise ValueError("aspect_ratio must be positive")
    
    def constrain_size(self, width: int, height: int) -> Tuple[int, int]:
        """
        Apply constraints to a given size.
        
        Args:
            width: Proposed width
            height: Proposed height
            
        Returns:
            Tuple of (constrained_width, constrained_height)
        """
        # Apply min/max constraints first
        if self.min_width is not None:
            width = max(width, self.min_width)
        if self.max_width is not None:
            width = min(width, self.max_width)
        
        if self.min_height is not None:
            height = max(height, self.min_height)
        if self.max_height is not None:
            height = min(height, self.max_height)
        
        # Apply aspect ratio constraint if needed
        if self.maintain_aspect_ratio or self.aspect_ratio is not None:
            width, height = self._apply_aspect_ratio(width, height)
        
        return width, height
    
    def _apply_aspect_ratio(self, width: int, height: int) -> Tuple[int, int]:
        """Apply aspect ratio constraint."""
        if self.aspect_ratio is not None:
            target_ratio = self.aspect_ratio
        else:
            # Use current ratio as target
            target_ratio = width / height if height > 0 else 1.0
        
        # Calculate what the dimensions should be to maintain aspect ratio
        width_by_height = int(height * target_ratio)
        height_by_width = int(width / target_ratio)
        
        # Choose the constraint that keeps us within bounds
        if width_by_height <= width:
            # Height-constrained
            return width_by_height, height
        else:
            # Width-constrained
            return width, height_by_width
    
    def is_size_valid(self, width: int, height: int) -> bool:
        """Check if a size is valid according to constraints."""
        constrained_width, constrained_height = self.constrain_size(width, height)
        return constrained_width == width and constrained_height == height
    
    def get_minimum_size(self) -> QSize:
        """Get the minimum allowed size."""
        min_w = self.min_width if self.min_width is not None else 1
        min_h = self.min_height if self.min_height is not None else 1
        return QSize(min_w, min_h)
    
    def get_maximum_size(self) -> QSize:
        """Get the maximum allowed size."""
        max_w = self.max_width if self.max_width is not None else 16777215  # Qt max
        max_h = self.max_height if self.max_height is not None else 16777215  # Qt max
        return QSize(max_w, max_h)
    
    @classmethod
    def for_avatar(cls) -> 'SizeConstraints':
        """Create constraints suitable for avatar widgets."""
        return cls(
            min_width=80,
            min_height=80,
            max_width=200,
            max_height=200,
            maintain_aspect_ratio=True
        )
    
    @classmethod
    def for_repl(cls) -> 'SizeConstraints':
        """Create constraints suitable for REPL windows."""
        return cls(
            min_width=360,
            min_height=320,
            max_width=None,  # Unlimited
            max_height=None  # Unlimited
        )