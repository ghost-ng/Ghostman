"""
Skill Registry - Thread-safe registration and lookup of skills.

Provides centralized management of available skills with thread-safe operations
and auto-discovery capabilities.
"""

import logging
from typing import Dict, List, Optional, Type
from threading import Lock

from ..interfaces.base_skill import BaseSkill, SkillMetadata, SkillCategory
from ..interfaces.skill_manager import SkillStatus

logger = logging.getLogger("specter.skills.registry")


class SkillRegistry:
    """
    Thread-safe registry for managing skill instances and metadata.

    The registry maintains a central index of all available skills,
    their instances, and current status.

    Attributes:
        _skills: Dictionary mapping skill_id to skill instance
        _metadata: Dictionary mapping skill_id to SkillMetadata
        _status: Dictionary mapping skill_id to SkillStatus
        _lock: Thread lock for safe concurrent access

    Example:
        >>> registry = SkillRegistry()
        >>> registry.register(ScreenCaptureSkill)
        >>> skill = registry.get("screen_capture")
        >>> all_skills = registry.list_all()
    """

    def __init__(self):
        """Initialize empty skill registry."""
        self._skills: Dict[str, BaseSkill] = {}
        self._metadata: Dict[str, SkillMetadata] = {}
        self._status: Dict[str, SkillStatus] = {}
        self._lock = Lock()

        logger.info("Skill registry initialized")

    def register(self, skill_class: Type[BaseSkill]) -> None:
        """
        Register a skill class with the registry.

        Args:
            skill_class: Class inheriting from BaseSkill

        Raises:
            ValueError: If skill_id already registered
            TypeError: If skill_class does not inherit from BaseSkill
        """
        # Validate skill class
        if not issubclass(skill_class, BaseSkill):
            raise TypeError(f"{skill_class.__name__} must inherit from BaseSkill")

        # Instantiate skill to get metadata
        try:
            skill_instance = skill_class()
        except Exception as e:
            logger.error(f"Failed to instantiate {skill_class.__name__}: {e}")
            raise ValueError(f"Cannot instantiate skill: {e}") from e

        metadata = skill_instance.metadata
        skill_id = metadata.skill_id

        with self._lock:
            # Check for duplicate registration
            if skill_id in self._skills:
                raise ValueError(f"Skill with ID '{skill_id}' is already registered")

            # Register skill
            self._skills[skill_id] = skill_instance
            self._metadata[skill_id] = metadata
            self._status[skill_id] = SkillStatus.LOADED

            logger.info(
                f"✓ Registered skill: {metadata.name} (ID: {skill_id}, "
                f"Category: {metadata.category.value})"
            )

    def unregister(self, skill_id: str) -> bool:
        """
        Unregister and remove a skill from the registry.

        Args:
            skill_id: ID of skill to remove

        Returns:
            True if skill was found and removed, False otherwise
        """
        with self._lock:
            if skill_id not in self._skills:
                logger.warning(f"Cannot unregister unknown skill: {skill_id}")
                return False

            skill_name = self._metadata[skill_id].name

            del self._skills[skill_id]
            del self._metadata[skill_id]
            del self._status[skill_id]

            logger.info(f"✓ Unregistered skill: {skill_name} (ID: {skill_id})")
            return True

    def get(self, skill_id: str) -> Optional[BaseSkill]:
        """
        Retrieve a skill instance by ID.

        Args:
            skill_id: Unique skill identifier

        Returns:
            BaseSkill instance if found, None otherwise
        """
        with self._lock:
            return self._skills.get(skill_id)

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """
        Retrieve skill metadata without loading the full skill.

        Args:
            skill_id: Unique skill identifier

        Returns:
            SkillMetadata if found, None otherwise
        """
        with self._lock:
            return self._metadata.get(skill_id)

    def get_status(self, skill_id: str) -> Optional[SkillStatus]:
        """
        Get current status of a skill.

        Args:
            skill_id: ID of skill to check

        Returns:
            SkillStatus enum value, None if not found
        """
        with self._lock:
            return self._status.get(skill_id)

    def set_status(self, skill_id: str, status: SkillStatus) -> bool:
        """
        Update status of a skill.

        Args:
            skill_id: ID of skill to update
            status: New status value

        Returns:
            True if updated, False if skill not found
        """
        with self._lock:
            if skill_id not in self._status:
                return False

            old_status = self._status[skill_id]
            self._status[skill_id] = status

            logger.debug(
                f"Skill {skill_id} status: {old_status.value} -> {status.value}"
            )
            return True

    def list_all(
        self,
        category: Optional[SkillCategory] = None,
        status: Optional[SkillStatus] = None
    ) -> List[SkillMetadata]:
        """
        List all registered skills with optional filtering.

        Args:
            category: Filter by category (None for all)
            status: Filter by status (None for all)

        Returns:
            List of SkillMetadata objects
        """
        with self._lock:
            results = []

            for skill_id, metadata in self._metadata.items():
                # Apply category filter
                if category and metadata.category != category:
                    continue

                # Apply status filter
                if status and self._status.get(skill_id) != status:
                    continue

                results.append(metadata)

            # Sort by category then name
            results.sort(key=lambda m: (m.category.value, m.name))
            return results

    def list_enabled(self) -> List[SkillMetadata]:
        """
        List all enabled skills.

        Returns:
            List of SkillMetadata for enabled skills
        """
        return self.list_all(status=SkillStatus.ENABLED)

    def exists(self, skill_id: str) -> bool:
        """
        Check if a skill is registered.

        Args:
            skill_id: ID to check

        Returns:
            True if skill is registered
        """
        with self._lock:
            return skill_id in self._skills

    def count(self) -> int:
        """
        Get total number of registered skills.

        Returns:
            Number of skills in registry
        """
        with self._lock:
            return len(self._skills)

    def clear(self) -> None:
        """Remove all skills from registry."""
        with self._lock:
            count = len(self._skills)
            self._skills.clear()
            self._metadata.clear()
            self._status.clear()

            logger.info(f"Registry cleared ({count} skills removed)")

    def get_statistics(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with skill counts by category and status
        """
        with self._lock:
            stats = {
                "total": len(self._skills),
                "by_category": {},
                "by_status": {},
            }

            # Count by category
            for metadata in self._metadata.values():
                category = metadata.category.value
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Count by status
            for status in self._status.values():
                status_name = status.value
                stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1

            return stats


# Decorator for automatic skill registration
def register_skill(registry: SkillRegistry):
    """
    Decorator to automatically register a skill class.

    Args:
        registry: SkillRegistry instance to register with

    Returns:
        Decorator function

    Example:
        >>> registry = SkillRegistry()
        >>>
        >>> @register_skill(registry)
        ... class MySkill(BaseSkill):
        ...     pass
    """
    def decorator(skill_class: Type[BaseSkill]):
        registry.register(skill_class)
        return skill_class
    return decorator
