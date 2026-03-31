"""
PKI Setup Wizard for Specter.

Simplified wizard that shows certificates from the Windows cert store
and lets the user enable PKI with one click.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit,
    QGroupBox, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt

from ...infrastructure.pki import pki_service
from ...infrastructure.ai.session_manager import enumerate_client_certs, CertStoreEntry

logger = logging.getLogger("specter.pki.wizard")

try:
    from ...ui.themes.theme_manager import get_theme_manager
    THEME_SYSTEM_AVAILABLE = True
except ImportError:
    THEME_SYSTEM_AVAILABLE = False


class PKISetupWizard(QDialog):
    """
    Simplified PKI setup — browse Windows cert store and enable PKI.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Specter — PKI Authentication Setup")
        self.resize(550, 400)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._certs = []
        self._selected_cert: Optional[CertStoreEntry] = None
        self._result: Optional[bool] = None

        self._init_ui()
        self._apply_styling()
        self._populate_certs()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QLabel("Certificate Store Authentication")
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(header)

        desc = QLabel(
            "Specter can use client certificates from the Windows certificate store "
            "for enterprise API authentication. Select a certificate below or let "
            "Specter auto-detect the best one."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Cert selector
        cert_group = QGroupBox("Available Certificates")
        cert_layout = QVBoxLayout()

        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Certificate:"))
        self.cert_combo = QComboBox()
        self.cert_combo.setMinimumWidth(350)
        self.cert_combo.currentIndexChanged.connect(self._on_cert_changed)
        combo_row.addWidget(self.cert_combo, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(70)
        self.refresh_btn.clicked.connect(self._populate_certs)
        combo_row.addWidget(self.refresh_btn)

        cert_layout.addLayout(combo_row)
        cert_group.setLayout(cert_layout)
        layout.addWidget(cert_group)

        # Details
        details_group = QGroupBox("Certificate Details")
        details_layout = QVBoxLayout()
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        self.details_text.setPlaceholderText("Select a certificate to see details")
        details_layout.addWidget(self.details_text)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Buttons
        button_box = QDialogButtonBox()
        self.enable_btn = QPushButton("Enable PKI")
        self.enable_btn.setDefault(True)
        self.skip_btn = QPushButton("Skip (Standard Auth)")
        button_box.addButton(self.enable_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(self.skip_btn, QDialogButtonBox.ButtonRole.RejectRole)
        self.enable_btn.clicked.connect(self._enable_pki)
        self.skip_btn.clicked.connect(self._skip_pki)
        layout.addWidget(button_box)

    def _apply_styling(self):
        theme_manager = None
        if THEME_SYSTEM_AVAILABLE:
            try:
                theme_manager = get_theme_manager()
            except Exception:
                pass

        if theme_manager and hasattr(theme_manager, 'current_theme'):
            colors = theme_manager.current_theme
            self.setStyleSheet(f"""
            QDialog {{ background-color: {colors.background_primary}; color: {colors.text_primary}; }}
            QGroupBox {{
                color: {colors.text_primary}; border: 1px solid {colors.border_primary};
                border-radius: 4px; margin-top: 10px; padding-top: 10px;
                font-weight: bold; font-size: 12px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 8px; }}
            QLabel {{ color: {colors.text_primary}; }}
            QPushButton {{
                background-color: {colors.interactive_normal}; border: 1px solid {colors.border_primary};
                color: {colors.text_primary}; padding: 8px 16px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {colors.interactive_hover}; }}
            QComboBox {{
                background-color: {colors.background_tertiary}; border: 1px solid {colors.border_primary};
                color: {colors.text_primary}; padding: 4px 8px; border-radius: 3px;
            }}
            QTextEdit {{
                background-color: {colors.background_tertiary}; border: 1px solid {colors.border_primary};
                color: {colors.text_primary}; border-radius: 3px; font-family: Consolas, monospace; font-size: 10px;
            }}
            """)

    def _populate_certs(self):
        self.cert_combo.blockSignals(True)
        self.cert_combo.clear()

        self._certs = enumerate_client_certs()

        if not self._certs:
            self.cert_combo.addItem("(No certificates found in Windows store)")
            self.cert_combo.setEnabled(False)
            self.enable_btn.setEnabled(False)
            self.details_text.setText(
                "No client certificates with private keys were found.\n\n"
                "Ensure your enterprise certificate is installed in the "
                "Windows certificate store (Current User > Personal)."
            )
        else:
            self.cert_combo.setEnabled(True)
            self.enable_btn.setEnabled(True)
            self.cert_combo.addItem(f"(Auto-detect — {len(self._certs)} cert(s) available)")
            for cert in self._certs:
                cn = cert.subject.split("CN=")[-1].split(",")[0] if "CN=" in cert.subject else cert.subject
                self.cert_combo.addItem(f"{cn}  [{cert.thumbprint[:12]}...]")

        self.cert_combo.blockSignals(False)
        self._on_cert_changed(0)

    def _on_cert_changed(self, index):
        if index <= 0 or not self._certs:
            self._selected_cert = None
            if self._certs:
                # Show what auto-detect would pick
                from ...infrastructure.ai.session_manager import find_best_client_cert
                best = find_best_client_cert()
                if best:
                    self._show_details(best, auto=True)
                else:
                    self.details_text.clear()
            return

        cert = self._certs[index - 1]
        self._selected_cert = cert
        self._show_details(cert)

    def _show_details(self, cert: CertStoreEntry, auto=False):
        prefix = "(Auto-detected) " if auto else ""
        eku = ", ".join(cert.enhanced_key_usage) if cert.enhanced_key_usage else "Not specified"
        self.details_text.setText(
            f"{prefix}Subject: {cert.subject}\n"
            f"Issuer: {cert.issuer}\n"
            f"Thumbprint: {cert.thumbprint}\n"
            f"Valid: {cert.not_before} to {cert.not_after}\n"
            f"Key Usage: {eku}\n"
            f"Has Private Key: {cert.has_private_key}"
        )

    def _enable_pki(self):
        try:
            if self._selected_cert:
                ok, err = pki_service.select_cert_by_thumbprint(self._selected_cert.thumbprint)
            else:
                ok, err = pki_service.enable_auto_detect()

            if ok:
                self._result = True
                self.accept()
            else:
                QMessageBox.warning(self, "PKI Error", f"Failed to enable PKI:\n{err}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to enable PKI:\n{e}")

    def _skip_pki(self):
        self._result = False
        self.reject()

    def get_result(self) -> Optional[bool]:
        """True = PKI enabled, False = skipped, None = cancelled."""
        return self._result


def show_pki_wizard(parent=None) -> Optional[bool]:
    """Show the PKI setup wizard and return the result."""
    wizard = PKISetupWizard(parent)
    wizard.exec()
    return wizard.get_result()
