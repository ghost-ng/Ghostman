"""
Settings Dialog for Ghostman.

Provides comprehensive settings interface with AI model configuration,
presets, and custom model support.
"""

import logging
import os
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,
    QGroupBox, QFormLayout, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QSplitter, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QFont, QIcon

# Import font service for font configuration
from ...application.font_service import font_service

logger = logging.getLogger("ghostman.settings_dialog")


class SettingsDialog(QDialog):
    """
    Comprehensive settings dialog for Ghostman configuration.
    
    Features:
    - AI Model configuration with presets and custom entries
    - Base URL and API key configuration
    - Save/Load configuration profiles
    - All configs stored in APPDATA location
    """
    
    # Signals
    settings_applied = pyqtSignal(dict)
    opacity_preview_changed = pyqtSignal(float)  # Signal for live opacity preview
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.current_config = {}
        
        self._init_ui()
        self._load_current_settings()
        self._apply_uniform_button_styles()
        
        logger.info("SettingsDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Ghostman Settings")
        self.setModal(False)
        self.resize(600, 500)
        # Non-modal tool window that doesn't block main app interaction
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowCloseButtonHint | 
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Apply theme styling
        self._apply_theme()
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add tabs
        self._create_ai_model_tab()
        self._create_interface_tab()
        self._create_font_tab()
        self._create_advanced_tab()
        self._create_pki_tab()
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Config management buttons
        self.save_config_btn = QPushButton("Save Config...")
        self.save_config_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton("Load Config...")
        self.load_config_btn.clicked.connect(self._load_config)
        button_layout.addWidget(self.load_config_btn)
        
        button_layout.addStretch()
        
        # Dialog buttons
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._ok_clicked)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
        logger.debug("Settings UI initialized")
    
    def _create_ai_model_tab(self):
        """Create AI Model configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Model Configuration Group
        model_group = QGroupBox("AI Model Configuration")
        model_layout = QFormLayout(model_group)
        
        # Model presets
        self.model_preset_combo = QComboBox()
        self._populate_model_presets()
        self.model_preset_combo.currentTextChanged.connect(self._on_preset_changed)
        model_layout.addRow("Model Preset:", self.model_preset_combo)
        
        # Custom model fields
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("e.g., gpt-4, claude-3-sonnet, custom-model")
        model_layout.addRow("Model Name:", self.model_name_edit)
        
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("e.g., https://api.openai.com/v1")
        model_layout.addRow("Base URL:", self.base_url_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter your API key")
        model_layout.addRow("API Key:", self.api_key_edit)
        
        # Show/Hide API key button
        show_key_btn = QPushButton("Show/Hide Key")
        show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        model_layout.addRow("", show_key_btn)
        
        layout.addWidget(model_group)
        
        # Model Parameters Group
        params_group = QGroupBox("Model Parameters")
        params_layout = QFormLayout(params_group)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        params_layout.addRow("Temperature:", self.temperature_spin)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32000)
        self.max_tokens_spin.setValue(2000)
        params_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        # System Prompt - Split into user customizable and hardcoded base
        system_prompt_group = QGroupBox("AI Assistant Instructions")
        system_prompt_layout = QVBoxLayout()
        
        # User customizable prompt
        user_prompt_label = QLabel("Custom Personality & Behavior:")
        user_prompt_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        system_prompt_layout.addWidget(user_prompt_label)
        
        help_label = QLabel("Define the AI's identity, role, expertise, and specific behavioral traits")
        help_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic; margin-bottom: 5px;")
        system_prompt_layout.addWidget(help_label)
        
        self.user_prompt_edit = QTextEdit()
        self.user_prompt_edit.setMaximumHeight(100)
        self.user_prompt_edit.setPlaceholderText("Example: You are a Python expert specialized in data science. Focus on performance optimization and explain complex concepts simply.")
        system_prompt_layout.addWidget(self.user_prompt_edit)
        
        # Hardcoded base prompt (read-only display)
        base_prompt_label = QLabel("Built-in Response Formatting (Always Applied):")
        base_prompt_label.setStyleSheet("font-weight: bold; color: #666; margin-top: 10px;")
        system_prompt_layout.addWidget(base_prompt_label)
        
        format_help_label = QLabel("These formatting rules are automatically applied to ensure readable responses")
        format_help_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic; margin-bottom: 5px;")
        system_prompt_layout.addWidget(format_help_label)
        
        self.base_prompt_display = QTextEdit()
        self.base_prompt_display.setMaximumHeight(80)
        self.base_prompt_display.setReadOnly(True)
        self.base_prompt_display.setStyleSheet("background-color: #f8f9fa; color: #666; border: 1px solid #e9ecef; border-radius: 4px;")
        
        # Set the hardcoded base prompt - purely formatting rules
        base_prompt = ("Format all responses using markdown syntax:\n"
                      "• **bold** for key terms\n"
                      "• *italics* for emphasis\n" 
                      "• `code` for technical terms and variables\n"
                      "• ```language\ncode blocks\n``` for multi-line code\n"
                      "• # Headers to organize sections\n"
                      "• - Bullet points for lists\n"
                      "• > Blockquotes for important notes")
        self.base_prompt_display.setPlainText(base_prompt)
        system_prompt_layout.addWidget(self.base_prompt_display)
        
        system_prompt_group.setLayout(system_prompt_layout)
        params_layout.addRow("", system_prompt_group)
        
        layout.addWidget(params_group)
        
        # Test Connection Group
        test_group = QGroupBox("Connection Test")
        test_layout = QHBoxLayout(test_group)
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        test_layout.addWidget(self.test_btn)
        
        self.test_status_label = QLabel("Not tested")
        test_layout.addWidget(self.test_status_label)
        test_layout.addStretch()
        
        layout.addWidget(test_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "AI Model")
    
    def _create_interface_tab(self):
        """Create Interface settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Appearance Group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        # Percent-based opacity (store int percent 10-100) with +/- buttons
        opacity_layout = QHBoxLayout()
        
        # Decrease button
        self.opacity_decrease_btn = QPushButton("-")
        self.opacity_decrease_btn.setMaximumWidth(30)
        self.opacity_decrease_btn.clicked.connect(lambda: self._adjust_opacity(-5))
        
        # Opacity spin box
        self.opacity_percent_spin = QSpinBox()
        self.opacity_percent_spin.setRange(10, 100)
        self.opacity_percent_spin.setSingleStep(5)
        self.opacity_percent_spin.setValue(90)
        self.opacity_percent_spin.valueChanged.connect(self._on_opacity_preview)
        
        # Increase button
        self.opacity_increase_btn = QPushButton("+")
        self.opacity_increase_btn.setMaximumWidth(30)
        self.opacity_increase_btn.clicked.connect(lambda: self._adjust_opacity(5))
        
        opacity_layout.addWidget(self.opacity_decrease_btn)
        opacity_layout.addWidget(self.opacity_percent_spin)
        opacity_layout.addWidget(self.opacity_increase_btn)
        opacity_layout.addStretch()
        
        appearance_layout.addRow("Panel Opacity (%):", opacity_layout)


        layout.addWidget(appearance_group)

        # Behavior Group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout(behavior_group)

        self.start_minimized_check = QCheckBox("Start minimized to system tray")
        behavior_layout.addRow("", self.start_minimized_check)

        self.close_to_tray_check = QCheckBox("Close to system tray (don't exit)")
        self.close_to_tray_check.setChecked(True)
        behavior_layout.addRow("", self.close_to_tray_check)

        layout.addWidget(behavior_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Interface")
    
    def _create_font_tab(self):
        """Create Font settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # AI Response Font Group
        ai_font_group = QGroupBox("AI Response Font")
        ai_font_layout = QFormLayout(ai_font_group)

        # AI Response Font Family
        self.ai_font_family_combo = QComboBox()
        self.ai_font_family_combo.setEditable(False)
        available_fonts = font_service.get_available_fonts()
        self.ai_font_family_combo.addItems(available_fonts)
        ai_font_layout.addRow("Font Family:", self.ai_font_family_combo)

        # AI Response Font Size with improved +/- buttons
        ai_font_size_layout = QHBoxLayout()
        
        # Decrease button with proper styling
        self.ai_font_size_decrease_btn = QPushButton("-")
        self.ai_font_size_decrease_btn.setMaximumWidth(30)
        self.ai_font_size_decrease_btn.clicked.connect(lambda: self._adjust_ai_font_size(-1))
        
        # Font size spin box
        self.ai_font_size_spin = QSpinBox()
        self.ai_font_size_spin.setRange(6, 72)
        self.ai_font_size_spin.setValue(11)
        
        # Increase button with proper styling
        self.ai_font_size_increase_btn = QPushButton("+")
        self.ai_font_size_increase_btn.setMaximumWidth(30)
        self.ai_font_size_increase_btn.clicked.connect(lambda: self._adjust_ai_font_size(1))
        
        ai_font_size_layout.addWidget(self.ai_font_size_decrease_btn)
        ai_font_size_layout.addWidget(self.ai_font_size_spin)
        ai_font_size_layout.addWidget(self.ai_font_size_increase_btn)
        ai_font_size_layout.addStretch()
        
        ai_font_layout.addRow("Font Size:", ai_font_size_layout)

        # AI Response Font Weight
        self.ai_font_weight_combo = QComboBox()
        self.ai_font_weight_combo.addItems(["normal", "bold"])
        ai_font_layout.addRow("Font Weight:", self.ai_font_weight_combo)

        # AI Response Font Style
        self.ai_font_style_combo = QComboBox()
        self.ai_font_style_combo.addItems(["normal", "italic"])
        ai_font_layout.addRow("Font Style:", self.ai_font_style_combo)

        layout.addWidget(ai_font_group)

        # User Input Font Group
        user_font_group = QGroupBox("User Input Font")
        user_font_layout = QFormLayout(user_font_group)

        # User Input Font Family
        self.user_font_family_combo = QComboBox()
        self.user_font_family_combo.setEditable(False)
        self.user_font_family_combo.addItems(available_fonts)
        user_font_layout.addRow("Font Family:", self.user_font_family_combo)

        # User Input Font Size with improved +/- buttons
        user_font_size_layout = QHBoxLayout()
        
        # Decrease button with proper styling
        self.user_font_size_decrease_btn = QPushButton("-")
        self.user_font_size_decrease_btn.setMaximumWidth(30)
        self.user_font_size_decrease_btn.clicked.connect(lambda: self._adjust_user_font_size(-1))
        
        # Font size spin box
        self.user_font_size_spin = QSpinBox()
        self.user_font_size_spin.setRange(6, 72)
        self.user_font_size_spin.setValue(10)
        
        # Increase button with proper styling
        self.user_font_size_increase_btn = QPushButton("+")
        self.user_font_size_increase_btn.setMaximumWidth(30)
        self.user_font_size_increase_btn.clicked.connect(lambda: self._adjust_user_font_size(1))
        
        user_font_size_layout.addWidget(self.user_font_size_decrease_btn)
        user_font_size_layout.addWidget(self.user_font_size_spin)
        user_font_size_layout.addWidget(self.user_font_size_increase_btn)
        user_font_size_layout.addStretch()
        
        user_font_layout.addRow("Font Size:", user_font_size_layout)

        # User Input Font Weight
        self.user_font_weight_combo = QComboBox()
        self.user_font_weight_combo.addItems(["normal", "bold"])
        user_font_layout.addRow("Font Weight:", self.user_font_weight_combo)

        # User Input Font Style
        self.user_font_style_combo = QComboBox()
        self.user_font_style_combo.addItems(["normal", "italic"])
        user_font_layout.addRow("Font Style:", self.user_font_style_combo)

        layout.addWidget(user_font_group)

        # Font Preview Group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.ai_preview_label = QLabel("AI Response: This is how AI responses will look.")
        self._apply_preview_label_style(self.ai_preview_label)
        preview_layout.addWidget(self.ai_preview_label)

        self.user_preview_label = QLabel("User Input: This is how your input will look.")
        self._apply_preview_label_style(self.user_preview_label)
        preview_layout.addWidget(self.user_preview_label)

        layout.addWidget(preview_group)

        # Connect font change events to preview updates AND immediate application
        self.ai_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_family_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.ai_font_size_spin.valueChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_weight_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_style_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_style_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        
        self.user_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_family_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.user_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.user_font_size_spin.valueChanged.connect(self._apply_font_changes_immediately)
        self.user_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_weight_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.user_font_style_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_style_combo.currentTextChanged.connect(self._apply_font_changes_immediately)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Fonts")
    
    def _apply_preview_label_style(self, label):
        """Apply theme-aware style to preview labels."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            colors = theme_manager.current_theme
            label.setStyleSheet(f"padding: 10px; border: 1px solid {colors.border_primary}; background-color: {colors.background_secondary};")
        except ImportError:
            # Fallback to dark theme style
            label.setStyleSheet("padding: 10px; border: 1px solid #555; background-color: #2a2a2a;")
    
    def _update_font_previews(self):
        """Update font preview labels when font settings change."""
        try:
            # Create AI response font
            ai_font = QFont()
            ai_font.setFamily(self.ai_font_family_combo.currentText())
            ai_font.setPointSize(self.ai_font_size_spin.value())
            ai_font.setBold(self.ai_font_weight_combo.currentText() == "bold")
            ai_font.setItalic(self.ai_font_style_combo.currentText() == "italic")
            self.ai_preview_label.setFont(ai_font)
            
            # Create user input font
            user_font = QFont()
            user_font.setFamily(self.user_font_family_combo.currentText())
            user_font.setPointSize(self.user_font_size_spin.value())
            user_font.setBold(self.user_font_weight_combo.currentText() == "bold")
            user_font.setItalic(self.user_font_style_combo.currentText() == "italic")
            self.user_preview_label.setFont(user_font)
            
        except Exception as e:
            logger.error(f"Failed to update font previews: {e}")
    
    def _adjust_ai_font_size(self, delta):
        """Adjust AI response font size by the given delta."""
        current_size = self.ai_font_size_spin.value()
        new_size = max(6, min(72, current_size + delta))
        self.ai_font_size_spin.setValue(new_size)
        # Immediately apply the font change
        self._apply_font_changes_immediately()
    
    def _adjust_user_font_size(self, delta):
        """Adjust user input font size by the given delta."""
        current_size = self.user_font_size_spin.value()
        new_size = max(6, min(72, current_size + delta))
        self.user_font_size_spin.setValue(new_size)
        # Immediately apply the font change
        self._apply_font_changes_immediately()
    
    def _adjust_opacity(self, delta):
        """Adjust panel opacity by the given delta."""
        current_opacity = self.opacity_percent_spin.value()
        new_opacity = max(10, min(100, current_opacity + delta))
        self.opacity_percent_spin.setValue(new_opacity)
    
    def _apply_font_changes_immediately(self):
        """Apply font changes immediately without waiting for the Apply button."""
        try:
            # Get current font configuration
            fonts_config = {
                "ai_response": {
                    "family": self.ai_font_family_combo.currentText(),
                    "size": self.ai_font_size_spin.value(),
                    "weight": self.ai_font_weight_combo.currentText().lower(),
                    "style": self.ai_font_style_combo.currentText().lower()
                },
                "user_input": {
                    "family": self.user_font_family_combo.currentText(),
                    "size": self.user_font_size_spin.value(),
                    "weight": self.user_font_weight_combo.currentText().lower(),
                    "style": self.user_font_style_combo.currentText().lower()
                }
            }
            
            # Save to settings manager immediately
            self.settings_manager.set('fonts', fonts_config)
            
            # Emit signal to apply fonts immediately (just the fonts category)
            font_only_config = {"fonts": fonts_config}
            self.settings_applied.emit(font_only_config)
            
            logger.debug("Font changes applied immediately")
            
        except Exception as e:
            logger.error(f"Failed to apply font changes immediately: {e}")
    
    def _apply_uniform_button_styles(self):
        """Apply uniform styling to all buttons in the settings dialog."""
        try:
            from ...ui.themes.style_templates import ButtonStyleManager
            from ...ui.themes.theme_manager import get_theme_manager
            
            # Get theme manager for consistent styling
            theme_manager = get_theme_manager()
            if theme_manager and hasattr(theme_manager, 'current_theme'):
                colors = theme_manager.current_theme
                
                # Apply custom styled +/- buttons
                # Create a modern button style for +/- buttons
                plus_minus_style = f"""
                QPushButton {{
                    background-color: {colors.interactive_normal};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 2px;
                    min-width: 28px;
                    max-width: 30px;
                    min-height: 24px;
                }}
                QPushButton:hover {{
                    background-color: {colors.interactive_hover};
                    border-color: {colors.primary};
                }}
                QPushButton:pressed {{
                    background-color: {colors.interactive_active};
                    border-color: {colors.primary_hover};
                }}
                """
                
                # Apply to all +/- buttons
                self.ai_font_size_decrease_btn.setStyleSheet(plus_minus_style)
                self.ai_font_size_increase_btn.setStyleSheet(plus_minus_style)
                self.user_font_size_decrease_btn.setStyleSheet(plus_minus_style)
                self.user_font_size_increase_btn.setStyleSheet(plus_minus_style)
                self.opacity_decrease_btn.setStyleSheet(plus_minus_style)
                self.opacity_increase_btn.setStyleSheet(plus_minus_style)
                
                # Style the spinboxes to remove arrows and look cleaner
                spinbox_style = f"""
                QSpinBox {{
                    background-color: {colors.background_tertiary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    padding: 4px 8px;
                    min-width: 60px;
                }}
                QSpinBox:focus {{
                    border-color: {colors.primary};
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    width: 0px;
                    border: none;
                }}
                """
                
                # Apply to opacity and font size spinboxes
                self.opacity_percent_spin.setStyleSheet(spinbox_style)
                self.ai_font_size_spin.setStyleSheet(spinbox_style)
                self.user_font_size_spin.setStyleSheet(spinbox_style)
                
                # Apply uniform button style to regular buttons using ButtonStyleManager
                regular_button_style = ButtonStyleManager.get_unified_button_style(colors, "push", "medium")
                self.apply_btn.setStyleSheet(regular_button_style)
                self.cancel_btn.setStyleSheet(regular_button_style)
                self.ok_btn.setStyleSheet(regular_button_style)
                self.save_config_btn.setStyleSheet(regular_button_style)
                self.load_config_btn.setStyleSheet(regular_button_style)
                self.test_btn.setStyleSheet(regular_button_style)
                
                logger.debug("Applied modern button styles to settings dialog")
            else:
                logger.warning("Theme manager not available for button styling")
                
        except Exception as e:
            logger.error(f"Failed to apply uniform button styles: {e}")
    
    def _get_combined_system_prompt(self):
        """Combine user custom prompt with hardcoded base formatting instructions."""
        user_prompt = self.user_prompt_edit.toPlainText().strip()
        base_prompt = self.base_prompt_display.toPlainText().strip()
        
        if user_prompt:
            return f"{user_prompt}\n\n{base_prompt}"
        else:
            return base_prompt
    
    def _set_user_prompt_from_combined(self, combined_prompt):
        """Extract user prompt from combined system prompt."""
        if not combined_prompt:
            self.user_prompt_edit.clear()
            return
        
        base_prompt = self.base_prompt_display.toPlainText().strip()
        
        # If the combined prompt ends with the base prompt, extract the user part
        if combined_prompt.endswith(base_prompt):
            user_part = combined_prompt[:-len(base_prompt)].strip()
            # Remove the separator if present
            if user_part.endswith('\n\n'):
                user_part = user_part[:-2].strip()
            self.user_prompt_edit.setPlainText(user_part)
        else:
            # Fallback: set the entire prompt as user prompt
            self.user_prompt_edit.setPlainText(combined_prompt)
    
    def _create_advanced_tab(self):
        """Create Advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Logging Group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["Standard", "Detailed"])
        self.log_level_combo.setCurrentText("Standard")
        logging_layout.addRow("Logging Mode:", self.log_level_combo)
        
        layout.addWidget(logging_group)
        
        # Data Storage Group
        storage_group = QGroupBox("Data Storage")
        storage_layout = QFormLayout(storage_group)
        
        self.config_path_label = QLabel()
        self.config_path_label.setWordWrap(True)
        storage_layout.addRow("Config Location:", self.config_path_label)
        
        open_config_btn = QPushButton("Open Config Folder")
        open_config_btn.clicked.connect(self._open_config_folder)
        storage_layout.addRow("", open_config_btn)
        
        layout.addWidget(storage_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Advanced")
        
        # Create theme tab
        self._create_theme_tab()
    
    def _create_pki_tab(self):
        """Create PKI Authentication settings tab."""
        try:
            from ..widgets.pki_settings_widget import PKISettingsWidget
            
            # Create PKI settings widget
            self.pki_widget = PKISettingsWidget()
            
            # Connect PKI status changes
            self.pki_widget.pki_status_changed.connect(self._on_pki_status_changed)
            
            # Add as tab
            self.tab_widget.addTab(self.pki_widget, "PKI Auth")
            
        except ImportError as e:
            logger.warning(f"PKI settings not available: {e}")
            # Create a placeholder tab
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            
            info_label = QLabel("""
            <h3>PKI Authentication Not Available</h3>
            <p>PKI (Public Key Infrastructure) authentication features are not available 
            in this installation.</p>
            
            <p>To enable PKI authentication:</p>
            <ul>
            <li>Ensure the cryptography library is installed</li>
            <li>Contact your administrator for PKI setup assistance</li>
            </ul>
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            layout.addStretch()
            
            self.tab_widget.addTab(placeholder, "PKI Auth")
    
    def _on_pki_status_changed(self, enabled: bool):
        """Handle PKI authentication status changes."""
        try:
            logger.info(f"PKI authentication {'enabled' if enabled else 'disabled'}")
            
            # You could add additional handling here, such as:
            # - Updating other parts of the application
            # - Refreshing connection settings
            # - Notifying the main application window
            
        except Exception as e:
            logger.error(f"Error handling PKI status change: {e}")
        
        # Update config path
        self._update_config_path_display()
    
    def _create_theme_tab(self):
        """Create theme customization tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Theme selection group
        theme_group = QGroupBox("Theme Selection")
        theme_layout = QFormLayout()
        
        # Current theme label
        self.current_theme_label = QLabel()
        self.current_theme_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        
        # Built-in theme selector
        self.builtin_theme_selector = QComboBox()
        self.builtin_theme_selector.setMinimumWidth(200)
        
        # Custom theme selector
        self.custom_theme_selector = QComboBox()
        self.custom_theme_selector.setMinimumWidth(200)
        
        try:
            # Try to import theme manager
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            themes = theme_manager.get_available_themes()
            
            # Get built-in and custom themes directly from theme manager
            preset_themes = theme_manager.get_preset_themes()
            custom_themes = theme_manager.get_custom_themes()
            
            # Populate built-in themes dropdown
            if preset_themes:
                self.builtin_theme_selector.addItems(sorted(preset_themes))
            else:
                self.builtin_theme_selector.addItem("No built-in themes")
                self.builtin_theme_selector.setEnabled(False)
            
            # Populate custom themes dropdown
            if custom_themes:
                self.custom_theme_selector.addItems(sorted(custom_themes))
            else:
                self.custom_theme_selector.addItem("No custom themes found")
                self.custom_theme_selector.setEnabled(False)
            
            # Set current theme label and selection
            current_theme = theme_manager.current_theme_name
            self.current_theme_label.setText(f"Active: {current_theme}")
            
            # Select current theme in appropriate dropdown
            if current_theme in preset_themes:
                index = self.builtin_theme_selector.findText(current_theme)
                if index >= 0:
                    self.builtin_theme_selector.setCurrentIndex(index)
            elif current_theme in custom_themes:
                index = self.custom_theme_selector.findText(current_theme)
                if index >= 0:
                    self.custom_theme_selector.setCurrentIndex(index)
            
            # Connect signals
            self.builtin_theme_selector.currentTextChanged.connect(
                lambda theme: self._on_theme_selected(theme, "builtin"))
            self.custom_theme_selector.currentTextChanged.connect(
                lambda theme: self._on_theme_selected(theme, "custom"))
                
        except ImportError:
            self.builtin_theme_selector.addItem("Theme system not available")
            self.builtin_theme_selector.setEnabled(False)
            self.custom_theme_selector.setEnabled(False)
            self.current_theme_label.setText("Theme system not available")
        
        # Add to layout
        theme_layout.addRow("Current Theme:", self.current_theme_label)
        theme_layout.addRow("Built-in Themes:", self.builtin_theme_selector)
        theme_layout.addRow("Custom Themes:", self.custom_theme_selector)
        
        # Refresh themes button
        refresh_btn = QPushButton("Refresh Themes")
        refresh_btn.clicked.connect(self._refresh_themes)
        theme_layout.addRow("", refresh_btn)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Theme Management group
        management_group = QGroupBox("Theme Management")
        management_layout = QVBoxLayout()
        
        # Load theme button
        load_theme_layout = QHBoxLayout()
        self.load_theme_btn = QPushButton("Load Theme from File")
        self.load_theme_btn.clicked.connect(self._load_theme_from_file)
        load_theme_layout.addWidget(self.load_theme_btn)
        
        # Open themes folder button
        self.open_themes_folder_btn = QPushButton("Open Themes Folder")
        self.open_themes_folder_btn.clicked.connect(self._open_themes_folder)
        load_theme_layout.addWidget(self.open_themes_folder_btn)
        
        management_layout.addLayout(load_theme_layout)
        
        # Export theme button
        export_theme_layout = QHBoxLayout()
        self.export_theme_btn = QPushButton("Export Current Theme")
        self.export_theme_btn.clicked.connect(self._export_current_theme)
        export_theme_layout.addWidget(self.export_theme_btn)
        
        management_layout.addLayout(export_theme_layout)
        
        # Theme info
        info_label = QLabel("Place .json theme files in the themes folder and click 'Refresh Themes' to load them.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-style: italic;")
        management_layout.addWidget(info_label)
        
        management_group.setLayout(management_layout)
        layout.addWidget(management_group)
        
        # Theme editor button (keep existing)
        editor_group = QGroupBox("Theme Customization")
        editor_layout = QVBoxLayout()
        
        self.open_theme_editor_btn = QPushButton("Open Theme Editor")
        self.open_theme_editor_btn.clicked.connect(self._open_theme_editor)
        editor_layout.addWidget(self.open_theme_editor_btn)
        
        # Theme info label
        self.theme_info_label = QLabel("Use the theme editor to customize colors, create new themes, and import/export theme configurations.")
        self.theme_info_label.setWordWrap(True)
        self.theme_info_label.setStyleSheet("color: #888; font-style: italic;")
        editor_layout.addWidget(self.theme_info_label)
        
        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Themes")
    
    def _on_theme_selected(self, theme_name: str, source: str):
        """Handle theme selection change from either dropdown."""
        # Skip invalid selections
        if not theme_name or theme_name.startswith("No "):
            return
            
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            
            # Clear selection in the other dropdown to avoid confusion
            if source == "builtin":
                self.custom_theme_selector.blockSignals(True)
                self.custom_theme_selector.setCurrentIndex(-1)
                self.custom_theme_selector.blockSignals(False)
            else:  # source == "custom"
                self.builtin_theme_selector.blockSignals(True)
                self.builtin_theme_selector.setCurrentIndex(-1)
                self.builtin_theme_selector.blockSignals(False)
            
            if theme_manager.set_theme(theme_name):
                logger.info(f"Theme changed to: {theme_name}")
                self.current_theme_label.setText(f"Active: {theme_name}")
                # Apply the new theme to this dialog as well
                self._apply_theme()
            else:
                logger.error(f"Failed to set theme: {theme_name}")
        except ImportError:
            logger.warning("Theme system not available")
    
    def _refresh_themes(self):
        """Refresh the theme list by reloading themes from disk."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            
            # Reload themes
            theme_manager._load_custom_themes()
            
            # Save current theme
            current_theme = theme_manager.current_theme_name
            
            # Get all themes
            themes = theme_manager.get_available_themes()
            
            # Get built-in and custom themes directly from theme manager
            preset_themes = theme_manager.get_preset_themes()
            custom_themes = theme_manager.get_custom_themes()
            
            # Block signals during update
            self.builtin_theme_selector.blockSignals(True)
            self.custom_theme_selector.blockSignals(True)
            
            # Update built-in themes dropdown
            self.builtin_theme_selector.clear()
            if preset_themes:
                self.builtin_theme_selector.addItems(sorted(preset_themes))
                self.builtin_theme_selector.setEnabled(True)
            else:
                self.builtin_theme_selector.addItem("No built-in themes")
                self.builtin_theme_selector.setEnabled(False)
            
            # Update custom themes dropdown
            self.custom_theme_selector.clear()
            if custom_themes:
                self.custom_theme_selector.addItems(sorted(custom_themes))
                self.custom_theme_selector.setEnabled(True)
            else:
                self.custom_theme_selector.addItem("No custom themes found")
                self.custom_theme_selector.setEnabled(False)
            
            # Restore current theme selection
            if current_theme in preset_themes:
                index = self.builtin_theme_selector.findText(current_theme)
                if index >= 0:
                    self.builtin_theme_selector.setCurrentIndex(index)
                self.custom_theme_selector.setCurrentIndex(-1)
            elif current_theme in custom_themes:
                index = self.custom_theme_selector.findText(current_theme)
                if index >= 0:
                    self.custom_theme_selector.setCurrentIndex(index)
                self.builtin_theme_selector.setCurrentIndex(-1)
            
            # Re-enable signals
            self.builtin_theme_selector.blockSignals(False)
            self.custom_theme_selector.blockSignals(False)
                
            QMessageBox.information(self, "Themes Refreshed", 
                                  f"Found {len(custom_themes)} custom theme(s) and {len(preset_themes)} built-in theme(s).")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh themes: {e}")
    
    def _load_theme_from_file(self):
        """Load a theme from a JSON file."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...utils.config_paths import get_themes_dir
            
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Theme File",
                str(get_themes_dir()),
                "Theme Files (*.json);;All Files (*.*)"
            )
            
            if file_path:
                import shutil
                from pathlib import Path
                
                # Copy file to themes directory
                themes_dir = get_themes_dir()
                dest_path = themes_dir / Path(file_path).name
                
                if dest_path.exists():
                    reply = QMessageBox.question(
                        self, 
                        "Overwrite Theme?",
                        f"Theme file '{dest_path.name}' already exists. Overwrite?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                
                shutil.copy2(file_path, dest_path)
                
                # Refresh themes
                self._refresh_themes()
                
                QMessageBox.information(self, "Theme Loaded", 
                                      f"Theme file copied to themes folder: {dest_path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load theme file: {e}")
    
    def _open_themes_folder(self):
        """Open the themes folder in the file explorer."""
        try:
            from ...utils.config_paths import get_themes_dir
            import os
            import platform
            
            themes_dir = get_themes_dir()
            
            if platform.system() == 'Windows':
                os.startfile(themes_dir)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{themes_dir}"')
            else:  # Linux and others
                os.system(f'xdg-open "{themes_dir}"')
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open themes folder: {e}")
    
    def _export_current_theme(self):
        """Export the current theme to a JSON file."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...utils.config_paths import get_themes_dir
            import json
            from pathlib import Path
            
            # Get the current theme
            theme_manager = get_theme_manager()
            current_theme_name = theme_manager.current_theme_name
            current_theme = theme_manager.current_theme
            
            if not current_theme:
                QMessageBox.warning(self, "Error", "No theme currently loaded")
                return
            
            # Create theme data for export
            theme_data = {
                "name": current_theme_name,
                "display_name": current_theme_name.replace("_", " ").title(),
                "description": f"Exported {current_theme_name} theme",
                "author": "User Export",
                "version": "1.0.0",
                "colors": {
                    "primary": current_theme.primary,
                    "primary_hover": current_theme.primary_hover,
                    "secondary": current_theme.secondary,
                    "secondary_hover": current_theme.secondary_hover,
                    
                    "background_primary": current_theme.background_primary,
                    "background_secondary": current_theme.background_secondary,
                    "background_tertiary": current_theme.background_tertiary,
                    "background_overlay": current_theme.background_overlay,
                    
                    "text_primary": current_theme.text_primary,
                    "text_secondary": current_theme.text_secondary,
                    "text_tertiary": current_theme.text_tertiary,
                    "text_disabled": current_theme.text_disabled,
                    
                    "interactive_normal": current_theme.interactive_normal,
                    "interactive_hover": current_theme.interactive_hover,
                    "interactive_active": current_theme.interactive_active,
                    "interactive_disabled": current_theme.interactive_disabled,
                    
                    "status_success": current_theme.status_success,
                    "status_warning": current_theme.status_warning,
                    "status_error": current_theme.status_error,
                    "status_info": current_theme.status_info,
                    
                    "border_primary": current_theme.border_primary,
                    "border_secondary": current_theme.border_secondary,
                    "border_focus": current_theme.border_focus,
                    "separator": current_theme.separator
                }
            }
            
            # Open save dialog
            default_filename = f"{current_theme_name}_exported.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Theme",
                str(get_themes_dir() / default_filename),
                "Theme Files (*.json);;All Files (*.*)"
            )
            
            if file_path:
                # Save the theme file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(theme_data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self, 
                    "Theme Exported", 
                    f"Theme '{current_theme_name}' exported successfully to:\n{Path(file_path).name}"
                )
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export theme: {e}")
    
    def _open_theme_editor(self):
        """Open the theme editor dialog."""
        try:
            from .theme_editor import ThemeEditorDialog
            dialog = ThemeEditorDialog(self)
            dialog.theme_applied.connect(self._on_theme_applied)
            dialog.exec()
        except ImportError as e:
            QMessageBox.warning(
                self,
                "Theme Editor Unavailable", 
                f"Theme editor is not available: {e}"
            )
    
    def _on_theme_applied(self, color_system):
        """Handle theme application from editor."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            theme_manager.set_custom_theme(color_system)
            logger.info("Custom theme applied from editor")
            # Apply the new theme to this dialog
            self._apply_theme()
        except ImportError:
            logger.warning("Theme system not available")
    
    def _populate_model_presets(self):
        """Populate the model preset combo box."""
        presets = [
            "Custom",
            "OpenAI GPT-4",
            "OpenAI GPT-4 Turbo",
            "OpenAI GPT-3.5 Turbo",
            "Anthropic Claude 3 Opus",
            "Anthropic Claude 3 Sonnet",
            "Anthropic Claude 3 Haiku",
            "OpenRouter GPT-4",
            "OpenRouter Claude",
            "Local Ollama",
            "Local LM Studio"
        ]
        
        for preset in presets:
            self.model_preset_combo.addItem(preset)
    
    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        logger.debug(f"Preset changed to: {preset_name}")
        if preset_name == "Custom":
            logger.debug("Custom preset selected - no auto-fill")
            return
        
        # Define preset configurations
        presets = {
            "OpenAI GPT-4": {
                "model_name": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "OpenAI GPT-4 Turbo": {
                "model_name": "gpt-4-turbo-preview",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 4000
            },
            "OpenAI GPT-3.5 Turbo": {
                "model_name": "gpt-3.5-turbo",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "Anthropic Claude 3 Opus": {
                "model_name": "claude-3-opus-20240229",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "Anthropic Claude 3 Sonnet": {
                "model_name": "claude-3-sonnet-20240229",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "Anthropic Claude 3 Haiku": {
                "model_name": "claude-3-haiku-20240307",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "OpenRouter GPT-4": {
                "model_name": "openai/gpt-4",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "OpenRouter Claude": {
                "model_name": "anthropic/claude-3-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "Local Ollama": {
                "model_name": "llama2",
                "base_url": "http://localhost:11434/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "Local LM Studio": {
                "model_name": "local-model",
                "base_url": "http://localhost:1234/v1",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            self.model_name_edit.setText(preset["model_name"])
            self.base_url_edit.setText(preset["base_url"])
            self.temperature_spin.setValue(preset["temperature"])
            self.max_tokens_spin.setValue(preset["max_tokens"])
            
            logger.debug(f"Applied preset: {preset_name}")
    
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility."""
        if self.api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            logger.debug("API key visibility: SHOWN")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            logger.debug("API key visibility: HIDDEN")
    
    def _test_connection(self):
        """Test the AI model connection."""
        self.test_btn.setEnabled(False)
        self.test_status_label.setText("Testing...")
        self.test_status_label.setStyleSheet("color: orange;")
        
        # Get current configuration
        config = {
            'model_name': self.model_name_edit.text().strip(),
            'base_url': self.base_url_edit.text().strip(),
            'api_key': self.api_key_edit.text().strip(),
            'temperature': self.temperature_spin.value(),
            'max_tokens': self.max_tokens_spin.value(),
        }
        
        # Validate required fields
        if not config['model_name'] or not config['base_url']:
            self._finish_test(False, "❌ Missing model name or base URL")
            return
        
        # Run test in a separate thread to avoid blocking UI
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        class ConnectionTester(QObject):
            finished = pyqtSignal(bool, str, dict)
            
            def __init__(self, config):
                super().__init__()
                self.config = config
            
            def run(self):
                try:
                    from ...infrastructure.ai.ai_service import AIService
                    
                    # Create temporary AI service for testing
                    service = AIService()
                    success = service.initialize(self.config)
                    
                    if success:
                        # Test the actual connection
                        result = service.test_connection()
                        service.shutdown()
                        
                        if result['success']:
                            self.finished.emit(True, "✅ Connection successful", result.get('details', {}))
                        else:
                            self.finished.emit(False, f"❌ {result['message']}", {})
                    else:
                        self.finished.emit(False, "❌ Failed to initialize AI service", {})
                        
                except Exception as e:
                    logger.error(f"Connection test error: {e}")
                    self.finished.emit(False, f"❌ Error: {str(e)}", {})
        
        # Create worker and thread
        self.test_thread = QThread()
        self.test_worker = ConnectionTester(config)
        self.test_worker.moveToThread(self.test_thread)
        
        # Connect signals
        self.test_thread.started.connect(self.test_worker.run)
        self.test_worker.finished.connect(self._on_test_finished)
        self.test_worker.finished.connect(self.test_thread.quit)
        self.test_worker.finished.connect(self.test_worker.deleteLater)
        self.test_thread.finished.connect(self.test_thread.deleteLater)
        
        # Start the test
        self.test_thread.start()
        logger.debug("Connection test initiated")
    
    def _on_test_finished(self, success: bool, message: str, details: dict):
        """Handle connection test completion."""
        self._finish_test(success, message)
        
        if details and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Connection test details: {details}")
    
    def _finish_test(self, success: bool, message: str):
        """Finish the connection test and update UI."""
        self.test_btn.setEnabled(True)
        self.test_status_label.setText(message)
        
        if success:
            self.test_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.test_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        logger.info(f"Connection test completed: {success} - {message}")
    
    def _get_config_dir(self) -> str:
        """Get the configuration directory path (aligned with SettingsManager)."""
        try:
            if self.settings_manager and hasattr(self.settings_manager, 'settings_dir'):
                # settings_dir already points to Ghostman/configs
                path = str(self.settings_manager.settings_dir)
                os.makedirs(path, exist_ok=True)
                return path
        except Exception:
            pass
        # Fallback to previous logic
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        config_dir = os.path.join(app_data, "Ghostman", "configs")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    def _update_config_path_display(self):
        """Update the config path display."""
        config_dir = self._get_config_dir()
        self.config_path_label.setText(config_dir)
    
    def _open_config_folder(self):
        """Open the config folder in file explorer."""
        config_dir = self._get_config_dir()
        os.startfile(config_dir)
        logger.debug(f"Opened config folder: {config_dir}")
    
    def _save_config(self):
        """Save current configuration to a file."""
        config_dir = self._get_config_dir()
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            os.path.join(config_dir, "config.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                config = self._get_current_config()
                
                import json
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Success")
                msg_box.setText(f"Configuration saved to:\n{filename}")
                msg_box.setIcon(QMessageBox.Icon.Information)
                self._apply_messagebox_theme(msg_box)
                msg_box.exec()
                logger.info(f"Configuration saved to: {filename}")
                
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to save configuration:\n{str(e)}")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                self._apply_messagebox_theme(msg_box, button_color="#f44336")
                msg_box.exec()
                logger.error(f"Failed to save config: {e}")
    
    def _load_config(self):
        """Load configuration from a file."""
        config_dir = self._get_config_dir()
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration", 
            config_dir,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    config = json.load(f)
                
                self._apply_config_to_ui(config)
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Success")
                msg_box.setText(f"Configuration loaded from:\n{filename}")
                msg_box.setIcon(QMessageBox.Icon.Information)
                self._apply_messagebox_theme(msg_box)
                msg_box.exec()
                logger.info(f"Configuration loaded from: {filename}")
                
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to load configuration:\n{str(e)}")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                self._apply_messagebox_theme(msg_box, button_color="#f44336")
                msg_box.exec()
                logger.error(f"Failed to load config: {e}")
    
    def _get_current_config(self) -> Dict[str, Any]:
        """Get current configuration from UI."""
        return {
            "ai_model": {
                "preset": self.model_preset_combo.currentText(),
                "model_name": self.model_name_edit.text(),
                "base_url": self.base_url_edit.text(),
                "api_key": self.api_key_edit.text(),
                "temperature": self.temperature_spin.value(),
                "max_tokens": self.max_tokens_spin.value(),
                "system_prompt": self._get_combined_system_prompt(),
                "user_prompt": self.user_prompt_edit.toPlainText()
            },
            "interface": {
                # Store as integer percent
                "opacity": int(self.opacity_percent_spin.value()),
                "start_minimized": self.start_minimized_check.isChecked(),
                "close_to_tray": self.close_to_tray_check.isChecked()
            },
            "fonts": {
                "ai_response": {
                    "family": self.ai_font_family_combo.currentText(),
                    "size": self.ai_font_size_spin.value(),
                    "weight": self.ai_font_weight_combo.currentText(),
                    "style": self.ai_font_style_combo.currentText()
                },
                "user_input": {
                    "family": self.user_font_family_combo.currentText(),
                    "size": self.user_font_size_spin.value(),
                    "weight": self.user_font_weight_combo.currentText(),
                    "style": self.user_font_style_combo.currentText()
                }
            },
            "advanced": {
                "log_level": self.log_level_combo.currentText()
            }
        }
    
    def _apply_config_to_ui(self, config: Dict[str, Any]):
        """Apply configuration to UI elements."""
        # AI Model settings
        ai_config = config.get("ai_model", {})
        if "preset" in ai_config:
            index = self.model_preset_combo.findText(str(ai_config["preset"]))
            if index >= 0:
                self.model_preset_combo.setCurrentIndex(index)
        
        if "model_name" in ai_config:
            self.model_name_edit.setText(str(ai_config["model_name"]))
        if "base_url" in ai_config:
            self.base_url_edit.setText(str(ai_config["base_url"]))
        if "api_key" in ai_config:
            # Use settings.get() to properly decrypt the API key
            decrypted_key = self.settings_manager.get("ai_model.api_key", "")
            self.api_key_edit.setText(str(decrypted_key))
        if "temperature" in ai_config:
            try:
                self.temperature_spin.setValue(float(ai_config["temperature"]))
            except (ValueError, TypeError):
                self.temperature_spin.setValue(0.7)  # default
        if "max_tokens" in ai_config:
            try:
                self.max_tokens_spin.setValue(int(ai_config["max_tokens"]))
            except (ValueError, TypeError):
                self.max_tokens_spin.setValue(2000)  # default
        if "user_prompt" in ai_config:
            # New format: use separate user_prompt field
            self.user_prompt_edit.setPlainText(str(ai_config["user_prompt"]))
        elif "system_prompt" in ai_config:
            # Legacy format: extract user prompt from combined system prompt
            self._set_user_prompt_from_combined(str(ai_config["system_prompt"]))
        
        # Interface settings
        interface_config = config.get("interface", {})
        # Backward compatibility: migrate legacy ui.window_opacity float (0-1) to interface.opacity percent
        if (not interface_config or "opacity" not in interface_config) and "ui" in config:
            legacy_ui = config.get("ui", {})
            legacy_op = legacy_ui.get("window_opacity")
            if isinstance(legacy_op, (int, float)):
                if legacy_op <= 1.0:
                    legacy_percent = int(round(float(legacy_op) * 100))
                else:
                    legacy_percent = int(legacy_op)
                legacy_percent = max(10, min(100, legacy_percent))
                interface_config = dict(interface_config)
                interface_config["opacity"] = legacy_percent
        if "opacity" in interface_config:
            try:
                op_val = interface_config["opacity"]
                # Backward compatibility: floats 0-1 convert to percent
                if isinstance(op_val, float) and op_val <= 1.0:
                    op_val = int(round(op_val * 100))
                op_int = int(op_val)
                if not (10 <= op_int <= 100):
                    op_int = 90
                self.opacity_percent_spin.setValue(op_int)
            except (ValueError, TypeError):
                self.opacity_percent_spin.setValue(90)  # default
        if "start_minimized" in interface_config:
            value = interface_config["start_minimized"]
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes')
            self.start_minimized_check.setChecked(bool(value))
        if "close_to_tray" in interface_config:
            value = interface_config["close_to_tray"]
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes')
            self.close_to_tray_check.setChecked(bool(value))
        
        # Font settings
        fonts_config = config.get("fonts", {})
        
        # AI Response Font
        ai_font_config = fonts_config.get("ai_response", {})
        if "family" in ai_font_config:
            font_family = ai_font_config["family"]
            index = self.ai_font_family_combo.findText(font_family)
            if index >= 0:
                self.ai_font_family_combo.setCurrentIndex(index)
        if "size" in ai_font_config:
            self.ai_font_size_spin.setValue(ai_font_config["size"])
        if "weight" in ai_font_config:
            weight_index = self.ai_font_weight_combo.findText(ai_font_config["weight"])
            if weight_index >= 0:
                self.ai_font_weight_combo.setCurrentIndex(weight_index)
        if "style" in ai_font_config:
            style_index = self.ai_font_style_combo.findText(ai_font_config["style"])
            if style_index >= 0:
                self.ai_font_style_combo.setCurrentIndex(style_index)
        
        # User Input Font
        user_font_config = fonts_config.get("user_input", {})
        if "family" in user_font_config:
            font_family = user_font_config["family"]
            index = self.user_font_family_combo.findText(font_family)
            if index >= 0:
                self.user_font_family_combo.setCurrentIndex(index)
        if "size" in user_font_config:
            self.user_font_size_spin.setValue(user_font_config["size"])
        if "weight" in user_font_config:
            weight_index = self.user_font_weight_combo.findText(user_font_config["weight"])
            if weight_index >= 0:
                self.user_font_weight_combo.setCurrentIndex(weight_index)
        if "style" in user_font_config:
            style_index = self.user_font_style_combo.findText(user_font_config["style"])
            if style_index >= 0:
                self.user_font_style_combo.setCurrentIndex(style_index)
        
        # Update font previews after loading
        self._update_font_previews()
        
        # Advanced settings
        advanced_config = config.get("advanced", {})
        if "log_level" in advanced_config:
            # Map old debug settings to new simplified mode
            old_value = str(advanced_config["log_level"])
            if old_value.upper() == "DEBUG" or advanced_config.get("enable_debug", False):
                self.log_level_combo.setCurrentText("Detailed")
            else:
                self.log_level_combo.setCurrentText("Standard")
    
    def _load_current_settings(self):
        """Load current settings from settings manager."""
        logger.info("=== 📥 LOADING SETTINGS FROM STORAGE ===")
        
        # Load existing settings if available
        if self.settings_manager:
            try:
                current_settings = self.settings_manager.get_all()
                if current_settings:
                    logger.info(f"📦 Loaded {len(current_settings)} settings categories from storage")
                    
                    # Log all loaded settings
                    for category, settings in current_settings.items():
                        if isinstance(settings, dict):
                            logger.info(f"📂 Loaded category: {category} ({len(settings)} items)")
                            for key, value in settings.items():
                                display_value = "***MASKED***" if key == "api_key" and value else value
                                value_type = type(value).__name__
                                logger.info(f"  📥 {key}: {display_value} (type: {value_type})")
                        else:
                            # Handle flat settings structure
                            display_value = "***MASKED***" if "api_key" in str(category).lower() and settings else settings
                            logger.info(f"📥 Flat setting: {category} = {display_value}")
                    
                    logger.info("🔄 Applying loaded settings to UI...")
                    self._apply_config_to_ui(current_settings)
                    logger.info("✅ Settings applied to UI successfully")
                else:
                    logger.info("📦 No existing settings found in storage")
                    self._set_default_values()
            except Exception as e:
                logger.error(f"❌ Failed to load settings from storage: {e}")
                self._set_default_values()
        else:
            logger.warning("⚠️  No settings manager available - using defaults")
            self._set_default_values()
        
        logger.info("=== 📥 SETTINGS LOADING COMPLETE ===")
        logger.info("")  # Add blank line for readability
    
    def _set_default_values(self):
        """Set default values when no settings are available."""
        logger.info("🔧 Setting default values...")
        # Set default user prompt (purely identity/role, no behavioral or formatting instructions)
        default_user_prompt = "You are Ghostman, a desktop AI assistant."
        self.user_prompt_edit.setPlainText(default_user_prompt)
        logger.info(f"📝 Set default user prompt (length: {len(default_user_prompt)})")
        logger.info(f"🎨 Using default opacity: {self.opacity_percent_spin.value()}%")
        logger.info("✅ Default values set")
    
    def _apply_settings(self):
        """Apply settings without closing dialog."""
        logger.info("=== APPLYING SETTINGS - DETAILED LOG ===")
        config = self._get_current_config()
        self.current_config = config
        
        # Log all settings being applied with detailed information
        logger.info(f"Total settings categories: {len(config)}")
        for category, settings in config.items():
            logger.info(f"📂 Category: {category} ({len(settings)} items)")
            for key, value in settings.items():
                # Mask API key for logging
                if key == "api_key" and value:
                    display_value = f"***MASKED*** (length: {len(str(value))})"
                else:
                    display_value = value
                    
                # Add type information for better debugging
                value_type = type(value).__name__
                logger.info(f"  🔧 {key}: {display_value} (type: {value_type})")
        
        logger.info("=== SETTINGS VALUES CAPTURED ===")
        
        # Log validation and conversion details
        if "interface" in config:
            opacity = config["interface"].get("opacity", "not set")
            logger.info(f"🎨 Interface opacity validation: {opacity}% -> {opacity/100.0 if isinstance(opacity, (int, float)) else 'invalid'}")
        
        if "ai_model" in config:
            model_name = config["ai_model"].get("model_name", "not set")
            base_url = config["ai_model"].get("base_url", "not set")
            logger.info(f"🤖 AI Model config: {model_name} at {base_url}")
        
        if "advanced" in config:
            log_level = config["advanced"].get("log_level", "not set")
            logger.info(f"🔍 Advanced config: log_level={log_level}")
        
        if self.settings_manager:
            logger.info("💾 SAVING SETTINGS TO STORAGE")
            # Save to settings manager using nested structure for proper persistence
            saved_count = 0
            for category, settings in config.items():
                try:
                    # Save the entire category as a nested structure
                    self.settings_manager.set(category, settings)
                    logger.info(f"  ✅ Saved category: {category} ({len(settings)} items)")
                    saved_count += 1
                except Exception as e:
                    logger.error(f"  ❌ Failed to save category {category}: {e}")
            logger.info(f"💾 Settings storage complete: {saved_count} categories saved")
        else:
            logger.warning("⚠️  No settings manager available - settings not persisted")
        
        # Update font service with new font settings
        if "fonts" in config:
            fonts_config = config["fonts"]
            if "ai_response" in fonts_config:
                ai_font = fonts_config["ai_response"]
                font_service.update_font_config('ai_response', **ai_font)
            if "user_input" in fonts_config:
                user_font = fonts_config["user_input"]
                font_service.update_font_config('user_input', **user_font)
            logger.info("✅ Font service updated with new font settings")
        
        # Emit signal with detailed config
        logger.info(f"📡 Emitting settings_applied signal with {len(config)} categories")
        logger.info("📡 Signal payload categories: " + ", ".join(config.keys()))
        self.settings_applied.emit(config)
        
        # Create themed message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Settings Applied")
        msg_box.setText("Settings have been applied successfully.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        self._apply_messagebox_theme(msg_box)
        msg_box.exec()
        logger.info("=== ✅ SETTINGS APPLICATION COMPLETE ===")
        logger.info("")  # Add blank line for readability
    
    def _ok_clicked(self):
        """Handle OK button click."""
        self._apply_settings()
        self.accept()
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.current_config
    
    def _on_opacity_preview(self, value: int):
        """Handle opacity preview changes for immediate visual feedback."""
        # Convert percent to float (0.1 to 1.0)
        opacity_float = max(0.1, min(1.0, value / 100.0))
        logger.debug(f"Opacity preview: {value}% -> {opacity_float:.2f}")
        
        # Emit signal for live preview (parent window can connect to this)
        self.opacity_preview_changed.emit(opacity_float)
    
    def _apply_messagebox_theme(self, msg_box: QMessageBox, button_color: str = None):
        """Apply current theme styling to a message box."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            colors = theme_manager.current_theme
            
            # Use theme colors or fallback to provided color
            btn_color = button_color or colors.primary
            btn_hover = colors.primary_hover if button_color is None else ("#45a049" if button_color == "#4CAF50" else "#da190b")
            
            msg_box.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {colors.background_primary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                }}
                QMessageBox QLabel {{
                    color: {colors.text_primary};
                }}
                QMessageBox QPushButton {{
                    background-color: {btn_color};
                    color: {colors.text_primary};
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }}
                QMessageBox QPushButton:hover {{
                    background-color: {btn_hover};
                }}
            """)
        except ImportError:
            # Fallback to dark theme if theme system not available
            hover_color = "#45a049" if button_color == "#4CAF50" else "#da190b"
            button_color = button_color or "#4CAF50"
            
            msg_box.setStyleSheet(f"""
                QMessageBox {{
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }}
                QMessageBox QLabel {{
                    color: #ffffff;
                }}
                QMessageBox QPushButton {{
                    background-color: {button_color};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }}
                QMessageBox QPushButton:hover {{
                    background-color: {hover_color};
                }}
            """)
    
    def _apply_theme(self):
        """Apply current theme styling to the settings dialog."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...ui.themes.style_templates import StyleTemplates
            
            theme_manager = get_theme_manager()
            style = StyleTemplates.get_settings_dialog_style(theme_manager.current_theme)
            self.setStyleSheet(style)
            logger.debug(f"Applied theme: {theme_manager.current_theme_name}")
        except ImportError:
            logger.warning("Theme system not available, using fallback dark theme")
            self._apply_fallback_theme()
    
    def _apply_fallback_theme(self):
        """Apply fallback dark theme styling when theme system is not available."""
        self.setStyleSheet("""
            /* Main dialog styling */
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            /* Tab widget styling */
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #555555;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            
            /* Group box styling */
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            /* Label styling */
            QLabel {
                color: #ffffff;
            }
            
            /* Input field styling */
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #4CAF50;
            }
            
            /* ComboBox styling */
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                min-width: 6em;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #555555;
                border-left-style: solid;
            }
            QComboBox::down-arrow {
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #4CAF50;
                border: 1px solid #555555;
            }
            
            /* CheckBox styling */
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
            }
            
            /* Button styling */
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            
            /* Special button colors */
            QPushButton[objectName="cancel_btn"] {
                background-color: #757575;
            }
            QPushButton[objectName="cancel_btn"]:hover {
                background-color: #616161;
            }
            
            /* List widget styling */
            QListWidget {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }
            
            /* Splitter styling */
            QSplitter::handle {
                background-color: #555555;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
        """)