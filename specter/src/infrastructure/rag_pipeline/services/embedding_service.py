"""
Embedding service for creating and managing text embeddings.

Provides a robust interface to embeddings APIs with retry logic, caching,
and error handling for production use.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Union
from functools import lru_cache
import hashlib
import json

import numpy as np
import requests

logger = logging.getLogger("specter.embedding_service")


class EmbeddingService:
    """
    Production-ready embedding service with comprehensive error handling.
    
    Features:
    - Multiple embedding providers support
    - Automatic retry with exponential backoff  
    - Request caching with configurable TTL
    - Rate limiting and batch processing
    - Comprehensive error handling and logging
    - Input validation and sanitization
    """
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        model: str = "text-embedding-ada-002",
        max_retries: int = 3,
        timeout: float = 30.0,
        rate_limit_delay: float = 0.1,
        cache_size: int = 1000,
        cache_ttl: int = 3600
    ):
        """
        Initialize embedding service.
        
        Args:
            api_endpoint: Embeddings API endpoint URL
            api_key: API key for authentication (optional)
            model: Embedding model name
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests for rate limiting
            cache_size: LRU cache size for embeddings
            cache_ttl: Cache time-to-live in seconds
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        # Use centralized session manager for PKI/SSL support
        from ...ai.session_manager import session_manager
        self.session_manager = session_manager

        # Ensure session manager is configured
        if not self.session_manager.is_configured:
            self.session_manager.configure_session(
                timeout=int(timeout),
                max_retries=max_retries
            )

        # Prepare headers for requests
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Specter-RAGPipeline/1.0'
        }

        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        
        # Initialize caching
        self._setup_cache(cache_size)
        
        # Rate limiting
        self._last_request_time = 0
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'total_tokens_processed': 0
        }
        
        logger.info(f"Embedding service initialized: {self.api_endpoint}, model: {self.model}")
    
    def _setup_cache(self, cache_size: int):
        """Setup embedding cache with TTL."""
        self._cache = {}
        self._cache_timestamps = {}
        self._max_cache_size = cache_size
        
        # Make get_embedding_cached an LRU cache method
        self._get_embedding_from_cache = lru_cache(maxsize=cache_size)(self._get_embedding_from_cache)
    
    def _generate_cache_key(self, text: str, model: str = None) -> str:
        """Generate cache key for text and model."""
        key_data = f"{model or self.model}:{text}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self.cache_ttl
    
    def _get_embedding_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Get embedding from cache if valid."""
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            self.stats['cache_hits'] += 1
            return self._cache[cache_key]
        
        self.stats['cache_misses'] += 1
        return None
    
    def _store_in_cache(self, cache_key: str, embedding: np.ndarray):
        """Store embedding in cache."""
        # Clean old entries if cache is full
        if len(self._cache) >= self._max_cache_size:
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._cache[cache_key] = embedding
        self._cache_timestamps[cache_key] = time.time()
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.rate_limit_delay > 0:
            time_since_last = time.time() - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = time.time()

    def _should_retry(self, status_code: int, attempt: int, max_retries: int = 3) -> float:
        """
        Determine if request should be retried and return delay in seconds.
        Returns 0 if should not retry.
        """
        if attempt >= max_retries:
            return 0
        if status_code == 429:
            # Rate limit: exponential backoff 1s, 2s, 4s
            return min(2 ** attempt, 8)
        if status_code >= 500:
            # Server error: backoff 1s, 2s
            return min(2 ** attempt, 4) if attempt < 2 else 0
        return 0

    def _get_error_message(self, status_code: int, response_text: str) -> str:
        """Return actionable error message based on HTTP status."""
        if status_code == 404:
            return (
                f"Embedding endpoint returned 404 (Not Found). "
                f"If using Anthropic for chat, configure a separate embedding "
                f"provider in Settings → Advanced. URL: {self.api_endpoint}/embeddings"
            )
        if status_code in (401, 403):
            return (
                f"Embedding API key is invalid or expired (HTTP {status_code}). "
                f"Check Settings → Advanced → Embedding API Key."
            )
        if status_code == 429:
            return "Embedding rate limit exceeded after retries. Try again in a few minutes."
        if status_code >= 500:
            return f"Embedding server error (HTTP {status_code}). The provider may be experiencing issues."
        return f"Embedding API error: HTTP {status_code} - {response_text[:200]}"

    def _validate_input(self, text: str) -> str:
        """Validate and sanitize input text."""
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # Trim excessive whitespace
        text = ' '.join(text.split())
        
        # Check length limits (adjust based on your model)
        max_length = 8000  # Conservative limit for most models
        if len(text) > max_length:
            logger.warning(f"Text truncated from {len(text)} to {max_length} characters")
            text = text[:max_length] + "..."
        
        return text
    
    def _parse_response(self, response_data: Dict[str, Any]) -> np.ndarray:
        """Parse embedding response from API."""
        try:
            # Handle different response formats
            if 'data' in response_data:
                # OpenAI format
                embeddings_data = response_data['data']
                if isinstance(embeddings_data, list) and len(embeddings_data) > 0:
                    embedding = embeddings_data[0].get('embedding')
                    if embedding:
                        return np.array(embedding, dtype=np.float32)
            
            elif 'embeddings' in response_data:
                # Alternative format
                embeddings = response_data['embeddings']
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    return np.array(embeddings[0], dtype=np.float32)
            
            elif 'embedding' in response_data:
                # Direct embedding format
                return np.array(response_data['embedding'], dtype=np.float32)
            
            # If we get here, the response format is unexpected
            logger.error(f"Unexpected response format: {response_data.keys()}")
            return None
            
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error(f"Error parsing embedding response: {e}")
            return None
    
    def create_embedding(self, text: str, model: str = None) -> Optional[np.ndarray]:
        """
        Create embedding for text with caching, retry, and error handling.

        Args:
            text: Input text to embed
            model: Override default model

        Returns:
            numpy array embedding or None if failed
        """
        try:
            text = self._validate_input(text)
            model = model or self.model

            # Check cache first
            cache_key = self._generate_cache_key(text, model)
            cached_embedding = self._get_embedding_from_cache(cache_key)
            if cached_embedding is not None:
                logger.debug(f"Cache hit for text hash: {cache_key[:8]}...")
                return cached_embedding

            # Rate limiting
            self._rate_limit()

            # Prepare request
            request_data = {
                'input': text,
                'model': model
            }
            request_data.update(self._get_provider_params())

            logger.debug(f"Creating embedding for {len(text)} characters")

            # Retry loop
            max_retries = 3
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    response = self.session_manager.make_request(
                        method="POST",
                        url=f"{self.api_endpoint}/embeddings",
                        json=request_data,
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    self.stats['requests_made'] += 1

                    if response.status_code == 200:
                        response_data = response.json()
                        embedding = self._parse_response(response_data)
                        if embedding is not None:
                            self._store_in_cache(cache_key, embedding)
                            if 'usage' in response_data:
                                self.stats['total_tokens_processed'] += response_data['usage'].get('total_tokens', 0)
                            logger.debug(f"Successfully created embedding: {embedding.shape}")
                            return embedding
                        else:
                            logger.error("Failed to parse embedding from response")
                            self.stats['errors'] += 1
                            return None

                    # Check if we should retry
                    retry_delay = self._should_retry(response.status_code, attempt, max_retries)
                    if retry_delay > 0:
                        logger.warning(
                            f"Embedding request failed (HTTP {response.status_code}), "
                            f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        continue

                    # Non-retryable error
                    error_msg = self._get_error_message(response.status_code, response.text)
                    logger.error(error_msg)
                    self.stats['errors'] += 1
                    return None

                except requests.exceptions.Timeout:
                    last_error = "timeout"
                    if attempt < max_retries:
                        logger.warning(f"Embedding request timed out, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
                        continue
                    logger.error(f"Embedding request timed out after {max_retries} retries")
                    self.stats['errors'] += 1
                    return None

                except requests.exceptions.ConnectionError as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        logger.warning(f"Connection error, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
                        continue
                    logger.error(
                        f"Cannot connect to embedding endpoint: {self.api_endpoint}. "
                        f"Verify the URL in Settings → Advanced. Error: {e}"
                    )
                    self.stats['errors'] += 1
                    return None

            # All retries exhausted
            logger.error(f"Embedding failed after all retries. Last error: {last_error}")
            self.stats['errors'] += 1
            return None

        except ValueError as e:
            logger.error(f"Invalid embedding input: {e}")
            self.stats['errors'] += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating embedding: {e}")
            self.stats['errors'] += 1
            return None
    
    def create_batch_embeddings(
        self, 
        texts: List[str], 
        model: str = None,
        batch_size: int = 20
    ) -> List[Optional[np.ndarray]]:
        """
        Create embeddings for multiple texts with batching.
        
        Args:
            texts: List of texts to embed
            model: Override default model
            batch_size: Maximum texts per batch request
            
        Returns:
            List of embeddings (same order as input, None for failures)
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = []
            
            # For now, process individually (can be optimized for APIs supporting batch)
            for text in batch:
                embedding = self.create_embedding(text, model)
                batch_embeddings.append(embedding)
                
                # Brief pause between requests in batch
                if len(batch) > 1:
                    time.sleep(0.05)
            
            embeddings.extend(batch_embeddings)
            
            # Pause between batches
            if i + batch_size < len(texts):
                time.sleep(0.2)
        
        logger.info(f"Created {len([e for e in embeddings if e is not None])}/{len(texts)} embeddings")
        return embeddings
    
    def _get_provider_params(self) -> Dict[str, Any]:
        """Get provider-specific parameters."""
        # Can be extended for different providers
        return {}

    def validate_endpoint(self) -> dict:
        """
        Test that the embedding endpoint is reachable and functional.
        Returns dict with 'valid' (bool), 'error' (str), 'dimensions' (int or None).
        """
        try:
            test_text = "test"
            response = self.session_manager.make_request(
                method="POST",
                url=f"{self.api_endpoint}/embeddings",
                json={'input': test_text, 'model': self.model},
                headers=self.headers,
                timeout=min(self.timeout, 10.0)
            )
            if response.status_code == 200:
                data = response.json()
                embedding = self._parse_response(data)
                if embedding is not None:
                    return {'valid': True, 'error': '', 'dimensions': len(embedding)}
                return {'valid': False, 'error': 'Could not parse embedding response'}
            return {
                'valid': False,
                'error': self._get_error_message(response.status_code, response.text)
            }
        except requests.exceptions.ConnectionError:
            return {
                'valid': False,
                'error': f"Cannot connect to {self.api_endpoint}. Check the URL."
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def get_embedding_dimensions(self, model: str = None) -> Optional[int]:
        """
        Get embedding dimensions for a model.
        
        Args:
            model: Model name (uses default if None)
            
        Returns:
            Embedding dimensions or None if unknown
        """
        model = model or self.model
        
        # Known model dimensions (expand as needed)
        model_dimensions = {
            'text-embedding-ada-002': 1536,
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
        }
        
        return model_dimensions.get(model)
    
    def test_connection(self) -> bool:
        """Test API connection with a simple request."""
        try:
            # Skip connection test if no API key to prevent segfaults
            if not self.api_key:
                logger.warning("⚠️ Skipping connection test - no API key configured")
                return False
            
            logger.info("Testing embedding service connection...")
            
            test_text = "This is a test message for embedding service connectivity."
            embedding = self.create_embedding(test_text)
            
            if embedding is not None:
                logger.info(f"✓ Connection test successful. Embedding shape: {embedding.shape}")
                return True
            else:
                logger.error("✗ Connection test failed - no embedding returned")
                return False
                
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            return False
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._get_embedding_from_cache.cache_clear()
        logger.info("Embedding cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        cache_info = self._get_embedding_from_cache.cache_info()
        
        return {
            **self.stats,
            'cache_size': len(self._cache),
            'cache_hit_rate': (
                self.stats['cache_hits'] / 
                (self.stats['cache_hits'] + self.stats['cache_misses'])
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0.0
            ),
            'lru_cache_info': {
                'hits': cache_info.hits,
                'misses': cache_info.misses,
                'maxsize': cache_info.maxsize,
                'currsize': cache_info.currsize
            }
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        # Session is managed centrally, no need to close here
        pass