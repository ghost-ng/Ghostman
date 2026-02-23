"""
Base skill interface for the Specter skills system.

This module defines the abstract base class that all skills must implement,
providing a consistent contract for skill execution, validation, and lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PermissionType(Enum):
    """Types of permissions a skill may require."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_ACCESS = "network_access"
    OUTLOOK_ACCESS = "outlook_access"
    CLIPBOARD_ACCESS = "clipboard_access"
    SCREEN_CAPTURE = "screen_capture"
    SYSTEM_INFO = "system_info"
    PROCESS_CONTROL = "process_control"


class SkillCategory(Enum):
    """Categories for organizing skills in the UI."""

    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    FILE_MANAGEMENT = "file_management"
    SCREEN_CAPTURE = "screen_capture"
    SYSTEM = "system"
    DEVELOPMENT = "development"
    CUSTOM = "custom"


@dataclass(frozen=True)
class SkillMetadata:
    """
    Metadata describing a skill's properties and capabilities.

    Attributes:
        skill_id: Unique identifier (e.g., "screen_capture", "task_tracker")
        name: Human-readable name displayed in UI
        description: Brief description of what the skill does
        category: Skill category for UI organization
        icon: Icon identifier (Material Icons or emoji)
        enabled_by_default: Whether skill is active on first install
        requires_confirmation: Whether to prompt user before execution
        permissions_required: List of permissions needed
        version: Semantic version string
        author: Skill author/maintainer

    Example:
        >>> metadata = SkillMetadata(
        ...     skill_id="screen_capture",
        ...     name="Screen Capture",
        ...     description="Capture screenshots with annotations",
        ...     category=SkillCategory.SCREEN_CAPTURE,
        ...     icon="screenshot",
        ...     enabled_by_default=True,
        ...     requires_confirmation=False,
        ...     permissions_required=[PermissionType.SCREEN_CAPTURE]
        ... )
    """

    skill_id: str
    name: str
    description: str
    category: SkillCategory
    icon: str
    enabled_by_default: bool = True
    requires_confirmation: bool = False
    permissions_required: List[PermissionType] = field(default_factory=list)
    ai_callable: bool = False  # Whether AI models can invoke this skill via tool calling
    version: str = "1.0.0"
    author: str = "Specter"

    def __post_init__(self):
        """Validate metadata invariants."""
        if not self.skill_id or not self.skill_id.isidentifier():
            raise ValueError(f"skill_id must be a valid Python identifier, got: {self.skill_id}")
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if not self.description.strip():
            raise ValueError("description cannot be empty")


@dataclass(frozen=True)
class SkillParameter:
    """
    Definition of a skill parameter with validation rules.

    Attributes:
        name: Parameter identifier (must be valid Python identifier)
        type: Python type annotation (str, int, bool, etc.)
        required: Whether parameter must be provided
        description: Human-readable parameter description
        default: Default value if not provided (None if required)
        constraints: Validation constraints (min, max, regex, choices, etc.)

    Constraints format:
        {
            "min": 0,           # Minimum value (numbers) or length (strings)
            "max": 100,         # Maximum value (numbers) or length (strings)
            "regex": r"^\d+$",  # Regex pattern (strings)
            "choices": [...],   # List of allowed values
            "min_length": 1,    # Minimum string/list length
            "max_length": 255,  # Maximum string/list length
        }

    Example:
        >>> param = SkillParameter(
        ...     name="capture_mode",
        ...     type=str,
        ...     required=True,
        ...     description="Screenshot capture mode",
        ...     constraints={"choices": ["rectangle", "window", "fullscreen"]}
        ... )

        >>> param = SkillParameter(
        ...     name="border_width",
        ...     type=int,
        ...     required=False,
        ...     description="Border width in pixels",
        ...     default=2,
        ...     constraints={"min": 0, "max": 10}
        ... )
    """

    name: str
    type: type
    required: bool
    description: str
    default: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parameter invariants."""
        if not self.name or not self.name.isidentifier():
            raise ValueError(f"name must be a valid Python identifier, got: {self.name}")
        if self.required and self.default is not None:
            raise ValueError(f"required parameter '{self.name}' cannot have a default value")
        if not self.required and self.default is None and self.type != type(None):
            # Optional params should have defaults unless they accept None
            pass  # Allow None as implicit default


@dataclass
class SkillResult:
    """
    Result of skill execution with status, data, and error information.

    Attributes:
        success: Whether execution succeeded
        message: Human-readable status message
        data: Execution result data (skill-specific structure)
        error: Error message if failed (None if success)
        action_taken: Description of action for undo support
        metadata: Additional execution metadata (timing, resources used, etc.)
        timestamp: When the result was created

    Invariants:
        - If success is True, error must be None
        - If success is False, error should be provided
        - message should always be present

    Example:
        >>> result = SkillResult(
        ...     success=True,
        ...     message="Screenshot captured successfully",
        ...     data={"path": "C:/screenshots/img.png", "size": (1920, 1080)},
        ...     action_taken="Captured fullscreen screenshot to clipboard"
        ... )

        >>> error_result = SkillResult(
        ...     success=False,
        ...     message="Failed to capture screenshot",
        ...     error="Screen capture permission denied",
        ...     data=None
        ... )
    """

    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    action_taken: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate result invariants."""
        if self.success and self.error is not None:
            raise ValueError("Successful result cannot have an error")
        if not self.message.strip():
            raise ValueError("message cannot be empty")


class BaseSkill(ABC):
    """
    Abstract base class for all Specter skills.

    Skills are executable units that perform specific tasks in response to user input.
    Each skill must implement the abstract methods and can optionally override lifecycle hooks.

    Lifecycle:
        1. validate_parameters() - Validate input before execution
        2. execute() - Perform the skill's main logic
        3. on_success() OR on_error() - Handle result
        4. cleanup() - Release resources

    Thread Safety:
        Skills may be executed concurrently. Implementations must be thread-safe
        or document threading limitations.

    Example Implementation:
        >>> class GreeterSkill(BaseSkill):
        ...
        ...     @property
        ...     def metadata(self) -> SkillMetadata:
        ...         return SkillMetadata(
        ...             skill_id="greeter",
        ...             name="Greeter",
        ...             description="Says hello to users",
        ...             category=SkillCategory.CUSTOM,
        ...             icon="👋"
        ...         )
        ...
        ...     @property
        ...     def parameters(self) -> List[SkillParameter]:
        ...         return [
        ...             SkillParameter(
        ...                 name="name",
        ...                 type=str,
        ...                 required=True,
        ...                 description="Name to greet"
        ...             )
        ...         ]
        ...
        ...     async def execute(self, **params) -> SkillResult:
        ...         name = params["name"]
        ...         return SkillResult(
        ...             success=True,
        ...             message=f"Greeted {name}",
        ...             data={"greeting": f"Hello, {name}!"}
        ...         )
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """
        Return skill metadata.

        This property must be implemented to provide skill identification
        and configuration information.

        Returns:
            SkillMetadata instance describing this skill
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[SkillParameter]:
        """
        Return list of parameters this skill accepts.

        Parameters define the skill's input contract. The skill manager
        will validate user input against these definitions before execution.

        Returns:
            List of SkillParameter definitions (empty list if no parameters)
        """
        pass

    @abstractmethod
    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the skill's main logic.

        This is the core method that implements the skill's functionality.
        It receives validated parameters and returns a result.

        Args:
            **params: Validated parameters matching the skill's parameter definitions

        Returns:
            SkillResult indicating success/failure with data/error

        Raises:
            Should not raise exceptions - catch and return SkillResult with error

        Example:
            >>> async def execute(self, **params) -> SkillResult:
            ...     try:
            ...         result_data = await self._do_work(params)
            ...         return SkillResult(
            ...             success=True,
            ...             message="Work completed",
            ...             data=result_data
            ...         )
            ...     except Exception as e:
            ...         return SkillResult(
            ...             success=False,
            ...             message="Work failed",
            ...             error=str(e)
            ...         )
        """
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters before execution.

        This method checks that all required parameters are present and
        validates constraints. Override for custom validation logic.

        Args:
            params: Dictionary of parameter values

        Returns:
            None if valid, error message string if invalid

        Example:
            >>> def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
            ...     error = super().validate_parameters(params)
            ...     if error:
            ...         return error
            ...
            ...     # Custom validation
            ...     if params.get("count", 0) > params.get("limit", 100):
            ...         return "count cannot exceed limit"
            ...
            ...     return None
        """
        # Check required parameters
        for param_def in self.parameters:
            if param_def.required and param_def.name not in params:
                return f"Missing required parameter: {param_def.name}"

        # Validate types and constraints
        for param_def in self.parameters:
            if param_def.name not in params:
                continue

            value = params[param_def.name]

            # Type check
            if not isinstance(value, param_def.type):
                return f"Parameter '{param_def.name}' must be {param_def.type.__name__}, got {type(value).__name__}"

            # Constraint validation
            error = self._validate_constraints(param_def, value)
            if error:
                return error

        return None

    def _validate_constraints(self, param_def: SkillParameter, value: Any) -> Optional[str]:
        """Validate a value against parameter constraints."""
        constraints = param_def.constraints

        # Choices constraint
        if "choices" in constraints:
            if isinstance(value, (list, tuple)):
                # For array values, validate each item individually
                invalid = [v for v in value if v not in constraints["choices"]]
                if invalid:
                    return f"Parameter '{param_def.name}' contains invalid values: {invalid}. Must be one of {constraints['choices']}"
            else:
                if value not in constraints["choices"]:
                    return f"Parameter '{param_def.name}' must be one of {constraints['choices']}, got {value}"

        # Numeric constraints
        if isinstance(value, (int, float)):
            if "min" in constraints and value < constraints["min"]:
                return f"Parameter '{param_def.name}' must be >= {constraints['min']}, got {value}"
            if "max" in constraints and value > constraints["max"]:
                return f"Parameter '{param_def.name}' must be <= {constraints['max']}, got {value}"

        # String constraints
        if isinstance(value, str):
            if "min_length" in constraints and len(value) < constraints["min_length"]:
                return f"Parameter '{param_def.name}' must be at least {constraints['min_length']} characters"
            if "max_length" in constraints and len(value) > constraints["max_length"]:
                return f"Parameter '{param_def.name}' must be at most {constraints['max_length']} characters"
            if "regex" in constraints:
                import re
                if not re.match(constraints["regex"], value):
                    return f"Parameter '{param_def.name}' does not match required pattern"

        # List/collection constraints
        if isinstance(value, (list, tuple)):
            if "min_length" in constraints and len(value) < constraints["min_length"]:
                return f"Parameter '{param_def.name}' must have at least {constraints['min_length']} items"
            if "max_length" in constraints and len(value) > constraints["max_length"]:
                return f"Parameter '{param_def.name}' must have at most {constraints['max_length']} items"

        return None

    async def on_success(self, result: SkillResult) -> None:
        """
        Hook called after successful execution.

        Override to implement post-execution logic like logging,
        notifications, or cleanup of successful operations.

        Args:
            result: The successful SkillResult
        """
        pass

    async def on_error(self, result: SkillResult) -> None:
        """
        Hook called after failed execution.

        Override to implement error handling logic like logging,
        user notifications, or rollback operations.

        Args:
            result: The failed SkillResult
        """
        pass

    async def cleanup(self) -> None:
        """
        Hook called after execution regardless of success/failure.

        Override to release resources, close connections, or perform
        other cleanup operations. Always called even if execution raises.

        Example:
            >>> async def cleanup(self) -> None:
            ...     if hasattr(self, "_temp_file"):
            ...         os.unlink(self._temp_file)
            ...     if hasattr(self, "_connection"):
            ...         await self._connection.close()
        """
        pass

    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Get JSON Schema representation of parameters.

        Useful for generating UI forms or API documentation.

        Returns:
            JSON Schema object describing parameters
        """
        properties = {}
        required = []

        for param_def in self.parameters:
            json_type = self._python_type_to_json_type(param_def.type)
            param_schema = {
                "description": param_def.description,
                "type": json_type
            }

            if param_def.default is not None:
                param_schema["default"] = param_def.default

            # Array-specific schema: build "items" sub-schema
            if json_type == "array":
                items_type = param_def.constraints.get("items_type", str)
                items_schema = {"type": self._python_type_to_json_type(items_type)}
                if "choices" in param_def.constraints:
                    items_schema["enum"] = param_def.constraints["choices"]
                param_schema["items"] = items_schema

                # Array length constraints use minItems/maxItems
                if "min_length" in param_def.constraints:
                    param_schema["minItems"] = param_def.constraints["min_length"]
                if "max_length" in param_def.constraints:
                    param_schema["maxItems"] = param_def.constraints["max_length"]
            else:
                # Non-array constraints
                if "choices" in param_def.constraints:
                    param_schema["enum"] = param_def.constraints["choices"]
                if "min_length" in param_def.constraints:
                    param_schema["minLength"] = param_def.constraints["min_length"]
                if "max_length" in param_def.constraints:
                    param_schema["maxLength"] = param_def.constraints["max_length"]

            # Numeric constraints (apply to any numeric type)
            if "min" in param_def.constraints:
                param_schema["minimum"] = param_def.constraints["min"]
            if "max" in param_def.constraints:
                param_schema["maximum"] = param_def.constraints["max"]
            if "regex" in param_def.constraints:
                param_schema["pattern"] = param_def.constraints["regex"]

            properties[param_def.name] = param_schema

            if param_def.required:
                required.append(param_def.name)

        schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            schema["required"] = required

        return schema

    def _python_type_to_json_type(self, python_type: type) -> str:
        """Map Python type to JSON Schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(python_type, "string")

    def __str__(self) -> str:
        """String representation showing skill ID and name."""
        return f"{self.metadata.skill_id} ({self.metadata.name})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"<{self.__class__.__name__} skill_id={self.metadata.skill_id!r}>"
