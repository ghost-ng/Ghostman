"""
Task Tracker Skill - Local task management with SQLite storage.

This skill provides a 100% local task tracking system with SQLite database
storage. No cloud sync, all data stays on the local machine.

The skill also provides a GUI control panel for comprehensive task management.
"""

import logging
import sqlite3
from typing import List, Any, Dict, Optional
from datetime import datetime
from pathlib import Path
import os

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)
from ..interfaces.task_tracker_skill import (
    Task, TaskStatus, TaskPriority, TaskFilter
)

logger = logging.getLogger("specter.skills.task_tracker")

# Lazy import for GUI components (avoid circular dependencies)
_task_control_panel = None


class TaskTrackerSkill(BaseSkill):
    """
    Skill for managing tasks with local SQLite database.

    Provides CRUD operations for tasks with support for status, priority,
    due dates, and filtering. All data stored locally in SQLite database.

    Requirements:
        - sqlite3 (built-in to Python)

    Example:
        >>> skill = TaskTrackerSkill()
        >>> result = await skill.execute(
        ...     action="create",
        ...     title="Review documentation",
        ...     priority="high",
        ...     due_date="2025-01-20"
        ... )
        >>> print(result.data["task_id"])
        1
    """

    def __init__(self):
        """Initialize task tracker skill and database."""
        super().__init__()
        self._db_path = self._get_db_path()
        self._init_database()

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="task_tracker",
            name="Task Tracker",
            description="Manage tasks locally with SQLite database",
            category=SkillCategory.PRODUCTIVITY,
            icon="✅",
            enabled_by_default=True,
            requires_confirmation=False,  # Safe local operation
            permissions_required=[PermissionType.FILE_WRITE],
            version="1.0.0",
            author="Specter"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        return [
            SkillParameter(
                name="action",
                type=str,
                required=True,
                description="Action: 'create', 'update', 'delete', 'list', 'get', 'show', 'open'",
                constraints={"enum": ["create", "update", "delete", "list", "get", "show", "open"]}
            ),
            SkillParameter(
                name="task_id",
                type=int,
                required=False,
                description="Task ID (required for update, delete, get)",
                constraints={"min": 1}
            ),
            SkillParameter(
                name="title",
                type=str,
                required=False,
                description="Task title",
                constraints={"min_length": 1, "max_length": 255}
            ),
            SkillParameter(
                name="description",
                type=str,
                required=False,
                description="Task description",
                default="",
                constraints={"max_length": 10000}
            ),
            SkillParameter(
                name="status",
                type=str,
                required=False,
                description="Task status: 'pending', 'in_progress', 'completed', 'cancelled'",
                default="pending",
                constraints={"enum": ["pending", "in_progress", "completed", "cancelled"]}
            ),
            SkillParameter(
                name="priority",
                type=str,
                required=False,
                description="Task priority: 'low', 'medium', 'high'",
                default="medium",
                constraints={"enum": ["low", "medium", "high"]}
            ),
            SkillParameter(
                name="due_date",
                type=str,
                required=False,
                description="Due date (YYYY-MM-DD format)",
                constraints={"pattern": r"^\d{4}-\d{2}-\d{2}$"}
            ),
            SkillParameter(
                name="filter_status",
                type=str,
                required=False,
                description="Filter by status for list action",
                constraints={"enum": ["pending", "in_progress", "completed", "cancelled"]}
            ),
            SkillParameter(
                name="filter_priority",
                type=str,
                required=False,
                description="Filter by priority for list action",
                constraints={"enum": ["low", "medium", "high"]}
            ),
        ]

    def _get_db_path(self) -> Path:
        """Get path to tasks database."""
        appdata = os.environ.get('APPDATA', '')
        if not appdata:
            raise RuntimeError("APPDATA environment variable not found")

        db_dir = Path(appdata) / "Specter" / "db"
        db_dir.mkdir(parents=True, exist_ok=True)

        return db_dir / "tasks.db"

    def _init_database(self):
        """Initialize SQLite database and create tables."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)

            # Create index on status for faster filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)

            # Create index on priority
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
            """)

            conn.commit()
            conn.close()

            logger.info(f"✓ Task tracker database initialized: {self._db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize task database: {e}", exc_info=True)
            raise

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the task tracker skill.

        Performs CRUD operations on tasks based on the action parameter.
        Supports 'show' or 'open' actions to display the GUI control panel.

        Args:
            **params: Validated parameters (action, task_id, title, etc.)

        Returns:
            SkillResult with operation result
        """
        action = params["action"]

        try:
            if action == "create":
                return await self._create_task(params)
            elif action == "update":
                return await self._update_task(params)
            elif action == "delete":
                return await self._delete_task(params)
            elif action == "list":
                return await self._list_tasks(params)
            elif action == "get":
                return await self._get_task(params)
            elif action in ["show", "open"]:
                return await self._show_control_panel(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"Unknown action: {action}",
                    error="Valid actions: create, update, delete, list, get, show, open"
                )

        except Exception as e:
            logger.error(f"Task tracker skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message=f"Task {action} failed",
                error=str(e)
            )

    async def _create_task(self, params: Dict[str, Any]) -> SkillResult:
        """Create a new task."""
        if not params.get("title"):
            return SkillResult(
                success=False,
                message="Task title is required",
                error="Please provide a title for the task"
            )

        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            params["title"],
            params.get("description", ""),
            params.get("status", "pending"),
            params.get("priority", "medium"),
            params.get("due_date"),
            now,
            now
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"✓ Task created: {task_id} - {params['title']}")

        return SkillResult(
            success=True,
            message=f"Task created: {params['title']}",
            data={
                "task_id": task_id,
                "title": params["title"],
                "status": params.get("status", "pending"),
                "priority": params.get("priority", "medium"),
            },
            action_taken=f"Created task: {params['title']}",
        )

    async def _update_task(self, params: Dict[str, Any]) -> SkillResult:
        """Update an existing task."""
        task_id = params.get("task_id")
        if not task_id:
            return SkillResult(
                success=False,
                message="Task ID is required for update",
                error="Please provide task_id parameter"
            )

        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        # Build update query dynamically
        updates = []
        values = []

        if "title" in params:
            updates.append("title = ?")
            values.append(params["title"])

        if "description" in params:
            updates.append("description = ?")
            values.append(params["description"])

        if "status" in params:
            updates.append("status = ?")
            values.append(params["status"])

            # Set completed_at if status is completed
            if params["status"] == "completed":
                updates.append("completed_at = ?")
                values.append(datetime.now().isoformat())

        if "priority" in params:
            updates.append("priority = ?")
            values.append(params["priority"])

        if "due_date" in params:
            updates.append("due_date = ?")
            values.append(params["due_date"])

        if not updates:
            conn.close()
            return SkillResult(
                success=False,
                message="No updates provided",
                error="Please provide at least one field to update"
            )

        # Add updated_at
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())

        # Add task_id to values
        values.append(task_id)

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)

        if cursor.rowcount == 0:
            conn.close()
            return SkillResult(
                success=False,
                message=f"Task not found: {task_id}",
                error=f"No task with ID {task_id}"
            )

        conn.commit()
        conn.close()

        logger.info(f"✓ Task updated: {task_id}")

        return SkillResult(
            success=True,
            message=f"Task {task_id} updated",
            data={"task_id": task_id, "updates": updates},
            action_taken=f"Updated task {task_id}",
        )

    async def _delete_task(self, params: Dict[str, Any]) -> SkillResult:
        """Delete a task."""
        task_id = params.get("task_id")
        if not task_id:
            return SkillResult(
                success=False,
                message="Task ID is required for delete",
                error="Please provide task_id parameter"
            )

        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        if cursor.rowcount == 0:
            conn.close()
            return SkillResult(
                success=False,
                message=f"Task not found: {task_id}",
                error=f"No task with ID {task_id}"
            )

        conn.commit()
        conn.close()

        logger.info(f"✓ Task deleted: {task_id}")

        return SkillResult(
            success=True,
            message=f"Task {task_id} deleted",
            data={"task_id": task_id},
            action_taken=f"Deleted task {task_id}",
        )

    async def _list_tasks(self, params: Dict[str, Any]) -> SkillResult:
        """List tasks with optional filtering."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM tasks WHERE 1=1"
        values = []

        if params.get("filter_status"):
            query += " AND status = ?"
            values.append(params["filter_status"])

        if params.get("filter_priority"):
            query += " AND priority = ?"
            values.append(params["filter_priority"])

        query += " ORDER BY created_at DESC"

        cursor.execute(query, values)
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            tasks.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "due_date": row["due_date"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "completed_at": row["completed_at"],
            })

        conn.close()

        logger.info(f"✓ Listed {len(tasks)} tasks")

        return SkillResult(
            success=True,
            message=f"Found {len(tasks)} task(s)",
            data={"tasks": tasks, "count": len(tasks)},
            action_taken="Listed tasks",
        )

    async def _get_task(self, params: Dict[str, Any]) -> SkillResult:
        """Get a specific task by ID."""
        task_id = params.get("task_id")
        if not task_id:
            return SkillResult(
                success=False,
                message="Task ID is required",
                error="Please provide task_id parameter"
            )

        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return SkillResult(
                success=False,
                message=f"Task not found: {task_id}",
                error=f"No task with ID {task_id}"
            )

        task = {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "priority": row["priority"],
            "due_date": row["due_date"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }

        conn.close()

        logger.info(f"✓ Retrieved task: {task_id}")

        return SkillResult(
            success=True,
            message=f"Task {task_id}: {task['title']}",
            data={"task": task},
            action_taken=f"Retrieved task {task_id}",
        )

    async def _show_control_panel(self, params: Dict[str, Any]) -> SkillResult:
        """
        Show the task list control panel GUI.

        This creates or activates the standalone task management window.
        """
        global _task_control_panel

        try:
            # Lazy import to avoid circular dependencies
            from ....presentation.widgets.skills.task_list_control_panel import TaskListControlPanel

            # Create panel if it doesn't exist or was closed
            if _task_control_panel is None or not _task_control_panel.isVisible():
                _task_control_panel = TaskListControlPanel()
                logger.info("Task control panel created")

            # Show and activate the panel
            _task_control_panel.show()
            _task_control_panel.raise_()
            _task_control_panel.activateWindow()

            logger.info("Task control panel displayed")

            return SkillResult(
                success=True,
                message="Task List Control Panel opened",
                data={"panel_visible": True},
                action_taken="Opened task list control panel",
            )

        except Exception as e:
            logger.error(f"Failed to show control panel: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Failed to open task control panel",
                error=str(e)
            )

    async def on_success(self, result: SkillResult) -> None:
        """Log successful task operation."""
        logger.info(f"Task tracker skill succeeded: {result.message}")

    async def on_error(self, result: SkillResult) -> None:
        """Log task operation failure."""
        logger.warning(f"Task tracker skill failed: {result.error}")
