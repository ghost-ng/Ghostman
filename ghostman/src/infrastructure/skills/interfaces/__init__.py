"""
Skills system interfaces for Ghostman.

This package provides the core interfaces, abstract classes, and data structures
for implementing skills in the Ghostman AI assistant.

Quick Start:
    >>> from ghostman.src.infrastructure.skills.interfaces import (
    ...     BaseSkill,
    ...     SkillMetadata,
    ...     SkillParameter,
    ...     SkillResult,
    ...     ISkillManager,
    ...     IIntentClassifier
    ... )
    >>>
    >>> # Define a custom skill
    >>> class MySkill(BaseSkill):
    ...     @property
    ...     def metadata(self) -> SkillMetadata:
    ...         return SkillMetadata(
    ...             skill_id="my_skill",
    ...             name="My Skill",
    ...             description="Does something useful",
    ...             category=SkillCategory.CUSTOM,
    ...             icon="star"
    ...         )
    ...
    ...     @property
    ...     def parameters(self) -> List[SkillParameter]:
    ...         return [
    ...             SkillParameter(
    ...                 name="input",
    ...                 type=str,
    ...                 required=True,
    ...                 description="Input text"
    ...             )
    ...         ]
    ...
    ...     async def execute(self, **params) -> SkillResult:
    ...         result = f"Processed: {params['input']}"
    ...         return SkillResult(
    ...             success=True,
    ...             message="Processing complete",
    ...             data={"result": result}
    ...         )

Architecture:
    The skills system follows a clean architecture pattern:

    1. BaseSkill - Abstract base class for all skills
       - Defines metadata, parameters, and execution contract
       - Provides validation and lifecycle hooks
       - Thread-safe execution model

    2. ISkillManager - Skill registry and execution manager
       - Registers and loads skills
       - Validates permissions and parameters
       - Executes skills with proper error handling
       - Tracks execution history

    3. IIntentClassifier - Natural language intent detection
       - Detects user intent from input text
       - Extracts parameters from natural language
       - Returns confidence scores for matches

Design Principles:
    - Type Safety: All interfaces use Python type hints
    - Validation: Parameter validation before execution
    - Error Handling: Graceful error handling with SkillResult
    - Extensibility: Easy to add new skills
    - Testability: Interfaces enable easy mocking

Skill-Specific Modules:
    - screen_capture_skill: Screen capture and annotation
    - task_tracker_skill: Task management and tracking
"""

# Core interfaces
from .base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

from .skill_manager import (
    ISkillManager,
    IIntentClassifier,
    SkillIntent,
    SkillStatus,
    SkillExecutionError,
)

# Screen capture skill types
from .screen_capture_skill import (
    CaptureMode,
    CaptureShape,  # Alias for CaptureMode
    BorderStyle,
    AnnotationType,
    ImageFormat,
    BorderConfig,
    Annotation,
    CaptureRegion,
    CaptureOptions,
    OCRResult,
    CaptureResult,  # Simple result for overlay
    DetailedCaptureResult,  # Detailed result with full metadata
    SimpleCaptureResult,  # Explicit simple result
    ScreenInfo,
)

# Task tracker skill types
from .task_tracker_skill import (
    TaskStatus,
    TaskPriority,
    RecurrenceType,
    TaskFilterType,
    TaskRecurrence,
    Task,
    TaskFilter,
    TaskStatistics,
    TaskListResult,
)

__all__ = [
    # Core interfaces
    "BaseSkill",
    "SkillMetadata",
    "SkillParameter",
    "SkillResult",
    "PermissionType",
    "SkillCategory",
    "ISkillManager",
    "IIntentClassifier",
    "SkillIntent",
    "SkillStatus",
    "SkillExecutionError",
    # Screen capture
    "CaptureMode",
    "CaptureShape",
    "BorderStyle",
    "AnnotationType",
    "ImageFormat",
    "BorderConfig",
    "Annotation",
    "CaptureRegion",
    "CaptureOptions",
    "OCRResult",
    "CaptureResult",
    "DetailedCaptureResult",
    "SimpleCaptureResult",
    "ScreenInfo",
    # Task tracker
    "TaskStatus",
    "TaskPriority",
    "RecurrenceType",
    "TaskFilterType",
    "TaskRecurrence",
    "Task",
    "TaskFilter",
    "TaskStatistics",
    "TaskListResult",
]

# Version information
__version__ = "1.0.0"
__author__ = "Ghostman Team"
