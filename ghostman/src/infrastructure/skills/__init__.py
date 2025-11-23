"""
Ghostman Skills System - Main Module.

This package provides the skills framework for Ghostman, enabling executable
desktop automation tasks with intent detection and natural language invocation.

Modules:
    - interfaces: Abstract base classes and contracts
    - core: Concrete implementations of skill management
    - skills_library: Built-in skills (email, calendar, file search, etc.)
    - ui: Widgets for skill UI integration

Example Usage:
    >>> from ghostman.src.infrastructure.skills import skill_manager
    >>>
    >>> # Register a skill
    >>> from ghostman.src.infrastructure.skills.skills_library import ScreenCaptureSkill
    >>> skill_manager.register_skill(ScreenCaptureSkill)
    >>>
    >>> # Execute a skill
    >>> result = await skill_manager.execute_skill(
    ...     "screen_capture",
    ...     mode="rectangle"
    ... )
    >>> print(result.message)
"""

from .interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

from .interfaces.skill_manager import (
    ISkillManager,
    IIntentClassifier,
    SkillIntent,
    SkillStatus,
    SkillExecutionError,
)

__all__ = [
    # Base interfaces
    "BaseSkill",
    "SkillMetadata",
    "SkillParameter",
    "SkillResult",
    "PermissionType",
    "SkillCategory",

    # Skill manager
    "ISkillManager",
    "IIntentClassifier",
    "SkillIntent",
    "SkillStatus",
    "SkillExecutionError",
]
