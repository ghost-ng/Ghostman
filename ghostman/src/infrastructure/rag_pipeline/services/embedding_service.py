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
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger("ghostman.embedding_service")


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
        
        # Configure HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Ghostman-RAGPipeline/1.0'
        })
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
        
        self.session.timeout = timeout
        
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
        Create embedding for text with caching and error handling.
        
        Args:
            text: Input text to embed
            model: Override default model
            
        Returns:
            numpy array embedding or None if failed
        """
        try:
            # Validate input
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
            
            # Add any provider-specific parameters
            request_data.update(self._get_provider_params())
            
            logger.debug(f"Creating embedding for {len(text)} characters")
            
            # Make API request
            response = self.session.post(
                f"{self.api_endpoint}/embeddings",
                json=request_data
            )
            
            self.stats['requests_made'] += 1
            
            # Handle response
            if response.status_code == 200:
                response_data = response.json()
                embedding = self._parse_response(response_data)
                
                if embedding is not None:
                    # Store in cache
                    self._store_in_cache(cache_key, embedding)
                    
                    # Update stats
                    if 'usage' in response_data:
                        self.stats['total_tokens_processed'] += response_data['usage'].get('total_tokens', 0)
                    
                    logger.debug(f"Successfully created embedding: {embedding.shape}")
                    return embedding
                else:
                    logger.error("Failed to parse embedding from response")
                    self.stats['errors'] += 1
                    return None
            
            elif response.status_code == 429:
                logger.warning("Rate limit hit, request failed")
                self.stats['errors'] += 1
                return None
            
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                self.stats['errors'] += 1
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout while creating embedding")
            self.stats['errors'] += 1
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while creating embedding: {e}")
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
        self.session.close()