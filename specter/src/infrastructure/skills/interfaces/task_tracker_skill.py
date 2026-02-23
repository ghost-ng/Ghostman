"""
Task tracker skill interfaces and data structures.

This module defines the specific interfaces, enums, and dataclasses
for the task tracker skill functionality.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, date, timedelta
from uuid import UUID, uuid4


class TaskStatus(Enum):
    """
    Status of a task in the tracker.

    Attributes:
        TODO: Task not yet started
        IN_PROGRESS: Task currently being worked on
        BLOCKED: Task blocked by dependencies or external factors
        DONE: Task completed
        ARCHIVED: Task completed and archived
        CANCELLED: Task cancelled without completion
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """
    Priority levels for tasks.

    Attributes:
        LOW: Low priority, can be done when convenient
        MEDIUM: Normal priority, should be done soon
        HIGH: High priority, should be done quickly
        URGENT: Urgent priority, requires immediate attention
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def sort_order(self) -> int:
        """Get numeric sort order (higher = more urgent)."""
        return {
            TaskPriority.LOW: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.URGENT: 4
        }[self]


class RecurrenceType(Enum):
    """
    Recurrence pattern for recurring tasks.

    Attributes:
        NONE: No recurrence
        DAILY: Repeats daily
        WEEKLY: Repeats weekly
        MONTHLY: Repeats monthly
        YEARLY: Repeats yearly
        CUSTOM: Custom recurrence pattern
    """

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class TaskFilterType(Enum):
    """
    Types of filters for task queries.

    Attributes:
        ALL: All tasks
        ACTIVE: Non-completed tasks (TODO, IN_PROGRESS, BLOCKED)
        COMPLETED: Completed tasks (DONE, ARCHIVED)
        OVERDUE: Tasks past due date
        TODAY: Tasks due today
        THIS_WEEK: Tasks due this week
        BY_PRIORITY: Filter by specific priority
        BY_TAG: Filter by tag
        BY_STATUS: Filter by specific status
    """

    ALL = "all"
    ACTIVE = "active"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    TODAY = "today"
    THIS_WEEK = "this_week"
    BY_PRIORITY = "by_priority"
    BY_TAG = "by_tag"
    BY_STATUS = "by_status"


@dataclass
class TaskRecurrence:
    """
    Configuration for recurring tasks.

    Attributes:
        type: Type of recurrence
        interval: Interval between recurrences (e.g., every 2 days)
        end_date: When recurrence ends (None for indefinite)
        days_of_week: For weekly recurrence (0=Monday, 6=Sunday)
        day_of_month: For monthly recurrence (1-31)
        custom_pattern: Custom recurrence pattern (cron-like syntax)

    Example:
        >>> # Every Monday and Wednesday
        >>> recurrence = TaskRecurrence(
        ...     type=RecurrenceType.WEEKLY,
        ...     days_of_week=[0, 2]
        ... )
        >>>
        >>> # Every 2 days
        >>> recurrence = TaskRecurrence(
        ...     type=RecurrenceType.DAILY,
        ...     interval=2
        ... )
        >>>
        >>> # 15th of every month
        >>> recurrence = TaskRecurrence(
        ...     type=RecurrenceType.MONTHLY,
        ...     day_of_month=15
        ... )
    """

    type: RecurrenceType = RecurrenceType.NONE
    interval: int = 1
    end_date: Optional[date] = None
    days_of_week: List[int] = field(default_factory=list)
    day_of_month: Optional[int] = None
    custom_pattern: Optional[str] = None

    def __post_init__(self):
        """Validate recurrence configuration."""
        if self.interval < 1:
            raise ValueError(f"interval must be >= 1, got {self.interval}")
        if self.days_of_week:
            if not all(0 <= day <= 6 for day in self.days_of_week):
                raise ValueError("days_of_week must be between 0 (Monday) and 6 (Sunday)")
        if self.day_of_month and not 1 <= self.day_of_month <= 31:
            raise ValueError(f"day_of_month must be between 1 and 31, got {self.day_of_month}")

    def get_next_occurrence(self, from_date: date) -> Optional[date]:
        """
        Calculate next occurrence date from a given date.

        Args:
            from_date: Starting date

        Returns:
            Next occurrence date, None if no more occurrences

        Example:
            >>> recurrence = TaskRecurrence(type=RecurrenceType.WEEKLY, days_of_week=[0, 3])
            >>> next_date = recurrence.get_next_occurrence(date(2025, 1, 1))
            >>> print(next_date)
            2025-01-06  # Next Monday
        """
        if self.type == RecurrenceType.NONE:
            return None

        if self.end_date and from_date >= self.end_date:
            return None

        if self.type == RecurrenceType.DAILY:
            return from_date + timedelta(days=self.interval)

        elif self.type == RecurrenceType.WEEKLY:
            if not self.days_of_week:
                return from_date + timedelta(weeks=self.interval)

            # Find next day of week
            current_day = from_date.weekday()
            for day in sorted(self.days_of_week):
                if day > current_day:
                    days_ahead = day - current_day
                    return from_date + timedelta(days=days_ahead)

            # Next week
            days_ahead = (7 - current_day) + self.days_of_week[0]
            return from_date + timedelta(days=days_ahead)

        elif self.type == RecurrenceType.MONTHLY:
            # Simple monthly recurrence (same day next month)
            if self.day_of_month:
                # TODO: Handle month-end edge cases
                month = from_date.month + self.interval
                year = from_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    return date(year, month, self.day_of_month)
                except ValueError:
                    # Day doesn't exist in month (e.g., Feb 30)
                    return None

        elif self.type == RecurrenceType.YEARLY:
            return date(from_date.year + self.interval, from_date.month, from_date.day)

        return None


@dataclass
class Task:
    """
    A task in the tracker system.

    Attributes:
        id: Unique task identifier
        title: Task title/summary
        description: Detailed task description
        status: Current task status
        priority: Task priority level
        tags: List of tags for categorization
        due_date: When the task is due
        created_at: When task was created
        updated_at: When task was last updated
        completed_at: When task was completed (None if not done)
        recurrence: Recurrence configuration (None for one-time tasks)
        parent_id: ID of parent task (for subtasks)
        dependencies: IDs of tasks this depends on
        estimated_hours: Estimated time to complete
        actual_hours: Actual time spent
        assignee: Person assigned to task
        metadata: Additional task-specific data

    Example:
        >>> task = Task(
        ...     title="Implement user authentication",
        ...     description="Add OAuth2 authentication with Google and GitHub",
        ...     status=TaskStatus.IN_PROGRESS,
        ...     priority=TaskPriority.HIGH,
        ...     tags=["backend", "security"],
        ...     due_date=date(2025, 12, 31),
        ...     estimated_hours=8.0
        ... )
    """

    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    id: UUID = field(default_factory=uuid4)
    tags: Set[str] = field(default_factory=set)
    due_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    recurrence: Optional[TaskRecurrence] = None
    parent_id: Optional[UUID] = None
    dependencies: Set[UUID] = field(default_factory=set)
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    assignee: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task invariants."""
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if self.estimated_hours is not None and self.estimated_hours < 0:
            raise ValueError(f"estimated_hours must be >= 0, got {self.estimated_hours}")
        if self.actual_hours is not None and self.actual_hours < 0:
            raise ValueError(f"actual_hours must be >= 0, got {self.actual_hours}")
        if self.status in (TaskStatus.DONE, TaskStatus.ARCHIVED) and not self.completed_at:
            self.completed_at = datetime.now()

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status in (TaskStatus.DONE, TaskStatus.ARCHIVED, TaskStatus.CANCELLED):
            return False
        return date.today() > self.due_date

    @property
    def is_active(self) -> bool:
        """Check if task is active (not completed or cancelled)."""
        return self.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)

    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - date.today()
        return delta.days

    @property
    def time_efficiency(self) -> Optional[float]:
        """Calculate efficiency ratio (estimated vs actual hours)."""
        if self.estimated_hours and self.actual_hours:
            return self.estimated_hours / self.actual_hours
        return None

    def add_tag(self, tag: str) -> None:
        """Add a tag to the task."""
        self.tags.add(tag.lower().strip())
        self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the task."""
        if tag.lower().strip() in self.tags:
            self.tags.remove(tag.lower().strip())
            self.updated_at = datetime.now()
            return True
        return False

    def add_dependency(self, task_id: UUID) -> None:
        """Add a task dependency."""
        if task_id == self.id:
            raise ValueError("Task cannot depend on itself")
        self.dependencies.add(task_id)
        self.updated_at = datetime.now()

    def remove_dependency(self, task_id: UUID) -> bool:
        """Remove a task dependency."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
            self.updated_at = datetime.now()
            return True
        return False

    def mark_complete(self) -> None:
        """Mark task as complete."""
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()

    def reopen(self) -> None:
        """Reopen a completed task."""
        self.status = TaskStatus.TODO
        self.completed_at = None
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for serialization.

        Returns:
            Dictionary representation of the task
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": list(self.tags),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "dependencies": [str(dep_id) for dep_id in self.dependencies],
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "assignee": self.assignee,
            "is_overdue": self.is_overdue,
            "days_until_due": self.days_until_due,
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        """String representation of task."""
        return f"[{self.priority.value.upper()}] {self.title} ({self.status.value})"

    def __repr__(self) -> str:
        """Developer representation of task."""
        return f"<Task id={self.id} title={self.title!r} status={self.status.value}>"


@dataclass
class TaskFilter:
    """
    Filter criteria for querying tasks.

    Attributes:
        filter_type: Type of filter to apply
        status: Filter by specific status (for BY_STATUS filter)
        priority: Filter by specific priority (for BY_PRIORITY filter)
        tags: Filter by tags (for BY_TAG filter)
        assignee: Filter by assignee
        parent_id: Filter by parent task (get subtasks)
        start_date: Filter tasks created/due after this date
        end_date: Filter tasks created/due before this date
        search_text: Text search in title/description
        has_dependencies: Filter tasks with/without dependencies
        is_recurring: Filter recurring/non-recurring tasks

    Example:
        >>> # Get all high priority tasks due this week
        >>> filter1 = TaskFilter(
        ...     filter_type=TaskFilterType.THIS_WEEK,
        ...     priority=TaskPriority.HIGH
        ... )
        >>>
        >>> # Get all tasks tagged "backend" that are in progress
        >>> filter2 = TaskFilter(
        ...     filter_type=TaskFilterType.BY_TAG,
        ...     tags={"backend"},
        ...     status=TaskStatus.IN_PROGRESS
        ... )
        >>>
        >>> # Search for authentication-related tasks
        >>> filter3 = TaskFilter(
        ...     filter_type=TaskFilterType.ALL,
        ...     search_text="authentication"
        ... )
    """

    filter_type: TaskFilterType = TaskFilterType.ALL
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Set[str] = field(default_factory=set)
    assignee: Optional[str] = None
    parent_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search_text: Optional[str] = None
    has_dependencies: Optional[bool] = None
    is_recurring: Optional[bool] = None


@dataclass
class TaskStatistics:
    """
    Statistics about tasks in the system.

    Attributes:
        total_tasks: Total number of tasks
        by_status: Count of tasks by status
        by_priority: Count of tasks by priority
        overdue_count: Number of overdue tasks
        completed_today: Tasks completed today
        completed_this_week: Tasks completed this week
        average_completion_time: Average time to complete tasks (in days)
        total_estimated_hours: Sum of all estimated hours
        total_actual_hours: Sum of all actual hours
        most_used_tags: Top tags by usage count

    Example:
        >>> stats = TaskStatistics(
        ...     total_tasks=150,
        ...     by_status={
        ...         TaskStatus.TODO: 45,
        ...         TaskStatus.IN_PROGRESS: 23,
        ...         TaskStatus.DONE: 82
        ...     },
        ...     by_priority={
        ...         TaskPriority.HIGH: 12,
        ...         TaskPriority.MEDIUM: 98,
        ...         TaskPriority.LOW: 40
        ...     },
        ...     overdue_count=8,
        ...     completed_today=5,
        ...     completed_this_week=23
        ... )
    """

    total_tasks: int = 0
    by_status: Dict[TaskStatus, int] = field(default_factory=dict)
    by_priority: Dict[TaskPriority, int] = field(default_factory=dict)
    overdue_count: int = 0
    completed_today: int = 0
    completed_this_week: int = 0
    average_completion_time: Optional[float] = None
    total_estimated_hours: float = 0.0
    total_actual_hours: float = 0.0
    most_used_tags: List[tuple[str, int]] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        """Calculate overall completion rate."""
        if self.total_tasks == 0:
            return 0.0
        completed = self.by_status.get(TaskStatus.DONE, 0) + self.by_status.get(TaskStatus.ARCHIVED, 0)
        return completed / self.total_tasks

    @property
    def time_accuracy(self) -> Optional[float]:
        """Calculate time estimation accuracy."""
        if self.total_estimated_hours > 0 and self.total_actual_hours > 0:
            return self.total_estimated_hours / self.total_actual_hours
        return None


@dataclass
class TaskListResult:
    """
    Result of a task list/query operation.

    Attributes:
        tasks: List of tasks matching query
        total_count: Total number of tasks (before pagination)
        filter_applied: Filter used for query
        statistics: Statistics about the results
        page: Current page number (1-indexed)
        page_size: Number of tasks per page
        has_more: Whether more results exist

    Example:
        >>> result = TaskListResult(
        ...     tasks=[task1, task2, task3],
        ...     total_count=45,
        ...     filter_applied=filter_obj,
        ...     page=1,
        ...     page_size=10,
        ...     has_more=True
        ... )
    """

    tasks: List[Task] = field(default_factory=list)
    total_count: int = 0
    filter_applied: Optional[TaskFilter] = None
    statistics: Optional[TaskStatistics] = None
    page: int = 1
    page_size: int = 50
    has_more: bool = False

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size


# Usage Examples
if __name__ == "__main__":
    # Example 1: Create a simple task
    task = Task(
        title="Review pull request #123",
        description="Review authentication changes",
        priority=TaskPriority.HIGH,
        tags={"code-review", "backend"},
        due_date=date.today() + timedelta(days=2)
    )

    # Example 2: Create a recurring task
    daily_standup = Task(
        title="Daily standup meeting",
        description="10 AM daily standup with team",
        priority=TaskPriority.MEDIUM,
        tags={"meeting"},
        recurrence=TaskRecurrence(
            type=RecurrenceType.WEEKLY,
            days_of_week=[0, 1, 2, 3, 4]  # Monday to Friday
        )
    )

    # Example 3: Create task with dependencies
    implementation = Task(
        title="Implement feature",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH
    )

    testing = Task(
        title="Test feature",
        status=TaskStatus.BLOCKED,
        priority=TaskPriority.HIGH
    )
    testing.add_dependency(implementation.id)

    # Example 4: Query tasks
    filter_high_priority = TaskFilter(
        filter_type=TaskFilterType.BY_PRIORITY,
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS
    )

    filter_overdue = TaskFilter(
        filter_type=TaskFilterType.OVERDUE,
        tags={"backend"}
    )

    # Example 5: Task lifecycle
    task.add_tag("urgent")
    print(f"Task status: {task.status.value}")
    print(f"Days until due: {task.days_until_due}")
    print(f"Is overdue: {task.is_overdue}")

    # Start working on it
    task.status = TaskStatus.IN_PROGRESS
    task.actual_hours = 2.5

    # Complete it
    task.mark_complete()
    print(f"Completed at: {task.completed_at}")

    # Example 6: Task statistics
    stats = TaskStatistics(
        total_tasks=100,
        by_status={
            TaskStatus.TODO: 30,
            TaskStatus.IN_PROGRESS: 20,
            TaskStatus.DONE: 45,
            TaskStatus.ARCHIVED: 5
        },
        overdue_count=8,
        completed_today=3
    )
    print(f"Completion rate: {stats.completion_rate:.2%}")
