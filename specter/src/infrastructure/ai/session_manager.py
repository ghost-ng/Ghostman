"""
Centralized Session Manager for HTTP requests in Specter.

Provides thread-safe session management with connection pooling,
retry logic, Windows cert store PKI auto-detection, and proper
resource cleanup for the requests library.
"""

import threading
import logging
import os
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("specter.session_manager")


# ---------------------------------------------------------------------------
# Windows Certificate Store helpers
# ---------------------------------------------------------------------------

@dataclass
class CertStoreEntry:
    """A client-authentication certificate found in the Windows cert store."""
    thumbprint: str
    subject: str
    issuer: str
    not_before: str
    not_after: str
    has_private_key: bool
    enhanced_key_usage: List[str] = field(default_factory=list)


def enumerate_client_certs() -> List[CertStoreEntry]:
    """
    Enumerate certificates in the Windows CurrentUser\\My store that have
    a private key and are suitable for client authentication.

    Returns an empty list on non-Windows platforms or if enumeration fails.
    """
    if os.name != 'nt':
        return []

    # Use PowerShell to enumerate — works on all Windows without extra packages
    try:
        import subprocess
        import json as _json
        import re

        ps_script = r"""
$certs = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.HasPrivateKey } |
    ForEach-Object {
        $eku = @()
        if ($_.EnhancedKeyUsageList) {
            $eku = $_.EnhancedKeyUsageList | ForEach-Object { $_.FriendlyName }
        }
        [PSCustomObject]@{
            Thumbprint     = $_.Thumbprint
            Subject        = $_.Subject
            Issuer         = $_.Issuer
            NotBefore      = $_.NotBefore.ToString('o')
            NotAfter       = $_.NotAfter.ToString('o')
            HasPrivateKey  = $_.HasPrivateKey
            EKU            = $eku
        }
    }
$certs | ConvertTo-Json -Depth 3
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
        )

        if result.returncode != 0 or not result.stdout.strip():
            logger.debug("PowerShell cert enumeration returned no results")
            return []

        raw = _json.loads(result.stdout)
        # PowerShell returns a single object (not array) when there's exactly 1 cert
        if isinstance(raw, dict):
            raw = [raw]

        entries: List[CertStoreEntry] = []
        for item in raw:
            eku = item.get("EKU") or []
            if isinstance(eku, str):
                eku = [eku]
            elif not isinstance(eku, list):
                eku = []
            entries.append(CertStoreEntry(
                thumbprint=item["Thumbprint"],
                subject=item.get("Subject", ""),
                issuer=item.get("Issuer", ""),
                not_before=item.get("NotBefore", ""),
                not_after=item.get("NotAfter", ""),
                has_private_key=item.get("HasPrivateKey", False),
                enhanced_key_usage=eku,
            ))

        logger.info(f"Found {len(entries)} client cert(s) in Windows cert store")
        return entries

    except Exception as e:
        logger.warning(f"Failed to enumerate Windows cert store: {e}")
        return []


def find_best_client_cert(
    thumbprint_hint: Optional[str] = None,
) -> Optional[CertStoreEntry]:
    """
    Find the best client-authentication certificate.

    If *thumbprint_hint* is given and matches a cert, that cert is returned.
    Otherwise the first cert with a Client Authentication EKU is returned.
    Falls back to the first cert with a private key.
    """
    certs = enumerate_client_certs()
    if not certs:
        return None

    # Exact thumbprint match
    if thumbprint_hint:
        thumb_upper = thumbprint_hint.upper().replace(" ", "")
        for c in certs:
            if c.thumbprint.upper() == thumb_upper:
                logger.info(f"Matched cert by thumbprint: {c.subject}")
                return c
        logger.warning(f"No cert matched thumbprint {thumbprint_hint}")

    # Prefer certs with Client Authentication EKU
    for c in certs:
        if "Client Authentication" in c.enhanced_key_usage:
            logger.info(f"Auto-detected client auth cert: {c.subject}")
            return c

    # Fallback: first cert with private key
    logger.info(f"Using first available cert: {certs[0].subject}")
    return certs[0]


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------

class SessionManager:
    """
    Thread-safe session manager for HTTP requests.

    Features:
    - Single session object shared across the application
    - Connection pooling with HTTPAdapter
    - Thread-safe access with proper locking
    - Retry logic with exponential backoff
    - Windows cert store auto-detection for PKI
    - Proper resource cleanup
    """

    _instance: Optional['SessionManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'SessionManager':
        """Singleton pattern to ensure single session manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the session manager (called only once due to singleton)."""
        if self._initialized:
            return

        self._session: Optional[requests.Session] = None
        self._session_lock = threading.RLock()  # Reentrant lock for nested calls
        self._adapters: Dict[str, HTTPAdapter] = {}
        self._default_timeout = 30
        # Detected cert from Windows store (populated by reconfigure_security)
        self._detected_cert: Optional[CertStoreEntry] = None
        self._initialized = True

        # Auto-register for settings changes (lazy import avoids circular dep at module load)
        try:
            from ..storage.settings_manager import settings
            settings.on_change(self._on_settings_changed)
        except Exception:
            logger.debug("Cannot register settings listener during init (will be wired later)")

        logger.info("SessionManager initialized")

    # ------------------------------------------------------------------
    # Session configuration
    # ------------------------------------------------------------------

    def configure_session(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        pool_block: bool = False,
    ) -> None:
        """
        Configure the session with connection pooling and retry settings.
        """
        with self._session_lock:
            # Close existing session if it exists
            if self._session:
                self._close_session()

            # Create new session
            self._session = requests.Session()
            self._default_timeout = timeout

            # Configure retry strategy
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            )

            # Create HTTP/HTTPS adapters with connection pooling
            http_adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                pool_block=pool_block
            )
            https_adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                pool_block=pool_block
            )

            self._session.mount("http://", http_adapter)
            self._session.mount("https://", https_adapter)

            self._adapters = {
                "http": http_adapter,
                "https": https_adapter
            }

            # Set default headers
            self._session.headers.update({
                "User-Agent": "Specter/1.0.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })

            logger.debug(f"Session configured: timeout={timeout}s, retries={max_retries}, pool_size={pool_maxsize}")

            # Apply security config inside the lock
            self.reconfigure_security()

    # ------------------------------------------------------------------
    # Unified security configuration — THE single method
    # ------------------------------------------------------------------

    def _compute_security_config(self) -> Dict[str, Any]:
        """
        Compute the full security configuration by reading from SettingsManager.

        Returns dict with:
          'verify': bool | str   — False to skip verification, CA path, or True
          'cert':   tuple | None — (cert_path, key_path) for PEM-based PKI
          'thumbprint': str | None — Windows cert store thumbprint
        """
        try:
            from ..storage.settings_manager import settings
        except Exception:
            logger.warning("Cannot import SettingsManager — using safe defaults")
            return {'verify': True, 'cert': None, 'thumbprint': None}

        all_settings = settings.get_all()

        # --- SSL verification ---
        ignore_ssl = all_settings.get('advanced', {}).get('ignore_ssl_verification', False)

        # --- PKI configuration ---
        pki = all_settings.get('pki', {})
        pki_enabled = pki.get('enabled', False)
        auto_detect = pki.get('auto_detect', True)
        thumbprint = pki.get('thumbprint') or None
        # Legacy PEM paths (backwards compat with old P12-extracted files)
        cert_path = pki.get('client_cert_path')
        key_path = pki.get('client_key_path')
        ca_path = pki.get('ca_chain_path')

        # Compute verify parameter
        if ignore_ssl:
            verify = False
        elif pki_enabled and ca_path and os.path.exists(ca_path):
            verify = ca_path  # PKI CA chain takes precedence
        else:
            verify = True  # System CA bundle

        # Compute cert / thumbprint
        cert = None
        resolved_thumbprint = None

        if pki_enabled:
            if auto_detect or thumbprint:
                # Windows cert store approach (preferred)
                resolved_thumbprint = thumbprint  # may be None → auto-detect
            elif cert_path and key_path:
                # Legacy PEM file approach
                if os.path.exists(cert_path) and os.path.exists(key_path):
                    cert = (cert_path, key_path)
                else:
                    missing = []
                    if not os.path.exists(cert_path):
                        missing.append(f"cert={cert_path}")
                    if not os.path.exists(key_path):
                        missing.append(f"key={key_path}")
                    logger.warning(f"PKI enabled but cert files not found: {', '.join(missing)}")

        return {'verify': verify, 'cert': cert, 'thumbprint': resolved_thumbprint}

    def reconfigure_security(self) -> None:
        """
        Single entry point for ALL security configuration changes.

        Reads PKI and SSL settings from SettingsManager, auto-detects
        certs from the Windows store if configured, validates cert files,
        dirty-checks against current state, and applies atomically.

        Safe to call repeatedly — no-ops when nothing changed.
        """
        config = self._compute_security_config()

        with self._session_lock:
            if not self._session:
                logger.debug("Security config computed (session not yet created)")
                return

            # Handle Windows cert store PKI
            if config['thumbprint'] is not None or (
                config['cert'] is None and config.get('thumbprint') is None
                and self._should_auto_detect_pki()
            ):
                self._apply_certstore_pki(config)
            else:
                # Legacy PEM-based or no PKI
                self._detected_cert = None

            # Apply PEM cert if provided (legacy path)
            new_cert = config['cert']
            new_verify = config['verify']

            # Dirty check — skip if nothing changed
            current_verify = self._session.verify
            current_cert = self._session.cert
            if current_verify == new_verify and current_cert == new_cert and not config.get('thumbprint'):
                logger.debug("Security config unchanged, skipping reconfiguration")
                return

            # Apply atomically
            self._session.cert = new_cert
            self._session.verify = new_verify

            # Suppress urllib3 warnings when SSL is disabled
            if new_verify is False:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                logger.info(f"Security reconfigured: SSL verification DISABLED, "
                            f"PKI={'CertStore' if self._detected_cert else ('PEM' if new_cert else 'No')}")
            elif isinstance(new_verify, str):
                logger.info(f"Security reconfigured: custom CA={new_verify}, "
                            f"PKI={'CertStore' if self._detected_cert else ('PEM' if new_cert else 'No')}")
            else:
                logger.info(f"Security reconfigured: system CA bundle, "
                            f"PKI={'CertStore' if self._detected_cert else ('PEM' if new_cert else 'No')}")

    def _should_auto_detect_pki(self) -> bool:
        """Check if PKI auto-detect is enabled in settings."""
        try:
            from ..storage.settings_manager import settings
            pki = settings.get('pki', {})
            return pki.get('enabled', False) and pki.get('auto_detect', True)
        except Exception:
            return False

    def _apply_certstore_pki(self, config: Dict[str, Any]) -> None:
        """Auto-detect and apply a cert from the Windows cert store."""
        thumbprint = config.get('thumbprint')
        cert_entry = find_best_client_cert(thumbprint_hint=thumbprint)

        if cert_entry:
            self._detected_cert = cert_entry
            logger.info(f"PKI: using Windows cert store cert — "
                        f"subject={cert_entry.subject}, thumbprint={cert_entry.thumbprint[:16]}...")

            # For requests library: we need to use the cert store via SSLContext.
            # The simplest reliable approach: export the cert to temp PEM via PowerShell
            # and set session.cert. This happens once at startup / reconfigure.
            pem_paths = self._export_cert_to_temp_pem(cert_entry.thumbprint)
            if pem_paths:
                config['cert'] = pem_paths
            else:
                logger.warning("Could not export cert from store — PKI may not work for requests")
        else:
            self._detected_cert = None
            if thumbprint:
                logger.warning(f"No cert found for thumbprint {thumbprint}")
            else:
                logger.debug("No suitable client cert found in Windows store")

    def _export_cert_to_temp_pem(self, thumbprint: str):
        """
        Export a certificate + private key from the Windows cert store to
        PEM files that the requests library can use.

        The private key file has restricted ACLs (owner-only) on Windows.
        Returns (cert_path, key_path) or None on failure.
        """
        if os.name != 'nt':
            return None

        import re
        # Validate thumbprint is hex-only to prevent command injection
        if not re.match(r'^[A-Fa-f0-9]+$', thumbprint):
            logger.error(f"Invalid thumbprint format: {thumbprint}")
            return None

        pfx_path = None
        try:
            import subprocess

            appdata = os.environ.get('APPDATA', '')
            pki_dir = os.path.join(appdata, 'Specter', 'pki')
            os.makedirs(pki_dir, exist_ok=True)

            pfx_path = os.path.join(pki_dir, 'certstore_export.pfx')
            cert_pem_path = os.path.join(pki_dir, 'client.crt')
            key_pem_path = os.path.join(pki_dir, 'client.pem')

            # Export from cert store to PFX (temporary, cleaned up in finally)
            pfx_escaped = pfx_path.replace(chr(92), chr(92) + chr(92))
            ps_export = (
                f"$cert = Get-ChildItem Cert:\\CurrentUser\\My\\{thumbprint}\n"
                f"if ($cert) {{\n"
                f"    $bytes = $cert.Export("
                f"[System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, '')\n"
                f"    [System.IO.File]::WriteAllBytes('{pfx_escaped}', $bytes)\n"
                f"    Write-Output 'OK'\n"
                f"}} else {{ Write-Output 'NOT_FOUND' }}"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_export],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )

            if 'NOT_FOUND' in result.stdout or result.returncode != 0:
                logger.warning(f"PowerShell cert export failed: {result.stderr or result.stdout}")
                return None

            # Convert PFX to PEM using cryptography library
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.serialization import pkcs12

            with open(pfx_path, 'rb') as f:
                pfx_data = f.read()

            private_key, certificate, chain = pkcs12.load_key_and_certificates(pfx_data, b'')

            if not private_key or not certificate:
                logger.warning("Exported PFX missing key or certificate")
                return None

            # Write cert PEM
            with open(cert_pem_path, 'wb') as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
                if chain:
                    for ca_cert in chain:
                        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

            # Write key PEM
            with open(key_pem_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Restrict key file to owner-only access via Windows ACL
            try:
                subprocess.run(
                    ["icacls", key_pem_path, "/inheritance:r",
                     "/grant:r", f"{os.environ.get('USERNAME', 'OWNER')}:(R)"],
                    capture_output=True, timeout=5,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
            except Exception as acl_e:
                logger.debug(f"Could not restrict key file ACL: {acl_e}")

            logger.info(f"Exported cert store cert to PEM: {cert_pem_path}")
            return (cert_pem_path, key_pem_path)

        except Exception as e:
            logger.error(f"Failed to export cert from Windows store: {e}")
            return None
        finally:
            # Always clean up the PFX file (contains unencrypted private key)
            if pfx_path:
                try:
                    os.remove(pfx_path)
                except OSError:
                    pass

    def _on_settings_changed(self, key_path: str) -> None:
        """Callback for SettingsManager.on_change — triggers reconfigure for security keys."""
        _SECURITY_PREFIXES = ('pki.', 'advanced.ignore_ssl_verification', 'advanced.custom_ca_path')
        if key_path.startswith(_SECURITY_PREFIXES):
            logger.debug(f"Security-relevant setting changed: {key_path}")
            self.reconfigure_security()

    # ------------------------------------------------------------------
    # PKI info (public API)
    # ------------------------------------------------------------------

    def get_pki_info(self) -> Dict[str, Any]:
        """Get PKI configuration information."""
        with self._session_lock:
            info = {
                "pki_enabled": False,
                "method": None,
                "thumbprint": None,
                "subject": None,
                "cert_path": None,
                "key_path": None,
            }

            if self._detected_cert:
                info.update({
                    "pki_enabled": True,
                    "method": "certstore",
                    "thumbprint": self._detected_cert.thumbprint,
                    "subject": self._detected_cert.subject,
                })
            elif self._session and self._session.cert:
                cert_tuple = self._session.cert
                info.update({
                    "pki_enabled": True,
                    "method": "pem",
                    "cert_path": cert_tuple[0] if isinstance(cert_tuple, tuple) else cert_tuple,
                    "key_path": cert_tuple[1] if isinstance(cert_tuple, tuple) and len(cert_tuple) > 1 else None,
                })

            return info

    @property
    def detected_cert(self) -> Optional[CertStoreEntry]:
        """The currently active cert auto-detected from the Windows store (or None)."""
        return self._detected_cert

    # ------------------------------------------------------------------
    # Request API
    # ------------------------------------------------------------------

    @contextmanager
    def get_session(self):
        """Get the configured session in a thread-safe manner."""
        with self._session_lock:
            if self._session is None:
                raise RuntimeError("Session not configured. Call configure_session() first.")
            try:
                yield self._session
            except Exception as e:
                logger.error(f"Error during session usage: {e}")
                raise

    def make_request(
        self,
        method: str,
        url: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """Make an HTTP request using the managed session."""
        if timeout is None:
            timeout = self._default_timeout

        with self.get_session() as session:
            logger.debug(f"Making {method} request to {url}")
            try:
                response = session.request(
                    method=method,
                    url=url,
                    timeout=timeout,
                    **kwargs
                )
                logger.debug(f"Request completed: {method} {url} -> {response.status_code}")
                return response
            except requests.RequestException as e:
                logger.error(f"Request failed: {method} {url} -> {type(e).__name__}: {e}")
                raise

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update default headers for all requests."""
        with self._session_lock:
            if self._session:
                self._session.headers.update(headers)
                logger.debug(f"Headers updated: {list(headers.keys())}")
            else:
                logger.warning("Cannot update headers: session not configured")

    def remove_headers(self, header_names: list) -> None:
        """Remove specific headers from default headers."""
        with self._session_lock:
            if self._session:
                for header_name in header_names:
                    self._session.headers.pop(header_name, None)
                logger.debug(f"Headers removed: {header_names}")
            else:
                logger.warning("Cannot remove headers: session not configured")

    # ------------------------------------------------------------------
    # Connection info
    # ------------------------------------------------------------------

    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about current connection pools."""
        info = {
            "session_configured": self._session is not None,
            "adapters": list(self._adapters.keys()),
            "default_timeout": self._default_timeout,
            "pki_info": self.get_pki_info()
        }

        if self._session:
            info["headers"] = dict(self._session.headers)
            for scheme, adapter in self._adapters.items():
                if hasattr(adapter, 'config'):
                    info[f"{scheme}_adapter"] = {
                        "max_retries": getattr(adapter.max_retries, 'total', None),
                        "pool_connections": getattr(adapter, 'config', {}).get('pool_connections'),
                        "pool_maxsize": getattr(adapter, 'config', {}).get('pool_maxsize')
                    }

        return info

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _close_session(self) -> None:
        """Close the current session and clean up resources."""
        if self._session:
            try:
                self._session.close()
                logger.debug("Session closed")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._session = None
                self._adapters.clear()

    def close(self) -> None:
        """Close the session manager and clean up all resources."""
        with self._session_lock:
            self._close_session()
        logger.info("SessionManager closed")

    def __del__(self):
        """Destructor to ensure session is closed."""
        try:
            self.close()
        except Exception:
            pass

    @property
    def is_configured(self) -> bool:
        """Check if the session is configured and ready to use."""
        with self._session_lock:
            return self._session is not None

    # ------------------------------------------------------------------
    # Legacy compat shims (called by old code during transition)
    # ------------------------------------------------------------------

    def configure_pki(self, cert_path: str, key_path: str, ca_path: Optional[str] = None) -> None:
        """Legacy: configure PKI from PEM file paths. Prefer cert store approach."""
        with self._session_lock:
            logger.info(f"Legacy PKI configured: cert={cert_path}, key={key_path}")
            self.reconfigure_security()

    def disable_pki(self) -> None:
        """Legacy: disable PKI authentication."""
        with self._session_lock:
            self._detected_cert = None
            logger.info("PKI authentication disabled")
            self.reconfigure_security()


# Global session manager instance
session_manager = SessionManager()
