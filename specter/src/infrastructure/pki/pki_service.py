"""
PKI Service for Specter.

Coordinates PKI operations between certificate management and 
HTTP session configuration for seamless enterprise authentication.
"""

import logging
from typing import Optional, Dict, Any, Tuple

from .certificate_manager import CertificateManager, PKIError
from ..ai.session_manager import session_manager

logger = logging.getLogger("specter.pki.service")


class PKIService:
    """
    High-level PKI service for enterprise authentication.
    
    Coordinates between certificate management and HTTP session
    configuration to provide seamless PKI authentication.
    """
    
    def __init__(self):
        """Initialize PKI service."""
        self.cert_manager = CertificateManager()
        self._initialized = False
        logger.info("PKI Service initialized")
    
    def initialize(self) -> bool:
        """
        Initialize PKI service and apply configuration.
        
        Returns:
            True if PKI is enabled and configured
        """
        # If already initialized, just return current status silently
        if self._initialized:
            #logger.debug("PKI service already initialized, returning cached status")
            return self.cert_manager.is_pki_enabled()
        
        try:
            logger.debug("Initializing PKI service...")
            
            # Load current configuration
            self.cert_manager.load_config()
            
            # Apply PKI configuration if enabled
            if self.cert_manager.is_pki_enabled():
                success = self._apply_pki_to_session()
                if success:
                    logger.info("✓ PKI service initialized with authentication")
                else:
                    logger.warning("⚠ PKI service initialized but authentication failed")
                self._initialized = True
                return success
            else:
                logger.info("PKI service initialized without authentication")
                self._initialized = True
                return True
                
        except Exception as e:
            logger.error(f"✗ PKI service initialization failed: {e}")
            self._initialized = False
            return False
    
    def reset_initialization(self):
        """Reset initialization state to allow re-initialization after configuration changes."""
        self._initialized = False
        logger.debug("PKI service initialization state reset")
    
    def setup_pki_authentication(
        self, 
        p12_path: str, 
        password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Setup PKI authentication from P12 file.
        
        Args:
            p12_path: Path to P12 certificate file
            password: Password for P12 file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            logger.info("Setting up PKI authentication...")
            
            # Import P12 certificate
            success = self.cert_manager.import_p12_file(p12_path, password)
            if not success:
                return False, "Failed to import P12 certificate"
            
            # Validate certificates
            if not self.cert_manager.validate_certificates():
                return False, "Certificate validation failed"
            
            # Apply to session manager
            if not self._apply_pki_to_session():
                return False, "Failed to configure session with PKI"

            # Reset initialization state to apply new configuration
            self.reset_initialization()
            
            logger.info("✓ PKI authentication setup completed")
            return True, None
            
        except Exception as e:
            error_msg = f"PKI setup failed: {e}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
    
    def disable_pki_authentication(self) -> bool:
        """
        Disable PKI authentication.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Disabling PKI authentication...")
            
            # Disable in certificate manager
            self.cert_manager.disable_pki()
            
            # Reconfigure session manager (reads settings directly)
            session_manager.reconfigure_security()

            # Reset initialization state after disabling
            self.reset_initialization()
            
            logger.info("✓ PKI authentication disabled")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to disable PKI: {e}")
            return False
    
    def validate_current_certificates(self) -> bool:
        """
        Validate current certificates.
        
        Returns:
            True if certificates are valid
        """
        try:
            if not self.cert_manager.is_pki_enabled():
                return False
            
            return self.cert_manager.validate_certificates()
            
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return False
    
    def get_certificate_status(self) -> Dict[str, Any]:
        """
        Get comprehensive certificate status.
        
        Returns:
            Dictionary with certificate status information
        """
        try:
            status = self.cert_manager.get_pki_status()
            
            # Add session manager PKI info
            session_pki_info = session_manager.get_pki_info()
            status['session_pki_enabled'] = session_pki_info['pki_enabled']
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get certificate status: {e}")
            return {
                'enabled': False,
                'configured': False,
                'valid': False,
                'errors': [f"Status check failed: {e}"]
            }
    
    def _apply_pki_to_session(self) -> bool:
        """Apply PKI configuration to session manager."""
        try:
            # Get certificate files
            cert_path, key_path = self.cert_manager.get_client_cert_files()
            if not cert_path or not key_path:
                logger.error("Client certificate files not available")
                return False
            
            # Get CA chain (optional)
            ca_path = self.cert_manager.get_ca_chain_file()
            
            # Reconfigure session manager (reads settings directly)
            session_manager.reconfigure_security()
            
            logger.debug("PKI configuration applied to session manager")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply PKI to session: {e}")
            return False
    
    def test_pki_connection(self, test_url: str, max_attempts: int = 3, ignore_ssl: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Test PKI authentication with a given URL with retry logic.
        
        Args:
            test_url: URL to test PKI authentication against
            max_attempts: Maximum number of test attempts (default: 3)
            ignore_ssl: Whether to ignore SSL certificate verification (default: False)
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Testing PKI connection to: {test_url} (max {max_attempts} attempts, ignore_ssl={ignore_ssl})")
        
        if not self.cert_manager.is_pki_enabled():
            return False, "PKI is not enabled"
        
        last_error = None
        
        # Configure session for PKI test
        # SSL settings are managed by ssl_service, not manually overridden here
        session_manager.configure_session(
            timeout=10,
            max_retries=0  # Disable all lower-level retries - we handle retries here
        )
        # Note: SSL verification and CA bundle are automatically configured by
        # reconfigure_security() which configure_session() calls internally
        logger.info(f"PKI test session configured (ignore_ssl={ignore_ssl})")
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"PKI test attempt {attempt}/{max_attempts}")
                
                # Make a simple request to test PKI
                response = session_manager.make_request(
                    method="GET",
                    url=test_url,
                    timeout=10
                )
                
                if response.status_code < 400:
                    logger.info(f"✓ PKI connection test successful on attempt {attempt}")
                    return True, None
                else:
                    last_error = f"HTTP {response.status_code}: {response.reason}"
                    logger.warning(f"⚠ PKI test attempt {attempt} returned: {last_error}")
                    
            except Exception as e:
                last_error = f"PKI connection test failed: {e}"
                logger.error(f"✗ PKI test attempt {attempt} error: {last_error}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_attempts:
                import time
                time.sleep(2)  # 2 second delay between attempts
        
        # All attempts failed - provide user-friendly error message
        from ..ai.api_test_service import _get_user_friendly_error
        friendly_error = _get_user_friendly_error(last_error) if last_error else "Unknown error"
        
        # Log technical error for debugging
        logger.error(f"✗ PKI test failed after {max_attempts} attempts. Last technical error: {last_error}")
        
        # Return user-friendly error
        return False, f"PKI connection failed after {max_attempts} attempts: {friendly_error}"
    
    def get_certificate_expiry_warning(self) -> Optional[str]:
        """
        Get certificate expiry warning if applicable.
        
        Returns:
            Warning message or None
        """
        try:
            cert_info = self.cert_manager.get_certificate_info()
            if cert_info and cert_info.days_until_expiry <= 30:
                return f"Certificate expires in {cert_info.days_until_expiry} days"
            return None
            
        except Exception as e:
            logger.error(f"Failed to check certificate expiry: {e}")
            return None
    
    def is_pki_required(self, test_url: str) -> bool:
        """
        Test if PKI authentication is required for a given URL.
        
        Args:
            test_url: URL to test
            
        Returns:
            True if PKI appears to be required
        """
        try:
            # First, try without PKI
            session_manager.disable_pki()
            
            response = session_manager.make_request(
                method="GET",
                url=test_url,
                timeout=5
            )
            
            # If we get a client certificate error (status 400, 401, 403)
            # it might indicate PKI is required
            if response.status_code in [400, 401, 403]:
                logger.debug(f"PKI might be required for {test_url} (status: {response.status_code})")
                return True
            
            return False
            
        except Exception as e:
            # Connection errors might indicate PKI is required
            logger.debug(f"Connection test failed, PKI might be required: {e}")
            return True
        finally:
            # Restore PKI configuration if it was enabled
            if self.cert_manager.is_pki_enabled():
                self._apply_pki_to_session()
    
    def shutdown(self):
        """Shutdown PKI service."""
        try:
            if self.cert_manager:
                self.cert_manager.shutdown()
            logger.info("PKI service shut down")
        except Exception as e:
            logger.warning(f"Error during PKI service shutdown: {e}")


# Global PKI service instance
pki_service = PKIService()