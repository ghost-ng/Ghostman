"""
SSL Verification Service for Specter — thin shim.

All real work is now done by session_manager.reconfigure_security().
This module exists for backwards compatibility with code that imports
ssl_service directly (settings_dialog, app_coordinator, api_test_service).
"""

import logging
from typing import Optional, Union, Dict, Any

logger = logging.getLogger("specter.ssl.service")


class SSLVerificationService:
    """
    Thin wrapper that delegates to SessionManager for all SSL config.
    Kept for API compatibility with existing callers.
    """

    def __init__(self):
        self._ignore_ssl: bool = False
        self._custom_ca_path: Optional[str] = None
        self._initialized: bool = False
        logger.info("SSL Verification Service initialized (shim)")

    def configure(self, ignore_ssl: bool = False, custom_ca_path: Optional[str] = None) -> None:
        """Configure SSL verification settings and push to session manager."""
        self._ignore_ssl = ignore_ssl
        self._custom_ca_path = custom_ca_path
        self._initialized = True

        if ignore_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                pass

        # Push to session manager
        self._push_to_session_manager()

    def _push_to_session_manager(self):
        """Trigger session manager to re-read settings."""
        try:
            from ..ai.session_manager import session_manager
            session_manager.reconfigure_security()
        except Exception as e:
            logger.warning(f"Failed to push SSL config to session manager: {e}")

    def get_verify_parameter(self) -> Union[bool, str]:
        if not self._initialized:
            return True
        if self._ignore_ssl:
            return False
        if self._custom_ca_path:
            from pathlib import Path
            if Path(self._custom_ca_path).exists():
                return self._custom_ca_path
        return True

    def is_ssl_verification_enabled(self) -> bool:
        return not self._ignore_ssl

    def get_custom_ca_path(self) -> Optional[str]:
        return self._custom_ca_path

    def configure_session_manager(self) -> bool:
        self._push_to_session_manager()
        return True

    def configure_from_settings(self, settings_dict: Dict[str, Any]) -> bool:
        """Configure from application settings dict."""
        try:
            ignore_ssl = settings_dict.get('advanced', {}).get('ignore_ssl_verification', False)
            self.configure(ignore_ssl=ignore_ssl)
            return True
        except Exception as e:
            logger.error(f"Failed to configure SSL from settings: {e}")
            return False

    def configure_from_pki_service(self) -> bool:
        self._push_to_session_manager()
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            'initialized': self._initialized,
            'ssl_verification_enabled': not self._ignore_ssl,
            'ignore_ssl': self._ignore_ssl,
            'custom_ca_configured': bool(self._custom_ca_path),
            'custom_ca_path': self._custom_ca_path,
            'verify_parameter': self.get_verify_parameter() if self._initialized else None
        }

    def test_ssl_configuration(self, test_url: str = "https://www.google.com") -> Dict[str, Any]:
        result = {
            'success': False, 'url': test_url, 'error': None,
            'ssl_enabled': not self._ignore_ssl,
        }
        try:
            from ..ai.session_manager import session_manager
            response = session_manager.make_request(method="GET", url=test_url, timeout=10)
            if response.status_code < 400:
                result['success'] = True
                result['status_code'] = response.status_code
        except Exception as e:
            result['error'] = str(e)
        return result


def make_ssl_aware_request(method: str, url: str, **kwargs):
    """Convenience wrapper — just delegates to session_manager."""
    from ..ai.session_manager import session_manager
    return session_manager.make_request(method=method, url=url, **kwargs)


# Global SSL service instance
ssl_service = SSLVerificationService()
