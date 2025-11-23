"""
Skill manager interface for registering, discovering, and executing skills.

This module defines the interface for managing the lifecycle of skills
in the Ghostman application.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .base_skill import BaseSkill, SkillResult, SkillMetadata


class SkillStatus(Enum):
    """Current status of a skill in the system."""

    REGISTERED = "registered"  # Skill is registered but not loaded
    LOADED = "loaded"  # Skill class loaded and ready
    ENABLED = "enabled"  # Skill is active and can be executed
    DISABLED = "disabled"  # Skill is loaded but temporarily disabled
    ERROR = "error"  # Skill failed to load or has configuration error


@dataclass
class SkillIntent:
    """
    Detected user intent to execute a skill.

    Attributes:
        skill_id: ID of the skill to execute
        confidence: Confidence score (0.0 to 1.0)
        parameters: Extracted parameters from user input
        raw_input: Original user input text
        matched_patterns: Patterns that triggered detection

    Example:
        >>> intent = SkillIntent(
        ...     skill_id="screen_capture",
        ...     confidence=0.95,
        ...     parameters={"mode": "rectangle"},
        ...     raw_input="take a screenshot of a rectangle",
        ...     matched_patterns=["screenshot", "capture"]
        ... )
    """

    skill_id: str
    confidence: float
    parameters: Dict[str, Any]
    raw_input: str
    matched_patterns: List[str]

    def __post_init__(self):
        """Validate intent invariants."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not self.skill_id:
            raise ValueError("skill_id cannot be empty")


class SkillExecutionError(Exception):
    """Raised when skill execution fails catastrophically."""

    def __init__(self, skill_id: str, message: str, original_error: Optional[Exception] = None):
        self.skill_id = skill_id
        self.message = message
        self.original_error = original_error
        super().__init__(f"Skill '{skill_id}' failed: {message}")


class ISkillManager(ABC):
    """
    Interface for managing skills in the Ghostman application.

    The skill manager is responsible for:
    - Registering and loading skills
    - Enabling/disabling skills
    - Executing skills with parameter validation
    - Detecting user intent to trigger skills
    - Managing skill lifecycle and state

    Usage Example:
        >>> manager = SkillManager()
        >>>
        >>> # Register a skill
        >>> manager.register_skill(ScreenCaptureSkill)
        >>>
        >>> # Detect intent from user input
        >>> intent = await manager.detect_intent("take a screenshot")
        >>> if intent and intent.confidence > 0.8:
        ...     result = await manager.execute_skill(
        ...         intent.skill_id,
        ...         **intent.parameters
        ...     )
        ...     print(result.message)
        >>>
        >>> # List available skills
        >>> skills = manager.list_skills(enabled_only=True)
        >>> for skill_meta in skills:
        ...     print(f"{skill_meta.name}: {skill_meta.description}")
    """

    @abstractmethod
    def register_skill(self, skill_class: type[BaseSkill]) -> None:
        """
        Register a skill class with the manager.

        The skill is loaded and validated but not automatically enabled.
        Use enable_skill() to activate it.

        Args:
            skill_class: Class inheriting from BaseSkill

        Raises:
            ValueError: If skill_id already registered
            TypeError: If skill_class does not inherit from BaseSkill

        Example:
            >>> manager.register_skill(ScreenCaptureSkill)
            >>> manager.register_skill(TaskTrackerSkill)
        """
        pass

    @abstractmethod
    def unregister_skill(self, skill_id: str) -> bool:
        """
        Unregister and remove a skill from the manager.

        Args:
            skill_id: ID of skill to remove

        Returns:
            True if skill was found and removed, False otherwise

        Example:
            >>> manager.unregister_skill("screen_capture")
            True
        """
        pass

    @abstractmethod
    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """
        Retrieve a skill instance by ID.

        Args:
            skill_id: Unique skill identifier

        Returns:
            BaseSkill instance if found, None otherwise

        Example:
            >>> skill = manager.get_skill("screen_capture")
            >>> if skill:
            ...     print(skill.metadata.description)
        """
        pass

    @abstractmethod
    def get_skill_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """
        Retrieve skill metadata without loading the full skill.

        Useful for displaying skill information in UI without
        instantiating the skill.

        Args:
            skill_id: Unique skill identifier

        Returns:
            SkillMetadata if found, None otherwise

        Example:
            >>> metadata = manager.get_skill_metadata("screen_capture")
            >>> if metadata:
            ...     print(f"{metadata.name} - {metadata.description}")
        """
        pass

    @abstractmethod
    def list_skills(
        self,
        category: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[SkillMetadata]:
        """
        List all registered skills.

        Args:
            category: Filter by category (None for all)
            enabled_only: Only return enabled skills

        Returns:
            List of SkillMetadata objects

        Example:
            >>> # All skills
            >>> all_skills = manager.list_skills()
            >>>
            >>> # Only enabled productivity skills
            >>> enabled = manager.list_skills(
            ...     category="productivity",
            ...     enabled_only=True
            ... )
        """
        pass

    @abstractmethod
    async def execute_skill(
        self,
        skill_id: str,
        skip_confirmation: bool = False,
        **parameters: Any
    ) -> SkillResult:
        """
        Execute a skill with the given parameters.

        This method:
        1. Validates the skill is enabled
        2. Validates parameters
        3. Requests user confirmation if needed
        4. Executes the skill
        5. Calls lifecycle hooks (on_success/on_error/cleanup)

        Args:
            skill_id: ID of skill to execute
            skip_confirmation: Skip confirmation prompt even if skill requires it
            **parameters: Skill parameters

        Returns:
            SkillResult from execution

        Raises:
            SkillExecutionError: If execution fails catastrophically
            ValueError: If skill not found or disabled

        Example:
            >>> result = await manager.execute_skill(
            ...     "screen_capture",
            ...     mode="rectangle",
            ...     save_to_clipboard=True
            ... )
            >>> if result.success:
            ...     print(f"Screenshot saved: {result.data['path']}")
            ... else:
            ...     print(f"Error: {result.error}")
        """
        pass

    @abstractmethod
    def enable_skill(self, skill_id: str) -> bool:
        """
        Enable a registered skill.

        Args:
            skill_id: ID of skill to enable

        Returns:
            True if enabled successfully, False if not found

        Example:
            >>> manager.enable_skill("screen_capture")
            True
        """
        pass

    @abstractmethod
    def disable_skill(self, skill_id: str) -> bool:
        """
        Disable an enabled skill.

        Args:
            skill_id: ID of skill to disable

        Returns:
            True if disabled successfully, False if not found

        Example:
            >>> manager.disable_skill("screen_capture")
            True
        """
        pass

    @abstractmethod
    def is_skill_enabled(self, skill_id: str) -> bool:
        """
        Check if a skill is enabled.

        Args:
            skill_id: ID of skill to check

        Returns:
            True if enabled, False otherwise

        Example:
            >>> if manager.is_skill_enabled("screen_capture"):
            ...     print("Screen capture is ready")
        """
        pass

    @abstractmethod
    def get_skill_status(self, skill_id: str) -> Optional[SkillStatus]:
        """
        Get current status of a skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            SkillStatus enum value, None if not found

        Example:
            >>> status = manager.get_skill_status("screen_capture")
            >>> if status == SkillStatus.ERROR:
            ...     print("Skill has configuration error")
        """
        pass

    @abstractmethod
    async def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        """
        Detect if user input matches any skill's intent patterns.

        This method analyzes user input and returns the most likely
        skill intent with extracted parameters.

        Args:
            user_input: User's natural language input

        Returns:
            SkillIntent if a match is found above threshold, None otherwise

        Example:
            >>> intent = await manager.detect_intent("capture my screen")
            >>> if intent:
            ...     print(f"Detected: {intent.skill_id} ({intent.confidence:.2%})")
            ...     print(f"Parameters: {intent.parameters}")
        """
        pass

    @abstractmethod
    def register_intent_patterns(
        self,
        skill_id: str,
        patterns: List[str],
        parameter_extractors: Optional[Dict[str, Callable[[str], Any]]] = None
    ) -> None:
        """
        Register intent detection patterns for a skill.

        Patterns can be:
        - Simple keywords: "screenshot", "capture"
        - Phrases: "take a screenshot", "capture screen"
        - Regex patterns: r"save (?P<filename>.+) to (?P<location>.+)"

        Args:
            skill_id: ID of skill to register patterns for
            patterns: List of pattern strings/regexes
            parameter_extractors: Optional dict mapping parameter names to extractor functions

        Example:
            >>> manager.register_intent_patterns(
            ...     "screen_capture",
            ...     patterns=[
            ...         "screenshot",
            ...         "capture screen",
            ...         r"take a (?P<mode>rectangle|window) screenshot"
            ...     ],
            ...     parameter_extractors={
            ...         "mode": lambda text: "fullscreen" if "full" in text else "rectangle"
            ...     }
            ... )
        """
        pass

    @abstractmethod
    def on_skill_executed(self, callback: Callable[[str, SkillResult], None]) -> None:
        """
        Register a callback to be notified when any skill executes.

        Useful for logging, analytics, or UI updates.

        Args:
            callback: Function called with (skill_id, result) after execution

        Example:
            >>> def log_execution(skill_id: str, result: SkillResult):
            ...     logger.info(f"Skill {skill_id}: {result.message}")
            >>>
            >>> manager.on_skill_executed(log_execution)
        """
        pass

    @abstractmethod
    def get_execution_history(
        self,
        skill_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get history of skill executions.

        Args:
            skill_id: Filter by specific skill (None for all)
            limit: Maximum number of records to return

        Returns:
            List of execution records with timestamp, parameters, result

        Example:
            >>> history = manager.get_execution_history("screen_capture", limit=10)
            >>> for record in history:
            ...     print(f"{record['timestamp']}: {record['result'].message}")
        """
        pass

    @abstractmethod
    def clear_execution_history(self, skill_id: Optional[str] = None) -> int:
        """
        Clear execution history.

        Args:
            skill_id: Clear specific skill history (None for all)

        Returns:
            Number of records cleared

        Example:
            >>> cleared = manager.clear_execution_history("screen_capture")
            >>> print(f"Cleared {cleared} records")
        """
        pass

    @abstractmethod
    def validate_permissions(self, skill_id: str) -> bool:
        """
        Check if all required permissions are granted for a skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            True if all permissions granted, False otherwise

        Example:
            >>> if not manager.validate_permissions("screen_capture"):
            ...     print("Screen capture permission not granted")
        """
        pass

    @abstractmethod
    def request_permissions(self, skill_id: str) -> bool:
        """
        Request required permissions from user for a skill.

        Shows UI dialog to request permissions if not already granted.

        Args:
            skill_id: ID of skill requiring permissions

        Returns:
            True if all permissions granted, False if denied

        Example:
            >>> if manager.request_permissions("screen_capture"):
            ...     print("Permissions granted, skill ready to use")
        """
        pass


class IIntentClassifier(ABC):
    """
    Interface for detecting user intent from natural language input.

    Intent classifiers analyze user input and determine which skill
    (if any) the user wants to execute, along with extracting parameters.

    The classifier may use various techniques:
    - Pattern matching (regex, keywords)
    - Machine learning models
    - Rule-based systems
    - LLM-based classification

    Example Implementation Strategy:
        >>> class SimpleIntentClassifier(IIntentClassifier):
        ...     def __init__(self):
        ...         self.patterns = {}  # skill_id -> list of patterns
        ...
        ...     async def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        ...         # Score each skill's patterns
        ...         best_match = None
        ...         best_score = 0.0
        ...
        ...         for skill_id, patterns in self.patterns.items():
        ...             score = self._score_patterns(user_input, patterns)
        ...             if score > best_score:
        ...                 best_score = score
        ...                 best_match = skill_id
        ...
        ...         if best_score > 0.7:  # Confidence threshold
        ...             return SkillIntent(
        ...                 skill_id=best_match,
        ...                 confidence=best_score,
        ...                 parameters=self._extract_params(user_input, best_match),
        ...                 raw_input=user_input,
        ...                 matched_patterns=[...]
        ...             )
        ...         return None
    """

    @abstractmethod
    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillIntent]:
        """
        Detect skill intent from user input.

        Args:
            user_input: User's natural language input
            context: Optional contextual information (conversation history, etc.)

        Returns:
            SkillIntent if detected above threshold, None otherwise

        Example:
            >>> classifier = IntentClassifier()
            >>> intent = await classifier.detect_intent(
            ...     "take a screenshot of the window",
            ...     context={"previous_skill": "screen_capture"}
            ... )
            >>> if intent:
            ...     print(f"Skill: {intent.skill_id}")
            ...     print(f"Confidence: {intent.confidence:.2%}")
            ...     print(f"Params: {intent.parameters}")
        """
        pass

    @abstractmethod
    def register_patterns(
        self,
        skill_id: str,
        patterns: List[str],
        parameter_extractors: Optional[Dict[str, Callable[[str], Any]]] = None
    ) -> None:
        """
        Register intent patterns for a skill.

        Patterns define how to recognize when a user wants to use a skill.
        Parameter extractors define how to extract parameter values from input.

        Args:
            skill_id: ID of skill
            patterns: List of pattern strings or regexes
            parameter_extractors: Functions to extract parameter values

        Example:
            >>> classifier.register_patterns(
            ...     "task_tracker",
            ...     patterns=[
            ...         r"add task (?P<title>.+)",
            ...         r"create (?P<priority>high|low) priority task (?P<title>.+)",
            ...         "show my tasks"
            ...     ],
            ...     parameter_extractors={
            ...         "priority": lambda text: "high" if "urgent" in text else "medium"
            ...     }
            ... )
        """
        pass

    @abstractmethod
    def unregister_patterns(self, skill_id: str) -> bool:
        """
        Remove all patterns for a skill.

        Args:
            skill_id: ID of skill to unregister

        Returns:
            True if patterns were removed, False if skill not found

        Example:
            >>> classifier.unregister_patterns("task_tracker")
            True
        """
        pass

    @abstractmethod
    def set_confidence_threshold(self, threshold: float) -> None:
        """
        Set minimum confidence score for intent detection.

        Intents with confidence below threshold are not returned.

        Args:
            threshold: Confidence threshold (0.0 to 1.0)

        Example:
            >>> classifier.set_confidence_threshold(0.8)  # Only high-confidence matches
        """
        pass

    @abstractmethod
    def get_confidence_scores(
        self,
        user_input: str
    ) -> Dict[str, float]:
        """
        Get confidence scores for all skills.

        Useful for debugging or showing user multiple options.

        Args:
            user_input: User's input text

        Returns:
            Dict mapping skill_id to confidence score

        Example:
            >>> scores = classifier.get_confidence_scores("capture screen")
            >>> for skill_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            ...     print(f"{skill_id}: {score:.2%}")
            screen_capture: 95.00%
            screen_recorder: 45.00%
        """
        pass
