"""
Tool Calling Bridge for AI Provider Integration.

Converts BaseSkill instances into OpenAI and Anthropic tool-calling definitions,
and handles parsing tool_call responses back into skill execution requests.

This module acts as the translation layer between the Ghostman skills framework
and the tool-calling protocols used by OpenAI-compatible and Anthropic APIs.

Supported providers:
    - "openai"    : OpenAI, OpenRouter, and any OpenAI-compatible endpoint
    - "anthropic" : Anthropic Claude API

Usage:
    >>> from ghostman.src.infrastructure.skills.core.tool_bridge import tool_bridge
    >>> definitions = tool_bridge.get_tool_definitions(registry, "openai")
    >>> if tool_bridge.is_tool_call_response(response_data, "openai"):
    ...     calls = tool_bridge.parse_tool_calls(response_data, "openai")
    ...     for call in calls:
    ...         result = await registry.get(call["skill_id"]).execute(**call["arguments"])
    ...         tool_msg = tool_bridge.format_tool_result(call["id"], result, "openai")
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..interfaces.base_skill import SkillResult

logger = logging.getLogger("ghostman.skills.tool_bridge")


class ToolCallingBridge:
    """
    Stateless bridge that translates between the Ghostman skills framework
    and AI provider tool-calling protocols.

    All methods are regular instance methods on a module-level singleton.
    No instance state is required; the singleton pattern is used purely for
    a clean calling convention (``tool_bridge.method(...)``).
    """

    # ------------------------------------------------------------------
    # 1. Build tool definitions for a given provider
    # ------------------------------------------------------------------

    def get_tool_definitions(
        self,
        registry: "SkillRegistry",
        provider_format: str,
    ) -> List[Dict[str, Any]]:
        """
        Build a list of tool/function definitions consumable by an AI provider.

        Iterates all registered skills, keeps only those that are both
        ``ai_callable`` and enabled in the user's settings, then formats
        each skill's parameter schema according to *provider_format*.

        Args:
            registry: The SkillRegistry containing all registered skills.
            provider_format: Either ``"openai"`` or ``"anthropic"``.

        Returns:
            A list of tool definition dicts ready to be sent to the provider.
        """
        # Lazy import to avoid circular dependency at module load time
        from ...storage.settings_manager import settings

        # Global kill-switch for tool calling
        if not settings.get("tools.enabled", True):
            logger.debug("Tool calling globally disabled via settings")
            return []

        definitions: List[Dict[str, Any]] = []

        for metadata in registry.list_all():
            # Only expose skills explicitly marked as AI-callable
            if not metadata.ai_callable:
                continue

            # Per-tool toggle (defaults to enabled)
            tool_enabled = settings.get(
                f"tools.{metadata.skill_id}.enabled", True
            )
            if not tool_enabled:
                logger.debug(
                    "Skill '%s' disabled via per-tool setting", metadata.skill_id
                )
                continue

            skill = registry.get(metadata.skill_id)
            if skill is None:
                logger.warning(
                    "Skill '%s' listed in metadata but not found in registry",
                    metadata.skill_id,
                )
                continue

            parameter_schema = skill.get_parameter_schema()

            if provider_format == "anthropic":
                definition = {
                    "name": metadata.skill_id,
                    "description": metadata.description,
                    "input_schema": parameter_schema,
                }
            else:
                # Default to OpenAI-compatible format (works for OpenRouter, local, etc.)
                definition = {
                    "type": "function",
                    "function": {
                        "name": metadata.skill_id,
                        "description": metadata.description,
                        "parameters": parameter_schema,
                    },
                }

            definitions.append(definition)
            logger.debug(
                "Added tool definition for skill '%s' (%s format)",
                metadata.skill_id,
                provider_format,
            )

        logger.info(
            "Generated %d tool definition(s) for provider format '%s'",
            len(definitions),
            provider_format,
        )
        return definitions

    # ------------------------------------------------------------------
    # 1b. Build tool awareness prompt for system message
    # ------------------------------------------------------------------

    def build_tool_awareness_prompt(self, registry: "SkillRegistry") -> str:
        """
        Build a system prompt section describing available tools.

        This is injected into the system prompt so the AI model knows what
        tools it has and when to use them.  Without this, models often refuse
        file paths or suggest cloud uploads instead of using their tools.
        """
        from ...storage.settings_manager import settings

        if not settings.get("tools.enabled", True):
            return ""

        USAGE_EXAMPLES = {
            "web_search": "User asks 'search for penguins' or 'what is quantum computing' → call web_search with the query.",
            "docx_formatter": "User says 'format my report.docx' or provides a .docx file path → call docx_formatter with the file_path.",
            "screen_capture": "User says 'take a screenshot' or 'capture my screen' → call screen_capture.",
            "task_tracker": "User says 'add a task' or 'show my tasks' → call task_tracker.",
            "email_draft": "User says 'draft an email to John' → call email_draft.",
            "email_search": "User says 'find emails from Sarah' → call email_search.",
            "calendar_event": "User says 'schedule a meeting tomorrow at 3pm' → call calendar_event.",
            "file_search": "User says 'find files named report' → call file_search.",
        }

        lines = [
            "\n## Your Tools",
            "You have access to tools that let you perform actions on the user's local computer.",
            "When a user asks about files, searching the web, formatting documents, or capturing the screen — USE your tools.",
            "IMPORTANT: You CAN access local files on the user's computer through your tools. "
            "When a user provides a file path (like C:/Users/.../file.docx), use the appropriate tool. "
            "Do NOT say you cannot access local files.",
            "",
            "Available tools:",
        ]

        tool_count = 0
        for metadata in registry.list_all():
            if not metadata.ai_callable:
                continue
            tool_enabled = settings.get(
                f"tools.{metadata.skill_id}.enabled", True
            )
            if not tool_enabled:
                continue

            example = USAGE_EXAMPLES.get(metadata.skill_id, "")
            example_text = f" Example: {example}" if example else ""
            lines.append(
                f"- **{metadata.skill_id}**: {metadata.description}.{example_text}"
            )
            tool_count += 1

        if tool_count == 0:
            return ""

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 2. Detect provider from base URL
    # ------------------------------------------------------------------

    def detect_provider(self, base_url: str) -> str:
        """
        Infer the provider format from an API base URL.

        Args:
            base_url: The API endpoint URL (e.g. ``"https://api.anthropic.com/v1"``).

        Returns:
            ``"anthropic"`` if the URL contains ``"anthropic"``,
            otherwise ``"openai"`` (the safe default for OpenAI, OpenRouter,
            and local inference servers).
        """
        if base_url and "anthropic" in base_url.lower():
            return "anthropic"
        return "openai"

    # ------------------------------------------------------------------
    # 3. Parse tool calls from a provider response
    # ------------------------------------------------------------------

    def parse_tool_calls(
        self,
        response_data: Dict[str, Any],
        provider_format: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract tool call information from an AI provider response.

        Args:
            response_data: The raw JSON response dict from the provider.
            provider_format: Either ``"openai"`` or ``"anthropic"``.

        Returns:
            A list of dicts, each containing:
                - ``id``       : The provider-assigned tool call ID.
                - ``skill_id`` : The skill identifier (function/tool name).
                - ``arguments``: The parsed argument dict.

            Malformed entries are logged and skipped rather than raising.
        """
        if provider_format == "anthropic":
            return self._parse_anthropic_tool_calls(response_data)
        return self._parse_openai_tool_calls(response_data)

    def _parse_openai_tool_calls(
        self, response_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse tool calls from an OpenAI-compatible response."""
        results: List[Dict[str, Any]] = []

        try:
            choices = response_data.get("choices", [])
            if not choices:
                return results

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            for tc in tool_calls:
                try:
                    call_id = tc.get("id", "")
                    function_data = tc.get("function", {})
                    skill_id = function_data.get("name", "")
                    raw_args = function_data.get("arguments", "{}")

                    # OpenAI sends arguments as a JSON string
                    if isinstance(raw_args, str):
                        arguments = json.loads(raw_args)
                    else:
                        arguments = raw_args

                    results.append(
                        {
                            "id": call_id,
                            "skill_id": skill_id,
                            "arguments": arguments,
                        }
                    )
                except (json.JSONDecodeError, TypeError, KeyError) as exc:
                    logger.warning(
                        "Skipping malformed OpenAI tool call: %s (error: %s)",
                        tc,
                        exc,
                    )
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "Failed to parse OpenAI tool calls from response: %s", exc
            )

        return results

    def _parse_anthropic_tool_calls(
        self, response_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse tool calls from an Anthropic response."""
        results: List[Dict[str, Any]] = []

        try:
            content_blocks = response_data.get("content", [])

            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue

                try:
                    call_id = block.get("id", "")
                    skill_id = block.get("name", "")
                    arguments = block.get("input", {})

                    # Anthropic provides arguments as a dict directly
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)

                    results.append(
                        {
                            "id": call_id,
                            "skill_id": skill_id,
                            "arguments": arguments,
                        }
                    )
                except (json.JSONDecodeError, TypeError, KeyError) as exc:
                    logger.warning(
                        "Skipping malformed Anthropic tool_use block: %s (error: %s)",
                        block,
                        exc,
                    )
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Failed to parse Anthropic tool calls from response: %s", exc
            )

        return results

    # ------------------------------------------------------------------
    # 4. Format a tool result for the conversation history
    # ------------------------------------------------------------------

    def format_tool_result(
        self,
        tool_call_id: str,
        result: SkillResult,
        provider_format: str,
    ) -> Dict[str, Any]:
        """
        Format a SkillResult into a message dict suitable for appending
        to the conversation history so the AI can see the tool output.

        Args:
            tool_call_id: The ID returned by the provider for this tool call.
            result: The SkillResult produced by executing the skill.
            provider_format: Either ``"openai"`` or ``"anthropic"``.

        Returns:
            A message dict in the provider's expected format.
        """
        content_payload = json.dumps(
            {
                "success": result.success,
                "message": result.message,
                "data": result.data,
            },
            default=str,  # Fallback serializer for non-JSON types (datetime, Path, etc.)
        )

        if provider_format == "anthropic":
            # Anthropic requires tool results inside a user-role message
            # with content blocks. When batching multiple results, the
            # caller should collect these blocks into a single message.
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": content_payload,
                    }
                ],
            }

        # OpenAI-compatible format
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content_payload,
        }

    # ------------------------------------------------------------------
    # 5. Format the assistant's tool-call message for conversation history
    # ------------------------------------------------------------------

    def format_assistant_tool_call_message(
        self,
        response_data: Dict[str, Any],
        provider_format: str,
    ) -> Dict[str, Any]:
        """
        Extract the assistant message that contains tool calls, so it can
        be appended to the conversation history before the tool results.

        Args:
            response_data: The raw JSON response dict from the provider.
            provider_format: Either ``"openai"`` or ``"anthropic"``.

        Returns:
            A message dict representing the assistant's tool-call turn.
        """
        if provider_format == "anthropic":
            return {
                "role": "assistant",
                "content": response_data.get("content", []),
            }

        # OpenAI-compatible: return the full message object from choices
        try:
            message = response_data["choices"][0]["message"]
            # Return a copy to avoid mutating the original response
            return dict(message)
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "Could not extract assistant tool-call message (OpenAI): %s", exc
            )
            return {"role": "assistant", "content": None, "tool_calls": []}

    # ------------------------------------------------------------------
    # 6. Check whether a response contains tool calls
    # ------------------------------------------------------------------

    def is_tool_call_response(
        self,
        response_data: Dict[str, Any],
        provider_format: str,
    ) -> bool:
        """
        Determine whether a provider response contains tool calls that
        need to be executed.

        Args:
            response_data: The raw JSON response dict from the provider.
            provider_format: Either ``"openai"`` or ``"anthropic"``.

        Returns:
            ``True`` if the response contains at least one tool call.
        """
        try:
            if provider_format == "anthropic":
                content_blocks = response_data.get("content", [])
                return any(
                    isinstance(block, dict) and block.get("type") == "tool_use"
                    for block in content_blocks
                )

            # OpenAI-compatible
            choices = response_data.get("choices", [])
            if not choices:
                return False

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls")
            return bool(tool_calls)

        except (KeyError, IndexError, TypeError) as exc:
            logger.debug("Error checking for tool calls: %s", exc)
            return False


# Module-level singleton for convenient access
tool_bridge = ToolCallingBridge()
