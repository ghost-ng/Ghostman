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
    ACCEPTED = "accepted"
    REJECTED = "rejected"


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
    builtin: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for settings.json storage."""
        return {
            "name": self.name,
            "description": self.description,
            "operations": list(self.operations),
            "parameters": dict(self.parameters),
            "builtin": self.builtin,
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
            builtin=data.get("builtin", False),
        )


BUILTIN_RECIPES = {
    "builtin_clean_professional": {
        "name": "Clean & Professional",
        "description": "Calibri 11pt, 1in margins, normalized spacing",
        "operations": ["standardize_fonts", "fix_margins", "normalize_spacing"],
        "parameters": {"font_name": "Calibri", "font_size": 11, "margins": 1.0},
    },
    "builtin_apa_format": {
        "name": "APA Format",
        "description": "Times New Roman 12pt, 1in margins, double spacing, 0.5in indent",
        "operations": ["standardize_fonts", "fix_margins", "normalize_spacing", "set_indent"],
        "parameters": {"font_name": "Times New Roman", "font_size": 12, "margins": 1.0, "indentation": 0.5},
    },
    "builtin_mla_format": {
        "name": "MLA Format",
        "description": "Times New Roman 12pt, 1in margins, double spacing",
        "operations": ["standardize_fonts", "fix_margins", "normalize_spacing"],
        "parameters": {"font_name": "Times New Roman", "font_size": 12, "margins": 1.0},
    },
    "builtin_corporate_memo": {
        "name": "Corporate Memo",
        "description": "Calibri 11pt, narrow margins, headings normalized",
        "operations": ["standardize_fonts", "fix_margins", "normalize_headings"],
        "parameters": {"font_name": "Calibri", "font_size": 11, "margins": 0.75},
    },
    "builtin_quick_cleanup": {
        "name": "Quick Cleanup",
        "description": "Fix spelling, case, and bullet formatting",
        "operations": ["fix_spelling", "fix_case", "fix_bullets"],
        "parameters": {},
    },
    "builtin_presentation_ready": {
        "name": "Presentation Ready",
        "description": "Arial 14pt, justified alignment, headings normalized",
        "operations": ["standardize_fonts", "set_alignment", "normalize_headings"],
        "parameters": {"font_name": "Arial", "font_size": 14, "alignment": "justify"},
    },
}


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
        self.output_directory: Optional[str] = None
        self.last_recipe_id: Optional[str] = None

    # -- Document operations --

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

    # -- Selection --

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

    # -- Recipe operations --

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

    def get_failed_paths(self) -> List[str]:
        """Return file paths of all documents with FAILED status."""
        return [
            path for path, entry in self.documents.items()
            if entry.status == DocumentStatus.FAILED
        ]

    def reset_failed_to_pending(self) -> None:
        """Reset all FAILED documents back to PENDING for retry."""
        for path, entry in self.documents.items():
            if entry.status == DocumentStatus.FAILED:
                entry.status = DocumentStatus.PENDING
                entry.error_message = ""
                entry.progress = 0.0
                self.document_status_changed.emit(path, DocumentStatus.PENDING.value)
