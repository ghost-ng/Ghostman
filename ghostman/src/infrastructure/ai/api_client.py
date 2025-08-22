"""
OpenAI-Compatible API Client for Ghostman.

Provides a robust HTTP client for making API calls to OpenAI-compatible services
with proper error handling, authentication, and retry logic.
"""

import json
import logging
import time
import os
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional, List, AsyncIterator, Iterator, Callable, Union
from urllib.parse import urljoin
import requests
from dataclasses import dataclass

from .session_manager import session_manager
from .file_models import (
    OpenAIFile, VectorStore, VectorStoreFile, FileUploadProgress,
    FileOperationResult, ProgressCallback, ErrorCallback,
    validate_file_for_upload
)

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


class FileUploadError(APIClientError):
    """File upload specific error."""
    pass


class VectorStoreError(APIClientError):
    """Vector store operation error."""
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
        """Convert HTTP error responses to appropriate exceptions with OpenAI-specific handling."""
        try:
            error_data = response.json()
            
            # Handle OpenAI API error format
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    error_message = error_info.get("message", "Unknown error")
                    error_type = error_info.get("type", "unknown_error")
                    error_code = error_info.get("code")
                    
                    # Log detailed error information
                    logger.debug(f"OpenAI API Error - Type: {error_type}, Code: {error_code}, Message: {error_message}")
                    
                    # Handle specific OpenAI error types
                    if error_type == "invalid_request_error":
                        if "file" in error_message.lower() and "not found" in error_message.lower():
                            return FileUploadError(f"File not found: {error_message}")
                        elif "vector_store" in error_message.lower():
                            return VectorStoreError(f"Vector store error: {error_message}")
                        else:
                            return APIClientError(f"Invalid request: {error_message}")
                    elif error_type == "authentication_error":
                        return AuthenticationError(f"Authentication failed: {error_message}")
                    elif error_type == "permission_error":
                        return AuthenticationError(f"Permission denied: {error_message}")
                    elif error_type == "rate_limit_error":
                        retry_after = self._extract_retry_after(response, error_info)
                        return RateLimitError(f"Rate limit exceeded: {error_message}", retry_after)
                    elif error_type == "quota_exceeded_error":
                        return RateLimitError(f"Quota exceeded: {error_message}")
                    elif error_type == "server_error":
                        return APIServerError(f"OpenAI server error: {error_message}")
                    elif error_type == "service_unavailable_error":
                        return APIServerError(f"Service unavailable: {error_message}")
                    else:
                        error_message = f"{error_type}: {error_message}"
                else:
                    error_message = str(error_info)
            else:
                # Fallback to generic error message
                error_message = error_data.get("message", "Unknown error")
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Failed to parse error response JSON: {e}")
            error_message = f"HTTP {response.status_code}: {response.text[:200]}"
        
        # Handle by status code if no specific error type was determined
        if response.status_code == 400:
            return APIClientError(f"Bad request: {error_message}")
        elif response.status_code == 401:
            return AuthenticationError(f"Authentication failed: {error_message}")
        elif response.status_code == 403:
            return AuthenticationError(f"Permission denied: {error_message}")
        elif response.status_code == 404:
            if "file" in error_message.lower():
                return FileUploadError(f"File not found: {error_message}")
            elif "vector_store" in error_message.lower():
                return VectorStoreError(f"Vector store not found: {error_message}")
            else:
                return APIClientError(f"Resource not found: {error_message}")
        elif response.status_code == 413:
            return FileUploadError(f"File too large: {error_message}")
        elif response.status_code == 429:
            retry_after = self._extract_retry_after(response)
            return RateLimitError(f"Rate limit exceeded: {error_message}", retry_after)
        elif response.status_code >= 500:
            return APIServerError(f"Server error: {error_message}")
        else:
            return APIClientError(f"API error ({response.status_code}): {error_message}")
    
    def _extract_retry_after(self, response: requests.Response, error_info: Optional[Dict] = None) -> Optional[int]:
        """Extract retry-after value from response headers or error info."""
        # Check response headers first
        if "retry-after" in response.headers:
            try:
                return int(response.headers["retry-after"])
            except ValueError:
                pass
        
        # Check OpenAI-specific rate limit headers
        if "x-ratelimit-reset-requests" in response.headers:
            try:
                import time
                reset_time = int(response.headers["x-ratelimit-reset-requests"])
                current_time = int(time.time())
                return max(0, reset_time - current_time)
            except (ValueError, TypeError):
                pass
        
        # Check error info for retry suggestion
        if error_info and isinstance(error_info, dict):
            if "retry_after" in error_info:
                try:
                    return int(error_info["retry_after"])
                except (ValueError, TypeError):
                    pass
        
        return None
    
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
                
                # Prepare headers with API key
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Ghostman/1.0"
                }
                
                # Add Authorization header if API key is provided
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                # Make the request using session manager
                response = session_manager.make_request(
                    method=method,
                    url=url,
                    json=data if data else None,
                    params=params,
                    headers=headers,
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
        Test the API connection with a single request.
        
        Returns:
            APIResponse indicating success or failure
        """
        logger.info("Testing API connection...")
        
        # Try the most common endpoint first - models listing
        response = self._make_request("GET", "models")
        if response.success:
            logger.info("✓ API connection test successful")
            return response
        
        # If models endpoint fails, the API is likely not working
        logger.error(f"✗ API connection test failed: {response.error}")
        return response
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        verbosity: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """
        Make a chat completion request with optional file search support.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model name to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            verbosity: Response verbosity level for GPT-5 models ('low', 'medium', 'high')
            reasoning_effort: Reasoning effort for GPT-5 models ('low', 'medium', 'high')
            tools: List of tools to use (e.g., file_search, code_interpreter)
            tool_choice: How the model should use tools ('auto', 'none', or specific tool)
            tool_resources: Resources for tools (e.g., vector_store_ids for file_search)
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
            # Use max_completion_tokens for GPT-5 models and newer OpenAI models
            if self.base_url and 'openai.com' in self.base_url:
                # GPT-5 models (including gpt-5-nano) require max_completion_tokens
                if model.startswith('gpt-5') or model.startswith('o1'):
                    data["max_completion_tokens"] = max_tokens
                    logger.debug(f"Using max_completion_tokens for {model}: {max_tokens}")
                else:
                    # Older models still use max_tokens
                    data["max_tokens"] = max_tokens
                    logger.debug(f"Using max_tokens for {model}: {max_tokens}")
            else:
                data["max_tokens"] = max_tokens
        
        if stream:
            data["stream"] = True
        
        # Add tool support
        if tools:
            data["tools"] = tools
            logger.debug(f"Using tools: {[tool.get('type', 'unknown') for tool in tools]}")
        
        if tool_choice:
            data["tool_choice"] = tool_choice
            logger.debug(f"Tool choice: {tool_choice}")
        
        if tool_resources:
            data["tool_resources"] = tool_resources
            logger.debug(f"Tool resources: {list(tool_resources.keys())}")
        
        # Add GPT-5 specific parameters if provided
        if model.startswith('gpt-5') and self.base_url and 'openai.com' in self.base_url:
            if verbosity is not None:
                data["verbosity"] = verbosity
                logger.debug(f"Using verbosity for {model}: {verbosity}")
            if reasoning_effort is not None:
                data["reasoning_effort"] = reasoning_effort
                logger.debug(f"Using reasoning_effort for {model}: {reasoning_effort}")
        
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
    
    def chat_completion_with_file_search(
        self,
        messages: List[Dict[str, str]],
        model: str,
        vector_store_ids: List[str],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        ranking_options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """
        Make a chat completion request with file search enabled.
        
        This is a convenience method that sets up file_search tool automatically.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model name to use
            vector_store_ids: List of vector store IDs to search
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            ranking_options: Options for ranking search results
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            APIResponse with the completion result including file search results
        """
        # Set up file_search tool
        tools = [{
            "type": "file_search"
        }]
        
        # Add ranking options if provided
        if ranking_options:
            tools[0]["file_search"] = {
                "ranking_options": ranking_options
            }
        
        # Set up tool resources
        tool_resources = {
            "file_search": {
                "vector_store_ids": vector_store_ids
            }
        }
        
        logger.info(f"Chat completion with file search: {len(vector_store_ids)} vector stores")
        
        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto",
            tool_resources=tool_resources,
            **kwargs
        )
    
    def _make_multipart_request(
        self,
        method: str,
        endpoint: str,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        timeout: Optional[int] = None
    ) -> APIResponse:
        """
        Make multipart form request (for file uploads).
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            files: Files to upload
            data: Form data
            progress_callback: Optional progress callback
            timeout: Request timeout
            
        Returns:
            APIResponse object
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        
        # Prepare headers (without Content-Type for multipart)
        headers = {
            "User-Agent": "Ghostman/1.0"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Use session manager but handle multipart manually
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Multipart request attempt {attempt + 1}: {method} {url}")
                
                # Try to use progress tracking if callback provided and toolbelt available
                if progress_callback and files:
                    try:
                        from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
                        
                        # Prepare fields for multipart encoder
                        fields = dict(data) if data else {}
                        if files:
                            fields.update(files)
                        
                        encoder = MultipartEncoder(fields=fields)
                        
                        # Create monitor for progress tracking
                        def monitor_callback(monitor):
                            if progress_callback:
                                # Calculate progress from monitor
                                progress = FileUploadProgress(
                                    file_path=getattr(monitor, '_file_path', 'unknown'),
                                    file_size=monitor.len,
                                    bytes_uploaded=monitor.bytes_read
                                )
                                progress.update_progress(monitor.bytes_read)
                                progress_callback(progress)
                        
                        monitor = MultipartEncoderMonitor(encoder, monitor_callback)
                        headers["Content-Type"] = monitor.content_type
                        
                        response = session_manager.make_request(
                            method=method,
                            url=url,
                            data=monitor,
                            headers=headers,
                            timeout=timeout or self.timeout
                        )
                    except ImportError:
                        logger.warning("requests-toolbelt not available, progress tracking disabled")
                        # Fall back to standard multipart request
                        response = session_manager.make_request(
                            method=method,
                            url=url,
                            files=files,
                            data=data,
                            headers=headers,
                            timeout=timeout or self.timeout
                        )
                else:
                    # Standard multipart request without progress
                    response = session_manager.make_request(
                        method=method,
                        url=url,
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=timeout or self.timeout
                    )
                
                # Handle response
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
                
                # Handle errors with retry logic
                error = self._handle_error_response(response)
                
                if isinstance(error, RateLimitError) and error.retry_after and attempt < self.max_retries:
                    logger.warning(f"Rate limited, waiting {error.retry_after}s before retry")
                    time.sleep(error.retry_after)
                    continue
                
                if isinstance(error, APIServerError) and attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error, retrying in {delay}s: {error}")
                    time.sleep(delay)
                    continue
                
                return APIResponse(
                    success=False,
                    error=str(error),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request error, retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                
                return APIResponse(
                    success=False,
                    error=f"Request error: {str(e)}",
                    status_code=None
                )
        
        return APIResponse(
            success=False,
            error="Maximum retries exceeded",
            status_code=None
        )
    
    # File Operations
    def upload_file(
        self,
        file_path: str,
        purpose: str = "assistants",
        progress_callback: Optional[ProgressCallback] = None
    ) -> FileOperationResult:
        """
        Upload a file to OpenAI.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (assistants, fine-tune, etc.)
            progress_callback: Optional callback for upload progress
            
        Returns:
            FileOperationResult with uploaded file information
        """
        try:
            # Validate file
            is_valid, error_msg = validate_file_for_upload(file_path)
            if not is_valid:
                return FileOperationResult(
                    success=False,
                    error=error_msg
                )
            
            logger.info(f"Uploading file: {file_path} (purpose: {purpose})")
            
            # Prepare file for upload
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Initialize progress
            if progress_callback:
                progress = FileUploadProgress(file_path, file_size)
                progress.status = "starting"
                progress_callback(progress)
            
            # Open file and prepare for upload
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/octet-stream')
                }
                data = {
                    'purpose': purpose
                }
                
                # Set file path on monitor for progress tracking
                if progress_callback:
                    def wrapped_callback(progress_obj):
                        progress_obj.file_path = file_path
                        progress_obj.status = "uploading"
                        progress_callback(progress_obj)
                    
                    response = self._make_multipart_request(
                        "POST",
                        "files",
                        files=files,
                        data=data,
                        progress_callback=wrapped_callback,
                        timeout=300  # 5 minute timeout for uploads
                    )
                else:
                    response = self._make_multipart_request(
                        "POST",
                        "files",
                        files=files,
                        data=data,
                        timeout=300
                    )
            
            if response.success:
                file_obj = OpenAIFile.from_api_response(response.data)
                logger.info(f"✓ File uploaded successfully: {file_obj.id}")
                
                # Final progress update
                if progress_callback:
                    progress = FileUploadProgress(file_path, file_size, file_size)
                    progress.update_progress(file_size)
                    progress.status = "completed"
                    progress_callback(progress)
                
                return FileOperationResult(
                    success=True,
                    data=file_obj,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ File upload failed: {response.error}")
                
                # Error progress update
                if progress_callback:
                    progress = FileUploadProgress(file_path, file_size)
                    progress.status = "error"
                    progress.error = response.error
                    progress_callback(progress)
                
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ File upload error: {e}")
            
            # Error progress update
            if progress_callback:
                try:
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    progress = FileUploadProgress(file_path, file_size)
                    progress.status = "error"
                    progress.error = str(e)
                    progress_callback(progress)
                except:
                    pass  # Don't let progress callback errors propagate
            
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def list_files(
        self,
        purpose: Optional[str] = None,
        limit: Optional[int] = None
    ) -> FileOperationResult:
        """
        List files uploaded to OpenAI.
        
        Args:
            purpose: Filter by file purpose
            limit: Maximum number of files to return
            
        Returns:
            FileOperationResult with list of files
        """
        try:
            logger.debug(f"Listing files (purpose: {purpose}, limit: {limit})")
            
            params = {}
            if purpose:
                params["purpose"] = purpose
            if limit:
                params["limit"] = limit
            
            response = self._make_request("GET", "files", params=params)
            
            if response.success:
                files_data = response.data.get("data", [])
                files = [OpenAIFile.from_api_response(file_data) for file_data in files_data]
                
                logger.info(f"✓ Retrieved {len(files)} files")
                return FileOperationResult(
                    success=True,
                    data=files,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to list files: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error listing files: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def get_file(
        self,
        file_id: str
    ) -> FileOperationResult:
        """
        Get information about a specific file.
        
        Args:
            file_id: ID of the file to retrieve
            
        Returns:
            FileOperationResult with file information
        """
        try:
            logger.debug(f"Getting file info: {file_id}")
            
            response = self._make_request("GET", f"files/{file_id}")
            
            if response.success:
                file_obj = OpenAIFile.from_api_response(response.data)
                logger.debug(f"✓ Retrieved file info: {file_obj.filename}")
                
                return FileOperationResult(
                    success=True,
                    data=file_obj,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to get file info: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error getting file info: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def delete_file(
        self,
        file_id: str
    ) -> FileOperationResult:
        """
        Delete a file from OpenAI.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            logger.info(f"Deleting file: {file_id}")
            
            response = self._make_request("DELETE", f"files/{file_id}")
            
            if response.success:
                logger.info(f"✓ File deleted successfully: {file_id}")
                return FileOperationResult(
                    success=True,
                    data=response.data,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to delete file: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error deleting file: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    # Vector Store Operations
    def create_vector_store(
        self,
        name: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None,
        chunking_strategy: Optional[Dict[str, Any]] = None
    ) -> FileOperationResult:
        """
        Create a new vector store.
        
        Args:
            name: Name of the vector store
            file_ids: List of file IDs to add to the vector store
            metadata: Optional metadata for the vector store
            expires_after: Expiration policy (e.g., {"anchor": "last_active_at", "days": 7})
            chunking_strategy: Strategy for chunking files
            
        Returns:
            FileOperationResult with vector store information
        """
        try:
            logger.info(f"Creating vector store: {name or 'unnamed'}")
            
            data = {}
            if name:
                data["name"] = name
            if file_ids:
                data["file_ids"] = file_ids
            if metadata:
                data["metadata"] = metadata
            if expires_after:
                data["expires_after"] = expires_after
            if chunking_strategy:
                data["chunking_strategy"] = chunking_strategy
            
            response = self._make_request("POST", "vector_stores", data=data)
            
            if response.success:
                vector_store = VectorStore.from_api_response(response.data)
                logger.info(f"✓ Vector store created: {vector_store.id}")
                
                return FileOperationResult(
                    success=True,
                    data=vector_store,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to create vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error creating vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def list_vector_stores(
        self,
        limit: Optional[int] = None,
        order: str = "desc",
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> FileOperationResult:
        """
        List vector stores.
        
        Args:
            limit: Maximum number of vector stores to return
            order: Sort order ('asc' or 'desc')
            after: Cursor for pagination (ID)
            before: Cursor for pagination (ID)
            
        Returns:
            FileOperationResult with list of vector stores
        """
        try:
            logger.debug(f"Listing vector stores (limit: {limit})")
            
            params = {"order": order}
            if limit:
                params["limit"] = limit
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            
            response = self._make_request("GET", "vector_stores", params=params)
            
            if response.success:
                stores_data = response.data.get("data", [])
                stores = [VectorStore.from_api_response(store_data) for store_data in stores_data]
                
                logger.info(f"✓ Retrieved {len(stores)} vector stores")
                return FileOperationResult(
                    success=True,
                    data=stores,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to list vector stores: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error listing vector stores: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def get_vector_store(
        self,
        vector_store_id: str
    ) -> FileOperationResult:
        """
        Get information about a specific vector store.
        
        Args:
            vector_store_id: ID of the vector store
            
        Returns:
            FileOperationResult with vector store information
        """
        try:
            logger.debug(f"Getting vector store: {vector_store_id}")
            
            response = self._make_request("GET", f"vector_stores/{vector_store_id}")
            
            if response.success:
                vector_store = VectorStore.from_api_response(response.data)
                logger.debug(f"✓ Retrieved vector store: {vector_store.name or vector_store.id}")
                
                return FileOperationResult(
                    success=True,
                    data=vector_store,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to get vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error getting vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def update_vector_store(
        self,
        vector_store_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None
    ) -> FileOperationResult:
        """
        Update a vector store.
        
        Args:
            vector_store_id: ID of the vector store to update
            name: New name for the vector store
            metadata: New metadata for the vector store
            expires_after: New expiration policy
            
        Returns:
            FileOperationResult with updated vector store information
        """
        try:
            logger.info(f"Updating vector store: {vector_store_id}")
            
            data = {}
            if name is not None:
                data["name"] = name
            if metadata is not None:
                data["metadata"] = metadata
            if expires_after is not None:
                data["expires_after"] = expires_after
            
            response = self._make_request("POST", f"vector_stores/{vector_store_id}", data=data)
            
            if response.success:
                vector_store = VectorStore.from_api_response(response.data)
                logger.info(f"✓ Vector store updated: {vector_store.id}")
                
                return FileOperationResult(
                    success=True,
                    data=vector_store,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to update vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error updating vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def delete_vector_store(
        self,
        vector_store_id: str
    ) -> FileOperationResult:
        """
        Delete a vector store.
        
        Args:
            vector_store_id: ID of the vector store to delete
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            logger.info(f"Deleting vector store: {vector_store_id}")
            
            response = self._make_request("DELETE", f"vector_stores/{vector_store_id}")
            
            if response.success:
                logger.info(f"✓ Vector store deleted: {vector_store_id}")
                return FileOperationResult(
                    success=True,
                    data=response.data,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to delete vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error deleting vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def add_file_to_vector_store(
        self,
        vector_store_id: str,
        file_id: str,
        chunking_strategy: Optional[Dict[str, Any]] = None
    ) -> FileOperationResult:
        """
        Add a file to a vector store.
        
        Args:
            vector_store_id: ID of the vector store
            file_id: ID of the file to add
            chunking_strategy: Optional chunking strategy for the file
            
        Returns:
            FileOperationResult with vector store file information
        """
        try:
            logger.info(f"Adding file {file_id} to vector store {vector_store_id}")
            
            data = {"file_id": file_id}
            if chunking_strategy:
                data["chunking_strategy"] = chunking_strategy
            
            response = self._make_request(
                "POST", 
                f"vector_stores/{vector_store_id}/files", 
                data=data
            )
            
            if response.success:
                vs_file = VectorStoreFile.from_api_response(response.data)
                logger.info(f"✓ File added to vector store: {vs_file.id}")
                
                return FileOperationResult(
                    success=True,
                    data=vs_file,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to add file to vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error adding file to vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def list_vector_store_files(
        self,
        vector_store_id: str,
        limit: Optional[int] = None,
        order: str = "desc",
        after: Optional[str] = None,
        before: Optional[str] = None,
        filter_by_status: Optional[str] = None
    ) -> FileOperationResult:
        """
        List files in a vector store.
        
        Args:
            vector_store_id: ID of the vector store
            limit: Maximum number of files to return
            order: Sort order ('asc' or 'desc')
            after: Cursor for pagination
            before: Cursor for pagination
            filter_by_status: Filter by file status
            
        Returns:
            FileOperationResult with list of vector store files
        """
        try:
            logger.debug(f"Listing files in vector store: {vector_store_id}")
            
            params = {"order": order}
            if limit:
                params["limit"] = limit
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            if filter_by_status:
                params["filter"] = filter_by_status
            
            response = self._make_request(
                "GET", 
                f"vector_stores/{vector_store_id}/files", 
                params=params
            )
            
            if response.success:
                files_data = response.data.get("data", [])
                vs_files = [VectorStoreFile.from_api_response(file_data) for file_data in files_data]
                
                logger.info(f"✓ Retrieved {len(vs_files)} files from vector store")
                return FileOperationResult(
                    success=True,
                    data=vs_files,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to list vector store files: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error listing vector store files: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    def remove_file_from_vector_store(
        self,
        vector_store_id: str,
        file_id: str
    ) -> FileOperationResult:
        """
        Remove a file from a vector store.
        
        Args:
            vector_store_id: ID of the vector store
            file_id: ID of the file to remove
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            logger.info(f"Removing file {file_id} from vector store {vector_store_id}")
            
            response = self._make_request(
                "DELETE", 
                f"vector_stores/{vector_store_id}/files/{file_id}"
            )
            
            if response.success:
                logger.info(f"✓ File removed from vector store: {file_id}")
                return FileOperationResult(
                    success=True,
                    data=response.data,
                    status_code=response.status_code
                )
            else:
                logger.error(f"✗ Failed to remove file from vector store: {response.error}")
                return FileOperationResult(
                    success=False,
                    error=response.error,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"✗ Error removing file from vector store: {e}")
            return FileOperationResult(
                success=False,
                error=str(e)
            )
    
    # Async File Operations
    async def upload_file_async(
        self,
        file_path: str,
        purpose: str = "assistants",
        progress_callback: Optional[ProgressCallback] = None
    ) -> FileOperationResult:
        """
        Upload a file to OpenAI asynchronously.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (assistants, fine-tune, etc.)
            progress_callback: Optional callback for upload progress
            
        Returns:
            FileOperationResult with uploaded file information
        """
        loop = asyncio.get_event_loop()
        
        # Run the synchronous upload in a thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.upload_file(file_path, purpose, progress_callback)
            )
    
    async def list_files_async(
        self,
        purpose: Optional[str] = None,
        limit: Optional[int] = None
    ) -> FileOperationResult:
        """
        List files uploaded to OpenAI asynchronously.
        
        Args:
            purpose: Filter by file purpose
            limit: Maximum number of files to return
            
        Returns:
            FileOperationResult with list of files
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.list_files(purpose, limit)
            )
    
    async def get_file_async(
        self,
        file_id: str
    ) -> FileOperationResult:
        """
        Get information about a specific file asynchronously.
        
        Args:
            file_id: ID of the file to retrieve
            
        Returns:
            FileOperationResult with file information
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.get_file(file_id)
            )
    
    async def delete_file_async(
        self,
        file_id: str
    ) -> FileOperationResult:
        """
        Delete a file from OpenAI asynchronously.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            FileOperationResult indicating success or failure
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.delete_file(file_id)
            )
    
    # Async Vector Store Operations
    async def create_vector_store_async(
        self,
        name: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None,
        chunking_strategy: Optional[Dict[str, Any]] = None
    ) -> FileOperationResult:
        """
        Create a new vector store asynchronously.
        
        Args:
            name: Name of the vector store
            file_ids: List of file IDs to add to the vector store
            metadata: Optional metadata for the vector store
            expires_after: Expiration policy
            chunking_strategy: Strategy for chunking files
            
        Returns:
            FileOperationResult with vector store information
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.create_vector_store(
                    name, file_ids, metadata, expires_after, chunking_strategy
                )
            )
    
    async def list_vector_stores_async(
        self,
        limit: Optional[int] = None,
        order: str = "desc",
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> FileOperationResult:
        """
        List vector stores asynchronously.
        
        Args:
            limit: Maximum number of vector stores to return
            order: Sort order ('asc' or 'desc')
            after: Cursor for pagination
            before: Cursor for pagination
            
        Returns:
            FileOperationResult with list of vector stores
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.list_vector_stores(limit, order, after, before)
            )
    
    async def chat_completion_with_file_search_async(
        self,
        messages: List[Dict[str, str]],
        model: str,
        vector_store_ids: List[str],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        ranking_options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """
        Make a chat completion request with file search enabled asynchronously.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model name to use
            vector_store_ids: List of vector store IDs to search
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            ranking_options: Options for ranking search results
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            APIResponse with the completion result including file search results
        """
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.chat_completion_with_file_search(
                    messages, model, vector_store_ids, temperature, 
                    max_tokens, ranking_options, **kwargs
                )
            )
    
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