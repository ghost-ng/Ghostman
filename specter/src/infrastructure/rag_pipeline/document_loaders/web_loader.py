"""
Web Content Loader

Fetches and processes web content from URLs:
- HTML pages with content extraction
- Text content cleaning and normalization
- Metadata extraction from HTML meta tags
- Rate limiting and respectful crawling
- Error handling for network issues
- Unified session management with PKI/SSL support
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse, urljoin, urldefrag
import re
import requests

try:
    from bs4 import BeautifulSoup, Comment
    import html2text
    HTML_PROCESSING_AVAILABLE = True
except ImportError:
    HTML_PROCESSING_AVAILABLE = False
    BeautifulSoup = None
    Comment = None
    html2text = None

from .base_loader import BaseDocumentLoader, Document, DocumentMetadata, DocumentLoadError

logger = logging.getLogger("specter.web_loader")


class WebLoader(BaseDocumentLoader):
    """
    Web content loader with HTML processing and content extraction.

    Features:
    - HTTP requests via unified session_manager (with PKI/SSL support)
    - HTML content extraction and cleaning
    - Metadata extraction from HTML meta tags
    - Rate limiting and timeout handling
    - User-agent rotation
    - Link extraction and processing
    - Respectful crawling practices
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize web loader.

        Args:
            config: Configuration options including:
                - timeout: Request timeout in seconds (default: 10.0)
                - max_content_length: Maximum content length (default: 1MB)
                - user_agent: User-Agent string (default: Specter-RAG/1.0)
                - follow_redirects: Follow HTTP redirects (default: True)
                - max_redirects: Maximum redirects to follow (default: 5)
                - rate_limit_delay: Delay between requests (default: 1.0)
                - extract_links: Extract and store links (default: True)
                - clean_html: Clean HTML content (default: True)
                - include_meta: Include HTML meta tags in metadata (default: True)
        """
        super().__init__(config)

        if not HTML_PROCESSING_AVAILABLE:
            logger.warning("BeautifulSoup/html2text not available - HTML processing will be limited")

        self.timeout = self.config.get('timeout', 10.0)
        self.max_content_length = self.config.get('max_content_length', 1024 * 1024)  # 1MB
        self.user_agent = self.config.get('user_agent', 'Specter-RAG/1.0 (Document Indexing)')
        self.follow_redirects = self.config.get('follow_redirects', True)
        self.max_redirects = self.config.get('max_redirects', 5)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 1.0)
        self.extract_links = self.config.get('extract_links', True)
        self.clean_html = self.config.get('clean_html', True)
        self.include_meta = self.config.get('include_meta', True)

        # Rate limiting
        self._last_request_time = 0.0

        # Use centralized session manager (has PKI/SSL support)
        from ...ai.session_manager import session_manager
        self.session_manager = session_manager
    
    def supports(self, source: Union[str, 'Path']) -> bool:
        """Check if this loader supports the given source."""
        if isinstance(source, str):
            return source.startswith(('http://', 'https://'))
        return False
    
    async def load(self, source: Union[str, 'Path']) -> Document:
        """
        Load web document from URL.
        
        Args:
            source: URL to load
            
        Returns:
            Document with extracted content and metadata
        """
        start_time = time.time()
        url = str(source)
        
        # Validate URL
        self._validate_url(url)
        
        # Get basic metadata
        metadata = self.get_metadata_from_url(url)
        metadata.loader_type = self.__class__.__name__
        
        try:
            # Rate limiting
            await self._apply_rate_limit()
            
            # Fetch content
            html_content, response_metadata = await self._fetch_content(url)
            
            # Update metadata with response information
            self._update_metadata_from_response(metadata, response_metadata)
            
            # Extract text content
            content = await self._extract_text_content(html_content, url, metadata)
            
            # Clean content
            if self.clean_html:
                content = self.clean_content(content)
            
            if not content or len(content.strip()) < self.config.get('min_content_length', 100):
                raise DocumentLoadError("No meaningful content extracted from URL", url)
            
            # Extract title if not already set
            if not metadata.title:
                metadata.title = self.extract_title(content, metadata)
            
            # Detect language
            metadata.language = self.detect_language(content)
            
            # Record processing time
            processing_time = time.time() - start_time
            metadata.processing_time = processing_time
            
            # Update statistics
            self._stats['documents_loaded'] += 1
            self._stats['total_processing_time'] += processing_time
            self._stats['total_content_size'] += len(content)
            
            document = Document(content=content, metadata=metadata)
            self.logger.info(f"Successfully loaded URL: {url} ({len(content)} chars, {processing_time:.2f}s)")
            
            return document
            
        except Exception as e:
            self._stats['documents_failed'] += 1
            if isinstance(e, DocumentLoadError):
                raise
            else:
                raise DocumentLoadError(f"Web content extraction failed: {str(e)}", url, e)
    
    def _fetch_content_sync(self, url: str) -> tuple[str, Dict[str, Any]]:
        """
        Fetch HTML content from URL using requests (synchronous).

        Args:
            url: URL to fetch

        Returns:
            Tuple of (html_content, response_metadata)
        """
        response_metadata = {}

        try:
            # Prepare headers
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # Make request using session_manager
            response = self.session_manager.make_request(
                method='GET',
                url=url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=self.follow_redirects
            )

            # Record response metadata
            response_metadata['status_code'] = response.status_code
            response_metadata['content_type'] = response.headers.get('content-type', '')
            response_metadata['content_length'] = response.headers.get('content-length')
            response_metadata['last_modified'] = response.headers.get('last-modified')
            response_metadata['server'] = response.headers.get('server')
            response_metadata['final_url'] = str(response.url)

            # Check status code
            if response.status_code >= 400:
                raise DocumentLoadError(f"HTTP {response.status_code}: {response.reason}", url)

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['text/html', 'application/xhtml', 'text/plain']):
                raise DocumentLoadError(f"Unsupported content type: {content_type}", url)

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_content_length:
                raise DocumentLoadError(f"Content too large: {content_length} bytes", url)

            # Read content with size limit
            content = response.text

            if len(content) > self.max_content_length:
                content = content[:self.max_content_length]
                logger.warning(f"Content truncated to {self.max_content_length} characters")

            return content, response_metadata

        except requests.exceptions.Timeout as e:
            raise DocumentLoadError("Request timeout", url, e)
        except requests.exceptions.RequestException as e:
            raise DocumentLoadError(f"Network error: {str(e)}", url, e)

    async def _fetch_content(self, url: str) -> tuple[str, Dict[str, Any]]:
        """
        Fetch HTML content from URL (async wrapper around sync request).

        Args:
            url: URL to fetch

        Returns:
            Tuple of (html_content, response_metadata)
        """
        # Run synchronous request in thread pool to avoid blocking event loop
        return await asyncio.to_thread(self._fetch_content_sync, url)
    
    async def _extract_text_content(self, html_content: str, url: str, 
                                   metadata: DocumentMetadata) -> str:
        """
        Extract text content from HTML.
        
        Args:
            html_content: Raw HTML content
            url: Source URL
            metadata: Document metadata to update
            
        Returns:
            Extracted text content
        """
        if not HTML_PROCESSING_AVAILABLE:
            # Fallback: simple HTML tag removal
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract metadata from HTML head
        if self.include_meta:
            self._extract_html_metadata(soup, metadata, url)
        
        # Remove script and style elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()
        
        # Remove comments
        if Comment:
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
        
        # Extract main content (prioritize main content areas)
        main_content = None
        content_selectors = [
            'main', 'article', '[role="main"]', '.main-content', 
            '.content', '.post-content', '.entry-content'
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content area found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract links if requested
        if self.extract_links:
            links = []
            for link in main_content.find_all('a', href=True):
                href = link.get('href')
                if href:
                    absolute_url = urljoin(url, href)
                    link_text = link.get_text().strip()
                    if link_text:
                        links.append({'url': absolute_url, 'text': link_text})
            
            if links:
                if not metadata.custom:
                    metadata.custom = {}
                metadata.custom['links'] = links[:50]  # Limit to first 50 links
        
        # Convert to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap lines
        h.single_line_break = True
        
        text = h.handle(str(main_content))
        metadata.extraction_method = 'html2text'
        
        return text
    
    def _extract_html_metadata(self, soup: 'BeautifulSoup', metadata: DocumentMetadata, url: str):
        """Extract metadata from HTML head section."""
        # Title
        if soup.title:
            title = soup.title.get_text().strip()
            if title:
                metadata.title = title
        
        # Meta tags
        meta_mapping = {
            'description': 'subject',
            'author': 'author',
            'keywords': 'custom.keywords',
            'language': 'language',
            'robots': 'custom.robots',
            'viewport': 'custom.viewport',
        }
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '').strip()
            
            if not content:
                continue
            
            if name in meta_mapping:
                field = meta_mapping[name]
                if '.' in field:
                    # Custom field
                    if not metadata.custom:
                        metadata.custom = {}
                    metadata.custom[field.split('.')[1]] = content
                else:
                    setattr(metadata, field, content)
        
        # Open Graph tags
        og_mapping = {
            'og:title': 'title',
            'og:description': 'subject',
            'og:type': 'custom.og_type',
            'og:site_name': 'custom.site_name',
        }
        
        for meta in soup.find_all('meta', property=True):
            property_name = meta.get('property', '').lower()
            content = meta.get('content', '').strip()
            
            if content and property_name in og_mapping:
                field = og_mapping[property_name]
                if '.' in field:
                    if not metadata.custom:
                        metadata.custom = {}
                    metadata.custom[field.split('.')[1]] = content
                else:
                    # Only set if not already set
                    if not getattr(metadata, field, None):
                        setattr(metadata, field, content)
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            if not metadata.custom:
                metadata.custom = {}
            metadata.custom['canonical_url'] = urljoin(url, canonical['href'])
    
    def _update_metadata_from_response(self, metadata: DocumentMetadata, 
                                     response_metadata: Dict[str, Any]):
        """Update metadata with HTTP response information."""
        if not metadata.custom:
            metadata.custom = {}
        
        metadata.custom['http_status'] = response_metadata.get('status_code')
        metadata.custom['content_type'] = response_metadata.get('content_type')
        metadata.custom['final_url'] = response_metadata.get('final_url')
        
        # Parse last modified date
        last_modified = response_metadata.get('last_modified')
        if last_modified:
            try:
                from email.utils import parsedate_to_datetime
                metadata.modified_at = parsedate_to_datetime(last_modified)
            except (ValueError, TypeError):
                pass
        
        # Set server information
        server = response_metadata.get('server')
        if server:
            metadata.custom['server'] = server
    
    def _validate_url(self, url: str):
        """Validate URL format and scheme."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise DocumentLoadError("Invalid URL format", url)
            
            if parsed.scheme not in ('http', 'https'):
                raise DocumentLoadError(f"Unsupported URL scheme: {parsed.scheme}", url)
            
        except Exception as e:
            raise DocumentLoadError(f"URL validation failed: {str(e)}", url, e)
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        if self.rate_limit_delay > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()
    
    async def load_batch(self, sources: List[Union[str, 'Path']], 
                        max_concurrent: int = 3) -> List[Optional[Document]]:
        """
        Load multiple web documents with controlled concurrency.
        
        Args:
            sources: List of URLs to load
            max_concurrent: Maximum concurrent requests (lower for web)
            
        Returns:
            List of Document objects (None for failed loads)
        """
        # Override parent method with lower default concurrency for web requests
        return await super().load_batch(sources, max_concurrent)
    
    
    def clean_content(self, content: str) -> str:
        """Override clean_content for web-specific cleaning."""
        if not content:
            return ""
        
        # Standard cleaning
        content = super().clean_content(content)
        
        # Web-specific cleaning
        # Remove markdown-style link references
        import re
        content = re.sub(r'\[[^\]]*\]\([^)]*\)', '', content)  # Remove [text](url)
        content = re.sub(r'\[[^\]]*\]:\s*https?://[^\s]*', '', content)  # Remove [ref]: url
        
        # Remove excessive punctuation from poor HTML conversion
        content = re.sub(r'[_*]{3,}', '', content)  # Remove long underscores/asterisks
        content = re.sub(r'[-=]{4,}', '', content)  # Remove long dashes/equals
        
        # Clean up navigation breadcrumbs and menu items
        content = re.sub(r'^\s*[\|>»›]\s*', '', content, flags=re.MULTILINE)
        
        # Remove "Continue reading" type links
        content = re.sub(r'\s*\[?Continue reading[^\]]*\]?\s*', '', content, flags=re.IGNORECASE)
        
        return content.strip()