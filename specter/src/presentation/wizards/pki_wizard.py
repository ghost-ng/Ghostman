"""
PKI Setup Wizard for Specter.

Provides a user-friendly wizard for setting up PKI authentication
with enterprise certificate management.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QRadioButton,
    QGroupBox, QFileDialog, QProgressBar, QScrollArea,
    QFrame, QButtonGroup, QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPixmap, QIcon

from ...infrastructure.pki import pki_service, PKIError

logger = logging.getLogger("specter.pki.wizard")

# Check if theme system is available
try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    logger.debug("Theme system not available - using default styling")


class PKISetupWizard(QWizard):
    """
    PKI Setup Wizard for configuring enterprise authentication.
    
    Provides a step-by-step process to:
    1. Choose PKI mode (Enterprise vs Standard)
    2. Import P12 certificate files
    3. Configure certificate chain
    4. Validate and test configuration
    5. Complete setup
    """
    
    # Wizard pages
    PAGE_WELCOME = 0
    PAGE_MODE_SELECTION = 1
    PAGE_P12_IMPORT = 2
    PAGE_CERTIFICATE_CHAIN = 3
    PAGE_VALIDATION = 4
    PAGE_SUMMARY = 5
    
    # Signals
    pki_configured = pyqtSignal(bool)  # True if PKI enabled, False if disabled
    
    def __init__(self, parent=None):
        """Initialize PKI setup wizard."""
        super().__init__(parent)
        
        self.setWindowTitle("Specter - PKI Authentication Setup")
        self.setWindowIcon(QIcon())  # You can set your app icon here
        self.resize(600, 500)
        
        # Wizard configuration
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.setOption(QWizard.WizardOption.CancelButtonOnLeft, True)
        
        # Theme manager
        self.theme_manager = None
        if THEME_SYSTEM_AVAILABLE:
            try:
                self.theme_manager = get_theme_manager()
            except Exception as e:
                logger.warning(f"Failed to get theme manager: {e}")
        
        # Setup data storage
        self.wizard_data: Dict[str, Any] = {
            'pki_mode': None,  # 'enterprise' or 'standard'
            'p12_file_path': None,
            'p12_password': None,
            'ca_chain_path': None,
            'test_url': None,
            'validation_results': None
        }
        
        self._setup_pages()
        self._apply_styling()
        
        logger.info("PKI Setup Wizard initialized")
    
    def _setup_pages(self):
        """Setup all wizard pages."""
        self.addPage(WelcomePage(self))
        self.addPage(ModeSelectionPage(self))
        self.addPage(P12ImportPage(self))
        self.addPage(CertificateChainPage(self))
        self.addPage(ValidationPage(self))
        self.addPage(SummaryPage(self))
    
    def _apply_styling(self):
        """Apply consistent styling to the wizard."""
        if self.theme_manager and THEME_SYSTEM_AVAILABLE:
            try:
                colors = self.theme_manager.current_theme
                self._apply_theme_colors(colors)
            except Exception as e:
                logger.warning(f"Failed to apply theme colors: {e}")
                self._apply_default_styling()
        else:
            self._apply_default_styling()
    
    def _apply_theme_colors(self, colors):
        """Apply theme-based colors to the wizard."""
        style = f"""
        QWizard {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        
        QWizardPage {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
        }}
        
        QLabel {{
            color: {colors.text_primary};
            font-size: 11px;
        }}
        
        QLabel[role="title"] {{
            color: {colors.text_primary};
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        QLabel[role="subtitle"] {{
            color: {colors.text_secondary};
            font-size: 12px;
            margin-bottom: 15px;
        }}

        QLabel[role="option_desc"] {{
            color: {colors.text_secondary};
            font-size: 10px;
            margin-left: 20px;
        }}

        QPushButton {{
            background-color: {colors.interactive_normal};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 11px;
        }}
        
        QPushButton:hover {{
            background-color: {colors.interactive_hover};
        }}
        
        QPushButton:pressed {{
            background-color: {colors.interactive_active};
        }}
        
        QLineEdit {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            padding: 6px;
            border-radius: 3px;
            font-size: 11px;
        }}
        
        QLineEdit:focus {{
            border-color: {colors.primary};
        }}
        
        QTextEdit {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            padding: 6px;
            border-radius: 3px;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        
        QRadioButton {{
            color: {colors.text_primary};
            font-size: 11px;
            spacing: 8px;
        }}

        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid {colors.border_primary};
            background-color: {colors.background_tertiary};
        }}

        QRadioButton::indicator:checked {{
            background-color: {colors.primary};
            border: 2px solid {colors.primary};
        }}

        QRadioButton::indicator:hover {{
            border-color: {colors.interactive_hover};
        }}
        
        QGroupBox {{
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
        }}
        
        QProgressBar {{
            border: 1px solid {colors.border_primary};
            border-radius: 3px;
            text-align: center;
            font-size: 10px;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors.primary};
            border-radius: 2px;
        }}
        """
        self.setStyleSheet(style)
    
    def _apply_default_styling(self):
        """Apply default styling when theme system is not available."""
        style = """
        QWizard {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QWizardPage {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QLabel {
            color: #ffffff;
            font-size: 11px;
        }
        
        QLabel[role="title"] {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        QLabel[role="subtitle"] {
            color: #cccccc;
            font-size: 12px;
            margin-bottom: 15px;
        }

        QLabel[role="option_desc"] {
            color: #cccccc;
            font-size: 10px;
            margin-left: 20px;
        }

        QPushButton {
            background-color: #404040;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 11px;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #353535;
        }
        
        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 6px;
            border-radius: 3px;
            font-size: 11px;
        }
        
        QLineEdit:focus {
            border-color: #0078d4;
        }
        
        QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 6px;
            border-radius: 3px;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        
        QRadioButton {
            color: #ffffff;
            font-size: 11px;
            spacing: 8px;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid #555555;
            background-color: #3c3c3c;
        }

        QRadioButton::indicator:checked {
            background-color: #0078d4;
            border: 2px solid #0078d4;
        }

        QRadioButton::indicator:hover {
            border-color: #1e90ff;
        }
        
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
        }
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 3px;
            text-align: center;
            font-size: 10px;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 2px;
        }
        """
        self.setStyleSheet(style)


class WelcomePage(QWizardPage):
    """Welcome page for PKI setup wizard."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Welcome to PKI Authentication Setup")
        self.setSubTitle("Configure enterprise-grade certificate authentication for secure API communications")
        
        layout = QVBoxLayout()
        
        # Welcome message
        welcome_text = QLabel("""
        <h3>Enterprise PKI Authentication</h3>
        <p>This wizard will help you configure Public Key Infrastructure (PKI) authentication 
        for secure communication with enterprise APIs and services.</p>
        
        <h4>What you'll need:</h4>
        <ul>
        <li><b>P12 Certificate File</b> - Your personal certificate with private key</li>
        <li><b>Certificate Password</b> - Password to unlock your P12 file</li>
        <li><b>CA Certificate Chain</b> - Certificate authority chain (optional)</li>
        </ul>
        
        <h4>What this wizard will do:</h4>
        <ul>
        <li>Import and validate your certificates</li>
        <li>Configure secure HTTP connections</li>
        <li>Test authentication with your services</li>
        <li>Store certificates securely in your user profile</li>
        </ul>
        
        <p><b>Note:</b> You can also choose to skip PKI setup and use standard authentication.</p>
        """)
        welcome_text.setWordWrap(True)
        welcome_text.setOpenExternalLinks(True)
        
        layout.addWidget(welcome_text)
        layout.addStretch()
        
        self.setLayout(layout)


class ModeSelectionPage(QWizardPage):
    """Page for selecting PKI mode (Enterprise or Standard)."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Choose Authentication Mode")
        self.setSubTitle("PKI authentication is optional - choose what works best for your environment")
        
        layout = QVBoxLayout()
        
        # Mode selection group
        mode_group = QGroupBox("Authentication Mode")
        mode_layout = QVBoxLayout()
        
        self.button_group = QButtonGroup()
        
        # Enterprise PKI option
        self.enterprise_radio = QRadioButton("Enterprise PKI Authentication")
        self.enterprise_desc = QLabel("""
        • Use client certificates for authentication
        • Required for enterprise environments with PKI infrastructure
        • Supports P12 certificate files with password protection
        • Includes certificate chain validation
        """)
        self.enterprise_desc.setProperty("role", "option_desc")

        # Standard authentication option
        self.standard_radio = QRadioButton("Standard Authentication (Recommended)")
        self.standard_radio.setChecked(True)  # Default to standard
        self.standard_desc = QLabel("""
        • Use API keys and standard authentication methods
        • Suitable for most cloud services and APIs (OpenAI, Anthropic, etc.)
        • No certificate management required
        • Simpler setup - works immediately
        • Can enable PKI later if needed
        """)
        self.standard_desc.setProperty("role", "option_desc")
        
        self.button_group.addButton(self.enterprise_radio, 0)
        self.button_group.addButton(self.standard_radio, 1)

        mode_layout.addWidget(self.enterprise_radio)
        mode_layout.addWidget(self.enterprise_desc)
        mode_layout.addSpacing(15)
        mode_layout.addWidget(self.standard_radio)
        mode_layout.addWidget(self.standard_desc)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def nextId(self):
        """Determine next page based on selection."""
        if self.enterprise_radio.isChecked():
            self.wizard.wizard_data['pki_mode'] = 'enterprise'
            return PKISetupWizard.PAGE_P12_IMPORT
        else:
            self.wizard.wizard_data['pki_mode'] = 'standard'
            return PKISetupWizard.PAGE_SUMMARY


class P12ImportPage(QWizardPage):
    """Page for importing P12 certificate file."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Import P12 Certificate")
        self.setSubTitle("Select your P12 certificate file and enter the password")
        
        layout = QVBoxLayout()
        
        # File selection section
        file_group = QGroupBox("Certificate File")
        file_layout = QGridLayout()
        
        file_layout.addWidget(QLabel("P12 File:"), 0, 0)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select your .p12 or .pfx certificate file...")
        self.file_path_edit.textChanged.connect(self._validate_inputs)
        file_layout.addWidget(self.file_path_edit, 0, 1)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_p12_file)
        file_layout.addWidget(self.browse_button, 0, 2)
        
        file_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter certificate password...")
        self.password_edit.textChanged.connect(self._validate_inputs)
        file_layout.addWidget(self.password_edit, 1, 1, 1, 2)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Info section
        info_label = QLabel("""
        <h4>About P12 Certificates:</h4>
        <p>P12 (PKCS#12) files contain your personal certificate and private key in a 
        password-protected format. They may have extensions like .p12, .pfx, or .pk12.</p>
        
        <p><b>Security Note:</b> Your certificate password will be used only for import. 
        The extracted certificates will be stored securely in your user profile.</p>
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _browse_p12_file(self):
        """Open file browser for P12 file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select P12 Certificate File",
            "",
            "Certificate Files (*.p12 *.pfx *.pk12);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def _validate_inputs(self):
        """Validate inputs and update page completeness."""
        # Signal that the page completion status may have changed
        # The actual validation is done in isComplete()
        self.completeChanged.emit()
    
    def isComplete(self):
        """Check if page is complete."""
        file_path = self.file_path_edit.text().strip()
        password = self.password_edit.text()
        
        # Ensure we always return a boolean value
        result = (
            bool(file_path) and 
            os.path.exists(file_path) and 
            file_path.lower().endswith(('.p12', '.pfx', '.pk12')) and
            bool(password)
        )
        return bool(result)
    
    def nextId(self):
        """Store data and proceed to next page."""
        self.wizard.wizard_data['p12_file_path'] = self.file_path_edit.text().strip()
        self.wizard.wizard_data['p12_password'] = self.password_edit.text()
        return PKISetupWizard.PAGE_CERTIFICATE_CHAIN


class CertificateChainPage(QWizardPage):
    """Page for optional certificate chain configuration."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Certificate Chain (Optional)")
        self.setSubTitle("Import additional CA certificates if required by your organization")
        
        layout = QVBoxLayout()
        
        # Chain selection section
        chain_group = QGroupBox("Certificate Authority Chain")
        chain_layout = QVBoxLayout()
        
        self.use_chain_checkbox = QCheckBox("Import additional CA certificate chain")
        self.use_chain_checkbox.stateChanged.connect(self._toggle_chain_controls)
        chain_layout.addWidget(self.use_chain_checkbox)
        
        # Chain file controls
        self.chain_controls_frame = QFrame()
        chain_controls_layout = QGridLayout()
        
        chain_controls_layout.addWidget(QLabel("CA Chain File:"), 0, 0)
        self.chain_path_edit = QLineEdit()
        self.chain_path_edit.setPlaceholderText("Select CA certificate chain file...")
        self.chain_path_edit.setEnabled(False)
        chain_controls_layout.addWidget(self.chain_path_edit, 0, 1)
        
        self.chain_browse_button = QPushButton("Browse...")
        self.chain_browse_button.clicked.connect(self._browse_chain_file)
        self.chain_browse_button.setEnabled(False)
        chain_controls_layout.addWidget(self.chain_browse_button, 0, 2)
        
        self.chain_controls_frame.setLayout(chain_controls_layout)
        chain_layout.addWidget(self.chain_controls_frame)
        
        chain_group.setLayout(chain_layout)
        layout.addWidget(chain_group)
        
        # Info section
        info_label = QLabel("""
        <h4>About Certificate Chains (Optional):</h4>
        <p><b>Most users can skip this step.</b> Certificate Authority (CA) chains are only 
        needed in specific enterprise environments with internal certificate authorities.</p>
        
        <p><b>You may need this if:</b></p>
        <ul>
        <li>Your organization uses internal corporate certificate authorities</li>
        <li>You have custom root certificates that must be trusted</li>
        <li>You're connecting to services with intermediate certificate authorities</li>
        <li>You receive SSL/TLS verification errors during authentication</li>
        </ul>
        
        <p><b>Recommendation:</b> Skip this step initially. You can always run this wizard 
        again to add CA certificates if needed.</p>
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_chain_controls(self, state):
        """Toggle chain control visibility."""
        enabled = state == Qt.CheckState.Checked.value
        self.chain_path_edit.setEnabled(enabled)
        self.chain_browse_button.setEnabled(enabled)
        
        if not enabled:
            self.chain_path_edit.clear()
    
    def _browse_chain_file(self):
        """Open file browser for chain file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CA Certificate Chain File",
            "",
            "Certificate Files (*.pem *.crt *.cer *.p7b);;All Files (*)"
        )
        
        if file_path:
            self.chain_path_edit.setText(file_path)
    
    def nextId(self):
        """Store data and proceed to validation."""
        if self.use_chain_checkbox.isChecked():
            self.wizard.wizard_data['ca_chain_path'] = self.chain_path_edit.text().strip()
        else:
            self.wizard.wizard_data['ca_chain_path'] = None
        
        return PKISetupWizard.PAGE_VALIDATION


class ValidationPage(QWizardPage):
    """Page for validating and testing PKI configuration."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Validate Configuration")
        self.setSubTitle("Testing certificate import and authentication")
        
        layout = QVBoxLayout()
        
        # Progress section
        progress_group = QGroupBox("Validation Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to validate...")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results section
        results_group = QGroupBox("Validation Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Test URL section (optional)
        test_group = QGroupBox("Connection Test (Optional)")
        test_layout = QGridLayout()
        
        test_layout.addWidget(QLabel("Test URL:"), 0, 0)
        self.test_url_edit = QLineEdit()
        self.test_url_edit.setPlaceholderText("https://your-api-server.com/health")
        test_layout.addWidget(self.test_url_edit, 0, 1)
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._test_connection)
        self.test_button.setEnabled(False)
        test_layout.addWidget(self.test_button, 0, 2)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        self.setLayout(layout)
        
        # Validation will be triggered when page is shown
        self._validation_complete = False
    
    def initializePage(self):
        """Initialize page when shown."""
        # Start validation process
        self._start_validation()
    
    def _start_validation(self):
        """Start the validation process."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting validation...")
        self.results_text.clear()
        
        # Use QTimer to run validation without blocking UI
        QTimer.singleShot(100, self._run_validation)
    
    def _run_validation(self):
        """Run the validation process."""
        try:
            self._log_result("🔄 Starting PKI certificate validation...")
            self.progress_bar.setValue(20)
            
            # Get wizard data
            p12_path = self.wizard.wizard_data['p12_file_path']
            password = self.wizard.wizard_data['p12_password']
            
            self._log_result(f"📁 P12 File: {p12_path}")
            self.progress_bar.setValue(40)
            
            # Import certificate
            self.status_label.setText("Importing certificate...")
            success, error = pki_service.setup_pki_authentication(p12_path, password)
            
            if success:
                self._log_result("✓ Certificate imported successfully")
                self.progress_bar.setValue(60)
                
                # Import CA chain if provided
                ca_chain_path = self.wizard.wizard_data.get('ca_chain_path')
                if ca_chain_path:
                    self.status_label.setText("Importing CA chain...")
                    self._log_result(f"🔗 Importing CA chain: {ca_chain_path}")
                    
                    ca_success = pki_service.cert_manager.import_ca_chain_file(ca_chain_path)
                    if ca_success:
                        self._log_result("✓ CA chain imported successfully")
                    else:
                        self._log_result("⚠ CA chain import failed, proceeding without it")
                
                self.progress_bar.setValue(80)
                
                # Get certificate info
                cert_info = pki_service.get_certificate_status()
                if cert_info.get('certificate_info'):
                    info = cert_info['certificate_info']
                    self._log_result(f"📋 Subject: {info['subject']}")
                    self._log_result(f"📋 Issuer: {info['issuer']}")
                    self._log_result(f"📅 Valid until: {info['not_valid_after']}")
                    
                    if info['days_until_expiry'] <= 30:
                        self._log_result(f"⚠ Certificate expires in {info['days_until_expiry']} days")
                
                self.status_label.setText("Validation completed successfully")
                self.test_button.setEnabled(True)
                self._validation_complete = True
                
            else:
                self._log_result(f"✗ Certificate import failed: {error}")
                self.status_label.setText("Validation failed")
                
            self.progress_bar.setValue(100)
            self.completeChanged.emit()
            
        except Exception as e:
            self._log_result(f"✗ Validation error: {e}")
            self.status_label.setText("Validation error")
            self.progress_bar.setValue(100)
            logger.error(f"PKI validation error: {e}")
    
    def _test_connection(self):
        """Test PKI connection to specified URL with max 3 attempts using consolidated function."""
        from ...infrastructure.ai.api_test_service import test_network_connection_consolidated
        from ...infrastructure.storage.settings_manager import settings
        
        test_url = self.test_url_edit.text().strip()
        if not test_url:
            self._log_result("✗ Please enter a test URL")
            return
        
        # Get ignore_ssl setting from settings
        ignore_ssl = settings.get('advanced.ignore_ssl_verification', False)
        
        self._log_result(f"🌐 Testing connection to: {test_url}")
        self._log_result(f"📡 Using max 3 attempts, SSL verification: {'Disabled' if ignore_ssl else 'Enabled'}")
        
        # Disable the test button during testing
        self.test_button.setEnabled(False)
        self.test_button.setText("Testing...")
        
        try:
            # Get PKI configuration for test
            pki_config = None
            if pki_service.cert_manager.is_pki_enabled():
                cert_path, key_path = pki_service.cert_manager.get_client_cert_files()
                ca_path = pki_service.cert_manager.get_ca_chain_file()
                pki_config = {
                    'cert_path': cert_path,
                    'key_path': key_path,
                    'ca_path': ca_path
                }
            
            # Test connection using consolidated function
            result = test_network_connection_consolidated(
                base_url=test_url,
                api_key="test",  # Dummy API key for connection test
                model_name="test-model",  # Dummy model for connection test
                pki_config=pki_config,
                ignore_ssl=ignore_ssl,
                max_attempts=3,
                timeout=15
            )
            
            # Log configuration details for debugging
            logger.debug(f"PKI test details: pki_config={bool(pki_config)}, ignore_ssl={ignore_ssl}")
            if pki_config:
                logger.debug(f"Cert path: {pki_config.get('cert_path')}, CA path: {pki_config.get('ca_path')}")
            
            if result.success:
                self._log_result("✅ Connection test successful!")
                self._log_result("🎉 Your PKI authentication is working correctly")
            else:
                self._log_result(f"❌ Connection test failed: {result.message}")
                self._log_result("💡 Check your URL and certificate configuration")
                
        except Exception as e:
            # User-friendly error message
            error_msg = str(e)
            if "PKI is not enabled" in error_msg:
                self._log_result("✗ PKI authentication is not enabled")
            elif "No such host" in error_msg or "Name or service not known" in error_msg:
                self._log_result("✗ Could not connect to server - check URL and internet connection")
            elif "certificate" in error_msg.lower():
                self._log_result("✗ Certificate error - check PKI configuration")
            else:
                self._log_result(f"✗ Connection test error: {error_msg}")
        finally:
            # Re-enable the test button
            self.test_button.setEnabled(True)
            self.test_button.setText("Test Connection")
    
    def _log_result(self, message: str):
        """Add message to results text."""
        self.results_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def isComplete(self):
        """Page is complete when validation is done."""
        return bool(self._validation_complete)


class SummaryPage(QWizardPage):
    """Summary page showing setup results."""
    
    def __init__(self, wizard: PKISetupWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Setup Complete")
        self.setSubTitle("PKI authentication configuration summary")
        
        layout = QVBoxLayout()
        
        self.summary_text = QLabel()
        self.summary_text.setWordWrap(True)
        layout.addWidget(self.summary_text)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Initialize page when shown."""
        mode = self.wizard.wizard_data.get('pki_mode')
        
        if mode == 'standard':
            summary = """
            <h3>Standard Authentication Configured</h3>
            <p>✓ Specter is configured to use standard authentication methods.</p>
            
            <h4>What's configured:</h4>
            <ul>
            <li>API key authentication for supported services</li>
            <li>Standard HTTPS connections</li>
            <li>No certificate management required</li>
            </ul>
            
            <p>You can enable PKI authentication later through the Settings menu 
            if your organization requires certificate-based authentication.</p>
            """
        else:
            # Enterprise PKI mode
            status = pki_service.get_certificate_status()
            
            if status.get('valid'):
                cert_info = status.get('certificate_info', {})
                summary = f"""
                <h3>PKI Authentication Configured</h3>
                <p>✓ Enterprise certificate authentication is now active.</p>
                
                <h4>Certificate Details:</h4>
                <ul>
                <li><b>Subject:</b> {cert_info.get('subject', 'N/A')}</li>
                <li><b>Valid Until:</b> {cert_info.get('not_valid_after', 'N/A')}</li>
                <li><b>Days Until Expiry:</b> {cert_info.get('days_until_expiry', 'N/A')}</li>
                </ul>
                
                <h4>Certificate Storage:</h4>
                <ul>
                <li>Certificates stored in: <code>{pki_service.cert_manager.pki_dir}</code></li>
                <li>Client certificate: <code>client.crt</code></li>
                <li>Private key: <code>client.pem</code></li>
                """
                
                if self.wizard.wizard_data.get('ca_chain_path'):
                    summary += "<li>CA chain: <code>ca_chain.pem</code></li>"
                
                summary += """
                </ul>
                
                <p><b>Next Steps:</b></p>
                <ul>
                <li>Test API connections to verify authentication</li>
                <li>Monitor certificate expiry dates</li>
                <li>Update certificates before expiration</li>
                </ul>
                """
            else:
                summary = """
                <h3>PKI Setup Incomplete</h3>
                <p>✗ There was an issue configuring PKI authentication.</p>
                
                <p>You can:</p>
                <ul>
                <li>Run this wizard again with different certificates</li>
                <li>Check certificate file permissions</li>
                <li>Contact your IT administrator for assistance</li>
                <li>Use standard authentication instead</li>
                </ul>
                """
        
        self.summary_text.setText(summary)
    
    def accept(self):
        """Handle wizard completion."""
        mode = self.wizard.wizard_data.get('pki_mode')
        pki_enabled = mode == 'enterprise' and pki_service.get_certificate_status().get('valid', False)
        
        # Emit signal with PKI status
        self.wizard.pki_configured.emit(pki_enabled)
        
        return super().accept()


def show_pki_wizard(parent=None) -> Optional[bool]:
    """
    Show PKI setup wizard.
    
    Args:
        parent: Parent widget
        
    Returns:
        True if PKI enabled, False if disabled, None if cancelled
    """
    wizard = PKISetupWizard(parent)
    
    # Connect to result signal
    result = None
    
    def on_configured(enabled):
        nonlocal result
        result = enabled
    
    wizard.pki_configured.connect(on_configured)
    
    # Show wizard
    if wizard.exec() == QWizard.DialogCode.Accepted:
        return result
    else:
        return None  # Cancelled


def check_and_setup_pki_if_needed(parent=None) -> bool:
    """
    Check if PKI setup is needed and show wizard if required.
    
    This should be called during initial app setup to guide users
    through PKI configuration if they haven't configured it yet.
    
    Args:
        parent: Parent widget
        
    Returns:
        True if PKI is configured or user chose standard auth
    """
    try:
        # Initialize PKI service to check current status
        pki_service.initialize()
        
        # Check if PKI is already configured and working
        status = pki_service.get_certificate_status()
        if status.get('enabled') and status.get('valid'):
            logger.info("PKI already configured and valid")
            return True
        
        # Check if PKI configuration exists but is invalid
        if status.get('enabled') and not status.get('valid'):
            logger.warning("PKI configured but invalid - showing wizard for reconfiguration")
            # Show wizard to reconfigure
            result = show_pki_wizard(parent)
            return result is not None  # True if completed, False if cancelled
        
        # No PKI configuration exists - show setup wizard
        logger.info("No PKI configuration found - showing setup wizard")
        result = show_pki_wizard(parent)
        return result is not None  # True if completed, False if cancelled
        
    except Exception as e:
        logger.error(f"Error checking PKI setup: {e}")
        # On error, assume no PKI needed and continue
        return True


def is_pki_configured() -> bool:
    """
    Check if PKI is currently configured and valid.
    
    Returns:
        True if PKI is configured and certificates are valid
    """
    try:
        pki_service.initialize()
        status = pki_service.get_certificate_status()
        return status.get('enabled', False) and status.get('valid', False)
    except Exception as e:
        logger.error(f"Error checking PKI status: {e}")
        return False