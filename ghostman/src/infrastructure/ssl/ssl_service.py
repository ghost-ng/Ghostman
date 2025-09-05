"""
Unified SSL Verification Service for Ghostman.

Provides centralized SSL/TLS verification management that integrates with:
- Application settings (ignore_ssl_verification)
- PKI certificate management (custom CA chains)
- Session manager configuration
- All web requests throughout the application
"""

import logging
from typing import Optional, Union, Dict, Any
from pathlib import Path

logger = logging.getLogger("ghostman.ssl.service")


class SSLVerificationService:
    """
    Centralized SSL verification management service.
    
    Handles SSL verification settings across the entire application,
    including integration with PKI certificates and user preferences.
    """
    
    def __init__(self):
        """Initialize SSL verification service."""
        self._ignore_ssl: bool = False
        self._custom_ca_path: Optional[str] = None
        self._initialized: bool = False
        logger.info("SSL Verification Service initialized")
    
    def configure(self, ignore_ssl: bool = False, custom_ca_path: Optional[str] = None) -> None:
        """
        Configure SSL verification settings.
        
        Args:
            ignore_ssl: If True, disable all SSL certificate verification
            custom_ca_path: Path to custom CA certificate chain file for verification
        """
        self._ignore_ssl = ignore_ssl
        self._custom_ca_path = custom_ca_path
        self._initialized = True
        
        if ignore_ssl:
            logger.info("🔒 SSL verification DISABLED globally")
            # Suppress SSL warnings when verification is disabled
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                pass
        else:
            if custom_ca_path:
                logger.info(f"🔒 SSL verification ENABLED with custom CA: {custom_ca_path}")
            else:
                logger.info("🔒 SSL verification ENABLED with system CA bundle")
    
    def get_verify_parameter(self) -> Union[bool, str]:
        """
        Get the appropriate verify parameter for requests.
        
        Returns:
            - False if SSL verification is disabled
            - str (CA path) if custom CA chain is configured
            - True for default SSL verification
        """
        if not self._initialized:
            logger.warning("SSL service not configured, using default verification")
            return True
        
        if self._ignore_ssl:
            return False
        
        if self._custom_ca_path and Path(self._custom_ca_path).exists():
            return self._custom_ca_path
        
        return True
    
    def is_ssl_verification_enabled(self) -> bool:
        """
        Check if SSL verification is enabled.
        
        Returns:
            True if SSL verification is enabled
        """
        return not self._ignore_ssl
    
    def get_custom_ca_path(self) -> Optional[str]:
        """
        Get the path to custom CA certificate chain.
        
        Returns:
            Path to custom CA chain or None
        """
        return self._custom_ca_path
    
    def configure_session_manager(self) -> bool:
        """
        Configure the global session manager with current SSL settings.
        
        Returns:
            True if configuration was successful
        """
        try:
            from ..ai.session_manager import session_manager
            
            # Configure session manager with SSL settings
            session_manager.configure_session(
                disable_ssl_verification=self._ignore_ssl
            )
            
            # If we have a custom CA and SSL verification is enabled,
            # we need to set it on the session
            if not self._ignore_ssl and self._custom_ca_path:
                try:
                    with session_manager.get_session() as session:
                        session.verify = self._custom_ca_path
                    logger.debug(f"Session configured to use custom CA: {self._custom_ca_path}")
                except Exception as e:
                    logger.error(f"Failed to configure custom CA in session: {e}")
                    return False
            
            logger.debug("Session manager configured with SSL settings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure session manager: {e}")
            return False
    
    def configure_from_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Configure SSL verification from application settings.
        
        Args:
            settings: Application settings dictionary
            
        Returns:
            True if configuration was successful
        """
        try:
            # Get ignore_ssl setting from advanced config
            ignore_ssl = settings.get('advanced', {}).get('ignore_ssl_verification', False)
            
            # Get PKI CA chain path if available
            custom_ca_path = None
            try:
                from ..pki.pki_service import pki_service
                if pki_service.cert_manager.is_pki_enabled():
                    custom_ca_path = pki_service.cert_manager.get_ca_chain_file()
            except Exception as e:
                logger.debug(f"Could not get PKI CA chain: {e}")
            
            # Configure SSL service
            self.configure(ignore_ssl=ignore_ssl, custom_ca_path=custom_ca_path)
            
            # Apply to session manager
            if not self.configure_session_manager():
                logger.warning("Failed to apply SSL settings to session manager")
                return False
            
            logger.info(f"✓ SSL verification configured from settings: ignore={ignore_ssl}, custom_ca={bool(custom_ca_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure SSL from settings: {e}")
            return False
    
    def configure_from_pki_service(self) -> bool:
        """
        Update SSL configuration when PKI settings change.
        
        Returns:
            True if configuration was successful
        """
        try:
            from ..pki.pki_service import pki_service
            
            # Get current PKI CA chain
            custom_ca_path = None
            if pki_service.cert_manager.is_pki_enabled():
                custom_ca_path = pki_service.cert_manager.get_ca_chain_file()
            
            # Update CA path but keep ignore_ssl setting
            self._custom_ca_path = custom_ca_path
            
            # Apply to session manager
            if not self.configure_session_manager():
                logger.warning("Failed to apply updated SSL settings to session manager")
                return False
            
            logger.info(f"✓ SSL verification updated from PKI service: custom_ca={bool(custom_ca_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure SSL from PKI service: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current SSL verification status.
        
        Returns:
            Dictionary with SSL status information
        """
        status = {
            'initialized': self._initialized,
            'ssl_verification_enabled': not self._ignore_ssl,
            'ignore_ssl': self._ignore_ssl,
            'custom_ca_configured': bool(self._custom_ca_path),
            'custom_ca_path': self._custom_ca_path,
            'verify_parameter': self.get_verify_parameter() if self._initialized else None
        }
        
        # Check if custom CA file exists
        if self._custom_ca_path:
            status['custom_ca_exists'] = Path(self._custom_ca_path).exists()
        
        return status
    
    def test_ssl_configuration(self, test_url: str = "https://www.google.com") -> Dict[str, Any]:
        """
        Test current SSL configuration with a simple request.
        
        Args:
            test_url: URL to test SSL configuration against
            
        Returns:
            Dictionary with test results
        """
        result = {
            'success': False,
            'url': test_url,
            'error': None,
            'ssl_enabled': not self._ignore_ssl,
            'custom_ca_used': bool(self._custom_ca_path and not self._ignore_ssl)
        }
        
        try:
            from ..ai.session_manager import session_manager
            
            # Make a test request
            response = session_manager.make_request(
                method="GET",
                url=test_url,
                timeout=10
            )
            
            if response.status_code < 400:
                result['success'] = True
                result['status_code'] = response.status_code
                logger.info(f"✓ SSL configuration test successful: {test_url}")
            else:
                result['error'] = f"HTTP {response.status_code}"
                logger.warning(f"⚠ SSL test returned HTTP {response.status_code}: {test_url}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ SSL configuration test failed: {e}")
        
        return result


def make_ssl_aware_request(method: str, url: str, **kwargs) -> 'requests.Response':
    """
    Make an SSL-aware HTTP request using current SSL configuration.
    
    This is a convenience function that automatically applies the correct
    SSL verification settings based on the current SSL service configuration.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        **kwargs: Additional arguments passed to the request
        
    Returns:
        requests.Response: The response object
        
    Raises:
        requests.RequestException: For request-related errors
    """
    from ..ai.session_manager import session_manager
    
    # Ensure SSL service is configured
    if not ssl_service._initialized:
        try:
            # Try to initialize from settings
            from ...application.settings import settings
            ssl_service.configure_from_settings(settings.get_all_settings())
        except Exception as e:
            logger.warning(f"Could not auto-initialize SSL service: {e}")
    
    # Make request using session manager (which should already be configured by SSL service)
    return session_manager.make_request(method=method, url=url, **kwargs)


# Global SSL service instance
ssl_service = SSLVerificationService()