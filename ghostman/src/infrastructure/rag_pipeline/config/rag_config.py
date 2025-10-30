"""
RAG Pipeline Configuration System

Centralized configuration management for the complete RAG pipeline with:
- Environment-based configuration
- Type-safe configuration classes using dataclasses
- Configuration validation and defaults
- Support for multiple embedding and LLM providers
- FAISS vector store configuration
- Document processing settings
- Retrieval and ranking parameters
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum

# Import settings manager to get API keys from settings file
try:
    from ...storage.settings_manager import settings
except ImportError:
    # Fallback if settings manager is not available
    settings = None


logger = logging.getLogger("ghostman.rag_config")


class EmbeddingProvider(Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    CUSTOM = "custom"


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CUSTOM = "custom"


class VectorStoreType(Enum):
    """Supported vector store types."""
    CHROMADB = "chromadb"
    FAISS = "faiss"


class TextSplitterType(Enum):
    """Supported text splitter types."""
    RECURSIVE_CHARACTER = "recursive_character"
    SENTENCE = "sentence"
    TOKEN = "token"
    MARKDOWN = "markdown"
    CODE = "code"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding services."""
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    model: str = "text-embedding-3-small"
    api_endpoint: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    dimensions: Optional[int] = None
    max_retries: int = 3
    timeout: float = 30.0
    rate_limit_delay: float = 0.1
    batch_size: int = 100
    
    # Cache settings
    cache_enabled: bool = True
    cache_size: int = 1000
    cache_ttl_hours: int = 24
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.provider == EmbeddingProvider.OPENAI and not self.api_key:
            # Use API key from settings file first, then fallback to environment
            self.api_key = settings.get("ai_model.api_key") if settings else None
            if not self.api_key:
                logger.warning("OpenAI API key not found - embeddings will fail")
                # Don't raise exception here to prevent crashes
                # The pipeline will handle failed embeddings gracefully
        
        # Set default dimensions based on model
        if not self.dimensions:
            model_dimensions = {
                "text-embedding-ada-002": 1536,
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
            }
            self.dimensions = model_dimensions.get(self.model, 1536)


@dataclass
class LLMConfig:
    """Configuration for LLM services."""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4"
    api_endpoint: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_retries: int = 3
    timeout: float = 60.0

    # Prompt templates (configurable)
    system_prompt: str = ("You are an assistant that answers user questions using only the provided context. "
                          "If the answer is not contained in the context, say so clearly.")
    user_prompt_template: str = ("Based on the following information, answer the question. "
                                 "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:")

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.provider == LLMProvider.OPENAI and not self.api_key:
            # Use API key from settings file first, then fallback to environment
            self.api_key = settings.get("ai_model.api_key") if settings else None
            if not self.api_key:
                logger.warning("OpenAI API key not found - LLM queries will fail")
                # Don't raise exception here to prevent crashes
                # The pipeline will handle failed LLM calls gracefully


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    type: VectorStoreType = VectorStoreType.FAISS  # FAISS is stable, ChromaDB causes segfaults
    
    # Common settings
    persist_directory: Optional[str] = None
    collection_name: str = "ghostman_documents"
    distance_function: str = "cosine"  # cosine, l2, ip
    
    # ChromaDB client settings
    host: str = "localhost"
    port: int = 8000
    ssl: bool = False
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Performance settings
    max_batch_size: int = 100
    index_type: str = "hnsw"  # hnsw, flat
    
    # FAISS specific settings
    faiss_index_type: str = "IndexFlatIP"  # IndexFlatIP, IndexHNSWFlat, etc.
    faiss_metric_type: str = "METRIC_INNER_PRODUCT"  # For cosine similarity
    faiss_nlist: int = 100  # Number of clusters for IVF indexes
    faiss_nprobe: int = 10  # Number of clusters to search
    
    def __post_init__(self):
        """Set default persist directory to AppData/Roaming/Ghostman/db if not provided."""
        if not self.persist_directory:
            # Use AppData/Roaming/Ghostman/db as requested (case-sensitive for cross-platform)
            if os.name == 'nt':  # Windows
                appdata = os.getenv('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
                data_dir = os.path.join(appdata, 'Ghostman', 'db')
            else:  # Unix/Mac - use consistent capitalization
                data_dir = os.path.expanduser("~/.Ghostman/db")
            
            # Set FAISS database persist directory
            self.persist_directory = os.path.join(data_dir, "faiss_db")
        
        # Ensure the FAISS database directory exists (create full path)
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            logger.info(f"FAISS database persist directory initialized: {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to create FAISS persist directory {self.persist_directory}: {e}")
            # Try fallback location in AppData
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA')
                if appdata:
                    fallback_dir = os.path.join(appdata, "Ghostman", "rag", "faiss_db")
                else:
                    fallback_dir = os.path.join(os.path.expanduser("~"), ".Ghostman", "rag", "faiss_db")
            else:  # Linux/Mac
                fallback_dir = os.path.join(os.path.expanduser("~"), ".Ghostman", "rag", "faiss_db")

            try:
                os.makedirs(fallback_dir, exist_ok=True)
                self.persist_directory = fallback_dir
                logger.warning(f"Using fallback FAISS directory: {fallback_dir}")
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback directory: {fallback_error}")
                # Use temp directory as last resort
                import tempfile
                self.persist_directory = os.path.join(tempfile.gettempdir(), "ghostman_faiss_temp")
                os.makedirs(self.persist_directory, exist_ok=True)
                logger.warning(f"Using temporary FAISS directory: {self.persist_directory}")


@dataclass
class DocumentLoadingConfig:
    """Configuration for document loading and processing."""
    # Supported file types
    supported_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".pdf", ".docx", ".html", ".htm", ".rtf"
    ])
    
    # PDF processing
    pdf_extraction_method: str = "pdfplumber"  # pdfplumber, pypdf2, both
    preserve_layout: bool = False
    extract_images: bool = False
    
    # Text processing
    encoding_detection: bool = True
    fallback_encoding: str = "utf-8"
    max_file_size_mb: int = 50
    
    # Web content
    web_timeout: float = 10.0
    max_web_content_length: int = 1000000  # 1MB
    user_agent: str = "Ghostman-RAG/1.0"
    
    # Content cleaning
    remove_html_tags: bool = True
    normalize_whitespace: bool = True
    min_content_length: int = 100


@dataclass
class TextProcessingConfig:
    """Configuration for text processing and chunking."""
    # Text splitting
    splitter_type: TextSplitterType = TextSplitterType.RECURSIVE_CHARACTER
    chunk_size: int = 1000
    chunk_overlap: int = 200
    length_function: str = "len"  # len, tiktoken
    
    # Sentence splitting (for sentence splitter)
    sentence_min_length: int = 10
    sentence_max_length: int = 2000
    
    # Token splitting (for token splitter)
    tokenizer_name: str = "cl100k_base"  # tiktoken encoding
    
    # Code splitting (for code splitter)
    code_languages: List[str] = field(default_factory=lambda: [
        "python", "javascript", "java", "cpp", "c", "go", "rust"
    ])
    
    # Text cleaning and normalization
    remove_extra_whitespace: bool = True
    remove_empty_lines: bool = True
    normalize_unicode: bool = True
    
    # Metadata extraction
    extract_titles: bool = True
    extract_sections: bool = True
    preserve_structure: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for document retrieval and ranking."""
    # Basic retrieval
    top_k: int = 5
    similarity_threshold: float = 0.7
    max_context_length: int = 4000
    
    # Retrieval strategies
    use_mmr: bool = True  # Maximal Marginal Relevance
    mmr_diversity_threshold: float = 0.5
    
    # Reranking
    enable_reranking: bool = True
    rerank_top_k: int = 20
    final_top_k: int = 5
    
    # Query processing
    query_expansion: bool = False
    expand_with_synonyms: bool = False
    
    # Filtering
    enable_metadata_filtering: bool = True
    date_range_filtering: bool = True
    
    # Context assembly
    context_overlap_handling: str = "merge"  # merge, truncate, skip
    preserve_chunk_boundaries: bool = True


@dataclass
class RAGPipelineConfig:
    """Main configuration class for the complete RAG pipeline."""
    # Component configurations
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    document_loading: DocumentLoadingConfig = field(default_factory=DocumentLoadingConfig)
    text_processing: TextProcessingConfig = field(default_factory=TextProcessingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    
    # Pipeline settings
    pipeline_name: str = "ghostman_rag"
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_export_interval: int = 300  # seconds
    
    # Async processing
    max_concurrent_requests: int = 10
    request_timeout: float = 60.0
    
    # Storage and persistence
    data_directory: Optional[str] = None
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if not self.data_directory:
            # Use platform-specific AppData location (same as settings_manager)
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA')
                if appdata:
                    self.data_directory = os.path.join(appdata, "Ghostman", "rag")
                else:
                    self.data_directory = os.path.expanduser("~/.Ghostman/rag")
            else:  # Linux/Mac
                self.data_directory = os.path.expanduser("~/.Ghostman/rag")

            # Allow override from environment variable
            self.data_directory = os.getenv("GHOSTMAN_DATA_DIR", self.data_directory)

        # Ensure data directory exists
        Path(self.data_directory).mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the RAG pipeline."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    os.path.join(str(self.data_directory), "rag_pipeline.log"),
                    mode='a'
                )
            ]
        )
    
    @classmethod
    def from_env(cls) -> 'RAGPipelineConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        val = os.getenv("RAG_EMBEDDING_MODEL")
        if val is not None:
            config.embedding.model = val
        
        val = os.getenv("RAG_LLM_MODEL")
        if val is not None:
            config.llm.model = val
        
        val = os.getenv("RAG_CHUNK_SIZE")
        if val is not None:
            try:
                config.text_processing.chunk_size = int(val)
            except ValueError:
                logger.warning("Invalid RAG_CHUNK_SIZE environment variable; must be an integer.")
        
        val = os.getenv("RAG_TOP_K")
        if val is not None:
            try:
                config.retrieval.top_k = int(val)
            except ValueError:
                logger.warning("Invalid RAG_TOP_K environment variable; must be an integer.")
        
        val = os.getenv("RAG_CHROMADB_PATH")
        if val is not None:
            config.vector_store.persist_directory = val
        
        return config
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RAGPipelineConfig':
        """Create configuration from dictionary."""
        # Extract nested configurations
        embedding_config = EmbeddingConfig(**config_dict.get("embedding", {}))
        llm_config = LLMConfig(**config_dict.get("llm", {}))
        vector_store_config = VectorStoreConfig(**config_dict.get("vector_store", {}))
        document_loading_config = DocumentLoadingConfig(**config_dict.get("document_loading", {}))
        text_processing_config = TextProcessingConfig(**config_dict.get("text_processing", {}))
        retrieval_config = RetrievalConfig(**config_dict.get("retrieval", {}))
        
        # Extract main config
        main_config = {k: v for k, v in config_dict.items() 
                      if k not in ["embedding", "llm", "vector_store", 
                                  "document_loading", "text_processing", "retrieval"]}
        
        return cls(
            embedding=embedding_config,
            llm=llm_config,
            vector_store=vector_store_config,
            document_loading=document_loading_config,
            text_processing=text_processing_config,
            retrieval=retrieval_config,
            **main_config
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "embedding": {
                "provider": self.embedding.provider.value,
                "model": self.embedding.model,
                "api_endpoint": self.embedding.api_endpoint,
                "dimensions": self.embedding.dimensions,
                "max_retries": self.embedding.max_retries,
                "timeout": self.embedding.timeout,
                "rate_limit_delay": self.embedding.rate_limit_delay,
                "batch_size": self.embedding.batch_size,
                "cache_enabled": self.embedding.cache_enabled,
                "cache_size": self.embedding.cache_size,
                "cache_ttl_hours": self.embedding.cache_ttl_hours,
            },
            "llm": {
                "provider": self.llm.provider.value,
                "model": self.llm.model,
                "api_endpoint": self.llm.api_endpoint,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "top_p": self.llm.top_p,
                "frequency_penalty": self.llm.frequency_penalty,
                "presence_penalty": self.llm.presence_penalty,
                "max_retries": self.llm.max_retries,
                "timeout": self.llm.timeout,
            },
            "vector_store": {
                "type": self.vector_store.type.value,
                "persist_directory": self.vector_store.persist_directory,
                "collection_name": self.vector_store.collection_name,
                "distance_function": self.vector_store.distance_function,
                "host": self.vector_store.host,
                "port": self.vector_store.port,
                "ssl": self.vector_store.ssl,
                "headers": self.vector_store.headers,
                "max_batch_size": self.vector_store.max_batch_size,
                "index_type": self.vector_store.index_type,
            },
            "document_loading": {
                "supported_extensions": self.document_loading.supported_extensions,
                "pdf_extraction_method": self.document_loading.pdf_extraction_method,
                "preserve_layout": self.document_loading.preserve_layout,
                "extract_images": self.document_loading.extract_images,
                "encoding_detection": self.document_loading.encoding_detection,
                "fallback_encoding": self.document_loading.fallback_encoding,
                "max_file_size_mb": self.document_loading.max_file_size_mb,
                "web_timeout": self.document_loading.web_timeout,
                "max_web_content_length": self.document_loading.max_web_content_length,
                "user_agent": self.document_loading.user_agent,
                "remove_html_tags": self.document_loading.remove_html_tags,
                "normalize_whitespace": self.document_loading.normalize_whitespace,
                "min_content_length": self.document_loading.min_content_length,
            },
            "text_processing": {
                "splitter_type": self.text_processing.splitter_type.value,
                "chunk_size": self.text_processing.chunk_size,
                "chunk_overlap": self.text_processing.chunk_overlap,
                "length_function": self.text_processing.length_function,
                "sentence_min_length": self.text_processing.sentence_min_length,
                "sentence_max_length": self.text_processing.sentence_max_length,
                "tokenizer_name": self.text_processing.tokenizer_name,
                "code_languages": self.text_processing.code_languages,
                "remove_extra_whitespace": self.text_processing.remove_extra_whitespace,
                "remove_empty_lines": self.text_processing.remove_empty_lines,
                "normalize_unicode": self.text_processing.normalize_unicode,
                "extract_titles": self.text_processing.extract_titles,
                "extract_sections": self.text_processing.extract_sections,
                "preserve_structure": self.text_processing.preserve_structure,
            },
            "retrieval": {
                "top_k": self.retrieval.top_k,
                "similarity_threshold": self.retrieval.similarity_threshold,
                "max_context_length": self.retrieval.max_context_length,
                "use_mmr": self.retrieval.use_mmr,
                "mmr_diversity_threshold": self.retrieval.mmr_diversity_threshold,
                "enable_reranking": self.retrieval.enable_reranking,
                "rerank_top_k": self.retrieval.rerank_top_k,
                "final_top_k": self.retrieval.final_top_k,
                "query_expansion": self.retrieval.query_expansion,
                "expand_with_synonyms": self.retrieval.expand_with_synonyms,
                "enable_metadata_filtering": self.retrieval.enable_metadata_filtering,
                "date_range_filtering": self.retrieval.date_range_filtering,
                "context_overlap_handling": self.retrieval.context_overlap_handling,
                "preserve_chunk_boundaries": self.retrieval.preserve_chunk_boundaries,
            },
            "pipeline_name": self.pipeline_name,
            "log_level": self.log_level,
            "enable_metrics": self.enable_metrics,
            "metrics_export_interval": self.metrics_export_interval,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout": self.request_timeout,
            "data_directory": self.data_directory,
            "backup_enabled": self.backup_enabled,
            "backup_interval_hours": self.backup_interval_hours,
        }
    
    def validate(self) -> List[str]:
        """Validate the configuration and return any errors."""
        errors = []
        
        # Validate embedding configuration
        # Don't require API key - we handle failures gracefully
        # if self.embedding.provider == EmbeddingProvider.OPENAI and not self.embedding.api_key:
        #     errors.append("OpenAI API key required for embedding service")
        
        if self.embedding.dimensions is None or self.embedding.dimensions <= 0:
            errors.append("Embedding dimensions must be positive")
        
        # Validate LLM configuration
        # Don't require API key - we handle failures gracefully
        # if self.llm.provider == LLMProvider.OPENAI and not self.llm.api_key:
        #     errors.append("OpenAI API key required for LLM service")
        
        if not (0.0 <= self.llm.temperature <= 2.0):
            errors.append("LLM temperature must be between 0.0 and 2.0")
        
        # Validate text processing
        if self.text_processing.chunk_size <= 0:
            errors.append("Chunk size must be positive")
        
        if self.text_processing.chunk_overlap >= self.text_processing.chunk_size:
            errors.append("Chunk overlap must be less than chunk size")
        
        # Validate retrieval configuration
        if self.retrieval.top_k <= 0:
            errors.append("Retrieval top_k must be positive")
        
        if not (0.0 <= self.retrieval.similarity_threshold <= 1.0):
            errors.append("Similarity threshold must be between 0.0 and 1.0")
        
        # Validate paths
        if self.data_directory and not os.path.exists(self.data_directory):
            try:
                Path(self.data_directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create data directory: {e}")
        
        return errors
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to JSON file."""
        import json
        
        config_dict = self.to_dict()
        
        # Remove sensitive information
        if "api_key" in config_dict.get("embedding", {}):
            config_dict["embedding"]["api_key"] = "***REDACTED***"
        
        if "api_key" in config_dict.get("llm", {}):
            config_dict["llm"]["api_key"] = "***REDACTED***"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'RAGPipelineConfig':
        """Load configuration from JSON file."""
        import json
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)


# Default configuration instance
DEFAULT_CONFIG = RAGPipelineConfig()


def get_config() -> RAGPipelineConfig:
    """Get the current configuration, loading from environment if available."""
    config_file = os.getenv("GHOSTMAN_RAG_CONFIG")
    
    if config_file and os.path.exists(config_file):
        logger.info(f"Loading RAG configuration from {config_file}")
        return RAGPipelineConfig.load_from_file(config_file)
    else:
        logger.info("Using default RAG configuration with environment overrides")
        return RAGPipelineConfig.from_env()


def validate_config(config: RAGPipelineConfig) -> None:
    """Validate configuration and raise exception if invalid."""
    errors = config.validate()
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ValueError(error_msg)


if __name__ == "__main__":
    # Configuration testing and validation
    config = get_config()
    try:
        validate_config(config)
        print("✓ Configuration is valid")
        
        # Print configuration summary
        print(f"✓ Embedding: {config.embedding.provider.value} ({config.embedding.model})")
        print(f"✓ LLM: {config.llm.provider.value} ({config.llm.model})")
        print(f"✓ Vector Store: {config.vector_store.type.value}")
        print(f"✓ Data Directory: {config.data_directory}")
        print(f"✓ Chunk Size: {config.text_processing.chunk_size}")
        print(f"✓ Top-K Retrieval: {config.retrieval.top_k}")
        
    except ValueError as e:
        print(f"✗ Configuration validation failed: {e}")