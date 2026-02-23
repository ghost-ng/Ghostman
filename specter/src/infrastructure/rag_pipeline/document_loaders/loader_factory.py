"""
Document Loader Factory

Factory for creating and managing document loaders with automatic format detection.
Provides unified interface for loading documents from various sources and formats.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type

from ..config.rag_config import DocumentLoadingConfig
from .base_loader import BaseDocumentLoader, MultiFormatLoader, Document, DocumentLoadError
from .pdf_loader import PDFLoader
from .text_loader import TextLoader
from .web_loader import WebLoader

logger = logging.getLogger("specter.loader_factory")


class DocumentLoaderFactory:
    """
    Factory for creating appropriate document loaders based on source type and format.
    
    Features:
    - Automatic loader selection based on file extension or URL
    - Configuration management for all loaders
    - Loader registration and customization
    - Batch loading with optimal loader assignment
    - Error handling and fallback strategies
    """
    
    def __init__(self, config: Optional[DocumentLoadingConfig] = None):
        """
        Initialize document loader factory.
        
        Args:
            config: Document loading configuration
        """
        self.config = config or DocumentLoadingConfig()
        self.logger = logging.getLogger(f"{__name__}.DocumentLoaderFactory")
        
        # Registry of available loaders
        self._loader_registry: Dict[str, Type[BaseDocumentLoader]] = {}
        self._loader_instances: Dict[str, BaseDocumentLoader] = {}
        
        # Register default loaders
        self._register_default_loaders()
        
        # Create multi-format loader
        self._multi_loader: Optional[MultiFormatLoader] = None
        
    def _register_default_loaders(self):
        """Register default document loaders."""
        self.register_loader('pdf', PDFLoader)
        self.register_loader('text', TextLoader)
        self.register_loader('web', WebLoader)
    
    def register_loader(self, name: str, loader_class: Type[BaseDocumentLoader]):
        """
        Register a document loader class.
        
        Args:
            name: Name identifier for the loader
            loader_class: Loader class to register
        """
        if not issubclass(loader_class, BaseDocumentLoader):
            raise ValueError(f"Loader class must inherit from BaseDocumentLoader")
        
        self._loader_registry[name] = loader_class
        self.logger.debug(f"Registered loader: {name} -> {loader_class.__name__}")
    
    def get_loader(self, loader_name: str, config_override: Optional[Dict[str, Any]] = None) -> BaseDocumentLoader:
        """
        Get a loader instance by name.
        
        Args:
            loader_name: Name of the registered loader
            config_override: Optional configuration override
            
        Returns:
            Loader instance
        """
        if loader_name not in self._loader_registry:
            raise ValueError(f"Unknown loader: {loader_name}")
        
        # Create cache key
        config_key = str(sorted((config_override or {}).items()))
        cache_key = f"{loader_name}:{config_key}"
        
        # Return cached instance if available
        if cache_key in self._loader_instances:
            return self._loader_instances[cache_key]
        
        # Create new instance
        loader_class = self._loader_registry[loader_name]
        loader_config = self._get_loader_config(loader_name, config_override)
        
        loader_instance = loader_class(loader_config)
        self._loader_instances[cache_key] = loader_instance
        
        return loader_instance
    
    def get_loader_for_source(self, source: Union[str, Path]) -> Optional[BaseDocumentLoader]:
        """
        Get the appropriate loader for a given source.
        
        Args:
            source: Source to load (file path or URL)
            
        Returns:
            Appropriate loader instance or None if no loader supports the source
        """
        # Try each registered loader
        for loader_name in self._loader_registry:
            loader = self.get_loader(loader_name)
            if loader.supports(source):
                return loader
        
        return None
    
    def get_multi_loader(self) -> MultiFormatLoader:
        """
        Get a multi-format loader that can handle any supported source.
        
        Returns:
            MultiFormatLoader instance
        """
        if self._multi_loader is None:
            # Create instances of all registered loaders
            loader_instances = []
            for loader_name in self._loader_registry:
                try:
                    loader = self.get_loader(loader_name)
                    loader_instances.append(loader)
                except Exception as e:
                    self.logger.warning(f"Failed to create loader {loader_name}: {e}")
            
            self._multi_loader = MultiFormatLoader(loader_instances)
        
        return self._multi_loader
    
    async def load_document(self, source: Union[str, Path], 
                           loader_hint: Optional[str] = None) -> Document:
        """
        Load a document using the appropriate loader.
        
        Args:
            source: Source to load
            loader_hint: Optional hint for which loader to use
            
        Returns:
            Loaded document
        """
        if loader_hint:
            # Use specified loader
            loader = self.get_loader(loader_hint)
            if not loader.supports(source):
                raise DocumentLoadError(f"Loader {loader_hint} does not support source", str(source))
            return await loader.load(source)
        else:
            # Use multi-loader for automatic detection
            multi_loader = self.get_multi_loader()
            return await multi_loader.load(source)
    
    async def load_documents(self, sources: List[Union[str, Path]], 
                            max_concurrent: int = 5) -> List[Optional[Document]]:
        """
        Load multiple documents using appropriate loaders.
        
        Args:
            sources: List of sources to load
            max_concurrent: Maximum concurrent operations
            
        Returns:
            List of loaded documents (None for failures)
        """
        multi_loader = self.get_multi_loader()
        return await multi_loader.load_batch(sources, max_concurrent)
    
    def _get_loader_config(self, loader_name: str, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific loader.
        
        Args:
            loader_name: Name of the loader
            config_override: Optional configuration override
            
        Returns:
            Configuration dictionary
        """
        base_config = {}
        
        # Apply global configuration
        if loader_name == 'pdf':
            base_config = {
                'extraction_method': getattr(self.config, 'pdf_extraction_method', 'auto'),
                'preserve_layout': getattr(self.config, 'preserve_layout', False),
                'extract_images': getattr(self.config, 'extract_images', False),
                'max_file_size_mb': getattr(self.config, 'max_file_size_mb', 50),
            }
        elif loader_name == 'text':
            base_config = {
                'encoding_detection': getattr(self.config, 'encoding_detection', True),
                'fallback_encoding': getattr(self.config, 'fallback_encoding', 'utf-8'),
                'normalize_whitespace': getattr(self.config, 'normalize_whitespace', True),
                'min_content_length': getattr(self.config, 'min_content_length', 100),
                'max_file_size_mb': getattr(self.config, 'max_file_size_mb', 50),
            }
        elif loader_name == 'web':
            base_config = {
                'timeout': getattr(self.config, 'web_timeout', 10.0),
                'max_content_length': getattr(self.config, 'max_web_content_length', 1000000),
                'user_agent': getattr(self.config, 'user_agent', 'Specter-RAG/1.0'),
                'min_content_length': getattr(self.config, 'min_content_length', 100),
            }
        
        # Apply common configuration
        base_config.update({
            'min_content_length': getattr(self.config, 'min_content_length', 100),
            'normalize_whitespace': getattr(self.config, 'normalize_whitespace', True),
            'remove_html_tags': getattr(self.config, 'remove_html_tags', True),
        })
        
        # Apply override configuration
        if config_override:
            base_config.update(config_override)
        
        return base_config
    
    def get_supported_extensions(self) -> set:
        """
        Get all supported file extensions.
        
        Returns:
            Set of supported extensions
        """
        extensions = set()
        
        for loader_name in self._loader_registry:
            try:
                loader = self.get_loader(loader_name)
                if hasattr(loader, 'SUPPORTED_EXTENSIONS'):
                    extensions.update(loader.SUPPORTED_EXTENSIONS)
            except Exception as e:
                self.logger.warning(f"Failed to get extensions for {loader_name}: {e}")
        
        return extensions
    
    def is_supported(self, source: Union[str, Path]) -> bool:
        """
        Check if a source is supported by any registered loader.
        
        Args:
            source: Source to check
            
        Returns:
            True if supported
        """
        return self.get_loader_for_source(source) is not None
    
    def get_loader_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all loader instances.
        
        Returns:
            Dictionary of loader statistics
        """
        stats = {}
        
        for cache_key, loader in self._loader_instances.items():
            loader_name = cache_key.split(':')[0]
            stats[cache_key] = {
                'loader_name': loader_name,
                'class_name': loader.__class__.__name__,
                'stats': loader.get_stats()
            }
        
        return stats
    
    def reset_all_stats(self):
        """Reset statistics for all loader instances."""
        for loader in self._loader_instances.values():
            loader.reset_stats()
    
    async def test_loaders(self) -> Dict[str, Dict[str, Any]]:
        """
        Test all registered loaders for basic functionality.
        
        Returns:
            Test results for each loader
        """
        results = {}
        
        for loader_name in self._loader_registry:
            results[loader_name] = {
                'available': False,
                'error': None,
                'supported_extensions': [],
                'class_name': None
            }
            
            try:
                loader = self.get_loader(loader_name)
                results[loader_name]['available'] = True
                results[loader_name]['class_name'] = loader.__class__.__name__
                
                if hasattr(loader, 'SUPPORTED_EXTENSIONS'):
                    results[loader_name]['supported_extensions'] = list(loader.SUPPORTED_EXTENSIONS)
                
                # Test basic methods
                test_source = "test.txt"
                supports_result = loader.supports(test_source)
                results[loader_name]['supports_method_works'] = True
                
            except Exception as e:
                results[loader_name]['error'] = str(e)
                self.logger.warning(f"Loader {loader_name} test failed: {e}")
        
        return results
    
    def __str__(self) -> str:
        return f"DocumentLoaderFactory(loaders={list(self._loader_registry.keys())})"
    
    def __repr__(self) -> str:
        return f"DocumentLoaderFactory(config={self.config}, loaders={list(self._loader_registry.keys())})"


# Global factory instance
_global_factory: Optional[DocumentLoaderFactory] = None


def get_document_loader_factory(config: Optional[DocumentLoadingConfig] = None) -> DocumentLoaderFactory:
    """
    Get the global document loader factory instance.
    
    Args:
        config: Optional configuration (only used on first call)
        
    Returns:
        DocumentLoaderFactory instance
    """
    global _global_factory
    
    if _global_factory is None:
        _global_factory = DocumentLoaderFactory(config)
    
    return _global_factory


def set_document_loader_factory(factory: DocumentLoaderFactory):
    """
    Set the global document loader factory instance.
    
    Args:
        factory: Factory instance to set as global
    """
    global _global_factory
    _global_factory = factory


async def load_document(source: Union[str, Path], 
                       loader_hint: Optional[str] = None,
                       config: Optional[DocumentLoadingConfig] = None) -> Document:
    """
    Convenience function to load a single document.
    
    Args:
        source: Source to load
        loader_hint: Optional loader hint
        config: Optional configuration
        
    Returns:
        Loaded document
    """
    factory = get_document_loader_factory(config)
    return await factory.load_document(source, loader_hint)


async def load_documents(sources: List[Union[str, Path]], 
                        max_concurrent: int = 5,
                        config: Optional[DocumentLoadingConfig] = None) -> List[Optional[Document]]:
    """
    Convenience function to load multiple documents.
    
    Args:
        sources: List of sources to load
        max_concurrent: Maximum concurrent operations
        config: Optional configuration
        
    Returns:
        List of loaded documents (None for failures)
    """
    factory = get_document_loader_factory(config)
    return await factory.load_documents(sources, max_concurrent)