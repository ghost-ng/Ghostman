"""Test script for Task List Control Panel integration."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from ghostman.src.infrastructure.skills.core.intent_classifier import IntentClassifier
from ghostman.src.infrastructure.skills.skills_library.task_tracker_skill import TaskTrackerSkill


async def test_intent_detection():
    """Test intent detection for various task commands."""
    print("=" * 60)
    print("Testing Intent Detection")
    print("=" * 60)

    classifier = IntentClassifier()

    test_commands = [
        "tasks",
        "show tasks",
        "task list",
        "open task manager",
        "view my tasks",
        "add task",
        "create new task",
    ]

    for command in test_commands:
        intent = await classifier.detect_intent(command)
        if intent:
            print(f"\nCommand: '{command}'")
            print(f"  Skill: {intent.skill_id}")
            print(f"  Confidence: {intent.confidence:.2%}")
            print(f"  Parameters: {intent.parameters}")
        else:
            print(f"\nCommand: '{command}' - NO INTENT DETECTED")

    print("\n" + "=" * 60)


async def test_skill_execution():
    """Test task_tracker_skill execution with 'show' action."""
    print("\n" + "=" * 60)
    print("Testing Skill Execution")
    print("=" * 60)

    skill = TaskTrackerSkill()
    print(f"Database path: {skill._db_path}")

    # Test showing the control panel (without actually opening GUI)
    print("\nTesting 'show' action...")
    result = await skill.execute(action="show")

    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.error:
        print(f"Error: {result.error}")
    if result.data:
        print(f"Data: {result.data}")

    print("\n" + "=" * 60)


async def test_database_operations():
    """Test basic database operations."""
    print("\n" + "=" * 60)
    print("Testing Database Operations")
    print("=" * 60)

    skill = TaskTrackerSkill()

    # Create a test task
    print("\nCreating test task...")
    result = await skill.execute(
        action="create",
        title="Test Task from Script",
        description="This is a test task created by the test script",
        priority="high",
        due_date="2025-12-31"
    )
    print(f"Create result: {result.message}")

    # List tasks
    print("\nListing all tasks...")
    result = await skill.execute(action="list")
    print(f"Found {result.data.get('count', 0)} tasks")

    if result.data.get("tasks"):
        for task in result.data["tasks"][:3]:  # Show first 3 tasks
            print(f"  - [{task['id']}] {task['title']} ({task['status']})")

    print("\n" + "=" * 60)


async def main():
    """Run all tests."""
    await test_intent_detection()
    await test_skill_execution()
    await test_database_operations()

    print("\n✅ All tests completed!")
    print("\nTo open the GUI, run the application and type 'tasks' in the chat.")


if __name__ == "__main__":
    asyncio.run(main())
