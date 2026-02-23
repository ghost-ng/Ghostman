"""
Theme Editor Dialog for Specter Application.

Provides a comprehensive interface for editing themes with:
- Preset theme selector with instant preview
- Individual color pickers for each theme variable
- Undo buttons for each color
- Custom theme saving
- Immediate live updates
"""

import logging
from typing import Dict, Optional, Any, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QComboBox, QColorDialog,
    QFrame, QScrollArea, QMessageBox, QLineEdit, QCheckBox,
    QGroupBox, QFileDialog, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPalette

from ...ui.themes.theme_manager import get_theme_manager
from ...ui.themes.color_system import ColorSystem
from ...ui.themes.style_templates import StyleTemplates

logger = logging.getLogger("specter.theme_editor")


class ColorPickerWidget(QWidget):
    """Enhanced color picker widget with improved UX and accessibility."""
    
    color_changed = pyqtSignal(str, str)  # color_name, new_color
    
    def __init__(self, color_name: str, color_value: str, display_name: str = None, description: str = None):
        super().__init__()
        self.color_name = color_name
        self.original_color = color_value
        self.current_color = color_value
        self.display_name = display_name or self._get_user_friendly_name(color_name)
        self.description = description or self._get_color_description(color_name)
        
        self._init_ui()
        self._update_color_display()
    
    def _get_user_friendly_name(self, color_name: str) -> str:
        """Convert technical color names to user-friendly names."""
        name_map = {
            'primary': 'Primary Brand',
            'primary_hover': 'Primary Hover',
            'secondary': 'Secondary Brand',
            'secondary_hover': 'Secondary Hover',
            'background_primary': 'Main Background',
            'background_secondary': 'REPL Panel Background',
            'background_tertiary': 'Card Background',
            'background_overlay': 'Modal Overlay',
            'text_primary': 'Main Text',
            'text_secondary': 'Secondary Text',
            'text_tertiary': 'Muted Text',
            'text_disabled': 'Disabled Text',
            'interactive_normal': 'Button Default',
            'interactive_hover': 'Button Hover',
            'interactive_active': 'Button Active',
            'interactive_disabled': 'Button Disabled',
            'status_success': 'Success',
            'status_warning': 'Warning',
            'status_error': 'Error',
            'status_info': 'Information',
            'border_primary': 'Main Borders',
            'border_secondary': 'Subtle Borders',
            'border_focus': 'Focus Outline',
            'separator': 'Divider Lines',
        }
        return name_map.get(color_name, color_name.replace('_', ' ').title())
    
    def _get_color_description(self, color_name: str) -> str:
        """Get helpful description for color usage."""
        descriptions = {
            'primary': 'Main brand color for buttons and highlights',
            'primary_hover': 'Darker shade when hovering over primary elements',
            'secondary': 'Secondary accent color for variety',
            'secondary_hover': 'Darker shade for secondary hover states',
            'background_primary': 'Main window background color',
            'background_secondary': 'Background for the REPL chat panel and sidebars',
            'background_tertiary': 'Background for cards and elevated elements',
            'background_overlay': 'Semi-transparent overlay for modals',
            'text_primary': 'Main text color for headings and content',
            'text_secondary': 'Lighter text for descriptions and labels',
            'text_tertiary': 'Very light text for hints and placeholders',
            'text_disabled': 'Text color for disabled elements',
            'interactive_normal': 'Default state for clickable elements',
            'interactive_hover': 'Hover state for interactive elements',
            'interactive_active': 'Pressed/active state for interactions',
            'interactive_disabled': 'Disabled state for interactions',
            'status_success': 'Color for success messages and positive states',
            'status_warning': 'Color for warnings and caution states',
            'status_error': 'Color for errors and destructive actions',
            'status_info': 'Color for informational messages',
            'border_primary': 'Main border color for panels and inputs',
            'border_secondary': 'Subtle borders for less important elements',
            'border_focus': 'Border color when elements are focused',
            'separator': 'Color for divider lines and separators',
        }
        return descriptions.get(color_name, 'Customize this color for your theme')
    
    def _init_ui(self):
        """Initialize the enhanced UI components with better accessibility."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)
        
        # Top row: name and controls
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        # Color name label with improved typography
        self.name_label = QLabel(self.display_name)
        self.name_label.setMinimumWidth(140)
        self.name_label.setStyleSheet("""
            QLabel {
                font-weight: 500;
                font-size: 13px;
                color: #ffffff;
            }
        """)
        top_layout.addWidget(self.name_label)
        
        # Color preview button (larger and more accessible)
        self.color_button = QPushButton()
        self.color_button.setMinimumSize(50, 32)
        self.color_button.setMaximumSize(50, 32)
        self.color_button.clicked.connect(self._open_color_picker)
        self.color_button.setToolTip(f"Click to change {self.display_name.lower()}")
        self.color_button.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self.color_button)
        
        # Color value label with better formatting
        self.value_label = QLabel(self.current_color)
        self.value_label.setMinimumWidth(75)
        self.value_label.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                color: #aaaaaa;
                background-color: #333333;
                padding: 2px 6px;
                border-radius: 3px;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.value_label)
        
        # Undo button with better visual design
        self.undo_button = QPushButton("⟲")
        self.undo_button.setMinimumSize(28, 28)
        self.undo_button.setMaximumSize(28, 28)
        self.undo_button.setToolTip(f"Reset {self.display_name.lower()} to original color")
        self.undo_button.clicked.connect(self._undo_color)
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: 1px solid #606060;
                border-radius: 14px;
                color: #cccccc;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #707070;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                border-color: #404040;
                color: #666666;
            }
        """)
        top_layout.addWidget(self.undo_button)
        
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        
        # Description label for context
        self.description_label = QLabel(self.description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                line-height: 1.3;
                margin-top: 2px;
            }
        """)
        main_layout.addWidget(self.description_label)
        
        self.setLayout(main_layout)
        
        # Add hover effects
        self.setStyleSheet("""
            ColorPickerWidget {
                background-color: transparent;
                border-radius: 6px;
            }
            ColorPickerWidget:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
    
    def _update_color_display(self):
        """Update the color preview with enhanced visual feedback."""
        color = QColor(self.current_color)
        if color.isValid():
            # Calculate luminance for contrast
            luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
            border_color = "#ffffff" if luminance < 0.5 else "#000000"
            
            # Enhanced button styling with accessibility considerations
            self.color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.current_color};
                    border: 2px solid {border_color};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border: 3px solid #4CAF50;
                    margin: -1px;
                }}
                QPushButton:focus {{
                    border: 3px solid #2196F3;
                    margin: -1px;
                    outline: none;
                }}
            """)
            
            self.value_label.setText(self.current_color.upper())
            
            # Visual indication of changes
            has_changed = self.current_color != self.original_color
            self.undo_button.setEnabled(has_changed)
            
            # Add visual change indicator
            if has_changed:
                self.name_label.setStyleSheet("""
                    QLabel {
                        font-weight: 600;
                        font-size: 13px;
                        color: #4CAF50;
                    }
                """)
            else:
                self.name_label.setStyleSheet("""
                    QLabel {
                        font-weight: 500;
                        font-size: 13px;
                        color: #ffffff;
                    }
                """)
    
    def _open_color_picker(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(self.current_color),
            self,
            f"Choose {self.display_name}"
        )
        
        if color.isValid():
            self.set_color(color.name())
    
    def _undo_color(self):
        """Restore original color."""
        self.set_color(self.original_color)
    
    def set_color(self, color: str):
        """Set the color value."""
        if color != self.current_color:
            self.current_color = color
            self._update_color_display()
            self.color_changed.emit(self.color_name, color)
    
    def get_color(self) -> str:
        """Get current color value."""
        return self.current_color
    
    def reset_to_original(self):
        """Reset to original color without emitting signal."""
        self.current_color = self.original_color
        self._update_color_display()


class ThemePreviewWidget(QWidget):
    """Widget showing a preview of the current theme."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.setMinimumHeight(200)
    
    def _init_ui(self):
        """Initialize preview UI."""
        layout = QVBoxLayout()
        
        # Preview label
        preview_label = QLabel("Theme Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(preview_label)
        
        # Sample UI elements
        sample_frame = QFrame()
        sample_layout = QVBoxLayout()
        
        # Sample button
        self.sample_button = QPushButton("Sample Button")
        sample_layout.addWidget(self.sample_button)
        
        # Sample input
        self.sample_input = QLineEdit("Sample text input")
        sample_layout.addWidget(self.sample_input)
        
        # Sample combo box
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["Option 1", "Option 2", "Option 3"])
        sample_layout.addWidget(self.sample_combo)
        
        # Sample labels
        self.sample_label_primary = QLabel("Primary text")
        self.sample_label_secondary = QLabel("Secondary text")
        self.sample_label_tertiary = QLabel("Tertiary text")
        
        sample_layout.addWidget(self.sample_label_primary)
        sample_layout.addWidget(self.sample_label_secondary)
        sample_layout.addWidget(self.sample_label_tertiary)
        
        sample_frame.setLayout(sample_layout)
        layout.addWidget(sample_frame)
        
        self.setLayout(layout)
    
    def update_theme_preview(self, color_system: ColorSystem):
        """Update preview with new theme."""
        try:
            # Apply styles to sample elements
            button_style = StyleTemplates.get_button_primary_style(color_system)
            self.sample_button.setStyleSheet(button_style)
            
            input_style = StyleTemplates.get_input_field_style(color_system)
            self.sample_input.setStyleSheet(input_style)
            
            combo_style = StyleTemplates.get_combo_box_style(color_system)
            self.sample_combo.setStyleSheet(combo_style)
            
            # Apply label styles
            self.sample_label_primary.setStyleSheet(
                StyleTemplates.get_label_style(color_system, "primary")
            )
            self.sample_label_secondary.setStyleSheet(
                StyleTemplates.get_label_style(color_system, "secondary")
            )
            self.sample_label_tertiary.setStyleSheet(
                StyleTemplates.get_label_style(color_system, "tertiary")
            )
            
            # Update background
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {color_system.background_secondary};
                    border: 1px solid {color_system.border_primary};
                    border-radius: 4px;
                }}
            """)
            
        except Exception as e:
            logger.error(f"Failed to update theme preview: {e}")


class ThemeEditorDialog(QDialog):
    """
    Comprehensive theme editor dialog.
    
    Features:
    - Preset theme selection with instant preview
    - Individual color pickers for all 24 theme variables
    - Live theme updates
    - Custom theme saving
    - Import/export functionality
    """
    
    theme_applied = pyqtSignal(ColorSystem)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.current_theme = ColorSystem()
        self.color_pickers: Dict[str, ColorPickerWidget] = {}
        self.live_updates_enabled = True
        
        # Debounce timer for live updates
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._apply_theme_updates)
        
        self._init_ui()
        self._load_current_theme()
        self._connect_signals()
        
        logger.info("ThemeEditorDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Theme Editor (Not Yet Implemented)")
        self.setModal(True)
        self.resize(900, 700)
        
        # Main layout with stacked widget for overlay
        main_layout = QVBoxLayout()
        
        # Create a container widget for the actual content
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - controls
        controls_widget = self._create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Right panel - preview
        preview_widget = self._create_preview_panel()
        splitter.addWidget(preview_widget)
        
        # Set splitter ratios
        splitter.setStretchFactor(0, 2)  # Controls take 2/3
        splitter.setStretchFactor(1, 1)  # Preview takes 1/3
        
        content_layout.addWidget(splitter)
        
        # Button bar
        button_layout = self._create_button_bar()
        content_layout.addLayout(button_layout)
        
        content_widget.setLayout(content_layout)
        
        # Create overlay widget with "Not Yet Implemented" message
        overlay_widget = QWidget()
        overlay_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                background-color: rgba(255, 140, 0, 200);
                border-radius: 10px;
            }
        """)
        overlay_layout = QVBoxLayout()
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        overlay_label = QLabel("🚧 Theme Editor Not Yet Implemented 🚧\n\nThis feature is coming soon!")
        overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(overlay_label)
        
        overlay_widget.setLayout(overlay_layout)
        
        # Stack the widgets
        from PyQt6.QtWidgets import QStackedLayout
        stacked_layout = QStackedLayout()
        stacked_layout.addWidget(content_widget)
        stacked_layout.addWidget(overlay_widget)
        stacked_layout.setCurrentIndex(1)  # Show overlay on top
        
        main_layout.addLayout(stacked_layout)
        self.setLayout(main_layout)
    
    def _create_controls_panel(self) -> QWidget:
        """Create the controls panel."""
        controls_widget = QWidget()
        layout = QVBoxLayout()
        
        # Preset theme selector
        preset_group = QGroupBox("Preset Themes")
        preset_layout = QVBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.theme_manager.get_available_themes())
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Color editor tabs
        self.tab_widget = QTabWidget()
        self._create_color_editor_tabs()
        layout.addWidget(self.tab_widget)
        
        # Live updates checkbox
        self.live_updates_checkbox = QCheckBox("Live Updates")
        self.live_updates_checkbox.setChecked(True)
        self.live_updates_checkbox.toggled.connect(self._on_live_updates_toggled)
        layout.addWidget(self.live_updates_checkbox)
        
        controls_widget.setLayout(layout)
        return controls_widget
    
    def _create_preview_panel(self) -> QWidget:
        """Create an enhanced preview panel with better user guidance."""
        preview_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Preview section with header
        preview_header = QLabel("Live Preview")
        preview_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(preview_header)
        
        # Enhanced preview widget
        self.preview_widget = ThemePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # Quick actions section
        actions_group = QGroupBox("Quick Actions")
        actions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: #2b2b2b;
            }
        """)
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        # Preset variations button
        variations_btn = QPushButton("🎨 Generate Variations")
        variations_btn.setToolTip("Create automatic color variations of the current theme")
        variations_btn.clicked.connect(self._generate_theme_variations)
        variations_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        actions_layout.addWidget(variations_btn)
        
        # Reset all button
        reset_btn = QPushButton("🔄 Reset All Colors")
        reset_btn.setToolTip("Reset all colors to the selected preset theme")
        reset_btn.clicked.connect(self._reset_all_colors)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        actions_layout.addWidget(reset_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Theme validation with better visuals
        validation_group = QGroupBox("Theme Status")
        validation_group.setStyleSheet(actions_group.styleSheet())
        validation_layout = QVBoxLayout()
        
        self.validation_label = QLabel("⚙️ Validating theme...")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        validation_layout.addWidget(self.validation_label)
        
        # Accessibility report button
        accessibility_btn = QPushButton("📋 Accessibility Report")
        accessibility_btn.setToolTip("View detailed accessibility analysis")
        accessibility_btn.clicked.connect(self._show_accessibility_report)
        accessibility_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 11px;
                margin-top: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        validation_layout.addWidget(accessibility_btn)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Enhanced theme saving
        save_group = QGroupBox("Save Custom Theme")
        save_group.setStyleSheet(actions_group.styleSheet())
        save_layout = QVBoxLayout()
        save_layout.setSpacing(8)
        
        # Theme name input with better styling
        self.theme_name_input = QLineEdit()
        self.theme_name_input.setPlaceholderText("🎨 My Custom Theme")
        self.theme_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #444444;
                border-radius: 6px;
                background-color: #3a3a3a;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
        """)
        save_layout.addWidget(self.theme_name_input)
        
        # Save button with icon
        self.save_theme_button = QPushButton("💾 Save Theme")
        self.save_theme_button.clicked.connect(self._save_custom_theme)
        self.save_theme_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        save_layout.addWidget(self.save_theme_button)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        layout.addStretch()
        preview_widget.setLayout(layout)
        return preview_widget
    
    def _generate_theme_variations(self):
        """Generate automatic theme variations."""
        # This would create lighter/darker variations of the current theme
        QMessageBox.information(
            self,
            "Theme Variations",
            "This feature will generate lighter and darker variations of your current theme. Coming soon!"
        )
    
    def _create_color_editor_tabs(self):
        """Create organized tabs for intuitive color editing."""
        # Reorganized color groups with user-focused organization
        color_groups = {
            "Essential Colors": {
                "description": "The most important colors that define your theme's personality",
                "colors": [
                    ("primary", "Primary Brand", "Your main brand color for buttons and highlights"),
                    ("secondary", "Secondary Brand", "Accent color for variety and contrast"),
                    ("background_primary", "Main Background", "The primary background color of your application"),
                    ("background_secondary", "REPL Panel Background", "Background for the REPL chat panel and sidebars"),
                    ("text_primary", "Main Text", "Primary text color for headings and content")
                ]
            },
            "Backgrounds & Surfaces": {
                "description": "Different background shades that create depth and hierarchy",
                "colors": [
                    ("background_tertiary", "Card Background", "Background for cards and elevated elements"),
                    ("background_overlay", "Modal Overlay", "Semi-transparent overlay for dialogs")
                ]
            },
            "Text & Content": {
                "description": "Text colors for different levels of information hierarchy",
                "colors": [
                    ("text_secondary", "Secondary Text", "For descriptions and supporting text"),
                    ("text_tertiary", "Muted Text", "For hints, placeholders, and less important text"),
                    ("text_disabled", "Disabled Text", "For inactive or disabled text elements")
                ]
            },
            "Interactive States": {
                "description": "Colors for buttons and interactive elements in different states",
                "colors": [
                    ("primary_hover", "Brand Hover", "Darker shade when hovering over brand elements"),
                    ("secondary_hover", "Accent Hover", "Darker shade for secondary hover states"),
                    ("interactive_normal", "Button Default", "Default state for interactive elements"),
                    ("interactive_hover", "Button Hover", "Hover state for interactive elements"),
                    ("interactive_active", "Button Active", "Pressed/active state for interactions"),
                    ("interactive_disabled", "Button Disabled", "Disabled state for interactions")
                ]
            },
            "Status & Feedback": {
                "description": "Colors that communicate different types of messages and states",
                "colors": [
                    ("status_success", "Success", "For positive feedback and successful actions"),
                    ("status_warning", "Warning", "For warnings and actions requiring caution"),
                    ("status_error", "Error", "For errors and destructive actions"),
                    ("status_info", "Information", "For neutral informational messages")
                ]
            },
            "Borders & Structure": {
                "description": "Subtle colors that define structure and focus states",
                "colors": [
                    ("border_primary", "Main Borders", "Primary border color for panels and inputs"),
                    ("border_secondary", "Subtle Borders", "Secondary borders for less important elements"),
                    ("border_focus", "Focus Outline", "Border color when elements receive focus"),
                    ("separator", "Divider Lines", "Color for dividers and separators")
                ]
            }
        }
        
        for group_name, group_data in color_groups.items():
            tab = self._create_enhanced_color_tab(group_data["colors"], group_data["description"])
            self.tab_widget.addTab(tab, group_name)
    
    def _create_enhanced_color_tab(self, colors, description: str) -> QWidget:
        """Create an enhanced tab with better organization and guidance."""
        tab_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Category description
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: #cccccc;
                    font-size: 12px;
                    font-style: italic;
                    padding: 8px 12px;
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                    border-left: 3px solid #4CAF50;
                }
            """)
            main_layout.addWidget(desc_label)
        
        # Colors container with improved spacing
        colors_widget = QWidget()
        colors_layout = QVBoxLayout()
        colors_layout.setSpacing(8)
        colors_layout.setContentsMargins(0, 8, 0, 0)
        
        for i, (color_name, display_name, color_description) in enumerate(colors):
            color_picker = ColorPickerWidget(color_name, "#000000", display_name, color_description)
            color_picker.color_changed.connect(self._on_color_changed)
            self.color_pickers[color_name] = color_picker
            
            # Add subtle separator between items (except last)
            if i > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.1);
                        max-height: 1px;
                        margin: 4px 0px;
                    }
                """)
                colors_layout.addWidget(separator)
            
            colors_layout.addWidget(color_picker)
        
        colors_widget.setLayout(colors_layout)
        
        # Scroll area with better styling
        scroll = QScrollArea()
        scroll.setWidget(colors_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        main_layout.addWidget(scroll)
        tab_widget.setLayout(main_layout)
        
        return tab_widget
    
    def _create_color_tab(self, colors) -> QWidget:
        """Legacy method for backward compatibility."""
        # Convert old format to new format
        enhanced_colors = [(name, display, "") for name, display in colors]
        return self._create_enhanced_color_tab(enhanced_colors, "")
    
    def _create_button_bar(self) -> QHBoxLayout:
        """Create an enhanced button bar with better organization."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 16)
        
        # File operations group
        file_group = QWidget()
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        file_layout.setContentsMargins(0, 0, 0, 0)
        
        # Import button with icon
        import_button = QPushButton("📁 Import Theme")
        import_button.clicked.connect(self._import_theme)
        import_button.setToolTip("Import a theme from a JSON file")
        import_button.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        file_layout.addWidget(import_button)
        
        # Export button with icon
        export_button = QPushButton("💾 Export Theme")
        export_button.clicked.connect(self._export_theme)
        export_button.setToolTip("Export current theme to a JSON file")
        export_button.setStyleSheet(import_button.styleSheet())
        file_layout.addWidget(export_button)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        layout.addStretch()
        
        # Main action buttons
        # Apply button - primary action
        apply_button = QPushButton("✓ Apply Theme")
        apply_button.clicked.connect(self._apply_theme)
        apply_button.setDefault(True)
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        layout.addWidget(apply_button)
        
        # Cancel button - secondary action
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        layout.addWidget(cancel_button)
        
        return layout
    
    def _connect_signals(self):
        """Connect theme manager signals."""
        self.theme_manager.theme_validation_failed.connect(self._on_validation_failed)
    
    def _load_current_theme(self):
        """Load the current theme into the editor."""
        self.current_theme = self.theme_manager.current_theme
        
        # Update preset selector
        current_name = self.theme_manager.current_theme_name
        index = self.preset_combo.findText(current_name)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        
        # Update color pickers
        theme_dict = self.current_theme.to_dict()
        for color_name, color_picker in self.color_pickers.items():
            if color_name in theme_dict:
                color_picker.set_color(theme_dict[color_name])
                color_picker.original_color = theme_dict[color_name]
        
        # Update preview
        self._update_preview()
        self._validate_theme()
    
    def _on_preset_selected(self, theme_name: str):
        """Handle preset theme selection."""
        if not theme_name:
            return
        
        theme = self.theme_manager.get_theme(theme_name)
        if theme:
            self.current_theme = theme
            
            # Update color pickers
            theme_dict = theme.to_dict()
            for color_name, color_picker in self.color_pickers.items():
                if color_name in theme_dict:
                    color_picker.set_color(theme_dict[color_name])
            
            self._update_preview()
            self._validate_theme()
    
    def _on_color_changed(self, color_name: str, new_color: str):
        """Handle individual color changes."""
        # Update current theme
        setattr(self.current_theme, color_name, new_color)
        
        # Schedule live update
        if self.live_updates_enabled:
            self.update_timer.start(100)  # 100ms debounce
        
        self._update_preview()
        self._validate_theme()
    
    def _on_live_updates_toggled(self, enabled: bool):
        """Handle live updates toggle."""
        self.live_updates_enabled = enabled
        if enabled:
            self._apply_theme_updates()
    
    def _apply_theme_updates(self):
        """Apply theme updates to the application."""
        if self.live_updates_enabled:
            self.theme_applied.emit(self.current_theme)
    
    def _update_preview(self):
        """Update the theme preview."""
        self.preview_widget.update_theme_preview(self.current_theme)
    
    def _validate_theme(self):
        """Validate the current theme with enhanced visual feedback."""
        is_valid, issues = self.current_theme.validate()
        
        if is_valid:
            self.validation_label.setText("✓ Theme looks great! All accessibility checks passed.")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    border-radius: 4px;
                    background-color: rgba(76, 175, 80, 0.2);
                    color: #4CAF50;
                    border: 1px solid rgba(76, 175, 80, 0.3);
                }
            """)
        else:
            self.validation_label.setText(f"⚠ {len(issues)} accessibility issue{'s' if len(issues) != 1 else ''} found")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    border-radius: 4px;
                    background-color: rgba(255, 152, 0, 0.2);
                    color: #FF9800;
                    border: 1px solid rgba(255, 152, 0, 0.3);
                }
            """)
            
            # Create a more user-friendly tooltip
            tooltip_text = "Accessibility Issues:\n\n" + "\n• ".join(issues)
            tooltip_text += "\n\nThese issues may affect users with visual impairments."
            self.validation_label.setToolTip(tooltip_text)
    
    def _on_validation_failed(self, issues):
        """Handle validation failure."""
        QMessageBox.warning(
            self,
            "Theme Validation Failed",
            f"Theme has validation issues:\n\n" + "\n".join(issues)
        )
    
    def _save_custom_theme(self):
        """Save current theme as custom theme."""
        name = self.theme_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a theme name.")
            return
        
        if self.theme_manager.save_custom_theme(name, self.current_theme):
            QMessageBox.information(self, "Theme Saved", f"Theme '{name}' saved successfully.")
            self.theme_name_input.clear()
            
            # Refresh preset combo
            self.preset_combo.clear()
            self.preset_combo.addItems(self.theme_manager.get_available_themes())
        else:
            QMessageBox.warning(self, "Save Failed", f"Failed to save theme '{name}'.")
    
    def _import_theme(self):
        """Import theme from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Theme",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self.theme_manager.import_theme(file_path):
                QMessageBox.information(self, "Import Successful", "Theme imported successfully.")
                
                # Refresh preset combo
                self.preset_combo.clear()
                self.preset_combo.addItems(self.theme_manager.get_available_themes())
            else:
                QMessageBox.warning(self, "Import Failed", "Failed to import theme.")
    
    def _export_theme(self):
        """Export current theme to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Theme",
            "custom_theme.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            # Create temporary theme name for export
            theme_name = self.theme_name_input.text().strip() or "exported_theme"
            
            # Save current theme temporarily
            temp_saved = self.theme_manager.save_custom_theme(f"_temp_{theme_name}", self.current_theme)
            
            if temp_saved and self.theme_manager.export_theme(f"_temp_{theme_name}", file_path):
                QMessageBox.information(self, "Export Successful", "Theme exported successfully.")
                
                # Clean up temporary theme
                self.theme_manager.delete_custom_theme(f"_temp_{theme_name}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export theme.")
    
    def _reset_all_colors(self):
        """Reset all colors to their original values."""
        reply = QMessageBox.question(
            self,
            "Reset All Colors",
            "Are you sure you want to reset all colors to their original values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for color_picker in self.color_pickers.values():
                color_picker.reset_to_original()
            
            # Reload current theme
            self._load_current_theme()
    
    def _apply_theme(self):
        """Apply the current theme and close dialog."""
        self.theme_applied.emit(self.current_theme)
        self.accept()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop any pending updates
        self.update_timer.stop()
        super().closeEvent(event)
    
    def _show_accessibility_report(self):
        """Show detailed accessibility analysis report."""
        is_valid, issues = self.current_theme.validate()
        
        # Calculate additional accessibility metrics
        contrast_ratios = self._calculate_all_contrast_ratios()
        color_blindness_analysis = self._analyze_color_blindness_accessibility()
        
        report_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ color: #4CAF50; font-size: 18px; font-weight: bold; margin-bottom: 15px; }}
                .section {{ margin-bottom: 20px; }}
                .section-title {{ font-weight: bold; font-size: 14px; margin-bottom: 8px; color: #2196F3; }}
                .good {{ color: #4CAF50; }}
                .warning {{ color: #FF9800; }}
                .error {{ color: #F44336; }}
                .info {{ color: #2196F3; }}
                .metric {{ margin: 5px 0; padding: 5px; background-color: #f5f5f5; border-radius: 3px; }}
                ul {{ margin: 5px 0; padding-left: 20px; }}
                li {{ margin: 2px 0; }}
            </style>
        </head>
        <body>
            <div class="header">🔍 Theme Accessibility Report</div>
            
            <div class="section">
                <div class="section-title">Overall Assessment</div>
                <div class="metric">
                    <strong>Status:</strong> 
                    <span class="{'good' if is_valid else 'warning'}">
                        {'✓ Passes accessibility checks' if is_valid else f'⚠ {len(issues)} issue(s) found'}
                    </span>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Contrast Ratios (WCAG 2.1)</div>
                <div style="font-size: 12px; margin-bottom: 8px;">
                    <strong>Standards:</strong> AA (4.5+) | AAA (7.0+)
                </div>
                {self._format_contrast_ratios_html(contrast_ratios)}
            </div>
            
            <div class="section">
                <div class="section-title">Color Differentiation</div>
                {color_blindness_analysis}
            </div>
            
            {f'<div class="section"><div class="section-title">Issues Found</div><ul>{"".join([f"<li class=\"warning\">{issue}</li>" for issue in issues])}</ul></div>' if issues else ''}
            
            <div class="section">
                <div class="section-title">Recommendations</div>
                <ul>
                    <li>Ensure all text has sufficient contrast (4.5+ for AA, 7.0+ for AAA)</li>
                    <li>Use patterns or icons in addition to color for status communication</li>
                    <li>Test your theme with color blindness simulators</li>
                    <li>Consider users with low vision or light sensitivity</li>
                    <li>Maintain consistent color usage throughout the application</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Create and show the report dialog
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("Accessibility Report")
        report_dialog.setModal(True)
        report_dialog.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # HTML display
        from PyQt6.QtWidgets import QTextBrowser
        browser = QTextBrowser()
        browser.setHtml(report_html)
        layout.addWidget(browser)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(report_dialog.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(close_btn)
        
        report_dialog.setLayout(layout)
        report_dialog.exec()
    
    def _calculate_all_contrast_ratios(self):
        """Calculate contrast ratios for all relevant color combinations."""
        ratios = {}
        text_colors = ['text_primary', 'text_secondary', 'text_tertiary']
        bg_colors = ['background_primary', 'background_secondary', 'background_tertiary']
        status_colors = ['status_success', 'status_warning', 'status_error', 'status_info']
        
        # Text on backgrounds
        for text in text_colors:
            for bg in bg_colors:
                ratio = self.current_theme._calculate_contrast_ratio(
                    self.current_theme.get_color(text),
                    self.current_theme.get_color(bg)
                )
                ratios[f"{text}_on_{bg}"] = ratio
        
        # Status colors on backgrounds
        for status in status_colors:
            for bg in bg_colors:
                ratio = self.current_theme._calculate_contrast_ratio(
                    self.current_theme.get_color(status),
                    self.current_theme.get_color(bg)
                )
                ratios[f"{status}_on_{bg}"] = ratio
        
        return ratios
    
    def _format_contrast_ratios_html(self, ratios):
        """Format contrast ratios for HTML display."""
        html = ""
        for combo, ratio in ratios.items():
            # Determine status
            if ratio >= 7.0:
                status_class = "good"
                status_text = "AAA ✓"
            elif ratio >= 4.5:
                status_class = "info"
                status_text = "AA ✓"
            else:
                status_class = "error"
                status_text = "Fails ✗"
            
            # Clean up the combination name
            clean_name = combo.replace('_on_', ' on ').replace('_', ' ').title()
            
            html += f'<div class="metric"><strong>{clean_name}:</strong> <span class="{status_class}">{ratio:.2f} ({status_text})</span></div>'
        
        return html
    
    def _analyze_color_blindness_accessibility(self):
        """Analyze theme for color blindness accessibility."""
        # Check if status colors are distinguishable
        status_colors = [
            self.current_theme.status_success,
            self.current_theme.status_warning,
            self.current_theme.status_error,
            self.current_theme.status_info
        ]
        
        analysis = "<div class=\"metric\">"
        
        # Check for common problematic combinations
        red = QColor(self.current_theme.status_error)
        green = QColor(self.current_theme.status_success)
        
        # Simple hue difference check (not perfect but helpful)
        red_hue = red.hue()
        green_hue = green.hue()
        hue_diff = abs(red_hue - green_hue)
        
        if hue_diff < 60 or hue_diff > 300:  # Colors might be confusing
            analysis += "<span class=\"warning\">⚠ Success and error colors may be difficult to distinguish for color-blind users</span><br>"
        else:
            analysis += "<span class=\"good\">✓ Success and error colors appear distinguishable</span><br>"
        
        # Check if all status colors are unique
        unique_colors = len(set(status_colors))
        if unique_colors == 4:
            analysis += "<span class=\"good\">✓ All status colors are unique</span>"
        else:
            analysis += f"<span class=\"warning\">⚠ Only {unique_colors}/4 status colors are unique</span>"
        
        analysis += "</div>"
        return analysis