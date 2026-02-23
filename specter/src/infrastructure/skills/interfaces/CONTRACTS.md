# Skills System Design Contracts and Invariants

## Table of Contents

1. [Core Contracts](#core-contracts)
2. [Interface Invariants](#interface-invariants)
3. [Type System Contracts](#type-system-contracts)
4. [Lifecycle Contracts](#lifecycle-contracts)
5. [Error Handling Contracts](#error-handling-contracts)
6. [Threading and Concurrency](#threading-and-concurrency)
7. [Validation Contracts](#validation-contracts)
8. [Extension Contracts](#extension-contracts)

---

## Core Contracts

### BaseSkill Contract

```python
"""
Contract for all skills in the system.

MUST:
1. Implement `metadata` property returning SkillMetadata
2. Implement `parameters` property returning List[SkillParameter]
3. Implement `execute()` async method returning SkillResult
4. Never raise exceptions from execute() - return SkillResult with error
5. Call super().validate_parameters() if overriding validation
6. Clean up resources in cleanup(), not in execute()

MAY:
1. Override validate_parameters() for custom validation
2. Override lifecycle hooks (on_success, on_error, cleanup)
3. Add private helper methods
4. Maintain internal state (must be thread-safe)

MUST NOT:
1. Modify parameters dict passed to execute()
2. Store secrets in metadata
3. Block indefinitely in execute()
4. Access UI components directly (use callbacks)
5. Assume execute() will be called on main thread
"""
```

### SkillMetadata Contract

```python
"""
Contract for skill metadata.

INVARIANTS:
1. skill_id must be a valid Python identifier
2. skill_id must be unique across all skills
3. name and description cannot be empty
4. version must follow semantic versioning (MAJOR.MINOR.PATCH)
5. permissions_required must be valid PermissionType values
6. Metadata is immutable (frozen dataclass)

RECOMMENDATIONS:
1. skill_id should be namespaced (e.g., "outlook_email_sender")
2. icon should be Material Icons name or single emoji
3. description should be concise (< 100 chars)
4. Set requires_confirmation=True for destructive actions
5. List all required permissions explicitly
"""
```

### SkillParameter Contract

```python
"""
Contract for skill parameters.

INVARIANTS:
1. name must be a valid Python identifier
2. type must be a Python type (str, int, bool, list, dict, etc.)
3. If required=True, default must be None
4. If required=False, default should be provided (unless type accepts None)
5. constraints must be valid for the parameter type
6. Parameter definitions are immutable (frozen dataclass)

VALIDATION ORDER:
1. Check required parameters present
2. Check parameter types match
3. Check constraints (choices, min/max, regex, etc.)
4. Run custom validation in validate_parameters()

SUPPORTED CONSTRAINTS:
For numeric types (int, float):
  - min: Minimum value (inclusive)
  - max: Maximum value (inclusive)

For string types:
  - min_length: Minimum string length
  - max_length: Maximum string length
  - regex: Regex pattern to match

For all types:
  - choices: List of allowed values

For collection types (list, set, tuple):
  - min_length: Minimum number of items
  - max_length: Maximum number of items
"""
```

### SkillResult Contract

```python
"""
Contract for skill execution results.

INVARIANTS:
1. If success=True, error must be None
2. If success=False, error should be provided
3. message must never be empty
4. data can be any JSON-serializable value
5. timestamp is set automatically if not provided

RECOMMENDATIONS:
1. message should be user-friendly (shown in UI)
2. error should be technical/detailed (for debugging)
3. data should be structured (dict, list) not primitive
4. action_taken should describe what was done (for undo)
5. metadata should contain execution details (timing, resources)

THREAD SAFETY:
SkillResult is a dataclass and should be treated as immutable
after creation. Do not modify fields after construction.
"""
```

---

## Interface Invariants

### ISkillManager Contract

```python
"""
Contract for skill manager implementations.

REGISTRATION INVARIANTS:
1. Skills can only be registered once (duplicate skill_id rejected)
2. Skills must inherit from BaseSkill
3. Skills are loaded but not enabled on registration
4. Unregistering removes skill completely (cannot be executed)

EXECUTION INVARIANTS:
1. Only enabled skills can be executed
2. Parameters are validated before execution
3. Permissions are checked before execution (if required)
4. Lifecycle hooks called in order: execute → on_success/on_error → cleanup
5. cleanup() always called, even if execute() raises
6. Execution is async (may run on thread pool)

STATE INVARIANTS:
1. Skill status transitions: REGISTERED → LOADED → ENABLED/DISABLED
2. Skills cannot transition from ERROR to ENABLED without reload
3. Disabling preserves skill configuration
4. Enabling checks permissions

HISTORY INVARIANTS:
1. All executions recorded in history (success and failure)
2. History includes timestamp, parameters, result
3. History size may be limited (LRU eviction)
4. Clearing history does not affect skill state
"""
```

### IIntentClassifier Contract

```python
"""
Contract for intent classifier implementations.

DETECTION INVARIANTS:
1. Returns None if no skill matches above threshold
2. Returns highest-confidence match if multiple skills match
3. Confidence score always in range [0.0, 1.0]
4. Extracted parameters validated before returning SkillIntent
5. Context is optional and does not affect contract

PATTERN INVARIANTS:
1. Patterns are matched case-insensitively by default
2. Regex patterns use named groups for parameter extraction
3. Parameter extractors override regex-extracted values
4. Patterns registered for non-existent skills are ignored
5. Unregistering patterns is idempotent

THRESHOLD INVARIANTS:
1. Default threshold is 0.7 (70% confidence)
2. Threshold in range [0.0, 1.0]
3. Threshold=0.0 means return all non-zero matches
4. Threshold=1.0 means require perfect match

PERFORMANCE INVARIANTS:
1. Detection should complete in < 100ms for typical input
2. Pattern matching should be O(n) in number of patterns
3. No network calls during detection
4. Classifiers may cache compiled patterns
"""
```

---

## Type System Contracts

### Type Safety

```python
"""
All public interfaces use Python type hints.

REQUIREMENTS:
1. All public methods have complete type annotations
2. Return types are explicitly declared
3. Optional types use Optional[T] or T | None
4. Collections use specific types (List[str], not list)
5. Use Any only when type is truly dynamic

GENERIC TYPES:
- Dict[str, Any] for arbitrary key-value data
- List[T] for homogeneous lists
- Optional[T] for nullable values
- Union[A, B] or A | B for multiple types

RUNTIME TYPE CHECKING:
Skills system performs runtime validation of:
1. Parameter types match declarations
2. Constraint types match parameter types
3. Result data is JSON-serializable (for persistence)
"""
```

### Serialization Contract

```python
"""
All data structures must be JSON-serializable.

SERIALIZABLE TYPES:
- Primitives: str, int, float, bool, None
- Collections: list, dict, tuple (containing serializable types)
- Dataclasses: Must implement to_dict() method
- Enums: Serialized as .value attribute
- datetime: Serialized as ISO format string
- UUID: Serialized as string
- Path: Serialized as string

NON-SERIALIZABLE TYPES:
- Functions, lambdas
- Classes (only instances via to_dict())
- File handles
- Database connections
- Qt objects

TO_DICT CONTRACT:
Dataclasses that need serialization should implement:

def to_dict(self) -> Dict[str, Any]:
    \"\"\"Convert to JSON-serializable dict.\"\"\"
    return {
        "field1": self.field1,
        "field2": self.field2.to_dict() if self.field2 else None,
        "field3": [item.to_dict() for item in self.field3],
        "enum_field": self.enum_field.value,
        "datetime_field": self.datetime_field.isoformat()
    }
"""
```

---

## Lifecycle Contracts

### Skill Lifecycle

```python
"""
Skill execution follows strict lifecycle:

1. VALIDATION PHASE
   - validate_parameters() called with input params
   - Returns None if valid, error string if invalid
   - No side effects allowed in validation

2. EXECUTION PHASE
   - execute() called with validated params
   - Must return SkillResult (success or failure)
   - Should not raise exceptions (catch and return error result)
   - May be async/await

3. SUCCESS/ERROR HOOK
   - on_success() called if result.success == True
   - on_error() called if result.success == False
   - Hooks may perform side effects (logging, notifications)
   - Hooks should not raise exceptions

4. CLEANUP PHASE
   - cleanup() always called, even if execute() raises
   - Must release all resources (files, connections, locks)
   - Should not raise exceptions (log errors instead)
   - Called even if skill disabled/unregistered during execution

TIMING GUARANTEES:
- Hooks execute in order (no parallel hook execution)
- cleanup() called after hooks complete
- Next execution does not start until cleanup() finishes

EXCEPTION HANDLING:
If execute() raises despite contract:
  1. Exception logged with full traceback
  2. SkillResult created with success=False, error=exception message
  3. on_error() called with error result
  4. cleanup() still called
  5. Exception not propagated to caller
"""
```

### Manager Lifecycle

```python
"""
Skill manager lifecycle and state transitions:

STARTUP:
1. Manager created (empty registry)
2. Skills registered (REGISTERED state)
3. Skills loaded and validated (LOADED state)
4. Skills enabled based on configuration (ENABLED state)

RUNTIME:
1. Skills may be enabled/disabled dynamically
2. Skills may be unregistered (removed from registry)
3. New skills may be registered at runtime
4. Execution history accumulated

SHUTDOWN:
1. All running skills complete or timeout
2. All skills' cleanup() called
3. Execution history may be persisted
4. Registry cleared

STATE TRANSITIONS:
REGISTERED → LOADED: Skill class instantiated, metadata validated
LOADED → ENABLED: Permissions checked, skill activated
ENABLED → DISABLED: Skill deactivated (config preserved)
DISABLED → ENABLED: Skill reactivated (no reload needed)
LOADED → ERROR: Skill initialization failed
ERROR → LOADED: Skill reloaded after fixing error

INVALID TRANSITIONS:
- Cannot execute REGISTERED, LOADED, DISABLED, or ERROR skills
- Cannot enable skill in ERROR state (must reload)
- Cannot unregister while skill executing (queued until complete)
"""
```

---

## Error Handling Contracts

### Exception vs SkillResult

```python
"""
RULE: Skills must return SkillResult, not raise exceptions.

RATIONALE:
1. Allows graceful error handling in UI
2. Preserves error details for debugging
3. Enables error recovery and retry logic
4. Consistent error reporting across skills

EXCEPTION HANDLING PATTERN:

async def execute(self, **params) -> SkillResult:
    try:
        # Normal execution path
        result = await self._do_work(params)
        return SkillResult(
            success=True,
            message="Work completed",
            data=result
        )

    except SpecificError as e:
        # Expected error (e.g., file not found, permission denied)
        logger.warning(f"Expected error: {e}")
        return SkillResult(
            success=False,
            message="User-friendly error message",
            error=str(e)
        )

    except Exception as e:
        # Unexpected error (bug in skill)
        logger.exception("Unexpected error in skill")
        return SkillResult(
            success=False,
            message="An unexpected error occurred",
            error=f"{type(e).__name__}: {str(e)}"
        )

WHEN TO RAISE EXCEPTIONS:
Only in __init__, metadata, or parameters properties:
- Raises during skill registration
- Prevents invalid skill from being loaded
- Examples: Invalid config, missing dependencies
"""
```

### Error Recovery

```python
"""
Skills should support graceful degradation and retry.

RETRY CONTRACT:
1. Skills should be idempotent when possible
2. Side effects tracked in action_taken field
3. Partial failures return success=True with metadata

DEGRADATION CONTRACT:
1. Optional features fail gracefully
2. Core functionality still works
3. Error messages explain what's unavailable

EXAMPLE - Graceful Degradation:

async def execute(self, **params) -> SkillResult:
    # Core functionality (required)
    screenshot = await self._capture_screen(params)

    result_data = {"image_path": screenshot}

    # Optional OCR (best effort)
    if params.get("ocr_enabled"):
        try:
            ocr_result = await self._perform_ocr(screenshot)
            result_data["ocr_result"] = ocr_result
        except OCRError as e:
            # OCR failed but screenshot succeeded
            logger.warning(f"OCR unavailable: {e}")
            result_data["ocr_error"] = str(e)

    return SkillResult(
        success=True,  # Core succeeded
        message="Screenshot captured (OCR unavailable)",
        data=result_data
    )
"""
```

---

## Threading and Concurrency

### Thread Safety

```python
"""
Skills may be executed concurrently.

THREAD SAFETY REQUIREMENTS:
1. Skills must be thread-safe or document limitations
2. Shared state must be protected (locks, thread-local storage)
3. External resources must handle concurrent access
4. Qt objects require main thread (use signals/slots)

THREAD-SAFE PATTERN:

class ThreadSafeSkill(BaseSkill):
    def __init__(self):
        self._lock = asyncio.Lock()
        self._state = {}

    async def execute(self, **params) -> SkillResult:
        async with self._lock:
            # Protected critical section
            self._state[params["id"]] = "processing"

        # Unprotected work (read-only or isolated)
        result = await self._do_work(params)

        async with self._lock:
            self._state[params["id"]] = "complete"

        return SkillResult(success=True, data=result)

THREAD-LOCAL PATTERN:

class ThreadLocalSkill(BaseSkill):
    def __init__(self):
        self._local = threading.local()

    async def execute(self, **params) -> SkillResult:
        # Each thread gets isolated state
        if not hasattr(self._local, "connection"):
            self._local.connection = await self._create_connection()

        result = await self._use_connection(self._local.connection, params)
        return SkillResult(success=True, data=result)
"""
```

### Async Contracts

```python
"""
All skill execution is async.

ASYNC REQUIREMENTS:
1. execute() must be async def
2. Use await for I/O operations (network, disk, subprocess)
3. Use asyncio.to_thread() for CPU-bound work
4. Never use blocking calls in async methods

BLOCKING TO ASYNC CONVERSION:

# Bad: Blocking call in async method
async def execute(self, **params):
    result = requests.get(url)  # Blocks event loop!
    return SkillResult(...)

# Good: Use async library
async def execute(self, **params):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
    return SkillResult(...)

# Good: Offload blocking work to thread
async def execute(self, **params):
    result = await asyncio.to_thread(
        self._blocking_operation,
        params
    )
    return SkillResult(...)

TIMEOUT CONTRACT:
1. Skills should respect timeouts (default: 30 seconds)
2. Long-running operations should be cancellable
3. Use asyncio.timeout() context manager

async def execute(self, **params):
    try:
        async with asyncio.timeout(30):
            result = await self._long_operation()
        return SkillResult(success=True, data=result)
    except asyncio.TimeoutError:
        return SkillResult(
            success=False,
            message="Operation timed out",
            error="Exceeded 30 second timeout"
        )
"""
```

---

## Validation Contracts

### Parameter Validation

```python
"""
Two-phase validation: built-in + custom.

PHASE 1: Built-in Validation (BaseSkill)
1. Check all required parameters present
2. Check parameter types match declarations
3. Check constraints (min/max, regex, choices)
4. Returns error string if validation fails

PHASE 2: Custom Validation (Skill Override)
1. Call super().validate_parameters() first
2. Perform cross-parameter validation
3. Perform business logic validation
4. Return None if valid, error string if invalid

VALIDATION TIMING:
- Before execute() is called
- After parameter extraction from intent
- Before permission checks
- Before user confirmation prompt

VALIDATION CONTRACT:

def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
    # MUST call parent validation
    error = super().validate_parameters(params)
    if error:
        return error

    # MAY add custom validation
    if params.get("end_date") < params.get("start_date"):
        return "end_date must be after start_date"

    # MUST return None if valid
    return None

VALIDATION RULES:
1. Validation must be pure (no side effects)
2. Validation must be fast (< 10ms)
3. Error messages must be user-friendly
4. Error messages should not leak sensitive data
"""
```

### Constraint Validation

```python
"""
Constraint validation is type-specific.

NUMERIC CONSTRAINTS (int, float):
{
    "min": 0,        # value >= min
    "max": 100,      # value <= max
}

STRING CONSTRAINTS:
{
    "min_length": 1,     # len(value) >= min_length
    "max_length": 255,   # len(value) <= max_length
    "regex": r"^\d+$",   # re.match(regex, value)
}

COLLECTION CONSTRAINTS (list, tuple, set):
{
    "min_length": 1,   # len(value) >= min_length
    "max_length": 10,  # len(value) <= max_length
}

CHOICE CONSTRAINTS (any type):
{
    "choices": ["a", "b", "c"]  # value in choices
}

CONSTRAINT PRECEDENCE:
1. Type check (before constraints)
2. Required check (before constraints)
3. Choices (if specified, skip other constraints)
4. Type-specific constraints (min/max, regex, etc.)

CONSTRAINT ERRORS:
All constraint violations return descriptive error:
- "Parameter 'age' must be >= 18, got 16"
- "Parameter 'email' does not match required pattern"
- "Parameter 'priority' must be one of ['low', 'medium', 'high'], got 'critical'"
"""
```

---

## Extension Contracts

### Adding New Skills

```python
"""
Skills are the primary extension point.

TO ADD A SKILL:
1. Create class inheriting from BaseSkill
2. Implement metadata property
3. Implement parameters property
4. Implement execute() method
5. Register with skill manager
6. Register intent patterns (optional)

SKILL DISCOVERY:
Skills may be:
- Built-in (packaged with Specter)
- User-defined (in user config directory)
- Plugin-based (loaded from plugins/ directory)

SKILL PACKAGING:
Single-file skills:
    specter/skills/my_skill.py

Multi-file skills:
    specter/skills/my_skill/
        __init__.py
        skill.py
        helpers.py
        config.json

SKILL MANIFEST (config.json):
{
    "skill_class": "MySkill",
    "dependencies": ["aiohttp>=3.8"],
    "platforms": ["win32", "linux"],
    "min_specter_version": "1.0.0"
}
"""
```

### Skill Dependencies

```python
"""
Skills may depend on external packages.

DEPENDENCY CONTRACT:
1. Skills declare dependencies in metadata or manifest
2. Manager checks dependencies before loading
3. Missing dependencies cause ERROR state
4. Skills must handle import failures gracefully

IMPORT PATTERN:

class MySkill(BaseSkill):
    def __init__(self):
        try:
            import some_optional_lib
            self._lib = some_optional_lib
            self._lib_available = True
        except ImportError:
            self._lib_available = False

    async def execute(self, **params) -> SkillResult:
        if not self._lib_available:
            return SkillResult(
                success=False,
                message="Required library not available",
                error="Install 'some_optional_lib' to use this skill"
            )
        # Use library...

PLATFORM DEPENDENCIES:
Skills may be platform-specific:

class WindowsOnlySkill(BaseSkill):
    def __init__(self):
        if sys.platform != "win32":
            raise ValueError("Windows-only skill")

    # Implementation...
"""
```

### Custom Intent Classifiers

```python
"""
Intent classifiers may use various strategies.

CLASSIFIER STRATEGIES:
1. Pattern-based (regex, keywords)
2. ML-based (trained model)
3. LLM-based (GPT classification)
4. Hybrid (multiple strategies combined)

CLASSIFIER CONTRACT:
1. Implement IIntentClassifier interface
2. Return None if no match above threshold
3. Return highest-confidence match if multiple
4. Extract parameters from user input
5. Complete in < 100ms for interactive use

EXAMPLE - ML Classifier:

class MLIntentClassifier(IIntentClassifier):
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
        self.threshold = 0.7

    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillIntent]:

        # Classify using ML model
        predictions = await asyncio.to_thread(
            self.model.predict,
            user_input
        )

        skill_id, confidence = predictions[0]

        if confidence < self.threshold:
            return None

        # Extract parameters using NER
        parameters = await self._extract_parameters(
            user_input,
            skill_id
        )

        return SkillIntent(
            skill_id=skill_id,
            confidence=confidence,
            parameters=parameters,
            raw_input=user_input,
            matched_patterns=["ml_model"]
        )
"""
```

---

## Design Principles

### 1. Fail-Safe Defaults

Skills should default to safe behavior:
- `requires_confirmation=True` for destructive actions
- `enabled_by_default=False` for sensitive skills
- Conservative timeouts and limits
- Explicit permission requirements

### 2. Progressive Enhancement

Skills should work with minimal configuration:
- Required parameters only for essential functionality
- Optional parameters for advanced features
- Graceful degradation when optional features unavailable
- Sensible defaults for all optional parameters

### 3. Explicit Over Implicit

Skills should be explicit about:
- Required permissions
- Side effects and actions taken
- Parameter requirements and constraints
- Error conditions and recovery

### 4. Composition Over Inheritance

Skills should favor composition:
- Use helper classes for reusable functionality
- Inject dependencies rather than hardcoding
- Share logic through services, not base classes
- Keep skill classes focused and simple

### 5. Testability

Skills must be testable:
- Dependencies injectable (not hardcoded)
- Pure functions where possible (validation, formatting)
- Mockable external services (network, filesystem, APIs)
- Deterministic behavior (avoid time.time(), use injected clock)

---

## Contract Compliance Checklist

When implementing a skill, verify:

- [ ] Inherits from BaseSkill
- [ ] Implements metadata property with valid SkillMetadata
- [ ] Implements parameters property with valid SkillParameter list
- [ ] Implements execute() as async def returning SkillResult
- [ ] Never raises exceptions from execute() (returns error SkillResult)
- [ ] Calls super().validate_parameters() if overriding
- [ ] Releases resources in cleanup(), not execute()
- [ ] Thread-safe or documents threading limitations
- [ ] All public methods have type hints
- [ ] All data structures are JSON-serializable
- [ ] Error messages are user-friendly
- [ ] Permissions are explicitly declared
- [ ] Documentation includes examples
- [ ] Unit tests cover success and error cases

---

## Version Compatibility

This contract specification is for **Skills System v1.0.0**.

**Semantic Versioning:**
- MAJOR version: Breaking changes to contracts
- MINOR version: New optional features, backward compatible
- PATCH version: Bug fixes, no interface changes

**Compatibility Promise:**
Skills written against v1.x.y will work with any v1.*.* manager.
Skills must be updated for v2.0.0 and later major versions.

**Deprecation Policy:**
- Features deprecated in MINOR release
- Removed in next MAJOR release
- Minimum 6 months deprecation period
- Warnings logged when using deprecated features
