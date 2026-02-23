"""
Skill Executor - Async execution coordinator with validation and error handling.

Manages the full skill execution lifecycle including parameter validation,
permission checks, execution, and lifecycle hooks.
"""

import logging
import asyncio
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field

from ..interfaces.base_skill import BaseSkill, SkillResult, PermissionType
from ..interfaces.skill_manager import SkillExecutionError, SkillStatus

logger = logging.getLogger("specter.skills.executor")


@dataclass
class ExecutionRecord:
    """
    Record of a skill execution for history/auditing.

    Attributes:
        skill_id: ID of executed skill
        parameters: Parameters passed to skill
        result: Execution result
        timestamp: When execution occurred
        duration_ms: How long execution took in milliseconds
        error: Error message if execution failed
    """

    skill_id: str
    parameters: Dict[str, Any]
    result: SkillResult
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    error: Optional[str] = None


class SkillExecutor:
    """
    Async execution coordinator for skills.

    Handles the full skill lifecycle:
    1. Parameter validation
    2. Permission checking
    3. User confirmation (if required)
    4. Async execution
    5. Success/error hooks
    6. Cleanup
    7. History tracking

    Attributes:
        _execution_history: List of past executions
        _execution_callbacks: Callbacks notified after execution
        _permission_validator: Function to validate permissions
        _confirmation_requester: Function to request user confirmation
        _max_history: Maximum history records to keep

    Example:
        >>> executor = SkillExecutor()
        >>> skill = ScreenCaptureSkill()
        >>>
        >>> result = await executor.execute(
        ...     skill,
        ...     mode="rectangle",
        ...     save_to_clipboard=True
        ... )
        >>> print(result.message)
    """

    def __init__(
        self,
        max_history: int = 100,
        permission_validator: Optional[Callable[[List[PermissionType]], bool]] = None,
        confirmation_requester: Optional[Callable[[BaseSkill, Dict[str, Any]], bool]] = None
    ):
        """
        Initialize skill executor.

        Args:
            max_history: Maximum execution records to keep (default 100)
            permission_validator: Function to validate permissions
            confirmation_requester: Function to request user confirmation
        """
        self._execution_history: List[ExecutionRecord] = []
        self._execution_callbacks: List[Callable[[str, SkillResult], None]] = []
        self._permission_validator = permission_validator
        self._confirmation_requester = confirmation_requester
        self._max_history = max_history

        logger.info("Skill executor initialized")

    async def execute(
        self,
        skill: BaseSkill,
        skip_validation: bool = False,
        skip_confirmation: bool = False,
        **parameters: Any
    ) -> SkillResult:
        """
        Execute a skill with full lifecycle management.

        Args:
            skill: Skill instance to execute
            skip_validation: Skip parameter validation
            skip_confirmation: Skip user confirmation
            **parameters: Skill parameters

        Returns:
            SkillResult from execution

        Raises:
            SkillExecutionError: If execution fails catastrophically
        """
        skill_id = skill.metadata.skill_id
        skill_name = skill.metadata.name
        start_time = datetime.now()

        logger.info(f"Executing skill: {skill_name} (ID: {skill_id})")
        logger.debug(f"Parameters: {parameters}")

        try:
            # Step 1: Validate parameters
            if not skip_validation:
                validation_error = skill.validate_parameters(parameters)
                if validation_error:
                    logger.warning(f"Parameter validation failed: {validation_error}")
                    return SkillResult(
                        success=False,
                        message="Invalid parameters",
                        error=validation_error
                    )

            # Step 2: Check permissions
            if skill.metadata.permissions_required:
                if not self._validate_permissions(skill.metadata.permissions_required):
                    logger.warning(f"Permission check failed for {skill_id}")
                    return SkillResult(
                        success=False,
                        message="Permissions not granted",
                        error=f"Required permissions: {skill.metadata.permissions_required}"
                    )

            # Step 3: Request user confirmation
            if skill.metadata.requires_confirmation and not skip_confirmation:
                if not self._request_confirmation(skill, parameters):
                    logger.info(f"User cancelled execution of {skill_id}")
                    return SkillResult(
                        success=False,
                        message="Execution cancelled by user",
                        error="User did not confirm execution"
                    )

            # Step 4: Execute skill
            logger.debug(f"Executing {skill_id} with params: {list(parameters.keys())}")

            result = await asyncio.wait_for(
                skill.execute(**parameters),
                timeout=300.0  # 5 minute timeout
            )

            # Step 5: Call success/error hooks
            if result.success:
                logger.info(f"✓ Skill succeeded: {skill_name} - {result.message}")
                await skill.on_success(result)
            else:
                logger.warning(f"✗ Skill failed: {skill_name} - {result.error}")
                await skill.on_error(result)

            # Step 6: Record execution
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._record_execution(skill_id, parameters, result, duration_ms)

            # Step 7: Notify callbacks
            self._notify_callbacks(skill_id, result)

            return result

        except asyncio.TimeoutError:
            error_msg = f"Skill execution timed out after 5 minutes"
            logger.error(f"✗ {error_msg}: {skill_id}")
            return SkillResult(
                success=False,
                message="Execution timeout",
                error=error_msg
            )

        except Exception as e:
            error_msg = f"Unexpected error during execution: {str(e)}"
            logger.error(f"✗ Skill execution failed: {skill_id} - {error_msg}", exc_info=True)

            raise SkillExecutionError(
                skill_id=skill_id,
                message=error_msg,
                original_error=e
            ) from e

        finally:
            # Step 8: Always call cleanup
            try:
                await skill.cleanup()
            except Exception as e:
                logger.warning(f"Skill cleanup failed for {skill_id}: {e}")

    def _validate_permissions(self, required_permissions: List[PermissionType]) -> bool:
        """
        Validate that required permissions are granted.

        Args:
            required_permissions: List of required permissions

        Returns:
            True if all permissions granted
        """
        if not self._permission_validator:
            # No validator configured - assume permissions granted
            logger.debug("No permission validator configured, assuming granted")
            return True

        try:
            return self._permission_validator(required_permissions)
        except Exception as e:
            logger.error(f"Permission validation failed: {e}")
            return False

    def _request_confirmation(self, skill: BaseSkill, parameters: Dict[str, Any]) -> bool:
        """
        Request user confirmation for skill execution.

        Args:
            skill: Skill to execute
            parameters: Execution parameters

        Returns:
            True if user confirmed, False otherwise
        """
        if not self._confirmation_requester:
            # No confirmation requester configured - auto-confirm
            logger.debug("No confirmation requester configured, auto-confirming")
            return True

        try:
            return self._confirmation_requester(skill, parameters)
        except Exception as e:
            logger.error(f"Confirmation request failed: {e}")
            return False

    def _record_execution(
        self,
        skill_id: str,
        parameters: Dict[str, Any],
        result: SkillResult,
        duration_ms: int
    ) -> None:
        """
        Record execution to history.

        Args:
            skill_id: ID of executed skill
            parameters: Execution parameters
            result: Execution result
            duration_ms: Execution duration in milliseconds
        """
        record = ExecutionRecord(
            skill_id=skill_id,
            parameters=parameters.copy(),
            result=result,
            duration_ms=duration_ms,
            error=result.error if not result.success else None
        )

        self._execution_history.append(record)

        # Trim history if too large
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

        logger.debug(f"Recorded execution (history size: {len(self._execution_history)})")

    def _notify_callbacks(self, skill_id: str, result: SkillResult) -> None:
        """
        Notify registered callbacks of execution.

        Args:
            skill_id: ID of executed skill
            result: Execution result
        """
        for callback in self._execution_callbacks:
            try:
                callback(skill_id, result)
            except Exception as e:
                logger.warning(f"Execution callback failed: {e}")

    def register_callback(self, callback: Callable[[str, SkillResult], None]) -> None:
        """
        Register a callback to be notified after skill execution.

        Args:
            callback: Function called with (skill_id, result)
        """
        self._execution_callbacks.append(callback)
        logger.debug(f"Registered execution callback (total: {len(self._execution_callbacks)})")

    def get_history(
        self,
        skill_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionRecord]:
        """
        Get execution history.

        Args:
            skill_id: Filter by specific skill (None for all)
            limit: Maximum records to return

        Returns:
            List of execution records (most recent first)
        """
        history = self._execution_history

        # Filter by skill_id if specified
        if skill_id:
            history = [r for r in history if r.skill_id == skill_id]

        # Return most recent first, up to limit
        return list(reversed(history[-limit:]))

    def clear_history(self, skill_id: Optional[str] = None) -> int:
        """
        Clear execution history.

        Args:
            skill_id: Clear specific skill history (None for all)

        Returns:
            Number of records cleared
        """
        if skill_id:
            before = len(self._execution_history)
            self._execution_history = [
                r for r in self._execution_history if r.skill_id != skill_id
            ]
            cleared = before - len(self._execution_history)
        else:
            cleared = len(self._execution_history)
            self._execution_history.clear()

        logger.info(f"Cleared {cleared} execution records")
        return cleared

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get executor statistics.

        Returns:
            Dictionary with execution statistics
        """
        total_executions = len(self._execution_history)
        successful = sum(1 for r in self._execution_history if r.result.success)
        failed = total_executions - successful

        return {
            "total_executions": total_executions,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_executions if total_executions > 0 else 0.0,
            "registered_callbacks": len(self._execution_callbacks),
            "max_history": self._max_history,
        }
