"""
RecipeEditor -- form widget for creating and editing formatting recipes.

Provides a scrollable form with name, description, operations checkboxes,
and parameter fields (font, font size, margins).  Emits ``recipe_saved``
with the completed ``Recipe`` dataclass on successful save, or ``cancelled``
when the user navigates back.

Layout:
+-----------------------------------------+
|  <- Back to list                        |
|  New Recipe / Edit Recipe               |
+-----------------------------------------+
|  QScrollArea                            |
|    Name       [____________________]    |
|    Description [____________________]   |
|                                         |
|    Operations                           |
|      [x] Standardize Fonts             |
|      [x] Fix Margins                   |
|      ...                                |
|                                         |
|    Parameters                           |
|      Font Name  [Calibri       v]       |
|      Font Size  [11]                    |
|      Margins    [1.00]                  |
+-----------------------------------------+
|  [Cancel]                    [Save]     |
+-----------------------------------------+
"""

import logging
import uuid
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .studio_state import Recipe

# Theme imports -- graceful fallback when running outside the full app.
try:
    from ...ui.themes.color_system import ColorSystem
    from ...ui.themes.style_templates import ButtonStyleManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

logger = logging.getLogger("specter.document_studio.recipe_editor")

# ---------------------------------------------------------------------------
# Operation labels — maps internal key -> human-readable label
# ---------------------------------------------------------------------------
OPERATION_LABELS: Dict[str, str] = {
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

# Common fonts for the font-name combo box.
_COMMON_FONTS = [
    "Calibri",
    "Arial",
    "Times New Roman",
    "Cambria",
    "Garamond",
    "Verdana",
    "Georgia",
    "Tahoma",
    "Trebuchet MS",
    "Courier New",
    "Consolas",
    "Segoe UI",
]


class RecipeEditor(QFrame):
    """
    A form widget for creating or editing a formatting recipe.

    Signals
    -------
    recipe_saved(object)
        Emitted with the completed ``Recipe`` dataclass when saved.
    cancelled()
        Emitted when the user clicks *Back* or *Cancel*.
    """

    recipe_saved = pyqtSignal(object)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecipeEditor")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # The recipe being edited (None = new recipe).
        self._editing_recipe_id: Optional[str] = None

        self._op_checkboxes: Dict[str, QCheckBox] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the full form layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Back button + title header -----------------------------------
        header = QFrame()
        header.setObjectName("RecipeEditorHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 4)
        header_layout.setSpacing(4)

        self._back_btn = QPushButton("\u2190 Back to list")
        self._back_btn.setObjectName("RecipeEditorBackBtn")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setFlat(True)
        self._back_btn.clicked.connect(self.cancelled.emit)
        header_layout.addWidget(self._back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._title_label = QLabel("New Recipe")
        self._title_label.setObjectName("RecipeEditorTitle")
        header_layout.addWidget(self._title_label)

        root.addWidget(header)

        # --- Scrollable form area -----------------------------------------
        scroll = QScrollArea()
        scroll.setObjectName("RecipeEditorScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        form_container = QWidget()
        form_container.setObjectName("RecipeEditorForm")
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(10, 8, 10, 8)
        form_layout.setSpacing(10)

        # Name field
        name_label = QLabel("Name")
        name_label.setObjectName("RecipeEditorFieldLabel")
        form_layout.addWidget(name_label)

        self._name_edit = QLineEdit()
        self._name_edit.setObjectName("RecipeEditorNameEdit")
        self._name_edit.setPlaceholderText("e.g., Corporate Memo")
        form_layout.addWidget(self._name_edit)

        # Description field
        desc_label = QLabel("Description")
        desc_label.setObjectName("RecipeEditorFieldLabel")
        form_layout.addWidget(desc_label)

        self._desc_edit = QLineEdit()
        self._desc_edit.setObjectName("RecipeEditorDescEdit")
        self._desc_edit.setPlaceholderText("Optional description")
        form_layout.addWidget(self._desc_edit)

        # --- Operations group ---------------------------------------------
        self._ops_group = QGroupBox("Operations")
        ops_group = self._ops_group
        ops_group.setObjectName("RecipeEditorOpsGroup")
        ops_layout = QVBoxLayout(ops_group)
        ops_layout.setContentsMargins(8, 12, 8, 8)
        ops_layout.setSpacing(4)

        for op_key, op_label in OPERATION_LABELS.items():
            cb = QCheckBox(op_label)
            cb.setObjectName(f"RecipeEditorOp_{op_key}")
            self._op_checkboxes[op_key] = cb
            ops_layout.addWidget(cb)

        form_layout.addWidget(ops_group)

        # --- Parameters group ---------------------------------------------
        params_group = QGroupBox("Parameters")
        params_group.setObjectName("RecipeEditorParamsGroup")
        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(8, 12, 8, 8)
        params_layout.setSpacing(8)

        # Font name
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_name_label = QLabel("Font Name")
        font_name_label.setFixedWidth(70)
        font_row.addWidget(font_name_label)

        self._font_combo = QComboBox()
        self._font_combo.setObjectName("RecipeEditorFontCombo")
        self._font_combo.setEditable(True)
        for font in _COMMON_FONTS:
            self._font_combo.addItem(font)
        self._font_combo.setCurrentText("Calibri")
        font_row.addWidget(self._font_combo, 1)
        params_layout.addLayout(font_row)

        # Font size
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        font_size_label = QLabel("Font Size")
        font_size_label.setFixedWidth(70)
        size_row.addWidget(font_size_label)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setObjectName("RecipeEditorFontSizeSpin")
        self._font_size_spin.setRange(6, 72)
        self._font_size_spin.setValue(11)
        self._font_size_spin.setSuffix(" pt")
        size_row.addWidget(self._font_size_spin)
        size_row.addStretch()
        params_layout.addLayout(size_row)

        # Margins
        margin_row = QHBoxLayout()
        margin_row.setSpacing(8)
        margin_label = QLabel("Margins")
        margin_label.setFixedWidth(70)
        margin_row.addWidget(margin_label)

        self._margin_spin = QDoubleSpinBox()
        self._margin_spin.setObjectName("RecipeEditorMarginSpin")
        self._margin_spin.setRange(0.25, 3.0)
        self._margin_spin.setValue(1.0)
        self._margin_spin.setSingleStep(0.25)
        self._margin_spin.setDecimals(2)
        self._margin_spin.setSuffix(" in")
        margin_row.addWidget(self._margin_spin)
        margin_row.addStretch()
        params_layout.addLayout(margin_row)

        form_layout.addWidget(params_group)

        form_layout.addStretch()

        scroll.setWidget(form_container)
        root.addWidget(scroll, 1)  # stretch

        # --- Bottom button bar --------------------------------------------
        btn_bar = QFrame()
        btn_bar.setObjectName("RecipeEditorBtnBar")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(10, 6, 10, 8)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("RecipeEditorCancelBtn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.cancelled.emit)
        btn_layout.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("RecipeEditorSaveBtn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self._save_btn)

        root.addWidget(btn_bar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_recipe(self, recipe: Recipe) -> None:
        """
        Populate the form from an existing ``Recipe`` for editing.

        Parameters
        ----------
        recipe : Recipe
            The recipe to load into the form fields.
        """
        self._editing_recipe_id = recipe.recipe_id
        self._title_label.setText("Edit Recipe")

        self._name_edit.setText(recipe.name)
        self._desc_edit.setText(recipe.description)

        # Check matching operations
        for op_key, cb in self._op_checkboxes.items():
            cb.setChecked(op_key in recipe.operations)

        # Load parameters
        params = recipe.parameters or {}
        if "font_name" in params:
            self._font_combo.setCurrentText(str(params["font_name"]))
        if "font_size" in params:
            try:
                self._font_size_spin.setValue(int(params["font_size"]))
            except (ValueError, TypeError):
                pass
        if "margins" in params:
            try:
                self._margin_spin.setValue(float(params["margins"]))
            except (ValueError, TypeError):
                pass

    def clear_form(self) -> None:
        """Reset the form to its default (new recipe) state."""
        self._editing_recipe_id = None
        self._title_label.setText("New Recipe")
        self._name_edit.clear()
        self._desc_edit.clear()
        for cb in self._op_checkboxes.values():
            cb.setChecked(False)
        self._font_combo.setCurrentText("Calibri")
        self._font_size_spin.setValue(11)
        self._margin_spin.setValue(1.0)

    # ------------------------------------------------------------------
    # Save logic
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Validate the form and emit ``recipe_saved`` with the result."""
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setPlaceholderText("Name is required!")
            logger.warning("Recipe save aborted: name is empty")
            return

        # Gather checked operations
        operations = [
            op_key
            for op_key, cb in self._op_checkboxes.items()
            if cb.isChecked()
        ]
        if not operations:
            self._ops_group.setTitle("Operations — select at least one!")
            logger.warning("Recipe save aborted: no operations selected")
            return
        # Reset title in case it was previously set to error
        self._ops_group.setTitle("Operations")

        # Build parameters dict
        parameters = {
            "font_name": self._font_combo.currentText().strip(),
            "font_size": self._font_size_spin.value(),
            "margins": self._margin_spin.value(),
        }

        # Reuse existing ID for edits, generate new UUID for new recipes.
        recipe_id = self._editing_recipe_id or str(uuid.uuid4())

        recipe = Recipe(
            recipe_id=recipe_id,
            name=name,
            description=self._desc_edit.text().strip(),
            operations=operations,
            parameters=parameters,
        )

        logger.info("Recipe saved: %s (%s)", recipe.name, recipe.recipe_id)
        self.recipe_saved.emit(recipe)

    # ------------------------------------------------------------------
    # Theme support
    # ------------------------------------------------------------------

    def apply_theme(self, colors) -> None:
        """
        Apply theme colours to the editor form.

        Parameters
        ----------
        colors : ColorSystem (or compatible object)
            Provides semantic colour attributes used for styling.
        """
        if not THEME_AVAILABLE or not colors:
            return

        bg_primary = getattr(colors, "background_primary", "#2b2b2b")
        bg_secondary = getattr(colors, "background_secondary", "#333333")
        bg_tertiary = getattr(colors, "background_tertiary", "#3a3a3a")
        text_primary = getattr(colors, "text_primary", "#ffffff")
        text_secondary = getattr(colors, "text_secondary", "#cccccc")
        text_disabled = getattr(colors, "text_disabled", "#888888")
        border_primary = getattr(colors, "border_primary", "#444444")
        border_secondary = getattr(colors, "border_secondary", "#333333")
        primary = getattr(colors, "primary", "#4CAF50")
        interactive_hover = getattr(colors, "interactive_hover", "#5a5a5a")

        # Editor frame
        self.setStyleSheet(f"""
            QFrame#RecipeEditor {{
                background-color: {bg_primary};
                border: none;
            }}
        """)

        # Header
        header = self.findChild(QFrame, "RecipeEditorHeader")
        if header:
            header.setStyleSheet(f"""
                QFrame#RecipeEditorHeader {{
                    background-color: {bg_secondary};
                    border: none;
                    border-bottom: 1px solid {border_secondary};
                }}
            """)

        # Back button
        self._back_btn.setStyleSheet(f"""
            QPushButton#RecipeEditorBackBtn {{
                color: {primary};
                background: transparent;
                border: none;
                font-size: 12px;
                text-align: left;
                padding: 2px 0px;
            }}
            QPushButton#RecipeEditorBackBtn:hover {{
                color: {text_primary};
            }}
        """)

        # Title
        self._title_label.setStyleSheet(
            f"color: {text_primary}; font-weight: bold; font-size: 14px; "
            f"background: transparent; border: none;"
        )

        # Scroll area
        scroll = self.findChild(QScrollArea, "RecipeEditorScroll")
        if scroll:
            scroll.setStyleSheet(f"""
                QScrollArea#RecipeEditorScroll {{
                    background-color: {bg_primary};
                    border: none;
                }}
            """)

        # Form container
        form = self.findChild(QWidget, "RecipeEditorForm")
        if form:
            form.setStyleSheet(f"""
                QWidget#RecipeEditorForm {{
                    background-color: {bg_primary};
                }}
            """)

        # Field labels
        field_label_style = (
            f"color: {text_secondary}; font-size: 12px; "
            f"background: transparent; border: none;"
        )
        for label in self.findChildren(QLabel, "RecipeEditorFieldLabel"):
            label.setStyleSheet(field_label_style)

        # Line edits
        line_edit_style = f"""
            QLineEdit {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {primary};
            }}
            QLineEdit::placeholder {{
                color: {text_disabled};
            }}
        """
        self._name_edit.setStyleSheet(line_edit_style)
        self._desc_edit.setStyleSheet(line_edit_style)

        # Group boxes
        group_style = f"""
            QGroupBox {{
                color: {text_primary};
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {border_secondary};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px 6px;
                color: {text_primary};
            }}
        """
        ops_group = self.findChild(QGroupBox, "RecipeEditorOpsGroup")
        if ops_group:
            ops_group.setStyleSheet(group_style)
        params_group = self.findChild(QGroupBox, "RecipeEditorParamsGroup")
        if params_group:
            params_group.setStyleSheet(group_style)

        # Checkboxes
        checkbox_style = f"""
            QCheckBox {{
                color: {text_primary};
                spacing: 6px;
                font-size: 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {border_secondary};
                border-radius: 3px;
                background-color: {bg_tertiary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {primary};
                border-color: {primary};
            }}
        """
        for cb in self._op_checkboxes.values():
            cb.setStyleSheet(checkbox_style)

        # Parameter labels (inside parameter rows)
        param_label_style = (
            f"color: {text_secondary}; font-size: 12px; font-weight: normal; "
            f"background: transparent; border: none;"
        )
        params_group = self.findChild(QGroupBox, "RecipeEditorParamsGroup")
        if params_group:
            for label in params_group.findChildren(QLabel):
                label.setStyleSheet(param_label_style)

        # Combo box (font name)
        self._font_combo.setStyleSheet(f"""
            QComboBox#RecipeEditorFontCombo {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox#RecipeEditorFontCombo::drop-down {{
                border: none;
            }}
            QComboBox#RecipeEditorFontCombo QAbstractItemView {{
                background-color: {bg_secondary};
                color: {text_primary};
                selection-background-color: {primary};
                border: 1px solid {border_secondary};
            }}
        """)

        # Spin boxes
        spin_style = f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {primary};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {bg_secondary};
                border: 1px solid {border_secondary};
                width: 16px;
            }}
        """
        self._font_size_spin.setStyleSheet(spin_style)
        self._margin_spin.setStyleSheet(spin_style)

        # Bottom button bar
        btn_bar = self.findChild(QFrame, "RecipeEditorBtnBar")
        if btn_bar:
            btn_bar.setStyleSheet(f"""
                QFrame#RecipeEditorBtnBar {{
                    background-color: {bg_secondary};
                    border: none;
                    border-top: 1px solid {border_secondary};
                }}
            """)

        # Cancel button
        self._cancel_btn.setStyleSheet(f"""
            QPushButton#RecipeEditorCancelBtn {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_secondary};
                border-radius: 3px;
                padding: 5px 16px;
                font-size: 12px;
            }}
            QPushButton#RecipeEditorCancelBtn:hover {{
                background-color: {interactive_hover};
            }}
        """)

        # Save button
        self._save_btn.setStyleSheet(f"""
            QPushButton#RecipeEditorSaveBtn {{
                background-color: {primary};
                color: {text_primary};
                border: 1px solid {primary};
                border-radius: 3px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#RecipeEditorSaveBtn:hover {{
                background-color: {interactive_hover};
            }}
        """)
