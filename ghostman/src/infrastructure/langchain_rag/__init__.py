"""
LangChain RAG Infrastructure for Ghostman

Provides conversational retrieval-augmented generation using LangChain components:
- OpenAI Embeddings (text-embedding-3-large)
- Chroma vector store
- Conversational chains with memory
- Document loaders and text splitters
"""

from .langchain_rag_pipeline import (
    LangChainRAGPipeline,
    StreamingCallbackHandler
)

from .langchain_integration_service import (
    LangChainIntegrationService,
    ProcessingStatus,
    DocumentProcessingResult
)

from .repl_langchain_integration import REPLLangChainIntegration

__all__ = [
    'LangChainRAGPipeline',
    'StreamingCallbackHandler',
    'LangChainIntegrationService',
    'ProcessingStatus',
    'DocumentProcessingResult',
    'REPLLangChainIntegration'
]

# Version info
__version__ = '1.0.0'