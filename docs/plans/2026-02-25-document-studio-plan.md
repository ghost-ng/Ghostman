# Document Studio Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a collapsible Document Studio sidebar panel to the REPL that provides visual document cards, reusable formatting recipes, batch processing for 10-50 files, live preview, and before/after diff view.

**Architecture:** The Document Studio is a QWidget panel embedded via QSplitter inside the existing FloatingREPLWindow, sharing space with REPLWidget. A centralized `DocumentStudioState` QObject manages all state with pyqtSignal-based updates. Batch processing runs on a background QThread using the existing `DocxFormatterSkill`. Recipes are stored in `settings.json`.

**Tech Stack:** PyQt6 (QSplitter, QStackedWidget, QScrollArea, QTextBrowser, QProgressBar, QThread), python-docx (document inspection + rendering), difflib (text comparison), existing Specter theme system (ColorSystem, ButtonStyleManager, StyleTemplates).

---

## Phase 1: Foundation

### Task 1: Create DocumentStudioState (centralized state + data models)

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/__init__.py`
- Create: `specter/src/presentation/widgets/document_studio/studio_state.py`
- Test: `specter/tests/test_studio_state.py`

**Step 1: Create package directory**

```bash
mkdir -p specter/src/presentation/widgets/document_studio
```

**Step 2: Create `__init__.py`**

Create `specter/src/presentation/widgets/document_studio/__init__.py`:
```python
"""Document Studio Panel — visual document workspace for batch formatting."""
```

**Step 3: Write the test file**

Create `specter/tests/test_studio_state.py`:
```python
"""Tests for DocumentStudioState, DocumentEntry, and Recipe."""
import pytest
from specter.src.presentation.widgets.document_studio.studio_state import (
    DocumentStudioState,
    DocumentEntry,
    DocumentStatus,
    Recipe,
)


class TestDocumentEntry:
    def test_create_default(self):
        entry = DocumentEntry(file_path="C:/docs/report.docx", filename="report.docx")
        assert entry.status == DocumentStatus.PENDING
        assert entry.progress == 0.0
        assert entry.selected is False
        assert entry.error_message == ""
        assert entry.original_path is None
        assert entry.formatted_path is None

    def test_create_with_metadata(self):
        entry = DocumentEntry(
            file_path="C:/docs/report.docx",
            filename="report.docx",
            page_count=12,
            file_size=245000,
        )
        assert entry.page_count == 12
        assert entry.file_size == 245000


class TestRecipe:
    def test_create_recipe(self):
        recipe = Recipe(
            recipe_id="corporate_memo",
            name="Corporate Memo",
            description="Standard corporate formatting",
            operations=["standardize_fonts", "fix_margins"],
            parameters={"font_name": "Calibri", "font_size": 11},
        )
        assert recipe.recipe_id == "corporate_memo"
        assert len(recipe.operations) == 2
        assert recipe.parameters["font_name"] == "Calibri"

    def test_to_dict_roundtrip(self):
        recipe = Recipe(
            recipe_id="test",
            name="Test",
            description="A test recipe",
            operations=["standardize_fonts"],
            parameters={"font_size": 12},
        )
        d = recipe.to_dict()
        restored = Recipe.from_dict("test", d)
        assert restored.name == recipe.name
        assert restored.operations == recipe.operations
        assert restored.parameters == recipe.parameters


class TestDocumentStudioState:
    def test_add_document(self, qtbot):
        state = DocumentStudioState()
        with qtbot.waitSignal(state.document_added, timeout=1000):
            state.add_document("C:/docs/report.docx")
        assert "C:/docs/report.docx" in state.documents
        entry = state.documents["C:/docs/report.docx"]
        assert entry.filename == "report.docx"
        assert entry.status == DocumentStatus.PENDING

    def test_add_duplicate_ignored(self, qtbot):
        state = DocumentStudioState()
        state.add_document("C:/docs/report.docx")
        count_before = len(state.documents)
        state.add_document("C:/docs/report.docx")
        assert len(state.documents) == count_before

    def test_remove_document(self, qtbot):
        state = DocumentStudioState()
        state.add_document("C:/docs/report.docx")
        with qtbot.waitSignal(state.document_removed, timeout=1000):
            state.remove_document("C:/docs/report.docx")
        assert "C:/docs/report.docx" not in state.documents

    def test_update_status(self, qtbot):
        state = DocumentStudioState()
        state.add_document("C:/docs/report.docx")
        with qtbot.waitSignal(state.document_status_changed, timeout=1000):
            state.update_status("C:/docs/report.docx", DocumentStatus.PROCESSING)
        assert state.documents["C:/docs/report.docx"].status == DocumentStatus.PROCESSING

    def test_toggle_selection(self):
        state = DocumentStudioState()
        state.add_document("C:/docs/report.docx")
        state.toggle_selection("C:/docs/report.docx")
        assert state.documents["C:/docs/report.docx"].selected is True
        state.toggle_selection("C:/docs/report.docx")
        assert state.documents["C:/docs/report.docx"].selected is False

    def test_selected_documents(self):
        state = DocumentStudioState()
        state.add_document("C:/docs/a.docx")
        state.add_document("C:/docs/b.docx")
        state.add_document("C:/docs/c.docx")
        state.toggle_selection("C:/docs/a.docx")
        state.toggle_selection("C:/docs/c.docx")
        selected = state.get_selected_paths()
        assert set(selected) == {"C:/docs/a.docx", "C:/docs/c.docx"}

    def test_select_all_deselect_all(self):
        state = DocumentStudioState()
        state.add_document("C:/docs/a.docx")
        state.add_document("C:/docs/b.docx")
        state.select_all()
        assert all(e.selected for e in state.documents.values())
        state.deselect_all()
        assert not any(e.selected for e in state.documents.values())

    def test_add_recipe(self, qtbot):
        state = DocumentStudioState()
        recipe = Recipe(
            recipe_id="memo",
            name="Memo",
            description="",
            operations=["standardize_fonts"],
            parameters={},
        )
        with qtbot.waitSignal(state.recipe_saved, timeout=1000):
            state.add_recipe(recipe)
        assert "memo" in state.recipes

    def test_remove_recipe(self, qtbot):
        state = DocumentStudioState()
        recipe = Recipe(
            recipe_id="memo",
            name="Memo",
            description="",
            operations=["standardize_fonts"],
            parameters={},
        )
        state.add_recipe(recipe)
        with qtbot.waitSignal(state.recipe_removed, timeout=1000):
            state.remove_recipe("memo")
        assert "memo" not in state.recipes

    def test_clear_all(self, qtbot):
        state = DocumentStudioState()
        state.add_document("C:/docs/a.docx")
        state.add_document("C:/docs/b.docx")
        state.clear_all_documents()
        assert len(state.documents) == 0
```

**Step 4: Run tests to verify they fail**

```bash
cd c:/Users/miguel/OneDrive/Documents/Ghostman
python -m pytest specter/tests/test_studio_state.py -v --tb=short 2>&1 | head -30
```
Expected: FAIL — `ModuleNotFoundError: No module named 'specter.src.presentation.widgets.document_studio'`

**Step 5: Write `studio_state.py`**

Create `specter/src/presentation/widgets/document_studio/studio_state.py`:
```python
"""
Centralized state management for the Document Studio panel.

Holds document entries, recipes, and batch state. Uses pyqtSignal for
thread-safe UI updates from background workers.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("specter.document_studio.state")


class DocumentStatus(Enum):
    """Processing status for a document in the studio."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentEntry:
    """A single document tracked by the studio."""
    file_path: str
    filename: str
    status: DocumentStatus = DocumentStatus.PENDING
    page_count: int = 0
    file_size: int = 0
    progress: float = 0.0
    error_message: str = ""
    original_path: Optional[str] = None
    formatted_path: Optional[str] = None
    selected: bool = False


@dataclass
class Recipe:
    """A reusable set of formatting operations with parameters."""
    recipe_id: str
    name: str
    description: str
    operations: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for settings.json storage."""
        return {
            "name": self.name,
            "description": self.description,
            "operations": list(self.operations),
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, recipe_id: str, data: Dict[str, Any]) -> "Recipe":
        """Deserialize from settings.json dict."""
        return cls(
            recipe_id=recipe_id,
            name=data.get("name", recipe_id),
            description=data.get("description", ""),
            operations=data.get("operations", []),
            parameters=data.get("parameters", {}),
        )


class DocumentStudioState(QObject):
    """
    Centralized state for the Document Studio panel.

    All mutations emit signals so that UI widgets and background workers
    stay in sync without direct coupling.
    """

    # Document lifecycle
    document_added = pyqtSignal(str)            # file_path
    document_removed = pyqtSignal(str)          # file_path
    document_status_changed = pyqtSignal(str, str)  # file_path, new status value
    document_progress_changed = pyqtSignal(str, float)  # file_path, 0.0-1.0
    selection_changed = pyqtSignal()

    # Batch processing
    batch_started = pyqtSignal(str)             # recipe_id
    batch_progress = pyqtSignal(int, int)       # completed_count, total_count
    batch_completed = pyqtSignal(bool, str)     # all_success, summary

    # Recipe management
    recipe_saved = pyqtSignal(str)              # recipe_id
    recipe_removed = pyqtSignal(str)            # recipe_id

    # Panel visibility
    panel_visibility_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.documents: Dict[str, DocumentEntry] = {}
        self.recipes: Dict[str, Recipe] = {}
        self.active_recipe_id: Optional[str] = None
        self.is_batch_running: bool = False

    # -- Document operations --------------------------------------------------

    def add_document(self, file_path: str) -> Optional[DocumentEntry]:
        """Add a document to the studio. Returns the entry or None if duplicate."""
        if file_path in self.documents:
            logger.debug(f"Document already tracked: {file_path}")
            return None
        filename = os.path.basename(file_path)
        file_size = 0
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            pass
        entry = DocumentEntry(file_path=file_path, filename=filename, file_size=file_size)
        self.documents[file_path] = entry
        self.document_added.emit(file_path)
        logger.info(f"Document added to studio: {filename}")
        return entry

    def remove_document(self, file_path: str) -> bool:
        """Remove a document from the studio."""
        if file_path not in self.documents:
            return False
        del self.documents[file_path]
        self.document_removed.emit(file_path)
        logger.info(f"Document removed from studio: {file_path}")
        return True

    def clear_all_documents(self):
        """Remove all documents."""
        paths = list(self.documents.keys())
        for path in paths:
            self.remove_document(path)

    def update_status(self, file_path: str, status: DocumentStatus, error: str = ""):
        """Update processing status for a document."""
        entry = self.documents.get(file_path)
        if not entry:
            return
        entry.status = status
        if error:
            entry.error_message = error
        self.document_status_changed.emit(file_path, status.value)

    def update_progress(self, file_path: str, progress: float):
        """Update processing progress (0.0 - 1.0)."""
        entry = self.documents.get(file_path)
        if not entry:
            return
        entry.progress = max(0.0, min(1.0, progress))
        self.document_progress_changed.emit(file_path, entry.progress)

    # -- Selection ------------------------------------------------------------

    def toggle_selection(self, file_path: str):
        """Toggle selection state for a document."""
        entry = self.documents.get(file_path)
        if entry:
            entry.selected = not entry.selected
            self.selection_changed.emit()

    def select_all(self):
        """Select all documents."""
        for entry in self.documents.values():
            entry.selected = True
        self.selection_changed.emit()

    def deselect_all(self):
        """Deselect all documents."""
        for entry in self.documents.values():
            entry.selected = False
        self.selection_changed.emit()

    def get_selected_paths(self) -> List[str]:
        """Return file paths of all selected documents."""
        return [path for path, entry in self.documents.items() if entry.selected]

    # -- Recipe operations ----------------------------------------------------

    def add_recipe(self, recipe: Recipe):
        """Add or update a recipe."""
        self.recipes[recipe.recipe_id] = recipe
        self.recipe_saved.emit(recipe.recipe_id)
        logger.info(f"Recipe saved: {recipe.name} ({recipe.recipe_id})")

    def remove_recipe(self, recipe_id: str) -> bool:
        """Remove a recipe."""
        if recipe_id not in self.recipes:
            return False
        del self.recipes[recipe_id]
        self.recipe_removed.emit(recipe_id)
        logger.info(f"Recipe removed: {recipe_id}")
        return True

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Get a recipe by ID."""
        return self.recipes.get(recipe_id)

    def load_recipes_from_settings(self, recipes_dict: Dict[str, Dict]) -> int:
        """Load recipes from settings.json data. Returns count loaded."""
        count = 0
        for rid, data in recipes_dict.items():
            try:
                self.recipes[rid] = Recipe.from_dict(rid, data)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load recipe {rid}: {e}")
        return count

    def get_all_recipes_as_dict(self) -> Dict[str, Dict]:
        """Serialize all recipes for settings.json storage."""
        return {rid: recipe.to_dict() for rid, recipe in self.recipes.items()}
```

**Step 6: Run tests to verify they pass**

```bash
cd c:/Users/miguel/OneDrive/Documents/Ghostman
python -m pytest specter/tests/test_studio_state.py -v --tb=short 2>&1 | tail -25
```
Expected: All tests PASS.

**Step 7: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/__init__.py \
        specter/src/presentation/widgets/document_studio/studio_state.py \
        specter/tests/test_studio_state.py
git commit -m "feat(studio): add DocumentStudioState, DocumentEntry, Recipe data models"
```

---

### Task 2: Create DocumentCard widget

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/document_card.py`
- Test: Manual visual — card renders correctly with theme

**Step 1: Write the DocumentCard widget**

Create `specter/src/presentation/widgets/document_studio/document_card.py`:
```python
"""
DocumentCard — visual card for a single document in the Document Studio.

Shows filename, metadata, progress bar, status, and selection checkbox.
Emits signals for user interactions (click, select, remove, preview).
"""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from .studio_state import DocumentEntry, DocumentStatus

logger = logging.getLogger("specter.document_studio.card")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


def _format_file_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


class DocumentCard(QFrame):
    """
    Visual card representing a document in the studio.

    Layout:
        [checkbox] [icon] filename.docx              [remove_btn]
                          12 pages  245 KB
                          [progress_bar]
                          Status: Pending
    """

    clicked = pyqtSignal(str)                    # file_path
    selection_toggled = pyqtSignal(str, bool)     # file_path, selected
    remove_requested = pyqtSignal(str)            # file_path
    preview_requested = pyqtSignal(str)           # file_path

    # Extension-to-icon mapping
    _ICONS = {
        ".docx": "\U0001f4c4",
        ".doc": "\U0001f4c4",
        ".pdf": "\U0001f4d5",
        ".txt": "\U0001f4dd",
        ".xlsx": "\U0001f4ca",
        ".xls": "\U0001f4ca",
        ".pptx": "\U0001f4ca",
    }

    def __init__(self, entry: DocumentEntry, parent=None):
        super().__init__(parent)
        self._file_path = entry.file_path
        self._entry = entry
        self.setObjectName("document_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._init_ui(entry)

    def _init_ui(self, entry: DocumentEntry):
        """Build the card layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(3)

        # Row 1: checkbox + icon + filename + remove button
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._checkbox = QCheckBox()
        self._checkbox.setChecked(entry.selected)
        self._checkbox.toggled.connect(
            lambda checked: self.selection_toggled.emit(self._file_path, checked)
        )
        row1.addWidget(self._checkbox)

        ext = os.path.splitext(entry.filename)[1].lower()
        icon_text = self._ICONS.get(ext, "\U0001f4c1")
        icon_label = QLabel(icon_text)
        icon_label.setFixedWidth(20)
        row1.addWidget(icon_label)

        self._filename_label = QLabel(entry.filename)
        self._filename_label.setObjectName("card_filename")
        self._filename_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        row1.addWidget(self._filename_label)

        self._remove_btn = QToolButton()
        self._remove_btn.setText("\u2715")
        self._remove_btn.setToolTip("Remove from studio")
        self._remove_btn.setFixedSize(20, 20)
        self._remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self._file_path)
        )
        row1.addWidget(self._remove_btn)

        main_layout.addLayout(row1)

        # Row 2: metadata (page count, file size)
        meta_parts = []
        if entry.page_count > 0:
            meta_parts.append(f"{entry.page_count} pages")
        if entry.file_size > 0:
            meta_parts.append(_format_file_size(entry.file_size))
        self._meta_label = QLabel(" \u00b7 ".join(meta_parts) if meta_parts else "")
        self._meta_label.setObjectName("card_meta")
        main_layout.addWidget(self._meta_label)

        # Row 3: progress bar (hidden by default)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.setVisible(False)
        main_layout.addWidget(self._progress_bar)

        # Row 4: status label
        self._status_label = QLabel(f"Status: {entry.status.value.capitalize()}")
        self._status_label.setObjectName("card_status")
        main_layout.addWidget(self._status_label)

    # -- Public API -----------------------------------------------------------

    @property
    def file_path(self) -> str:
        return self._file_path

    def update_status(self, status: DocumentStatus, error: str = ""):
        """Update the displayed status."""
        self._entry.status = status
        text = f"Status: {status.value.capitalize()}"
        if error:
            text += f" \u2014 {error}"
        self._status_label.setText(text)

        # Show/hide progress bar
        self._progress_bar.setVisible(status == DocumentStatus.PROCESSING)
        if status != DocumentStatus.PROCESSING:
            self._progress_bar.setValue(0)

        self._apply_status_border()

    def update_progress(self, progress: float):
        """Update the progress bar (0.0 to 1.0)."""
        self._progress_bar.setValue(int(progress * 100))

    def set_selected(self, selected: bool):
        """Update checkbox without emitting signal."""
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(selected)
        self._checkbox.blockSignals(False)

    def update_metadata(self, page_count: int = 0, file_size: int = 0):
        """Update the metadata line."""
        parts = []
        if page_count > 0:
            parts.append(f"{page_count} pages")
        if file_size > 0:
            parts.append(_format_file_size(file_size))
        self._meta_label.setText(" \u00b7 ".join(parts))

    # -- Theme ----------------------------------------------------------------

    def apply_theme(self, colors: "ColorSystem"):
        """Apply theme colors to this card."""
        if not THEME_AVAILABLE or not colors:
            return
        self._colors = colors
        self._apply_status_border()

        self._filename_label.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; background: transparent;"
        )
        self._meta_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 11px; background: transparent;"
        )
        self._status_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 11px; background: transparent;"
        )
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {colors.border_secondary};
                border-radius: 3px;
                background: {colors.background_tertiary};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: {colors.primary};
                border-radius: 2px;
            }}
        """)

    def _apply_status_border(self):
        """Set card border color based on current status."""
        colors = getattr(self, "_colors", None)
        if not colors:
            return
        status = self._entry.status
        border_map = {
            DocumentStatus.PENDING: colors.text_disabled,
            DocumentStatus.QUEUED: colors.text_disabled,
            DocumentStatus.PROCESSING: colors.primary,
            DocumentStatus.COMPLETED: colors.status_success,
            DocumentStatus.FAILED: colors.status_error,
        }
        border = border_map.get(status, colors.border_primary)
        self.setStyleSheet(f"""
            QFrame#document_card {{
                background: {colors.background_secondary};
                border: 1.5px solid {border};
                border-radius: 6px;
            }}
            QFrame#document_card:hover {{
                border-color: {colors.primary};
                background: {colors.background_tertiary};
            }}
        """)

    # -- Events ---------------------------------------------------------------

    def mousePressEvent(self, event):
        """Emit clicked signal on left click (for preview navigation)."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't emit click if checkbox or remove button was the target
            child = self.childAt(event.pos())
            if child not in (self._checkbox, self._remove_btn):
                self.clicked.emit(self._file_path)
        super().mousePressEvent(event)
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/document_card.py
git commit -m "feat(studio): add DocumentCard widget with status, progress, theme"
```

---

### Task 3: Create StudioHeaderBar

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/studio_header_bar.py`

**Step 1: Write the header bar**

Create `specter/src/presentation/widgets/document_studio/studio_header_bar.py`:
```python
"""
StudioHeaderBar — title bar for the Document Studio panel.

Shows "Document Studio" title with a collapse/close button.
"""

import logging
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QSizePolicy

logger = logging.getLogger("specter.document_studio.header")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


class StudioHeaderBar(QFrame):
    """Header bar with title and collapse button."""

    collapse_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("studio_header_bar")
        self.setFixedHeight(36)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)

        self._title = QLabel("\U0001f4da Document Studio")
        self._title.setObjectName("studio_title")
        self._title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._title)

        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("\u25c0")  # left-pointing triangle
        self._collapse_btn.setToolTip("Collapse panel")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        layout.addWidget(self._collapse_btn)

    def apply_theme(self, colors: "ColorSystem"):
        """Apply theme to header bar."""
        if not THEME_AVAILABLE or not colors:
            return
        self.setStyleSheet(f"""
            QFrame#studio_header_bar {{
                background: {colors.background_tertiary};
                border: none;
                border-bottom: 1px solid {colors.border_secondary};
            }}
        """)
        self._title.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; font-size: 13px; background: transparent;"
        )
        if colors:
            ButtonStyleManager.apply_unified_button_style(
                self._collapse_btn, colors, "tool", "icon", "normal"
            )
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/studio_header_bar.py
git commit -m "feat(studio): add StudioHeaderBar widget"
```

---

### Task 4: Create DocumentStudioPanel (main panel shell)

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/studio_panel.py`

**Step 1: Write the main panel widget**

Create `specter/src/presentation/widgets/document_studio/studio_panel.py`:
```python
"""
DocumentStudioPanel — main panel widget for the Document Studio.

Contains a header bar, stacked views (document list, preview, diff, recipe editor),
and a status bar. Manages view navigation and theme application.
"""

import logging
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .document_card import DocumentCard
from .studio_header_bar import StudioHeaderBar
from .studio_state import DocumentEntry, DocumentStatus, DocumentStudioState, Recipe

logger = logging.getLogger("specter.document_studio.panel")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager, StyleTemplates
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


# View indices in the QStackedWidget
VIEW_LIST = 0
VIEW_PREVIEW = 1
VIEW_DIFF = 2
VIEW_RECIPE_EDITOR = 3


class DocumentStudioPanel(QWidget):
    """
    Main Document Studio panel.

    Provides a visual workspace for document management, batch formatting,
    recipe creation, preview, and diff viewing.
    """

    # Signals for REPL integration
    collapse_requested = pyqtSignal()
    apply_recipe_requested = pyqtSignal(str, list)  # recipe_id, file_paths
    files_dropped = pyqtSignal(list)                 # list of file paths

    def __init__(self, state: Optional[DocumentStudioState] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("document_studio_panel")
        self.setMinimumWidth(280)
        self._state = state or DocumentStudioState(self)
        self._cards: dict[str, DocumentCard] = {}
        self._theme_manager = get_theme_manager() if THEME_AVAILABLE else None
        self._init_ui()
        self._connect_state_signals()
        self._apply_theme()
        self.setAcceptDrops(True)

    @property
    def state(self) -> DocumentStudioState:
        return self._state

    # -- UI Setup -------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        self._header = StudioHeaderBar()
        self._header.collapse_requested.connect(self.collapse_requested.emit)
        main_layout.addWidget(self._header)

        # Stacked widget for views
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # View 0: Document list view
        self._list_view = self._create_list_view()
        self._stack.addWidget(self._list_view)

        # Views 1-3: Placeholder — will be replaced when those features are built
        # Preview, Diff, Recipe Editor
        for _ in range(3):
            placeholder = QLabel("Coming soon...")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._stack.addWidget(placeholder)

        # Status bar
        self._status_bar = self._create_status_bar()
        main_layout.addWidget(self._status_bar)

        # Start on list view
        self._stack.setCurrentIndex(VIEW_LIST)

    def _create_list_view(self) -> QWidget:
        """Create the document list view with batch controls."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Batch controls toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self._select_all_btn = QToolButton()
        self._select_all_btn.setText("Select All")
        self._select_all_btn.setToolTip("Select all documents")
        self._select_all_btn.clicked.connect(self._state.select_all)
        toolbar.addWidget(self._select_all_btn)

        self._deselect_all_btn = QToolButton()
        self._deselect_all_btn.setText("None")
        self._deselect_all_btn.setToolTip("Deselect all")
        self._deselect_all_btn.clicked.connect(self._state.deselect_all)
        toolbar.addWidget(self._deselect_all_btn)

        toolbar.addStretch()

        self._apply_btn = QToolButton()
        self._apply_btn.setText("Apply Recipe")
        self._apply_btn.setToolTip("Apply selected recipe to selected files")
        self._apply_btn.clicked.connect(self._on_apply_clicked)
        toolbar.addWidget(self._apply_btn)

        layout.addLayout(toolbar)

        # Scroll area for document cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_content = QWidget()
        self._cards_layout = QVBoxLayout(self._scroll_content)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(4)
        self._cards_layout.addStretch()  # Push cards to top
        self._scroll.setWidget(self._scroll_content)
        layout.addWidget(self._scroll, 1)

        # Drop zone hint (shown when empty)
        self._empty_hint = QLabel("Drop DOCX files here\nor use the REPL to add files")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setObjectName("studio_empty_hint")
        self._empty_hint.setVisible(True)
        layout.addWidget(self._empty_hint)

        # Batch progress bar
        self._batch_progress = QProgressBar()
        self._batch_progress.setRange(0, 100)
        self._batch_progress.setFixedHeight(16)
        self._batch_progress.setVisible(False)
        layout.addWidget(self._batch_progress)

        return view

    def _create_status_bar(self) -> QFrame:
        """Create the status bar at the bottom of the panel."""
        bar = QFrame()
        bar.setObjectName("studio_status_bar")
        bar.setFixedHeight(24)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 2, 8, 2)

        self._status_label = QLabel("No documents")
        self._status_label.setObjectName("studio_status_text")
        layout.addWidget(self._status_label)

        return bar

    # -- State signal handlers ------------------------------------------------

    def _connect_state_signals(self):
        self._state.document_added.connect(self._on_document_added)
        self._state.document_removed.connect(self._on_document_removed)
        self._state.document_status_changed.connect(self._on_status_changed)
        self._state.document_progress_changed.connect(self._on_progress_changed)
        self._state.selection_changed.connect(self._on_selection_changed)
        self._state.batch_progress.connect(self._on_batch_progress)
        self._state.batch_completed.connect(self._on_batch_completed)

    def _on_document_added(self, file_path: str):
        entry = self._state.documents.get(file_path)
        if not entry:
            return
        card = DocumentCard(entry)
        card.clicked.connect(lambda fp: self.preview_requested_internal(fp))
        card.selection_toggled.connect(
            lambda fp, sel: self._state.toggle_selection(fp)
        )
        card.remove_requested.connect(
            lambda fp: self._state.remove_document(fp)
        )

        # Insert before the stretch item
        count = self._cards_layout.count()
        self._cards_layout.insertWidget(count - 1, card)
        self._cards[file_path] = card

        # Apply theme to new card
        if self._theme_manager and THEME_AVAILABLE:
            colors = self._theme_manager.current_theme
            if colors:
                card.apply_theme(colors)

        self._empty_hint.setVisible(False)
        self._update_status_text()

    def _on_document_removed(self, file_path: str):
        card = self._cards.pop(file_path, None)
        if card:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._empty_hint.setVisible(len(self._cards) == 0)
        self._update_status_text()

    def _on_status_changed(self, file_path: str, status_value: str):
        card = self._cards.get(file_path)
        if card:
            try:
                status = DocumentStatus(status_value)
            except ValueError:
                return
            entry = self._state.documents.get(file_path)
            error = entry.error_message if entry else ""
            card.update_status(status, error)
        self._update_status_text()

    def _on_progress_changed(self, file_path: str, progress: float):
        card = self._cards.get(file_path)
        if card:
            card.update_progress(progress)

    def _on_selection_changed(self):
        for path, card in self._cards.items():
            entry = self._state.documents.get(path)
            if entry:
                card.set_selected(entry.selected)

    def _on_batch_progress(self, completed: int, total: int):
        self._batch_progress.setVisible(True)
        if total > 0:
            self._batch_progress.setValue(int(completed / total * 100))
        self._status_label.setText(f"Processing {completed}/{total}...")

    def _on_batch_completed(self, all_success: bool, summary: str):
        self._batch_progress.setVisible(False)
        self._status_label.setText(summary)

    # -- Actions --------------------------------------------------------------

    def _on_apply_clicked(self):
        selected = self._state.get_selected_paths()
        if not selected:
            self._status_label.setText("No files selected")
            return
        recipe_id = self._state.active_recipe_id
        if not recipe_id:
            self._status_label.setText("No recipe selected")
            return
        self.apply_recipe_requested.emit(recipe_id, selected)

    def preview_requested_internal(self, file_path: str):
        """Navigate to preview view (placeholder until preview_view.py is built)."""
        logger.info(f"Preview requested: {file_path}")
        # Will switch to VIEW_PREVIEW once that view exists

    def navigate_to_list(self):
        """Return to the document list view."""
        self._stack.setCurrentIndex(VIEW_LIST)

    def navigate_to_preview(self, file_path: str):
        """Show preview for a document."""
        self._stack.setCurrentIndex(VIEW_PREVIEW)

    def navigate_to_diff(self, original_path: str, formatted_path: str):
        """Show before/after diff."""
        self._stack.setCurrentIndex(VIEW_DIFF)

    def navigate_to_recipe_editor(self, recipe: Optional[Recipe] = None):
        """Open recipe editor (new or edit existing)."""
        self._stack.setCurrentIndex(VIEW_RECIPE_EDITOR)

    # -- Status ---------------------------------------------------------------

    def _update_status_text(self):
        total = len(self._state.documents)
        selected = len(self._state.get_selected_paths())
        completed = sum(
            1 for e in self._state.documents.values()
            if e.status == DocumentStatus.COMPLETED
        )
        failed = sum(
            1 for e in self._state.documents.values()
            if e.status == DocumentStatus.FAILED
        )
        parts = [f"{total} files"]
        if selected > 0:
            parts.append(f"{selected} selected")
        if completed > 0:
            parts.append(f"{completed} done")
        if failed > 0:
            parts.append(f"{failed} failed")
        self._status_label.setText(" \u00b7 ".join(parts))

    # -- Theme ----------------------------------------------------------------

    def _apply_theme(self):
        if not self._theme_manager or not THEME_AVAILABLE:
            return
        colors = self._theme_manager.current_theme
        if not colors:
            return

        self.setStyleSheet(f"""
            QWidget#document_studio_panel {{
                background: {colors.background_primary};
                border-left: 1px solid {colors.border_secondary};
            }}
        """)

        self._header.apply_theme(colors)

        # Status bar
        self._status_bar.setStyleSheet(f"""
            QFrame#studio_status_bar {{
                background: {colors.background_tertiary};
                border-top: 1px solid {colors.border_secondary};
            }}
        """)
        self._status_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 11px; background: transparent;"
        )

        # Empty hint
        self._empty_hint.setStyleSheet(
            f"color: {colors.text_disabled}; font-size: 12px; background: transparent;"
        )

        # Batch controls
        for btn in (self._select_all_btn, self._deselect_all_btn, self._apply_btn):
            ButtonStyleManager.apply_unified_button_style(
                btn, colors, "tool", "small", "normal"
            )

        # Scroll area
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QWidget {{
                background: transparent;
            }}
        """)

        # Batch progress bar
        self._batch_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {colors.border_secondary};
                border-radius: 4px;
                background: {colors.background_tertiary};
            }}
            QProgressBar::chunk {{
                background: {colors.primary};
                border-radius: 3px;
            }}
        """)

        # Re-theme all cards
        for card in self._cards.values():
            card.apply_theme(colors)

        # Connect to future theme changes
        if hasattr(self._theme_manager, "theme_changed"):
            try:
                self._theme_manager.theme_changed.disconnect(self._apply_theme)
            except TypeError:
                pass
            self._theme_manager.theme_changed.connect(self._apply_theme)

    # -- Drag and drop --------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            has_docx = any(
                url.toLocalFile().lower().endswith((".docx", ".doc"))
                for url in urls
            )
            if has_docx:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith((".docx", ".doc")):
                    paths.append(path)
            if paths:
                for path in paths:
                    self._state.add_document(path)
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        event.ignore()
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/studio_panel.py
git commit -m "feat(studio): add DocumentStudioPanel with list view, cards, batch controls"
```

---

### Task 5: Integrate panel into FloatingREPLWindow via QSplitter

**Files:**
- Modify: `specter/src/presentation/widgets/floating_repl.py:10-11,197-201`
- Modify: `specter/src/presentation/widgets/repl_widget.py:~5928` (toolbar button area)

**Step 1: Modify `floating_repl.py` — add QSplitter**

In `floating_repl.py`, add import at top (after line 10):
```python
from PyQt6.QtWidgets import QWidget, QMainWindow, QSplitter
```

Replace `_init_ui()` method (lines 197-213) with:
```python
    def _init_ui(self):
        """Initialize the user interface."""
        # Create REPL widget
        self.repl_widget = REPLWidget()

        # Create Document Studio panel (lazy import to avoid circular)
        try:
            from .document_studio.studio_panel import DocumentStudioPanel
            self._studio_panel = DocumentStudioPanel()
            self._studio_panel.collapse_requested.connect(self._collapse_studio)
        except Exception as e:
            logger.warning(f"Failed to create Document Studio panel: {e}")
            self._studio_panel = None

        # Wrap in QSplitter if studio panel exists
        if self._studio_panel:
            self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
            self._main_splitter.setChildrenCollapsible(True)
            self._main_splitter.setHandleWidth(3)
            self._main_splitter.addWidget(self.repl_widget)
            self._main_splitter.addWidget(self._studio_panel)
            # Studio collapsed by default
            self._main_splitter.setSizes([1, 0])
            self._studio_panel.setVisible(False)
            self.setCentralWidget(self._main_splitter)
            # Transparent splitter handle
            self._main_splitter.setStyleSheet(
                "QSplitter::handle { background: transparent; }"
            )
        else:
            self._main_splitter = None
            self.setCentralWidget(self.repl_widget)

        # REPL widget already loads its own opacity from settings in its constructor

        # Connect REPL signals
        self.repl_widget.minimize_requested.connect(self.close)
        self.repl_widget.command_entered.connect(self.command_entered.emit)

        logger.debug("FloatingREPL UI initialized")

    def toggle_studio_panel(self, visible: Optional[bool] = None):
        """Toggle the Document Studio panel visibility."""
        if not self._studio_panel or not self._main_splitter:
            logger.warning("Document Studio panel not available")
            return

        if visible is None:
            visible = not self._studio_panel.isVisible()

        if visible:
            self._studio_panel.setVisible(True)
            # Restore reasonable split — 60% REPL, 40% Studio
            total = self._main_splitter.width()
            repl_w = int(total * 0.6)
            studio_w = total - repl_w
            self._main_splitter.setSizes([repl_w, studio_w])
        else:
            self._main_splitter.setSizes([1, 0])
            self._studio_panel.setVisible(False)

        if self._studio_panel.state:
            self._studio_panel.state.panel_visibility_changed.emit(visible)

    def _collapse_studio(self):
        """Collapse the studio panel (called from header bar close button)."""
        self.toggle_studio_panel(False)

    @property
    def studio_panel(self):
        """Access the Document Studio panel (may be None)."""
        return self._studio_panel
```

**Step 2: Add Studio toggle button to REPL toolbar**

In `repl_widget.py`, after the settings button is added to the toolbar (approximately line 5928, after `toolbar_layout.addWidget(self.settings_btn)`), add:

```python
        # Document Studio toggle button
        self.studio_btn = QToolButton()
        self.studio_btn.setText("\U0001f4da")
        self.studio_btn.setToolTip("Toggle Document Studio (Ctrl+Shift+D)")
        self.studio_btn.setCheckable(True)
        self.studio_btn.clicked.connect(self._toggle_studio_panel)
        self._style_tool_button(self.studio_btn)
        toolbar_layout.addWidget(self.studio_btn)
```

Add `self.studio_btn` to the `_toolbar_buttons` list (line ~5942-5945):
```python
        self._toolbar_buttons = [
            self.toolbar_new_conv_btn, self.browse_btn,
            self.export_btn, self.settings_btn, self.studio_btn
        ]
```

Add the toggle method (after `_toggle_file_browser` at ~line 13251):
```python
    def _toggle_studio_panel(self):
        """Toggle the Document Studio panel via FloatingREPLWindow."""
        try:
            window = self.window()
            if hasattr(window, 'toggle_studio_panel'):
                window.toggle_studio_panel()
                # Update button checked state
                if hasattr(window, 'studio_panel') and window.studio_panel:
                    self.studio_btn.setChecked(window.studio_panel.isVisible())
            else:
                logger.warning("Parent window doesn't support studio panel toggle")
        except Exception as e:
            logger.error(f"Failed to toggle studio panel: {e}")
```

**Step 3: Add keyboard shortcut in floating_repl.py**

In `_setup_keyboard_shortcuts()` (line ~250), add:
```python
        # Ctrl+Shift+D to toggle Document Studio
        studio_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        studio_shortcut.activated.connect(lambda: self.toggle_studio_panel())
```

**Step 4: Test manually**

```bash
cd c:/Users/miguel/OneDrive/Documents/Ghostman
python -m specter --debug
```

Test: Click the studio button in the toolbar. The panel should slide open on the right. Click the collapse button. The panel should collapse. Ctrl+Shift+D toggles.

**Step 5: Commit**

```bash
git add specter/src/presentation/widgets/floating_repl.py \
        specter/src/presentation/widgets/repl_widget.py
git commit -m "feat(studio): integrate Document Studio panel via QSplitter in REPL window"
```

---

### Task 6: Add settings and theme styles

**Files:**
- Modify: `specter/src/infrastructure/storage/settings_manager.py:~178` (after 'avatar' in DEFAULT_SETTINGS)
- Modify: `specter/src/ui/themes/style_templates.py:~2656` (end of file)

**Step 1: Add document_studio section to DEFAULT_SETTINGS**

In `settings_manager.py`, after the `'avatar'` section (after line ~179), add:
```python
    'document_studio': {
        'panel_visible': False,
        'splitter_sizes': [600, 350],
        'recipes': {},
    },
```

**Step 2: Add style templates**

At the end of `style_templates.py` (after `get_file_upload_button_style`, line ~2656), add:
```python
    @staticmethod
    def get_document_studio_panel_style(colors: ColorSystem) -> str:
        """Style template for the Document Studio panel container."""
        if not colors:
            return ""
        return f"""
        QWidget#document_studio_panel {{
            background-color: {colors.background_primary};
            border-left: 1px solid {colors.border_secondary};
        }}
        """

    @staticmethod
    def get_document_card_style(colors: ColorSystem, status: str = "pending") -> str:
        """Style template for document cards with status-dependent border."""
        if not colors:
            return ""
        border_map = {
            "pending": colors.text_disabled,
            "queued": colors.text_disabled,
            "processing": colors.primary,
            "completed": colors.status_success,
            "failed": colors.status_error,
        }
        border = border_map.get(status, colors.border_primary)
        return f"""
        QFrame#document_card {{
            background: {colors.background_secondary};
            border: 1.5px solid {border};
            border-radius: 6px;
        }}
        QFrame#document_card:hover {{
            border-color: {colors.primary};
            background: {colors.background_tertiary};
        }}
        """

    @staticmethod
    def get_studio_header_style(colors: ColorSystem) -> str:
        """Style template for the Document Studio header bar."""
        if not colors:
            return ""
        return f"""
        QFrame#studio_header_bar {{
            background: {colors.background_tertiary};
            border: none;
            border-bottom: 1px solid {colors.border_secondary};
        }}
        """

    @staticmethod
    def get_studio_status_bar_style(colors: ColorSystem) -> str:
        """Style template for the Document Studio status bar."""
        if not colors:
            return ""
        return f"""
        QFrame#studio_status_bar {{
            background: {colors.background_tertiary};
            border-top: 1px solid {colors.border_secondary};
        }}
        """
```

**Step 3: Commit**

```bash
git add specter/src/infrastructure/storage/settings_manager.py \
        specter/src/ui/themes/style_templates.py
git commit -m "feat(studio): add settings defaults and theme style templates"
```

---

## Phase 2: Batch Processing + Recipes

### Task 7: Create BatchProcessor (background QThread worker)

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/batch_processor.py`
- Test: `specter/tests/test_batch_processor.py`

**Step 1: Write the test**

Create `specter/tests/test_batch_processor.py`:
```python
"""Tests for BatchProcessor."""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from specter.src.presentation.widgets.document_studio.batch_processor import (
    BatchProcessor,
)
from specter.src.presentation.widgets.document_studio.studio_state import (
    DocumentStudioState,
    Recipe,
)


@pytest.fixture
def temp_docx(tmp_path):
    """Create a minimal .docx file for testing."""
    try:
        from docx import Document
        doc = Document()
        doc.add_paragraph("Hello World")
        path = tmp_path / "test.docx"
        doc.save(str(path))
        return str(path)
    except ImportError:
        pytest.skip("python-docx not installed")


@pytest.fixture
def recipe():
    return Recipe(
        recipe_id="test_recipe",
        name="Test Recipe",
        description="A test",
        operations=["standardize_fonts"],
        parameters={"font_name": "Arial", "font_size": 12},
    )


class TestBatchProcessor:
    def test_init(self):
        state = DocumentStudioState()
        proc = BatchProcessor(state)
        assert proc._state is state
        assert proc._cancelled is False

    def test_cancel(self):
        state = DocumentStudioState()
        proc = BatchProcessor(state)
        proc.cancel()
        assert proc._cancelled is True
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest specter/tests/test_batch_processor.py -v --tb=short 2>&1 | head -20
```
Expected: FAIL — module not found

**Step 3: Write `batch_processor.py`**

Create `specter/src/presentation/widgets/document_studio/batch_processor.py`:
```python
"""
BatchProcessor — background worker for batch document formatting.

Processes multiple files sequentially using DocxFormatterSkill, emitting
progress signals for each file. Runs in a QThread to keep the UI responsive.
"""

import asyncio
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .studio_state import DocumentStatus, DocumentStudioState, Recipe

logger = logging.getLogger("specter.document_studio.batch")


class BatchWorker(QObject):
    """Worker that runs formatting operations in a QThread."""

    file_started = pyqtSignal(str)                    # file_path
    file_progress = pyqtSignal(str, float)            # file_path, 0.0-1.0
    file_completed = pyqtSignal(str, bool, str, str)  # file_path, success, message, formatted_path
    batch_finished = pyqtSignal(int, int)             # success_count, total_count
    error_occurred = pyqtSignal(str, str)             # file_path, error_message

    def __init__(self, file_paths: List[str], recipe: Recipe, parent=None):
        super().__init__(parent)
        self._file_paths = file_paths
        self._recipe = recipe
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Process all files sequentially."""
        success_count = 0
        total = len(self._file_paths)

        for i, file_path in enumerate(self._file_paths):
            if self._cancelled:
                logger.info("Batch processing cancelled")
                break

            self.file_started.emit(file_path)

            try:
                formatted_path = self._process_single_file(file_path)
                success_count += 1
                self.file_completed.emit(file_path, True, "Formatted successfully", formatted_path)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to format {file_path}: {error_msg}")
                self.file_completed.emit(file_path, False, error_msg, "")
                self.error_occurred.emit(file_path, error_msg)

            # Progress: proportion of files done
            self.file_progress.emit(file_path, (i + 1) / total)

        self.batch_finished.emit(success_count, total)

    def _process_single_file(self, file_path: str) -> str:
        """
        Format a single file using DocxFormatterSkill.

        Returns the path to the formatted file.
        """
        # Lazy import to avoid circular dependencies
        from specter.src.infrastructure.skills.skills_library.docx_formatter_skill import (
            DocxFormatterSkill,
        )

        skill = DocxFormatterSkill()

        # Build params matching what execute() expects
        params = {
            "file_path": file_path,
            "operations": self._recipe.operations,
        }
        # Add recipe parameters (font_name, font_size, margin_inches, etc.)
        params.update(self._recipe.parameters)

        # DocxFormatterSkill.execute() is async — run in a new event loop
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(skill.execute(**params))
        finally:
            loop.close()

        if not result.success:
            raise RuntimeError(result.error or result.message)

        formatted_path = ""
        if result.data and isinstance(result.data, dict):
            formatted_path = result.data.get("formatted_path", "")

        return formatted_path


class BatchProcessor(QObject):
    """
    High-level batch processor that manages a QThread worker.

    Usage:
        processor = BatchProcessor(state)
        processor.start_batch(file_paths, recipe)
        # ... signals update state and UI ...
        processor.cancel()  # optional
    """

    def __init__(self, state: DocumentStudioState, parent=None):
        super().__init__(parent)
        self._state = state
        self._thread: Optional[QThread] = None
        self._worker: Optional[BatchWorker] = None
        self._cancelled = False

    def start_batch(self, file_paths: List[str], recipe: Recipe):
        """Start batch processing in a background thread."""
        if self._thread and self._thread.isRunning():
            logger.warning("Batch already running — ignoring new request")
            return

        self._cancelled = False

        # Mark all files as queued
        for fp in file_paths:
            self._state.update_status(fp, DocumentStatus.QUEUED)

        # Emit batch started
        self._state.is_batch_running = True
        self._state.batch_started.emit(recipe.recipe_id)

        # Create thread + worker
        self._thread = QThread()
        self._worker = BatchWorker(file_paths, recipe)
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.batch_finished.connect(self._thread.quit)
        self._worker.batch_finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()
        logger.info(f"Batch started: {len(file_paths)} files with recipe '{recipe.name}'")

    def cancel(self):
        """Cancel the running batch."""
        self._cancelled = True
        if self._worker:
            self._worker.cancel()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    # -- Worker signal handlers -----------------------------------------------

    def _on_file_started(self, file_path: str):
        self._state.update_status(file_path, DocumentStatus.PROCESSING)

    def _on_file_completed(self, file_path: str, success: bool, message: str, formatted_path: str):
        if success:
            self._state.update_status(file_path, DocumentStatus.COMPLETED)
            entry = self._state.documents.get(file_path)
            if entry:
                entry.formatted_path = formatted_path
                entry.original_path = file_path
        else:
            self._state.update_status(file_path, DocumentStatus.FAILED, error=message)

    def _on_file_progress(self, file_path: str, progress: float):
        self._state.update_progress(file_path, progress)
        # Also update batch-level progress
        total = len(self._state.documents)
        completed = sum(
            1 for e in self._state.documents.values()
            if e.status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED)
        )
        self._state.batch_progress.emit(completed, total)

    def _on_batch_finished(self, success_count: int, total_count: int):
        self._state.is_batch_running = False
        all_success = success_count == total_count
        summary = f"{success_count}/{total_count} files formatted successfully"
        self._state.batch_completed.emit(all_success, summary)
        logger.info(f"Batch completed: {summary}")
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest specter/tests/test_batch_processor.py -v --tb=short
```
Expected: PASS

**Step 5: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/batch_processor.py \
        specter/tests/test_batch_processor.py
git commit -m "feat(studio): add BatchProcessor with QThread worker for batch formatting"
```

---

### Task 8: Create RecipeEditor and RecipeLibrary widgets

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/recipe_editor.py`
- Create: `specter/src/presentation/widgets/document_studio/recipe_library.py`

**Step 1: Write RecipeEditor**

Create `specter/src/presentation/widgets/document_studio/recipe_editor.py`:
```python
"""
RecipeEditor — form for creating and editing formatting recipes.

Shows checkboxes for each formatting operation and parameter fields
for font name, font size, margins, etc.
"""

import logging
import uuid
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .studio_state import Recipe

logger = logging.getLogger("specter.document_studio.recipe_editor")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

# Available operations with human-readable labels
OPERATION_LABELS = {
    "standardize_fonts": "Standardize Fonts",
    "fix_margins": "Fix Margins",
    "normalize_spacing": "Normalize Spacing",
    "fix_bullets": "Fix Bullet Lists",
    "fix_spelling": "Fix Spelling",
    "fix_case": "Fix Case",
    "normalize_headings": "Normalize Headings",
    "find_replace": "Find & Replace",
    "set_font_color": "Set Font Color",
    "set_alignment": "Set Alignment",
    "set_indent": "Set Indent",
}


class RecipeEditor(QWidget):
    """Form for creating/editing a formatting recipe."""

    recipe_saved = pyqtSignal(object)    # Recipe
    cancelled = pyqtSignal()

    def __init__(self, recipe: Optional[Recipe] = None, parent=None):
        super().__init__(parent)
        self._editing = recipe
        self._init_ui()
        if recipe:
            self._load_recipe(recipe)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Back button
        back_btn = QPushButton("\u2190 Back to list")
        back_btn.clicked.connect(self.cancelled.emit)
        layout.addWidget(back_btn)
        self._back_btn = back_btn

        # Title
        title = QLabel("New Recipe" if not self._editing else "Edit Recipe")
        title.setObjectName("recipe_editor_title")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        self._title_label = title

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(8)

        # Name
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g., Corporate Memo")
        form.addRow("Name:", self._name_input)

        # Description
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText("Brief description")
        form.addRow("Description:", self._desc_input)

        # Operations checkboxes
        ops_group = QGroupBox("Formatting Operations")
        ops_layout = QVBoxLayout(ops_group)
        self._op_checkboxes = {}
        for op_id, label in OPERATION_LABELS.items():
            cb = QCheckBox(label)
            self._op_checkboxes[op_id] = cb
            ops_layout.addWidget(cb)
        form.addRow(ops_group)

        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QFormLayout(params_group)

        self._font_name = QComboBox()
        self._font_name.setEditable(True)
        self._font_name.addItems([
            "Calibri", "Arial", "Times New Roman", "Helvetica",
            "Georgia", "Verdana", "Cambria", "Garamond",
        ])
        params_layout.addRow("Font Name:", self._font_name)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(11)
        params_layout.addRow("Font Size (pt):", self._font_size)

        self._margin = QDoubleSpinBox()
        self._margin.setRange(0.25, 3.0)
        self._margin.setValue(1.0)
        self._margin.setSingleStep(0.25)
        self._margin.setSuffix(" in")
        params_layout.addRow("Margins:", self._margin)

        form.addRow(params_group)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        # Save/Cancel buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancelled.emit)
        btn_row.addWidget(cancel_btn)
        self._cancel_btn = cancel_btn

        save_btn = QPushButton("Save Recipe")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        self._save_btn = save_btn

        layout.addLayout(btn_row)

    def _load_recipe(self, recipe: Recipe):
        """Populate form from an existing recipe."""
        self._name_input.setText(recipe.name)
        self._desc_input.setText(recipe.description)
        for op_id, cb in self._op_checkboxes.items():
            cb.setChecked(op_id in recipe.operations)
        if "font_name" in recipe.parameters:
            self._font_name.setCurrentText(recipe.parameters["font_name"])
        if "font_size" in recipe.parameters:
            self._font_size.setValue(recipe.parameters["font_size"])
        if "margin_inches" in recipe.parameters:
            self._margin.setValue(recipe.parameters["margin_inches"])

    def _save(self):
        """Build recipe from form and emit."""
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setFocus()
            return

        operations = [op for op, cb in self._op_checkboxes.items() if cb.isChecked()]
        if not operations:
            return

        recipe_id = self._editing.recipe_id if self._editing else str(uuid.uuid4())[:8]
        recipe = Recipe(
            recipe_id=recipe_id,
            name=name,
            description=self._desc_input.text().strip(),
            operations=operations,
            parameters={
                "font_name": self._font_name.currentText(),
                "font_size": self._font_size.value(),
                "margin_inches": self._margin.value(),
            },
        )
        self.recipe_saved.emit(recipe)

    def apply_theme(self, colors):
        """Apply theme colors."""
        if not THEME_AVAILABLE or not colors:
            return
        self._title_label.setStyleSheet(
            f"color: {colors.text_primary}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        ButtonStyleManager.apply_unified_button_style(
            self._save_btn, colors, "push", "medium", "success"
        )
        ButtonStyleManager.apply_unified_button_style(
            self._cancel_btn, colors, "push", "medium", "normal"
        )
```

**Step 2: Write RecipeLibrary**

Create `specter/src/presentation/widgets/document_studio/recipe_library.py`:
```python
"""
RecipeLibrary — list of saved recipes with CRUD operations.

Shows saved recipes as a selectable list with edit/delete/apply actions.
"""

import logging
from typing import Dict, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .studio_state import DocumentStudioState, Recipe

logger = logging.getLogger("specter.document_studio.recipe_library")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


class RecipeLibrary(QWidget):
    """Widget showing all saved recipes with management actions."""

    recipe_selected = pyqtSignal(str)        # recipe_id
    create_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)         # recipe_id
    delete_requested = pyqtSignal(str)       # recipe_id
    apply_requested = pyqtSignal(str)        # recipe_id

    def __init__(self, state: DocumentStudioState, parent=None):
        super().__init__(parent)
        self._state = state
        self._init_ui()
        self._connect_signals()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        label = QLabel("Recipes")
        label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header.addWidget(label)
        self._header_label = label

        header.addStretch()

        self._new_btn = QToolButton()
        self._new_btn.setText("+")
        self._new_btn.setToolTip("Create new recipe")
        self._new_btn.clicked.connect(self.create_requested.emit)
        header.addWidget(self._new_btn)

        layout.addLayout(header)

        # Recipe list
        self._list = QListWidget()
        self._list.setMaximumHeight(120)
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(4)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._on_edit)
        actions.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        actions.addWidget(self._delete_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        actions.addWidget(self._apply_btn)

        layout.addLayout(actions)

    def _connect_signals(self):
        self._state.recipe_saved.connect(lambda _: self._refresh_list())
        self._state.recipe_removed.connect(lambda _: self._refresh_list())

    def _refresh_list(self):
        """Rebuild list from state."""
        self._list.clear()
        for rid, recipe in self._state.recipes.items():
            item = QListWidgetItem(f"{recipe.name}")
            item.setData(Qt.ItemDataRole.UserRole, rid)
            item.setToolTip(recipe.description or "No description")
            self._list.addItem(item)

    def _on_row_changed(self, row: int):
        has_selection = row >= 0
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)
        self._apply_btn.setEnabled(has_selection)
        if has_selection:
            item = self._list.item(row)
            recipe_id = item.data(Qt.ItemDataRole.UserRole)
            self._state.active_recipe_id = recipe_id
            self.recipe_selected.emit(recipe_id)

    def _on_edit(self):
        item = self._list.currentItem()
        if item:
            self.edit_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_delete(self):
        item = self._list.currentItem()
        if item:
            self.delete_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_apply(self):
        item = self._list.currentItem()
        if item:
            self.apply_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def apply_theme(self, colors):
        if not THEME_AVAILABLE or not colors:
            return
        self._header_label.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; font-size: 12px; background: transparent;"
        )
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {colors.background_secondary};
                border: 1px solid {colors.border_secondary};
                border-radius: 4px;
                color: {colors.text_primary};
            }}
            QListWidget::item:selected {{
                background: {colors.primary};
                color: {colors.text_primary};
            }}
            QListWidget::item:hover {{
                background: {colors.interactive_hover};
            }}
        """)
        for btn in (self._edit_btn, self._delete_btn, self._apply_btn):
            ButtonStyleManager.apply_unified_button_style(
                btn, colors, "push", "extra_small", "normal"
            )
        ButtonStyleManager.apply_unified_button_style(
            self._new_btn, colors, "tool", "icon", "normal"
        )
```

**Step 3: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/recipe_editor.py \
        specter/src/presentation/widgets/document_studio/recipe_library.py
git commit -m "feat(studio): add RecipeEditor form and RecipeLibrary list widget"
```

---

### Task 9: Wire recipes + batch into the studio panel

**Files:**
- Modify: `specter/src/presentation/widgets/document_studio/studio_panel.py`

**Step 1: Update `studio_panel.py` to integrate recipe library and batch processor**

In `studio_panel.py`, add imports at top:
```python
from .batch_processor import BatchProcessor
from .recipe_editor import RecipeEditor
from .recipe_library import RecipeLibrary
```

Replace the `_create_list_view()` method to include the recipe library between the batch controls and scroll area. Add the recipe editor as view index 3 in the stacked widget. Wire the batch processor signals.

Key changes:
1. Add `self._recipe_library = RecipeLibrary(self._state)` to the list view layout (between toolbar and scroll area)
2. Replace the view[3] placeholder with a real `RecipeEditor`
3. Add `self._batch_processor = BatchProcessor(self._state, self)` in `__init__`
4. Wire `apply_recipe_requested` to call `self._batch_processor.start_batch()`
5. Wire `recipe_library.create_requested` → `navigate_to_recipe_editor()`
6. Wire `recipe_library.edit_requested` → `navigate_to_recipe_editor(recipe)`
7. Wire `recipe_library.delete_requested` → `self._state.remove_recipe()`
8. Wire `recipe_library.apply_requested` → start batch with selected files
9. Load saved recipes from settings on init
10. Save recipes to settings when they change

**Step 2: Test manually**

```bash
python -m specter --debug
```

Test: Open studio → click "+" in recipe library → fill form → save → recipe appears in list. Select files + recipe → click Apply → batch runs with progress.

**Step 3: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/studio_panel.py
git commit -m "feat(studio): integrate RecipeLibrary, RecipeEditor, and BatchProcessor"
```

---

## Phase 3: Preview + Diff

### Task 10: Create DocumentPreviewView

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/preview_view.py`

**Step 1: Write the preview view**

Create `specter/src/presentation/widgets/document_studio/preview_view.py`:
```python
"""
DocumentPreviewView — in-app document preview using python-docx.

Extracts paragraphs and runs from a .docx file and renders as
styled HTML in a QTextBrowser.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("specter.document_studio.preview")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


def docx_to_html(file_path: str) -> str:
    """
    Convert a DOCX file to styled HTML for preview.

    Extracts paragraphs with style info (bold, italic, headings)
    and builds an HTML representation.
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
    except ImportError:
        return "<p><i>python-docx not installed — cannot preview</i></p>"

    if not os.path.exists(file_path):
        return f"<p><i>File not found: {file_path}</i></p>"

    try:
        doc = Document(file_path)
    except Exception as e:
        return f"<p><i>Error opening document: {e}</i></p>"

    html_parts = ['<div style="font-family: Calibri, sans-serif; font-size: 11pt;">']

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""

        # Determine HTML tag from style
        if style_name.startswith("Heading 1"):
            tag = "h1"
        elif style_name.startswith("Heading 2"):
            tag = "h2"
        elif style_name.startswith("Heading 3"):
            tag = "h3"
        elif style_name.startswith("List"):
            tag = "li"
        else:
            tag = "p"

        # Build run HTML with formatting
        run_html = ""
        for run in para.runs:
            text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not text:
                continue

            styles = []
            if run.bold:
                styles.append("font-weight: bold")
            if run.italic:
                styles.append("font-style: italic")
            if run.underline:
                styles.append("text-decoration: underline")
            if run.font.size:
                pt = run.font.size.pt
                styles.append(f"font-size: {pt}pt")
            if run.font.name:
                styles.append(f"font-family: {run.font.name}")
            if run.font.color and run.font.color.rgb:
                rgb = run.font.color.rgb
                styles.append(f"color: #{rgb}")

            if styles:
                style_attr = "; ".join(styles)
                run_html += f'<span style="{style_attr}">{text}</span>'
            else:
                run_html += text

        if not run_html:
            run_html = "&nbsp;"

        html_parts.append(f"<{tag}>{run_html}</{tag}>")

    html_parts.append("</div>")
    return "\n".join(html_parts)


class DocumentPreviewView(QWidget):
    """Preview view for a single document."""

    back_requested = pyqtSignal()
    open_external_requested = pyqtSignal(str)  # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()

        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(self._back_btn)

        self._filename_label = QLabel("")
        self._filename_label.setObjectName("preview_filename")
        toolbar.addWidget(self._filename_label, 1)

        self._open_btn = QToolButton()
        self._open_btn.setText("\u2197")
        self._open_btn.setToolTip("Open in default application")
        self._open_btn.clicked.connect(self._open_external)
        toolbar.addWidget(self._open_btn)

        layout.addLayout(toolbar)

        # Content browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        layout.addWidget(self._browser, 1)

    def load_document(self, file_path: str):
        """Load and display a document."""
        self._current_path = file_path
        filename = os.path.basename(file_path)
        self._filename_label.setText(filename)
        html = docx_to_html(file_path)
        self._browser.setHtml(html)

    def _open_external(self):
        if self._current_path:
            self.open_external_requested.emit(self._current_path)

    def apply_theme(self, colors):
        if not THEME_AVAILABLE or not colors:
            return
        self._browser.setStyleSheet(f"""
            QTextBrowser {{
                background: {colors.background_secondary};
                color: {colors.text_primary};
                border: 1px solid {colors.border_secondary};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self._filename_label.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; background: transparent;"
        )
        ButtonStyleManager.apply_unified_button_style(
            self._back_btn, colors, "push", "small", "normal"
        )
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/preview_view.py
git commit -m "feat(studio): add DocumentPreviewView with docx-to-HTML rendering"
```

---

### Task 11: Create DiffView

**Files:**
- Create: `specter/src/presentation/widgets/document_studio/diff_view.py`

**Step 1: Write the diff view**

Create `specter/src/presentation/widgets/document_studio/diff_view.py`:
```python
"""
DiffView — side-by-side before/after comparison of document formatting.

Uses difflib to compute line-level differences and displays them
in two QTextBrowser panes with highlighted additions/removals.
"""

import difflib
import logging
import os
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .preview_view import docx_to_html

logger = logging.getLogger("specter.document_studio.diff")

try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False


def _extract_text_lines(file_path: str) -> list:
    """Extract plain text lines from a DOCX for diffing."""
    try:
        from docx import Document
        doc = Document(file_path)
        return [para.text for para in doc.paragraphs]
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return [f"[Error reading file: {e}]"]


def _build_diff_html(original_lines: list, formatted_lines: list,
                     add_color: str = "#1a3d1a", remove_color: str = "#3d1a1a",
                     add_bg: str = "#1a3d1a40", remove_bg: str = "#3d1a1a40") -> tuple:
    """
    Build HTML for original and formatted panes with diff highlighting.

    Returns (original_html, formatted_html).
    """
    differ = difflib.SequenceMatcher(None, original_lines, formatted_lines)

    orig_parts = []
    fmt_parts = []

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            for line in original_lines[i1:i2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                orig_parts.append(f"<p>{escaped}</p>")
            for line in formatted_lines[j1:j2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                fmt_parts.append(f"<p>{escaped}</p>")

        elif tag == "replace":
            for line in original_lines[i1:i2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                orig_parts.append(
                    f'<p style="background: {remove_bg}; '
                    f'border-left: 3px solid {remove_color}; padding-left: 6px;">'
                    f'{escaped}</p>'
                )
            for line in formatted_lines[j1:j2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                fmt_parts.append(
                    f'<p style="background: {add_bg}; '
                    f'border-left: 3px solid {add_color}; padding-left: 6px;">'
                    f'{escaped}</p>'
                )

        elif tag == "delete":
            for line in original_lines[i1:i2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                orig_parts.append(
                    f'<p style="background: {remove_bg}; '
                    f'border-left: 3px solid {remove_color}; padding-left: 6px;">'
                    f'{escaped}</p>'
                )

        elif tag == "insert":
            for line in formatted_lines[j1:j2]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;")
                fmt_parts.append(
                    f'<p style="background: {add_bg}; '
                    f'border-left: 3px solid {add_color}; padding-left: 6px;">'
                    f'{escaped}</p>'
                )

    return "\n".join(orig_parts), "\n".join(fmt_parts)


class DiffView(QWidget):
    """Side-by-side diff view for original vs formatted documents."""

    back_requested = pyqtSignal()
    accept_requested = pyqtSignal(str)   # formatted_path
    reject_requested = pyqtSignal(str)   # original_path (restore)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_path: Optional[str] = None
        self._formatted_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()

        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(self._back_btn)

        toolbar.addStretch()

        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setToolTip("Discard formatted version")
        self._reject_btn.clicked.connect(self._on_reject)
        toolbar.addWidget(self._reject_btn)

        self._accept_btn = QPushButton("Accept")
        self._accept_btn.setToolTip("Keep formatted version")
        self._accept_btn.clicked.connect(self._on_accept)
        toolbar.addWidget(self._accept_btn)

        layout.addLayout(toolbar)

        # Labels
        labels = QHBoxLayout()
        self._orig_label = QLabel("Original")
        self._orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        labels.addWidget(self._orig_label)
        self._fmt_label = QLabel("Formatted")
        self._fmt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        labels.addWidget(self._fmt_label)
        layout.addLayout(labels)

        # Side-by-side splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._orig_browser = QTextBrowser()
        self._orig_browser.setOpenExternalLinks(False)
        self._splitter.addWidget(self._orig_browser)

        self._fmt_browser = QTextBrowser()
        self._fmt_browser.setOpenExternalLinks(False)
        self._splitter.addWidget(self._fmt_browser)

        self._splitter.setSizes([1, 1])
        layout.addWidget(self._splitter, 1)

    def load_diff(self, original_path: str, formatted_path: str):
        """Load two documents and display their diff."""
        self._original_path = original_path
        self._formatted_path = formatted_path

        orig_lines = _extract_text_lines(original_path)
        fmt_lines = _extract_text_lines(formatted_path)

        orig_html, fmt_html = _build_diff_html(orig_lines, fmt_lines)

        self._orig_browser.setHtml(f'<div style="font-family: Calibri; font-size: 11pt;">{orig_html}</div>')
        self._fmt_browser.setHtml(f'<div style="font-family: Calibri; font-size: 11pt;">{fmt_html}</div>')

    def _on_accept(self):
        if self._formatted_path:
            self.accept_requested.emit(self._formatted_path)

    def _on_reject(self):
        if self._original_path:
            self.reject_requested.emit(self._original_path)

    def apply_theme(self, colors):
        if not THEME_AVAILABLE or not colors:
            return
        for browser in (self._orig_browser, self._fmt_browser):
            browser.setStyleSheet(f"""
                QTextBrowser {{
                    background: {colors.background_secondary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_secondary};
                    border-radius: 4px;
                    padding: 6px;
                }}
            """)
        for label in (self._orig_label, self._fmt_label):
            label.setStyleSheet(
                f"color: {colors.text_secondary}; font-weight: bold; background: transparent;"
            )
        ButtonStyleManager.apply_unified_button_style(
            self._back_btn, colors, "push", "small", "normal"
        )
        ButtonStyleManager.apply_unified_button_style(
            self._accept_btn, colors, "push", "small", "success"
        )
        ButtonStyleManager.apply_unified_button_style(
            self._reject_btn, colors, "push", "small", "danger"
        )
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/diff_view.py
git commit -m "feat(studio): add DiffView with side-by-side document comparison"
```

---

### Task 12: Wire preview + diff views into studio panel

**Files:**
- Modify: `specter/src/presentation/widgets/document_studio/studio_panel.py`

**Step 1: Replace placeholder views with real ones**

In `studio_panel.py`, add imports:
```python
from .preview_view import DocumentPreviewView
from .diff_view import DiffView
```

In `_init_ui()`, replace the placeholder views (the 3 placeholders in the loop) with:
```python
        # View 1: Document preview
        self._preview_view = DocumentPreviewView()
        self._preview_view.back_requested.connect(self.navigate_to_list)
        self._preview_view.open_external_requested.connect(self._open_file_external)
        self._stack.addWidget(self._preview_view)

        # View 2: Diff view
        self._diff_view = DiffView()
        self._diff_view.back_requested.connect(self.navigate_to_list)
        self._diff_view.accept_requested.connect(self._on_diff_accepted)
        self._diff_view.reject_requested.connect(self._on_diff_rejected)
        self._stack.addWidget(self._diff_view)

        # View 3: Recipe editor
        self._recipe_editor = RecipeEditor()
        self._recipe_editor.recipe_saved.connect(self._on_recipe_saved)
        self._recipe_editor.cancelled.connect(self.navigate_to_list)
        self._stack.addWidget(self._recipe_editor)
```

Update `navigate_to_preview()`:
```python
    def navigate_to_preview(self, file_path: str):
        self._preview_view.load_document(file_path)
        self._stack.setCurrentIndex(VIEW_PREVIEW)
```

Update `navigate_to_diff()`:
```python
    def navigate_to_diff(self, original_path: str, formatted_path: str):
        self._diff_view.load_diff(original_path, formatted_path)
        self._stack.setCurrentIndex(VIEW_DIFF)
```

Add helper methods:
```python
    def _open_file_external(self, file_path: str):
        """Open file in default application."""
        import os, sys, subprocess
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
        except Exception as e:
            logger.error(f"Failed to open file externally: {e}")

    def _on_diff_accepted(self, formatted_path: str):
        logger.info(f"Diff accepted: {formatted_path}")
        self.navigate_to_list()

    def _on_diff_rejected(self, original_path: str):
        logger.info(f"Diff rejected, keeping original: {original_path}")
        self.navigate_to_list()

    def _on_recipe_saved(self, recipe):
        self._state.add_recipe(recipe)
        # Persist to settings
        self._save_recipes_to_settings()
        self.navigate_to_list()

    def _save_recipes_to_settings(self):
        try:
            from specter.src.infrastructure.storage.settings_manager import settings
            recipes_dict = self._state.get_all_recipes_as_dict()
            settings.set("document_studio.recipes", recipes_dict)
        except Exception as e:
            logger.error(f"Failed to save recipes: {e}")

    def _load_recipes_from_settings(self):
        try:
            from specter.src.infrastructure.storage.settings_manager import settings
            recipes_dict = settings.get("document_studio.recipes", {})
            if recipes_dict:
                count = self._state.load_recipes_from_settings(recipes_dict)
                logger.info(f"Loaded {count} recipes from settings")
        except Exception as e:
            logger.error(f"Failed to load recipes: {e}")
```

Call `_load_recipes_from_settings()` at the end of `__init__`.

Update `_apply_theme()` to theme the new views:
```python
        self._preview_view.apply_theme(colors)
        self._diff_view.apply_theme(colors)
        self._recipe_editor.apply_theme(colors)
        if hasattr(self, '_recipe_library'):
            self._recipe_library.apply_theme(colors)
```

Also update `preview_requested_internal` to actually navigate:
```python
    def preview_requested_internal(self, file_path: str):
        entry = self._state.documents.get(file_path)
        if entry and entry.formatted_path and entry.original_path:
            # If formatted, show diff
            self.navigate_to_diff(entry.original_path, entry.formatted_path)
        else:
            # Show preview of current state
            self.navigate_to_preview(file_path)
```

**Step 2: Test manually**

```bash
python -m specter --debug
```

Test: Open studio → drop a .docx file → click card → preview shows rendered document content. After batch formatting, click card → diff view shows before/after.

**Step 3: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/studio_panel.py
git commit -m "feat(studio): wire preview, diff, and recipe editor views into panel"
```

---

## Phase 4: AI Integration + Polish

### Task 13: Add recipe extraction from example documents

**Files:**
- Modify: `specter/src/infrastructure/skills/skills_library/docx_formatter_skill.py`

**Step 1: Add `extract_recipe_from_document()` static method**

After the `cancel_session()` method (~line 1311), add:

```python
    @staticmethod
    def extract_recipe_from_document(file_path: str) -> dict:
        """
        Inspect a DOCX and extract its formatting properties as recipe parameters.

        Returns a dict with keys: operations, parameters (font_name, font_size,
        margin_inches, line_spacing), suitable for Recipe construction.
        """
        try:
            from docx import Document
            from docx.shared import Inches, Pt
        except ImportError:
            return {"operations": [], "parameters": {}, "error": "python-docx not installed"}

        try:
            doc = Document(file_path)
        except Exception as e:
            return {"operations": [], "parameters": {}, "error": str(e)}

        operations = []
        parameters = {}

        # Extract font info from first few body paragraphs
        fonts_seen = {}
        sizes_seen = {}
        for para in doc.paragraphs[:30]:
            if para.style and para.style.name.startswith("Heading"):
                continue
            for run in para.runs:
                if run.font.name:
                    fonts_seen[run.font.name] = fonts_seen.get(run.font.name, 0) + len(run.text)
                if run.font.size:
                    pt = int(run.font.size.pt)
                    sizes_seen[pt] = sizes_seen.get(pt, 0) + len(run.text)

        if fonts_seen:
            most_common_font = max(fonts_seen, key=fonts_seen.get)
            parameters["font_name"] = most_common_font
            operations.append("standardize_fonts")
        if sizes_seen:
            most_common_size = max(sizes_seen, key=sizes_seen.get)
            parameters["font_size"] = most_common_size
            if "standardize_fonts" not in operations:
                operations.append("standardize_fonts")

        # Extract margins
        sections = doc.sections
        if sections:
            sec = sections[0]
            try:
                margin_inches = round(sec.left_margin.inches, 2) if sec.left_margin else 1.0
                parameters["margin_inches"] = margin_inches
                operations.append("fix_margins")
            except Exception:
                pass

        # Extract line spacing
        for para in doc.paragraphs[:10]:
            pf = para.paragraph_format
            if pf.line_spacing:
                try:
                    parameters["line_spacing"] = round(float(pf.line_spacing), 2)
                    operations.append("normalize_spacing")
                except (TypeError, ValueError):
                    pass
                break

        # Check for headings
        has_headings = any(
            p.style and p.style.name.startswith("Heading")
            for p in doc.paragraphs
        )
        if has_headings:
            operations.append("normalize_headings")

        return {
            "operations": operations,
            "parameters": parameters,
        }
```

**Step 2: Commit**

```bash
git add specter/src/infrastructure/skills/skills_library/docx_formatter_skill.py
git commit -m "feat(studio): add recipe extraction from example DOCX documents"
```

---

### Task 14: Add `recipe_name` and `batch_mode` parameters to DocxFormatterSkill

**Files:**
- Modify: `specter/src/infrastructure/skills/skills_library/docx_formatter_skill.py:131-199` (parameters list)
- Modify: `specter/src/infrastructure/skills/skills_library/docx_formatter_skill.py:217+` (execute method)

**Step 1: Add new parameters**

In the `parameters` property, after the last `SkillParameter` (the `alignment` one at ~line 199), add:

```python
            SkillParameter(
                name="recipe_name",
                type=str,
                required=False,
                description="Name of a saved recipe to apply. Overrides individual operations/parameters.",
            ),
            SkillParameter(
                name="extract_recipe",
                type=bool,
                required=False,
                description="If true, extract formatting from this document as a reusable recipe instead of applying changes.",
            ),
```

**Step 2: Update execute() to handle recipe_name**

At the start of `execute()`, after parameter validation, add recipe resolution:

```python
        # Handle recipe extraction mode
        if params.get("extract_recipe", False):
            recipe_data = self.extract_recipe_from_document(str(file_path))
            return SkillResult(
                success=True,
                message=f"Extracted recipe from {file_path.name}",
                data=recipe_data,
                action_taken="extract_recipe",
            )

        # Handle recipe_name — look up from settings
        recipe_name = params.get("recipe_name")
        if recipe_name:
            try:
                from specter.src.infrastructure.storage.settings_manager import settings
                recipes = settings.get("document_studio.recipes", {})
                # Find recipe by name (case-insensitive)
                recipe_data = None
                for rid, rdata in recipes.items():
                    if rdata.get("name", "").lower() == recipe_name.lower():
                        recipe_data = rdata
                        break
                if recipe_data:
                    params["operations"] = recipe_data.get("operations", [])
                    params.update(recipe_data.get("parameters", {}))
                    logger.info(f"Applied recipe '{recipe_name}': {params['operations']}")
                else:
                    return SkillResult(
                        success=False,
                        message=f"Recipe '{recipe_name}' not found",
                        error=f"No recipe named '{recipe_name}' exists. Available recipes: {list(recipes.keys())}",
                    )
            except Exception as e:
                logger.warning(f"Failed to load recipe: {e}")
```

**Step 3: Commit**

```bash
git add specter/src/infrastructure/skills/skills_library/docx_formatter_skill.py
git commit -m "feat(studio): add recipe_name and extract_recipe parameters to DocxFormatterSkill"
```

---

### Task 15: Update `__init__.py` with public exports

**Files:**
- Modify: `specter/src/presentation/widgets/document_studio/__init__.py`

**Step 1: Update exports**

```python
"""Document Studio Panel — visual document workspace for batch formatting."""

from .studio_state import DocumentStudioState, DocumentEntry, DocumentStatus, Recipe
from .studio_panel import DocumentStudioPanel

__all__ = [
    "DocumentStudioState",
    "DocumentEntry",
    "DocumentStatus",
    "Recipe",
    "DocumentStudioPanel",
]
```

**Step 2: Commit**

```bash
git add specter/src/presentation/widgets/document_studio/__init__.py
git commit -m "feat(studio): add public exports to document_studio package"
```

---

### Task 16: Final integration test and verification

**Step 1: Run all tests**

```bash
cd c:/Users/miguel/OneDrive/Documents/Ghostman
python -m pytest specter/tests/test_studio_state.py specter/tests/test_batch_processor.py -v --tb=short
```
Expected: All tests PASS.

**Step 2: Manual end-to-end test**

```bash
python -m specter --debug
```

Verification checklist:
1. **Panel toggle**: Click Studio button (book icon) in toolbar → panel slides open on right. Click header collapse button → panel collapses. Ctrl+Shift+D toggles.
2. **Document cards**: Drag-and-drop 3 DOCX files onto the panel → 3 cards appear with filename, file size. Cards show "Pending" status.
3. **Recipe create**: Click "+" in recipe library → fill: name="Test Recipe", check "Standardize Fonts" + "Fix Margins", font=Calibri, size=11 → Save → recipe appears in list.
4. **Batch format**: Select all 3 files (checkboxes or "Select All"), select recipe in library → click "Apply" → progress bar animates → cards turn green/red.
5. **Preview**: Click a card → preview view shows rendered document text → click Back → returns to list.
6. **Diff**: After formatting, click a completed card → diff view shows original (left) vs formatted (right) with highlighted changes → click Accept or Reject.
7. **Theme**: Change theme in settings → all panel elements restyle (cards, buttons, status bar, progress bars, diff panes).
8. **Persistence**: Close and reopen app → recipes still saved. Panel visibility state persists.
9. **Error recovery**: Include a non-DOCX or corrupted file → card shows red/failed with error message → other files continue processing.

**Step 3: Final commit**

```bash
git add -A
git status
git commit -m "feat(studio): complete Document Studio panel — Phase 1-4 integration"
```

---

## File Inventory

### New Files (11)
| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `document_studio/__init__.py` | Package + exports | 10 |
| `document_studio/studio_state.py` | State management, data models | 180 |
| `document_studio/studio_panel.py` | Main panel widget | 350 |
| `document_studio/studio_header_bar.py` | Header with collapse button | 60 |
| `document_studio/document_card.py` | Visual file card | 200 |
| `document_studio/batch_processor.py` | QThread batch worker | 180 |
| `document_studio/recipe_editor.py` | Recipe creation form | 200 |
| `document_studio/recipe_library.py` | Recipe list + CRUD | 150 |
| `document_studio/preview_view.py` | docx→HTML preview | 160 |
| `document_studio/diff_view.py` | Side-by-side comparison | 200 |
| `tests/test_studio_state.py` | State model tests | 130 |
| `tests/test_batch_processor.py` | Batch processor tests | 50 |

### Modified Files (4)
| File | Change |
|------|--------|
| `floating_repl.py` | QSplitter integration, toggle_studio_panel() |
| `repl_widget.py` | Studio toolbar button, _toggle_studio_panel() |
| `settings_manager.py` | document_studio section in DEFAULT_SETTINGS |
| `style_templates.py` | 4 new style template methods |
| `docx_formatter_skill.py` | extract_recipe_from_document(), recipe_name param |
