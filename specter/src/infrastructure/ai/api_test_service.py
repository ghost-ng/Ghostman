"""
Unified API Configuration Testing Service for Specter.

Provides centralized API testing functionality used by both the setup wizard
and settings dialog with configurable retry limits and SSL verification.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from threading import Thread
from PyQt6.QtCore import QObject, pyqtSignal

from .ai_service import AIService
from .session_manager import session_manager

logger = logging.getLogger("specter.api_test_service")


def _get_user_friendly_error(error_message: str) -> str:
    """
    Convert technical error messages to user-friendly ones.
    
    Args:
        error_message: Technical error message from API/network
        
    Returns:
        User-friendly error message
    """
    error_lower = error_message.lower()
    
    # PKI-specific errors
    if 'pki is not enabled' in error_lower:
        return "PKI authentication is not configured - please set up PKI first"
    
    # SSL/Certificate errors
    if any(ssl_term in error_lower for ssl_term in [
        'ssl', 'certificate', 'tlsv1_unrecognized_name', 'ssl_error', 
        'certificate verify failed', 'hostname doesn\'t match', 'ssl handshake failed',
        'client certificate', 'pki', 'ca bundle'
    ]):
        if 'client certificate' in error_lower or 'pki' in error_lower:
            return "PKI client certificate error - check your certificate configuration"
        elif 'ca bundle' in error_lower or 'certificate verify failed' in error_lower:
            return "Server certificate verification failed - check CA chain or disable SSL verification"
        else:
            return "SSL certificate error - check server URL or disable SSL verification"
    
    # Network/Connection errors
    if any(net_term in error_lower for net_term in [
        'connection refused', 'connection error', 'connection failed',
        'name or service not known', 'nodename nor servname provided',
        'failed to establish a new connection', 'connection broken'
    ]):
        return "Cannot connect to server - check URL and network connection"
    
    # DNS resolution errors  
    if any(dns_term in error_lower for dns_term in [
        'name resolution', 'getaddrinfo failed', 'dns', 'host not found'
    ]):
        return "Server not found - check the base URL"
    
    # Timeout errors
    if any(timeout_term in error_lower for timeout_term in [
        'timeout', 'timed out', 'read timeout'
    ]):
        return "Connection timed out - server may be slow or unreachable"
    
    # Authentication errors
    if any(auth_term in error_lower for auth_term in [
        'unauthorized', 'authentication failed', 'invalid api key',
        'incorrect api key', 'api key', '401', 'forbidden', '403'
    ]):
        return "Authentication failed - check your API key"
    
    # Rate limiting
    if any(rate_term in error_lower for rate_term in [
        'rate limit', 'too many requests', '429', 'quota exceeded'
    ]):
        return "Rate limited - too many requests, try again later"
    
    # Server errors
    if any(server_term in error_lower for server_term in [
        '500', '502', '503', '504', 'internal server error', 'bad gateway',
        'service unavailable', 'gateway timeout'
    ]):
        return "Server error - the API service is having issues"
    
    # Model/endpoint errors
    if any(model_term in error_lower for model_term in [
        'model not found', 'invalid model', 'model does not exist',
        'not found', '404'
    ]):
        return "Model or endpoint not found - check model name and base URL"
    
    # Temperature/parameter errors
    if 'temperature' in error_lower and ('unsupported' in error_lower or 'not support' in error_lower):
        if 'only the default' in error_lower or 'only' in error_lower and '1' in error_lower:
            return "🌡️ Temperature not supported by this model - using default value (1.0). Some reasoning models like GPT-5/o1 only support fixed temperature."
        else:
            return "🌡️ Temperature value not supported - check model documentation for valid range"
    
    # Other parameter errors
    if any(param_term in error_lower for param_term in [
        'unsupported parameter', 'parameter not supported', 'invalid parameter'
    ]):
        return "⚙️ Model parameter not supported - check model documentation for valid parameters"
    
    # Invalid request format
    if any(format_term in error_lower for format_term in [
        'bad request', '400', 'invalid request', 'malformed'
    ]):
        return "Invalid request format - check API configuration"
    
    # Generic fallback - try to extract meaningful part
    if 'connection' in error_lower:
        return "Connection failed - check server URL and network"
    elif 'error' in error_lower:
        return "API error - check configuration and try again"
    
    # If no specific pattern matches, provide a generic but helpful message
    return "Connection test failed - please check your API configuration"


@dataclass
class APITestConfig:
    """Configuration for API testing."""
    model_name: str
    base_url: str
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    max_test_attempts: int = 3
    disable_ssl_verification: bool = True


class APITestResult:
    """Result of an API test."""
    def __init__(self, success: bool, message: str, details: Optional[Dict[str, Any]] = None, 
                 attempt: int = 1, total_attempts: int = 1):
        self.success = success
        self.message = message
        self.details = details or {}
        self.attempt = attempt
        self.total_attempts = total_attempts


class APITestService(QObject):
    """
    Unified API testing service with retry logic and SSL configuration.
    
    Used by both the setup wizard and settings dialog to ensure
    consistent API testing behavior across the application.
    """
    
    # Signals for UI updates
    test_started = pyqtSignal()
    test_attempt = pyqtSignal(int, int)  # current_attempt, total_attempts
    test_completed = pyqtSignal(object)  # APITestResult
    
    def __init__(self):
        super().__init__()
        # CRITICAL: Use global singleton, don't create new instance
        # The global singleton has PKI configuration applied
        self.session_manager = session_manager
        self._current_test_thread = None
        
    def test_api_config_async(self, config: APITestConfig, 
                            progress_callback: Optional[Callable[[str], None]] = None):
        """
        Test API configuration asynchronously.
        
        Args:
            config: API configuration to test
            progress_callback: Optional callback for progress updates
        """
        if self._current_test_thread and self._current_test_thread.is_alive():
            logger.warning("API test already in progress")
            return
            
        self._current_test_thread = Thread(
            target=self._run_test,
            args=(config, progress_callback),
            daemon=True
        )
        self._current_test_thread.start()
    
    def test_api_config_sync(self, config: APITestConfig) -> APITestResult:
        """
        Test API configuration synchronously.
        
        Args:
            config: API configuration to test
            
        Returns:
            APITestResult with test outcome
        """
        return self._run_test(config)
    
    def _run_test(self, config: APITestConfig, 
                  progress_callback: Optional[Callable[[str], None]] = None) -> APITestResult:
        """
        Run the actual API test with retry logic.
        
        Args:
            config: API configuration to test
            progress_callback: Optional callback for progress updates
            
        Returns:
            APITestResult with test outcome
        """
        self.test_started.emit()
        
        # Configure session manager with SSL settings
        self._configure_session_for_testing(config)
        
        last_error = None
        
        for attempt in range(1, config.max_test_attempts + 1):
            self.test_attempt.emit(attempt, config.max_test_attempts)
            
            if progress_callback:
                progress_callback(f"Testing connection (attempt {attempt}/{config.max_test_attempts})...")
            
            logger.info(f"API test attempt {attempt}/{config.max_test_attempts}")
            
            try:
                result = self._test_single_attempt(config, attempt)
                
                if result.success:
                    logger.info(f"✓ API test successful on attempt {attempt}")
                    self.test_completed.emit(result)
                    return result
                else:
                    last_error = result.message
                    friendly_error = _get_user_friendly_error(result.message)
                    # Log full technical error for debugging
                    logger.warning(f"✗ API test attempt {attempt} failed: {result.message}")
                    
                    if progress_callback:
                        # Show user-friendly error in UI
                        progress_callback(f"Attempt {attempt} failed: {friendly_error}")
                        
            except Exception as e:
                last_error = str(e)
                friendly_error = _get_user_friendly_error(str(e))
                # Log full technical error for debugging
                logger.error(f"✗ API test attempt {attempt} error: {e}")
                
                if progress_callback:
                    # Show user-friendly error in UI
                    progress_callback(f"Attempt {attempt} error: {friendly_error}")
            
            # Wait before retry (except on last attempt)
            if attempt < config.max_test_attempts:
                time.sleep(2)  # 2 second delay between attempts
        
        # All attempts failed - provide user-friendly message
        friendly_final_error = _get_user_friendly_error(last_error) if last_error else "Unknown error"
        final_result = APITestResult(
            success=False,
            message=f"Connection failed after {config.max_test_attempts} attempts: {friendly_final_error}",
            details={'last_error': last_error, 'total_attempts': config.max_test_attempts},
            attempt=config.max_test_attempts,
            total_attempts=config.max_test_attempts
        )
        
        # Log full technical error for debugging
        logger.error(f"✗ API test failed after {config.max_test_attempts} attempts. Last technical error: {last_error}")
        self.test_completed.emit(final_result)
        return final_result
    
    def _configure_session_for_testing(self, config: APITestConfig):
        """Configure session manager for API testing using unified SSL service."""
        try:
            # Use the unified SSL service to get proper SSL verification settings
            from ..ssl.ssl_service import ssl_service

            # Override SSL settings based on test configuration
            if config.disable_ssl_verification:
                logger.info("SSL verification disabled by test configuration")
                # Temporarily configure SSL service to ignore SSL for this test
                ssl_service.configure(ignore_ssl=True, custom_ca_path=None)
            else:
                # Use current SSL service configuration or apply from settings
                ssl_status = ssl_service.get_status()
                if not ssl_status['initialized']:
                    # Initialize SSL service from settings if not done yet
                    try:
                        from ...application.settings import settings
                        ssl_service.configure_from_settings(settings.get_all_settings())
                    except Exception as e:
                        logger.warning(f"Could not initialize SSL service from settings: {e}")

                ssl_status = ssl_service.get_status()
                logger.info(f"SSL verification configured: ignore={ssl_status['ignore_ssl']}, custom_ca={ssl_status['custom_ca_configured']}")

            # Configure session with connection parameters.
            # configure_session() internally calls reconfigure_security() which reads
            # the current ssl_service + PKI state from SettingsManager and applies it
            # atomically. It uses dirty-checking so it won't change anything if config
            # is unchanged, and it updates verify/cert in-place without wiping PKI.
            self.session_manager.configure_session(
                timeout=config.timeout,
                max_retries=0,  # Disable all lower-level retries - we handle retries at the service level
                pool_maxsize=5
            )

            logger.info("Session configured for API testing with unified SSL settings")

        except Exception as e:
            logger.error(f"Failed to configure session for testing: {e}")
    
    def _test_single_attempt(self, config: APITestConfig, attempt: int) -> APITestResult:
        """
        Perform a single API test attempt.
        
        Args:
            config: API configuration to test
            attempt: Current attempt number
            
        Returns:
            APITestResult for this attempt
        """
        ai_service = None
        
        try:
            # Create and initialize AI service
            ai_service = AIService()
            
            ai_config = {
                'model_name': config.model_name,
                'base_url': config.base_url,
                'api_key': config.api_key,
                'temperature': config.temperature,
                'max_tokens': config.max_tokens,
                'timeout': config.timeout,
                'max_retries': 0  # Disable API client retries - we handle all retries here
            }
            
            # Initialize the service
            if not ai_service.initialize(ai_config):
                return APITestResult(
                    success=False,
                    message="Failed to initialize AI service",
                    attempt=attempt,
                    total_attempts=config.max_test_attempts
                )
            
            # Test the connection
            test_result = ai_service.test_connection()
            
            if test_result['success']:
                return APITestResult(
                    success=True,
                    message="Connection successful",
                    details=test_result.get('details', {}),
                    attempt=attempt,
                    total_attempts=config.max_test_attempts
                )
            else:
                # Use friendly error for UI but keep technical details for debugging
                friendly_message = _get_user_friendly_error(test_result['message'])
                return APITestResult(
                    success=False,
                    message=friendly_message,
                    details={**test_result.get('details', {}), 'technical_error': test_result['message']},
                    attempt=attempt,
                    total_attempts=config.max_test_attempts
                )
                
        except Exception as e:
            # Use friendly error for UI but keep technical details for debugging
            friendly_message = _get_user_friendly_error(str(e))
            return APITestResult(
                success=False,
                message=friendly_message,
                details={'exception': str(e), 'technical_error': str(e)},
                attempt=attempt,
                total_attempts=config.max_test_attempts
            )
        finally:
            # Always cleanup the AI service
            if ai_service:
                try:
                    ai_service.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down AI service: {e}")


def test_network_connection_consolidated(
    base_url: str, 
    api_key: str = "", 
    model_name: str = "gpt-3.5-turbo",
    pki_config: Optional[Dict[str, Any]] = None,
    ignore_ssl: bool = True,
    max_attempts: int = 3,
    timeout: int = 30
) -> APITestResult:
    """
    Consolidated network test function that replaces all separate test functions.
    
    This single function handles all network testing scenarios:
    - Standard API testing with/without SSL verification
    - PKI authentication testing
    - Session manager integration
    - Configurable retry logic
    
    Args:
        base_url: API base URL to test
        api_key: API key for authentication
        model_name: Model name to test with
        pki_config: Optional PKI configuration dict with cert paths
        ignore_ssl: Whether to ignore SSL certificate verification
        max_attempts: Maximum number of retry attempts
        timeout: Request timeout in seconds
        
    Returns:
        APITestResult with success status and details
    """
    logger.info(f"🌐 Starting consolidated network test: {base_url}")
    logger.info(f"🔧 Config: model={model_name}, pki={bool(pki_config)}, ignore_ssl={ignore_ssl}, attempts={max_attempts}")
    
    # Configure PKI if provided
    if pki_config:
        try:
            from ..pki.pki_service import pki_service
            if pki_config.get('cert_path') and pki_config.get('key_path'):
                logger.info(f"🔐 Configuring PKI with cert: {pki_config['cert_path']}")
                # Use the session manager's configure_pki method
                from .session_manager import session_manager
                session_manager.configure_pki(
                    cert_path=pki_config['cert_path'],
                    key_path=pki_config['key_path'],
                    ca_path=pki_config.get('ca_path')
                )
                logger.info("✓ PKI configuration applied to session manager")
            else:
                logger.warning("PKI config provided but missing cert_path or key_path")
        except Exception as e:
            logger.warning(f"Failed to configure PKI for test: {e}")
            # Don't fail the entire test, just log the warning and continue
    
    # Create test configuration
    config = APITestConfig(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_test_attempts=max_attempts,
        disable_ssl_verification=ignore_ssl
    )
    
    # Run the test
    test_service = get_api_test_service()
    result = test_service.test_api_config_sync(config)
    
    logger.info(f"🏁 Consolidated network test result: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    if not result.success:
        logger.debug(f"🔍 Test failure details: {result.message}")
    
    return result


# Global instance for reuse
_api_test_service = None

def get_api_test_service() -> APITestService:
    """Get the global API test service instance."""
    global _api_test_service
    if _api_test_service is None:
        _api_test_service = APITestService()
    return _api_test_service