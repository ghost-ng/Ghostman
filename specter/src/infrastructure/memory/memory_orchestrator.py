"""
Memory Orchestrator for the MemGPT-style memory system.

Sits between the user and the AI service, managing:
- System prompt injection with core memory blocks
- Context window tracking and eviction
- Summarization of evicted messages
- Extraction of send_message / inner_thoughts from tool calls

The orchestrator does NOT call the LLM directly — it prepares the
context and lets the existing AIService tool-call loop handle execution.
The AIService checks for ``send_message`` tool calls to short-circuit.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .core_memory import CoreMemoryManager
from .recall_memory import RecallMemoryService
from .archival_memory import ArchivalMemoryService

logger = logging.getLogger("specter.memory.orchestrator")

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

_MEMGPT_INSTRUCTIONS = """
### Memory Management Instructions

You have a persistent memory system with three tiers:

1. **Core Memory** (below) — always visible, editable by you.
   Update it when you learn important information about the user.
2. **Recall Memory** — full conversation history, searchable by text or date.
   Use ``conversation_search`` or ``conversation_search_date`` to find past discussions.
3. **Archival Memory** — long-term storage, semantically searchable.
   Use ``archival_memory_insert`` to save important information.
   Use ``archival_memory_search`` to retrieve it later.

**Rules:**
- You MUST use the ``memory`` skill with operation ``send_message`` to respond to the user.
- Use ``inner_thoughts`` on every call to reason privately before acting.
- Proactively update core memory when you learn user preferences, names, projects, etc.
- Search recall/archival memory when you need information not in your current context.
- If core memory is full, move less important details to archival first.

**Memory Stats:** {stats}

### Core Memory (editable)

{core_memory}

### Conversation Summary

{summary}
"""


class MemoryOrchestrator:
    """
    Central coordinator for MemGPT-style memory management.

    Usage::

        orchestrator = MemoryOrchestrator()
        if orchestrator.is_enabled():
            system_prompt = orchestrator.build_system_prompt(base_prompt)
            # ... use system_prompt with tool_choice="required" ...
    """

    def __init__(self):
        self._core_memory = CoreMemoryManager()
        self._recall_memory = RecallMemoryService()
        self._archival_memory = ArchivalMemoryService()
        self._summary: str = ""
        self._eviction_threshold: float = 0.75
        self._max_context_tokens: int = 32768

        # Load settings
        self._load_settings()
        logger.info("MemoryOrchestrator initialized")

    def _load_settings(self) -> None:
        """Load MemGPT settings from SettingsManager."""
        try:
            from ..storage.settings_manager import settings
            memgpt = settings.get("memgpt", {})
            self._eviction_threshold = memgpt.get("context_eviction_threshold", 0.75)

            # Core memory block limits
            persona_limit = memgpt.get("core_memory_persona_limit", 2000)
            human_limit = memgpt.get("core_memory_human_limit", 2000)

            persona = self._core_memory.get_block("persona")
            if persona:
                persona.max_chars = persona_limit
            human = self._core_memory.get_block("human")
            if human:
                human.max_chars = human_limit

            # Context window from AI model settings
            self._max_context_tokens = settings.get("ai_model.max_tokens", 32768)
        except Exception as e:
            logger.warning(f"Failed to load MemGPT settings: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """Check if MemGPT mode is enabled in settings."""
        try:
            from ..storage.settings_manager import settings
            return settings.get("memgpt.enabled", False)
        except Exception:
            return False

    @property
    def core_memory(self) -> CoreMemoryManager:
        return self._core_memory

    @property
    def recall_memory(self) -> RecallMemoryService:
        return self._recall_memory

    @property
    def archival_memory(self) -> ArchivalMemoryService:
        return self._archival_memory

    def build_system_prompt(self, base_prompt: str = "") -> str:
        """
        Build the full system prompt with core memory blocks and instructions.

        The base_prompt (user's configured system prompt) is prepended,
        then the MemGPT instructions with core memory blocks are appended.
        """
        stats = self._core_memory.get_stats_string()
        recall_count = self._recall_memory.get_message_count()
        stats += f" | recall: {recall_count} messages"

        core_section = self._core_memory.to_system_prompt_section()
        summary = self._summary or "(No prior conversation summary)"

        memgpt_section = _MEMGPT_INSTRUCTIONS.format(
            stats=stats,
            core_memory=core_section,
            summary=summary,
        )

        if base_prompt:
            return base_prompt.rstrip() + "\n\n" + memgpt_section
        return memgpt_section

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def should_evict(self, messages: List[Dict], max_tokens: Optional[int] = None) -> bool:
        """Check if the context window needs compaction."""
        max_tok = max_tokens or self._max_context_tokens
        estimated = self._estimate_message_tokens(messages)
        threshold = max_tok * self._eviction_threshold
        return estimated > threshold

    def summarize_and_evict(
        self, messages: List[Dict], evict_count: Optional[int] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Summarize the oldest messages and return (new_summary, trimmed_messages).

        Does NOT call the LLM for summarization — returns a simple
        extractive summary. For LLM-based summarization, the caller
        should use the AI service separately.

        Args:
            messages: Current message list (excludes system prompt).
            evict_count: Number of oldest messages to evict (default: 25%).

        Returns:
            (updated_summary, remaining_messages)
        """
        if not messages:
            return self._summary, messages

        if evict_count is None:
            evict_count = max(2, len(messages) // 4)

        evict_count = min(evict_count, len(messages))
        to_evict = messages[:evict_count]
        remaining = messages[evict_count:]

        # Build a simple extractive summary from evicted messages
        evicted_text = []
        for msg in to_evict:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                # Truncate each message for the summary
                evicted_text.append(f"{role}: {content[:150]}")

        if evicted_text:
            new_addition = "\n".join(evicted_text)
            if self._summary:
                self._summary = self._summary + "\n---\n" + new_addition
            else:
                self._summary = new_addition

            # Keep summary under ~1000 chars (will get re-summarized by LLM later)
            if len(self._summary) > 2000:
                self._summary = self._summary[-2000:]

        logger.info(f"Evicted {evict_count} messages, summary now {len(self._summary)} chars")
        return self._summary, remaining

    # ------------------------------------------------------------------
    # Tool call extraction
    # ------------------------------------------------------------------

    @staticmethod
    def is_send_message(tool_call: Dict) -> bool:
        """Check if a tool call is a send_message (terminal action)."""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        # Handle both "memory" skill with operation and direct "send_message"
        if name == "send_message":
            return True
        if name == "memory":
            import json
            try:
                args = json.loads(func.get("arguments", "{}"))
                return args.get("operation") == "send_message"
            except (json.JSONDecodeError, TypeError):
                pass
        return False

    @staticmethod
    def extract_message_text(tool_call: Dict) -> Optional[str]:
        """Extract the visible message from a send_message tool call."""
        import json
        func = tool_call.get("function", {})
        try:
            args = json.loads(func.get("arguments", "{}"))
            return args.get("message")
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def extract_inner_thoughts(tool_call: Dict) -> Optional[str]:
        """Extract inner_thoughts from any tool call."""
        import json
        func = tool_call.get("function", {})
        try:
            args = json.loads(func.get("arguments", "{}"))
            return args.get("inner_thoughts")
        except (json.JSONDecodeError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    def _estimate_message_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens in a message list."""
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "") or ""
            total_chars += len(content)
            # Tool calls add overhead
            if "tool_calls" in msg:
                total_chars += 200  # rough estimate per tool call

        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            text = " ".join(msg.get("content", "") or "" for msg in messages)
            return len(enc.encode(text))
        except ImportError:
            return total_chars // 4

    # ------------------------------------------------------------------
    # Summary management
    # ------------------------------------------------------------------

    @property
    def summary(self) -> str:
        return self._summary

    def set_summary(self, text: str) -> None:
        """Set the conversation summary (e.g., from LLM summarization)."""
        self._summary = text

    def clear_summary(self) -> None:
        """Clear the conversation summary (e.g., on new conversation)."""
        self._summary = ""
