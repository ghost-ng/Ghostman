"""
PKI Settings Widget for Specter Settings Dialog.

Provides PKI authentication configuration and management interface.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox,
    QFrame, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from ...infrastructure.pki import pki_service, CertificateInfo
from ..wizards.pki_wizard import show_pki_wizard

logger = logging.getLogger("specter.pki.settings_widget")

# Check if theme system is available
try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False
    logger.debug("Theme system not available - using default styling")


class PKISettingsWidget(QWidget):
    """
    PKI settings widget for integration into settings dialog.
    
    Provides:
    - Current PKI status display
    - Certificate information
    - Setup/reconfigure wizard access
    - Enable/disable PKI authentication
    """
    
    # Signals
    pki_status_changed = pyqtSignal(bool)  # Emitted when PKI enabled/disabled
    
    def __init__(self, parent=None):
        """Initialize PKI settings widget."""
        super().__init__(parent)
        
        self._current_status = None
        
        # Initialize theme system
        self.theme_manager = None
        if THEME_SYSTEM_AVAILABLE:
            try:
                self.theme_manager = get_theme_manager()
            except Exception as e:
                logger.warning(f"Failed to get theme manager: {e}")
        
        self._init_ui()
        self._apply_theme_styling()
        self._refresh_status()
        
        # No auto-refresh timer - PKI status rarely changes and manual refresh is available
        
        logger.debug("PKI Settings Widget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # PKI Status Group
        self._create_status_group(layout)
        
        # Certificate Details Group
        self._create_certificate_group(layout)
        
        # Management Actions Group
        self._create_actions_group(layout)
        
        layout.addStretch()
    
    def _apply_theme_styling(self):
        """Apply theme-aware styling to the widget."""
        if not self.theme_manager or not THEME_SYSTEM_AVAILABLE:
            self._apply_default_styling()
            return
        
        try:
            colors = self.theme_manager.current_theme
            self._apply_themed_colors(colors)
        except Exception as e:
            logger.warning(f"Failed to apply theme styling: {e}")
            self._apply_default_styling()
    
    def _apply_themed_colors(self, colors):
        """Apply theme colors to the widget."""
        # Main widget styling
        widget_style = f"""
        QWidget {{
            background-color: {colors.background_primary};
            color: {colors.text_primary};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        
        QGroupBox {{
            color: {colors.text_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            font-size: 12px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: {colors.text_primary};
        }}
        
        QLabel {{
            color: {colors.text_primary};
            font-size: 11px;
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
        
        QTextEdit {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            border-radius: 3px;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        """
        
        self.setStyleSheet(widget_style)
        
        # Update setup button with theme-appropriate styling
        if hasattr(self, 'setup_button'):
            setup_button_style = f"""
            QPushButton {{
                background-color: {colors.interactive_normal};
                color: {colors.text_primary};
                border: 1px solid {colors.primary};
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.primary};
                color: {colors.background_primary};
            }}
            QPushButton:pressed {{
                background-color: {colors.primary_hover};
                color: {colors.background_primary};
            }}
            """
            self.setup_button.setStyleSheet(setup_button_style)
    
    def _apply_default_styling(self):
        """Apply default styling when theme system is not available."""
        style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            font-size: 12px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #ffffff;
        }
        
        QLabel {
            color: #ffffff;
            font-size: 11px;
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
        
        QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #ffffff;
            border-radius: 3px;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        """
        
        self.setStyleSheet(style)
    
    def _load_refresh_icon(self):
        """Load custom refresh icon based on current theme."""
        try:
            # Determine icon variant based on theme
            icon_variant = self._get_icon_variant()
            
            # Build path to refresh icon
            refresh_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"refresh_{icon_variant}.png"
            )
            
            if os.path.exists(refresh_icon_path):
                from PyQt6.QtGui import QIcon
                icon = QIcon(refresh_icon_path)
                self.refresh_button.setIcon(icon)
                self.refresh_button.setText("")  # Remove any text
                logger.debug(f"Loaded refresh icon: {refresh_icon_path}")
            else:
                # Fallback to Unicode emoji if custom icon not found
                self.refresh_button.setText("🔄")
                logger.warning(f"Refresh icon not found: {refresh_icon_path}")
                
        except Exception as e:
            logger.error(f"Failed to load refresh icon: {e}")
            # Fallback to Unicode emoji
            self.refresh_button.setText("🔄")
    
    def _get_icon_variant(self) -> str:
        """Get icon variant (dark/lite) based on current theme."""
        try:
            if self.theme_manager and THEME_SYSTEM_AVAILABLE:
                # Get current theme colors to determine if it's dark or light
                theme = self.theme_manager.current_theme
                if hasattr(theme, 'background_primary'):
                    # Simple heuristic: if background is dark, use lite icons
                    bg_color = theme.background_primary
                    if bg_color.startswith('#'):
                        # Convert hex to brightness
                        hex_color = bg_color[1:]
                        if len(hex_color) == 6:
                            r = int(hex_color[0:2], 16)
                            g = int(hex_color[2:4], 16)  
                            b = int(hex_color[4:6], 16)
                            brightness = (r * 0.299 + g * 0.587 + b * 0.114)
                            return "lite" if brightness < 128 else "dark"
        except Exception as e:
            logger.debug(f"Failed to determine icon variant from theme: {e}")
        
        # Default fallback
        return "lite"
    
    
    def _create_status_group(self, parent_layout):
        """Create PKI status group."""
        status_group = QGroupBox("PKI Authentication Status")
        status_layout = QVBoxLayout()
        
        # Status indicator
        status_frame = QFrame()
        status_frame_layout = QHBoxLayout()
        status_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create horizontal layout for status icon and text
        status_content_layout = QHBoxLayout()
        status_content_layout.setContentsMargins(0, 0, 0, 0)
        status_content_layout.setSpacing(5)
        
        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        self.status_icon.setScaledContents(True)
        status_content_layout.addWidget(self.status_icon)
        
        # Status text
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_content_layout.addWidget(self.status_label)
        
        # Hide icon initially during checking
        self.status_icon.hide()
        
        # Create container widget for the status content
        status_container = QWidget()
        status_container.setLayout(status_content_layout)
        status_frame_layout.addWidget(status_container)
        
        status_frame_layout.addStretch()
        
        self.refresh_button = QPushButton()
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setToolTip("Refresh PKI status")
        self.refresh_button.clicked.connect(self._refresh_status)
        
        # Load custom refresh icon
        self._load_refresh_icon()
        status_frame_layout.addWidget(self.refresh_button)
        
        status_frame.setLayout(status_frame_layout)
        status_layout.addWidget(status_frame)
        
        # Additional status info
        self.status_details = QLabel("Initializing PKI service...")
        self.status_details.setWordWrap(True)
        self.status_details.setStyleSheet("color: #888888; font-size: 10px; margin-top: 5px;")
        status_layout.addWidget(self.status_details)
        
        status_group.setLayout(status_layout)
        parent_layout.addWidget(status_group)
    
    def _create_certificate_group(self, parent_layout):
        """Create certificate details group."""
        self.cert_group = QGroupBox("Certificate Information")
        cert_layout = QVBoxLayout()
        
        self.cert_details = QTextEdit()
        self.cert_details.setMaximumHeight(120)
        self.cert_details.setReadOnly(True)
        self.cert_details.setPlaceholderText("No certificate information available")
        cert_layout.addWidget(self.cert_details)
        
        self.cert_group.setLayout(cert_layout)
        self.cert_group.setVisible(False)  # Initially hidden
        parent_layout.addWidget(self.cert_group)
    
    def _create_actions_group(self, parent_layout):
        """Create management actions group."""
        actions_group = QGroupBox("Management")
        actions_layout = QVBoxLayout()
        
        # Setup/Configure PKI button
        self.setup_button = QPushButton("Setup PKI Authentication")
        self.setup_button.setMaximumWidth(200)
        self.setup_button.clicked.connect(self._show_setup_wizard)
        actions_layout.addWidget(self.setup_button)
        
        # Manual refresh button
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self._refresh_status)
        self.refresh_button.setMaximumWidth(120)
        actions_layout.addWidget(self.refresh_button)
        
        # Enable/Disable button
        self.toggle_button = QPushButton("Disable PKI")
        self.toggle_button.clicked.connect(self._toggle_pki)
        self.toggle_button.setVisible(False)  # Initially hidden
        actions_layout.addWidget(self.toggle_button)
        
        # Test connection button
        self.test_button = QPushButton("Test PKI Connection")
        self.test_button.clicked.connect(self._test_connection)
        self.test_button.setVisible(False)  # Initially hidden
        actions_layout.addWidget(self.test_button)
        
        actions_group.setLayout(actions_layout)
        parent_layout.addWidget(actions_group)
    
    def _refresh_status(self):
        """Refresh PKI status display."""
        try:
            # Reset PKI service initialization to pick up any changes
            pki_service.reset_initialization()

            # Initialize PKI service
            pki_service.initialize()

            # Get current status
            status = pki_service.get_certificate_status()
            self._current_status = status
            
            # Update status display
            if status.get('enabled') and status.get('valid'):
                self._show_enabled_status(status)
            elif status.get('enabled') and not status.get('valid'):
                self._show_invalid_status(status)
            else:
                self._show_disabled_status()
            
            # Check for warnings
            self._check_warnings(status)
            
        except Exception as e:
            logger.error(f"Failed to refresh PKI status: {e}")
            self._show_error_status(str(e))
    
    def _show_enabled_status(self, status: Dict[str, Any]):
        """Show enabled PKI status."""
        # Load green check icon
        try:
            check_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", "check_green.png"
            )
            
            if os.path.exists(check_icon_path):
                from PyQt6.QtGui import QPixmap
                check_pixmap = QPixmap(check_icon_path)
                scaled_pixmap = check_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.status_icon.setPixmap(scaled_pixmap)
                self.status_icon.show()
                self.status_label.setText("PKI Authentication Enabled")
                logger.debug("Loaded green check icon")
            else:
                # Fallback to text symbol
                self.status_icon.hide()
                self.status_label.setText("✓ PKI Authentication Enabled")
                logger.warning(f"Check icon not found: {check_icon_path}")
        except Exception as e:
            logger.error(f"Failed to load check icon: {e}")
            self.status_icon.hide()
            self.status_label.setText("✓ PKI Authentication Enabled")
        
        # Use theme colors with hardcoded fallbacks
        success_color = '#28a745'
        success_detail_color = '#155724'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            success_color = getattr(colors, 'status_success', success_color)
            success_detail_color = getattr(colors, 'text_secondary', success_detail_color)
        self.status_label.setStyleSheet(f"color: {success_color}; font-weight: bold; font-size: 12px;")

        cert_info = status.get('certificate_info')
        if cert_info:
            details = f"""PKI authentication is active and certificates are valid.
Certificate expires in {cert_info['days_until_expiry']} days.
Last validated: {status.get('last_validation', 'Unknown')}"""
        else:
            details = "PKI authentication is active."

        self.status_details.setText(details)
        self.status_details.setStyleSheet(f"color: {success_detail_color}; font-size: 10px; margin-top: 5px;")
        
        # Update certificate details
        self._update_certificate_details(cert_info)
        
        # Update buttons
        self.setup_button.setText("Reconfigure PKI")
        self.toggle_button.setText("Disable PKI")
        self.toggle_button.setVisible(True)
        self.test_button.setVisible(True)
        self.cert_group.setVisible(True)
    
    def _show_invalid_status(self, status: Dict[str, Any]):
        """Show invalid PKI status."""
        # Load warning icon
        try:
            icon_variant = self._get_icon_variant()
            warning_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", "warning_color.png"
            )
            
            if os.path.exists(warning_icon_path):
                from PyQt6.QtGui import QPixmap
                warning_pixmap = QPixmap(warning_icon_path)
                scaled_pixmap = warning_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.status_icon.setPixmap(scaled_pixmap)
                self.status_icon.show()
                self.status_label.setText("PKI Configuration Invalid")
                logger.debug("Loaded warning icon: warning_color.png")
            else:
                # Fallback to text symbol
                self.status_icon.hide()
                self.status_label.setText("⚠ PKI Configuration Invalid")
                logger.warning(f"Warning icon not found: {warning_icon_path}")
        except Exception as e:
            logger.error(f"Failed to load warning icon: {e}")
            self.status_icon.hide()
            self.status_label.setText("⚠ PKI Configuration Invalid")
        
        # Use theme colors with hardcoded fallbacks
        warning_color = '#fd7e14'
        warning_detail_color = '#856404'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            warning_color = getattr(colors, 'status_warning', warning_color)
            warning_detail_color = getattr(colors, 'text_secondary', warning_detail_color)
        self.status_label.setStyleSheet(f"color: {warning_color}; font-weight: bold; font-size: 12px;")

        errors = status.get('errors', [])
        warnings = status.get('warnings', [])
        issues = errors + warnings

        if issues:
            details = f"PKI is configured but has issues:\n• " + "\n• ".join(issues)
        else:
            details = "PKI configuration exists but certificates are not valid."

        self.status_details.setText(details)
        self.status_details.setStyleSheet(f"color: {warning_detail_color}; font-size: 10px; margin-top: 5px;")
        
        # Update buttons
        self.setup_button.setText("Fix PKI Configuration")
        self.toggle_button.setText("Disable PKI")
        self.toggle_button.setVisible(True)
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)
    
    def _show_disabled_status(self):
        """Show disabled PKI status."""
        # Load warning icon
        try:
            icon_variant = self._get_icon_variant()
            warning_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", "warning_color.png"
            )
            
            if os.path.exists(warning_icon_path):
                from PyQt6.QtGui import QPixmap
                warning_pixmap = QPixmap(warning_icon_path)
                # Scale icon to appropriate size
                scaled_pixmap = warning_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.status_icon.setPixmap(scaled_pixmap)
                self.status_label.setText("PKI Authentication Disabled")
                logger.debug("Loaded warning icon: warning_color.png")
            else:
                # Fallback to text symbol - hide icon and show symbol in text
                self.status_icon.hide()
                self.status_label.setText("⚠ PKI Authentication Disabled")
                logger.warning(f"Warning icon not found: {warning_icon_path}")
        except Exception as e:
            logger.error(f"Failed to load warning icon: {e}")
            # Fallback to text symbol - hide icon and show symbol in text
            self.status_icon.hide()
            self.status_label.setText("⚠ PKI Authentication Disabled")
        
        # Use theme colors with hardcoded fallbacks
        disabled_color = '#6c757d'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            disabled_color = getattr(colors, 'text_disabled', disabled_color)
        self.status_label.setStyleSheet(f"color: {disabled_color}; font-weight: bold; font-size: 12px;")

        self.status_details.setText("""PKI authentication is disabled. Standard authentication methods are in use.
You can enable PKI authentication if your organization requires certificate-based authentication.""")
        self.status_details.setStyleSheet(f"color: {disabled_color}; font-size: 10px; margin-top: 5px;")
        
        # Update buttons
        self.setup_button.setText("Setup PKI Authentication")
        self.toggle_button.setVisible(False)
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)
    
    def _show_error_status(self, error: str):
        """Show error status."""
        # Load error icon
        try:
            icon_variant = self._get_icon_variant()
            error_icon_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", 
                "assets", "icons", f"x_{icon_variant}.png"
            )
            
            if os.path.exists(error_icon_path):
                from PyQt6.QtGui import QPixmap
                error_pixmap = QPixmap(error_icon_path)
                scaled_pixmap = error_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.status_icon.setPixmap(scaled_pixmap)
                self.status_icon.show()
                self.status_label.setText("PKI Service Error")
                logger.debug(f"Loaded error icon: x_{icon_variant}.png")
            else:
                # Try the red error icon as fallback
                error_icon_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", 
                    "assets", "icons", "x_red.png"
                )
                if os.path.exists(error_icon_path):
                    from PyQt6.QtGui import QPixmap
                    error_pixmap = QPixmap(error_icon_path)
                    scaled_pixmap = error_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.status_icon.setPixmap(scaled_pixmap)
                    self.status_icon.show()
                    self.status_label.setText("PKI Service Error")
                    logger.debug("Loaded red error icon")
                else:
                    # Fallback to text symbol
                    self.status_icon.hide()
                    self.status_label.setText("✗ PKI Service Error")
                    logger.warning(f"Error icon not found: {error_icon_path}")
        except Exception as e:
            logger.error(f"Failed to load error icon: {e}")
            self.status_icon.hide()
            self.status_label.setText("✗ PKI Service Error")
        
        # Use theme colors with hardcoded fallbacks
        error_color = '#dc3545'
        error_detail_color = '#721c24'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            colors = self.theme_manager.current_theme
            error_color = getattr(colors, 'status_error', error_color)
            error_detail_color = getattr(colors, 'text_secondary', error_detail_color)
        self.status_label.setStyleSheet(f"color: {error_color}; font-weight: bold; font-size: 12px;")

        self.status_details.setText(f"Error checking PKI status: {error}")
        self.status_details.setStyleSheet(f"color: {error_detail_color}; font-size: 10px; margin-top: 5px;")
        
        # Update buttons
        self.setup_button.setText("Setup PKI Authentication")
        self.toggle_button.setVisible(False)
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)
    
    def _update_certificate_details(self, cert_info: Optional[Dict[str, Any]]):
        """Update certificate details display."""
        if not cert_info:
            self.cert_details.setText("No certificate information available")
            return
        
        try:
            # Parse dates if they're strings
            not_valid_after = cert_info.get('not_valid_after', '')
            if isinstance(not_valid_after, str):
                try:
                    expiry_date = datetime.fromisoformat(not_valid_after.replace('Z', '+00:00'))
                    formatted_expiry = expiry_date.strftime("%Y-%m-%d %H:%M:%S UTC")
                except:
                    formatted_expiry = not_valid_after
            else:
                formatted_expiry = str(not_valid_after)
            
            # Get storage location information
            storage_info = ""
            try:
                # Service should already be initialized by _refresh_status
                cert_path, key_path = pki_service.cert_manager.get_client_cert_files()
                ca_path = pki_service.cert_manager.get_ca_chain_file()
                pki_dir = str(pki_service.cert_manager.pki_dir)
                
                storage_info = f"""

📁 Certificate Storage Locations:
PKI Directory: {pki_dir}
Client Certificate: {cert_path if cert_path else 'Not available'}
Private Key: {key_path if key_path else 'Not available'}"""
                
                if ca_path:
                    storage_info += f"""
CA Chain: {ca_path}"""
                else:
                    storage_info += f"""
CA Chain: Not configured"""
                    
            except Exception as e:
                logger.debug(f"Could not get storage info: {e}")
            
            details = f"""Subject: {cert_info.get('subject', 'N/A')}
Issuer: {cert_info.get('issuer', 'N/A')}
Serial Number: {cert_info.get('serial_number', 'N/A')}
Valid Until: {formatted_expiry}
Days Until Expiry: {cert_info.get('days_until_expiry', 'N/A')}
Key Usage: {', '.join(cert_info.get('key_usage', []))}
Fingerprint: {cert_info.get('fingerprint', 'N/A')[:32]}...{storage_info}"""
            
            self.cert_details.setText(details)
            
        except Exception as e:
            logger.error(f"Failed to format certificate details: {e}")
            self.cert_details.setText(f"Certificate information available but formatting failed: {e}")
    
    def _check_warnings(self, status: Dict[str, Any]):
        """Check for certificate warnings."""
        warnings = status.get('warnings', [])
        if warnings:
            # Show warning in status details
            current_text = self.status_details.text()
            warning_text = "\n⚠ " + "\n⚠ ".join(warnings)
            self.status_details.setText(current_text + warning_text)
    
    def _show_setup_wizard(self):
        """Show PKI setup wizard."""
        try:
            result = show_pki_wizard(self)
            
            if result is not None:
                # Refresh status immediately after wizard completion
                self._refresh_status()
                
                # Emit signal for main application
                self.pki_status_changed.emit(result)
                
                # Show success message
                if result:
                    QMessageBox.information(
                        self,
                        "PKI Setup Complete",
                        "PKI authentication has been configured successfully."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Standard Authentication",
                        "Standard authentication is configured. PKI can be enabled later if needed."
                    )
            
        except Exception as e:
            logger.error(f"PKI setup wizard failed: {e}")
            QMessageBox.critical(
                self,
                "PKI Setup Error",
                f"Failed to configure PKI authentication:\n{e}"
            )
    
    def _toggle_pki(self):
        """Toggle PKI authentication on/off."""
        try:
            if self._current_status and self._current_status.get('enabled'):
                # Disable PKI
                reply = QMessageBox.question(
                    self,
                    "Disable PKI",
                    "Are you sure you want to disable PKI authentication?\n\n"
                    "This will switch to standard authentication methods.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    success = pki_service.disable_pki_authentication()
                    if success:
                        QMessageBox.information(self, "PKI Disabled", "PKI authentication has been disabled.")
                        self.pki_status_changed.emit(False)
                    else:
                        QMessageBox.warning(self, "Error", "Failed to disable PKI authentication.")
                    
                    self._refresh_status()
            
        except Exception as e:
            logger.error(f"Failed to toggle PKI: {e}")
            QMessageBox.critical(self, "Error", f"Failed to toggle PKI authentication:\n{e}")
    
    def _test_connection(self):
        """Test PKI connection using consolidated network test function."""
        from PyQt6.QtWidgets import QInputDialog, QProgressDialog
        from PyQt6.QtCore import QThread, pyqtSignal
        from ...infrastructure.ai.api_test_service import test_network_connection_consolidated
        from ...infrastructure.storage.settings_manager import settings
        
        try:
            # Simple dialog to get test URL
            url, ok = QInputDialog.getText(
                self,
                "Test PKI Connection",
                "Enter a URL to test PKI authentication against:",
                text="https://your-api-server.com/health"
            )
            
            if ok and url.strip():
                # Get ignore_ssl setting from settings
                ignore_ssl = settings.get('advanced.ignore_ssl_verification', False)
                
                # Create proper modal progress dialog
                progress = QProgressDialog("Testing PKI connection...", "Cancel", 0, 0, self)
                progress.setWindowTitle("Testing Connection")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)  # Show immediately
                progress.setCancelButton(None)  # No cancel button for now
                progress.setRange(0, 0)  # Indeterminate progress
                progress.show()
                
                # Process events to ensure dialog is shown
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                
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
                        base_url=url.strip(),
                        api_key="test",  # Dummy API key for connection test
                        model_name="test-model",  # Dummy model for connection test
                        pki_config=pki_config,
                        ignore_ssl=ignore_ssl,
                        max_attempts=3,
                        timeout=15
                    )
                    
                    # Close progress dialog
                    progress.close()
                    
                    if result.success:
                        QMessageBox.information(
                            self,
                            "Connection Successful",
                            f"✅ PKI authentication test successful!\n\nURL: {url}\nSSL Verification: {'Disabled' if ignore_ssl else 'Enabled'}\n\nYour certificate is working correctly."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Connection Failed",
                            f"❌ PKI authentication test failed:\n\n{result.message}\n\nSSL Verification: {'Disabled' if ignore_ssl else 'Enabled'}\n\nPlease check your certificate configuration."
                        )
                        
                except Exception as test_error:
                    # Ensure progress is closed on error
                    progress.close()
                    raise test_error
            
        except Exception as e:
            # Ensure progress is closed on any error
            try:
                progress.close()
            except:
                pass
            
            logger.error(f"Failed to test PKI connection: {e}")
            
            # User-friendly error message
            error_msg = "An error occurred while testing the PKI connection."
            if "PKI is not enabled" in str(e):
                error_msg = "PKI authentication is not enabled. Please configure PKI first."
            elif "No such host" in str(e) or "Name or service not known" in str(e):
                error_msg = "Could not connect to the server. Please check the URL and your internet connection."
            elif "certificate" in str(e).lower():
                error_msg = "Certificate error. Please check your PKI configuration."
            else:
                error_msg = f"Connection test failed: {e}"
            
            # Create proper modal error dialog
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Test Error")
            error_dialog.setText(error_msg)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            error_dialog.exec()
    
    def get_pki_status(self) -> Optional[Dict[str, Any]]:
        """Get current PKI status."""
        return self._current_status
    
    def cleanup(self):
        """Cleanup resources."""
        # No timer to cleanup since we removed the auto-refresh
        logger.debug("PKI Settings Widget cleaned up")