"""
PKI Service for Specter.

Simplified PKI service that auto-detects client certificates from the
Windows certificate store. No manual P12 import or PEM extraction needed —
the session manager handles cert store enumeration and export automatically.
"""

import logging
from typing import Optional, Dict, Any, Tuple, List

from ..ai.session_manager import session_manager, enumerate_client_certs, find_best_client_cert, CertStoreEntry

logger = logging.getLogger("specter.pki.service")


class PKIService:
    """
    High-level PKI service for enterprise authentication.

    Uses the Windows certificate store for zero-config client auth:
    - Auto-detects client certs with private keys
    - Optional thumbprint override via settings
    - Delegates all HTTP config to the unified SessionManager
    """

    def __init__(self):
        self._initialized = False
        self._detected_cert: Optional[CertStoreEntry] = None
        logger.info("PKI Service initialized")

    def initialize(self) -> bool:
        """
        Initialize PKI service — triggers cert store detection and
        applies config to the session manager.

        Returns True if PKI is enabled (cert found or configured).
        """
        if self._initialized:
            return self.is_pki_enabled()

        try:
            from ..storage.settings_manager import settings
            pki = settings.get('pki', {})

            if not pki.get('enabled', False):
                logger.info("PKI service initialized — authentication disabled")
                self._initialized = True
                return True

            # Trigger session manager to detect / apply cert
            session_manager.reconfigure_security()
            self._detected_cert = session_manager.detected_cert

            if self._detected_cert:
                logger.info(f"PKI service initialized — using cert: {self._detected_cert.subject}")
            else:
                logger.warning("PKI enabled but no suitable cert found in Windows store")

            self._initialized = True
            return self._detected_cert is not None

        except Exception as e:
            logger.error(f"PKI service initialization failed: {e}")
            self._initialized = False
            return False

    def reset_initialization(self):
        """Reset initialization state to allow re-initialization."""
        self._initialized = False
        self._detected_cert = None
        logger.debug("PKI service initialization state reset")

    # ------------------------------------------------------------------
    # Certificate store queries
    # ------------------------------------------------------------------

    def list_available_certs(self) -> List[CertStoreEntry]:
        """List all client-auth certificates in the Windows cert store."""
        return enumerate_client_certs()

    def get_detected_cert(self) -> Optional[CertStoreEntry]:
        """Get the currently detected / active certificate."""
        return session_manager.detected_cert

    def select_cert_by_thumbprint(self, thumbprint: str) -> Tuple[bool, Optional[str]]:
        """
        Select a specific certificate by thumbprint and persist the choice.

        Returns (success, error_message).
        """
        try:
            from ..storage.settings_manager import settings

            # Verify the cert exists
            cert = find_best_client_cert(thumbprint_hint=thumbprint)
            if not cert:
                return False, f"No certificate found with thumbprint {thumbprint}"

            # Persist
            settings.set('pki.enabled', True)
            settings.set('pki.thumbprint', thumbprint)
            settings.set('pki.auto_detect', False)
            settings.save()

            # Apply
            session_manager.reconfigure_security()
            self._detected_cert = session_manager.detected_cert

            logger.info(f"Selected cert: {cert.subject} ({thumbprint[:16]}...)")
            return True, None

        except Exception as e:
            return False, str(e)

    def enable_auto_detect(self) -> Tuple[bool, Optional[str]]:
        """Enable auto-detection (clear thumbprint override)."""
        try:
            from ..storage.settings_manager import settings
            settings.set('pki.enabled', True)
            settings.set('pki.auto_detect', True)
            settings.set('pki.thumbprint', None)
            settings.save()

            session_manager.reconfigure_security()
            self._detected_cert = session_manager.detected_cert

            if self._detected_cert:
                return True, None
            return False, "No suitable client cert found in Windows store"

        except Exception as e:
            return False, str(e)

    def disable_pki_authentication(self) -> bool:
        """Disable PKI authentication."""
        try:
            from ..storage.settings_manager import settings
            settings.set('pki.enabled', False)
            settings.save()

            session_manager.reconfigure_security()
            self._detected_cert = None
            self.reset_initialization()

            logger.info("PKI authentication disabled")
            return True

        except Exception as e:
            logger.error(f"Failed to disable PKI: {e}")
            return False

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def is_pki_enabled(self) -> bool:
        """Check if PKI is enabled in settings."""
        try:
            from ..storage.settings_manager import settings
            return settings.get('pki.enabled', False)
        except Exception:
            return False

    def get_certificate_status(self) -> Dict[str, Any]:
        """Get comprehensive certificate status."""
        status = {
            'enabled': False,
            'method': 'certstore',
            'auto_detect': True,
            'cert_found': False,
            'subject': None,
            'issuer': None,
            'thumbprint': None,
            'not_before': None,
            'not_after': None,
            'enhanced_key_usage': [],
            'available_certs': 0,
            'errors': [],
            'warnings': [],
        }

        try:
            from ..storage.settings_manager import settings
            pki = settings.get('pki', {})

            status['enabled'] = pki.get('enabled', False)
            status['auto_detect'] = pki.get('auto_detect', True)

            if not status['enabled']:
                return status

            # Get detected cert from session manager
            detected = session_manager.detected_cert
            if detected:
                status['cert_found'] = True
                status['subject'] = detected.subject
                status['issuer'] = detected.issuer
                status['thumbprint'] = detected.thumbprint
                status['not_before'] = detected.not_before
                status['not_after'] = detected.not_after
                status['enhanced_key_usage'] = detected.enhanced_key_usage
            else:
                status['errors'].append("No suitable client certificate found in Windows store")

            # Count available certs
            try:
                all_certs = enumerate_client_certs()
                status['available_certs'] = len(all_certs)
            except Exception:
                pass

        except Exception as e:
            status['errors'].append(f"Status check failed: {e}")

        return status

    def test_pki_connection(self, test_url: str, max_attempts: int = 3) -> Tuple[bool, Optional[str]]:
        """
        Test PKI authentication with a given URL.

        Returns (success, error_message).
        """
        if not self.is_pki_enabled():
            return False, "PKI is not enabled"

        detected = session_manager.detected_cert
        if not detected:
            return False, "No client certificate detected"

        logger.info(f"Testing PKI connection to: {test_url}")

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = session_manager.make_request(
                    method="GET", url=test_url, timeout=10
                )
                if response.status_code < 400:
                    logger.info(f"PKI connection test successful on attempt {attempt}")
                    return True, None
                last_error = f"HTTP {response.status_code}: {response.reason}"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"PKI test attempt {attempt} failed: {e}")

            if attempt < max_attempts:
                import time
                time.sleep(2)

        from ..ai.api_test_service import _get_user_friendly_error
        friendly = _get_user_friendly_error(last_error) if last_error else "Unknown error"
        return False, f"PKI connection failed after {max_attempts} attempts: {friendly}"

    def get_certificate_expiry_warning(self) -> Optional[str]:
        """Get expiry warning if cert is expiring soon."""
        detected = session_manager.detected_cert
        if not detected or not detected.not_after:
            return None
        try:
            from datetime import datetime, timezone
            expiry = datetime.fromisoformat(detected.not_after.replace('Z', '+00:00'))
            days = (expiry - datetime.now(timezone.utc)).days
            if days <= 30:
                return f"Certificate expires in {days} days"
        except Exception:
            pass
        return None

    def shutdown(self):
        """Shutdown PKI service."""
        logger.info("PKI service shut down")


# Global PKI service instance
pki_service = PKIService()
