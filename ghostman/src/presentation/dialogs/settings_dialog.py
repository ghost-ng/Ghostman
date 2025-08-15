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
        
        logger.info("SettingsDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Spector Settings")
        self.setModal(True)
        self.resize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
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
        
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setMaximumHeight(100)
        self.system_prompt_edit.setPlaceholderText("System prompt for the AI assistant...")
        params_layout.addRow("System Prompt:", self.system_prompt_edit)
        
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

        # Percent-based opacity (store int percent 10-100)
        self.opacity_percent_spin = QSpinBox()
        self.opacity_percent_spin.setRange(10, 100)
        self.opacity_percent_spin.setSingleStep(1)
        self.opacity_percent_spin.setValue(90)
        self.opacity_percent_spin.valueChanged.connect(self._on_opacity_preview)
        appearance_layout.addRow("Panel Opacity (%):", self.opacity_percent_spin)

        self.always_on_top_check = QCheckBox("Always stay on top")
        self.always_on_top_check.setChecked(True)
        appearance_layout.addRow("", self.always_on_top_check)

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

        # AI Response Font Size
        self.ai_font_size_spin = QSpinBox()
        self.ai_font_size_spin.setRange(6, 72)
        self.ai_font_size_spin.setValue(11)
        ai_font_layout.addRow("Font Size:", self.ai_font_size_spin)

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

        # User Input Font Size
        self.user_font_size_spin = QSpinBox()
        self.user_font_size_spin.setRange(6, 72)
        self.user_font_size_spin.setValue(10)
        user_font_layout.addRow("Font Size:", self.user_font_size_spin)

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

        # Connect font change events to preview updates
        self.ai_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.ai_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.ai_font_style_combo.currentTextChanged.connect(self._update_font_previews)
        
        self.user_font_family_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_size_spin.valueChanged.connect(self._update_font_previews)
        self.user_font_weight_combo.currentTextChanged.connect(self._update_font_previews)
        self.user_font_style_combo.currentTextChanged.connect(self._update_font_previews)

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
        
        # Update config path
        self._update_config_path_display()
    
    def _create_theme_tab(self):
        """Create theme customization tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Theme selection group
        theme_group = QGroupBox("Theme Selection")
        theme_layout = QFormLayout()
        
        # Preset theme selector
        self.theme_selector = QComboBox()
        try:
            # Try to import theme manager
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            themes = theme_manager.get_available_themes()
            self.theme_selector.addItems(themes)
            self.theme_selector.setCurrentText(theme_manager.current_theme_name)
            self.theme_selector.currentTextChanged.connect(self._on_theme_selected)
        except ImportError:
            self.theme_selector.addItem("Theme system not available")
            self.theme_selector.setEnabled(False)
        
        theme_layout.addRow("Current Theme:", self.theme_selector)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Theme editor button
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
    
    def _on_theme_selected(self, theme_name: str):
        """Handle theme selection change."""
        try:
            from ...ui.themes.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            if theme_manager.set_theme(theme_name):
                logger.info(f"Theme changed to: {theme_name}")
                # Apply the new theme to this dialog as well
                self._apply_theme()
            else:
                logger.error(f"Failed to set theme: {theme_name}")
        except ImportError:
            logger.warning("Theme system not available")
    
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
                "system_prompt": self.system_prompt_edit.toPlainText()
            },
            "interface": {
                # Store as integer percent
                "opacity": int(self.opacity_percent_spin.value()),
                "always_on_top": self.always_on_top_check.isChecked(),
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
        if "system_prompt" in ai_config:
            self.system_prompt_edit.setPlainText(str(ai_config["system_prompt"]))
        
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
        if "always_on_top" in interface_config:
            # Convert string "True"/"False" to boolean
            value = interface_config["always_on_top"]
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes')
            self.always_on_top_check.setChecked(bool(value))
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
        # Set default system prompt
        default_prompt = "You are Spector, a helpful AI assistant integrated into a desktop overlay application. Be concise, friendly, and helpful."
        self.system_prompt_edit.setPlainText(default_prompt)
        logger.info(f"📝 Set default system prompt (length: {len(default_prompt)})")
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
            # Save to settings manager
            saved_count = 0
            for category, settings in config.items():
                for key, value in settings.items():
                    full_key = f"{category}.{key}"
                    try:
                        self.settings_manager.set(full_key, value)
                        display_value = "***MASKED***" if key == "api_key" and value else value
                        logger.info(f"  ✅ Saved: {full_key} = {display_value}")
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"  ❌ Failed to save {full_key}: {e}")
            logger.info(f"💾 Settings storage complete: {saved_count} items saved")
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