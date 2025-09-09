"""
Vector Store Module

FAISS-based vector store implementation for the RAG pipeline.
ChromaDB support has been removed to prevent segmentation faults.
"""

from .faiss_client import FAISSClient

__all__ = ['FAISSClient']