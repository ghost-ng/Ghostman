"""
Core Memory Manager for the MemGPT-style memory system.

Manages persistent, LLM-editable memory blocks (persona + human) that are
embedded in the system prompt on every LLM call. The LLM can append to
or replace text within these blocks via tool calls.

Storage: ``%APPDATA%/Specter/configs/core_memory.json``
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("specter.memory.core")

# Default persona block content (used on first run)
_DEFAULT_PERSONA = (
    "I am Specter, an AI assistant built into a desktop application. "
    "I help with technical tasks, document formatting, email, calendar, "
    "file search, and general questions. I maintain context about the user "
    "across conversations using my memory system."
)


@dataclass
class CoreMemoryBlock:
    """A named, editable memory block."""
    name: str
    content: str = ""
    max_chars: int = 2000
    updated_at: str = ""

    def char_count(self) -> int:
        return len(self.content)

    def remaining_chars(self) -> int:
        return max(0, self.max_chars - len(self.content))

    def is_full(self) -> bool:
        return len(self.content) >= self.max_chars


class CoreMemoryManager:
    """
    Manages persistent core memory blocks stored in JSON.

    Core memory is always visible in the LLM's system prompt. The LLM
    can edit it via ``core_memory_append`` and ``core_memory_replace``
    tool calls.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            appdata = os.environ.get("APPDATA", "")
            storage_path = Path(appdata) / "Specter" / "configs" / "core_memory.json"
        self._storage_path = storage_path
        self._blocks: Dict[str, CoreMemoryBlock] = {}
        self._load()

    # ------------------------------------------------------------------
    # Block access
    # ------------------------------------------------------------------

    def get_block(self, name: str) -> Optional[CoreMemoryBlock]:
        """Get a memory block by name."""
        return self._blocks.get(name)

    def get_all_blocks(self) -> Dict[str, CoreMemoryBlock]:
        """Return all memory blocks."""
        return dict(self._blocks)

    def get_block_content(self, name: str) -> str:
        """Get a block's content, or empty string if not found."""
        block = self._blocks.get(name)
        return block.content if block else ""

    # ------------------------------------------------------------------
    # Block mutations
    # ------------------------------------------------------------------

    def append_to_block(self, name: str, text: str) -> str:
        """
        Append text to a block. Returns the updated content.
        Raises ValueError if the block would exceed its limit.
        """
        block = self._blocks.get(name)
        if not block:
            raise ValueError(f"Block '{name}' does not exist")

        new_content = block.content + text
        if len(new_content) > block.max_chars:
            raise ValueError(
                f"Would exceed {name} block limit "
                f"({len(new_content)}/{block.max_chars} chars)"
            )

        block.content = new_content
        block.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        logger.info(f"Appended {len(text)} chars to '{name}' block ({block.char_count()}/{block.max_chars})")
        return block.content

    def replace_in_block(self, name: str, old_text: str, new_text: str) -> str:
        """
        Replace exact text in a block. Returns the updated content.
        Raises ValueError if old_text not found or result exceeds limit.
        """
        block = self._blocks.get(name)
        if not block:
            raise ValueError(f"Block '{name}' does not exist")

        if old_text not in block.content:
            raise ValueError(f"Text not found in '{name}' block: '{old_text[:50]}...'")

        new_content = block.content.replace(old_text, new_text, 1)
        if len(new_content) > block.max_chars:
            raise ValueError(
                f"Replacement would exceed {name} block limit "
                f"({len(new_content)}/{block.max_chars} chars)"
            )

        block.content = new_content
        block.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        logger.info(f"Replaced text in '{name}' block ({block.char_count()}/{block.max_chars})")
        return block.content

    def set_block_content(self, name: str, content: str) -> None:
        """Directly set a block's content (for UI editing)."""
        block = self._blocks.get(name)
        if not block:
            raise ValueError(f"Block '{name}' does not exist")
        block.content = content[:block.max_chars]
        block.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

    # ------------------------------------------------------------------
    # System prompt generation
    # ------------------------------------------------------------------

    def to_system_prompt_section(self) -> str:
        """Format core memory blocks for injection into the system prompt."""
        sections = []
        for name, block in self._blocks.items():
            sections.append(f"<{name}>\n{block.content}\n</{name}>")
        return "\n\n".join(sections)

    def get_stats_string(self) -> str:
        """Return a stats string for the system prompt."""
        parts = []
        for name, block in self._blocks.items():
            parts.append(f"{name}: {block.char_count()}/{block.max_chars} chars")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    def estimate_tokens(self) -> int:
        """Estimate total tokens across all blocks."""
        total_chars = sum(b.char_count() for b in self._blocks.values())
        # Rough estimate: ~4 chars per token for English text
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            text = self.to_system_prompt_section()
            return len(enc.encode(text))
        except ImportError:
            return total_chars // 4

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load blocks from JSON file, or create defaults."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, block_data in data.get("blocks", {}).items():
                    self._blocks[name] = CoreMemoryBlock(
                        name=name,
                        content=block_data.get("content", ""),
                        max_chars=block_data.get("max_chars", 2000),
                        updated_at=block_data.get("updated_at", ""),
                    )
                logger.info(f"Loaded {len(self._blocks)} core memory block(s)")
                return
            except Exception as e:
                logger.warning(f"Failed to load core memory: {e}")

        # Create default blocks
        self._blocks = {
            "persona": CoreMemoryBlock(name="persona", content=_DEFAULT_PERSONA, max_chars=2000),
            "human": CoreMemoryBlock(name="human", content="", max_chars=2000),
        }
        self._save()
        logger.info("Created default core memory blocks")

    def _save(self) -> None:
        """Persist blocks to JSON file."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "blocks": {
                    name: {
                        "content": block.content,
                        "max_chars": block.max_chars,
                        "updated_at": block.updated_at,
                    }
                    for name, block in self._blocks.items()
                }
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save core memory: {e}")
