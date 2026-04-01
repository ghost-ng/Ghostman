"""
Memory management module for Specter.

Implements a MemGPT-inspired memory system with three tiers:
- Core Memory: always-in-context, LLM-editable persona + human blocks
- Recall Memory: searchable conversation history (SQLite FTS)
- Archival Memory: long-term semantic storage (FAISS vector store)
"""

from .core_memory import CoreMemoryManager, CoreMemoryBlock
from .memory_orchestrator import MemoryOrchestrator

__all__ = [
    "CoreMemoryManager",
    "CoreMemoryBlock",
    "MemoryOrchestrator",
]
