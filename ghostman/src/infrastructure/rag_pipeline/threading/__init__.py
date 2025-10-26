"""
RAG Pipeline Threading Module

Thread-safe components for ChromaDB and RAG operations in Qt applications.
"""

from .chromadb_worker import (
    ChromaDBWorker,
    RequestType,
    WorkerRequest,
    WorkerResponse,
    get_chromadb_worker,
    shutdown_chromadb_worker
)

from .safe_rag_session import (
    SafeRAGSession,
    create_safe_rag_session
)

__all__ = [
    'ChromaDBWorker',
    'RequestType', 
    'WorkerRequest',
    'WorkerResponse',
    'get_chromadb_worker',
    'shutdown_chromadb_worker',
    'SafeRAGSession',
    'create_safe_rag_session'
]