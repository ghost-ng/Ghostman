# Ghostman Skills System Interfaces

> Clean, type-safe interfaces for extending Ghostman with custom skills

## Overview

The Ghostman Skills System provides a powerful, extensible framework for adding new capabilities to the AI assistant. This package defines the core interfaces, abstract classes, and data structures that form the foundation of the skills system.

## Features

- **Type-Safe Architecture**: Full Python type hints for IDE support and type checking
- **Async-First Design**: Built on asyncio for non-blocking execution
- **Validation Framework**: Built-in parameter validation with extensible custom validation
- **Intent Detection**: Natural language processing to detect user intent
- **Permission System**: Granular permissions for secure skill execution
- **Lifecycle Hooks**: Pre/post execution hooks for logging, cleanup, and error handling
- **Execution History**: Track skill usage and results
- **Thread-Safe**: Concurrent skill execution with proper synchronization

## Quick Start

### Creating a Simple Skill

```python
from ghostman.src.infrastructure.skills.interfaces import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    SkillCategory
)

class CalculatorSkill(BaseSkill):
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="calculator",
            name="Calculator",
            description="Perform basic arithmetic operations",
            category=SkillCategory.PRODUCTIVITY,
            icon="calculate"
        )

    @property
    def parameters(self) -> list[SkillParameter]:
        return [
            SkillParameter(
                name="operation",
                type=str,
                required=True,
                description="Operation to perform",
                constraints={"choices": ["add", "subtract", "multiply", "divide"]}
            ),
            SkillParameter(
                name="a",
                type=float,
                required=True,
                description="First operand"
            ),
            SkillParameter(
                name="b",
                type=float,
                required=True,
                description="Second operand"
            )
        ]

    async def execute(self, **params) -> SkillResult:
        op = params["operation"]
        a = params["a"]
        b = params["b"]

        operations = {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b if b != 0 else None
        }

        result = operations[op]()

        if result is None:
            return SkillResult(
                success=False,
                message="Cannot divide by zero",
                error="Division by zero"
            )

        return SkillResult(
            success=True,
            message=f"{a} {op} {b} = {result}",
            data={"result": result, "operation": op}
        )
```

### Registering and Using Skills

```python
from ghostman.src.infrastructure.skills.skill_manager import SkillManager

# Create manager and register skill
manager = SkillManager()
manager.register_skill(CalculatorSkill)
manager.enable_skill("calculator")

# Execute skill
result = await manager.execute_skill(
    "calculator",
    operation="multiply",
    a=6,
    b=7
)

print(result.message)  # "6 multiply 7 = 42"
```

## Architecture

### Core Components

```
interfaces/
├── base_skill.py              # BaseSkill abstract class
├── skill_manager.py           # ISkillManager and IIntentClassifier interfaces
├── screen_capture_skill.py    # Screen capture specific types
├── task_tracker_skill.py      # Task tracker specific types
├── __init__.py                # Public API exports
├── USAGE.md                   # Comprehensive usage guide
├── CONTRACTS.md               # Design contracts and invariants
└── README.md                  # This file
```

### Key Abstractions

**BaseSkill** - Abstract base class for all skills
- Defines metadata, parameters, and execution contract
- Provides validation framework
- Lifecycle hooks for success, error, and cleanup

**ISkillManager** - Central registry for skill management
- Register, enable, disable skills
- Execute skills with validation
- Track execution history
- Manage permissions

**IIntentClassifier** - Natural language intent detection
- Pattern-based intent matching
- Parameter extraction from text
- Confidence scoring

## Design Principles

### 1. Clean Contracts

Every interface has explicit contracts defining:
- What implementations MUST do
- What implementations MAY do
- What implementations MUST NOT do

See [CONTRACTS.md](./CONTRACTS.md) for details.

### 2. Type Safety

All public APIs use Python type hints:
```python
async def execute_skill(
    self,
    skill_id: str,
    skip_confirmation: bool = False,
    **parameters: Any
) -> SkillResult:
    ...
```

### 3. Error Handling

Skills never raise exceptions - they return `SkillResult`:
```python
# Good
return SkillResult(
    success=False,
    message="Operation failed",
    error="Network timeout"
)

# Bad - Never do this!
raise NetworkTimeoutError("Connection failed")
```

### 4. Async by Default

All I/O operations are async:
```python
async def execute(self, **params) -> SkillResult:
    # Use async I/O
    async with aiohttp.ClientSession() as session:
        data = await session.get(url)

    # Offload blocking work to thread pool
    result = await asyncio.to_thread(cpu_intensive_work, data)

    return SkillResult(success=True, data=result)
```

### 5. Immutable Data Structures

Data classes are frozen for thread safety:
```python
@dataclass(frozen=True)
class SkillMetadata:
    skill_id: str
    name: str
    description: str
    # ... more fields
```

## Skill-Specific Types

### Screen Capture

Comprehensive types for screenshot functionality:

```python
from ghostman.src.infrastructure.skills.interfaces import (
    CaptureMode,      # RECTANGLE, WINDOW, FULLSCREEN, etc.
    BorderConfig,     # Border styling
    Annotation,       # Arrows, text, highlights
    CaptureOptions,   # Capture configuration
    CaptureResult,    # Results with OCR, paths, metadata
    OCRResult         # Text extraction results
)
```

See [screen_capture_skill.py](./screen_capture_skill.py) for full API.

### Task Tracking

Types for task management:

```python
from ghostman.src.infrastructure.skills.interfaces import (
    Task,             # Task with status, priority, tags
    TaskStatus,       # TODO, IN_PROGRESS, DONE, etc.
    TaskPriority,     # LOW, MEDIUM, HIGH, URGENT
    TaskRecurrence,   # Recurring task configuration
    TaskFilter,       # Query filtering
    TaskStatistics    # Usage statistics
)
```

See [task_tracker_skill.py](./task_tracker_skill.py) for full API.

## Permission System

Skills declare required permissions:

```python
from ghostman.src.infrastructure.skills.interfaces import PermissionType

SkillMetadata(
    skill_id="file_manager",
    name="File Manager",
    permissions_required=[
        PermissionType.FILE_READ,
        PermissionType.FILE_WRITE,
        PermissionType.FILE_DELETE
    ]
)
```

Available permissions:
- `FILE_READ`, `FILE_WRITE`, `FILE_DELETE`
- `NETWORK_ACCESS`
- `OUTLOOK_ACCESS`
- `CLIPBOARD_ACCESS`
- `SCREEN_CAPTURE`
- `SYSTEM_INFO`
- `PROCESS_CONTROL`

## Validation System

### Built-in Validation

Parameters are automatically validated:

```python
SkillParameter(
    name="age",
    type=int,
    required=True,
    constraints={"min": 0, "max": 150}
)

SkillParameter(
    name="email",
    type=str,
    required=True,
    constraints={
        "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    }
)

SkillParameter(
    name="priority",
    type=str,
    constraints={"choices": ["low", "medium", "high"]}
)
```

### Custom Validation

Override for complex validation:

```python
def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
    # Call parent validation
    error = super().validate_parameters(params)
    if error:
        return error

    # Custom cross-parameter validation
    if params["end_date"] < params["start_date"]:
        return "end_date must be after start_date"

    return None
```

## Intent Detection

Register patterns for natural language detection:

```python
classifier.register_patterns(
    skill_id="calculator",
    patterns=[
        r"calculate (?P<a>\d+) (?P<operation>\+|\-|\*|\/) (?P<b>\d+)",
        r"what is (?P<a>\d+) (?P<operation>plus|minus|times|divided by) (?P<b>\d+)",
    ],
    parameter_extractors={
        "operation": lambda text: {
            "plus": "add",
            "minus": "subtract",
            "times": "multiply",
            "divided by": "divide"
        }.get(text, text)
    }
)

# Detect intent
intent = await classifier.detect_intent("what is 6 times 7")
# SkillIntent(skill_id="calculator", confidence=0.95,
#             parameters={"a": 6, "b": 7, "operation": "multiply"})
```

## Lifecycle Hooks

Skills can hook into execution lifecycle:

```python
class MySkill(BaseSkill):
    async def execute(self, **params) -> SkillResult:
        # Main execution logic
        return SkillResult(success=True, data={"result": 42})

    async def on_success(self, result: SkillResult) -> None:
        # Called after successful execution
        logger.info(f"Success: {result.message}")
        await self._send_notification(result)

    async def on_error(self, result: SkillResult) -> None:
        # Called after failed execution
        logger.error(f"Error: {result.error}")
        await self._rollback_changes()

    async def cleanup(self) -> None:
        # Always called (even if execute raises)
        if hasattr(self, "_temp_file"):
            os.unlink(self._temp_file)
        if hasattr(self, "_connection"):
            await self._connection.close()
```

## Testing

Skills are designed for testability:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_calculator_multiply():
    skill = CalculatorSkill()

    result = await skill.execute(
        operation="multiply",
        a=6,
        b=7
    )

    assert result.success
    assert result.data["result"] == 42
    assert "multiply" in result.message

@pytest.mark.asyncio
async def test_calculator_divide_by_zero():
    skill = CalculatorSkill()

    result = await skill.execute(
        operation="divide",
        a=10,
        b=0
    )

    assert not result.success
    assert "zero" in result.error.lower()
```

## Documentation

- **[USAGE.md](./USAGE.md)** - Comprehensive usage guide with examples
- **[CONTRACTS.md](./CONTRACTS.md)** - Design contracts and invariants
- **Module docstrings** - Inline API documentation

## Examples

See the usage guide for complete examples:

1. **Email Sender Skill** - Complete skill with Outlook integration
2. **Weather Skill** - API integration with error handling
3. **Screen Capture** - Complex configuration with annotations
4. **Task Tracker** - CRUD operations with filtering

## Extension Points

The skills system is designed for extension:

### 1. Custom Skills
Implement `BaseSkill` to add new functionality

### 2. Custom Intent Classifiers
Implement `IIntentClassifier` for ML-based or LLM-based intent detection

### 3. Custom Skill Manager
Implement `ISkillManager` for alternative skill loading strategies

### 4. Custom Validation
Override `validate_parameters()` for domain-specific validation

### 5. Custom Data Types
Create dataclasses for skill-specific data structures

## Performance Considerations

- **Async I/O**: Non-blocking network and file operations
- **Thread Pool**: CPU-bound work offloaded to thread pool
- **Lazy Loading**: Skills loaded on-demand, not at startup
- **Caching**: Intent patterns compiled and cached
- **Timeout**: Default 30s timeout prevents hanging
- **Concurrent Execution**: Multiple skills can run in parallel

## Thread Safety

- Skills may be executed concurrently
- Shared state must be protected with locks
- Qt objects require main thread (use signals/slots)
- Use `asyncio.Lock()` for async synchronization

```python
class ThreadSafeSkill(BaseSkill):
    def __init__(self):
        self._lock = asyncio.Lock()
        self._counter = 0

    async def execute(self, **params) -> SkillResult:
        async with self._lock:
            self._counter += 1
            count = self._counter

        return SkillResult(
            success=True,
            data={"execution_count": count}
        )
```

## Compatibility

- **Python**: 3.10+
- **PyQt**: PyQt6
- **Asyncio**: Python asyncio standard library
- **Type Hints**: PEP 484, 585, 604

## License

This code is part of the Ghostman project.

## Contributing

When adding new interfaces:

1. Follow existing patterns and contracts
2. Add comprehensive docstrings with examples
3. Include type hints for all public APIs
4. Add validation for invariants
5. Update USAGE.md and CONTRACTS.md
6. Add unit tests

## Changelog

### v1.0.0 (2025-11-22)
- Initial release
- BaseSkill abstract class
- SkillManager and IntentClassifier interfaces
- Screen capture skill types
- Task tracker skill types
- Comprehensive validation framework
- Permission system
- Lifecycle hooks

---

**Questions?** See [USAGE.md](./USAGE.md) for detailed examples or [CONTRACTS.md](./CONTRACTS.md) for design details.
