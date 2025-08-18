"""
PKI Settings Widget for Ghostman Settings Dialog.

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
from PyQt6.QtGui import QFont

from ...infrastructure.pki import pki_service, CertificateInfo
from ..wizards.pki_wizard import show_pki_wizard

logger = logging.getLogger("ghostman.pki.settings_widget")

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
        
        # Auto-refresh status every 30 seconds
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(30000)  # 30 seconds
        
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
        
        # Update setup button with primary accent color
        if hasattr(self, 'setup_button'):
            setup_button_style = f"""
            QPushButton {{
                background-color: {colors.primary};
                color: {colors.text_primary};
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.primary_hover};
            }}
            QPushButton:pressed {{
                background-color: {colors.primary_hover};
                opacity: 0.9;
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
        
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_frame_layout.addWidget(self.status_label)
        
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
        self.setup_button.clicked.connect(self._show_setup_wizard)
        actions_layout.addWidget(self.setup_button)
        
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
        self.status_label.setText("Status: ✅ PKI Authentication Enabled")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
        
        cert_info = status.get('certificate_info')
        if cert_info:
            details = f"""PKI authentication is active and certificates are valid.
Certificate expires in {cert_info['days_until_expiry']} days.
Last validated: {status.get('last_validation', 'Unknown')}"""
        else:
            details = "PKI authentication is active."
        
        self.status_details.setText(details)
        self.status_details.setStyleSheet("color: #155724; font-size: 10px; margin-top: 5px;")
        
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
        self.status_label.setText("Status: ⚠️ PKI Configuration Invalid")
        self.status_label.setStyleSheet("color: #fd7e14; font-weight: bold; font-size: 12px;")
        
        errors = status.get('errors', [])
        warnings = status.get('warnings', [])
        issues = errors + warnings
        
        if issues:
            details = f"PKI is configured but has issues:\n• " + "\n• ".join(issues)
        else:
            details = "PKI configuration exists but certificates are not valid."
        
        self.status_details.setText(details)
        self.status_details.setStyleSheet("color: #856404; font-size: 10px; margin-top: 5px;")
        
        # Update buttons
        self.setup_button.setText("Fix PKI Configuration")
        self.toggle_button.setText("Disable PKI")
        self.toggle_button.setVisible(True)
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)
    
    def _show_disabled_status(self):
        """Show disabled PKI status."""
        self.status_label.setText("Status: ⚪ PKI Authentication Disabled")
        self.status_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        self.status_details.setText("""PKI authentication is disabled. Standard authentication methods are in use.
You can enable PKI authentication if your organization requires certificate-based authentication.""")
        self.status_details.setStyleSheet("color: #6c757d; font-size: 10px; margin-top: 5px;")
        
        # Update buttons
        self.setup_button.setText("Setup PKI Authentication")
        self.toggle_button.setVisible(False)
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)
    
    def _show_error_status(self, error: str):
        """Show error status."""
        self.status_label.setText("Status: ❌ PKI Service Error")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
        
        self.status_details.setText(f"Error checking PKI status: {error}")
        self.status_details.setStyleSheet("color: #721c24; font-size: 10px; margin-top: 5px;")
        
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
            
            details = f"""Subject: {cert_info.get('subject', 'N/A')}
Issuer: {cert_info.get('issuer', 'N/A')}
Serial Number: {cert_info.get('serial_number', 'N/A')}
Valid Until: {formatted_expiry}
Days Until Expiry: {cert_info.get('days_until_expiry', 'N/A')}
Key Usage: {', '.join(cert_info.get('key_usage', []))}
Fingerprint: {cert_info.get('fingerprint', 'N/A')[:32]}..."""
            
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
            warning_text = "\n⚠️ " + "\n⚠️ ".join(warnings)
            self.status_details.setText(current_text + warning_text)
    
    def _show_setup_wizard(self):
        """Show PKI setup wizard."""
        try:
            result = show_pki_wizard(self)
            
            if result is not None:
                # Refresh status after wizard completion
                QTimer.singleShot(500, self._refresh_status)
                
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
        """Test PKI connection."""
        try:
            # Simple dialog to get test URL
            from PyQt6.QtWidgets import QInputDialog
            
            url, ok = QInputDialog.getText(
                self,
                "Test PKI Connection",
                "Enter a URL to test PKI authentication against:",
                text="https://your-api-server.com/health"
            )
            
            if ok and url.strip():
                # Show progress
                progress = QMessageBox(self)
                progress.setWindowTitle("Testing Connection")
                progress.setText("Testing PKI connection...")
                progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
                progress.show()
                
                # Test connection
                success, error = pki_service.test_pki_connection(url.strip())
                progress.close()
                
                if success:
                    QMessageBox.information(
                        self,
                        "Connection Test Successful",
                        f"PKI authentication test to {url} was successful."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Connection Test Failed",
                        f"PKI authentication test to {url} failed:\n{error}"
                    )
            
        except Exception as e:
            logger.error(f"Failed to test PKI connection: {e}")
            QMessageBox.critical(self, "Test Error", f"Failed to test PKI connection:\n{e}")
    
    def get_pki_status(self) -> Optional[Dict[str, Any]]:
        """Get current PKI status."""
        return self._current_status
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, '_refresh_timer'):
            self._refresh_timer.stop()