# Skills System Interface Usage Guide

## Table of Contents

1. [Overview](#overview)
2. [Creating a Custom Skill](#creating-a-custom-skill)
3. [Skill Manager Usage](#skill-manager-usage)
4. [Intent Detection](#intent-detection)
5. [Screen Capture Skill](#screen-capture-skill)
6. [Task Tracker Skill](#task-tracker-skill)
7. [Advanced Topics](#advanced-topics)
8. [Best Practices](#best-practices)

---

## Overview

The Specter skills system provides a extensible framework for adding functionality to the AI assistant. Skills are self-contained units that:

- Define their own metadata (name, description, permissions)
- Specify required parameters with validation
- Execute asynchronously with proper error handling
- Support intent detection from natural language
- Integrate seamlessly with the UI

### Key Interfaces

```python
from specter.src.infrastructure.skills.interfaces import (
    BaseSkill,           # Abstract base class for skills
    SkillMetadata,       # Skill identification and configuration
    SkillParameter,      # Parameter definition with validation
    SkillResult,         # Execution result
    ISkillManager,       # Skill registry and execution
    IIntentClassifier,   # Natural language intent detection
)
```

---

## Creating a Custom Skill

### Step 1: Define Skill Metadata

```python
from specter.src.infrastructure.skills.interfaces import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    SkillCategory,
    PermissionType
)
from typing import List

class EmailSenderSkill(BaseSkill):
    """Skill for sending emails through Outlook."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="email_sender",
            name="Email Sender",
            description="Send emails through Microsoft Outlook",
            category=SkillCategory.COMMUNICATION,
            icon="email",
            enabled_by_default=True,
            requires_confirmation=True,  # Ask before sending
            permissions_required=[
                PermissionType.OUTLOOK_ACCESS
            ],
            version="1.0.0",
            author="Specter Team"
        )
```

### Step 2: Define Parameters

```python
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="to",
                type=str,
                required=True,
                description="Recipient email address",
                constraints={
                    "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            ),
            SkillParameter(
                name="subject",
                type=str,
                required=True,
                description="Email subject line",
                constraints={
                    "min_length": 1,
                    "max_length": 255
                }
            ),
            SkillParameter(
                name="body",
                type=str,
                required=True,
                description="Email body content"
            ),
            SkillParameter(
                name="cc",
                type=list,
                required=False,
                description="CC recipients (list of email addresses)",
                default=[]
            ),
            SkillParameter(
                name="priority",
                type=str,
                required=False,
                description="Email priority",
                default="normal",
                constraints={
                    "choices": ["low", "normal", "high"]
                }
            )
        ]
```

### Step 3: Implement Execution Logic

```python
    async def execute(self, **params) -> SkillResult:
        """Send email via Outlook."""
        try:
            # Extract validated parameters
            to = params["to"]
            subject = params["subject"]
            body = params["body"]
            cc = params.get("cc", [])
            priority = params.get("priority", "normal")

            # Execute the skill logic
            await self._send_outlook_email(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                priority=priority
            )

            return SkillResult(
                success=True,
                message=f"Email sent to {to}",
                data={
                    "to": to,
                    "subject": subject,
                    "sent_at": datetime.now().isoformat()
                },
                action_taken=f"Sent email to {to} with subject '{subject}'"
            )

        except Exception as e:
            return SkillResult(
                success=False,
                message="Failed to send email",
                error=str(e),
                data={"recipient": params.get("to")}
            )

    async def _send_outlook_email(self, to: str, subject: str, body: str,
                                   cc: List[str], priority: str) -> None:
        """Internal method to send email via Outlook COM interface."""
        # Implementation details...
        pass
```

### Step 4: Add Lifecycle Hooks (Optional)

```python
    async def on_success(self, result: SkillResult) -> None:
        """Called after successful email send."""
        # Log to email history
        logger.info(f"Email sent successfully: {result.data}")

        # Add to conversation context
        await self._add_to_context(result.data)

    async def on_error(self, result: SkillResult) -> None:
        """Called after failed email send."""
        # Log error for debugging
        logger.error(f"Email send failed: {result.error}")

        # Notify user of specific error
        if "authentication" in result.error.lower():
            await self._show_notification(
                "Please check Outlook authentication settings"
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Close Outlook COM connection if needed
        if hasattr(self, "_outlook_app"):
            self._outlook_app.Quit()
```

### Step 5: Custom Validation (Optional)

```python
    def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
        """Custom validation beyond type/constraint checks."""
        # Call parent validation first
        error = super().validate_parameters(params)
        if error:
            return error

        # Custom validation: ensure CC list contains valid emails
        cc = params.get("cc", [])
        if cc:
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            for email in cc:
                if not re.match(email_regex, email):
                    return f"Invalid CC email address: {email}"

        # Custom validation: prevent sending to blocked domains
        blocked_domains = ["spam.com", "test.invalid"]
        to_domain = params["to"].split("@")[1] if "@" in params["to"] else ""
        if to_domain in blocked_domains:
            return f"Cannot send to blocked domain: {to_domain}"

        return None
```

---

## Skill Manager Usage

### Registering Skills

```python
from specter.src.infrastructure.skills.skill_manager import SkillManager

# Create skill manager instance
manager = SkillManager()

# Register skills
manager.register_skill(EmailSenderSkill)
manager.register_skill(ScreenCaptureSkill)
manager.register_skill(TaskTrackerSkill)

# Enable specific skills
manager.enable_skill("email_sender")
manager.enable_skill("screen_capture")
```

### Executing Skills

```python
# Execute with explicit parameters
result = await manager.execute_skill(
    "email_sender",
    to="user@example.com",
    subject="Test Email",
    body="This is a test email from Specter",
    priority="high"
)

if result.success:
    print(f"Success: {result.message}")
    print(f"Data: {result.data}")
else:
    print(f"Error: {result.error}")
```

### Listing and Querying Skills

```python
# List all enabled skills
enabled_skills = manager.list_skills(enabled_only=True)
for skill_meta in enabled_skills:
    print(f"{skill_meta.name}: {skill_meta.description}")

# List skills by category
comm_skills = manager.list_skills(category=SkillCategory.COMMUNICATION)

# Get specific skill
skill = manager.get_skill("email_sender")
if skill:
    print(f"Skill: {skill.metadata.name}")
    print(f"Parameters: {skill.parameters}")

# Check skill status
status = manager.get_skill_status("email_sender")
print(f"Status: {status.value}")  # enabled, disabled, error, etc.
```

### Permission Management

```python
# Check if permissions are granted
if not manager.validate_permissions("email_sender"):
    # Request permissions from user
    granted = manager.request_permissions("email_sender")
    if not granted:
        print("User denied permissions")
        return

# Now safe to execute
result = await manager.execute_skill("email_sender", ...)
```

### Execution History

```python
# Get execution history for a skill
history = manager.get_execution_history("email_sender", limit=10)
for record in history:
    print(f"{record['timestamp']}: {record['result'].message}")
    print(f"  Parameters: {record['parameters']}")

# Get all execution history
all_history = manager.get_execution_history(limit=100)

# Clear history
cleared_count = manager.clear_execution_history("email_sender")
print(f"Cleared {cleared_count} records")
```

### Execution Callbacks

```python
# Register callback for all skill executions
def on_skill_executed(skill_id: str, result: SkillResult):
    logger.info(f"Skill {skill_id} executed: {result.message}")

    # Update UI
    update_status_bar(f"Last action: {result.message}")

    # Track analytics
    analytics.track_skill_usage(skill_id, result.success)

manager.on_skill_executed(on_skill_executed)
```

---

## Intent Detection

### Registering Intent Patterns

```python
from specter.src.infrastructure.skills.intent_classifier import IntentClassifier

classifier = IntentClassifier()

# Register patterns for email skill
classifier.register_patterns(
    skill_id="email_sender",
    patterns=[
        r"send (?:an )?email to (?P<to>[\w@.]+)",
        r"email (?P<to>[\w@.]+) about (?P<subject>.+)",
        "compose email",
        "send message",
    ],
    parameter_extractors={
        "priority": lambda text: "high" if "urgent" in text.lower() else "normal"
    }
)

# Register patterns for screen capture
classifier.register_patterns(
    skill_id="screen_capture",
    patterns=[
        r"(?:take|capture) (?:a )?screenshot",
        r"screenshot (?P<mode>window|rectangle|fullscreen)",
        r"capture (?P<mode>rectangle|window) (?:of )?(?P<target>.+)",
        "screen grab",
        "print screen"
    ],
    parameter_extractors={
        "mode": lambda text: (
            "window" if "window" in text.lower()
            else "fullscreen" if "full" in text.lower()
            else "rectangle"
        )
    }
)
```

### Detecting Intent from User Input

```python
# Detect intent from natural language
user_input = "send an email to john@example.com about project update"

intent = await classifier.detect_intent(user_input)

if intent and intent.confidence > 0.8:
    print(f"Detected skill: {intent.skill_id}")
    print(f"Confidence: {intent.confidence:.2%}")
    print(f"Extracted parameters: {intent.parameters}")

    # Execute the detected skill
    result = await manager.execute_skill(
        intent.skill_id,
        **intent.parameters
    )
else:
    print("No clear intent detected")
```

### Confidence Scoring

```python
# Get confidence scores for all skills
user_input = "capture my screen"
scores = classifier.get_confidence_scores(user_input)

# Display top matches
for skill_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]:
    print(f"{skill_id}: {score:.2%}")

# Output:
# screen_capture: 95.00%
# screen_recorder: 45.00%
# window_manager: 20.00%
```

### Threshold Configuration

```python
# Set minimum confidence threshold
classifier.set_confidence_threshold(0.75)  # Only return matches > 75%

# Lower threshold for exploratory mode
classifier.set_confidence_threshold(0.5)   # More permissive
```

---

## Screen Capture Skill

### Basic Screen Capture

```python
from specter.src.infrastructure.skills.interfaces import (
    CaptureMode,
    CaptureOptions,
    ImageFormat
)

# Simple fullscreen capture
result = await manager.execute_skill(
    "screen_capture",
    mode=CaptureMode.FULLSCREEN.value,
    copy_to_clipboard=True
)

if result.success:
    capture_data = result.data  # CaptureResult
    print(f"Saved to: {capture_data['image_path']}")
```

### Advanced Capture with Annotations

```python
from specter.src.infrastructure.skills.interfaces import (
    CaptureOptions,
    CaptureRegion,
    BorderConfig,
    BorderStyle,
    Annotation,
    AnnotationType
)

# Define capture region
region = CaptureRegion(x=100, y=100, width=800, height=600)

# Configure border
border = BorderConfig(
    width=3,
    color="#FF0000",
    style=BorderStyle.DASHED,
    opacity=0.8
)

# Create annotations
annotations = [
    Annotation(
        type=AnnotationType.ARROW,
        position=(150, 150),
        size=(50, 50),
        color="#00FF00",
        thickness=3
    ),
    Annotation(
        type=AnnotationType.TEXT,
        position=(200, 200),
        text="Important Section",
        color="#000000"
    ),
    Annotation(
        type=AnnotationType.BLUR,
        position=(400, 400),
        size=(200, 100)  # Blur this region
    )
]

# Execute capture
result = await manager.execute_skill(
    "screen_capture",
    mode=CaptureMode.RECTANGLE.value,
    region=region.to_dict(),
    border=border.__dict__,
    annotations=[ann.__dict__ for ann in annotations],
    format=ImageFormat.PNG.value,
    save_to_file=True,
    show_editor=True
)
```

### OCR-Enabled Capture

```python
# Capture with OCR
result = await manager.execute_skill(
    "screen_capture",
    mode=CaptureMode.RECTANGLE.value,
    ocr_enabled=True,
    copy_to_clipboard=True
)

if result.success:
    capture_data = result.data

    # Access OCR result
    if capture_data.get("ocr_result"):
        ocr = capture_data["ocr_result"]
        print(f"Extracted Text:\n{ocr['text']}")
        print(f"Confidence: {ocr['confidence']:.2%}")
        print(f"Language: {ocr['language']}")

        # Access text blocks with positions
        for block in ocr['blocks']:
            print(f"  {block['text']} at {block['position']}")
```

### Delayed Capture (for Menus)

```python
# Capture after 3 second delay (useful for dropdown menus)
result = await manager.execute_skill(
    "screen_capture",
    mode=CaptureMode.WINDOW.value,
    delay_seconds=3.0,
    cursor_visible=True
)
```

---

## Task Tracker Skill

### Creating Tasks

```python
from specter.src.infrastructure.skills.interfaces import (
    TaskPriority,
    TaskStatus
)
from datetime import date, timedelta

# Create a simple task
result = await manager.execute_skill(
    "task_tracker",
    action="create",
    title="Review pull request #123",
    description="Review authentication changes in PR #123",
    priority=TaskPriority.HIGH.value,
    tags=["code-review", "backend"],
    due_date=(date.today() + timedelta(days=2)).isoformat()
)

if result.success:
    task_id = result.data["task"]["id"]
    print(f"Task created: {task_id}")
```

### Creating Recurring Tasks

```python
from specter.src.infrastructure.skills.interfaces import RecurrenceType

# Weekly standup (Monday to Friday)
result = await manager.execute_skill(
    "task_tracker",
    action="create",
    title="Daily standup meeting",
    description="10 AM daily standup with team",
    priority=TaskPriority.MEDIUM.value,
    tags=["meeting"],
    recurrence={
        "type": RecurrenceType.WEEKLY.value,
        "days_of_week": [0, 1, 2, 3, 4]  # Mon-Fri
    }
)
```

### Querying Tasks

```python
from specter.src.infrastructure.skills.interfaces import (
    TaskFilterType,
    TaskFilter
)

# Get all overdue tasks
result = await manager.execute_skill(
    "task_tracker",
    action="list",
    filter_type=TaskFilterType.OVERDUE.value,
    tags=["backend"]
)

if result.success:
    tasks = result.data["tasks"]
    for task in tasks:
        print(f"[{task['priority']}] {task['title']} - Due: {task['due_date']}")

# Get high-priority tasks due this week
result = await manager.execute_skill(
    "task_tracker",
    action="list",
    filter_type=TaskFilterType.THIS_WEEK.value,
    priority=TaskPriority.HIGH.value,
    status=TaskStatus.IN_PROGRESS.value
)
```

### Updating Tasks

```python
# Update task status
result = await manager.execute_skill(
    "task_tracker",
    action="update",
    task_id=task_id,
    status=TaskStatus.IN_PROGRESS.value,
    actual_hours=2.5
)

# Add tags
result = await manager.execute_skill(
    "task_tracker",
    action="add_tag",
    task_id=task_id,
    tag="urgent"
)

# Mark complete
result = await manager.execute_skill(
    "task_tracker",
    action="complete",
    task_id=task_id
)
```

### Task Dependencies

```python
# Create dependent tasks
result1 = await manager.execute_skill(
    "task_tracker",
    action="create",
    title="Implement feature",
    priority=TaskPriority.HIGH.value
)
impl_task_id = result1.data["task"]["id"]

result2 = await manager.execute_skill(
    "task_tracker",
    action="create",
    title="Test feature",
    priority=TaskPriority.HIGH.value,
    status=TaskStatus.BLOCKED.value,
    dependencies=[impl_task_id]
)
```

### Task Statistics

```python
# Get task statistics
result = await manager.execute_skill(
    "task_tracker",
    action="statistics",
    filter_type=TaskFilterType.ALL.value
)

if result.success:
    stats = result.data["statistics"]
    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Completion rate: {stats['completion_rate']:.2%}")
    print(f"Overdue: {stats['overdue_count']}")
    print(f"Completed today: {stats['completed_today']}")

    print("\nBy Status:")
    for status, count in stats['by_status'].items():
        print(f"  {status}: {count}")

    print("\nTop Tags:")
    for tag, count in stats['most_used_tags'][:5]:
        print(f"  {tag}: {count}")
```

---

## Advanced Topics

### Custom Parameter Types

```python
from dataclasses import dataclass
from enum import Enum

@dataclass
class EmailPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3

# Use custom type in parameter
SkillParameter(
    name="priority",
    type=EmailPriority,
    required=False,
    default=EmailPriority.NORMAL,
    description="Email priority level"
)
```

### Async Lifecycle Hooks

```python
class FileProcessorSkill(BaseSkill):
    def __init__(self):
        self._temp_files = []

    async def execute(self, **params) -> SkillResult:
        temp_file = await self._create_temp_file()
        self._temp_files.append(temp_file)

        # Process file...

        return SkillResult(success=True, message="Processed")

    async def cleanup(self) -> None:
        """Always clean up temp files."""
        for temp_file in self._temp_files:
            try:
                await asyncio.to_thread(os.unlink, temp_file)
            except Exception as e:
                logger.error(f"Failed to cleanup {temp_file}: {e}")
        self._temp_files.clear()
```

### Skill Composition

```python
class CompositeSkill(BaseSkill):
    """Skill that combines multiple skills."""

    def __init__(self, skill_manager: ISkillManager):
        self.manager = skill_manager

    async def execute(self, **params) -> SkillResult:
        # Execute screen capture
        capture_result = await self.manager.execute_skill(
            "screen_capture",
            mode="fullscreen"
        )

        if not capture_result.success:
            return capture_result

        # Use captured image in email
        email_result = await self.manager.execute_skill(
            "email_sender",
            to=params["to"],
            subject="Screenshot",
            body="Here's the screenshot you requested",
            attachments=[capture_result.data["image_path"]]
        )

        return email_result
```

### Context-Aware Intent Detection

```python
# Provide conversation context for better intent detection
context = {
    "previous_skill": "screen_capture",
    "conversation_history": [
        "Can you help me with screenshots?",
        "I need to capture a specific window"
    ],
    "user_preferences": {
        "default_capture_mode": "window",
        "always_copy_to_clipboard": True
    }
}

intent = await classifier.detect_intent(
    user_input="capture it now",
    context=context
)

# Classifier can use context to:
# - Resolve "it" to "window" based on conversation
# - Use default preferences for parameters
# - Boost confidence for related skills
```

---

## Best Practices

### 1. Error Handling

```python
async def execute(self, **params) -> SkillResult:
    """Always return SkillResult, never raise exceptions."""
    try:
        result = await self._do_work(params)
        return SkillResult(
            success=True,
            message="Work completed",
            data=result
        )
    except PermissionError as e:
        return SkillResult(
            success=False,
            message="Permission denied",
            error=f"Insufficient permissions: {e}"
        )
    except Exception as e:
        logger.exception("Unexpected error in skill execution")
        return SkillResult(
            success=False,
            message="Execution failed",
            error=f"Unexpected error: {type(e).__name__}"
        )
```

### 2. Parameter Validation

```python
# Use constraints for simple validation
SkillParameter(
    name="count",
    type=int,
    required=True,
    description="Number of items",
    constraints={"min": 1, "max": 100}
)

# Override validate_parameters for complex logic
def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
    error = super().validate_parameters(params)
    if error:
        return error

    # Cross-parameter validation
    if params.get("count", 0) > params.get("limit", 100):
        return "count cannot exceed limit"

    return None
```

### 3. Resource Management

```python
async def execute(self, **params) -> SkillResult:
    connection = None
    try:
        connection = await self._create_connection()
        result = await self._execute_with_connection(connection, params)
        return SkillResult(success=True, data=result)
    finally:
        # Always clean up in cleanup(), not here
        pass

async def cleanup(self) -> None:
    """Always called, even if execute raises."""
    if hasattr(self, "_connection") and self._connection:
        await self._connection.close()
```

### 4. Metadata Design

```python
# Good: Specific, descriptive metadata
SkillMetadata(
    skill_id="outlook_email_sender",  # Unique, namespaced
    name="Outlook Email Sender",       # Clear name
    description="Send emails through Microsoft Outlook with rich formatting",
    category=SkillCategory.COMMUNICATION,
    icon="email",
    requires_confirmation=True,  # Sensitive action
    permissions_required=[PermissionType.OUTLOOK_ACCESS]
)

# Bad: Vague metadata
SkillMetadata(
    skill_id="email",  # Too generic
    name="Email",      # Not descriptive
    description="Emails",  # Not helpful
    # Missing important fields
)
```

### 5. Intent Pattern Design

```python
# Good: Specific patterns with parameter extraction
patterns=[
    r"send email to (?P<to>[\w@.]+) with subject (?P<subject>.+)",
    r"email (?P<to>[\w@.]+) about (?P<subject>.+)",
    r"compose (?P<priority>urgent|high priority) email",
]

# Bad: Overly broad patterns
patterns=[
    "email",  # Matches too many inputs
    r".+@.+",  # Matches any email mention
]
```

### 6. Result Data Structure

```python
# Good: Structured, documented data
return SkillResult(
    success=True,
    message="Email sent successfully",
    data={
        "message_id": "12345",
        "to": ["user@example.com"],
        "sent_at": datetime.now().isoformat(),
        "size_bytes": 4096
    },
    action_taken="Sent email to user@example.com with subject 'Test'",
    metadata={
        "server": "outlook.office365.com",
        "retry_count": 0
    }
)

# Bad: Unstructured data
return SkillResult(
    success=True,
    message="done",
    data="sent email"  # Not parseable
)
```

### 7. Testing Skills

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_email_skill_success():
    skill = EmailSenderSkill()
    skill._send_outlook_email = AsyncMock()

    result = await skill.execute(
        to="test@example.com",
        subject="Test",
        body="Test body"
    )

    assert result.success
    assert result.data["to"] == "test@example.com"
    skill._send_outlook_email.assert_called_once()

@pytest.mark.asyncio
async def test_email_skill_validation():
    skill = EmailSenderSkill()

    # Test invalid email
    error = skill.validate_parameters({
        "to": "invalid-email",
        "subject": "Test",
        "body": "Test"
    })

    assert error is not None
    assert "email" in error.lower()
```

---

## Complete Example: Weather Skill

```python
from specter.src.infrastructure.skills.interfaces import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    SkillCategory,
    PermissionType
)
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

class WeatherSkill(BaseSkill):
    """Fetch weather information for a location."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_base_url = "https://api.openweathermap.org/data/2.5"

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="weather",
            name="Weather Info",
            description="Get current weather and forecast for any location",
            category=SkillCategory.PRODUCTIVITY,
            icon="wb_sunny",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.NETWORK_ACCESS],
            version="1.0.0"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="location",
                type=str,
                required=True,
                description="City name or ZIP code",
                constraints={"min_length": 2, "max_length": 100}
            ),
            SkillParameter(
                name="units",
                type=str,
                required=False,
                description="Temperature units",
                default="imperial",
                constraints={"choices": ["metric", "imperial", "kelvin"]}
            ),
            SkillParameter(
                name="forecast_days",
                type=int,
                required=False,
                description="Number of forecast days (0 for current only)",
                default=0,
                constraints={"min": 0, "max": 7}
            )
        ]

    async def execute(self, **params) -> SkillResult:
        try:
            location = params["location"]
            units = params.get("units", "imperial")
            forecast_days = params.get("forecast_days", 0)

            # Fetch current weather
            current = await self._fetch_current_weather(location, units)

            result_data = {
                "location": current["name"],
                "current": {
                    "temperature": current["main"]["temp"],
                    "feels_like": current["main"]["feels_like"],
                    "humidity": current["main"]["humidity"],
                    "description": current["weather"][0]["description"],
                    "icon": current["weather"][0]["icon"]
                },
                "units": units,
                "timestamp": datetime.now().isoformat()
            }

            # Fetch forecast if requested
            if forecast_days > 0:
                forecast = await self._fetch_forecast(location, units, forecast_days)
                result_data["forecast"] = forecast

            # Format message
            temp_unit = "°F" if units == "imperial" else "°C" if units == "metric" else "K"
            message = (
                f"Weather in {current['name']}: "
                f"{current['main']['temp']}{temp_unit}, "
                f"{current['weather'][0]['description']}"
            )

            return SkillResult(
                success=True,
                message=message,
                data=result_data,
                action_taken=f"Fetched weather for {location}"
            )

        except aiohttp.ClientError as e:
            return SkillResult(
                success=False,
                message="Failed to fetch weather data",
                error=f"Network error: {str(e)}"
            )
        except KeyError as e:
            return SkillResult(
                success=False,
                message="Invalid response from weather service",
                error=f"Missing field: {str(e)}"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message="Weather fetch failed",
                error=str(e)
            )

    async def _fetch_current_weather(self, location: str, units: str) -> Dict[str, Any]:
        """Fetch current weather from API."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units
            }
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def _fetch_forecast(self, location: str, units: str, days: int) -> List[Dict[str, Any]]:
        """Fetch weather forecast from API."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_base_url}/forecast"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units,
                "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
            }
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data["list"]

# Register with manager
manager.register_skill(WeatherSkill(api_key="your_api_key"))
manager.enable_skill("weather")

# Register intent patterns
classifier.register_patterns(
    skill_id="weather",
    patterns=[
        r"weather (?:in |for )?(?P<location>.+)",
        r"what'?s the weather (?:in |at )?(?P<location>.+)",
        r"forecast (?:for )?(?P<location>.+) (?:for )?(?P<forecast_days>\d+) days?",
        "current weather",
        "temperature outside"
    ],
    parameter_extractors={
        "units": lambda text: "metric" if "celsius" in text.lower() else "imperial"
    }
)

# Use the skill
result = await manager.execute_skill(
    "weather",
    location="San Francisco",
    units="imperial",
    forecast_days=3
)

print(result.message)
# Output: Weather in San Francisco: 65°F, partly cloudy
```

---

This completes the comprehensive usage guide for the Specter skills system interfaces!
