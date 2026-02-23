"""
OpenAI-Compatible API Client for Specter.

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

logger = logging.getLogger("specter.api_client")


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
            "User-Agent": "Specter/1.0.0"
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
                
                # Prepare headers with API key
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Specter/1.0"
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
            verbosity: Response verbosity level for GPT-5 models ('low', 'medium', 'high')
            reasoning_effort: Reasoning effort for GPT-5 models ('low', 'medium', 'high')
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
    
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream_callback: Optional[callable] = None,
        thinking_callback: Optional[callable] = None,
        verbosity: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        **kwargs
    ) -> APIResponse:
        """
        Make a streaming chat completion request with SSE parsing.

        Yields text chunks to stream_callback as they arrive, then returns
        the fully assembled APIResponse at the end (same shape as
        chat_completion so callers can treat it identically).

        Args:
            messages: List of message objects
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream_callback: Called with each text chunk as it arrives
            thinking_callback: Called with each reasoning/thinking chunk
            verbosity: GPT-5 verbosity level
            reasoning_effort: GPT-5 reasoning effort
            **kwargs: Additional API parameters

        Returns:
            APIResponse with the full assembled response
        """
        # Build request data (same logic as chat_completion)
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }

        if max_tokens is not None:
            if self.base_url and 'openai.com' in self.base_url:
                if model.startswith('gpt-5') or model.startswith('o1'):
                    data["max_completion_tokens"] = max_tokens
                else:
                    data["max_tokens"] = max_tokens
            else:
                data["max_tokens"] = max_tokens

        if model.startswith('gpt-5') and self.base_url and 'openai.com' in self.base_url:
            if verbosity is not None:
                data["verbosity"] = verbosity
            if reasoning_effort is not None:
                data["reasoning_effort"] = reasoning_effort

        url = urljoin(f"{self.base_url}/", "chat/completions")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Specter/1.0"
        }
        if self.api_key:
            if 'anthropic.com' in self.base_url:
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"

        logger.debug(f"Streaming chat completion: model={model}, messages={len(messages)}")

        try:
            response = session_manager.make_request(
                method="POST",
                url=url,
                json=data,
                headers=headers,
                timeout=self.timeout,
                stream=True
            )

            if response.status_code >= 400:
                # Read full body for error
                error = self._handle_error_response(response)
                return APIResponse(
                    success=False,
                    error=str(error),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

            # Parse SSE stream
            full_content = ""
            full_reasoning = ""
            tool_calls_accum: Dict[int, Dict[str, Any]] = {}
            finish_reason = None
            model_name = model
            usage = {}

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue

                payload = line[5:].strip()
                if payload == "[DONE]":
                    break

                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    logger.debug(f"Skipping malformed SSE chunk: {payload[:80]}")
                    continue

                # Extract model name from first chunk
                if "model" in chunk:
                    model_name = chunk["model"]

                # OpenAI format: choices[0].delta
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    fr = choices[0].get("finish_reason")
                    if fr:
                        finish_reason = fr

                    # Text content
                    content_piece = delta.get("content")
                    if content_piece:
                        full_content += content_piece
                        if stream_callback:
                            try:
                                stream_callback(content_piece)
                            except Exception as cb_err:
                                logger.debug(f"Stream callback error: {cb_err}")

                    # Reasoning/thinking tokens (OpenAI o-series, DeepSeek R1)
                    reasoning_piece = delta.get("reasoning_content")
                    if reasoning_piece:
                        full_reasoning += reasoning_piece
                        if thinking_callback:
                            try:
                                thinking_callback(reasoning_piece)
                            except Exception as cb_err:
                                logger.debug(f"Thinking callback error: {cb_err}")

                    # OpenRouter reasoning_details array
                    reasoning_details = delta.get("reasoning_details")
                    if reasoning_details and isinstance(reasoning_details, list):
                        for rd in reasoning_details:
                            if isinstance(rd, dict) and rd.get("type") in (
                                "reasoning.text", "reasoning.summary"
                            ):
                                rd_text = rd.get("text", "")
                                if rd_text:
                                    full_reasoning += rd_text
                                    if thinking_callback:
                                        try:
                                            thinking_callback(rd_text)
                                        except Exception as cb_err:
                                            logger.debug(f"Thinking callback error: {cb_err}")

                    # Tool call deltas (accumulate across chunks)
                    tc_deltas = delta.get("tool_calls", [])
                    for tc_delta in tc_deltas:
                        idx = tc_delta.get("index", 0)
                        if idx not in tool_calls_accum:
                            tool_calls_accum[idx] = {
                                "id": tc_delta.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        tc = tool_calls_accum[idx]
                        if tc_delta.get("id"):
                            tc["id"] = tc_delta["id"]
                        fn = tc_delta.get("function", {})
                        if fn.get("name"):
                            tc["function"]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tc["function"]["arguments"] += fn["arguments"]

                # Anthropic format: content_block_delta
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            full_content += text
                            if stream_callback:
                                try:
                                    stream_callback(text)
                                except Exception as cb_err:
                                    logger.debug(f"Stream callback error: {cb_err}")
                    # Anthropic thinking/reasoning delta
                    elif delta.get("type") == "thinking_delta":
                        thinking_text = delta.get("thinking", "")
                        if thinking_text:
                            full_reasoning += thinking_text
                            if thinking_callback:
                                try:
                                    thinking_callback(thinking_text)
                                except Exception as cb_err:
                                    logger.debug(f"Thinking callback error: {cb_err}")

                # Anthropic usage
                if chunk.get("type") == "message_delta":
                    usage = chunk.get("usage", usage)
                    if chunk.get("delta", {}).get("stop_reason"):
                        finish_reason = chunk["delta"]["stop_reason"]

                # OpenAI usage in final chunk
                if "usage" in chunk and chunk["usage"]:
                    usage = chunk["usage"]

            # Build assembled response matching non-streaming shape
            assembled_message = {"role": "assistant", "content": full_content}
            if full_reasoning:
                assembled_message["reasoning_content"] = full_reasoning
            if tool_calls_accum:
                assembled_message["tool_calls"] = [
                    tool_calls_accum[i]
                    for i in sorted(tool_calls_accum.keys())
                ]

            assembled = {
                "id": f"stream-{id(response)}",
                "object": "chat.completion",
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "message": assembled_message,
                    "finish_reason": finish_reason or "stop"
                }],
                "usage": usage
            }

            return APIResponse(
                success=True,
                data=assembled,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except requests.Timeout:
            return APIResponse(
                success=False,
                error=f"Streaming request timeout after {self.timeout}s",
                status_code=None
            )
        except requests.ConnectionError as e:
            return APIResponse(
                success=False,
                error=f"Connection error during streaming: {str(e)}",
                status_code=None
            )
        except requests.RequestException as e:
            return APIResponse(
                success=False,
                error=f"Network error during streaming: {str(e)}",
                status_code=None
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