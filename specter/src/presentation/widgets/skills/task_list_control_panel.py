"""
Task List Control Panel - Comprehensive GUI for task management.

A standalone control panel window for managing tasks with full CRUD operations,
filtering, sorting, and always-on-top functionality. Integrates with the existing
task_tracker_skill SQLite database.
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QDialog, QTextEdit,
    QDateEdit, QMessageBox, QMenu, QHeaderView, QSizePolicy, QCheckBox,
    QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QBrush, QAction

# Import theme system for consistent styling
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.theme_manager import get_theme_manager, get_theme_color
    from ....infrastructure.storage.settings_manager import settings
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    settings = None

logger = logging.getLogger("specter.skills.task_control_panel")


class TaskEditDialog(QDialog):
    """Dialog for creating/editing tasks with full form fields."""

    def __init__(self, parent=None, task_data: Dict[str, Any] = None, colors: 'ColorSystem' = None):
        """
        Initialize task edit dialog.

        Args:
            parent: Parent widget
            task_data: Existing task data for editing (None for new task)
            colors: ColorSystem instance for theming
        """
        super().__init__(parent)
        self.task_data = task_data or {}
        self.colors = colors
        self.is_edit_mode = task_data is not None

        self.setWindowTitle("Edit Task" if self.is_edit_mode else "New Task")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        self._apply_theme()
        self._load_task_data()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title input
        title_label = QLabel("Title:")
        title_label.setObjectName("title_label")
        layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter task title...")
        self.title_input.setMinimumHeight(32)
        layout.addWidget(self.title_input)

        # Description input
        desc_label = QLabel("Description:")
        desc_label.setObjectName("desc_label")
        layout.addWidget(desc_label)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter task description (optional)...")
        self.description_input.setMinimumHeight(120)
        layout.addWidget(self.description_input)

        # Priority and Status row
        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)

        # Priority
        priority_group = QGroupBox("Priority")
        priority_layout = QHBoxLayout(priority_group)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        self.priority_combo.setCurrentIndex(1)  # Default: Medium
        priority_layout.addWidget(self.priority_combo)
        row_layout.addWidget(priority_group)

        # Status
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout(status_group)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "In Progress", "Completed", "Cancelled"])
        self.status_combo.setCurrentIndex(0)  # Default: Pending
        status_layout.addWidget(self.status_combo)
        row_layout.addWidget(status_group)

        layout.addLayout(row_layout)

        # Due date
        due_date_group = QGroupBox("Due Date (Optional)")
        due_date_layout = QHBoxLayout(due_date_group)

        self.due_date_enabled = QCheckBox("Set due date")
        self.due_date_enabled.toggled.connect(self._toggle_due_date)
        due_date_layout.addWidget(self.due_date_enabled)

        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDate(QDate.currentDate().addDays(7))  # Default: 1 week from now
        self.due_date_input.setEnabled(False)
        due_date_layout.addWidget(self.due_date_input)

        layout.addWidget(due_date_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setMinimumWidth(100)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save" if self.is_edit_mode else "Create")
        self.save_button.clicked.connect(self._save_task)
        self.save_button.setMinimumWidth(100)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _toggle_due_date(self, checked: bool):
        """Enable/disable due date picker."""
        self.due_date_input.setEnabled(checked)

    def _load_task_data(self):
        """Load existing task data into form fields."""
        if not self.is_edit_mode:
            return

        self.title_input.setText(self.task_data.get("title", ""))
        self.description_input.setPlainText(self.task_data.get("description", ""))

        # Priority
        priority = self.task_data.get("priority", "medium").capitalize()
        priority_index = self.priority_combo.findText(priority)
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        # Status
        status = self.task_data.get("status", "pending")
        status_map = {"pending": "Pending", "in_progress": "In Progress",
                      "completed": "Completed", "cancelled": "Cancelled"}
        status_text = status_map.get(status, "Pending")
        status_index = self.status_combo.findText(status_text)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)

        # Due date
        due_date_str = self.task_data.get("due_date")
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str).date()
                self.due_date_input.setDate(QDate(due_date.year, due_date.month, due_date.day))
                self.due_date_enabled.setChecked(True)
            except Exception as e:
                logger.warning(f"Failed to parse due date: {e}")

    def _save_task(self):
        """Validate and save task data."""
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Task title is required.")
            self.title_input.setFocus()
            return

        # Accept dialog (data will be retrieved via get_task_data)
        self.accept()

    def get_task_data(self) -> Dict[str, Any]:
        """
        Get task data from form fields.

        Returns:
            Dictionary with task data
        """
        # Map display values to database values
        priority_map = {"Low": "low", "Medium": "medium", "High": "high"}
        status_map = {"Pending": "pending", "In Progress": "in_progress",
                      "Completed": "completed", "Cancelled": "cancelled"}

        data = {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "priority": priority_map.get(self.priority_combo.currentText(), "medium"),
            "status": status_map.get(self.status_combo.currentText(), "pending"),
        }

        # Add due date if enabled
        if self.due_date_enabled.isChecked():
            qdate = self.due_date_input.date()
            data["due_date"] = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        else:
            data["due_date"] = None

        # Include task ID if editing
        if self.is_edit_mode and "id" in self.task_data:
            data["id"] = self.task_data["id"]

        return data

    def _apply_theme(self):
        """Apply theme colors to dialog."""
        if not self.colors:
            return

        # Dialog background
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors.background_primary};
                color: {self.colors.text_primary};
            }}
            QLabel {{
                color: {self.colors.text_primary};
                font-weight: bold;
            }}
            QLineEdit, QTextEdit, QComboBox, QDateEdit {{
                background-color: {self.colors.background_secondary};
                color: {self.colors.text_primary};
                border: 1px solid {self.colors.border_primary};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
                border: 2px solid {self.colors.border_focus};
            }}
            QComboBox::drop-down {{
                border: none;
                background: {self.colors.background_tertiary};
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {self.colors.text_primary};
            }}
            QPushButton {{
                background-color: {self.colors.interactive_normal};
                color: {self.colors.text_primary};
                border: 1px solid {self.colors.border_primary};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors.interactive_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.colors.interactive_active};
            }}
            QPushButton#save_button {{
                background-color: {self.colors.primary};
            }}
            QPushButton#save_button:hover {{
                background-color: {self.colors.primary_hover};
            }}
            QGroupBox {{
                color: {self.colors.text_primary};
                border: 1px solid {self.colors.border_secondary};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {self.colors.text_secondary};
            }}
            QCheckBox {{
                color: {self.colors.text_primary};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {self.colors.border_primary};
                border-radius: 3px;
                background: {self.colors.background_secondary};
            }}
            QCheckBox::indicator:checked {{
                background: {self.colors.primary};
            }}
        """)

        # Mark save button for special styling
        self.save_button.setObjectName("save_button")


class TaskListControlPanel(QWidget):
    """
    Comprehensive task list control panel with GUI management.

    Features:
    - Full CRUD operations (Create, Read, Update, Delete)
    - Tree view with checkboxes for completion status
    - Filtering by status and priority
    - Sorting by due date, priority, creation date, name
    - Search/filter by text
    - Always-on-top pin button
    - Context menu for task operations
    - Keyboard shortcuts
    - Theme-aware styling
    """

    # Signals
    task_created = pyqtSignal(dict)  # Emitted when task is created
    task_updated = pyqtSignal(dict)  # Emitted when task is updated
    task_deleted = pyqtSignal(int)   # Emitted when task is deleted

    def __init__(self, parent=None):
        """Initialize task list control panel."""
        super().__init__(parent)

        self._db_path = self._get_db_path()
        self._colors: Optional[ColorSystem] = None
        self._is_always_on_top = False

        self.setWindowTitle("Task List Control Panel")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        # Initialize database (ensure tables exist)
        self._ensure_database()

        # Initialize UI
        self._init_ui()
        self._apply_theme()
        self._load_tasks()

        # Connect to theme changes for live updates
        if THEME_SYSTEM_AVAILABLE:
            try:
                theme_manager = get_theme_manager()
                if theme_manager:
                    theme_manager.theme_changed.connect(lambda _: self.refresh_theme())
            except Exception:
                pass

        logger.info("Task List Control Panel initialized")

    def _get_db_path(self) -> Path:
        """Get path to tasks database."""
        appdata = os.environ.get('APPDATA', '')
        if not appdata:
            raise RuntimeError("APPDATA environment variable not found")

        db_dir = Path(appdata) / "Specter" / "db"
        db_dir.mkdir(parents=True, exist_ok=True)

        return db_dir / "tasks.db"

    def _ensure_database(self):
        """Ensure database and tables exist (same schema as task_tracker_skill)."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            # Create tasks table (identical to task_tracker_skill)
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

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
            """)

            conn.commit()
            conn.close()

            logger.debug(f"Database initialized: {self._db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Top toolbar
        toolbar_layout = self._create_toolbar()
        layout.addLayout(toolbar_layout)

        # Search and filter bar
        filter_layout = self._create_filter_bar()
        layout.addLayout(filter_layout)

        # Task tree widget
        self.task_tree = QTreeWidget()
        self.task_tree.setColumnCount(6)
        self.task_tree.setHeaderLabels(["✓", "Task", "Priority", "Status", "Due Date", "Created"])
        self.task_tree.setAlternatingRowColors(True)
        self.task_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.task_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.task_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.task_tree.itemChanged.connect(self._on_item_changed)

        # Configure column widths
        header = self.task_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Task title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Priority
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Due date
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Created

        self.task_tree.setColumnWidth(0, 40)  # Checkbox column

        layout.addWidget(self.task_tree)

        # Status bar
        status_layout = self._create_status_bar()
        layout.addLayout(status_layout)

        # Install keyboard shortcuts
        self._install_shortcuts()

    def _create_toolbar(self) -> QHBoxLayout:
        """Create top toolbar with action buttons."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Add task button
        self.add_button = QPushButton("+ Add Task")
        self.add_button.setToolTip("Create a new task (Ctrl+N)")
        self.add_button.clicked.connect(self._add_task)
        self.add_button.setMinimumHeight(32)
        toolbar.addWidget(self.add_button)

        # Edit task button
        self.edit_button = QPushButton("Edit")
        self.edit_button.setToolTip("Edit selected task (Enter)")
        self.edit_button.clicked.connect(self._edit_task)
        self.edit_button.setMinimumHeight(32)
        toolbar.addWidget(self.edit_button)

        # Delete task button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Delete selected task(s) (Delete)")
        self.delete_button.clicked.connect(self._delete_task)
        self.delete_button.setMinimumHeight(32)
        toolbar.addWidget(self.delete_button)

        toolbar.addStretch()

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Reload tasks from database (F5)")
        self.refresh_button.clicked.connect(self._load_tasks)
        self.refresh_button.setMinimumHeight(32)
        toolbar.addWidget(self.refresh_button)

        # Pin button (always on top toggle)
        self.pin_button = QPushButton("📌 Pin")
        self.pin_button.setToolTip("Toggle always on top")
        self.pin_button.setCheckable(True)
        self.pin_button.clicked.connect(self._toggle_always_on_top)
        self.pin_button.setMinimumHeight(32)
        toolbar.addWidget(self.pin_button)

        return toolbar

    def _create_filter_bar(self) -> QHBoxLayout:
        """Create filter and search bar."""
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        # Search box
        search_label = QLabel("Search:")
        filter_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by title or description...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMinimumHeight(28)
        filter_layout.addWidget(self.search_input, stretch=2)

        # Status filter
        status_label = QLabel("Status:")
        filter_layout.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "In Progress", "Completed", "Cancelled"])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        self.status_filter.setMinimumHeight(28)
        filter_layout.addWidget(self.status_filter)

        # Priority filter
        priority_label = QLabel("Priority:")
        filter_layout.addWidget(priority_label)

        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All", "Low", "Medium", "High"])
        self.priority_filter.currentTextChanged.connect(self._apply_filters)
        self.priority_filter.setMinimumHeight(28)
        filter_layout.addWidget(self.priority_filter)

        # Sort by
        sort_label = QLabel("Sort:")
        filter_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Due Date", "Priority", "Created Date", "Name"])
        self.sort_combo.currentTextChanged.connect(self._apply_filters)
        self.sort_combo.setMinimumHeight(28)
        filter_layout.addWidget(self.sort_combo)

        return filter_layout

    def _create_status_bar(self) -> QHBoxLayout:
        """Create status bar with task counts."""
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)

        self.status_label = QLabel("Total: 0 tasks")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.pending_label = QLabel("Pending: 0")
        status_layout.addWidget(self.pending_label)

        self.completed_label = QLabel("Completed: 0")
        status_layout.addWidget(self.completed_label)

        return status_layout

    def _install_shortcuts(self):
        """Install keyboard shortcuts."""
        # Add task (Ctrl+N)
        from PyQt6.QtGui import QShortcut, QKeySequence
        add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        add_shortcut.activated.connect(self._add_task)

        # Edit task (Enter)
        edit_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        edit_shortcut.activated.connect(self._edit_task)

        # Delete task (Delete)
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.activated.connect(self._delete_task)

        # Refresh (F5)
        refresh_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        refresh_shortcut.activated.connect(self._load_tasks)

    def _toggle_always_on_top(self, checked: bool):
        """Toggle always-on-top window flag."""
        self._is_always_on_top = checked

        # Get current window flags
        flags = self.windowFlags()

        if checked:
            # Add always on top flag
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.pin_button.setStyleSheet(f"font-weight: bold;")
        else:
            # Remove always on top flag
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.pin_button.setStyleSheet("")

        # Apply new flags (requires hide/show)
        self.setWindowFlags(flags)
        self.show()

        logger.info(f"Always on top: {checked}")

    def _load_tasks(self):
        """Load all tasks from database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            rows = cursor.fetchall()

            # Store tasks for filtering
            self._all_tasks = []
            for row in rows:
                self._all_tasks.append({
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

            # Apply current filters
            self._apply_filters()

            logger.info(f"Loaded {len(self._all_tasks)} tasks from database")

        except Exception as e:
            logger.error(f"Failed to load tasks: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to load tasks:\n{e}")

    def _apply_filters(self):
        """Apply search and filter criteria to task list."""
        if not hasattr(self, '_all_tasks'):
            return

        # Get filter criteria
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        priority_filter = self.priority_filter.currentText()
        sort_by = self.sort_combo.currentText()

        # Filter tasks
        filtered_tasks = []
        for task in self._all_tasks:
            # Status filter
            if status_filter != "All":
                status_map = {"Pending": "pending", "In Progress": "in_progress",
                              "Completed": "completed", "Cancelled": "cancelled"}
                if task["status"] != status_map.get(status_filter, "pending"):
                    continue

            # Priority filter
            if priority_filter != "All":
                if task["priority"] != priority_filter.lower():
                    continue

            # Search filter
            if search_text:
                if (search_text not in task["title"].lower() and
                    search_text not in (task["description"] or "").lower()):
                    continue

            filtered_tasks.append(task)

        # Sort tasks
        sort_key = None
        reverse = False

        if sort_by == "Due Date":
            sort_key = lambda t: (t["due_date"] is None, t["due_date"] or "")
        elif sort_by == "Priority":
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sort_key = lambda t: priority_order.get(t["priority"], 1)
        elif sort_by == "Created Date":
            sort_key = lambda t: t["created_at"]
            reverse = True
        elif sort_by == "Name":
            sort_key = lambda t: t["title"].lower()

        if sort_key:
            filtered_tasks.sort(key=sort_key, reverse=reverse)

        # Update tree widget
        self._populate_tree(filtered_tasks)
        self._update_status_bar(filtered_tasks)

    def _populate_tree(self, tasks: List[Dict[str, Any]]):
        """Populate tree widget with tasks."""
        # Block signals while updating
        self.task_tree.blockSignals(True)
        self.task_tree.clear()

        for task in tasks:
            item = QTreeWidgetItem()

            # Checkbox column (completion status)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_completed = task["status"] == "completed"
            item.setCheckState(0, Qt.CheckState.Checked if is_completed else Qt.CheckState.Unchecked)

            # Task title
            item.setText(1, task["title"])
            item.setToolTip(1, task["description"] or "No description")

            # Priority with color coding
            priority = task["priority"].capitalize()
            item.setText(2, priority)
            if self._colors:
                if task["priority"] == "high":
                    item.setForeground(2, QBrush(QColor(self._colors.status_error)))
                elif task["priority"] == "medium":
                    item.setForeground(2, QBrush(QColor(self._colors.status_warning)))
                else:
                    item.setForeground(2, QBrush(QColor(self._colors.text_secondary)))

            # Status
            status_map = {"pending": "Pending", "in_progress": "In Progress",
                          "completed": "Completed", "cancelled": "Cancelled"}
            item.setText(3, status_map.get(task["status"], "Pending"))

            # Due date with overdue highlighting
            if task["due_date"]:
                try:
                    due_date = datetime.fromisoformat(task["due_date"]).date()
                    today = datetime.now().date()
                    due_str = due_date.strftime("%Y-%m-%d")
                    item.setText(4, due_str)

                    # Highlight overdue tasks
                    if due_date < today and task["status"] != "completed":
                        if self._colors:
                            item.setForeground(4, QBrush(QColor(self._colors.status_error)))
                        item.setToolTip(4, "OVERDUE!")
                    else:
                        item.setToolTip(4, f"Due: {due_str}")
                except Exception as e:
                    logger.warning(f"Failed to parse due date: {e}")
                    item.setText(4, task["due_date"])
            else:
                item.setText(4, "-")

            # Created date
            try:
                created = datetime.fromisoformat(task["created_at"])
                item.setText(5, created.strftime("%Y-%m-%d %H:%M"))
            except Exception:
                item.setText(5, task["created_at"])

            # Store task ID in item data
            item.setData(0, Qt.ItemDataRole.UserRole, task["id"])

            self.task_tree.addTopLevelItem(item)

        self.task_tree.blockSignals(False)

    def _update_status_bar(self, tasks: List[Dict[str, Any]]):
        """Update status bar with task counts."""
        total = len(tasks)
        pending = sum(1 for t in tasks if t["status"] == "pending")
        completed = sum(1 for t in tasks if t["status"] == "completed")

        self.status_label.setText(f"Total: {total} task{'s' if total != 1 else ''}")
        self.pending_label.setText(f"Pending: {pending}")
        self.completed_label.setText(f"Completed: {completed}")

    def _add_task(self):
        """Open dialog to add a new task."""
        dialog = TaskEditDialog(self, task_data=None, colors=self._colors)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            self._create_task_in_db(task_data)

    def _edit_task(self):
        """Open dialog to edit selected task."""
        selected_items = self.task_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a task to edit.")
            return

        if len(selected_items) > 1:
            QMessageBox.information(self, "Multiple Selection", "Please select only one task to edit.")
            return

        item = selected_items[0]
        task_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Get task from database
        task_data = self._get_task_from_db(task_id)
        if not task_data:
            QMessageBox.warning(self, "Error", "Failed to load task data.")
            return

        dialog = TaskEditDialog(self, task_data=task_data, colors=self._colors)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_task_data()
            self._update_task_in_db(task_id, updated_data)

    def _delete_task(self):
        """Delete selected task(s) with confirmation."""
        selected_items = self.task_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select task(s) to delete.")
            return

        # Confirm deletion
        count = len(selected_items)
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} task{'s' if count > 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                task_id = item.data(0, Qt.ItemDataRole.UserRole)
                self._delete_task_from_db(task_id)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on task item."""
        if column != 0:  # Not the checkbox column
            self._edit_task()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle checkbox state change."""
        if column == 0:  # Checkbox column
            task_id = item.data(0, Qt.ItemDataRole.UserRole)
            is_checked = item.checkState(0) == Qt.CheckState.Checked

            # Update task status in database
            new_status = "completed" if is_checked else "pending"
            self._update_task_status(task_id, new_status)

    def _show_context_menu(self, position):
        """Show context menu for task operations."""
        item = self.task_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        # Edit action
        edit_action = QAction("Edit Task", self)
        edit_action.triggered.connect(self._edit_task)
        menu.addAction(edit_action)

        # Toggle completion
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        task_data = self._get_task_from_db(task_id)
        if task_data:
            is_completed = task_data["status"] == "completed"
            toggle_text = "Mark as Pending" if is_completed else "Mark as Completed"
            toggle_action = QAction(toggle_text, self)
            toggle_action.triggered.connect(lambda: self._toggle_task_completion(task_id))
            menu.addAction(toggle_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction("Delete Task", self)
        delete_action.triggered.connect(self._delete_task)
        menu.addAction(delete_action)

        menu.exec(self.task_tree.viewport().mapToGlobal(position))

    def _toggle_task_completion(self, task_id: int):
        """Toggle task completion status."""
        task_data = self._get_task_from_db(task_id)
        if task_data:
            new_status = "pending" if task_data["status"] == "completed" else "completed"
            self._update_task_status(task_id, new_status)

    # Database operations

    def _create_task_in_db(self, task_data: Dict[str, Any]):
        """Create a new task in database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data["title"],
                task_data.get("description", ""),
                task_data.get("status", "pending"),
                task_data.get("priority", "medium"),
                task_data.get("due_date"),
                now,
                now
            ))

            task_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created task: {task_id} - {task_data['title']}")

            # Reload tasks
            self._load_tasks()

            # Emit signal
            task_data["id"] = task_id
            self.task_created.emit(task_data)

            QMessageBox.information(self, "Success", "Task created successfully!")

        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to create task:\n{e}")

    def _update_task_in_db(self, task_id: int, task_data: Dict[str, Any]):
        """Update an existing task in database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            # Handle completion timestamp
            completed_at = None
            if task_data.get("status") == "completed":
                completed_at = now

            cursor.execute("""
                UPDATE tasks
                SET title = ?, description = ?, status = ?, priority = ?, due_date = ?,
                    updated_at = ?, completed_at = ?
                WHERE id = ?
            """, (
                task_data["title"],
                task_data.get("description", ""),
                task_data.get("status", "pending"),
                task_data.get("priority", "medium"),
                task_data.get("due_date"),
                now,
                completed_at,
                task_id
            ))

            conn.commit()
            conn.close()

            logger.info(f"Updated task: {task_id}")

            # Reload tasks
            self._load_tasks()

            # Emit signal
            task_data["id"] = task_id
            self.task_updated.emit(task_data)

            QMessageBox.information(self, "Success", "Task updated successfully!")

        except Exception as e:
            logger.error(f"Failed to update task: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to update task:\n{e}")

    def _update_task_status(self, task_id: int, new_status: str):
        """Update only the status of a task."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            completed_at = now if new_status == "completed" else None

            cursor.execute("""
                UPDATE tasks
                SET status = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
            """, (new_status, now, completed_at, task_id))

            conn.commit()
            conn.close()

            logger.info(f"Updated task {task_id} status to: {new_status}")

            # Reload tasks
            self._load_tasks()

        except Exception as e:
            logger.error(f"Failed to update task status: {e}", exc_info=True)

    def _delete_task_from_db(self, task_id: int):
        """Delete a task from database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

            conn.commit()
            conn.close()

            logger.info(f"Deleted task: {task_id}")

            # Reload tasks
            self._load_tasks()

            # Emit signal
            self.task_deleted.emit(task_id)

        except Exception as e:
            logger.error(f"Failed to delete task: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"Failed to delete task:\n{e}")

    def _get_task_from_db(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a single task from database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return {
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

            return None

        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            return None

    def _apply_theme(self):
        """Apply theme colors to control panel."""
        try:
            # Get theme manager and colors
            if THEME_SYSTEM_AVAILABLE and settings:
                from ...ui.themes.theme_manager import get_theme_manager
                theme_manager = get_theme_manager()
                if theme_manager:
                    self._colors = theme_manager.current_theme.colors

            if not self._colors:
                # Create default color system
                from ...ui.themes.color_system import ColorSystem
                self._colors = ColorSystem()

            # Apply stylesheet
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {self._colors.background_primary};
                    color: {self._colors.text_primary};
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
                QTreeWidget {{
                    background-color: {self._colors.background_secondary};
                    color: {self._colors.text_primary};
                    border: 1px solid {self._colors.border_primary};
                    border-radius: 4px;
                    alternate-background-color: {self._colors.background_tertiary};
                }}
                QTreeWidget::item {{
                    padding: 4px;
                }}
                QTreeWidget::item:selected {{
                    background-color: {self._colors.primary};
                    color: {self._colors.text_primary};
                }}
                QTreeWidget::item:hover {{
                    background-color: {self._colors.interactive_hover};
                }}
                QHeaderView::section {{
                    background-color: {self._colors.background_tertiary};
                    color: {self._colors.text_primary};
                    padding: 6px;
                    border: 1px solid {self._colors.border_secondary};
                    font-weight: bold;
                }}
                QPushButton {{
                    background-color: {self._colors.interactive_normal};
                    color: {self._colors.text_primary};
                    border: 1px solid {self._colors.border_primary};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self._colors.interactive_hover};
                }}
                QPushButton:pressed {{
                    background-color: {self._colors.interactive_active};
                }}
                QPushButton:checked {{
                    background-color: {self._colors.status_warning};
                    border: 2px solid {self._colors.border_focus};
                }}
                QLineEdit, QComboBox {{
                    background-color: {self._colors.background_secondary};
                    color: {self._colors.text_primary};
                    border: 1px solid {self._colors.border_primary};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QLineEdit:focus, QComboBox:focus {{
                    border: 2px solid {self._colors.border_focus};
                }}
                QComboBox::drop-down {{
                    border: none;
                    background: {self._colors.background_tertiary};
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid {self._colors.text_primary};
                }}
                QLabel {{
                    color: {self._colors.text_secondary};
                }}
                QMenu {{
                    background-color: {self._colors.background_tertiary};
                    color: {self._colors.text_primary};
                    border: 1px solid {self._colors.border_primary};
                }}
                QMenu::item:selected {{
                    background-color: {self._colors.primary};
                }}
            """)

            logger.debug("Theme applied to task control panel")

        except Exception as e:
            logger.warning(f"Failed to apply theme: {e}")

    def refresh_theme(self):
        """Refresh theme (called when theme changes)."""
        self._apply_theme()
        self._load_tasks()  # Reload to apply color coding
