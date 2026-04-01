"""
Memory Skill for the MemGPT-style memory system.

Exposes core memory, recall memory, and archival memory operations
as AI-callable tool functions. Every operation includes an
``inner_thoughts`` parameter for private LLM reasoning.

Operations:
  - send_message: visible response to user (terminal action)
  - core_memory_append: append text to a core memory block
  - core_memory_replace: find-and-replace within a core memory block
  - conversation_search: text search over past conversations
  - conversation_search_date: date-range search over past conversations
  - archival_memory_insert: store text in long-term vector memory
  - archival_memory_search: semantic search over archival memory
"""

import logging
from typing import Any, Dict

from ..interfaces.base_skill import (
    BaseSkill,
    PermissionType,
    SkillCategory,
    SkillMetadata,
    SkillResult,
)

logger = logging.getLogger("specter.skills.memory")


class MemorySkill(BaseSkill):
    """AI-callable skill for MemGPT-style memory management."""

    _shared_core_memory = None
    _shared_recall = None
    _shared_archival = None

    metadata = SkillMetadata(
        skill_id="memory",
        name="Memory Management",
        description=(
            "Manage persistent memory: edit core memory blocks, search "
            "conversation history, store and retrieve long-term memories."
        ),
        category=SkillCategory.SYSTEM,
        icon="brain",
        enabled_by_default=False,  # Enabled only when memgpt.enabled
        requires_confirmation=False,
        ai_callable=True,
    )

    @property
    def parameters(self) -> list:
        from ..interfaces.base_skill import SkillParameter
        return [
            SkillParameter("operation", str, required=True,
                          description="Memory operation to perform",
                          constraints={"choices": [
                              "send_message", "core_memory_append", "core_memory_replace",
                              "conversation_search", "conversation_search_date",
                              "archival_memory_insert", "archival_memory_search",
                          ]}),
            SkillParameter("inner_thoughts", str, required=True,
                          description="Private reasoning (not shown to user)"),
            SkillParameter("message", str, required=False,
                          description="For send_message: text to show user"),
            SkillParameter("block_name", str, required=False,
                          description="Core memory block name (persona or human)"),
            SkillParameter("content", str, required=False,
                          description="Text to append or store"),
            SkillParameter("old_content", str, required=False,
                          description="Text to find for replacement"),
            SkillParameter("new_content", str, required=False,
                          description="Replacement text"),
            SkillParameter("query", str, required=False,
                          description="Search query"),
            SkillParameter("start_date", str, required=False,
                          description="Start date (ISO 8601)"),
            SkillParameter("end_date", str, required=False,
                          description="End date (ISO 8601)"),
            SkillParameter("page", int, required=False,
                          description="Pagination page number", default=0),
        ]

    def get_parameter_schema(self) -> dict:
        """Return the JSON schema for tool calling."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "send_message",
                        "core_memory_append",
                        "core_memory_replace",
                        "conversation_search",
                        "conversation_search_date",
                        "archival_memory_insert",
                        "archival_memory_search",
                    ],
                    "description": "The memory operation to perform.",
                },
                "inner_thoughts": {
                    "type": "string",
                    "description": "Your private reasoning about this action (never shown to user).",
                },
                "message": {
                    "type": "string",
                    "description": "For send_message: the visible text to send to the user.",
                },
                "block_name": {
                    "type": "string",
                    "enum": ["persona", "human"],
                    "description": "For core_memory operations: which block to modify.",
                },
                "content": {
                    "type": "string",
                    "description": "Text to append (core_memory_append) or store (archival_memory_insert).",
                },
                "old_content": {
                    "type": "string",
                    "description": "For core_memory_replace: exact text to find.",
                },
                "new_content": {
                    "type": "string",
                    "description": "For core_memory_replace: replacement text.",
                },
                "query": {
                    "type": "string",
                    "description": "Search query for conversation_search or archival_memory_search.",
                },
                "start_date": {
                    "type": "string",
                    "description": "For conversation_search_date: start date (ISO 8601).",
                },
                "end_date": {
                    "type": "string",
                    "description": "For conversation_search_date: end date (ISO 8601).",
                },
                "page": {
                    "type": "integer",
                    "description": "Pagination page number (0-indexed).",
                    "default": 0,
                },
            },
            "required": ["operation", "inner_thoughts"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        """Dispatch to the appropriate memory operation."""
        operation = kwargs.get("operation", "")
        inner_thoughts = kwargs.get("inner_thoughts", "")

        logger.debug(f"Memory operation: {operation} | Thoughts: {inner_thoughts[:100]}")

        try:
            if operation == "send_message":
                return self._op_send_message(kwargs)
            elif operation == "core_memory_append":
                return self._op_core_memory_append(kwargs)
            elif operation == "core_memory_replace":
                return self._op_core_memory_replace(kwargs)
            elif operation == "conversation_search":
                return self._op_conversation_search(kwargs)
            elif operation == "conversation_search_date":
                return self._op_conversation_search_date(kwargs)
            elif operation == "archival_memory_insert":
                return await self._op_archival_memory_insert(kwargs)
            elif operation == "archival_memory_search":
                return await self._op_archival_memory_search(kwargs)
            else:
                return SkillResult(
                    success=False,
                    message=f"Unknown memory operation: {operation}",
                    error=f"Unknown operation: {operation}",
                )
        except Exception as e:
            logger.error(f"Memory operation '{operation}' failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message=f"Memory operation failed: {e}",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Operation implementations
    # ------------------------------------------------------------------

    def _op_send_message(self, kwargs: Dict[str, Any]) -> SkillResult:
        """send_message — the terminal action that returns visible text."""
        message = kwargs.get("message", "")
        if not message:
            return SkillResult(success=False, message="No message provided", error="Empty message")
        # The message is returned as data so the orchestrator can extract it
        return SkillResult(
            success=True,
            message="Message sent",
            data={"type": "send_message", "message": message},
        )

    def _get_core_memory(self):
        """Get the shared CoreMemoryManager singleton."""
        if not hasattr(MemorySkill, '_shared_core_memory') or MemorySkill._shared_core_memory is None:
            from ...memory.core_memory import CoreMemoryManager
            MemorySkill._shared_core_memory = CoreMemoryManager()
        return MemorySkill._shared_core_memory

    def _get_recall_memory(self):
        """Get the shared RecallMemoryService singleton."""
        if not hasattr(MemorySkill, '_shared_recall') or MemorySkill._shared_recall is None:
            from ...memory.recall_memory import RecallMemoryService
            MemorySkill._shared_recall = RecallMemoryService()
        return MemorySkill._shared_recall

    def _get_archival_memory(self):
        """Get the shared ArchivalMemoryService singleton."""
        if not hasattr(MemorySkill, '_shared_archival') or MemorySkill._shared_archival is None:
            from ...memory.archival_memory import ArchivalMemoryService
            MemorySkill._shared_archival = ArchivalMemoryService()
        return MemorySkill._shared_archival

    def _op_core_memory_append(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Append text to a core memory block."""
        block_name = kwargs.get("block_name", "")
        content = kwargs.get("content", "")
        if not block_name or not content:
            return SkillResult(success=False, message="block_name and content required", error="Missing params")

        try:
            mgr = self._get_core_memory()
            updated = mgr.append_to_block(block_name, content)
            block = mgr.get_block(block_name)
            return SkillResult(
                success=True,
                message=f"Appended to {block_name} ({block.char_count()}/{block.max_chars} chars)",
                data={"block_name": block_name, "content": updated},
            )
        except ValueError as e:
            return SkillResult(success=False, message=str(e), error=str(e))

    def _op_core_memory_replace(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Find-and-replace within a core memory block."""
        block_name = kwargs.get("block_name", "")
        old_content = kwargs.get("old_content", "")
        new_content = kwargs.get("new_content", "")
        if not block_name or not old_content:
            return SkillResult(success=False, message="block_name and old_content required", error="Missing params")

        try:
            mgr = self._get_core_memory()
            updated = mgr.replace_in_block(block_name, old_content, new_content)
            block = mgr.get_block(block_name)
            return SkillResult(
                success=True,
                message=f"Replaced text in {block_name} ({block.char_count()}/{block.max_chars} chars)",
                data={"block_name": block_name, "content": updated},
            )
        except ValueError as e:
            return SkillResult(success=False, message=str(e), error=str(e))

    def _op_conversation_search(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Search past conversation messages by text."""
        query = kwargs.get("query", "")
        page = kwargs.get("page", 0)
        if not query:
            return SkillResult(success=False, message="query is required", error="Missing query")

        svc = self._get_recall_memory()
        results = svc.search_by_text(query, page=page)
        formatted = svc.format_results(results)
        return SkillResult(
            success=True,
            message=f"Found {len(results)} result(s) for '{query}'",
            data={"results": results, "formatted": formatted},
        )

    def _op_conversation_search_date(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Search past conversations by date range."""
        start = kwargs.get("start_date", "")
        end = kwargs.get("end_date", "")
        page = kwargs.get("page", 0)
        if not start or not end:
            return SkillResult(success=False, message="start_date and end_date required", error="Missing dates")

        svc = self._get_recall_memory()
        results = svc.search_by_date(start, end, page=page)
        formatted = svc.format_results(results)
        return SkillResult(
            success=True,
            message=f"Found {len(results)} message(s) between {start} and {end}",
            data={"results": results, "formatted": formatted},
        )

    async def _op_archival_memory_insert(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Store text in archival memory."""
        content = kwargs.get("content", "")
        if not content:
            return SkillResult(success=False, message="content is required", error="Missing content")

        svc = self._get_archival_memory()
        result_msg = await svc.insert(content)
        success = not result_msg.startswith("Error")
        return SkillResult(success=success, message=result_msg)

    async def _op_archival_memory_search(self, kwargs: Dict[str, Any]) -> SkillResult:
        """Semantic search over archival memory."""
        query = kwargs.get("query", "")
        if not query:
            return SkillResult(success=False, message="query is required", error="Missing query")

        svc = self._get_archival_memory()
        results = await svc.search(query)
        formatted = svc.format_results(results)
        return SkillResult(
            success=True,
            message=f"Found {len(results)} archival result(s)",
            data={"results": results, "formatted": formatted},
        )
