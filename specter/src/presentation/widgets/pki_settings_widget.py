"""
PKI Settings Widget for Specter Settings Dialog.

Provides certificate store browsing and PKI toggle — zero-config
enterprise authentication using the Windows certificate store.
"""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox,
    QFrame, QMessageBox, QComboBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...infrastructure.pki import pki_service
from ...infrastructure.ai.session_manager import enumerate_client_certs, CertStoreEntry

logger = logging.getLogger("specter.pki.settings_widget")

try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False


class PKISettingsWidget(QWidget):
    """
    PKI settings widget — browse Windows cert store, auto-detect or
    manually select a client certificate, test connection.
    """

    pki_status_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_status = None
        self._certs = []

        self.theme_manager = None
        if THEME_SYSTEM_AVAILABLE:
            try:
                self.theme_manager = get_theme_manager()
            except Exception:
                pass

        self._init_ui()
        self._apply_theme_styling()
        self._refresh_status()
        logger.debug("PKI Settings Widget initialized")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Status group
        self._create_status_group(layout)

        # Certificate selector group
        self._create_cert_selector_group(layout)

        # Certificate details group
        self._create_certificate_group(layout)

        # Actions group
        self._create_actions_group(layout)

        layout.addStretch()

    def _create_status_group(self, parent_layout):
        status_group = QGroupBox("PKI Authentication Status")
        status_layout = QVBoxLayout()

        status_row = QHBoxLayout()
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setFixedWidth(80)
        self.refresh_button.clicked.connect(self._refresh_status)
        status_row.addWidget(self.refresh_button)

        status_layout.addLayout(status_row)

        self.status_details = QLabel("Initializing...")
        self.status_details.setWordWrap(True)
        self.status_details.setStyleSheet("color: #888888; font-size: 10px; margin-top: 5px;")
        status_layout.addWidget(self.status_details)

        status_group.setLayout(status_layout)
        parent_layout.addWidget(status_group)

    def _create_cert_selector_group(self, parent_layout):
        self.cert_selector_group = QGroupBox("Certificate Selection")
        layout = QVBoxLayout()

        desc = QLabel(
            "Specter auto-detects client certificates from the Windows certificate store. "
            "You can also select a specific certificate below."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 10px; margin-bottom: 6px;")
        layout.addWidget(desc)

        # Combo box for cert selection
        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Certificate:"))
        self.cert_combo = QComboBox()
        self.cert_combo.setMinimumWidth(350)
        self.cert_combo.currentIndexChanged.connect(self._on_cert_selected)
        combo_row.addWidget(self.cert_combo, 1)
        layout.addLayout(combo_row)

        self.cert_selector_group.setLayout(layout)
        parent_layout.addWidget(self.cert_selector_group)

    def _create_certificate_group(self, parent_layout):
        self.cert_group = QGroupBox("Certificate Details")
        cert_layout = QVBoxLayout()

        self.cert_details = QTextEdit()
        self.cert_details.setMaximumHeight(120)
        self.cert_details.setReadOnly(True)
        self.cert_details.setPlaceholderText("No certificate selected")
        cert_layout.addWidget(self.cert_details)

        self.cert_group.setLayout(cert_layout)
        self.cert_group.setVisible(False)
        parent_layout.addWidget(self.cert_group)

    def _create_actions_group(self, parent_layout):
        actions_group = QGroupBox("Management")
        actions_layout = QVBoxLayout()

        btn_row = QHBoxLayout()

        self.enable_button = QPushButton("Enable PKI")
        self.enable_button.setMaximumWidth(150)
        self.enable_button.clicked.connect(self._toggle_pki)
        btn_row.addWidget(self.enable_button)

        self.test_button = QPushButton("Test Connection")
        self.test_button.setMaximumWidth(150)
        self.test_button.clicked.connect(self._test_connection)
        self.test_button.setVisible(False)
        btn_row.addWidget(self.test_button)

        btn_row.addStretch()
        actions_layout.addLayout(btn_row)

        actions_group.setLayout(actions_layout)
        parent_layout.addWidget(actions_group)

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------

    def _apply_theme_styling(self):
        if not self.theme_manager or not THEME_SYSTEM_AVAILABLE:
            self._apply_default_styling()
            return
        try:
            colors = self.theme_manager.current_theme
            self._apply_themed_colors(colors)
        except Exception:
            self._apply_default_styling()

    def _apply_themed_colors(self, colors):
        self.setStyleSheet(f"""
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
            padding: 0 8px;
            color: {colors.text_primary};
        }}
        QLabel {{ color: {colors.text_primary}; font-size: 11px; }}
        QPushButton {{
            background-color: {colors.interactive_normal};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 11px;
        }}
        QPushButton:hover {{ background-color: {colors.interactive_hover}; }}
        QPushButton:pressed {{ background-color: {colors.interactive_active}; }}
        QComboBox {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 11px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QTextEdit {{
            background-color: {colors.background_tertiary};
            border: 1px solid {colors.border_primary};
            color: {colors.text_primary};
            border-radius: 3px;
            font-size: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        """)

    def _apply_default_styling(self):
        self.setStyleSheet("""
        QWidget { background-color: #2b2b2b; color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; }
        QGroupBox { color: #ffffff; border: 1px solid #555; border-radius: 4px; margin-top: 10px; padding-top: 10px; font-weight: bold; font-size: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; color: #ffffff; }
        QLabel { color: #ffffff; font-size: 11px; }
        QPushButton { background-color: #404040; border: 1px solid #555; color: #fff; padding: 8px 16px; border-radius: 4px; font-size: 11px; }
        QPushButton:hover { background-color: #505050; }
        QComboBox { background-color: #3c3c3c; border: 1px solid #555; color: #fff; padding: 4px 8px; border-radius: 3px; }
        QTextEdit { background-color: #3c3c3c; border: 1px solid #555; color: #fff; border-radius: 3px; font-size: 10px; font-family: 'Consolas', monospace; }
        """)

    # ------------------------------------------------------------------
    # Status refresh
    # ------------------------------------------------------------------

    def _refresh_status(self):
        try:
            pki_service.reset_initialization()
            pki_service.initialize()

            status = pki_service.get_certificate_status()
            self._current_status = status

            # Populate cert combo
            self._populate_cert_combo()

            if status.get('enabled') and status.get('cert_found'):
                self._show_enabled_status(status)
            elif status.get('enabled') and not status.get('cert_found'):
                self._show_no_cert_status(status)
            else:
                self._show_disabled_status()

        except Exception as e:
            logger.error(f"Failed to refresh PKI status: {e}")
            self._show_error_status(str(e))

    def _populate_cert_combo(self):
        """Populate the certificate combo box with available certs."""
        self.cert_combo.blockSignals(True)
        self.cert_combo.clear()

        self._certs = enumerate_client_certs()

        if not self._certs:
            self.cert_combo.addItem("(No certificates found in Windows store)")
            self.cert_combo.setEnabled(False)
        else:
            self.cert_combo.setEnabled(True)
            self.cert_combo.addItem("(Auto-detect best certificate)")

            detected = pki_service.get_detected_cert()
            selected_idx = 0

            for i, cert in enumerate(self._certs):
                # Show subject CN and thumbprint prefix
                cn = cert.subject.split("CN=")[-1].split(",")[0] if "CN=" in cert.subject else cert.subject
                label = f"{cn}  [{cert.thumbprint[:12]}...]"
                self.cert_combo.addItem(label)

                # Select the currently active cert
                if detected and cert.thumbprint == detected.thumbprint:
                    selected_idx = i + 1  # +1 because of auto-detect entry

            self.cert_combo.setCurrentIndex(selected_idx)

        self.cert_combo.blockSignals(False)

    def _on_cert_selected(self, index):
        """Handle cert combo box selection change."""
        if index <= 0 or not self._certs:
            # Auto-detect or no certs
            self.cert_details.clear()
            self.cert_group.setVisible(False)
            return

        cert = self._certs[index - 1]  # -1 for auto-detect entry
        self._show_cert_details(cert)

    def _show_cert_details(self, cert: CertStoreEntry):
        """Show details for a certificate."""
        self.cert_group.setVisible(True)
        eku = ", ".join(cert.enhanced_key_usage) if cert.enhanced_key_usage else "Not specified"
        self.cert_details.setText(
            f"Subject: {cert.subject}\n"
            f"Issuer: {cert.issuer}\n"
            f"Thumbprint: {cert.thumbprint}\n"
            f"Valid: {cert.not_before} to {cert.not_after}\n"
            f"Key Usage: {eku}\n"
            f"Has Private Key: {cert.has_private_key}"
        )

    # ------------------------------------------------------------------
    # Status display
    # ------------------------------------------------------------------

    def _show_enabled_status(self, status):
        success_color = '#28a745'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            success_color = getattr(self.theme_manager.current_theme, 'status_success', success_color)

        self.status_label.setText("PKI Authentication Enabled")
        self.status_label.setStyleSheet(f"color: {success_color}; font-weight: bold; font-size: 12px;")

        subject = status.get('subject', 'Unknown')
        thumb = status.get('thumbprint', '')[:16]
        method = "Auto-detected" if status.get('auto_detect') else "Manually selected"
        self.status_details.setText(f"{method} from Windows cert store.\nCert: {subject}\nThumbprint: {thumb}...")

        # Show detected cert details
        detected = pki_service.get_detected_cert()
        if detected:
            self._show_cert_details(detected)

        self.enable_button.setText("Disable PKI")
        self.test_button.setVisible(True)
        self.cert_selector_group.setVisible(True)

    def _show_no_cert_status(self, status):
        warning_color = '#fd7e14'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            warning_color = getattr(self.theme_manager.current_theme, 'status_warning', warning_color)

        self.status_label.setText("PKI Enabled — No Certificate Found")
        self.status_label.setStyleSheet(f"color: {warning_color}; font-weight: bold; font-size: 12px;")

        errors = status.get('errors', [])
        self.status_details.setText(
            "PKI is enabled but no suitable client certificate was found.\n"
            + ("\n".join(errors) if errors else "Ensure a certificate with a private key is installed.")
        )
        self.enable_button.setText("Disable PKI")
        self.test_button.setVisible(False)
        self.cert_selector_group.setVisible(True)
        self.cert_group.setVisible(False)

    def _show_disabled_status(self):
        disabled_color = '#6c757d'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            disabled_color = getattr(self.theme_manager.current_theme, 'text_disabled', disabled_color)

        self.status_label.setText("PKI Authentication Disabled")
        self.status_label.setStyleSheet(f"color: {disabled_color}; font-weight: bold; font-size: 12px;")
        self.status_details.setText(
            "Standard authentication methods are in use.\n"
            "Enable PKI to use certificates from the Windows certificate store."
        )
        self.enable_button.setText("Enable PKI")
        self.test_button.setVisible(False)
        self.cert_selector_group.setVisible(True)
        self.cert_group.setVisible(False)

    def _show_error_status(self, error: str):
        error_color = '#dc3545'
        if self.theme_manager and hasattr(self.theme_manager, 'current_theme'):
            error_color = getattr(self.theme_manager.current_theme, 'status_error', error_color)

        self.status_label.setText("PKI Service Error")
        self.status_label.setStyleSheet(f"color: {error_color}; font-weight: bold; font-size: 12px;")
        self.status_details.setText(f"Error: {error}")
        self.enable_button.setText("Enable PKI")
        self.test_button.setVisible(False)
        self.cert_group.setVisible(False)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_pki(self):
        try:
            if self._current_status and self._current_status.get('enabled'):
                reply = QMessageBox.question(
                    self, "Disable PKI",
                    "Disable PKI authentication?\nThis will switch to standard auth.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    pki_service.disable_pki_authentication()
                    self.pki_status_changed.emit(False)
                    self._refresh_status()
            else:
                # Enable — check if a specific cert is selected
                idx = self.cert_combo.currentIndex()
                if idx > 0 and self._certs:
                    cert = self._certs[idx - 1]
                    ok, err = pki_service.select_cert_by_thumbprint(cert.thumbprint)
                else:
                    ok, err = pki_service.enable_auto_detect()

                if ok:
                    QMessageBox.information(self, "PKI Enabled", "PKI authentication has been enabled.")
                    self.pki_status_changed.emit(True)
                else:
                    QMessageBox.warning(self, "PKI Error", f"Failed to enable PKI:\n{err}")

                self._refresh_status()

        except Exception as e:
            logger.error(f"Failed to toggle PKI: {e}")
            QMessageBox.critical(self, "Error", f"Failed to toggle PKI:\n{e}")

    def _test_connection(self):
        from ...infrastructure.ai.api_test_service import test_network_connection_consolidated
        from ...infrastructure.storage.settings_manager import settings

        try:
            url, ok = QInputDialog.getText(
                self, "Test PKI Connection",
                "Enter URL to test PKI authentication:",
                text="https://your-api-server.com/health"
            )

            if ok and url.strip():
                ignore_ssl = settings.get('advanced.ignore_ssl_verification', False)

                from PyQt6.QtWidgets import QProgressDialog, QApplication

                progress = QProgressDialog("Testing PKI connection...", None, 0, 0, self)
                progress.setWindowTitle("Testing Connection")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                progress.show()
                QApplication.processEvents()

                try:
                    result = test_network_connection_consolidated(
                        base_url=url.strip(),
                        api_key="test",
                        model_name="test-model",
                        ignore_ssl=ignore_ssl,
                        max_attempts=3,
                        timeout=15
                    )
                    progress.close()

                    if result.success:
                        QMessageBox.information(self, "Success", f"PKI connection test successful!\nURL: {url}")
                    else:
                        QMessageBox.warning(self, "Failed", f"PKI test failed:\n{result.message}")
                except Exception as e:
                    progress.close()
                    raise e

        except Exception as e:
            logger.error(f"PKI connection test failed: {e}")
            QMessageBox.critical(self, "Error", f"Connection test failed:\n{e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pki_status(self) -> Optional[Dict[str, Any]]:
        return self._current_status

    def cleanup(self):
        logger.debug("PKI Settings Widget cleaned up")
