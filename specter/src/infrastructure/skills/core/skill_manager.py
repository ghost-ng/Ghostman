"""
Unified Skill Manager - Central orchestrator for the skills system.

Provides a unified interface for registering, discovering, and executing skills,
combining the skill registry, intent classifier, and executor.
"""

import logging
from typing import List, Optional, Dict, Any, Callable, Type

from ..interfaces.base_skill import BaseSkill, SkillMetadata, PermissionType
from ..interfaces.skill_manager import (
    ISkillManager,
    SkillIntent,
    SkillStatus,
    SkillResult,
    SkillExecutionError
)

from .skill_registry import SkillRegistry
from .intent_classifier import IntentClassifier
from .skill_executor import SkillExecutor, ExecutionRecord

logger = logging.getLogger("specter.skills.manager")


class SkillManager(ISkillManager):
    """
    Central manager for the skills system.

    Orchestrates all skill operations by coordinating the registry,
    intent classifier, and executor components.

    This is the main entry point for skill interactions in Specter.

    Attributes:
        _registry: Skill registry for skill storage and lookup
        _classifier: Intent classifier for detecting user intent
        _executor: Skill executor for running skills
        _permissions_granted: Set of granted permissions

    Example:
        >>> manager = SkillManager()
        >>>
        >>> # Register skills
        >>> manager.register_skill(ScreenCaptureSkill)
        >>> manager.register_skill(TaskTrackerSkill)
        >>>
        >>> # Detect and execute from natural language
        >>> intent = await manager.detect_intent("take a screenshot")
        >>> if intent:
        ...     result = await manager.execute_skill(
        ...         intent.skill_id,
        ...         **intent.parameters
        ...     )
        ...     print(result.message)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        use_ai_fallback: bool = None,  # None = read from settings
        max_history: int = 100
    ):
        """
        Initialize skill manager.

        Args:
            confidence_threshold: Minimum confidence for intent detection (default 0.75)
            use_ai_fallback: Whether to use AI for ambiguous intent detection
                            (None = read from settings, explicit True/False overrides)
            max_history: Maximum execution records to keep (default 100)
        """
        # Read AI fallback setting from config if not explicitly set
        if use_ai_fallback is None:
            try:
                from ...storage.settings_manager import settings
                use_ai_fallback = settings.get('advanced.enable_ai_intent_classification', False)
                logger.debug(f"AI fallback from settings: {use_ai_fallback}")
            except Exception as e:
                logger.warning(f"Could not read AI fallback setting: {e}")
                use_ai_fallback = False

        self._registry = SkillRegistry()
        self._classifier = IntentClassifier(
            confidence_threshold=confidence_threshold,
            use_ai_fallback=use_ai_fallback
        )
        self._executor = SkillExecutor(
            max_history=max_history,
            permission_validator=self._validate_permissions_internal,
            confirmation_requester=self._request_confirmation_internal
        )

        # Permission management
        self._permissions_granted: set[PermissionType] = set()

        # Auto-grant safe permissions
        self._permissions_granted.add(PermissionType.CLIPBOARD_ACCESS)
        self._permissions_granted.add(PermissionType.SCREEN_CAPTURE)
        self._permissions_granted.add(PermissionType.NETWORK_ACCESS)
        self._permissions_granted.add(PermissionType.FILE_READ)
        self._permissions_granted.add(PermissionType.FILE_WRITE)
        self._permissions_granted.add(PermissionType.OUTLOOK_ACCESS)

        logger.info(f"Skill manager initialized (AI fallback: {use_ai_fallback})")

    @property
    def registry(self) -> SkillRegistry:
        """Public accessor for the skill registry."""
        return self._registry

    def register_skill(self, skill_class: Type[BaseSkill]) -> None:
        """
        Register a skill class with the manager.

        Args:
            skill_class: Class inheriting from BaseSkill

        Raises:
            ValueError: If skill_id already registered
            TypeError: If skill_class does not inherit from BaseSkill
        """
        self._registry.register(skill_class)

        # Enable skill by default if metadata says so
        skill_instance = self._registry.get(skill_class().metadata.skill_id)
        if skill_instance and skill_instance.metadata.enabled_by_default:
            self.enable_skill(skill_instance.metadata.skill_id)

    def unregister_skill(self, skill_id: str) -> bool:
        """
        Unregister and remove a skill from the manager.

        Args:
            skill_id: ID of skill to remove

        Returns:
            True if skill was found and removed, False otherwise
        """
        # Unregister from classifier
        self._classifier.unregister_patterns(skill_id)

        # Unregister from registry
        return self._registry.unregister(skill_id)

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """
        Retrieve a skill instance by ID.

        Args:
            skill_id: Unique skill identifier

        Returns:
            BaseSkill instance if found, None otherwise
        """
        return self._registry.get(skill_id)

    def get_skill_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """
        Retrieve skill metadata without loading the full skill.

        Args:
            skill_id: Unique skill identifier

        Returns:
            SkillMetadata if found, None otherwise
        """
        return self._registry.get_metadata(skill_id)

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
        """
        from ..interfaces.base_skill import SkillCategory

        # Convert string category to enum if provided
        category_enum = None
        if category:
            try:
                category_enum = SkillCategory(category)
            except ValueError:
                logger.warning(f"Invalid category: {category}")

        status_filter = SkillStatus.ENABLED if enabled_only else None

        return self._registry.list_all(category=category_enum, status=status_filter)

    async def execute_skill(
        self,
        skill_id: str,
        skip_confirmation: bool = False,
        **parameters: Any
    ) -> SkillResult:
        """
        Execute a skill with the given parameters.

        Args:
            skill_id: ID of skill to execute
            skip_confirmation: Skip confirmation prompt even if skill requires it
            **parameters: Skill parameters

        Returns:
            SkillResult from execution

        Raises:
            SkillExecutionError: If execution fails catastrophically
            ValueError: If skill not found or disabled
        """
        # Get skill instance
        skill = self._registry.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        # Check if skill is enabled
        status = self._registry.get_status(skill_id)
        if status != SkillStatus.ENABLED:
            raise ValueError(f"Skill is not enabled: {skill_id} (status: {status.value if status else 'unknown'})")

        # Execute skill
        return await self._executor.execute(
            skill=skill,
            skip_confirmation=skip_confirmation,
            **parameters
        )

    def enable_skill(self, skill_id: str) -> bool:
        """
        Enable a registered skill.

        Args:
            skill_id: ID of skill to enable

        Returns:
            True if enabled successfully, False if not found
        """
        if not self._registry.exists(skill_id):
            return False

        success = self._registry.set_status(skill_id, SkillStatus.ENABLED)
        if success:
            logger.info(f"✓ Enabled skill: {skill_id}")
        return success

    def disable_skill(self, skill_id: str) -> bool:
        """
        Disable an enabled skill.

        Args:
            skill_id: ID of skill to disable

        Returns:
            True if disabled successfully, False if not found
        """
        if not self._registry.exists(skill_id):
            return False

        success = self._registry.set_status(skill_id, SkillStatus.DISABLED)
        if success:
            logger.info(f"✓ Disabled skill: {skill_id}")
        return success

    def is_skill_enabled(self, skill_id: str) -> bool:
        """
        Check if a skill is enabled.

        Args:
            skill_id: ID of skill to check

        Returns:
            True if enabled, False otherwise
        """
        status = self._registry.get_status(skill_id)
        return status == SkillStatus.ENABLED

    def get_skill_status(self, skill_id: str) -> Optional[SkillStatus]:
        """
        Get current status of a skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            SkillStatus enum value, None if not found
        """
        return self._registry.get_status(skill_id)

    async def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        """
        Detect if user input matches any skill's intent patterns.

        Args:
            user_input: User's natural language input

        Returns:
            SkillIntent if a match is found above threshold, None otherwise
        """
        return await self._classifier.detect_intent(user_input)

    def register_intent_patterns(
        self,
        skill_id: str,
        patterns: List[str],
        parameter_extractors: Optional[Dict[str, Callable[[str], Any]]] = None
    ) -> None:
        """
        Register intent detection patterns for a skill.

        Args:
            skill_id: ID of skill to register patterns for
            patterns: List of pattern strings/regexes
            parameter_extractors: Optional dict mapping parameter names to extractor functions
        """
        self._classifier.register_patterns(skill_id, patterns, parameter_extractors)

    def on_skill_executed(self, callback: Callable[[str, SkillResult], None]) -> None:
        """
        Register a callback to be notified when any skill executes.

        Args:
            callback: Function called with (skill_id, result) after execution
        """
        self._executor.register_callback(callback)

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
        """
        records = self._executor.get_history(skill_id=skill_id, limit=limit)

        # Convert ExecutionRecord to dict
        return [
            {
                "skill_id": r.skill_id,
                "parameters": r.parameters,
                "result": r.result,
                "timestamp": r.timestamp,
                "duration_ms": r.duration_ms,
                "success": r.result.success,
                "error": r.error,
            }
            for r in records
        ]

    def clear_execution_history(self, skill_id: Optional[str] = None) -> int:
        """
        Clear execution history.

        Args:
            skill_id: Clear specific skill history (None for all)

        Returns:
            Number of records cleared
        """
        return self._executor.clear_history(skill_id=skill_id)

    def validate_permissions(self, skill_id: str) -> bool:
        """
        Check if all required permissions are granted for a skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            True if all permissions granted, False otherwise
        """
        skill = self._registry.get(skill_id)
        if not skill:
            return False

        required_permissions = skill.metadata.permissions_required

        return all(perm in self._permissions_granted for perm in required_permissions)

    def request_permissions(self, skill_id: str) -> bool:
        """
        Request required permissions from user for a skill.

        Args:
            skill_id: ID of skill requiring permissions

        Returns:
            True if all permissions granted, False if denied
        """
        skill = self._registry.get(skill_id)
        if not skill:
            return False

        required_permissions = skill.metadata.permissions_required

        # For now, auto-grant all permissions (TODO: Show UI dialog)
        for perm in required_permissions:
            self._permissions_granted.add(perm)
            logger.debug(f"Auto-granted permission: {perm.value}")

        return True

    def grant_permission(self, permission: PermissionType) -> None:
        """
        Manually grant a permission.

        Args:
            permission: Permission to grant
        """
        self._permissions_granted.add(permission)
        logger.info(f"✓ Granted permission: {permission.value}")

    def revoke_permission(self, permission: PermissionType) -> None:
        """
        Manually revoke a permission.

        Args:
            permission: Permission to revoke
        """
        self._permissions_granted.discard(permission)
        logger.info(f"✗ Revoked permission: {permission.value}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the skills system.

        Returns:
            Dictionary with statistics
        """
        return {
            "registry": self._registry.get_statistics(),
            "classifier": self._classifier.get_statistics(),
            "executor": self._executor.get_statistics(),
            "permissions_granted": [p.value for p in self._permissions_granted],
        }

    # Internal methods

    def _validate_permissions_internal(self, required_permissions: List[PermissionType]) -> bool:
        """
        Internal permission validator for skill executor.

        Args:
            required_permissions: List of required permissions

        Returns:
            True if all permissions granted
        """
        return all(perm in self._permissions_granted for perm in required_permissions)

    def _request_confirmation_internal(self, skill: BaseSkill, parameters: Dict[str, Any]) -> bool:
        """
        Internal confirmation requester for skill executor.

        Args:
            skill: Skill to execute
            parameters: Execution parameters

        Returns:
            True if user confirmed (currently auto-confirms)
        """
        # TODO: Show Qt dialog requesting confirmation
        # For now, auto-confirm all
        logger.debug(f"Auto-confirming execution of {skill.metadata.name}")
        return True


# Global skill manager instance
skill_manager = SkillManager()
