"""
Centralized Session Manager for HTTP requests in Ghostman.

Provides thread-safe session management with connection pooling,
retry logic, and proper resource cleanup for the requests library.
"""

import threading
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from contextlib import contextmanager

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("ghostman.session_manager")


class SessionManager:
    """
    Thread-safe session manager for HTTP requests.
    
    Features:
    - Single session object shared across the application
    - Connection pooling with HTTPAdapter
    - Thread-safe access with proper locking
    - Retry logic with exponential backoff
    - Proper resource cleanup
    - Support for different adapters per host/scheme
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
        self._pki_config: Optional[Tuple[str, str, Optional[str]]] = None  # (cert_path, key_path, ca_path)
        self._initialized = True
        
        logger.info("SessionManager initialized")
    
    def configure_session(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        pool_block: bool = False
    ) -> None:
        """
        Configure the session with connection pooling and retry settings.
        
        Args:
            timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Factor for exponential backoff between retries
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections in each pool
            pool_block: Whether to block when pool is at max capacity
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
                status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            )
            
            # Create HTTP adapter with connection pooling
            http_adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                pool_block=pool_block
            )
            
            # Create HTTPS adapter with same settings
            https_adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                pool_block=pool_block
            )
            
            # Mount adapters
            self._session.mount("http://", http_adapter)
            self._session.mount("https://", https_adapter)
            
            # Store adapters for cleanup
            self._adapters = {
                "http": http_adapter,
                "https": https_adapter
            }
            
            # Set default headers
            self._session.headers.update({
                "User-Agent": "Ghostman/1.0.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
            
            # Apply PKI configuration if available
            if self._pki_config:
                self._apply_pki_config()
            
            logger.info(f"Session configured: timeout={timeout}s, retries={max_retries}, pool_size={pool_maxsize}")
    
    def configure_pki(
        self,
        cert_path: str,
        key_path: str,
        ca_path: Optional[str] = None
    ) -> None:
        """
        Configure PKI client authentication for the session.
        
        Args:
            cert_path: Path to client certificate file (.crt or .pem)
            key_path: Path to client private key file (.pem)
            ca_path: Optional path to CA certificate chain file
        """
        with self._session_lock:
            self._pki_config = (cert_path, key_path, ca_path)
            
            # If session exists, apply PKI configuration immediately
            if self._session:
                self._apply_pki_config()
            
            logger.info(f"PKI configured: cert={cert_path}, key={key_path}, ca={'Yes' if ca_path else 'No'}")
    
    def disable_pki(self) -> None:
        """Disable PKI client authentication for the session."""
        with self._session_lock:
            self._pki_config = None
            
            # If session exists, remove PKI configuration
            if self._session:
                self._session.cert = None
                self._session.verify = True  # Reset to default
            
            logger.info("PKI authentication disabled")
    
    def _apply_pki_config(self) -> None:
        """Apply PKI configuration to the current session."""
        if not self._session or not self._pki_config:
            return
        
        cert_path, key_path, ca_path = self._pki_config
        
        try:
            # Set client certificate and key
            self._session.cert = (cert_path, key_path)
            
            # Set CA certificate for server verification if provided
            if ca_path:
                self._session.verify = ca_path
            else:
                # Use default CA verification
                self._session.verify = True
            
            logger.debug("PKI configuration applied to session")
            
        except Exception as e:
            logger.error(f"Failed to apply PKI configuration: {e}")
            raise
    
    def get_pki_info(self) -> Dict[str, Any]:
        """
        Get PKI configuration information.
        
        Returns:
            Dict with PKI configuration details
        """
        info = {
            "pki_enabled": self._pki_config is not None,
            "cert_path": None,
            "key_path": None,
            "ca_path": None
        }
        
        if self._pki_config:
            cert_path, key_path, ca_path = self._pki_config
            info.update({
                "cert_path": cert_path,
                "key_path": key_path,
                "ca_path": ca_path
            })
        
        return info
    
    @contextmanager
    def get_session(self):
        """
        Get the configured session in a thread-safe manner.
        
        Yields:
            requests.Session: The configured session object
            
        Raises:
            RuntimeError: If session is not configured
        """
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
        """
        Make an HTTP request using the managed session.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            timeout: Request timeout (uses default if None)
            **kwargs: Additional arguments passed to requests
            
        Returns:
            requests.Response: The response object
            
        Raises:
            requests.RequestException: For request-related errors
            RuntimeError: If session is not configured
        """
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
    
    def update_headers(self, headers: Dict[str, str]) -> None:
        """
        Update default headers for all requests.
        
        Args:
            headers: Dictionary of headers to add/update
        """
        with self._session_lock:
            if self._session:
                self._session.headers.update(headers)
                logger.debug(f"Headers updated: {list(headers.keys())}")
            else:
                logger.warning("Cannot update headers: session not configured")
    
    def remove_headers(self, header_names: list) -> None:
        """
        Remove specific headers from default headers.
        
        Args:
            header_names: List of header names to remove
        """
        with self._session_lock:
            if self._session:
                for header_name in header_names:
                    self._session.headers.pop(header_name, None)
                logger.debug(f"Headers removed: {header_names}")
            else:
                logger.warning("Cannot remove headers: session not configured")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about current connection pools.
        
        Returns:
            Dict with connection pool information
        """
        info = {
            "session_configured": self._session is not None,
            "adapters": list(self._adapters.keys()),
            "default_timeout": self._default_timeout,
            "pki_info": self.get_pki_info()
        }
        
        if self._session:
            info["headers"] = dict(self._session.headers)
            
            # Get adapter information
            for scheme, adapter in self._adapters.items():
                if hasattr(adapter, 'config'):
                    info[f"{scheme}_adapter"] = {
                        "max_retries": getattr(adapter.max_retries, 'total', None),
                        "pool_connections": getattr(adapter, 'config', {}).get('pool_connections'),
                        "pool_maxsize": getattr(adapter, 'config', {}).get('pool_maxsize')
                    }
        
        return info
    
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
            pass  # Ignore errors during cleanup
    
    @property
    def is_configured(self) -> bool:
        """Check if the session is configured and ready to use."""
        with self._session_lock:
            return self._session is not None


# Global session manager instance
session_manager = SessionManager()