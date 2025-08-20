"""
Unified API Configuration Testing Service for Ghostman.

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
from .session_manager import SessionManager

logger = logging.getLogger("ghostman.api_test_service")


def _get_user_friendly_error(error_message: str) -> str:
    """
    Convert technical error messages to user-friendly ones.
    
    Args:
        error_message: Technical error message from API/network
        
    Returns:
        User-friendly error message
    """
    error_lower = error_message.lower()
    
    # SSL/Certificate errors
    if any(ssl_term in error_lower for ssl_term in [
        'ssl', 'certificate', 'tlsv1_unrecognized_name', 'ssl_error', 
        'certificate verify failed', 'hostname doesn\'t match'
    ]):
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
        self.session_manager = SessionManager()
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
        """Configure session manager for API testing with proper PKI handling."""
        try:
            # Check if PKI is configured and get CA bundle path
            from ..pki.pki_service import pki_service
            ca_bundle_path = None
            
            if pki_service.cert_manager.is_pki_enabled():
                ca_bundle_path = pki_service.cert_manager.get_ca_chain_file()
                if ca_bundle_path:
                    logger.info(f"PKI is enabled, using CA bundle for verification: {ca_bundle_path}")
                    # When PKI is configured, use CA bundle instead of disabling SSL
                    config.disable_ssl_verification = False
                else:
                    logger.warning("PKI is enabled but no CA chain file found")
            
            # Configure session with NO retries - we handle all retries at the service level
            self.session_manager.configure_session(
                timeout=config.timeout,
                max_retries=0,  # Disable all lower-level retries
                pool_maxsize=5,
                disable_ssl_verification=config.disable_ssl_verification
            )
            
            # If we have a CA bundle path, configure the session to use it
            if ca_bundle_path and not config.disable_ssl_verification:
                with self.session_manager.get_session() as session:
                    session.verify = ca_bundle_path
                logger.info(f"Session configured to use CA bundle: {ca_bundle_path}")
            elif config.disable_ssl_verification:
                logger.info("SSL verification disabled for API testing")
            
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


# Global instance for reuse
_api_test_service = None

def get_api_test_service() -> APITestService:
    """Get the global API test service instance."""
    global _api_test_service
    if _api_test_service is None:
        _api_test_service = APITestService()
    return _api_test_service