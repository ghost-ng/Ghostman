"""
Settings Dialog for Specter.

Provides comprehensive settings interface with AI model configuration,
presets, and custom model support.
"""

import logging
import os
import json
import requests
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,
    QGroupBox, QFormLayout, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QAbstractSpinBox, QSlider, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths, QTimer
from PyQt6.QtGui import QFont, QIcon

# Import font service for font configuration
from ...application.font_service import font_service

logger = logging.getLogger("specter.settings_dialog")


class SettingsDialog(QDialog):
    """
    Comprehensive settings dialog for Specter configuration.
    
    Features:
    - AI Settings configuration with presets and custom entries
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
        self.setWindowTitle("Specter Settings")
        self.setModal(False)
        self.resize(600, 500)
        # Non-modal tool window that doesn't block main app interaction
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

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
        self._create_tools_tab()
        self._create_pki_tab()
        self._create_avatar_tab()

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

        # Apply theme styling AFTER all widgets are created
        self._apply_theme()

        logger.debug("Settings UI initialized")
    
    def _create_ai_model_tab(self):
        """Create AI Settings configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Model Configuration Group
        model_group = QGroupBox("AI Settings Configuration")
        model_layout = QFormLayout(model_group)
        
        # Model profiles
        self.model_preset_combo = QComboBox()
        self._populate_model_profiles()
        self.model_preset_combo.currentTextChanged.connect(self._on_profile_changed)
        model_layout.addRow("Model Profile:", self.model_preset_combo)
        
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
        
        # API key buttons row
        api_buttons_layout = QHBoxLayout()
        
        self.show_key_btn = QPushButton("Show/Hide Key")
        self.show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_buttons_layout.addWidget(self.show_key_btn)
        
        self.show_models_btn = QPushButton("Show Models")
        self.show_models_btn.clicked.connect(self._show_models)
        api_buttons_layout.addWidget(self.show_models_btn)
        
        # Add spinner label next to Show Models button
        self.show_models_spinner_label = QLabel()
        self.show_models_spinner_label.setFixedSize(20, 20)
        self.show_models_spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_models_spinner_label.hide()  # Initially hidden
        api_buttons_layout.addWidget(self.show_models_spinner_label)
        
        api_buttons_layout.addStretch()
        api_buttons_widget = QWidget()
        api_buttons_widget.setLayout(api_buttons_layout)
        model_layout.addRow("", api_buttons_widget)
        
        layout.addWidget(model_group)
        
        # Model Parameters Group
        params_group = QGroupBox("Model Parameters")
        params_layout = QFormLayout(params_group)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        # Temperature +/- buttons with proper styling and alignment
        temp_container = QWidget()
        temp_layout = QHBoxLayout(temp_container)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setSpacing(2)
        temp_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Center vertically
        
        temp_layout.addWidget(self.temperature_spin)
        
        self.temperature_decrease_btn = QPushButton("-")
        self.temperature_decrease_btn.setMaximumWidth(20)
        self.temperature_decrease_btn.setFixedHeight(self.temperature_spin.sizeHint().height())  # Match spinbox height
        self.temperature_decrease_btn.clicked.connect(lambda: self.temperature_spin.setValue(
            max(self.temperature_spin.minimum(), self.temperature_spin.value() - self.temperature_spin.singleStep())
        ))
        temp_layout.addWidget(self.temperature_decrease_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.temperature_increase_btn = QPushButton("+")
        self.temperature_increase_btn.setMaximumWidth(20)
        self.temperature_increase_btn.setFixedHeight(self.temperature_spin.sizeHint().height())  # Match spinbox height
        self.temperature_increase_btn.clicked.connect(lambda: self.temperature_spin.setValue(
            min(self.temperature_spin.maximum(), self.temperature_spin.value() + self.temperature_spin.singleStep())
        ))
        temp_layout.addWidget(self.temperature_increase_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        params_layout.addRow("Temperature:", temp_container)
        
        # Temperature description
        temp_description = QLabel("Controls randomness: 0.0 = deterministic, 1.0 = creative")
        temp_description.setStyleSheet("color: #666; font-size: 11px; font-style: italic; margin-left: 4px;")
        temp_description.setWordWrap(True)
        params_layout.addRow("", temp_description)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2147483647)  # Max int32 value - no artificial limit
        self.max_tokens_spin.setValue(2000)
        self.max_tokens_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        # Max Tokens +/- buttons with proper styling and alignment
        tokens_container = QWidget()
        tokens_layout = QHBoxLayout(tokens_container)
        tokens_layout.setContentsMargins(0, 0, 0, 0)
        tokens_layout.setSpacing(2)
        tokens_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Center vertically
        
        tokens_layout.addWidget(self.max_tokens_spin)
        
        self.max_tokens_decrease_btn = QPushButton("-")
        self.max_tokens_decrease_btn.setMaximumWidth(20)
        self.max_tokens_decrease_btn.setFixedHeight(self.max_tokens_spin.sizeHint().height())  # Match spinbox height
        self.max_tokens_decrease_btn.clicked.connect(lambda: self.max_tokens_spin.setValue(
            max(self.max_tokens_spin.minimum(), self.max_tokens_spin.value() - 100)  # Decrease by 100
        ))
        tokens_layout.addWidget(self.max_tokens_decrease_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.max_tokens_increase_btn = QPushButton("+")
        self.max_tokens_increase_btn.setMaximumWidth(20)
        self.max_tokens_increase_btn.setFixedHeight(self.max_tokens_spin.sizeHint().height())  # Match spinbox height
        self.max_tokens_increase_btn.clicked.connect(lambda: self.max_tokens_spin.setValue(
            min(self.max_tokens_spin.maximum(), self.max_tokens_spin.value() + 100)  # Increase by 100
        ))
        tokens_layout.addWidget(self.max_tokens_increase_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        params_layout.addRow("Max Tokens:", tokens_container)
        
        # Max tokens description
        max_tokens_desc = QLabel("Maximum tokens the model can generate in response. Lower values = shorter responses, faster generation.")
        max_tokens_desc.setStyleSheet("color: #666; font-size: 10px; font-style: italic; margin-top: 2px;")
        max_tokens_desc.setWordWrap(True)
        params_layout.addRow("", max_tokens_desc)
        
        # Connect manual changes to switch to Custom profile
        self._setup_auto_custom_profile()
        
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

        # Import/Export Group
        import_export_group = QGroupBox("Configuration Management")
        import_export_layout = QHBoxLayout(import_export_group)

        self.export_ai_settings_btn = QPushButton("Export AI Settings")
        self.export_ai_settings_btn.setToolTip("Save AI model configuration and parameters to a JSON file")
        self.export_ai_settings_btn.clicked.connect(self._export_ai_settings)
        import_export_layout.addWidget(self.export_ai_settings_btn)

        self.import_ai_settings_btn = QPushButton("Load AI Settings")
        self.import_ai_settings_btn.setToolTip("Load AI model configuration and parameters from a JSON file")
        self.import_ai_settings_btn.clicked.connect(self._import_ai_settings)
        import_export_layout.addWidget(self.import_ai_settings_btn)

        import_export_layout.addStretch()

        layout.addWidget(import_export_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "AI Settings")
    
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
        self.opacity_decrease_btn.setMaximumWidth(20)
        self.opacity_decrease_btn.clicked.connect(lambda: self._adjust_opacity(-5))
        
        # Opacity spin box
        self.opacity_percent_spin = QSpinBox()
        self.opacity_percent_spin.setRange(10, 100)
        self.opacity_percent_spin.setSingleStep(5)
        self.opacity_percent_spin.setValue(90)
        self.opacity_percent_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.opacity_percent_spin.valueChanged.connect(self._on_opacity_preview)
        
        # Increase button
        self.opacity_increase_btn = QPushButton("+")
        self.opacity_increase_btn.setMaximumWidth(20)
        self.opacity_increase_btn.clicked.connect(lambda: self._adjust_opacity(5))
        
        opacity_layout.addWidget(self.opacity_decrease_btn)
        opacity_layout.addWidget(self.opacity_percent_spin)
        opacity_layout.addWidget(self.opacity_increase_btn)
        opacity_layout.addStretch()

        appearance_layout.addRow("Panel Opacity (%):", opacity_layout)

        # Icon size slider (1-10)
        icon_size_layout = QHBoxLayout()

        # Decrease button
        self.icon_size_decrease_btn = QPushButton("-")
        self.icon_size_decrease_btn.setMaximumWidth(20)
        self.icon_size_decrease_btn.clicked.connect(lambda: self._adjust_icon_size(-1))

        # Icon size slider
        self.icon_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.icon_size_slider.setRange(1, 10)
        self.icon_size_slider.setValue(5)
        self.icon_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.icon_size_slider.setTickInterval(1)
        self.icon_size_slider.valueChanged.connect(self._on_icon_size_changed)

        # Icon size label (shows current value)
        self.icon_size_label = QLabel("5")
        self.icon_size_label.setMinimumWidth(20)
        self.icon_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Increase button
        self.icon_size_increase_btn = QPushButton("+")
        self.icon_size_increase_btn.setMaximumWidth(20)
        self.icon_size_increase_btn.clicked.connect(lambda: self._adjust_icon_size(1))

        icon_size_layout.addWidget(self.icon_size_decrease_btn)
        icon_size_layout.addWidget(self.icon_size_slider)
        icon_size_layout.addWidget(self.icon_size_label)
        icon_size_layout.addWidget(self.icon_size_increase_btn)

        appearance_layout.addRow("Icon Size:", icon_size_layout)

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

        # Screen Capture Group
        screen_capture_group = QGroupBox("Screen Capture")
        screen_capture_layout = QFormLayout(screen_capture_group)

        # Default save location
        save_location_layout = QHBoxLayout()
        self.screen_capture_path_edit = QLineEdit()
        self.screen_capture_path_edit.setPlaceholderText("Default: %APPDATA%\\Specter\\captures")
        save_location_layout.addWidget(self.screen_capture_path_edit)

        self.browse_capture_path_btn = QPushButton("Browse...")
        self.browse_capture_path_btn.clicked.connect(self._browse_capture_path)
        save_location_layout.addWidget(self.browse_capture_path_btn)

        screen_capture_layout.addRow("Default Save Location:", save_location_layout)

        # Border color picker
        border_color_layout = QHBoxLayout()
        self.border_color_btn = QPushButton()
        self.border_color_btn.setMaximumWidth(60)
        self.border_color_btn.clicked.connect(self._pick_border_color)
        border_color_layout.addWidget(self.border_color_btn)

        # Color presets
        preset_colors = [
            ("#FF0000", "Red"),
            ("#0000FF", "Blue"),
            ("#00FF00", "Green"),
            ("#FFFF00", "Yellow"),
            ("#FFFFFF", "White"),
            ("#000000", "Black")
        ]

        for color_hex, color_name in preset_colors:
            preset_btn = QPushButton()
            preset_btn.setMaximumWidth(30)
            preset_btn.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #888;")
            preset_btn.setToolTip(color_name)
            preset_btn.clicked.connect(lambda checked, c=color_hex: self._set_border_color(c))
            border_color_layout.addWidget(preset_btn)

        border_color_layout.addStretch()
        screen_capture_layout.addRow("Border Color:", border_color_layout)

        layout.addWidget(screen_capture_group)

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
        self.ai_font_size_decrease_btn.setMaximumWidth(20)
        self.ai_font_size_decrease_btn.clicked.connect(lambda: self._adjust_ai_font_size(-1))
        
        # Font size spin box
        self.ai_font_size_spin = QSpinBox()
        self.ai_font_size_spin.setRange(6, 72)
        self.ai_font_size_spin.setValue(11)
        self.ai_font_size_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        # Increase button with proper styling
        self.ai_font_size_increase_btn = QPushButton("+")
        self.ai_font_size_increase_btn.setMaximumWidth(20)
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
        
        # AI Response Font Reset Button
        self.ai_font_reset_btn = QPushButton("Reset to Theme Default")
        self.ai_font_reset_btn.setToolTip("Reset AI Response font to the current theme's default settings")
        self.ai_font_reset_btn.clicked.connect(self._reset_ai_font_to_theme_default)
        ai_font_layout.addRow("", self.ai_font_reset_btn)

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
        self.user_font_size_decrease_btn.setMaximumWidth(20)
        self.user_font_size_decrease_btn.clicked.connect(lambda: self._adjust_user_font_size(-1))
        
        # Font size spin box
        self.user_font_size_spin = QSpinBox()
        self.user_font_size_spin.setRange(6, 72)
        self.user_font_size_spin.setValue(10)
        self.user_font_size_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        # Increase button with proper styling
        self.user_font_size_increase_btn = QPushButton("+")
        self.user_font_size_increase_btn.setMaximumWidth(20)
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
        
        # User Input Font Reset Button
        self.user_font_reset_btn = QPushButton("Reset to Theme Default")
        self.user_font_reset_btn.setToolTip("Reset User Input font to the current theme's default settings")
        self.user_font_reset_btn.clicked.connect(self._reset_user_font_to_theme_default)
        user_font_layout.addRow("", self.user_font_reset_btn)

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

        # Font customization tracking
        self._fonts_user_customized = False
        self._loading_fonts = False

        # Connect font change events to preview updates AND immediate application
        self.ai_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_family_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_family_combo.currentTextChanged.connect(self._on_font_manually_changed)
        self.ai_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.ai_font_size_spin.valueChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_size_spin.valueChanged.connect(self._on_font_manually_changed)
        self.ai_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_weight_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_weight_combo.currentTextChanged.connect(self._on_font_manually_changed)
        self.ai_font_style_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_style_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.ai_font_style_combo.currentTextChanged.connect(self._on_font_manually_changed)

        self.user_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_family_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.user_font_family_combo.currentTextChanged.connect(self._on_font_manually_changed)
        self.user_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.user_font_size_spin.valueChanged.connect(self._apply_font_changes_immediately)
        self.user_font_size_spin.valueChanged.connect(self._on_font_manually_changed)
        self.user_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_weight_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.user_font_weight_combo.currentTextChanged.connect(self._on_font_manually_changed)
        self.user_font_style_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_style_combo.currentTextChanged.connect(self._apply_font_changes_immediately)
        self.user_font_style_combo.currentTextChanged.connect(self._on_font_manually_changed)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Fonts")
    
    def _apply_preview_label_style(self, label):
        """Apply theme-aware style to preview labels matching REPL background."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            colors = theme_manager.current_theme
            label.setStyleSheet(f"""
                padding: 10px;
                border: 1px solid {colors.border_primary};
                background-color: {colors.background_secondary};
                color: {colors.text_primary};
                border-radius: 5px;
            """)
        except ImportError:
            # Fallback to dark theme style
            label.setStyleSheet("padding: 10px; border: 1px solid #555; background-color: #2a2a2a; color: #f0f0f0; border-radius: 5px;")
    
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
    
    def _reset_ai_font_to_theme_default(self):
        """Reset AI Response font to theme default."""
        try:
            # Get current theme from settings manager or theme manager
            if hasattr(self, 'settings_manager') and self.settings_manager:
                current_theme_name = self.settings_manager.get('ui.theme', 'openai_like')
            else:
                current_theme_name = 'openai_like'  # fallback
            
            # Load theme data to get default fonts
            theme_data = self._get_theme_default_fonts(current_theme_name)
            if theme_data and 'default_ai_font' in theme_data:
                ai_font = theme_data['default_ai_font']
                
                # Apply theme defaults to UI controls
                if 'family' in ai_font:
                    index = self.ai_font_family_combo.findText(ai_font['family'])
                    if index >= 0:
                        self.ai_font_family_combo.setCurrentIndex(index)
                
                if 'size' in ai_font:
                    self.ai_font_size_spin.setValue(ai_font['size'])
                
                if 'weight' in ai_font:
                    weight_index = self.ai_font_weight_combo.findText(ai_font['weight'])
                    if weight_index >= 0:
                        self.ai_font_weight_combo.setCurrentIndex(weight_index)
                
                if 'style' in ai_font:
                    style_index = self.ai_font_style_combo.findText(ai_font['style'])
                    if style_index >= 0:
                        self.ai_font_style_combo.setCurrentIndex(style_index)
                
                # Apply changes immediately
                self._apply_font_changes_immediately()
                self._fonts_user_customized = False
                logger.info(f"Reset AI font to theme default: {ai_font}")
            else:
                # Fallback to reasonable defaults
                self.ai_font_family_combo.setCurrentText("Segoe UI")
                self.ai_font_size_spin.setValue(12)
                self.ai_font_weight_combo.setCurrentText("normal")
                self.ai_font_style_combo.setCurrentText("normal")
                self._apply_font_changes_immediately()
                self._fonts_user_customized = False
                logger.info("Reset AI font to fallback defaults")

        except Exception as e:
            logger.error(f"Failed to reset AI font to theme default: {e}")
            # Fallback to reasonable defaults
            self.ai_font_family_combo.setCurrentText("Segoe UI")
            self.ai_font_size_spin.setValue(12)
            self.ai_font_weight_combo.setCurrentText("normal")
            self.ai_font_style_combo.setCurrentText("normal")
            self._apply_font_changes_immediately()

    def _reset_user_font_to_theme_default(self):
        """Reset User Input font to theme default."""
        try:
            # Get current theme from settings manager or theme manager
            if hasattr(self, 'settings_manager') and self.settings_manager:
                current_theme_name = self.settings_manager.get('ui.theme', 'openai_like')
            else:
                current_theme_name = 'openai_like'  # fallback
            
            # Load theme data to get default fonts
            theme_data = self._get_theme_default_fonts(current_theme_name)
            if theme_data and 'default_user_font' in theme_data:
                user_font = theme_data['default_user_font']
                
                # Apply theme defaults to UI controls
                if 'family' in user_font:
                    index = self.user_font_family_combo.findText(user_font['family'])
                    if index >= 0:
                        self.user_font_family_combo.setCurrentIndex(index)
                
                if 'size' in user_font:
                    self.user_font_size_spin.setValue(user_font['size'])
                
                if 'weight' in user_font:
                    weight_index = self.user_font_weight_combo.findText(user_font['weight'])
                    if weight_index >= 0:
                        self.user_font_weight_combo.setCurrentIndex(weight_index)
                
                if 'style' in user_font:
                    style_index = self.user_font_style_combo.findText(user_font['style'])
                    if style_index >= 0:
                        self.user_font_style_combo.setCurrentIndex(style_index)
                
                # Apply changes immediately
                self._apply_font_changes_immediately()
                self._fonts_user_customized = False
                logger.info(f"Reset User font to theme default: {user_font}")
            else:
                # Fallback to reasonable defaults
                self.user_font_family_combo.setCurrentText("Segoe UI")
                self.user_font_size_spin.setValue(11)
                self.user_font_weight_combo.setCurrentText("normal")
                self.user_font_style_combo.setCurrentText("normal")
                self._apply_font_changes_immediately()
                self._fonts_user_customized = False
                logger.info("Reset User font to fallback defaults")

        except Exception as e:
            logger.error(f"Failed to reset User font to theme default: {e}")
            # Fallback to reasonable defaults
            self.user_font_family_combo.setCurrentText("Segoe UI")
            self.user_font_size_spin.setValue(11)
            self.user_font_weight_combo.setCurrentText("normal")
            self.user_font_style_combo.setCurrentText("normal")
            self._apply_font_changes_immediately()

    def _get_theme_default_fonts(self, theme_name: str) -> dict:
        """Get default fonts from theme JSON file."""
        try:
            import json
            from pathlib import Path
            
            # Construct path to theme JSON file
            theme_json_path = Path(__file__).parent.parent.parent / "ui" / "themes" / "json" / f"{theme_name}.json"
            
            if theme_json_path.exists():
                with open(theme_json_path, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                    return theme_data.get('default_fonts', {})
            else:
                logger.warning(f"Theme file not found: {theme_json_path}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to load theme default fonts for {theme_name}: {e}")
            return {}

    def _on_font_manually_changed(self, *args):
        """Mark fonts as user-customized when any font control changes manually."""
        if getattr(self, '_loading_fonts', False):
            return
        self._fonts_user_customized = True

    def _auto_apply_theme_fonts(self, theme_name: str):
        """Auto-apply a theme's default fonts to the Fonts tab controls."""
        theme_fonts = self._get_theme_default_fonts(theme_name)
        if not theme_fonts:
            return

        self._loading_fonts = True
        try:
            # Apply AI font defaults
            if 'default_ai_font' in theme_fonts:
                ai_font = theme_fonts['default_ai_font']
                if 'family' in ai_font:
                    idx = self.ai_font_family_combo.findText(ai_font['family'])
                    if idx >= 0:
                        self.ai_font_family_combo.setCurrentIndex(idx)
                if 'size' in ai_font:
                    self.ai_font_size_spin.setValue(ai_font['size'])
                if 'weight' in ai_font:
                    idx = self.ai_font_weight_combo.findText(ai_font['weight'])
                    if idx >= 0:
                        self.ai_font_weight_combo.setCurrentIndex(idx)
                if 'style' in ai_font:
                    idx = self.ai_font_style_combo.findText(ai_font['style'])
                    if idx >= 0:
                        self.ai_font_style_combo.setCurrentIndex(idx)

            # Apply User font defaults
            if 'default_user_font' in theme_fonts:
                user_font = theme_fonts['default_user_font']
                if 'family' in user_font:
                    idx = self.user_font_family_combo.findText(user_font['family'])
                    if idx >= 0:
                        self.user_font_family_combo.setCurrentIndex(idx)
                if 'size' in user_font:
                    self.user_font_size_spin.setValue(user_font['size'])
                if 'weight' in user_font:
                    idx = self.user_font_weight_combo.findText(user_font['weight'])
                    if idx >= 0:
                        self.user_font_weight_combo.setCurrentIndex(idx)
                if 'style' in user_font:
                    idx = self.user_font_style_combo.findText(user_font['style'])
                    if idx >= 0:
                        self.user_font_style_combo.setCurrentIndex(idx)

            # Update preview labels
            self._update_font_previews()

            # Apply immediately to REPL
            self._apply_font_changes_immediately()
            logger.info(f"Auto-applied theme fonts for '{theme_name}'")
        finally:
            self._loading_fonts = False

    def _adjust_opacity(self, delta):
        """Adjust panel opacity by the given delta."""
        current_opacity = self.opacity_percent_spin.value()
        new_opacity = max(10, min(100, current_opacity + delta))
        self.opacity_percent_spin.setValue(new_opacity)

    def _adjust_icon_size(self, delta):
        """Adjust icon size by the given delta."""
        current_size = self.icon_size_slider.value()
        new_size = max(1, min(10, current_size + delta))
        self.icon_size_slider.setValue(new_size)

    def _on_icon_size_changed(self, value: int):
        """Handle icon size changes for immediate visual feedback."""
        # Update the label to show current value
        self.icon_size_label.setText(str(value))
        logger.debug(f"Icon size changed: {value}")

        # Emit signal for live preview (REPL widget can connect to this)
        # For now, just apply immediately via settings
        try:
            from ...infrastructure.storage.settings_manager import settings
            settings.set('interface.icon_size', value)

            # Trigger immediate icon size update in REPL
            self._apply_icon_size_immediately(value)
        except Exception as e:
            logger.error(f"Failed to apply icon size: {e}")

    def _apply_icon_size_immediately(self, size: int):
        """Apply icon size changes immediately to the REPL widget."""
        try:
            # Get the main window's REPL widget
            from ...application.app_coordinator import get_app_coordinator
            coordinator = get_app_coordinator()

            if coordinator and hasattr(coordinator, '_main_window') and coordinator._main_window:
                main_window = coordinator._main_window
                if hasattr(main_window, 'repl_widget') and main_window.repl_widget:
                    # Update icon sizes in REPL widget
                    main_window.repl_widget._update_icon_sizes(size)
                    logger.debug(f"Applied icon size {size} to REPL widget")
        except Exception as e:
            logger.warning(f"Could not apply icon size immediately: {e}")

    def _adjust_log_retention(self, delta):
        """Adjust log retention days by the given delta."""
        current_retention = self.log_retention_spin.value()
        new_retention = max(1, min(365, current_retention + delta))
        self.log_retention_spin.setValue(new_retention)
    
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
                self.temperature_decrease_btn.setStyleSheet(plus_minus_style)
                self.temperature_increase_btn.setStyleSheet(plus_minus_style)
                self.max_tokens_decrease_btn.setStyleSheet(plus_minus_style)
                self.max_tokens_increase_btn.setStyleSheet(plus_minus_style)
                self.ai_font_size_decrease_btn.setStyleSheet(plus_minus_style)
                self.ai_font_size_increase_btn.setStyleSheet(plus_minus_style)
                self.user_font_size_decrease_btn.setStyleSheet(plus_minus_style)
                self.user_font_size_increase_btn.setStyleSheet(plus_minus_style)
                self.opacity_decrease_btn.setStyleSheet(plus_minus_style)
                self.opacity_increase_btn.setStyleSheet(plus_minus_style)
                self.log_retention_decrease_btn.setStyleSheet(plus_minus_style)
                self.log_retention_increase_btn.setStyleSheet(plus_minus_style)
                
                # Modern scroll bar styling
                scrollbar_style = f"""
                QScrollBar:vertical {{
                    background-color: {colors.background_secondary};
                    width: 12px;
                    border: none;
                    border-radius: 6px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {colors.border_primary};
                    border-radius: 6px;
                    min-height: 20px;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {colors.secondary};
                }}
                QScrollBar::handle:vertical:pressed {{
                    background-color: {colors.primary};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    border: none;
                    background: none;
                    height: 0px;
                    width: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QScrollBar:horizontal {{
                    background-color: {colors.background_secondary};
                    height: 12px;
                    border: none;
                    border-radius: 6px;
                    margin: 0px;
                }}
                QScrollBar::handle:horizontal {{
                    background-color: {colors.border_primary};
                    border-radius: 6px;
                    min-width: 20px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background-color: {colors.secondary};
                }}
                QScrollBar::handle:horizontal:pressed {{
                    background-color: {colors.primary};
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    border: none;
                    background: none;
                    height: 0px;
                    width: 0px;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
                """
                
                # Apply scroll bar styling to the dialog
                self.setStyleSheet(self.styleSheet() + scrollbar_style)
                
                # Style spinboxes with visible, theme-aware up/down buttons
                # NOTE: Qt CSS does not support border-triangle tricks for arrows.
                # We style the buttons and let Qt draw native arrows via palette.
                spinbox_style = f"""
                QSpinBox, QDoubleSpinBox {{
                    background-color: {colors.background_tertiary};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border_primary};
                    border-radius: 4px;
                    padding: 4px 30px 4px 8px;
                    min-width: 60px;
                    min-height: 24px;
                }}
                QSpinBox:focus, QDoubleSpinBox:focus {{
                    border-color: {colors.primary};
                }}
                QSpinBox::up-button, QDoubleSpinBox::up-button {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 24px;
                    height: 14px;
                    border-left: 1px solid {colors.border_primary};
                    border-bottom: 1px solid {colors.border_primary};
                    border-top-right-radius: 4px;
                    background-color: {colors.background_secondary};
                }}
                QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
                    background-color: {colors.primary};
                }}
                QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
                    background-color: {colors.secondary};
                }}
                QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-bottom: 6px solid {colors.text_primary};
                    width: 0px;
                    height: 0px;
                }}
                QSpinBox::down-button, QDoubleSpinBox::down-button {{
                    subcontrol-origin: padding;
                    subcontrol-position: bottom right;
                    width: 24px;
                    height: 14px;
                    border-left: 1px solid {colors.border_primary};
                    border-top: 1px solid {colors.border_primary};
                    border-bottom-right-radius: 4px;
                    background-color: {colors.background_secondary};
                }}
                QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                    background-color: {colors.primary};
                }}
                QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
                    background-color: {colors.secondary};
                }}
                QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid {colors.text_primary};
                    width: 0px;
                    height: 0px;
                }}
                """

                # Apply to all spinboxes (including Tools tab)
                all_spinboxes = [
                    self.temperature_spin, self.max_tokens_spin,
                    self.opacity_percent_spin, self.ai_font_size_spin,
                    self.user_font_size_spin, self.log_retention_spin,
                ]
                # Tools tab spinboxes (may not exist if tab not created yet)
                for attr in [
                    'tools_max_iterations_spin', 'web_search_max_results_spin',
                    'docx_font_size_spin', 'docx_line_spacing_spin',
                    'docx_margin_top_spin', 'docx_margin_bottom_spin',
                    'docx_margin_left_spin', 'docx_margin_right_spin',
                    'ai_intent_threshold_slider',
                ]:
                    if hasattr(self, attr):
                        all_spinboxes.append(getattr(self, attr))
                for spin in all_spinboxes:
                    spin.setStyleSheet(spinbox_style)
                
                # Apply uniform button style to ALL buttons using ButtonStyleManager
                regular_button_style = ButtonStyleManager.get_unified_button_style(colors, "push", "medium")
                
                # Dialog control buttons
                self.apply_btn.setStyleSheet(regular_button_style)
                self.cancel_btn.setStyleSheet(regular_button_style)
                self.ok_btn.setStyleSheet(regular_button_style)
                
                # Config management buttons
                self.save_config_btn.setStyleSheet(regular_button_style)
                self.load_config_btn.setStyleSheet(regular_button_style)
                
                # API tab buttons
                self.test_btn.setStyleSheet(regular_button_style)
                self.show_models_btn.setStyleSheet(regular_button_style)
                self.show_key_btn.setStyleSheet(regular_button_style)
                
                # Advanced tab buttons  
                self.log_location_browse_btn.setStyleSheet(regular_button_style)
                self.log_location_default_btn.setStyleSheet(regular_button_style)
                self.open_log_folder_btn.setStyleSheet(regular_button_style)
                self.open_config_btn.setStyleSheet(regular_button_style)
                
                # Themes tab buttons
                if hasattr(self, 'refresh_themes_btn'):
                    self.refresh_themes_btn.setStyleSheet(regular_button_style)
                if hasattr(self, 'load_theme_btn'):
                    self.load_theme_btn.setStyleSheet(regular_button_style)
                if hasattr(self, 'open_themes_folder_btn'):
                    self.open_themes_folder_btn.setStyleSheet(regular_button_style)
                if hasattr(self, 'export_theme_btn'):
                    self.export_theme_btn.setStyleSheet(regular_button_style)
                if hasattr(self, 'open_theme_editor_btn'):
                    self.open_theme_editor_btn.setStyleSheet(regular_button_style)
                
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
        
        # Log location section
        log_location_layout = QHBoxLayout()
        self.log_location_edit = QLineEdit()
        self.log_location_edit.setPlaceholderText("Default log location will be used")
        self.log_location_edit.setReadOnly(True)
        self.log_location_browse_btn = QPushButton("Browse...")
        self.log_location_browse_btn.clicked.connect(self._browse_log_location)
        self.log_location_default_btn = QPushButton("Use Default")
        self.log_location_default_btn.clicked.connect(self._use_default_log_location)
        
        log_location_layout.addWidget(self.log_location_edit)
        log_location_layout.addWidget(self.log_location_browse_btn)
        log_location_layout.addWidget(self.log_location_default_btn)
        
        logging_layout.addRow("Log Location:", log_location_layout)
        
        # Log retention days with +/- buttons
        retention_layout = QHBoxLayout()
        
        # Decrease button
        self.log_retention_decrease_btn = QPushButton("-")
        self.log_retention_decrease_btn.setMaximumWidth(20)
        self.log_retention_decrease_btn.clicked.connect(lambda: self._adjust_log_retention(-1))
        
        # Retention days spin box
        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(1, 365)
        self.log_retention_spin.setValue(10)  # Default 10 days
        self.log_retention_spin.setSuffix(" days")
        self.log_retention_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        # Increase button
        self.log_retention_increase_btn = QPushButton("+")
        self.log_retention_increase_btn.setMaximumWidth(20)
        self.log_retention_increase_btn.clicked.connect(lambda: self._adjust_log_retention(1))
        
        retention_layout.addWidget(self.log_retention_decrease_btn)
        retention_layout.addWidget(self.log_retention_spin)
        retention_layout.addWidget(self.log_retention_increase_btn)
        retention_layout.addStretch()
        
        logging_layout.addRow("Log Retention:", retention_layout)
        
        # Open log folder button
        self.open_log_folder_btn = QPushButton("Open Log Folder")
        self.open_log_folder_btn.clicked.connect(self._open_log_folder)
        logging_layout.addRow("", self.open_log_folder_btn)
        
        layout.addWidget(logging_group)
        
        # Security Group
        security_group = QGroupBox("Security")
        security_layout = QFormLayout(security_group)
        
        # SSL verification checkbox
        self.ignore_ssl_check = QCheckBox("Ignore SSL certificate verification (Not recommended)")
        self.ignore_ssl_check.setChecked(True)  # Default to checked as requested
        self.ignore_ssl_check.setToolTip(
            "When checked, SSL certificate verification is disabled. "
            "This is useful for development environments with self-signed certificates "
            "but should be disabled in production for security."
        )
        security_layout.addRow("", self.ignore_ssl_check)
        
        layout.addWidget(security_group)
        
        # Code Display Group
        code_display_group = QGroupBox("Code Display")
        code_display_layout = QFormLayout(code_display_group)
        
        # Auto detect code language checkbox
        self.auto_detect_code_language_check = QCheckBox("Auto Detect Code Language (Experimental)")
        self.auto_detect_code_language_check.setChecked(False)  # Default to unchecked
        self.auto_detect_code_language_check.setToolTip(
            "When enabled, attempts to automatically detect the programming language "
            "of code snippets and displays the detected language label. "
            "When disabled, language labels are hidden for cleaner display."
        )
        code_display_layout.addRow("", self.auto_detect_code_language_check)
        
        # Code syntax highlighting checkbox
        self.enable_code_lexing_check = QCheckBox("Enable Code Syntax Highlighting (Experimental)")
        self.enable_code_lexing_check.setChecked(False)  # Default to unchecked
        self.enable_code_lexing_check.setToolTip(
            "When enabled, applies syntax highlighting (lexing) to code snippets using Pygments. "
        )
        code_display_layout.addRow("", self.enable_code_lexing_check)
        
        # Debug commands checkbox
        self.enable_debug_commands_check = QCheckBox("Enable Debug Commands")
        self.enable_debug_commands_check.setChecked(False)  # Default to unchecked
        self.enable_debug_commands_check.setToolTip(
            "When enabled, debug commands are shown in the REPL help menu. "
        )
        code_display_layout.addRow("", self.enable_debug_commands_check)

        layout.addWidget(code_display_group)

        # AI Intent Classification Group
        ai_intent_group = QGroupBox("AI-Powered Skill Detection")
        ai_intent_layout = QFormLayout(ai_intent_group)

        # Enable AI classification checkbox
        self.enable_ai_intent_check = QCheckBox("Enable AI Fallback for Skill Detection")
        self.enable_ai_intent_check.setChecked(False)
        self.enable_ai_intent_check.setToolTip(
            "When enabled, uses AI to classify ambiguous skill requests when pattern matching confidence is low.\n\n"
            "⚠️ WARNING: This will add 1-5 second delay to requests with low pattern confidence (<75%).\n"
            "Only enable if you frequently use natural language that doesn't match predefined patterns."
        )
        ai_intent_layout.addRow("", self.enable_ai_intent_check)

        # Performance warning label (shown when enabled)
        self.ai_intent_warning_label = QLabel(
            "⚠️ Performance Impact: AI classification adds 1-5 second delay to ambiguous requests."
        )
        self.ai_intent_warning_label.setWordWrap(True)
        self.ai_intent_warning_label.setStyleSheet("QLabel { color: #ff9800; font-weight: bold; padding: 5px; }")
        self.ai_intent_warning_label.setVisible(False)
        ai_intent_layout.addRow("", self.ai_intent_warning_label)

        # Connect checkbox to show/hide warning
        self.enable_ai_intent_check.toggled.connect(self.ai_intent_warning_label.setVisible)

        # Confidence threshold slider (only visible when AI enabled)
        self.ai_intent_threshold_label = QLabel("AI Confidence Threshold:")
        self.ai_intent_threshold_slider = QSpinBox()
        self.ai_intent_threshold_slider.setRange(50, 95)
        self.ai_intent_threshold_slider.setValue(65)
        self.ai_intent_threshold_slider.setSuffix("%")
        self.ai_intent_threshold_slider.setToolTip(
            "Minimum confidence score (50-95%) for AI to suggest a skill.\n"
            "Lower = more suggestions but less accurate.\n"
            "Higher = fewer suggestions but more accurate."
        )

        ai_intent_layout.addRow(self.ai_intent_threshold_label, self.ai_intent_threshold_slider)

        # Initially hide threshold controls
        self.ai_intent_threshold_label.setVisible(False)
        self.ai_intent_threshold_slider.setVisible(False)

        # Show/hide threshold controls based on checkbox
        def toggle_threshold_visibility(enabled):
            self.ai_intent_threshold_label.setVisible(enabled)
            self.ai_intent_threshold_slider.setVisible(enabled)

        self.enable_ai_intent_check.toggled.connect(toggle_threshold_visibility)

        layout.addWidget(ai_intent_group)

        # Data Storage Group
        storage_group = QGroupBox("Data Storage")
        storage_layout = QFormLayout(storage_group)
        
        self.config_path_label = QLabel()
        self.config_path_label.setWordWrap(True)
        storage_layout.addRow("Config Location:", self.config_path_label)
        
        self.open_config_btn = QPushButton("Open Config Folder")
        self.open_config_btn.clicked.connect(self._open_config_folder)
        storage_layout.addRow("", self.open_config_btn)
        
        # Data Purge Options
        purge_layout = QHBoxLayout()
        
        self.purge_conversations_btn = QPushButton("Purge Conversations")
        self.purge_conversations_btn.setToolTip("Delete all conversation history and messages permanently")
        self.purge_conversations_btn.clicked.connect(self._purge_conversations)
        danger_color = self._get_status_color("status_error", "#d32f2f")
        self.purge_conversations_btn.setStyleSheet(f"QPushButton {{ color: {danger_color}; font-weight: bold; }}")

        self.purge_documents_btn = QPushButton("Purge Documents")
        self.purge_documents_btn.setToolTip("Delete all RAG documents and embeddings permanently")
        self.purge_documents_btn.clicked.connect(self._purge_documents)
        self.purge_documents_btn.setStyleSheet(f"QPushButton {{ color: {danger_color}; font-weight: bold; }}")
        
        purge_layout.addWidget(self.purge_conversations_btn)
        purge_layout.addWidget(self.purge_documents_btn)
        purge_layout.addStretch()
        
        storage_layout.addRow("Reset Data:", purge_layout)
        
        layout.addWidget(storage_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Advanced")
        
        # Create theme tab
        self._create_theme_tab()
    
    def _create_tools_tab(self):
        """Create Tools settings tab for AI tool calling configuration."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Global Settings Group ──────────────────────────────────────
        global_group = QGroupBox("Global Tool Settings")
        global_layout = QFormLayout(global_group)

        self.tools_enabled_check = QCheckBox("Enable AI Tool Calling")
        self.tools_enabled_check.setChecked(True)
        self.tools_enabled_check.setToolTip(
            "Master toggle for all AI tool calling capabilities."
        )
        self.tools_enabled_check.stateChanged.connect(self._on_tools_enabled_changed)
        global_layout.addRow("", self.tools_enabled_check)

        self.tools_max_iterations_spin = QSpinBox()
        self.tools_max_iterations_spin.setRange(1, 20)
        self.tools_max_iterations_spin.setValue(5)
        self.tools_max_iterations_spin.setToolTip(
            "Maximum number of tool-call loop iterations per message."
        )
        global_layout.addRow("Max Tool Iterations:", self.tools_max_iterations_spin)

        layout.addWidget(global_group)

        # ── Web Search Group ───────────────────────────────────────────
        web_search_group = QGroupBox("Web Search")
        web_search_layout = QFormLayout(web_search_group)

        self.web_search_enabled_check = QCheckBox("Enable Web Search")
        self.web_search_enabled_check.setChecked(True)
        self.web_search_enabled_check.setToolTip(
            "Allow the AI to perform web searches when answering questions."
        )
        self.web_search_enabled_check.stateChanged.connect(self._on_web_search_enabled_changed)
        web_search_layout.addRow("", self.web_search_enabled_check)

        self.web_search_max_results_spin = QSpinBox()
        self.web_search_max_results_spin.setRange(1, 20)
        self.web_search_max_results_spin.setValue(5)
        self.web_search_max_results_spin.setToolTip(
            "Maximum number of search results to retrieve per query."
        )
        web_search_layout.addRow("Max Results:", self.web_search_max_results_spin)

        # Search provider selection
        self.web_search_provider_combo = QComboBox()
        self.web_search_provider_combo.addItem("DuckDuckGo (Free, no API key)")
        self.web_search_provider_combo.addItem("Tavily (API key required)")
        self.web_search_provider_combo.setToolTip(
            "DuckDuckGo is free and requires no setup.\n"
            "Tavily provides higher-quality AI-optimised results (1,000 free searches/month)."
        )
        self.web_search_provider_combo.currentIndexChanged.connect(self._on_search_provider_changed)
        web_search_layout.addRow("Provider:", self.web_search_provider_combo)

        # Tavily API key (hidden by default, shown when Tavily selected)
        self.tavily_api_key_edit = QLineEdit()
        self.tavily_api_key_edit.setPlaceholderText("Enter your Tavily API key")
        self.tavily_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.tavily_api_key_edit.setToolTip(
            "Get a free API key at https://tavily.com (1,000 searches/month free tier)."
        )
        self.tavily_api_key_label = QLabel("Tavily API Key:")
        web_search_layout.addRow(self.tavily_api_key_label, self.tavily_api_key_edit)
        # Hide Tavily fields by default (DuckDuckGo is selected)
        self.tavily_api_key_label.setVisible(False)
        self.tavily_api_key_edit.setVisible(False)

        layout.addWidget(web_search_group)

        # ── Document Formatter Group ───────────────────────────────────
        docx_group = QGroupBox("Document Formatter")
        docx_layout = QFormLayout(docx_group)

        self.docx_enabled_check = QCheckBox("Enable Document Formatter")
        self.docx_enabled_check.setChecked(True)
        self.docx_enabled_check.setToolTip(
            "Allow the AI to format and standardize DOCX documents."
        )
        self.docx_enabled_check.stateChanged.connect(self._on_docx_enabled_changed)
        docx_layout.addRow("", self.docx_enabled_check)

        self.docx_font_combo = QComboBox()
        self.docx_font_combo.addItems([
            "Calibri", "Arial", "Times New Roman", "Verdana", "Georgia", "Courier New"
        ])
        self.docx_font_combo.setCurrentText("Calibri")
        docx_layout.addRow("Default Font:", self.docx_font_combo)

        self.docx_font_size_spin = QSpinBox()
        self.docx_font_size_spin.setRange(8, 28)
        self.docx_font_size_spin.setValue(11)
        docx_layout.addRow("Font Size:", self.docx_font_size_spin)

        self.docx_line_spacing_spin = QDoubleSpinBox()
        self.docx_line_spacing_spin.setRange(0.5, 3.0)
        self.docx_line_spacing_spin.setSingleStep(0.05)
        self.docx_line_spacing_spin.setDecimals(2)
        self.docx_line_spacing_spin.setValue(1.15)
        docx_layout.addRow("Line Spacing:", self.docx_line_spacing_spin)

        # Margins sub-group
        margins_group = QGroupBox("Margins")
        margins_layout = QFormLayout(margins_group)

        self.docx_margin_top_spin = QDoubleSpinBox()
        self.docx_margin_top_spin.setRange(0.0, 3.0)
        self.docx_margin_top_spin.setSingleStep(0.1)
        self.docx_margin_top_spin.setDecimals(2)
        self.docx_margin_top_spin.setValue(1.0)
        self.docx_margin_top_spin.setSuffix(" in")
        margins_layout.addRow("Top:", self.docx_margin_top_spin)

        self.docx_margin_bottom_spin = QDoubleSpinBox()
        self.docx_margin_bottom_spin.setRange(0.0, 3.0)
        self.docx_margin_bottom_spin.setSingleStep(0.1)
        self.docx_margin_bottom_spin.setDecimals(2)
        self.docx_margin_bottom_spin.setValue(1.0)
        self.docx_margin_bottom_spin.setSuffix(" in")
        margins_layout.addRow("Bottom:", self.docx_margin_bottom_spin)

        self.docx_margin_left_spin = QDoubleSpinBox()
        self.docx_margin_left_spin.setRange(0.0, 3.0)
        self.docx_margin_left_spin.setSingleStep(0.1)
        self.docx_margin_left_spin.setDecimals(2)
        self.docx_margin_left_spin.setValue(1.0)
        self.docx_margin_left_spin.setSuffix(" in")
        margins_layout.addRow("Left:", self.docx_margin_left_spin)

        self.docx_margin_right_spin = QDoubleSpinBox()
        self.docx_margin_right_spin.setRange(0.0, 3.0)
        self.docx_margin_right_spin.setSingleStep(0.1)
        self.docx_margin_right_spin.setDecimals(2)
        self.docx_margin_right_spin.setValue(1.0)
        self.docx_margin_right_spin.setSuffix(" in")
        margins_layout.addRow("Right:", self.docx_margin_right_spin)

        docx_layout.addRow(margins_group)

        # Default operations checkboxes
        ops_group = QGroupBox("Default Operations")
        ops_layout = QVBoxLayout(ops_group)

        self.docx_op_fonts_check = QCheckBox("Standardize Fonts")
        self.docx_op_fonts_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_fonts_check)

        self.docx_op_margins_check = QCheckBox("Fix Margins")
        self.docx_op_margins_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_margins_check)

        self.docx_op_spacing_check = QCheckBox("Normalize Spacing")
        self.docx_op_spacing_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_spacing_check)

        self.docx_op_bullets_check = QCheckBox("Fix Bullets")
        self.docx_op_bullets_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_bullets_check)

        self.docx_op_spelling_check = QCheckBox("Fix Spelling")
        self.docx_op_spelling_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_spelling_check)

        self.docx_op_case_check = QCheckBox("Fix Case")
        self.docx_op_case_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_case_check)

        self.docx_op_headings_check = QCheckBox("Normalize Headings")
        self.docx_op_headings_check.setChecked(True)
        ops_layout.addWidget(self.docx_op_headings_check)

        docx_layout.addRow(ops_group)

        layout.addWidget(docx_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Tools")

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
            # Create a themed placeholder tab
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
            
            # Store placeholder for theme updates
            self.pki_placeholder = placeholder
            self.pki_placeholder_label = info_label
            
            self.tab_widget.addTab(placeholder, "PKI Auth")
    
    def _on_pki_status_changed(self, enabled: bool):
        """Handle PKI authentication status changes."""
        try:
            logger.info(f"PKI authentication {'enabled' if enabled else 'disabled'}")

            # Reconfigure SSL service to pick up new PKI settings
            try:
                from ...infrastructure.ssl.ssl_service import ssl_service
                from ...infrastructure.storage.settings_manager import settings

                if ssl_service.configure_from_settings(settings.get_all_settings()):
                    logger.info("✓ SSL service reconfigured after PKI status change")
                else:
                    logger.warning("⚠ SSL service reconfiguration returned False")
            except Exception as ssl_e:
                logger.error(f"Failed to reconfigure SSL service: {ssl_e}")

            # Notify app coordinator to reinitialize SSL/PKI/AI services
            # This ensures the changes take effect immediately
            try:
                # Get the app coordinator through the parent window
                parent = self.parent()
                if parent and hasattr(parent, 'app_coordinator'):
                    app_coordinator = parent.app_coordinator
                    if hasattr(app_coordinator, '_reinitialize_ssl_pki_services'):
                        logger.info("🔄 Triggering SSL/PKI/AI services reinitialization via app coordinator...")
                        app_coordinator._reinitialize_ssl_pki_services()
                        logger.info("✓ SSL/PKI/AI services reinitialization triggered")
                    else:
                        logger.warning("⚠ App coordinator does not have _reinitialize_ssl_pki_services method")
                else:
                    logger.warning("⚠ Cannot access app coordinator to trigger reinitialization")
            except Exception as coord_e:
                logger.error(f"Failed to trigger app coordinator reinitialization: {coord_e}")

        except Exception as e:
            logger.error(f"Error handling PKI status change: {e}")

        # Update config path
    
    def _apply_pki_placeholder_theme(self, colors):
        """Apply theme styling to PKI placeholder widget."""
        if not hasattr(self, 'pki_placeholder') or not self.pki_placeholder:
            return
            
        try:
            placeholder_style = f"""
            QWidget {{
                background-color: {colors.background_primary};
                color: {colors.text_primary};
            }}
            QLabel {{
                color: {colors.text_primary};
                background-color: transparent;
            }}
            """
            self.pki_placeholder.setStyleSheet(placeholder_style)
            
        except Exception as e:
            logger.warning(f"Failed to apply PKI placeholder theme: {e}")
            # Apply fallback styling
            self.pki_placeholder.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            """)
        self._update_config_path_display()

    # ── Avatar Tab (Street Fighter Theme) ─────────────────────────────

    def _create_avatar_tab(self):
        """Create the 'Choose Your Avatar' tab with carousel UI."""
        from PyQt6.QtWidgets import (
            QFrame, QSizePolicy, QGraphicsOpacityEffect, QSlider, QScrollArea,
        )
        from PyQt6.QtGui import (
            QPainter, QColor, QBrush, QPen, QFont as QGuiFont,
            QPixmap, QPainterPath, QLinearGradient,
        )
        from PyQt6.QtCore import (
            QRectF, QPropertyAnimation, QEasingCurve, QTimer,
        )
        from ...domain.models.avatar_personas import (
            AVATAR_PERSONAS, AVATAR_ORDER, get_avatar, DEFAULT_AVATAR_ID
        )
        from ...utils.resource_resolver import resolve_asset

        # Wrap everything in a scroll area so it works at any dialog size
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #1a1a2e; border: none; }
            QScrollBar:vertical {
                background: #1a1a2e; width: 8px; border: none;
            }
            QScrollBar::handle:vertical {
                background: #333355; border-radius: 4px; min-height: 30px;
            }
        """)

        tab = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(6)

        # Dark arcade background
        tab.setStyleSheet("""
            QWidget#avatarTab {
                background-color: #1a1a2e;
            }
        """)
        tab.setObjectName("avatarTab")

        # ── Header ──
        header = QLabel("\u2694\ufe0f  CHOOSE YOUR AVATAR  \u2694\ufe0f")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #00ffff;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 3px;
                padding: 4px;
                background-color: transparent;
            }
        """)
        tab_layout.addWidget(header)

        # ── Carousel state ──
        import math as _math
        self._avatar_cards = {}
        self._selected_avatar_id = DEFAULT_AVATAR_ID
        self._carousel_index = 0
        self._carousel_order = list(AVATAR_ORDER)
        total = len(self._carousel_order)

        # Card dimensions
        self._card_w, self._card_h = 280, 420

        # Pre-load all card pixmaps at full resolution
        self._card_pixmaps_raw = {}
        for avatar_id in self._carousel_order:
            persona = AVATAR_PERSONAS[avatar_id]
            pm = None
            if persona.card_image:
                try:
                    img_path = resolve_asset(f"avatars/{persona.card_image}")
                    if img_path:
                        raw = QPixmap(str(img_path))
                        if not raw.isNull():
                            pm = raw
                except Exception:
                    pass
            if pm is None or pm.isNull():
                pm = self._generate_placeholder_card(persona, self._card_w, self._card_h)
            self._card_pixmaps_raw[avatar_id] = pm

        # ── 3D Carousel Widget (custom-painted) ──
        dialog_ref = self
        math_mod = _math

        class _Carousel3D(QWidget):
            """Custom-painted 3D rotating carousel of avatar cards."""

            def __init__(self, parent=None):
                super().__init__(parent)
                self._index = 0
                self._anim_offset = 0.0  # fractional offset during rotation
                self._anim = None
                self._selected_id = DEFAULT_AVATAR_ID
                self.setFixedHeight(dialog_ref._card_h + 30)
                self.setMinimumWidth(dialog_ref._card_w * 2 + 120)
                self.setCursor(Qt.CursorShape.PointingHandCursor)

            def set_index(self, idx):
                self._index = idx % len(dialog_ref._carousel_order)
                self._anim_offset = 0.0
                self.update()

            def set_selected(self, avatar_id):
                self._selected_id = avatar_id
                self.update()

            def navigate(self, direction):
                """Animate one step with 3D rotation."""
                from PyQt6.QtCore import QVariantAnimation, QEasingCurve
                if self._anim and self._anim.state() == QVariantAnimation.State.Running:
                    return
                self._nav_dir = direction
                self._anim = QVariantAnimation()
                self._anim.setStartValue(0.0)
                self._anim.setEndValue(float(direction))
                self._anim.setDuration(400)
                self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                self._anim.valueChanged.connect(self._on_tick)
                self._anim.finished.connect(self._on_done)
                self._anim.start()

            def _on_tick(self, value):
                self._anim_offset = value
                self.update()

            def _on_done(self):
                total = len(dialog_ref._carousel_order)
                self._index = (self._index + self._nav_dir) % total
                self._anim_offset = 0.0
                dialog_ref._carousel_index = self._index
                self.update()
                dialog_ref._carousel_update_ui_state()

            def jump_to(self, index):
                """Jump directly (no multi-step animation)."""
                from PyQt6.QtCore import QVariantAnimation
                if self._anim and self._anim.state() == QVariantAnimation.State.Running:
                    return
                self._index = index % len(dialog_ref._carousel_order)
                self._anim_offset = 0.0
                dialog_ref._carousel_index = self._index
                self.update()
                dialog_ref._carousel_update_ui_state()

            def paintEvent(self, event):
                from PyQt6.QtGui import QPainter, QColor, QPen

                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

                w = self.width()
                h = self.height()
                cx = w / 2.0
                cy = h / 2.0
                order = dialog_ref._carousel_order
                total = len(order)
                offset = self._anim_offset
                cw = dialog_ref._card_w
                ch = dialog_ref._card_h

                # Collect visible cards with 3D properties
                cards = []
                for delta in range(-2, 3):
                    idx = (self._index + delta) % total
                    pos = delta - offset  # effective position from center

                    if abs(pos) > 2.2:
                        continue

                    avatar_id = order[idx]
                    pm = dialog_ref._card_pixmaps_raw.get(avatar_id)
                    if not pm:
                        continue

                    # 3D cylinder projection
                    angle = pos * (math_mod.pi / 3.2)  # ~56 degrees per slot
                    cos_a = math_mod.cos(angle)
                    sin_a = math_mod.sin(angle)

                    # Scale: 1.0 at center, shrinks with depth
                    scale = max(0.30, 0.32 + 0.68 * max(0, (cos_a + 0.15) / 1.15))

                    # Horizontal compression (3D perspective foreshortening)
                    h_compress = max(0.20, abs(cos_a))

                    # Horizontal position (circular spread)
                    radius = cw * 1.2
                    x_pos = cx + sin_a * radius

                    # Opacity
                    opacity = max(0.10, 0.20 + 0.80 * max(0, (cos_a + 0.05) / 1.05))

                    cards.append((
                        cos_a,       # z-depth for sorting
                        x_pos,
                        scale,
                        h_compress,
                        opacity,
                        pm,
                        avatar_id,
                        pos,
                    ))

                # Sort back-to-front (lowest cos_a drawn first)
                cards.sort(key=lambda c: c[0])

                for z, xp, sc, hc, op, pm, aid, pos in cards:
                    draw_w = int(cw * sc * hc)
                    draw_h = int(ch * sc)

                    scaled = pm.scaled(
                        draw_w, draw_h,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

                    dx = int(xp - scaled.width() / 2)
                    dy = int(cy - scaled.height() / 2)

                    painter.setOpacity(op)
                    painter.drawPixmap(dx, dy, scaled)

                    # Highlight border for the center card (pos ≈ 0)
                    if abs(pos) < 0.15:
                        painter.setOpacity(min(1.0, op + 0.3))
                        is_sel = (aid == self._selected_id)
                        if is_sel:
                            persona = get_avatar(aid)
                            bc = QColor(persona.color_primary) if persona else QColor("#00ffff")
                        else:
                            bc = QColor("#00ffff")
                        painter.setPen(QPen(bc, 3))
                        painter.setBrush(Qt.GlobalColor.transparent)
                        painter.drawRoundedRect(dx, dy, scaled.width(), scaled.height(), 10, 10)

                painter.setOpacity(1.0)
                painter.end()

            def mousePressEvent(self, event):
                from PyQt6.QtCore import QVariantAnimation
                if self._anim and self._anim.state() == QVariantAnimation.State.Running:
                    return
                cx = self.width() / 2.0
                click_x = event.pos().x()
                half_w = dialog_ref._card_w * 0.45
                if abs(click_x - cx) < half_w:
                    # Clicked center card — select it
                    aid = dialog_ref._carousel_order[self._index]
                    dialog_ref._on_avatar_card_clicked(aid)
                elif click_x < cx:
                    self.navigate(-1)
                else:
                    self.navigate(1)

        self._carousel_widget = _Carousel3D()

        # Carousel row with arrow buttons
        carousel_container = QWidget()
        carousel_container.setFixedHeight(self._card_h + 30)
        carousel_container.setStyleSheet("background: transparent; border: none;")
        carousel_h_layout = QHBoxLayout()
        carousel_h_layout.setContentsMargins(0, 0, 0, 0)
        carousel_h_layout.setSpacing(0)

        arrow_style = """
            QPushButton {
                background-color: rgba(15, 52, 96, 180);
                color: #00ffff;
                font-size: 28px;
                font-weight: bold;
                border: 2px solid #00ffff;
                border-radius: 22px;
                min-width: 44px; max-width: 44px;
                min-height: 44px; max-height: 44px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 40);
                border: 2px solid #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(0, 255, 255, 80);
            }
        """

        btn_left = QPushButton("\u276e")
        btn_left.setStyleSheet(arrow_style)
        btn_left.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_left.clicked.connect(lambda: self._carousel_widget.navigate(-1))

        btn_right = QPushButton("\u276f")
        btn_right.setStyleSheet(arrow_style)
        btn_right.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_right.clicked.connect(lambda: self._carousel_widget.navigate(1))

        carousel_h_layout.addWidget(btn_left, 0, Qt.AlignmentFlag.AlignVCenter)
        carousel_h_layout.addWidget(self._carousel_widget, 1)
        carousel_h_layout.addWidget(btn_right, 0, Qt.AlignmentFlag.AlignVCenter)

        carousel_container.setLayout(carousel_h_layout)
        tab_layout.addWidget(carousel_container)

        # ── Dot indicators ──
        dots_widget = QWidget()
        dots_layout = QHBoxLayout()
        dots_layout.setContentsMargins(0, 0, 0, 0)
        dots_layout.setSpacing(8)
        dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._carousel_dots = []
        for i in range(total):
            dot = QLabel("\u2b24")  # ⬤
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(16, 16)
            dot.setStyleSheet("color: #333355; font-size: 10px; background: transparent; border: none;")
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            idx_capture = i
            dot.mousePressEvent = lambda e, idx=idx_capture: self._carousel_jump(idx)
            dots_layout.addWidget(dot)
            self._carousel_dots.append(dot)

        dots_widget.setLayout(dots_layout)
        tab_layout.addWidget(dots_widget)

        # ── Select Button ──
        self._carousel_select_btn = QPushButton("SELECT")
        self._carousel_select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._carousel_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #00ffff;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 2px;
                border: 2px solid #00ffff;
                border-radius: 6px;
                padding: 8px 32px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 40);
            }
            QPushButton:pressed {
                background-color: rgba(0, 255, 255, 80);
            }
        """)
        self._carousel_select_btn.clicked.connect(self._carousel_select_center)
        select_wrapper = QWidget()
        select_wrapper.setStyleSheet("background: transparent; border: none;")
        sw_layout = QHBoxLayout()
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sw_layout.addWidget(self._carousel_select_btn)
        select_wrapper.setLayout(sw_layout)
        tab_layout.addWidget(select_wrapper)

        # ── Preview Panel (name, tagline, signature) ──
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_frame.setObjectName("avatarPreview")
        preview_frame.setStyleSheet("""
            QFrame#avatarPreview {
                background-color: #0f3460;
                border: 2px solid #e94560;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(2)

        self._avatar_preview_name = QLabel()
        self._avatar_preview_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_preview_name.setStyleSheet("""
            QLabel { color: #ffffff; font-size: 16px; font-weight: bold;
                     background: transparent; border: none; }
        """)
        preview_layout.addWidget(self._avatar_preview_name)

        self._avatar_preview_signature = QLabel()
        self._avatar_preview_signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_preview_signature.setStyleSheet("""
            QLabel { color: #e94560; font-size: 13px; font-style: italic;
                     background: transparent; border: none; }
        """)
        preview_layout.addWidget(self._avatar_preview_signature)

        self._avatar_preview_tagline = QLabel()
        self._avatar_preview_tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_preview_tagline.setWordWrap(True)
        self._avatar_preview_tagline.setStyleSheet("""
            QLabel { color: #aaaacc; font-size: 11px;
                     background: transparent; border: none; padding-top: 2px; }
        """)
        preview_layout.addWidget(self._avatar_preview_tagline)

        preview_frame.setLayout(preview_layout)
        tab_layout.addWidget(preview_frame)

        # ── Avatar Scale Slider ──
        scale_frame = QFrame()
        scale_frame.setObjectName("avatarScaleFrame")
        scale_frame.setStyleSheet("""
            QFrame#avatarScaleFrame {
                background-color: #0f3460;
                border: 2px solid #4682B4;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        scale_layout = QVBoxLayout()
        scale_layout.setSpacing(4)

        scale_header = QLabel("AVATAR SIZE")
        scale_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scale_header.setStyleSheet("""
            QLabel { color: #00ffff; font-size: 12px; font-weight: bold;
                     letter-spacing: 2px; background: transparent; border: none; }
        """)
        scale_layout.addWidget(scale_header)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        small_lbl = QLabel("Small")
        small_lbl.setStyleSheet("color: #8888aa; font-size: 10px; background: transparent; border: none;")
        slider_row.addWidget(small_lbl)

        self._avatar_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._avatar_scale_slider.setMinimum(60)   # 0.6x
        self._avatar_scale_slider.setMaximum(500)  # 5.0x
        self._avatar_scale_slider.setValue(100)     # 1.0x default
        self._avatar_scale_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._avatar_scale_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f3460, stop:0.5 #00ffff, stop:1 #e94560);
                height: 6px;
                border-radius: 3px;
                border: 1px solid #333355;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
                border: 2px solid #0f3460;
            }
            QSlider::handle:horizontal:hover {
                background: #00ffff;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f3460, stop:1 #00ffff);
                border-radius: 3px;
            }
        """)
        self._avatar_scale_slider.valueChanged.connect(self._on_avatar_scale_changed)
        slider_row.addWidget(self._avatar_scale_slider, 1)

        large_lbl = QLabel("Large")
        large_lbl.setStyleSheet("color: #8888aa; font-size: 10px; background: transparent; border: none;")
        slider_row.addWidget(large_lbl)

        scale_layout.addLayout(slider_row)

        scale_frame.setLayout(scale_layout)
        tab_layout.addWidget(scale_frame)

        tab_layout.addStretch()
        tab.setLayout(tab_layout)
        scroll.setWidget(tab)
        self.tab_widget.addTab(scroll, "Avatar")

        # Initialize carousel to default avatar
        default_idx = 0
        if DEFAULT_AVATAR_ID in self._carousel_order:
            default_idx = self._carousel_order.index(DEFAULT_AVATAR_ID)
        self._carousel_index = default_idx
        self._carousel_update_display()
        self._on_avatar_card_clicked(DEFAULT_AVATAR_ID)

    def _generate_placeholder_card(self, persona, width, height):
        """Generate a placeholder card pixmap for personas without card_image."""
        from PyQt6.QtGui import (
            QPainter, QColor, QBrush, QPen, QFont as QGuiFont,
            QPixmap, QLinearGradient, QPainterPath,
        )
        from PyQt6.QtCore import QRectF, QPointF

        pm = QPixmap(width, height)
        pm.fill(QColor("#16213e"))

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cp = QColor(persona.color_primary)
        ca = QColor(persona.color_accent)

        # Gradient background
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height))
        dark = QColor(cp)
        dark.setAlpha(60)
        grad.setColorAt(0.0, QColor("#16213e"))
        grad.setColorAt(0.5, dark)
        grad.setColorAt(1.0, QColor("#0f0f23"))

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 12, 12)
        painter.fillPath(path, QBrush(grad))

        # Border
        painter.setPen(QPen(cp, 3))
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 12, 12)

        # "CHOOSE YOUR AVATAR" header text
        painter.setPen(QPen(QColor("#00ffff")))
        header_font = QGuiFont("Segoe UI", 8, QGuiFont.Weight.Bold)
        painter.setFont(header_font)
        painter.drawText(QRectF(0, 10, width, 20), Qt.AlignmentFlag.AlignCenter,
                         "CHOOSE YOUR AVATAR")

        # Large circle with initial
        cx, cy = width // 2, height // 2 - 20
        radius = 50
        painter.setBrush(QBrush(cp))
        painter.setPen(QPen(ca, 3))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(QPen(QColor("#ffffff")))
        init_font = QGuiFont("Segoe UI", 36, QGuiFont.Weight.Bold)
        painter.setFont(init_font)
        painter.drawText(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
            Qt.AlignmentFlag.AlignCenter, persona.initial,
        )

        # Name
        painter.setPen(QPen(QColor("#ffffff")))
        name_font = QGuiFont("Segoe UI", 16, QGuiFont.Weight.Bold)
        painter.setFont(name_font)
        painter.drawText(
            QRectF(0, cy + radius + 10, width, 30),
            Qt.AlignmentFlag.AlignCenter, persona.name.upper(),
        )

        # Tagline
        painter.setPen(QPen(QColor("#aaaacc")))
        tag_font = QGuiFont("Segoe UI", 9)
        painter.setFont(tag_font)
        painter.drawText(
            QRectF(10, cy + radius + 40, width - 20, 20),
            Qt.AlignmentFlag.AlignCenter, persona.tagline,
        )

        # Signature at bottom
        painter.setPen(QPen(QColor("#e94560")))
        sig_font = QGuiFont("Segoe UI", 9, QGuiFont.Weight.Normal)
        sig_font.setItalic(True)
        painter.setFont(sig_font)
        painter.drawText(
            QRectF(10, height - 35, width - 20, 25),
            Qt.AlignmentFlag.AlignCenter,
            f'"{persona.signature_phrase}"',
        )

        painter.end()
        return pm

    def _carousel_navigate(self, direction):
        """Navigate the carousel by +1 or -1 with 3D rotation."""
        if hasattr(self, '_carousel_widget'):
            self._carousel_widget.navigate(direction)

    def _carousel_jump(self, index):
        """Jump the carousel to a specific index."""
        if index == self._carousel_index:
            return
        if hasattr(self, '_carousel_widget'):
            self._carousel_widget.jump_to(index)

    def _carousel_select_center(self):
        """Select the currently centered avatar."""
        avatar_id = self._carousel_order[self._carousel_index]
        self._on_avatar_card_clicked(avatar_id)

    def _carousel_update_display(self):
        """Full update: repaint widget + UI state."""
        if hasattr(self, '_carousel_widget'):
            self._carousel_widget.set_index(self._carousel_index)
            self._carousel_widget.set_selected(self._selected_avatar_id)
        self._carousel_update_ui_state()

    def _carousel_update_ui_state(self):
        """Update dots, preview panel, and select button."""
        from ...domain.models.avatar_personas import get_avatar
        idx = self._carousel_index
        center_id = self._carousel_order[idx]
        persona = get_avatar(center_id)

        # Repaint carousel widget with updated selection
        if hasattr(self, '_carousel_widget'):
            self._carousel_widget.set_selected(self._selected_avatar_id)

        # Dots
        selected_idx = -1
        if self._selected_avatar_id in self._carousel_order:
            selected_idx = self._carousel_order.index(self._selected_avatar_id)

        for i, dot in enumerate(self._carousel_dots):
            if i == idx:
                dot.setStyleSheet("color: #00ffff; font-size: 10px; background: transparent; border: none;")
            elif i == selected_idx:
                persona_sel = get_avatar(self._selected_avatar_id)
                dot_color = persona_sel.color_primary if persona_sel else "#e94560"
                dot.setStyleSheet(f"color: {dot_color}; font-size: 10px; background: transparent; border: none;")
            else:
                dot.setStyleSheet("color: #333355; font-size: 10px; background: transparent; border: none;")

        # Preview panel
        if persona and hasattr(self, '_avatar_preview_name'):
            self._avatar_preview_name.setText(
                f"{persona.emoji}  {persona.name.upper()}  {persona.emoji}"
            )
            self._avatar_preview_signature.setText(
                f'"{persona.signature_phrase}"'
            )
            self._avatar_preview_tagline.setText(persona.tagline)

        # Select button
        if hasattr(self, '_carousel_select_btn'):
            if center_id == self._selected_avatar_id:
                self._carousel_select_btn.setText("\u2714  SELECTED")
                self._carousel_select_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(0, 255, 100, 30);
                        color: #00ff64;
                        font-size: 14px;
                        font-weight: bold;
                        letter-spacing: 2px;
                        border: 2px solid #00ff64;
                        border-radius: 6px;
                        padding: 8px 32px;
                    }
                """)
            else:
                self._carousel_select_btn.setText("SELECT")
                self._carousel_select_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0f3460;
                        color: #00ffff;
                        font-size: 14px;
                        font-weight: bold;
                        letter-spacing: 2px;
                        border: 2px solid #00ffff;
                        border-radius: 6px;
                        padding: 8px 32px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 255, 255, 40);
                    }
                    QPushButton:pressed {
                        background-color: rgba(0, 255, 255, 80);
                    }
                """)

    def _on_avatar_scale_changed(self, value):
        """Handle avatar scale slider change — live preview the size."""
        scale = value / 100.0

        # Live-resize the floating avatar window
        try:
            app = None
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for w in app.topLevelWidgets():
                    if hasattr(w, 'avatar_widget'):
                        base_size = 120
                        new_size = int(base_size * scale)
                        new_size = max(72, min(new_size, 600))
                        w.setFixedSize(new_size, new_size)
                        w.avatar_widget.setFixedSize(new_size, new_size)
                        w.avatar_widget._update_scaled_pixmap()
                        w.avatar_widget.update()
                        break
        except Exception:
            pass

    def _on_avatar_card_clicked(self, avatar_id: str):
        """Handle avatar card selection."""
        from ...domain.models.avatar_personas import get_avatar, get_default_avatar

        self._selected_avatar_id = avatar_id

        # Sync carousel position to selected avatar
        if hasattr(self, '_carousel_order') and avatar_id in self._carousel_order:
            self._carousel_index = self._carousel_order.index(avatar_id)

        # Sync the 3D carousel widget
        if hasattr(self, '_carousel_widget'):
            self._carousel_widget.set_index(self._carousel_index)
            self._carousel_widget.set_selected(avatar_id)

        persona = get_avatar(avatar_id) or get_default_avatar()

        # Update dots, preview, button
        if hasattr(self, '_carousel_dots'):
            self._carousel_update_ui_state()

        # Update preview panel
        if hasattr(self, '_avatar_preview_name'):
            self._avatar_preview_name.setText(
                f"{persona.emoji}  {persona.name.upper()}  {persona.emoji}"
            )
            self._avatar_preview_signature.setText(
                f'"{persona.signature_phrase}"'
            )
            self._avatar_preview_tagline.setText(persona.tagline)

        # Cross-tab sync: load persona's system prompt into AI Settings prompt editor
        if hasattr(self, 'user_prompt_edit'):
            self.user_prompt_edit.setPlainText(persona.system_prompt)

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
        self.refresh_themes_btn = QPushButton("Refresh Themes")
        self.refresh_themes_btn.clicked.connect(self._refresh_themes)
        theme_layout.addRow("", self.refresh_themes_btn)
        
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

                # Auto-apply theme's default fonts (unless user customized)
                if not getattr(self, '_fonts_user_customized', False):
                    self._auto_apply_theme_fonts(theme_name)

                # Refresh system tray menu to match new theme
                if self.parent() and hasattr(self.parent(), 'app_coordinator'):
                    app_coordinator = self.parent().app_coordinator
                    if app_coordinator and hasattr(app_coordinator, 'system_tray'):
                        system_tray = app_coordinator.system_tray
                        if system_tray and hasattr(system_tray, 'refresh_menu_theme'):
                            system_tray.refresh_menu_theme()
                            logger.debug("System tray menu theme refreshed")
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

            # Refresh system tray menu to match new theme
            if self.parent() and hasattr(self.parent(), 'app_coordinator'):
                app_coordinator = self.parent().app_coordinator
                if app_coordinator and hasattr(app_coordinator, 'system_tray'):
                    system_tray = app_coordinator.system_tray
                    if system_tray and hasattr(system_tray, 'refresh_menu_theme'):
                        system_tray.refresh_menu_theme()
                        logger.debug("System tray menu theme refreshed after custom theme")
        except ImportError:
            logger.warning("Theme system not available")
    
    def _populate_model_profiles(self):
        """Populate the model profile combo box with modern AI models."""
        profiles = [
            "Custom",
            # Latest Anthropic Models (Primary)
            "Anthropic Claude 3.5 Sonnet (Latest)",
            "Anthropic Claude 3.5 Haiku (Fast)",
            "Anthropic Claude 3 Opus (Best Quality)",
            # Latest OpenAI Models
            "OpenAI GPT-5 (Latest)",
            "OpenAI GPT-5-mini (Fast)",
            "OpenAI GPT-5-nano (Ultra Fast)",
            "OpenAI GPT-4o (Current)",
            "OpenAI o3-mini (Latest Reasoning)",
            "OpenAI o1-preview (Reasoning)",
            "OpenAI o1-mini (Fast Reasoning)",
            "OpenAI GPT-4 Turbo",
            "OpenAI GPT-4o-mini (Fast)",
            # Latest Google Models
            "Google Gemini 2.5 Pro (Latest)",
            "Google Gemini 2.5 Flash (Fast)",
            # OpenRouter Options
            "OpenRouter GPT-4o",
            "OpenRouter Claude 3.5 Sonnet",
            # Local Models
            "Local Ollama",
            "Local LM Studio"
        ]
        
        for profile in profiles:
            self.model_preset_combo.addItem(profile)
    
    def _on_profile_changed(self, profile_name: str):
        """Handle model profile selection change."""
        logger.debug(f"Model profile changed to: {profile_name}")
        if profile_name == "Custom":
            logger.debug("Custom profile selected - no auto-fill")
            return
        
        # Set flag to prevent auto-switching to Custom during preset updates
        self._updating_from_preset = True
        
        # Define comprehensive model profiles with optimized settings and limits
        profiles = {
            # Anthropic Claude Models
            "Anthropic Claude 3.5 Sonnet (Latest)": {
                "model_name": "claude-3-5-sonnet-20241022",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 1.0,  # Anthropic default, range 0.0-1.0
                "max_tokens": 8192,
                "max_tokens_limit": 8192
            },
            "Anthropic Claude 3.5 Haiku (Fast)": {
                "model_name": "claude-3-5-haiku-20241022",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 1.0,  # Anthropic default, range 0.0-1.0
                "max_tokens": 8192,
                "max_tokens_limit": 8192
            },
            "Anthropic Claude 3 Opus (Best Quality)": {
                "model_name": "claude-3-opus-20240229",
                "base_url": "https://api.anthropic.com/v1",
                "temperature": 1.0,  # Anthropic default, range 0.0-1.0
                "max_tokens": 4096,
                "max_tokens_limit": 4096
            },
            
            # Latest OpenAI Models
            "OpenAI GPT-5 (Latest)": {
                "model_name": "gpt-5",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,  # GPT-5/o1 models only support 1.0
                "max_tokens": 128000,
                "max_tokens_limit": 128000
            },
            "OpenAI GPT-5-mini (Fast)": {
                "model_name": "gpt-5-mini",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,  # GPT-5/o1 models only support 1.0
                "max_tokens": 128000,
                "max_tokens_limit": 128000
            },
            "OpenAI GPT-5-nano (Ultra Fast)": {
                "model_name": "gpt-5-nano",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,  # GPT-5/o1 models only support 1.0
                "max_tokens": 128000,
                "max_tokens_limit": 128000
            },
            "OpenAI GPT-4o (Current)": {
                "model_name": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,  # OpenAI default, range 0-2
                "max_tokens": 4096,
                "max_tokens_limit": 4096
            },
            "OpenAI o3-mini (Latest Reasoning)": {
                "model_name": "o3-mini",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,
                "max_tokens": 100000,
                "max_tokens_limit": 100000
            },
            
            # Google Gemini Models
            "Google Gemini 2.5 Pro (Latest)": {
                "model_name": "gemini-2.5-pro",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "temperature": 1.0,  # Gemini default, range 0.0-2.0
                "max_tokens": 65536,
                "max_tokens_limit": 65536
            },
            "Google Gemini 2.5 Flash (Fast)": {
                "model_name": "gemini-2.5-flash",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "temperature": 1.0,  # Gemini default, range 0.0-2.0
                "max_tokens": 65536,
                "max_tokens_limit": 65536
            },
            
            # OpenAI Reasoning Models
            "OpenAI o1-preview (Reasoning)": {
                "model_name": "o1-preview",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,
                "max_tokens": 32768,
                "max_tokens_limit": 32768
            },
            "OpenAI o1-mini (Fast Reasoning)": {
                "model_name": "o1-mini",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,
                "max_tokens": 65536,
                "max_tokens_limit": 65536
            },
            
            # Legacy Models
            "OpenAI GPT-4 Turbo": {
                "model_name": "gpt-4-turbo",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 4096,
                "max_tokens_limit": 4096
            },
            "OpenAI GPT-4o-mini (Fast)": {
                "model_name": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1",
                "temperature": 1.0,  # OpenAI default, range 0-2
                "max_tokens": 16384,
                "max_tokens_limit": 16384
            },
            
            # OpenRouter Models
            "OpenRouter GPT-4o": {
                "model_name": "openai/gpt-4o",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 1.0,  # OpenAI via OpenRouter, range 0-2
                "max_tokens": 4096,
                "max_tokens_limit": 4096
            },
            "OpenRouter Claude 3.5 Sonnet": {
                "model_name": "anthropic/claude-3.5-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 1.0,  # Anthropic via OpenRouter, range 0.0-1.0
                "max_tokens": 8192,
                "max_tokens_limit": 8192
            },
            
            # Local Models
            "Local Ollama": {
                "model_name": "llama3.1",
                "base_url": "http://localhost:11434/v1",
                "temperature": 0.8,  # Ollama default, range 0.0-1.0
                "max_tokens": 2000,
                "max_tokens_limit": 32768
            },
            "Local LM Studio": {
                "model_name": "local-model",
                "base_url": "http://localhost:1234/v1",
                "temperature": 0.8,  # Local model default, range varies
                "max_tokens": 2000,
                "max_tokens_limit": 32768
            }
        }
        
        if profile_name in profiles:
            profile = profiles[profile_name]
            # Preserve the existing API key when changing profiles
            current_api_key = self.api_key_edit.text()
            self.model_name_edit.setText(profile["model_name"])
            self.base_url_edit.setText(profile["base_url"])
            self.temperature_spin.setValue(profile["temperature"])
            # Keep the API key unchanged - user's API key should persist across profile changes
            if current_api_key:
                self.api_key_edit.setText(current_api_key)
            
            # Set max tokens range based on model limits
            max_tokens_limit = profile.get("max_tokens_limit", 32000)
            self.max_tokens_spin.setRange(1, max_tokens_limit)
            self.max_tokens_spin.setValue(profile["max_tokens"])
            
            logger.debug(f"Applied model profile: {profile_name} (max tokens limit: {max_tokens_limit})")
        else:
            # Reset to default range for custom profiles
            self.max_tokens_spin.setRange(1, 200000)
            logger.debug(f"Unknown profile: {profile_name}, using default max tokens range")
        
        # Reset flag after updating all fields
        self._updating_from_preset = False
    
    def _setup_auto_custom_profile(self):
        """Set up signal connections to automatically switch to Custom profile when user makes manual changes."""
        # Track if we're programmatically updating (to avoid switching to Custom during preset selection)
        self._updating_from_preset = False
        
        # Connect text field changes
        self.model_name_edit.textChanged.connect(self._on_manual_change)
        self.base_url_edit.textChanged.connect(self._on_manual_change)
        self.api_key_edit.textChanged.connect(self._on_manual_change)
        
        # Connect parameter changes
        self.temperature_spin.valueChanged.connect(self._on_manual_change)
        self.max_tokens_spin.valueChanged.connect(self._on_manual_change)
        
        # Connect button clicks for temperature and max tokens
        self.temperature_decrease_btn.clicked.connect(self._on_manual_change)
        self.temperature_increase_btn.clicked.connect(self._on_manual_change)
        self.max_tokens_decrease_btn.clicked.connect(self._on_manual_change)
        self.max_tokens_increase_btn.clicked.connect(self._on_manual_change)
    
    def _on_manual_change(self):
        """Handle manual changes to switch profile to Custom."""
        # Don't switch to Custom if we're updating from a preset selection
        if self._updating_from_preset:
            return
            
        # Don't switch if already on Custom
        if self.model_preset_combo.currentText() == "Custom":
            return
            
        # Switch to Custom profile
        self.model_preset_combo.setCurrentText("Custom")
        logger.debug("Switched to Custom profile due to manual setting change")
    
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility."""
        if self.api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            logger.debug("API key visibility: SHOWN")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            logger.debug("API key visibility: HIDDEN")
    
    def _test_connection(self):
        """Test the AI model connection using unified API test service."""
        self.test_btn.setEnabled(False)
        self.test_status_label.setText("Testing...")
        warning_color = self._get_status_color("status_warning", "orange")
        self.test_status_label.setStyleSheet(f"color: {warning_color};")
        
        # Get current configuration
        config_dict = {
            'model_name': self.model_name_edit.text().strip(),
            'base_url': self.base_url_edit.text().strip(),
            'api_key': self.api_key_edit.text().strip(),
            'temperature': self.temperature_spin.value(),
            'max_tokens': self.max_tokens_spin.value(),
        }
        
        # Validate required fields
        if not config_dict['model_name'] or not config_dict['base_url']:
            self._finish_test(False, "✗ Missing model name or base URL")
            return
        
        # Import unified API test service
        from ...infrastructure.ai.api_test_service import APITestConfig, get_api_test_service
        
        # Create test configuration with max 3 attempts 
        # Note: SSL verification will be automatically configured based on PKI status
        test_config = APITestConfig(
            model_name=config_dict['model_name'],
            base_url=config_dict['base_url'],
            api_key=config_dict['api_key'],
            temperature=config_dict['temperature'],
            max_tokens=config_dict['max_tokens'],
            timeout=30,
            max_test_attempts=3,
            disable_ssl_verification=True  # Will be overridden if PKI is enabled with CA bundle
        )
        
        # Get the unified test service
        self.api_test_service = get_api_test_service()
        
        # Connect signals for progress updates
        self.api_test_service.test_started.connect(self._on_test_started)
        self.api_test_service.test_attempt.connect(self._on_test_attempt)
        self.api_test_service.test_completed.connect(self._on_test_completed)
        
        # Start asynchronous test
        self.api_test_service.test_api_config_async(
            test_config,
            progress_callback=self._update_test_progress
        )
        
        logger.debug("Unified API connection test initiated")
    
    def _on_test_started(self):
        """Handle test start."""
        logger.debug("API test started")
    
    def _on_test_attempt(self, attempt: int, total_attempts: int):
        """Handle test attempt progress."""
        self.test_status_label.setText(f"Testing... (attempt {attempt}/{total_attempts})")
        logger.debug(f"API test attempt {attempt}/{total_attempts}")
    
    def _update_test_progress(self, message: str):
        """Update test progress message."""
        self.test_status_label.setText(message)
    
    def _on_test_completed(self, result):
        """Handle unified API test completion."""
        # Disconnect signals to avoid multiple connections
        try:
            self.api_test_service.test_started.disconnect(self._on_test_started)
            self.api_test_service.test_attempt.disconnect(self._on_test_attempt)
            self.api_test_service.test_completed.disconnect(self._on_test_completed)
        except Exception as e:
            logger.warning(f"Error disconnecting test signals: {e}")
        
        # Process result
        if result.success:
            self._finish_test(True, "✓ Connection successful")
            if result.details and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Connection test details: {result.details}")

            # Hide the error banner if connection test succeeds
            self._hide_error_banner_on_success()
        else:
            self._finish_test(False, result.message)
            logger.warning(f"Connection test failed after {result.total_attempts} attempts: {result.message}")
    
    def _finish_test(self, success: bool, message: str):
        """Finish the connection test and update UI."""
        self.test_btn.setEnabled(True)
        self.test_status_label.setText(message)

        if success:
            success_color = self._get_status_color("status_success", "green")
            self.test_status_label.setStyleSheet(f"color: {success_color}; font-weight: bold;")
        else:
            error_color = self._get_status_color("status_error", "red")
            self.test_status_label.setStyleSheet(f"color: {error_color}; font-weight: bold;")

        logger.info(f"Connection test completed: {success} - {message}")

    def _hide_error_banner_on_success(self):
        """Hide the API error banner when manual connection test succeeds."""
        try:
            logger.info("🔔 _hide_error_banner_on_success() called")
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            logger.debug(f"  App instance: {app is not None}")

            if app and hasattr(app, 'coordinator'):
                coordinator = app.coordinator
                logger.debug(f"  Coordinator: {coordinator is not None}")

                if coordinator and hasattr(coordinator, '_main_window'):
                    main_window = coordinator._main_window
                    logger.debug(f"  Main window: {main_window is not None}")

                    # Check for floating REPL with banner
                    if hasattr(main_window, 'floating_repl') and main_window.floating_repl:
                        logger.debug(f"  Floating REPL: exists")

                        if hasattr(main_window.floating_repl, 'floating_banner') and main_window.floating_repl.floating_banner:
                            logger.debug(f"  Floating banner: exists")
                            # Get the actual banner widget
                            floating_banner = main_window.floating_repl.floating_banner
                            banner = floating_banner.banner if hasattr(floating_banner, 'banner') else None
                            if banner and hasattr(banner, 'is_banner_visible') and banner.is_banner_visible():
                                logger.info("  Banner is visible - hiding it now")
                                banner.hide_banner()
                                logger.info("✓ API error banner hidden after successful manual connection test")
                            else:
                                logger.debug("  Banner is not visible - nothing to hide")
                        else:
                            logger.warning("  ✗ Floating banner not found or is None")
                    else:
                        logger.warning("  ✗ Floating REPL not found or is None")
                else:
                    logger.warning("  ✗ Main window not found")
            else:
                logger.warning("  ✗ App coordinator not found")
        except Exception as e:
            logger.error(f"Could not hide banner after manual test: {e}", exc_info=True)

    def _export_ai_settings(self):
        """Export AI model settings and parameters to a JSON file."""
        try:
            import json
            from PyQt6.QtWidgets import QFileDialog, QMessageBox

            # Gather AI model settings and AI-related advanced settings
            ai_config = {
                "ai_model": {
                    "model_name": self.model_name_edit.text(),
                    "base_url": self.base_url_edit.text(),
                    "api_key": self.api_key_edit.text(),
                    "temperature": self.temperature_spin.value(),
                    "max_tokens": self.max_tokens_spin.value(),
                    "system_prompt": self.user_prompt_edit.toPlainText()
                },
                "advanced": {
                    "enable_ai_intent_classification": self.enable_ai_intent_check.isChecked(),
                    "ai_intent_confidence_threshold": self.ai_intent_threshold_slider.value() / 100.0,
                    "ai_intent_timeout_seconds": 5
                }
            }

            # Ask user where to save
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export AI Settings",
                "ai_settings.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if file_path:
                # Write to file with pretty formatting
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(ai_config, f, indent=2, ensure_ascii=False)

                logger.info(f"AI settings exported to: {file_path}")
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"AI settings have been exported to:\n{file_path}"
                )

        except Exception as e:
            logger.error(f"Failed to export AI settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export AI settings:\n{str(e)}"
            )

    def _import_ai_settings(self):
        """Import AI model settings and parameters from a JSON file."""
        try:
            import json
            from PyQt6.QtWidgets import QFileDialog, QMessageBox

            # Ask user to select file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load AI Settings",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                return

            # Read from file
            with open(file_path, 'r', encoding='utf-8') as f:
                ai_config = json.load(f)

            # Validate structure
            if "ai_model" not in ai_config:
                raise ValueError("Invalid AI settings file: missing 'ai_model' section")

            # Apply AI model settings with detailed logging
            ai_model = ai_config["ai_model"]
            logger.info("=== 📥 IMPORTING AI SETTINGS ===")
            logger.info(f"Source file: {file_path}")
            logger.info(f"Total keys in ai_model section: {len(ai_model)}")

            imported_count = 0

            if "model_name" in ai_model:
                value = ai_model["model_name"]
                self.model_name_edit.setText(value)
                logger.debug(f"  ✓ Imported model_name: '{value}'")
                imported_count += 1
            else:
                logger.debug("  ⚠ model_name not found in import file")

            if "base_url" in ai_model:
                value = ai_model["base_url"]
                self.base_url_edit.setText(value)
                logger.debug(f"  ✓ Imported base_url: '{value}'")
                imported_count += 1
            else:
                logger.debug("  ⚠ base_url not found in import file")

            if "api_key" in ai_model:
                value = ai_model["api_key"]
                self.api_key_edit.setText(value)
                logger.debug(f"  ✓ Imported api_key: ***MASKED*** (length: {len(value)})")
                imported_count += 1
            else:
                logger.debug("  ⚠ api_key not found in import file")

            if "temperature" in ai_model:
                value = ai_model["temperature"]
                self.temperature_spin.setValue(value)
                logger.debug(f"  ✓ Imported temperature: {value} (type: {type(value).__name__})")
                imported_count += 1
            else:
                logger.debug("  ⚠ temperature not found in import file")

            if "max_tokens" in ai_model:
                value = ai_model["max_tokens"]
                logger.debug(f"  📝 max_tokens from file: {value} (type: {type(value).__name__})")
                logger.debug(f"  📝 max_tokens_spin range: {self.max_tokens_spin.minimum()} - {self.max_tokens_spin.maximum()}")
                logger.debug(f"  📝 max_tokens_spin current value before: {self.max_tokens_spin.value()}")
                self.max_tokens_spin.setValue(value)
                logger.debug(f"  📝 max_tokens_spin current value after: {self.max_tokens_spin.value()}")
                logger.debug(f"  ✓ Imported max_tokens: {value}")
                imported_count += 1
            else:
                logger.debug("  ⚠ max_tokens not found in import file")

            if "system_prompt" in ai_model:
                value = ai_model["system_prompt"]
                self.user_prompt_edit.setPlainText(value)
                logger.debug(f"  ✓ Imported system_prompt: (length: {len(value)})")
                imported_count += 1
            else:
                logger.debug("  ⚠ system_prompt not found in import file")

            # Apply advanced AI settings if present
            if "advanced" in ai_config:
                advanced = ai_config["advanced"]
                logger.info(f"Found advanced settings section with {len(advanced)} keys")

                if "enable_ai_intent_classification" in advanced:
                    value = advanced["enable_ai_intent_classification"]
                    self.enable_ai_intent_check.setChecked(bool(value))
                    logger.debug(f"  ✓ Imported enable_ai_intent_classification: {value}")
                    imported_count += 1

                if "ai_intent_confidence_threshold" in advanced:
                    value = advanced["ai_intent_confidence_threshold"]
                    # Convert 0.0-1.0 to 0-100 for slider
                    slider_value = int(value * 100)
                    self.ai_intent_threshold_slider.setValue(slider_value)
                    logger.debug(f"  ✓ Imported ai_intent_confidence_threshold: {value}")
                    imported_count += 1

            logger.info(f"✅ Import complete: {imported_count} total settings loaded")
            logger.info("=== 📥 IMPORT COMPLETE ===")
            logger.info(f"AI settings imported from: {file_path}")
            QMessageBox.information(
                self,
                "Import Successful",
                f"AI settings have been loaded from:\n{file_path}\n\nImported {imported_count} settings.\n\nClick 'Apply' to save these settings."
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in AI settings file: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Invalid JSON file:\n{str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to import AI settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import AI settings:\n{str(e)}"
            )

    def _show_models(self):
        """Show available models from the API endpoint."""
        try:
            # Get current configuration
            base_url = self.base_url_edit.text().strip()
            api_key = self.api_key_edit.text().strip()
            
            if not base_url:
                QMessageBox.warning(self, "Show Models", "Please enter a Base URL first.")
                return
                
            if not api_key:
                QMessageBox.warning(self, "Show Models", "Please enter an API Key first.")
                return
            
            # Disable button and start spinner
            self.show_models_btn.setEnabled(False)
            self._start_show_models_spinner()
            
            # Create and show models dialog
            dialog = ModelsDialog(base_url, api_key, self)
            dialog.model_selected.connect(self._on_model_selected)
            dialog.loading_finished.connect(self._stop_show_models_spinner)
            dialog.finished.connect(lambda: self._reset_show_models_button())
            dialog.show()
            
        except Exception as e:
            logger.error(f"Failed to show models: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show models:\n{str(e)}")
            self._reset_show_models_button()
    
    def _reset_show_models_button(self):
        """Reset the show models button state."""
        self._stop_show_models_spinner()
        self.show_models_btn.setEnabled(True)
    
    def _start_show_models_spinner(self):
        """Start the spinner animation next to the Show Models button."""
        # Initialize spinner if not already done
        if not hasattr(self, '_show_models_spinner_timer'):
            from PyQt6.QtCore import QTimer
            self._show_models_spinner_timer = QTimer()
            self._show_models_spinner_timer.timeout.connect(self._update_show_models_spinner)
            self._show_models_spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            self._show_models_spinner_index = 0
        
        # Show spinner label and start animation
        self.show_models_spinner_label.show()
        self._show_models_spinner_timer.start(100)  # Update every 100ms
        self._update_show_models_spinner()
    
    def _stop_show_models_spinner(self):
        """Stop the spinner animation next to the Show Models button."""
        if hasattr(self, '_show_models_spinner_timer'):
            self._show_models_spinner_timer.stop()
        self.show_models_spinner_label.hide()
    
    def _update_show_models_spinner(self):
        """Update the spinner animation next to the Show Models button."""
        try:
            if hasattr(self, '_show_models_spinner_chars') and hasattr(self, '_show_models_spinner_index'):
                self._show_models_spinner_index = (self._show_models_spinner_index + 1) % len(self._show_models_spinner_chars)
                spinner_char = self._show_models_spinner_chars[self._show_models_spinner_index]
                self.show_models_spinner_label.setText(spinner_char)
        except Exception as e:
            logger.error(f"Failed to update show models spinner: {e}")
    
    def _on_model_selected(self, model_name: str):
        """Handle model selection from the models dialog."""
        self.model_name_edit.setText(model_name)
        logger.info(f"Model selected: {model_name}")
    
    def _get_config_dir(self) -> str:
        """Get the configuration directory path (aligned with SettingsManager)."""
        try:
            if self.settings_manager and hasattr(self.settings_manager, 'settings_dir'):
                # settings_dir already points to Specter/configs
                path = str(self.settings_manager.settings_dir)
                os.makedirs(path, exist_ok=True)
                return path
        except Exception:
            pass
        # Fallback to previous logic
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        config_dir = os.path.join(app_data, "Specter", "configs")
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
    
    def _browse_log_location(self):
        """Browse for custom log location."""
        current_location = self.log_location_edit.text().strip()
        if not current_location:
            # Get default log location
            try:
                from ...infrastructure.logging.logging_config import _resolve_log_dir
                current_location = str(_resolve_log_dir())
            except Exception:
                current_location = ""
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Log Directory",
            current_location
        )
        
        if folder:
            self.log_location_edit.setText(folder)
            self.log_location_edit.setReadOnly(False)
            logger.debug(f"Selected custom log location: {folder}")
    
    def _use_default_log_location(self):
        """Reset to default log location."""
        self.log_location_edit.clear()
        self.log_location_edit.setPlaceholderText("Default log location will be used")
        self.log_location_edit.setReadOnly(True)
        logger.debug("Reset to default log location")

    def _browse_capture_path(self):
        """Browse for screen capture save location."""
        current_path = self.screen_capture_path_edit.text().strip()
        if not current_path:
            # Use default location
            import os
            from pathlib import Path
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                current_path = str(Path(appdata) / "Specter" / "captures")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Screen Capture Save Directory",
            current_path
        )

        if folder:
            self.screen_capture_path_edit.setText(folder)
            logger.debug(f"Screen capture save location set to: {folder}")

    def _pick_border_color(self):
        """Open color picker for border color."""
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor

        # Get current color
        current_color = QColor(getattr(self, '_current_border_color', '#FF0000'))

        # Open color dialog
        color = QColorDialog.getColor(current_color, self, "Select Border Color")

        if color.isValid():
            self._set_border_color(color.name())

    def _set_border_color(self, color_hex: str):
        """Set the border color and update button display."""
        self._current_border_color = color_hex
        self.border_color_btn.setStyleSheet(
            f"background-color: {color_hex}; border: 2px solid #888;"
        )
        self.border_color_btn.setText(color_hex.upper())
        logger.debug(f"Border color set to: {color_hex}")

    def _open_log_folder(self):
        """Open the current log folder in file explorer."""
        log_location = self.log_location_edit.text().strip()
        
        if not log_location:
            # Use default location
            try:
                from ...infrastructure.logging.logging_config import _resolve_log_dir
                log_location = str(_resolve_log_dir())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not determine log location: {e}")
                return
        
        try:
            if os.path.exists(log_location):
                os.startfile(log_location)
                logger.debug(f"Opened log folder: {log_location}")
            else:
                QMessageBox.warning(self, "Error", f"Log directory does not exist: {log_location}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open log folder: {e}")
    
    def _purge_conversations(self):
        """Purge all conversation history and messages permanently."""
        reply = QMessageBox.question(
            self,
            "Confirm Purge Conversations",
            "⚠️ WARNING: This will permanently delete ALL conversation history and messages.\n\n"
            "This action cannot be undone. Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Import required modules
                from ...infrastructure.conversation_management.repositories.conversation_repository import ConversationRepository
                from ...infrastructure.conversation_management.repositories.database import DatabaseManager
                
                # Initialize database and repository
                db_manager = DatabaseManager()
                db_manager.initialize()
                repo = ConversationRepository(db_manager)
                
                # Get all conversations and delete them (hard delete)
                import asyncio
                async def purge_all():
                    conversations = await repo.list_conversations(include_deleted=True)
                    deleted_count = 0
                    for conv in conversations:
                        success = await repo.delete_conversation(conv.id, soft_delete=False)
                        if success:
                            deleted_count += 1
                    return deleted_count
                
                # Run the purge
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                deleted_count = loop.run_until_complete(purge_all())
                loop.close()
                
                QMessageBox.information(
                    self,
                    "Purge Complete",
                    f"✅ Successfully purged {deleted_count} conversations.\n\n"
                    "All conversation history has been permanently deleted."
                )
                logger.info(f"Purged {deleted_count} conversations")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Purge Failed",
                    f"❌ Failed to purge conversations:\n\n{str(e)}"
                )
                logger.error(f"Failed to purge conversations: {e}")
    
    def _purge_documents(self):
        """Purge all RAG documents and embeddings permanently."""
        reply = QMessageBox.question(
            self,
            "Confirm Purge Documents",
            "⚠️ WARNING: This will permanently delete ALL RAG documents and embeddings.\n\n"
            "This includes all uploaded files and their processed embeddings.\n"
            "This action cannot be undone. Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Import FAISS client to clear the vector store
                from ...infrastructure.rag_pipeline.vector_store.faiss_client import FaissClient
                from ...infrastructure.rag_pipeline.config.rag_config import RAGPipelineConfig
                
                # Initialize FAISS client and clear all data
                rag_config = RAGPipelineConfig()
                faiss_client = FaissClient(rag_config.vector_store)
                
                # Clear the FAISS index and metadata
                faiss_client.clear_all_documents()
                
                # Also clear any conversation files from database
                from ...infrastructure.conversation_management.repositories.conversation_repository import ConversationRepository
                from ...infrastructure.conversation_management.repositories.database import DatabaseManager
                
                db_manager = DatabaseManager()
                db_manager.initialize()
                
                # Clear conversation_files table
                with db_manager.get_session() as session:
                    from ...infrastructure.conversation_management.models.database_models import ConversationFileModel
                    deleted_files = session.query(ConversationFileModel).count()
                    session.query(ConversationFileModel).delete()
                    session.commit()
                
                QMessageBox.information(
                    self,
                    "Purge Complete",
                    f"✅ Successfully purged all RAG documents and embeddings.\n\n"
                    f"Cleared {deleted_files} file associations and all vector embeddings.\n"
                    "All document data has been permanently deleted."
                )
                logger.info(f"Purged all RAG documents and {deleted_files} file associations")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Purge Failed",
                    f"❌ Failed to purge documents:\n\n{str(e)}"
                )
                logger.error(f"Failed to purge documents: {e}")
    
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
    
    # ── Tools tab helpers ───────────────────────────────────────────

    def _on_search_provider_changed(self, index):
        """Show/hide Tavily API key field based on selected provider."""
        is_tavily = index == 1
        self.tavily_api_key_label.setVisible(is_tavily)
        self.tavily_api_key_edit.setVisible(is_tavily)

    def _get_docx_operations(self):
        """Return list of operation strings based on checked checkboxes."""
        ops = []
        if self.docx_op_fonts_check.isChecked():
            ops.append("standardize_fonts")
        if self.docx_op_margins_check.isChecked():
            ops.append("fix_margins")
        if self.docx_op_spacing_check.isChecked():
            ops.append("normalize_spacing")
        if self.docx_op_bullets_check.isChecked():
            ops.append("fix_bullets")
        if self.docx_op_spelling_check.isChecked():
            ops.append("fix_spelling")
        if self.docx_op_case_check.isChecked():
            ops.append("fix_case")
        if self.docx_op_headings_check.isChecked():
            ops.append("normalize_headings")
        return ops

    def _on_tools_enabled_changed(self, state):
        """Immediately persist the tools enabled toggle."""
        self.settings_manager.set('tools.enabled', state == Qt.CheckState.Checked.value)

    def _on_web_search_enabled_changed(self, state):
        """Immediately persist the web search enabled toggle."""
        self.settings_manager.set('tools.web_search.enabled', state == Qt.CheckState.Checked.value)

    def _on_docx_enabled_changed(self, state):
        """Immediately persist the document formatter enabled toggle."""
        self.settings_manager.set('tools.docx_formatter.enabled', state == Qt.CheckState.Checked.value)

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
                "icon_size": int(self.icon_size_slider.value()),
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
                },
                "user_customized": getattr(self, '_fonts_user_customized', False)
            },
            "advanced": {
                "log_level": self.log_level_combo.currentText(),
                "log_location": self.log_location_edit.text().strip(),
                "log_retention_days": self.log_retention_spin.value(),
                "ignore_ssl_verification": self.ignore_ssl_check.isChecked(),
                "auto_detect_code_language": self.auto_detect_code_language_check.isChecked(),
                "enable_code_lexing": self.enable_code_lexing_check.isChecked(),
                "enable_debug_commands": self.enable_debug_commands_check.isChecked(),
                "enable_ai_intent_classification": self.enable_ai_intent_check.isChecked(),
                "ai_intent_confidence_threshold": self.ai_intent_threshold_slider.value() / 100.0,
                "ai_intent_timeout_seconds": 5  # Fixed value for now
            },
            "screen_capture": {
                "default_save_path": self.screen_capture_path_edit.text().strip(),
                "border_color": getattr(self, '_current_border_color', '#FF0000')
            },
            "tools": {
                "enabled": self.tools_enabled_check.isChecked(),
                "max_tool_iterations": self.tools_max_iterations_spin.value(),
                "web_search": {
                    "enabled": self.web_search_enabled_check.isChecked(),
                    "max_results": self.web_search_max_results_spin.value(),
                    "tavily_api_key": self.tavily_api_key_edit.text().strip()
                },
                "docx_formatter": {
                    "enabled": self.docx_enabled_check.isChecked(),
                    "default_font": self.docx_font_combo.currentText(),
                    "default_font_size": self.docx_font_size_spin.value(),
                    "line_spacing": self.docx_line_spacing_spin.value(),
                    "margins": {
                        "top": self.docx_margin_top_spin.value(),
                        "bottom": self.docx_margin_bottom_spin.value(),
                        "left": self.docx_margin_left_spin.value(),
                        "right": self.docx_margin_right_spin.value()
                    },
                    "default_operations": self._get_docx_operations()
                }
            },
            "avatar": {
                "selected": getattr(self, '_selected_avatar_id', 'specter'),
                "scale": getattr(self, '_avatar_scale_slider', None) and self._avatar_scale_slider.value() / 100.0 or 1.0
            }
        }
    
    def _apply_config_to_ui(self, config: Dict[str, Any]):
        """Apply configuration to UI elements."""
        # AI Settings
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

        # Icon size
        if "icon_size" in interface_config:
            try:
                icon_size = int(interface_config["icon_size"])
                if not (1 <= icon_size <= 10):
                    icon_size = 5
                self.icon_size_slider.setValue(icon_size)
                self.icon_size_label.setText(str(icon_size))
            except (ValueError, TypeError):
                self.icon_size_slider.setValue(5)  # default
                self.icon_size_label.setText("5")

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

        # Guard: loading fonts programmatically, don't mark as user-customized
        self._loading_fonts = True
        try:
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
        finally:
            self._loading_fonts = False

        # Load font customization flag
        self._fonts_user_customized = fonts_config.get("user_customized", False)
        
        # Advanced settings
        advanced_config = config.get("advanced", {})
        if "log_level" in advanced_config:
            # Map old debug settings to new simplified mode
            old_value = str(advanced_config["log_level"])
            if old_value.upper() == "DEBUG" or advanced_config.get("enable_debug", False):
                self.log_level_combo.setCurrentText("Detailed")
            else:
                self.log_level_combo.setCurrentText("Standard")
        
        if "log_location" in advanced_config:
            log_location = str(advanced_config["log_location"]).strip()
            if log_location:
                self.log_location_edit.setText(log_location)
                self.log_location_edit.setReadOnly(False)
            else:
                self._use_default_log_location()
        
        if "log_retention_days" in advanced_config:
            try:
                retention_days = int(advanced_config["log_retention_days"])
                if 1 <= retention_days <= 365:
                    self.log_retention_spin.setValue(retention_days)
                else:
                    self.log_retention_spin.setValue(10)  # default
            except (ValueError, TypeError):
                self.log_retention_spin.setValue(10)  # default
        
        if "ignore_ssl_verification" in advanced_config:
            self.ignore_ssl_check.setChecked(bool(advanced_config["ignore_ssl_verification"]))
        
        if "auto_detect_code_language" in advanced_config:
            self.auto_detect_code_language_check.setChecked(bool(advanced_config["auto_detect_code_language"]))
        
        if "enable_code_lexing" in advanced_config:
            self.enable_code_lexing_check.setChecked(bool(advanced_config["enable_code_lexing"]))
        
        if "enable_debug_commands" in advanced_config:
            self.enable_debug_commands_check.setChecked(bool(advanced_config["enable_debug_commands"]))

        # AI Intent Classification settings
        if "enable_ai_intent_classification" in advanced_config:
            self.enable_ai_intent_check.setChecked(bool(advanced_config["enable_ai_intent_classification"]))

        if "ai_intent_confidence_threshold" in advanced_config:
            threshold_value = int(advanced_config["ai_intent_confidence_threshold"] * 100)
            self.ai_intent_threshold_slider.setValue(threshold_value)

        # Screen Capture settings
        screen_capture_config = config.get("screen_capture", {})
        if "default_save_path" in screen_capture_config:
            self.screen_capture_path_edit.setText(str(screen_capture_config["default_save_path"]))
        if "border_color" in screen_capture_config:
            border_color = str(screen_capture_config["border_color"])
            self._set_border_color(border_color)

        # Tools settings
        tools_config = config.get("tools", {})
        if tools_config:
            self.tools_enabled_check.setChecked(tools_config.get("enabled", True))
            self.tools_max_iterations_spin.setValue(tools_config.get("max_tool_iterations", 5))

            ws = tools_config.get("web_search", {})
            self.web_search_enabled_check.setChecked(ws.get("enabled", True))
            self.web_search_max_results_spin.setValue(ws.get("max_results", 5))
            tavily_key = ws.get("tavily_api_key", "")
            if tavily_key and isinstance(tavily_key, str) and tavily_key.strip():
                self.web_search_provider_combo.setCurrentIndex(1)  # Tavily
                self.tavily_api_key_edit.setText(tavily_key)
            else:
                self.web_search_provider_combo.setCurrentIndex(0)  # DuckDuckGo

            df = tools_config.get("docx_formatter", {})
            self.docx_enabled_check.setChecked(df.get("enabled", True))
            font_index = self.docx_font_combo.findText(df.get("default_font", "Calibri"))
            if font_index >= 0:
                self.docx_font_combo.setCurrentIndex(font_index)
            self.docx_font_size_spin.setValue(df.get("default_font_size", 11))
            self.docx_line_spacing_spin.setValue(df.get("line_spacing", 1.15))

            margins = df.get("margins", {})
            self.docx_margin_top_spin.setValue(margins.get("top", 1.0))
            self.docx_margin_bottom_spin.setValue(margins.get("bottom", 1.0))
            self.docx_margin_left_spin.setValue(margins.get("left", 1.0))
            self.docx_margin_right_spin.setValue(margins.get("right", 1.0))

            operations = df.get("default_operations", [])
            self.docx_op_fonts_check.setChecked("standardize_fonts" in operations)
            self.docx_op_margins_check.setChecked("fix_margins" in operations)
            self.docx_op_spacing_check.setChecked("normalize_spacing" in operations)
            self.docx_op_bullets_check.setChecked("fix_bullets" in operations)
            self.docx_op_spelling_check.setChecked("fix_spelling" in operations)
            self.docx_op_case_check.setChecked("fix_case" in operations)
            self.docx_op_headings_check.setChecked("normalize_headings" in operations)

        # Avatar settings
        avatar_config = config.get("avatar", {})
        selected_id = avatar_config.get("selected", "specter")
        if hasattr(self, '_avatar_cards'):
            self._on_avatar_card_clicked(selected_id)
        scale = avatar_config.get("scale", 1.0)
        if hasattr(self, '_avatar_scale_slider'):
            self._avatar_scale_slider.setValue(int(scale * 100))

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
                    logger.info("✓ Settings applied to UI successfully")
                else:
                    logger.info("📦 No existing settings found in storage")
                    self._set_default_values()
            except Exception as e:
                logger.error(f"✗ Failed to load settings from storage: {e}")
                self._set_default_values()
        else:
            logger.warning("⚠  No settings manager available - using defaults")
            self._set_default_values()
        
        logger.info("=== 📥 SETTINGS LOADING COMPLETE ===")
        logger.info("")  # Add blank line for readability
    
    def _set_default_values(self):
        """Set default values when no settings are available."""
        logger.info("🔧 Setting default values...")
        # Set default user prompt (purely identity/role, no behavioral or formatting instructions)
        default_user_prompt = "Your name is Spector, a friendly ghost AI assistant that helps with anything - be friendly, courteous, and a tadbit sassy!"
        self.user_prompt_edit.setPlainText(default_user_prompt)
        logger.info(f"📝 Set default user prompt (length: {len(default_user_prompt)})")
        logger.info(f"🎨 Using default opacity: {self.opacity_percent_spin.value()}%")
        
        # Set default log settings
        self._use_default_log_location()
        self.log_retention_spin.setValue(10)  # Default 10 days
        logger.info(f"📁 Using default log settings: retention={self.log_retention_spin.value()} days")
        
        # Reset avatar to default
        if hasattr(self, '_avatar_cards'):
            self._on_avatar_card_clicked('specter')
        if hasattr(self, '_avatar_scale_slider'):
            self._avatar_scale_slider.setValue(100)

        # Reset font customization flag
        self._fonts_user_customized = False

        logger.info("✓ Default values set")
    
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
            logger.info(f"🤖 AI Settings config: {model_name} at {base_url}")
        
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
                    logger.info(f"  ✓ Saved category: {category} ({len(settings)} items)")
                    saved_count += 1
                except Exception as e:
                    logger.error(f"  ✗ Failed to save category {category}: {e}")
            logger.info(f"💾 Settings storage complete: {saved_count} categories saved")
        else:
            logger.warning("⚠  No settings manager available - settings not persisted")
        
        # Update font service with new font settings
        if "fonts" in config:
            fonts_config = config["fonts"]
            if "ai_response" in fonts_config:
                ai_font = fonts_config["ai_response"]
                font_service.update_font_config('ai_response', **ai_font)
            if "user_input" in fonts_config:
                user_font = fonts_config["user_input"]
                font_service.update_font_config('user_input', **user_font)
            logger.info("✓ Font service updated with new font settings")
        
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
        logger.info("=== ✓ SETTINGS APPLICATION COMPLETE ===")
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
            
            # Update PKI widget theme if it exists
            if hasattr(self, 'pki_widget') and self.pki_widget:
                self.pki_widget._apply_theme_styling()
            
            # Update PKI placeholder theme if it exists
            if hasattr(self, 'pki_placeholder') and self.pki_placeholder:
                self._apply_pki_placeholder_theme(theme_manager.current_theme)

            # Update font preview labels to match new theme
            if hasattr(self, 'ai_preview_label') and self.ai_preview_label:
                self._apply_preview_label_style(self.ai_preview_label)
            if hasattr(self, 'user_preview_label') and self.user_preview_label:
                self._apply_preview_label_style(self.user_preview_label)

            # Update button styles to match new theme
            self._apply_uniform_button_styles()

            logger.debug(f"Applied theme: {theme_manager.current_theme_name}")
        except ImportError:
            logger.warning("Theme system not available, using fallback dark theme")
            self._apply_fallback_theme()

    def _get_status_color(self, color_attr: str, fallback: str) -> str:
        """Get a theme-aware status color with a fallback value.

        Args:
            color_attr: The ColorSystem attribute name (e.g. 'status_error').
            fallback: The fallback CSS color if the theme system is unavailable.

        Returns:
            The resolved color string.
        """
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            if theme_manager and hasattr(theme_manager, 'current_theme'):
                colors = theme_manager.current_theme
                if hasattr(colors, color_attr):
                    return getattr(colors, color_attr)
        except Exception:
            pass
        return fallback

    def _apply_fallback_theme(self):
        """Apply fallback dark theme styling when theme system is not available."""
        # Update PKI placeholder with fallback theme if it exists
        if hasattr(self, 'pki_placeholder') and self.pki_placeholder:
            self.pki_placeholder.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            """)
        
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
                min-height: 24px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #4CAF50;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                height: 14px;
                border-left: 1px solid #555555;
                border-bottom: 1px solid #555555;
                border-top-right-radius: 4px;
                background-color: #3c3c3c;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
                background-color: #4CAF50;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #ffffff;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: padding;
                subcontrol-position: bottom right;
                width: 24px;
                height: 14px;
                border-left: 1px solid #555555;
                border-top: 1px solid #555555;
                border-bottom-right-radius: 4px;
                background-color: #3c3c3c;
            }
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #4CAF50;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #ffffff;
                width: 0px;
                height: 0px;
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


class ModelsDialog(QDialog):
    """Dialog for displaying and selecting available AI models from an API endpoint."""
    
    model_selected = pyqtSignal(str)  # Emitted when a model is selected
    loading_finished = pyqtSignal()   # Emitted when models loading completes
    
    def __init__(self, base_url: str, api_key: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key
        self.models = []
        
        self.setWindowTitle("Available Models")
        self.setModal(True)
        self.resize(400, 500)
        
        self._init_ui()
        self._apply_theme()
        
        # Defer the network request until after the dialog is shown
        # This allows the parent's spinner to start animating before the blocking network request
        # Alternative: For long-running requests, consider using QThread instead
        QTimer.singleShot(50, self._load_models)
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Select a model from the API endpoint:")
        layout.addWidget(header_label)
        
        # Status label
        self.status_label = QLabel("Loading models...")
        layout.addWidget(self.status_label)
        
        # Models list
        self.models_list = QListWidget()
        self.models_list.itemDoubleClicked.connect(self._on_model_double_clicked)
        self.models_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.models_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_models(self):
        """Load models from the API endpoint using session manager."""
        try:
            # Determine the models endpoint based on the base URL
            models_url = self._get_models_endpoint()
            
            if models_url is None:
                # Handle APIs without models endpoint (like Anthropic)
                self._load_predefined_models()
                self.loading_finished.emit()
                return
            
            # Import session manager and SSL service
            from ...infrastructure.ai.session_manager import session_manager
            from ...infrastructure.ssl.ssl_service import ssl_service
            from ...infrastructure.storage.settings_manager import settings

            # Configure SSL service from settings
            try:
                ssl_service.configure_from_settings(settings.get_all_settings())
                ssl_service.configure_session_manager()
            except Exception as ssl_e:
                logger.warning(f"Failed to configure SSL service, using defaults: {ssl_e}")

            # Configure session manager (SSL already configured via ssl_service)
            session_manager.configure_session(
                timeout=10,
                max_retries=2
            )
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make request using session manager
            response = session_manager.make_request(
                method="GET",
                url=models_url,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self._parse_models_response(data)
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            error_message = self._get_user_friendly_error(e)
            self.status_label.setText(error_message)
            error_color = self._get_status_color("status_error", "red")
            self.status_label.setStyleSheet(f"color: {error_color};")
        finally:
            # Always emit loading finished, whether success or error
            self.loading_finished.emit()
    
    def _get_user_friendly_error(self, error: Exception) -> str:
        """Convert technical error to user-friendly message."""
        error_str = str(error).lower()
        
        # Connection errors
        if "connection" in error_str or "network" in error_str or "timeout" in error_str:
            return "❌ Connection failed - Check your internet connection and Base URL"
        
        # Authentication errors  
        if "401" in error_str or "unauthorized" in error_str or "authentication" in error_str:
            return "🔑 Authentication failed - Check your API key"
        
        # Forbidden access
        if "403" in error_str or "forbidden" in error_str:
            return "🚫 Access denied - Your API key may not have permission"
        
        # Rate limiting
        if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return "⏳ Rate limited - Too many requests, please wait and try again"
        
        # Server errors
        if "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
            return "🔧 Server error - The API service is experiencing issues"
        
        # Invalid URL
        if "invalid url" in error_str or "malformed" in error_str:
            return "🔗 Invalid Base URL - Please check the URL format"
        
        # SSL/TLS errors
        if "ssl" in error_str or "certificate" in error_str:
            return "🔒 SSL certificate error - Check HTTPS settings"
        
        # API not found
        if "404" in error_str or "not found" in error_str:
            return "❓ API endpoint not found - Check your Base URL"
        
        # JSON parsing errors
        if "json" in error_str or "decode" in error_str:
            return "📄 Invalid response format - API returned unexpected data"
        
        # Generic fallback with truncated message
        if len(str(error)) > 80:
            return f"❌ Error: {str(error)[:80]}... (see logs for details)"
        else:
            return f"❌ Error: {str(error)}"
    
    def _get_models_endpoint(self) -> str:
        """Get the appropriate models endpoint for the API."""
        base_url = self.base_url.rstrip('/')
        
        # Handle different API providers
        if 'openai.com' in base_url or 'openrouter.ai' in base_url:
            return f"{base_url}/models"
        elif 'anthropic.com' in base_url:
            # Anthropic doesn't have a public models endpoint, use predefined list
            return None
        elif 'localhost' in base_url or '127.0.0.1' in base_url:
            # Local APIs (Ollama, LM Studio, etc.)
            return f"{base_url}/models"
        else:
            # Default to OpenAI-compatible endpoint
            return f"{base_url}/models"
    
    def _load_predefined_models(self):
        """Load predefined models for APIs without models endpoint."""
        base_url = self.base_url.rstrip('/')
        
        if 'anthropic.com' in base_url:
            # Anthropic Claude models
            self.models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022", 
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        else:
            # Generic fallback
            self.models = ["Ask user to check API documentation"]
        
        # Populate the list widget
        self.models_list.clear()
        for model in self.models:
            item = QListWidgetItem(model)
            self.models_list.addItem(item)
        
        self.status_label.setText(f"Showing {len(self.models)} predefined models")
        info_color = self._get_status_color("status_info", "blue")
        self.status_label.setStyleSheet(f"color: {info_color};")
    
    def _parse_models_response(self, data):
        """Parse the models response and populate the list."""
        try:
            if not data:
                raise ValueError("Empty response from API")
            
            # Handle different response formats
            if isinstance(data, dict):
                if 'data' in data:
                    # OpenAI/OpenRouter format
                    models_data = data['data']
                elif 'models' in data:
                    # Alternative format
                    models_data = data['models']
                else:
                    raise ValueError("Unexpected response format")
            elif isinstance(data, list):
                # Direct list format (some local APIs)
                models_data = data
            else:
                raise ValueError("Unexpected response format")
            
            # Extract model names
            self.models = []
            for model in models_data:
                if isinstance(model, dict):
                    model_id = model.get('id') or model.get('name') or model.get('model')
                    if model_id:
                        self.models.append(model_id)
                elif isinstance(model, str):
                    self.models.append(model)
            
            if not self.models:
                raise ValueError("No models found in response")
            
            # Sort models for better organization
            self.models.sort()
            
            # Populate the list widget
            self.models_list.clear()
            for model in self.models:
                item = QListWidgetItem(model)
                self.models_list.addItem(item)
            
            self.status_label.setText(f"Found {len(self.models)} models")
            success_color = self._get_status_color("status_success", "green")
            self.status_label.setStyleSheet(f"color: {success_color};")

        except Exception as e:
            logger.error(f"Failed to parse models response: {e}")
            self.status_label.setText(f"Error parsing models: {str(e)}")
            error_color = self._get_status_color("status_error", "red")
            self.status_label.setStyleSheet(f"color: {error_color};")
    
    def _on_model_double_clicked(self, item):
        """Handle double-click on a model item."""
        self._select_model(item.text())
    
    def _on_apply_clicked(self):
        """Handle apply button click."""
        current_item = self.models_list.currentItem()
        if current_item:
            self._select_model(current_item.text())
    
    def _select_model(self, model_name: str):
        """Select a model and emit the signal."""
        self.model_selected.emit(model_name)
        self.accept()
    
    def _on_selection_changed(self):
        """Handle list selection changes."""
        self.apply_btn.setEnabled(self.models_list.currentItem() is not None)
    
    def _apply_theme(self):
        """Apply current theme styling to the models dialog."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            from ...ui.themes.style_templates import StyleTemplates
            
            theme_manager = get_theme_manager()
            style = self._get_models_dialog_style(theme_manager.current_theme)
            self.setStyleSheet(style)
            logger.debug(f"Applied theme to ModelsDialog: {theme_manager.current_theme_name}")
        except ImportError:
            logger.warning("Theme system not available, using fallback dark theme")
            self._apply_fallback_theme()

    def _get_status_color(self, color_attr: str, fallback: str) -> str:
        """Get a theme-aware status color with a fallback value.

        Args:
            color_attr: The ColorSystem attribute name (e.g. 'status_error').
            fallback: The fallback CSS color if the theme system is unavailable.

        Returns:
            The resolved color string.
        """
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            if theme_manager and hasattr(theme_manager, 'current_theme'):
                colors = theme_manager.current_theme
                if hasattr(colors, color_attr):
                    return getattr(colors, color_attr)
        except Exception:
            pass
        return fallback

    def _apply_fallback_theme(self):
        """Apply fallback dark theme styling when theme system is not available."""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
    
    def _get_models_dialog_style(self, colors):
        """Generate comprehensive styling for the models dialog."""
        return f"""
        /* Main dialog styling */
        QDialog {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        
        /* Label styling */
        QLabel {{
            color: {colors.text_primary};
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        /* List widget styling */
        QListWidget {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors.separator};
        }}
        QListWidget::item:selected {{
            background-color: {colors.primary};
            color: {colors.background_primary};
        }}
        QListWidget::item:hover {{
            background-color: {colors.interactive_hover};
            color: {colors.text_primary};
        }}
        QListWidget::item:selected:hover {{
            background-color: {colors.primary_hover};
            color: {colors.background_primary};
            font-weight: bold;
        }}
        
        /* Button styling */
        QPushButton {{
            background-color: {colors.primary};
            color: {colors.background_primary};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 80px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {colors.primary_hover};
        }}
        QPushButton:pressed {{
            background-color: {colors.primary_hover};
        }}
        QPushButton:disabled {{
            background-color: {colors.interactive_disabled};
            color: {colors.text_disabled};
        }}
        """