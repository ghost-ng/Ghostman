"""Simple synchronous test for Task Panel integration."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing Task Panel Integration")
print("=" * 60)

# Test 1: Import all components
print("\n1. Testing imports...")
try:
    from ghostman.src.presentation.widgets.skills.task_list_control_panel import TaskListControlPanel, TaskEditDialog
    print("   ✓ TaskListControlPanel imported")
    print("   ✓ TaskEditDialog imported")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

try:
    from ghostman.src.infrastructure.skills.skills_library.task_tracker_skill import TaskTrackerSkill
    print("   ✓ TaskTrackerSkill imported")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

try:
    from ghostman.src.infrastructure.skills.core.intent_classifier import IntentClassifier
    print("   ✓ IntentClassifier imported")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize TaskTrackerSkill
print("\n2. Testing TaskTrackerSkill initialization...")
try:
    skill = TaskTrackerSkill()
    print(f"   ✓ TaskTrackerSkill initialized")
    print(f"   Database path: {skill._db_path}")
    print(f"   Skill ID: {skill.metadata.skill_id}")
    print(f"   Skill name: {skill.metadata.name}")
except Exception as e:
    print(f"   ✗ Initialization failed: {e}")
    sys.exit(1)

# Test 3: Check skill parameters
print("\n3. Testing skill parameters...")
try:
    params = skill.parameters
    action_param = next((p for p in params if p.name == "action"), None)
    if action_param:
        print(f"   ✓ Action parameter found")
        print(f"   Valid actions: {action_param.constraints.get('enum', [])}")
        if "show" in action_param.constraints.get('enum', []):
            print("   ✓ 'show' action is registered")
        else:
            print("   ✗ 'show' action not found in enum")
    else:
        print("   ✗ Action parameter not found")
except Exception as e:
    print(f"   ✗ Parameter check failed: {e}")

# Test 4: Check intent patterns
print("\n4. Testing intent classifier patterns...")
try:
    classifier = IntentClassifier()
    print("   ✓ IntentClassifier initialized")

    # Check if task_tracker patterns are registered
    if "task_tracker" in classifier._patterns:
        patterns = classifier._patterns["task_tracker"]
        print(f"   ✓ Found {len(patterns)} pattern set(s) for task_tracker")

        # Check for parameter extractor
        for pattern_set in patterns:
            if "action" in pattern_set.parameter_extractors:
                print("   ✓ Action parameter extractor registered")

                # Test extraction
                extractor = pattern_set.parameter_extractors["action"]
                test_cases = [
                    ("tasks", "show"),
                    ("task list", "show"),
                    ("add task", "create"),
                    ("show tasks", "show"),
                ]

                all_correct = True
                for input_text, expected in test_cases:
                    result = extractor(input_text)
                    if result == expected:
                        print(f"   ✓ '{input_text}' -> '{result}'")
                    else:
                        print(f"   ✗ '{input_text}' -> '{result}' (expected '{expected}')")
                        all_correct = False

                if all_correct:
                    print("   ✓ All action extraction tests passed")
                break
        else:
            print("   ✗ Action parameter extractor not found")
    else:
        print("   ✗ task_tracker patterns not registered")
except Exception as e:
    print(f"   ✗ Intent classifier test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Database check
print("\n5. Testing database...")
try:
    import sqlite3
    conn = sqlite3.connect(str(skill._db_path))
    cursor = conn.cursor()

    # Check if tasks table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    if cursor.fetchone():
        print("   ✓ Tasks table exists")

        # Count tasks
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        print(f"   Tasks in database: {count}")
    else:
        print("   ✗ Tasks table not found")

    conn.close()
except Exception as e:
    print(f"   ✗ Database check failed: {e}")

print("\n" + "=" * 60)
print("✅ Integration tests completed!")
print("\nTo test the GUI:")
print("1. Run the Ghostman application")
print("2. Type 'tasks' in the chat")
print("3. The Task List Control Panel should open")
print("\nThe panel features:")
print("- Add/Edit/Delete tasks")
print("- Filter by status and priority")
print("- Sort by due date, priority, created date, or name")
print("- Search by text")
print("- Pin button for always-on-top")
print("- Context menu with right-click")
print("- Keyboard shortcuts (Ctrl+N, Enter, Delete, F5)")
