"""
PDF Document Loader

Comprehensive PDF loading with multiple extraction backends:
- pdfplumber for high-quality text extraction with layout preservation
- PyPDF2 for fast extraction when layout doesn't matter
- Fallback strategies for problematic PDFs
- Metadata extraction and error handling
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    PyPDF2 = None

from .base_loader import BaseDocumentLoader, Document, DocumentMetadata, DocumentLoadError

logger = logging.getLogger("ghostman.pdf_loader")


class PDFLoader(BaseDocumentLoader):
    """
    Advanced PDF document loader with multiple extraction backends.
    
    Features:
    - Multiple extraction methods (pdfplumber, PyPDF2)
    - Layout-aware extraction
    - Metadata extraction from PDF properties
    - Error handling and fallback strategies
    - Password-protected PDF support
    - Page-by-page processing for large files
    """
    
    SUPPORTED_EXTENSIONS = {'.pdf'}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PDF loader.
        
        Args:
            config: Configuration options including:
                - extraction_method: 'pdfplumber', 'pypdf2', or 'auto' (default: 'auto')
                - preserve_layout: Whether to preserve text layout (default: False)
                - extract_images: Whether to extract images (default: False)
                - max_pages: Maximum pages to process (default: None)
                - password: PDF password if needed (default: None)
        """
        super().__init__(config)
        
        self.extraction_method = self.config.get('extraction_method', 'auto')
        self.preserve_layout = self.config.get('preserve_layout', False)
        self.extract_images = self.config.get('extract_images', False)
        self.max_pages = self.config.get('max_pages', None)
        self.password = self.config.get('password', None)
        
        # Validate extraction method
        if self.extraction_method not in ['auto', 'pdfplumber', 'pypdf2']:
            raise ValueError(f"Invalid extraction method: {self.extraction_method}")
        
        # Check availability of libraries
        if self.extraction_method == 'pdfplumber' and not PDFPLUMBER_AVAILABLE:
            raise ValueError("pdfplumber not available but requested as extraction method")
        
        if self.extraction_method == 'pypdf2' and not PYPDF2_AVAILABLE:
            raise ValueError("PyPDF2 not available but requested as extraction method")
        
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ValueError("No PDF extraction libraries available (install pdfplumber or PyPDF2)")
    
    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this loader supports the given source."""
        if isinstance(source, str) and source.startswith(('http://', 'https://')):
            return False  # URLs handled by web loader
        
        path = Path(source)
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    async def load(self, source: Union[str, Path]) -> Document:
        """
        Load PDF document.
        
        Args:
            source: Path to PDF file
            
        Returns:
            Document with extracted text and metadata
        """
        start_time = time.time()
        path = Path(source)
        
        # Validate source
        self.validate_source(path)
        
        # Get basic metadata
        metadata = self.get_metadata_from_path(path)
        metadata.loader_type = self.__class__.__name__
        
        try:
            # Choose extraction method
            method = self._choose_extraction_method()
            metadata.extraction_method = method
            
            # Extract content and additional metadata
            if method == 'pdfplumber':
                content, pdf_metadata = await self._extract_with_pdfplumber(path)
            elif method == 'pypdf2':
                content, pdf_metadata = await self._extract_with_pypdf2(path)
            else:
                raise DocumentLoadError(f"Unsupported extraction method: {method}", str(path))
            
            # Update metadata with PDF-specific information
            self._update_metadata_from_pdf(metadata, pdf_metadata)
            
            # Clean content
            content = self.clean_content(content)
            
            if not content or len(content.strip()) < self.config.get('min_content_length', 100):
                raise DocumentLoadError("No meaningful content extracted", str(path))
            
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
            self.logger.info(f"Successfully loaded PDF: {path} ({len(content)} chars, {processing_time:.2f}s)")
            
            return document
            
        except Exception as e:
            self._stats['documents_failed'] += 1
            if isinstance(e, DocumentLoadError):
                raise
            else:
                raise DocumentLoadError(f"PDF extraction failed: {str(e)}", str(path), e)
    
    def _choose_extraction_method(self) -> str:
        """Choose the best available extraction method."""
        if self.extraction_method != 'auto':
            return self.extraction_method
        
        # Auto-selection logic
        if PDFPLUMBER_AVAILABLE:
            return 'pdfplumber'
        elif PYPDF2_AVAILABLE:
            return 'pypdf2'
        else:
            raise ValueError("No PDF extraction libraries available")
    
    async def _extract_with_pdfplumber(self, path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using pdfplumber.
        
        Args:
            path: Path to PDF file
            
        Returns:
            Tuple of (content, metadata_dict)
        """
        def extract_sync():
            text_parts = []
            pdf_metadata = {}
            
            with pdfplumber.open(str(path), password=self.password) as pdf:
                # Extract PDF metadata
                if hasattr(pdf, 'metadata') and pdf.metadata:
                    pdf_metadata = dict(pdf.metadata)
                
                # Process pages
                max_pages = self.max_pages or len(pdf.pages)
                pages_to_process = min(len(pdf.pages), max_pages)
                
                for i, page in enumerate(pdf.pages[:pages_to_process]):
                    try:
                        if self.preserve_layout:
                            # Extract with layout preservation
                            page_text = page.extract_text(layout=True)
                        else:
                            # Standard text extraction
                            page_text = page.extract_text()
                        
                        if page_text:
                            text_parts.append(page_text)
                        
                        # Add page break between pages
                        if i < pages_to_process - 1:
                            text_parts.append('\n\n--- Page Break ---\n\n')
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to extract text from page {i+1}: {e}")
                        continue
                
                pdf_metadata['total_pages'] = len(pdf.pages)
                pdf_metadata['processed_pages'] = pages_to_process
            
            return '\n'.join(text_parts), pdf_metadata
        
        # Run extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_sync)
    
    async def _extract_with_pypdf2(self, path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using PyPDF2.
        
        Args:
            path: Path to PDF file
            
        Returns:
            Tuple of (content, metadata_dict)
        """
        def extract_sync():
            text_parts = []
            pdf_metadata = {}
            
            with open(path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Handle password-protected PDFs
                if pdf_reader.is_encrypted:
                    if self.password:
                        try:
                            pdf_reader.decrypt(self.password)
                        except Exception as e:
                            raise DocumentLoadError(f"Failed to decrypt PDF: {e}", str(path))
                    else:
                        raise DocumentLoadError("PDF is password-protected but no password provided", str(path))
                
                # Extract PDF metadata
                if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                    pdf_metadata = {
                        key.replace('/', ''): value 
                        for key, value in pdf_reader.metadata.items() 
                        if value is not None
                    }
                
                # Process pages
                total_pages = len(pdf_reader.pages)
                max_pages = self.max_pages or total_pages
                pages_to_process = min(total_pages, max_pages)
                
                for i in range(pages_to_process):
                    try:
                        page = pdf_reader.pages[i]
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            text_parts.append(page_text)
                        
                        # Add page break between pages
                        if i < pages_to_process - 1:
                            text_parts.append('\n\n--- Page Break ---\n\n')
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to extract text from page {i+1}: {e}")
                        continue
                
                pdf_metadata['total_pages'] = total_pages
                pdf_metadata['processed_pages'] = pages_to_process
            
            return '\n'.join(text_parts), pdf_metadata
        
        # Run extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_sync)
    
    def _update_metadata_from_pdf(self, metadata: DocumentMetadata, pdf_metadata: Dict[str, Any]) -> None:
        """
        Update document metadata with PDF-specific information.
        
        Args:
            metadata: Document metadata to update
            pdf_metadata: PDF metadata dictionary
        """
        # Map PDF metadata fields to document metadata
        field_mapping = {
            'Title': 'title',
            'Author': 'author', 
            'Creator': 'author',
            'Subject': 'subject',
            'Producer': 'custom.producer',
            'CreationDate': 'custom.creation_date',
            'ModDate': 'custom.modification_date',
            'total_pages': 'page_count',
            'processed_pages': 'custom.processed_pages'
        }
        
        for pdf_key, metadata_key in field_mapping.items():
            if pdf_key in pdf_metadata and pdf_metadata[pdf_key]:
                value = pdf_metadata[pdf_key]
                
                # Handle nested custom fields
                if '.' in metadata_key:
                    parts = metadata_key.split('.')
                    if parts[0] == 'custom':
                        if not hasattr(metadata, 'custom') or not metadata.custom:
                            metadata.custom = {}
                        metadata.custom[parts[1]] = value
                else:
                    setattr(metadata, metadata_key, value)
        
        # Store all PDF metadata in custom field
        if pdf_metadata:
            if not metadata.custom:
                metadata.custom = {}
            metadata.custom['pdf_metadata'] = pdf_metadata
    
    async def extract_pages_separately(self, source: Union[str, Path], 
                                     start_page: int = 1, end_page: Optional[int] = None) -> List[Document]:
        """
        Extract pages as separate documents.
        
        Args:
            source: Path to PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed, None for all pages)
            
        Returns:
            List of Document objects, one per page
        """
        path = Path(source)
        self.validate_source(path)
        
        base_metadata = self.get_metadata_from_path(path)
        method = self._choose_extraction_method()
        
        documents = []
        
        if method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
            documents = await self._extract_pages_pdfplumber(path, base_metadata, start_page, end_page)
        elif method == 'pypdf2' and PYPDF2_AVAILABLE:
            documents = await self._extract_pages_pypdf2(path, base_metadata, start_page, end_page)
        
        return documents
    
    async def _extract_pages_pdfplumber(self, path: Path, base_metadata: DocumentMetadata,
                                      start_page: int, end_page: Optional[int]) -> List[Document]:
        """Extract individual pages using pdfplumber."""
        def extract_sync():
            documents = []
            
            with pdfplumber.open(str(path), password=self.password) as pdf:
                total_pages = len(pdf.pages)
                end = end_page or total_pages
                
                for page_num in range(start_page - 1, min(end, total_pages)):
                    try:
                        page = pdf.pages[page_num]
                        
                        if self.preserve_layout:
                            page_text = page.extract_text(layout=True)
                        else:
                            page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            # Create metadata for this page
                            page_metadata = DocumentMetadata(
                                source=f"{path}#page-{page_num + 1}",
                                source_type="file",
                                filename=f"{path.stem}_page_{page_num + 1}.txt",
                                file_extension=".txt",
                                loader_type=self.__class__.__name__,
                                custom={
                                    'page_number': page_num + 1,
                                    'total_pages': total_pages,
                                    'original_file': str(path)
                                }
                            )
                            
                            # Copy relevant metadata from base
                            page_metadata.created_at = base_metadata.created_at
                            page_metadata.modified_at = base_metadata.modified_at
                            page_metadata.file_size = base_metadata.file_size
                            
                            content = self.clean_content(page_text)
                            page_metadata.title = self.extract_title(content, page_metadata)
                            
                            document = Document(content=content, metadata=page_metadata)
                            documents.append(document)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue
            
            return documents
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_sync)
    
    async def _extract_pages_pypdf2(self, path: Path, base_metadata: DocumentMetadata,
                                   start_page: int, end_page: Optional[int]) -> List[Document]:
        """Extract individual pages using PyPDF2."""
        def extract_sync():
            documents = []
            
            with open(path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.is_encrypted and self.password:
                    pdf_reader.decrypt(self.password)
                
                total_pages = len(pdf_reader.pages)
                end = end_page or total_pages
                
                for page_num in range(start_page - 1, min(end, total_pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            # Create metadata for this page
                            page_metadata = DocumentMetadata(
                                source=f"{path}#page-{page_num + 1}",
                                source_type="file",
                                filename=f"{path.stem}_page_{page_num + 1}.txt",
                                file_extension=".txt",
                                loader_type=self.__class__.__name__,
                                custom={
                                    'page_number': page_num + 1,
                                    'total_pages': total_pages,
                                    'original_file': str(path)
                                }
                            )
                            
                            # Copy relevant metadata from base
                            page_metadata.created_at = base_metadata.created_at
                            page_metadata.modified_at = base_metadata.modified_at
                            page_metadata.file_size = base_metadata.file_size
                            
                            content = self.clean_content(page_text)
                            page_metadata.title = self.extract_title(content, page_metadata)
                            
                            document = Document(content=content, metadata=page_metadata)
                            documents.append(document)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue
            
            return documents
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_sync)