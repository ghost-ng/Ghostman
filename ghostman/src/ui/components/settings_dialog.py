"""Settings dialog for Ghostman configuration."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTabWidget, QWidget,
                             QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
                             QCheckBox, QGroupBox, QFormLayout, QMessageBox,
                             QFrame, QSlider, QFileDialog, QColorDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor
from services.ai_service import AIConfig, AIProvider
from ui.themes.theme_manager import ThemeManager, Theme
import logging
from typing import Optional
from pathlib import Path

class AISettingsWidget(QWidget):
    """AI configuration settings widget."""
    
    def __init__(self, ai_config: AIConfig, parent=None):
        super().__init__(parent)
        self.ai_config = ai_config
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        self.load_values()
    
    def setup_ui(self):
        """Setup the AI settings UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # API Configuration Group
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(10)
        
        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("OpenAI", AIProvider.OPENAI.value)
        api_layout.addRow("AI Provider:", self.provider_combo)
        
        # API Base URL
        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("https://api.openai.com/v1")
        self.api_base_input.setMinimumWidth(300)
        api_layout.addRow("API Base URL:", self.api_base_input)
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your API key...")
        self.api_key_input.setMinimumWidth(300)
        
        # Show/Hide API key button
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.api_key_input)
        
        self.show_key_btn = QPushButton("👁")
        self.show_key_btn.setMaximumWidth(30)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.clicked.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.show_key_btn)
        
        api_layout.addRow("API Key:", key_layout)
        
        # Test API key button
        self.test_key_btn = QPushButton("Test API Key")
        self.test_key_btn.clicked.connect(self.test_api_key)
        api_layout.addRow("", self.test_key_btn)
        
        layout.addWidget(api_group)
        
        # Model Configuration Group
        model_group = QGroupBox("Model Configuration")
        model_layout = QFormLayout(model_group)
        model_layout.setSpacing(10)
        
        # Model selection (fully editable for custom models)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # Add common models as suggestions
        common_models = [
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k", 
            "gpt-4", "gpt-4-turbo-preview", "gpt-4-0125-preview",
            "claude-3-haiku", "claude-3-sonnet", "claude-3-opus",
            "llama-2-7b-chat", "llama-2-13b-chat", "llama-2-70b-chat",
            "mistral-7b-instruct", "mixtral-8x7b-instruct",
            "gemini-pro", "gemini-ultra"
        ]
        
        for model in common_models:
            self.model_combo.addItem(model)
        
        model_layout.addRow("Model Name:", self.model_combo)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setMinimum(1)
        self.max_tokens_spin.setMaximum(4000)
        self.max_tokens_spin.setValue(1000)
        model_layout.addRow("Max Tokens per Response:", self.max_tokens_spin)
        
        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setMinimum(0.0)
        self.temperature_spin.setMaximum(2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(1)
        self.temperature_spin.setValue(0.7)
        model_layout.addRow("Temperature (Creativity):", self.temperature_spin)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(120)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        model_layout.addRow("Request Timeout:", self.timeout_spin)
        
        layout.addWidget(model_group)
        
        # Conversation Settings Group
        conv_group = QGroupBox("Conversation Settings")
        conv_layout = QFormLayout(conv_group)
        conv_layout.setSpacing(10)
        
        # Max conversation tokens
        self.max_conv_tokens_spin = QSpinBox()
        self.max_conv_tokens_spin.setMinimum(1000)
        self.max_conv_tokens_spin.setMaximum(16000)
        self.max_conv_tokens_spin.setValue(4000)
        conv_layout.addRow("Max Conversation Tokens:", self.max_conv_tokens_spin)
        
        layout.addWidget(conv_group)
        
        # Help text
        help_label = QLabel(
            "💡 <b>Tips:</b><br>"
            "• <b>API Base URL:</b> Use custom endpoints (OpenAI-compatible APIs like Ollama, LM Studio, etc.)<br>"
            "• <b>Model Name:</b> Type any model name your API supports (e.g., 'llama2', 'claude-3-opus')<br>"
            "• <b>API Key:</b> Get from <a href='https://platform.openai.com/api-keys'>OpenAI</a> or your provider<br>"
            "• <b>Temperature:</b> Higher = more creative, Lower = more focused<br>"
            "• <b>Test Connection:</b> Verify your settings work before saving"
        )
        help_label.setWordWrap(True)
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(70, 130, 180, 50);
                border: 1px solid rgba(70, 130, 180, 100);
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(help_label)
        
        layout.addStretch()
    
    def toggle_key_visibility(self, checked: bool):
        """Toggle API key visibility."""
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("🙈")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("👁")
    
    def test_api_key(self):
        """Test the API key."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter an API key to test.")
            return
        
        api_base = self.api_base_input.text().strip() or "https://api.openai.com/v1"
        model = self.model_combo.currentText().strip() or "gpt-3.5-turbo"
        
        # Show testing state
        original_text = self.test_key_btn.text()
        self.test_key_btn.setText("Testing...")
        self.test_key_btn.setEnabled(False)
        
        try:
            import openai
            
            # Set up client with custom base URL if needed
            client_kwargs = {'api_key': api_key}
            if api_base != "https://api.openai.com/v1":
                client_kwargs['base_url'] = api_base
            
            client = openai.OpenAI(**client_kwargs)
            
            # Test with a simple request using the specified model
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=10
            )
            
            QMessageBox.information(
                self, 
                "API Key Valid", 
                "✅ API key is valid and working!"
            )
            
        except openai.AuthenticationError:
            QMessageBox.critical(
                self,
                "Invalid API Key",
                "❌ The API key is invalid. Please check your key and try again."
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Test Failed", 
                f"⚠️ Could not test API key: {str(e)}\n\n"
                "This might be due to network issues or service unavailability."
            )
        finally:
            # Restore button
            self.test_key_btn.setText(original_text)
            self.test_key_btn.setEnabled(True)
    
    def load_values(self):
        """Load values from configuration."""
        # Set provider
        provider_index = self.provider_combo.findData(self.ai_config.provider.value)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        
        # Set other values
        self.api_base_input.setText(self.ai_config.api_base)
        self.api_key_input.setText(self.ai_config.api_key)
        self.model_combo.setCurrentText(self.ai_config.model)
        self.max_tokens_spin.setValue(self.ai_config.max_tokens)
        self.temperature_spin.setValue(self.ai_config.temperature)
        self.timeout_spin.setValue(self.ai_config.timeout)
        self.max_conv_tokens_spin.setValue(self.ai_config.max_conversation_tokens)
    
    def save_values(self) -> AIConfig:
        """Save values to configuration."""
        self.ai_config.provider = AIProvider(self.provider_combo.currentData())
        self.ai_config.api_base = self.api_base_input.text().strip() or "https://api.openai.com/v1"
        self.ai_config.api_key = self.api_key_input.text().strip()
        self.ai_config.model = self.model_combo.currentText().strip()
        self.ai_config.max_tokens = self.max_tokens_spin.value()
        self.ai_config.temperature = self.temperature_spin.value()
        self.ai_config.timeout = self.timeout_spin.value()
        self.ai_config.max_conversation_tokens = self.max_conv_tokens_spin.value()
        
        return self.ai_config

class AppearanceSettingsWidget(QWidget):
    """Appearance and theme configuration settings widget."""
    
    theme_changed = pyqtSignal(str)  # Emits theme name when changed
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.logger = logging.getLogger(__name__)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.setup_ui()
        self.load_values()
    
    def setup_ui(self):
        """Setup the appearance settings UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Theme Selection Group
        theme_group = QGroupBox("Theme Selection")
        theme_layout = QFormLayout(theme_group)
        theme_layout.setSpacing(10)
        
        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.currentTextChanged.connect(self.on_theme_selected)
        
        # Add built-in themes
        builtin_themes = self.theme_manager.get_all_builtin_themes()
        for theme_name, theme in builtin_themes.items():
            self.theme_combo.addItem(f"{theme.name} (Built-in)", theme_name)
        
        # Add custom themes
        for theme_name, theme in self.theme_manager.custom_themes.items():
            self.theme_combo.addItem(f"{theme.name} (Custom)", theme_name)
        
        theme_layout.addRow("Current Theme:", self.theme_combo)
        
        # Theme preview frame
        self.preview_frame = QFrame()
        self.preview_frame.setFixedHeight(80)
        self.preview_frame.setFrameStyle(QFrame.Shape.Box)
        theme_layout.addRow("Preview:", self.preview_frame)
        
        # Theme management buttons
        theme_buttons = QHBoxLayout()
        
        self.import_btn = QPushButton("Import Theme")
        self.import_btn.clicked.connect(self.import_theme)
        theme_buttons.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export Theme")
        self.export_btn.clicked.connect(self.export_theme)
        theme_buttons.addWidget(self.export_btn)
        
        self.create_btn = QPushButton("Create Custom")
        self.create_btn.clicked.connect(self.create_custom_theme)
        theme_buttons.addWidget(self.create_btn)
        
        theme_buttons.addStretch()
        theme_layout.addRow("", theme_buttons)
        
        layout.addWidget(theme_group)
        
        # Theme Customization Group (for custom themes)
        self.custom_group = QGroupBox("Theme Customization")
        custom_layout = QFormLayout(self.custom_group)
        custom_layout.setSpacing(10)
        
        # Primary color
        self.primary_color_btn = QPushButton()
        self.primary_color_btn.setFixedHeight(30)
        self.primary_color_btn.clicked.connect(lambda: self.select_color('primary'))
        custom_layout.addRow("Primary Color:", self.primary_color_btn)
        
        # Background opacity
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(50)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(85)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("85%")
        opacity_layout.addWidget(self.opacity_label)
        
        custom_layout.addRow("Window Opacity:", opacity_layout)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(10)
        self.font_size_spin.setMaximum(20)
        self.font_size_spin.setValue(13)
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)
        custom_layout.addRow("Font Size:", self.font_size_spin)
        
        layout.addWidget(self.custom_group)
        
        # Help text
        help_label = QLabel(
            "🎨 <b>Theme Tips:</b><br>"
            "• <b>Built-in Themes:</b> Dark, Light, Neon, Ocean, Forest<br>"
            "• <b>Custom Themes:</b> Create your own or import from files<br>"
            "• <b>Preview:</b> See colors change in real-time<br>"
            "• <b>Export:</b> Share your custom themes with others<br>"
            "• <b>Import:</b> Load themes from .json files"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(135, 206, 235, 50);
                border: 1px solid rgba(135, 206, 235, 100);
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(help_label)
        
        layout.addStretch()
        
        # Initially hide custom group
        self.update_custom_controls_visibility()
    
    def load_values(self):
        """Load values from theme manager."""
        # Set current theme in combo box
        current_theme = self.theme_manager.current_theme
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme.name.lower():
                self.theme_combo.setCurrentIndex(i)
                break
        
        self.update_preview()
        self.update_custom_controls()
    
    def on_theme_selected(self, theme_display_name: str):
        """Handle theme selection."""
        if not theme_display_name:
            return
            
        # Get the theme data from the combo box
        current_index = self.theme_combo.currentIndex()
        theme_key = self.theme_combo.itemData(current_index)
        
        if theme_key:
            self.theme_changed.emit(theme_key)
            self.preview_timer.start(200)  # Delay preview update
            self.update_custom_controls_visibility()
            self.update_custom_controls()
    
    def update_preview(self):
        """Update the theme preview."""
        try:
            if not self.theme_manager:
                return
                
            theme = self.theme_manager.current_theme
            colors = theme.colors
            
            # Create a sample preview with theme colors
            style = f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {colors.background}, 
                        stop:0.5 {colors.background_light}, 
                        stop:1 {colors.background_dark});
                    border: 2px solid {colors.primary};
                    border-radius: 8px;
                }}
            """
            self.preview_frame.setStyleSheet(style)
            
            # Add preview labels if not already present
            if not self.preview_frame.findChildren(QLabel):
                preview_layout = QHBoxLayout(self.preview_frame)
                preview_layout.setContentsMargins(10, 5, 10, 5)
                
                # Sample elements with theme colors
                user_msg = QLabel("User message")
                user_msg.setStyleSheet(f"""
                    background-color: {colors.user_message_bg};
                    color: {colors.user_message_text};
                    padding: 5px;
                    border-radius: 5px;
                    font-size: 11px;
                """)
                
                ai_msg = QLabel("AI response")
                ai_msg.setStyleSheet(f"""
                    background-color: {colors.ai_message_bg};
                    color: {colors.ai_message_text};
                    padding: 5px;
                    border-radius: 5px;
                    font-size: 11px;
                """)
                
                preview_layout.addWidget(user_msg)
                preview_layout.addWidget(ai_msg)
                preview_layout.addStretch()
        
        except Exception as e:
            self.logger.error(f"Error updating preview: {e}")
    
    def update_custom_controls_visibility(self):
        """Show/hide custom controls based on theme type."""
        if not self.theme_manager or not hasattr(self, 'custom_group'):
            return
            
        current_theme = self.theme_manager.current_theme
        is_custom = hasattr(current_theme, 'mode') and current_theme.mode.value == 'custom'
        self.custom_group.setVisible(is_custom)
    
    def update_custom_controls(self):
        """Update custom controls with current theme values."""
        if not self.theme_manager:
            return
            
        theme = self.theme_manager.current_theme
        colors = theme.colors
        fonts = theme.fonts
        
        # Update primary color button
        self.update_color_button(self.primary_color_btn, colors.primary)
        
        # Update font size
        self.font_size_spin.setValue(fonts.size_normal)
    
    def update_color_button(self, button: QPushButton, color_hex: str):
        """Update a color button's appearance."""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                border: 2px solid #ccc;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #999;
            }}
        """)
        button.setText(color_hex)
    
    def select_color(self, color_type: str):
        """Open color picker for a specific color type."""
        if not self.theme_manager:
            return
            
        current_color = getattr(self.theme_manager.current_theme.colors, color_type)
        color = QColorDialog.getColor(QColor(current_color), self, f"Select {color_type.title()} Color")
        
        if color.isValid():
            color_hex = color.name()
            setattr(self.theme_manager.current_theme.colors, color_type, color_hex)
            self.update_color_button(self.primary_color_btn, color_hex)
            self.preview_timer.start(200)
    
    def on_opacity_changed(self, value: int):
        """Handle opacity slider changes."""
        self.opacity_label.setText(f"{value}%")
        # This would need to be implemented to modify background opacity
    
    def on_font_size_changed(self, value: int):
        """Handle font size changes."""
        if self.theme_manager:
            self.theme_manager.current_theme.fonts.size_normal = value
            self.preview_timer.start(200)
    
    def import_theme(self):
        """Import a theme from file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Theme",
                str(Path.home()),
                "Theme Files (*.json);;All Files (*)"
            )
            
            if file_path:
                theme = self.theme_manager.import_theme(Path(file_path))
                if theme:
                    # Refresh combo box
                    self.refresh_theme_list()
                    QMessageBox.information(self, "Import Success", f"Theme '{theme.name}' imported successfully!")
                else:
                    QMessageBox.warning(self, "Import Failed", "Failed to import theme. Please check the file format.")
        
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error importing theme: {str(e)}")
    
    def export_theme(self):
        """Export current theme to file."""
        try:
            current_theme = self.theme_manager.current_theme
            default_filename = f"{current_theme.name.lower()}_theme.json"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Theme",
                str(Path.home() / default_filename),
                "Theme Files (*.json);;All Files (*)"
            )
            
            if file_path:
                if self.theme_manager.export_theme(current_theme.name, Path(file_path)):
                    QMessageBox.information(self, "Export Success", f"Theme exported to {file_path}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export theme.")
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting theme: {str(e)}")
    
    def create_custom_theme(self):
        """Create a new custom theme."""
        try:
            from PyQt6.QtWidgets import QInputDialog
            
            name, ok = QInputDialog.getText(self, "Create Custom Theme", "Enter theme name:")
            if ok and name.strip():
                theme = self.theme_manager.create_custom_theme(name.strip())
                self.refresh_theme_list()
                
                # Select the new theme
                for i in range(self.theme_combo.count()):
                    if self.theme_combo.itemData(i) == name.strip():
                        self.theme_combo.setCurrentIndex(i)
                        break
                
                QMessageBox.information(self, "Theme Created", f"Custom theme '{name}' created successfully!")
        
        except Exception as e:
            QMessageBox.critical(self, "Creation Error", f"Error creating theme: {str(e)}")
    
    def refresh_theme_list(self):
        """Refresh the theme combo box."""
        current_selection = self.theme_combo.currentData()
        
        self.theme_combo.clear()
        
        # Add built-in themes
        builtin_themes = self.theme_manager.get_all_builtin_themes()
        for theme_name, theme in builtin_themes.items():
            self.theme_combo.addItem(f"{theme.name} (Built-in)", theme_name)
        
        # Add custom themes
        for theme_name, theme in self.theme_manager.custom_themes.items():
            self.theme_combo.addItem(f"{theme.name} (Custom)", theme_name)
        
        # Restore selection
        if current_selection:
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i) == current_selection:
                    self.theme_combo.setCurrentIndex(i)
                    break

class SettingsDialog(QDialog):
    """Main settings dialog."""
    
    settings_saved = pyqtSignal(dict)  # Emits the updated settings
    theme_changed = pyqtSignal(str)  # Emits theme name when changed
    
    def __init__(self, ai_config: AIConfig, theme_manager: Optional[ThemeManager] = None, parent=None):
        super().__init__(parent)
        self.ai_config = ai_config
        self.theme_manager = theme_manager
        self.logger = logging.getLogger(__name__)
        
        self.setWindowTitle("Ghostman Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        # Set window flags for proper behavior
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the settings dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("⚙️ Ghostman Settings")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #333;
                margin: 10px 0px;
            }
        """)
        layout.addWidget(title)
        
        # Tab widget for different settings categories
        self.tabs = QTabWidget()
        
        # AI Settings tab
        self.ai_settings = AISettingsWidget(self.ai_config)
        self.tabs.addTab(self.ai_settings, "🤖 AI Settings")
        
        # Appearance Settings tab
        if self.theme_manager:
            self.appearance_settings = AppearanceSettingsWidget(self.theme_manager)
            self.appearance_settings.theme_changed.connect(self.on_theme_changed)
            self.tabs.addTab(self.appearance_settings, "🎨 Appearance")
        
        # Future: Add more tabs here (Shortcuts, Behavior, etc.)
        
        layout.addWidget(self.tabs)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Reset to defaults button
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # Save button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def reset_to_defaults(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?\n\n"
            "This will clear your API key and other configurations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset AI config to defaults
            default_config = AIConfig()
            self.ai_config = default_config
            self.ai_settings.ai_config = default_config
            self.ai_settings.load_values()
            
            QMessageBox.information(
                self,
                "Settings Reset",
                "Settings have been reset to default values."
            )
    
    def save_settings(self):
        """Save the settings."""
        try:
            # Get updated AI config
            updated_ai_config = self.ai_settings.save_values()
            
            # Validate configuration
            if not updated_ai_config.api_key.strip():
                reply = QMessageBox.question(
                    self,
                    "No API Key",
                    "You haven't entered an API key. The AI features won't work without it.\n\n"
                    "Do you want to save the settings anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Emit settings updated signal
            settings_dict = {
                'ai_config': updated_ai_config
            }
            self.settings_saved.emit(settings_dict)
            
            # Show success message
            QMessageBox.information(
                self,
                "Settings Saved",
                "✅ Settings have been saved successfully!"
            )
            
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )
    
    def on_theme_changed(self, theme_name: str):
        """Handle theme changes from appearance settings."""
        try:
            self.theme_changed.emit(theme_name)
            self.logger.info(f"Theme change requested: {theme_name}")
        except Exception as e:
            self.logger.error(f"Error handling theme change: {e}")
    
    def closeEvent(self, event):
        """Handle close event."""
        self.logger.debug("Settings dialog closed")
        super().closeEvent(event)