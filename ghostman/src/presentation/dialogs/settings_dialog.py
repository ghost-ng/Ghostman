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
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add tabs
        self._create_ai_model_tab()
        self._create_interface_tab()
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
        
        # Update config path
        self._update_config_path_display()
    
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
                
                QMessageBox.information(self, "Success", f"Configuration saved to:\n{filename}")
                logger.info(f"Configuration saved to: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")
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
                
                QMessageBox.information(self, "Success", f"Configuration loaded from:\n{filename}")
                logger.info(f"Configuration loaded from: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load configuration:\n{str(e)}")
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
        
        # Emit signal with detailed config
        logger.info(f"📡 Emitting settings_applied signal with {len(config)} categories")
        logger.info("📡 Signal payload categories: " + ", ".join(config.keys()))
        self.settings_applied.emit(config)
        
        QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully.")
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