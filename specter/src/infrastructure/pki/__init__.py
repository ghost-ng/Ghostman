"""
PKI (Public Key Infrastructure) module for Specter.

Uses the Windows certificate store for zero-config enterprise authentication.
"""

from .pki_service import PKIService, pki_service
from ..ai.session_manager import CertStoreEntry

# Legacy exception kept for backwards compatibility with UI code
class PKIError(Exception):
    """Base PKI exception."""
    pass

# Legacy compat — CertificateInfo is now CertStoreEntry
CertificateInfo = CertStoreEntry

__all__ = [
    'PKIService',
    'pki_service',
    'PKIError',
    'CertStoreEntry',
    'CertificateInfo',
]
