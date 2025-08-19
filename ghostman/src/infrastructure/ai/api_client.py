"""
OpenAI-Compatible API Client for Ghostman.

Provides a robust HTTP client for making API calls to OpenAI-compatible services
with proper error handling, authentication, and retry logic.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List, AsyncIterator, Iterator
from urllib.parse import urljoin
import requests
from dataclasses import dataclass

from .session_manager import session_manager

logger = logging.getLogger("ghostman.api_client")


@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class AuthenticationError(APIClientError):
    """Authentication failed."""
    pass


class RateLimitError(APIClientError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class APIServerError(APIClientError):
    """Server-side error (5xx responses)."""
    pass


class NetworkError(APIClientError):
    """Network-related error."""
    pass


class TimeoutError(APIClientError):
    """Request timeout error."""
    pass


class OpenAICompatibleClient:
    """
    HTTP client for OpenAI-compatible API endpoints.
    
    Supports:
    - OpenAI API
    - Anthropic Claude API  
    - OpenRouter
    - Local services (Ollama, LM Studio)
    - Any OpenAI-compatible endpoint
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Base API URL (e.g., https://api.openai.com/v1)
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Base delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Configure the global session manager
        session_manager.configure_session(
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=retry_delay
        )
        
        # Set default headers
        self._setup_headers()
        
        logger.info(f"API client initialized: {self.base_url}")
    
    def _setup_headers(self):
        """Setup default headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Ghostman/1.0.0"
        }
        
        # Add authentication if API key is provided
        if self.api_key:
            if 'anthropic.com' in self.base_url:
                # Anthropic uses x-api-key header
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
            else:
                # OpenAI and most others use Authorization Bearer
                headers["Authorization"] = f"Bearer {self.api_key}"
        
        session_manager.update_headers(headers)
        logger.debug("API client headers configured")
    
    def _handle_error_response(self, response: requests.Response) -> APIClientError:
        """Convert HTTP error responses to appropriate exceptions."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except (json.JSONDecodeError, KeyError, ValueError):
            error_message = f"HTTP {response.status_code}: {response.text[:200]}"
        
        if response.status_code == 401:
            return AuthenticationError(f"Authentication failed: {error_message}")
        elif response.status_code == 429:
            retry_after = None
            if "retry-after" in response.headers:
                try:
                    retry_after = int(response.headers["retry-after"])
                except ValueError:
                    pass
            return RateLimitError(f"Rate limit exceeded: {error_message}", retry_after)
        elif response.status_code >= 500:
            return APIServerError(f"Server error: {error_message}")
        else:
            return APIClientError(f"API error ({response.status_code}): {error_message}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            data: Request body data (for POST/PUT requests)
            params: URL parameters
            
        Returns:
            APIResponse object with success/error information
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        
        # Retry logic is now handled by the session manager's HTTPAdapter
        # But we'll keep manual retry for specific error handling
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"API request attempt {attempt + 1}: {method} {url}")
                
                # Make the request using session manager
                response = session_manager.make_request(
                    method=method,
                    url=url,
                    json=data if data else None,
                    params=params,
                    timeout=self.timeout
                )
                
                # Check for success
                if response.status_code < 400:
                    try:
                        response_data = response.json()
                        return APIResponse(
                            success=True,
                            data=response_data,
                            status_code=response.status_code,
                            headers=dict(response.headers)
                        )
                    except (json.JSONDecodeError, ValueError):
                        return APIResponse(
                            success=True,
                            data={"text": response.text},
                            status_code=response.status_code,
                            headers=dict(response.headers)
                        )
                
                # Handle error responses
                error = self._handle_error_response(response)
                
                # For rate limits, respect retry-after header
                if isinstance(error, RateLimitError) and error.retry_after:
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limited, waiting {error.retry_after}s before retry")
                        time.sleep(error.retry_after)
                        continue
                
                # For server errors, retry with exponential backoff
                if isinstance(error, APIServerError) and attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error, retrying in {delay}s: {error}")
                    time.sleep(delay)
                    continue
                
                # Return error response
                return APIResponse(
                    success=False,
                    error=str(error),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            except requests.Timeout as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                
                return APIResponse(
                    success=False,
                    error=f"Request timeout after {self.timeout}s",
                    status_code=None
                )
            
            except requests.ConnectionError as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Connection error, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                
                return APIResponse(
                    success=False,
                    error=f"Connection error: {str(e)}",
                    status_code=None
                )
            
            except requests.RequestException as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request error, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                
                return APIResponse(
                    success=False,
                    error=f"Network error: {str(e)}",
                    status_code=None
                )
        
        # Should not reach here
        return APIResponse(
            success=False,
            error="Maximum retries exceeded",
            status_code=None
        )
    
    def test_connection(self) -> APIResponse:
        """
        Test the API connection.
        
        Returns:
            APIResponse indicating success or failure
        """
        logger.info("Testing API connection...")
        
        # For OpenAI-compatible APIs, try to list models or make a minimal request
        # This varies by provider, so we'll try a few common endpoints
        
        test_endpoints = [
            "models",  # Standard OpenAI endpoint
            "v1/models",  # Alternative path
        ]
        
        for endpoint in test_endpoints:
            response = self._make_request("GET", endpoint)
            if response.success:
                logger.info("✓ API connection test successful")
                return response
        
        # If model listing fails, try a minimal chat completion
        minimal_request = {
            "model": "gpt-3.5-turbo",  # Will be overridden by actual model
            "messages": [{"role": "user", "content": "test"}],
            "max_completion_tokens": 1,
            "temperature": 0
        }
        
        response = self._make_request("POST", "chat/completions", minimal_request)
        if response.success:
            logger.info("✓ API connection test successful (chat endpoint)")
        else:
            logger.error(f"✗ API connection test failed: {response.error}")
        
        return response
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> APIResponse:
        """
        Make a chat completion request.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model name to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            APIResponse with the completion result
        """
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        # Store original max_tokens value to retry with different parameter name
        original_max_tokens = max_tokens
        
        if max_tokens is not None:
            # Default to the newer parameter name for OpenAI models
            if self.base_url and 'openai.com' in self.base_url:
                data["max_completion_tokens"] = max_tokens
            else:
                data["max_tokens"] = max_tokens
        
        if stream:
            data["stream"] = True
        
        logger.debug(f"Chat completion request: model={model}, messages={len(messages)}")
        
        response = self._make_request("POST", "chat/completions", data)
        
        # If we got a 400 error about max_tokens/max_completion_tokens, retry with the other parameter
        if not response.success and response.status_code == 400 and original_max_tokens is not None:
            error_msg = str(response.error).lower()
            if 'max_tokens' in error_msg and 'max_completion_tokens' in error_msg:
                # Try switching the parameter name
                if "max_completion_tokens" in data:
                    logger.info("Retrying with 'max_tokens' instead of 'max_completion_tokens'")
                    del data["max_completion_tokens"]
                    data["max_tokens"] = original_max_tokens
                elif "max_tokens" in data:
                    logger.info("Retrying with 'max_completion_tokens' instead of 'max_tokens'")
                    del data["max_tokens"]
                    data["max_completion_tokens"] = original_max_tokens
                
                # Retry the request
                response = self._make_request("POST", "chat/completions", data)
        
        return response
    
    def close(self):
        """Close the HTTP client."""
        # Session is managed globally, so we don't close it here
        # Individual clients just remove their specific headers
        logger.debug("API client closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()