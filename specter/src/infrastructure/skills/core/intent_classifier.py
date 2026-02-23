"""
Intent Classifier - Hybrid intent detection system.

Combines pattern matching with optional AI fallback for detecting user intent
to execute skills from natural language input.
"""

import logging
import re
import json
import asyncio
from functools import lru_cache
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from ..interfaces.skill_manager import SkillIntent, IIntentClassifier

logger = logging.getLogger("specter.skills.intent")


@dataclass
class IntentPattern:
    """
    A pattern for matching user intent.

    Attributes:
        skill_id: ID of skill this pattern triggers
        patterns: List of regex patterns or keywords
        parameter_extractors: Functions to extract parameters from matched text
        confidence_boost: Additional confidence added when matched (0.0 to 0.3)
        examples: Example phrases that match this pattern
    """

    skill_id: str
    patterns: List[str]
    parameter_extractors: Dict[str, Callable[[str], Any]] = field(default_factory=dict)
    confidence_boost: float = 0.0
    examples: List[str] = field(default_factory=list)


class IntentClassifier(IIntentClassifier):
    """
    Hybrid intent classifier using pattern matching and optional AI fallback.

    The classifier works in two stages:
    1. **Pattern Matching** (instant, local): Fast regex/keyword matching
    2. **AI Fallback** (optional): Use AI for ambiguous cases

    This provides a balance of speed and accuracy.

    Attributes:
        _patterns: Dictionary mapping skill_id to list of IntentPattern
        _confidence_threshold: Minimum confidence to return intent (0.0 to 1.0)
        _use_ai_fallback: Whether to use AI for low-confidence matches

    Example:
        >>> classifier = IntentClassifier()
        >>> classifier.register_patterns(
        ...     "screen_capture",
        ...     patterns=[
        ...         "screenshot",
        ...         "capture screen",
        ...         r"take a (?P<mode>rectangle|window) screenshot"
        ...     ]
        ... )
        >>> intent = await classifier.detect_intent("take a screenshot")
        >>> print(f"{intent.skill_id}: {intent.confidence:.2%}")
    """

    # Pre-defined patterns for core skills
    DEFAULT_PATTERNS = {
        "email_draft": [
            r"(draft|write|compose|create)\s+(an?\s+)?(email|message)",
            r"send\s+(an?\s+)?email",
            r"email\s+(.+)\s+(to|about)",
        ],
        "email_search": [
            r"(find|search|look\s+for)\s+(my\s+)?(email|message)",
            r"show\s+(me\s+)?(emails?|messages?)\s+(from|about|containing)",
            r"when\s+did\s+.*(email|send|receive)",
        ],
        "calendar_event": [
            r"(schedule|create|add|set\s+up)\s+(a\s+)?(meeting|appointment|event)",
            r"put.*on\s+(my\s+)?calendar",
            r"add\s+to\s+calendar",
        ],
        "calendar_search": [
            r"(what|show|check|view)\s+(my\s+)?(calendar|schedule|meetings|appointments)",
            r"(am\s+I|are\s+we)\s+(free|available|busy)\s+(at|on|this|tomorrow|next)",
            r"(upcoming|today'?s?|tomorrow'?s?|this\s+week'?s?)\s+(meetings?|appointments?|calendar|schedule)",
        ],
        "file_search": [
            r"(find|locate|search\s+for)\s+(a\s+)?(file|document|folder)",
            r"where\s+is\s+(my|the)",
            r"show\s+me\s+files",
        ],
        "docx_formatter": [
            r"(format|reformat|standardize|clean\s*up|tidy|prettify)\s+(this\s+|the\s+|my\s+)?(document|doc|docx|word\s+file|word\s+document|file)",
            r"(change|set|make|convert)\s+(all\s+)?(fonts?|font\s*size|text)\s+to\s+",
            r"(fix|normalize|standardize)\s+(the\s+)?(fonts?|margins?|spacing|bullets?|headings?|spelling|formatting)",
            r"(set|change|update)\s+(all\s+)?(text|everything)\s+to\s+\d+\s*(pt|point)",
            r"(fix|check|correct)\s+(the\s+)?spelling",
        ],
        "screen_capture": [
            r"(take|capture|grab)\s+(a\s+)?(screenshot|screen\s+capture|screen\s+shot)",
            r"screenshot",
            r"capture\s+(my\s+)?screen",
        ],
        "task_tracker": [
            r"(add|create|new)\s+task",
            r"show\s+(my\s+)?tasks",
            r"(mark|complete|finish)\s+task",
            r"task\s+list",
            r"(open|show)\s+task\s+(list|panel|manager|control)",
            r"^tasks$",  # Just "tasks" command
            r"task\s+manager",
            r"manage\s+tasks",
            r"view\s+tasks",
        ],
        "skills_help": [
            r"(show|list|display)\s+(me\s+)?(my\s+)?(skills|tools|capabilities)",
            r"(what|which)\s+(skills|tools|capabilities)\s+(do\s+(you|i)\s+have|are\s+available)",
            r"(available|enabled)\s+(skills|tools)",
            r"how\s+do\s+(skills|tools)\s+work",
            r"tell\s+me\s+about\s+(your\s+)?(skills|tools|capabilities)",
            r"help\s+(with\s+)?skills",
            r"skills?\s+help",
            r"^skills$",
            r"^my\s+skills$",
            r"what\s+can\s+you\s+do",
        ],
    }

    # AI Classification Prompt Template
    AI_CLASSIFICATION_PROMPT_TEMPLATE = """You are a skill classification assistant for Specter, a desktop AI assistant. Analyze the user's request and determine which skill (if any) they want to use.

Available Skills:
{skill_list}

User Request: "{user_input}"

Instructions:
1. Determine if the user wants to use one of the available skills
2. If yes, identify which skill and extract any parameters mentioned
3. Return ONLY valid JSON (no markdown, no code blocks, no explanations)
4. If no skill matches, set skill_id to null

Response Format (JSON only):
{{
  "skill_id": "skill_identifier_or_null",
  "confidence": 0.85,
  "reasoning": "Brief explanation of why you chose this skill",
  "parameters": {{
    "param_name": "extracted_value"
  }}
}}

Examples:
User: "take a screenshot"
{{"skill_id": "screen_capture", "confidence": 0.95, "reasoning": "User requests screenshot", "parameters": {{}}}}

User: "find my report.pdf file"
{{"skill_id": "file_search", "confidence": 0.90, "reasoning": "User wants to search for a file", "parameters": {{"filename": "report.pdf"}}}}

User: "what's the weather today"
{{"skill_id": null, "confidence": 0.0, "reasoning": "No matching skill available", "parameters": {{}}}}

Now classify the user's request."""

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        use_ai_fallback: bool = False
    ):
        """
        Initialize intent classifier.

        Args:
            confidence_threshold: Minimum confidence to return intent (default 0.75)
            use_ai_fallback: Whether to use AI for ambiguous cases (default False)
        """
        self._patterns: Dict[str, List[IntentPattern]] = {}
        self._confidence_threshold = confidence_threshold
        self._use_ai_fallback = use_ai_fallback

        # Register default patterns
        self._register_default_patterns()

        logger.info(
            f"Intent classifier initialized (threshold={confidence_threshold:.2f}, "
            f"ai_fallback={use_ai_fallback})"
        )

    def _register_default_patterns(self) -> None:
        """Register default patterns for built-in skills."""
        for skill_id, patterns in self.DEFAULT_PATTERNS.items():
            # Add confidence boost for skills with simple, unambiguous keywords
            # This ensures single-word triggers like "screenshot" meet the 75% threshold
            confidence_boost = 0.30 if skill_id in ["screen_capture", "task_tracker", "skills_help", "docx_formatter"] else 0.0

            # Add parameter extractors for skills that need them
            parameter_extractors = {}
            if skill_id == "task_tracker":
                parameter_extractors["action"] = self._extract_task_action
            elif skill_id == "docx_formatter":
                parameter_extractors["operations"] = self._extract_docx_operations
                parameter_extractors["font_size"] = self._extract_font_size
                parameter_extractors["font_name"] = self._extract_font_name

            intent_pattern = IntentPattern(
                skill_id=skill_id,
                patterns=patterns,
                confidence_boost=confidence_boost,
                parameter_extractors=parameter_extractors
            )

            if skill_id not in self._patterns:
                self._patterns[skill_id] = []

            self._patterns[skill_id].append(intent_pattern)

        logger.debug(f"Registered default patterns for {len(self.DEFAULT_PATTERNS)} skills")

    def _extract_task_action(self, user_input: str) -> str:
        """
        Extract the appropriate action for task_tracker skill based on user input.

        Args:
            user_input: User's input text

        Returns:
            Action string: 'show', 'list', 'create', etc.
        """
        text_lower = user_input.lower().strip()

        # Commands that should open the GUI control panel
        show_patterns = [
            "tasks", "task list", "show tasks", "view tasks",
            "open task", "task panel", "task manager", "manage tasks"
        ]

        for pattern in show_patterns:
            if pattern in text_lower:
                return "show"

        # Commands that should create a new task
        if any(word in text_lower for word in ["add", "create", "new"]):
            return "create"

        # Commands that should list tasks (text output)
        if "list" in text_lower:
            return "list"

        # Default to show (open GUI)
        return "show"

    def _extract_docx_operations(self, user_input: str) -> Optional[list]:
        """
        Extract formatting operations and settings from user input.

        Parses natural language to determine which docx_formatter operations
        to run and what font size to use.

        Args:
            user_input: User's input text

        Returns:
            List of operation names, or None for all defaults
        """
        text_lower = user_input.lower().strip()
        operations = []

        # Map keywords to operations
        op_keywords = {
            "standardize_fonts": ["font", "fonts", "font size", "font name", "typeface"],
            "fix_margins": ["margin", "margins"],
            "normalize_spacing": ["spacing", "line spacing", "space"],
            "fix_bullets": ["bullet", "bullets", "list", "lists"],
            "fix_spelling": ["spell", "spelling", "spellcheck", "typo", "typos"],
            "fix_case": ["case", "casing", "uppercase", "lowercase", "capitalization"],
            "normalize_headings": ["heading", "headings", "header", "headers", "title"],
        }

        for op, keywords in op_keywords.items():
            if any(kw in text_lower for kw in keywords):
                operations.append(op)

        # "format" / "clean up" / "standardize" with no specifics → all operations
        if not operations:
            return None  # None means use all defaults

        return operations

    def _extract_font_size(self, user_input: str) -> Optional[int]:
        """Extract font size in points from user input (e.g. '14pt', '12 point')."""
        match = re.search(r'(\d+)\s*(?:pt|point|pts|points)', user_input.lower())
        if match:
            size = int(match.group(1))
            if 6 <= size <= 72:  # Reasonable font size range
                return size
        return None

    def _extract_font_name(self, user_input: str) -> Optional[str]:
        """Extract font name from user input."""
        known_fonts = [
            "calibri", "arial", "times new roman", "times",
            "helvetica", "georgia", "verdana", "courier",
            "courier new", "comic sans", "tahoma", "trebuchet",
            "cambria", "garamond", "palatino",
        ]
        text_lower = user_input.lower()
        for font in known_fonts:
            if font in text_lower:
                return font.title()  # Return properly cased
        return None

    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillIntent]:
        """
        Detect skill intent from user input.

        Args:
            user_input: User's natural language input
            context: Optional contextual information

        Returns:
            SkillIntent if detected above threshold, None otherwise
        """
        if not user_input.strip():
            return None

        # Stage 1: Pattern matching
        pattern_match = self._pattern_match(user_input, context)

        if pattern_match and pattern_match.confidence >= 0.85:
            # High confidence from pattern matching
            logger.info(
                f"✓ Intent detected (pattern): {pattern_match.skill_id} "
                f"({pattern_match.confidence:.2%})"
            )
            return pattern_match

        # Stage 2: AI fallback (if enabled and pattern confidence is low)
        if self._use_ai_fallback and (not pattern_match or pattern_match.confidence < 0.75):
            ai_match = await self._ai_classify(user_input, context)
            if ai_match and ai_match.confidence > (pattern_match.confidence if pattern_match else 0):
                logger.info(
                    f"✓ Intent detected (AI): {ai_match.skill_id} "
                    f"({ai_match.confidence:.2%})"
                )
                return ai_match

        # Return pattern match if above threshold
        if pattern_match and pattern_match.confidence >= self._confidence_threshold:
            logger.info(
                f"✓ Intent detected: {pattern_match.skill_id} "
                f"({pattern_match.confidence:.2%})"
            )
            return pattern_match

        logger.debug(f"No intent detected for: {user_input[:50]}...")
        return None

    def _pattern_match(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillIntent]:
        """
        Perform pattern matching on user input.

        Args:
            user_input: User input text
            context: Optional context

        Returns:
            SkillIntent if matched, None otherwise
        """
        text_lower = user_input.lower()
        best_match = None
        best_score = 0.0

        for skill_id, intent_patterns in self._patterns.items():
            for intent_pattern in intent_patterns:
                score = 0.0
                matched_patterns = []
                extracted_params = {}

                # Check each pattern
                for pattern in intent_pattern.patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        # Base score for match
                        score += 0.5

                        # Extract named groups as parameters
                        for param_name, param_value in match.groupdict().items():
                            if param_value:
                                extracted_params[param_name] = param_value

                        matched_patterns.append(pattern)

                # Apply parameter extractors
                for param_name, extractor in intent_pattern.parameter_extractors.items():
                    try:
                        value = extractor(user_input)
                        if value is not None:
                            extracted_params[param_name] = value
                            score += 0.1  # Bonus for extracted param
                    except Exception as e:
                        logger.warning(f"Parameter extractor failed for {param_name}: {e}")

                # Apply confidence boost
                score += intent_pattern.confidence_boost

                # Normalize score to 0.0-1.0
                confidence = min(score, 1.0)

                # Track best match
                if confidence > best_score:
                    best_score = confidence
                    best_match = SkillIntent(
                        skill_id=skill_id,
                        confidence=confidence,
                        parameters=extracted_params,
                        raw_input=user_input,
                        matched_patterns=matched_patterns
                    )

        return best_match

    async def _ai_classify(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillIntent]:
        """
        Use AI to classify intent (fallback for ambiguous cases).

        Implements robust error handling, timeout protection, and response validation.

        Args:
            user_input: User input text
            context: Optional context

        Returns:
            SkillIntent if AI detects intent, None otherwise
        """
        try:
            # Check if AI classification is enabled (lazy import settings)
            from ....storage.settings_manager import settings

            if not settings.get('advanced.enable_ai_intent_classification', False):
                logger.debug("AI intent classification disabled in settings")
                return None

            # Get configuration
            timeout_seconds = settings.get('advanced.ai_intent_timeout_seconds', 5)
            ai_threshold = settings.get('advanced.ai_intent_confidence_threshold', 0.65)

            # Import AIService lazily (avoid circular dependency)
            from ....ai.ai_service import ai_service

            if not ai_service or not ai_service.is_initialized:
                logger.warning("AIService not initialized, cannot perform AI classification")
                return None

            # Format prompt with enabled skills only
            skill_list = self._format_enabled_skill_list()
            if not skill_list:
                logger.debug("No enabled skills to classify")
                return None

            prompt = self.AI_CLASSIFICATION_PROMPT_TEMPLATE.format(
                skill_list=skill_list,
                user_input=user_input[:200]  # Limit input length
            )

            logger.debug(f"Sending AI classification request (timeout={timeout_seconds}s)")

            # Send request with timeout protection
            try:
                # Use asyncio.wait_for to enforce timeout
                response_text = await asyncio.wait_for(
                    self._call_ai_service(ai_service, prompt),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"AI classification timed out after {timeout_seconds}s")
                return None
            except Exception as e:
                logger.error(f"AI service call failed: {e}")
                return None

            if not response_text:
                logger.warning("AI returned empty response")
                return None

            # Parse and validate JSON response
            ai_result = self._parse_ai_response(response_text)
            if not ai_result:
                return None

            # Extract results
            skill_id = ai_result.get('skill_id')
            confidence = float(ai_result.get('confidence', 0.0))
            reasoning = ai_result.get('reasoning', '')
            parameters = ai_result.get('parameters', {})

            # Check if AI found a match
            if not skill_id or skill_id == 'null' or skill_id is None:
                logger.debug(f"AI found no matching skill: {reasoning}")
                return None

            # Verify skill exists and is enabled
            if skill_id not in self._patterns:
                logger.warning(f"AI suggested invalid/disabled skill_id: {skill_id}")
                return None

            # Calibrate AI confidence (reduce overconfidence)
            calibrated_confidence = confidence * 0.85

            # Check confidence threshold
            if calibrated_confidence < ai_threshold:
                logger.debug(
                    f"AI confidence {calibrated_confidence:.2%} below threshold {ai_threshold:.2%}"
                )
                return None

            # Validate parameters against skill schema
            validated_params = self._validate_parameters(skill_id, parameters)

            # Create SkillIntent
            intent = SkillIntent(
                skill_id=skill_id,
                confidence=calibrated_confidence,
                parameters=validated_params,
                raw_input=user_input,
                matched_patterns=[f"AI: {reasoning}"]
            )

            logger.info(
                f"✓ AI classified intent: {skill_id} ({calibrated_confidence:.2%}) - {reasoning}"
            )
            return intent

        except Exception as e:
            logger.error(f"AI classification error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    async def _call_ai_service(self, ai_service, prompt: str) -> Optional[str]:
        """
        Call AIService to get classification response.

        Args:
            ai_service: AIService instance
            prompt: Classification prompt

        Returns:
            Response text or None
        """
        try:
            # Call async method (wraps sync version)
            response_text = await ai_service.send_message_without_system_prompt_async(prompt)
            return response_text if response_text else None
        except Exception as e:
            logger.error(f"AIService call exception: {e}")
            return None

    def _parse_ai_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse and validate AI JSON response.

        Handles markdown code blocks and validates structure.

        Args:
            response_text: Raw AI response

        Returns:
            Parsed dict or None if invalid
        """
        try:
            # Clean markdown code blocks
            cleaned = self._clean_json_response(response_text)

            # Parse JSON
            ai_result = json.loads(cleaned)

            # Validate structure
            if not self._validate_ai_response(ai_result):
                return None

            return ai_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response_text[:200]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None

    def _clean_json_response(self, text: str) -> str:
        """
        Remove markdown code blocks and formatting from AI response.

        Handles:
        - ```json ... ```
        - ``` ... ```
        - Text before/after JSON

        Args:
            text: Raw response text

        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks using regex
        text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)

        # Try to extract JSON object if embedded in text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0).strip()

        return text.strip()

    def _validate_ai_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate AI response has required fields and correct types.

        Args:
            response: Parsed JSON response

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ['skill_id', 'confidence']
        for field in required_fields:
            if field not in response:
                logger.warning(f"AI response missing required field: {field}")
                return False

        # Validate confidence is a number between 0 and 1
        try:
            confidence = float(response['confidence'])
            if not 0.0 <= confidence <= 1.0:
                logger.warning(f"AI confidence out of range: {confidence}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"AI confidence is not a valid number: {response.get('confidence')}")
            return False

        # Validate parameters is a dict (if present)
        if 'parameters' in response and not isinstance(response['parameters'], dict):
            logger.warning("AI parameters field is not a dictionary")
            return False

        return True

    def _format_enabled_skill_list(self) -> str:
        """
        Format enabled skills for AI prompt.

        Only includes enabled skills to prevent AI from suggesting disabled ones.

        Returns:
            Formatted skill list string
        """
        skills_info = []

        for skill_id, patterns in self._patterns.items():
            # Get first few patterns as examples
            example_patterns = patterns[0].patterns[:2] if patterns else []
            examples = "', '".join(example_patterns)

            skills_info.append(
                f"- {skill_id}: Triggers on patterns like '{examples}'"
            )

        if not skills_info:
            return "No skills available"

        return "\n".join(skills_info)

    def _validate_parameters(self, skill_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against skill schema.

        Removes invalid parameters and logs warnings.

        Args:
            skill_id: Skill identifier
            parameters: Parameters from AI

        Returns:
            Validated parameters dict
        """
        # For Phase 2: Basic validation (non-empty dict check)
        # Phase 3: Add schema validation against skill metadata

        if not isinstance(parameters, dict):
            logger.warning(f"Parameters for {skill_id} not a dict: {type(parameters)}")
            return {}

        # Remove None values
        validated = {k: v for k, v in parameters.items() if v is not None}

        return validated

    def register_patterns(
        self,
        skill_id: str,
        patterns: List[str],
        parameter_extractors: Optional[Dict[str, Callable[[str], Any]]] = None
    ) -> None:
        """
        Register intent patterns for a skill.

        Args:
            skill_id: ID of skill
            patterns: List of pattern strings or regexes
            parameter_extractors: Functions to extract parameter values
        """
        if skill_id not in self._patterns:
            self._patterns[skill_id] = []

        intent_pattern = IntentPattern(
            skill_id=skill_id,
            patterns=patterns,
            parameter_extractors=parameter_extractors or {},
        )

        self._patterns[skill_id].append(intent_pattern)

        logger.debug(f"Registered {len(patterns)} patterns for skill: {skill_id}")

    def unregister_patterns(self, skill_id: str) -> bool:
        """
        Remove all patterns for a skill.

        Args:
            skill_id: ID of skill to unregister

        Returns:
            True if patterns were removed, False if skill not found
        """
        if skill_id in self._patterns:
            del self._patterns[skill_id]
            logger.debug(f"Unregistered patterns for skill: {skill_id}")
            return True
        return False

    def set_confidence_threshold(self, threshold: float) -> None:
        """
        Set minimum confidence score for intent detection.

        Args:
            threshold: Confidence threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        self._confidence_threshold = threshold
        logger.info(f"Intent confidence threshold set to {threshold:.2%}")

    def get_confidence_scores(self, user_input: str) -> Dict[str, float]:
        """
        Get confidence scores for all skills.

        Args:
            user_input: User's input text

        Returns:
            Dict mapping skill_id to confidence score
        """
        text_lower = user_input.lower()
        scores = {}

        for skill_id, intent_patterns in self._patterns.items():
            max_score = 0.0

            for intent_pattern in intent_patterns:
                score = 0.0

                # Check each pattern
                for pattern in intent_pattern.patterns:
                    if re.search(pattern, text_lower):
                        score += 0.5

                score += intent_pattern.confidence_boost
                max_score = max(max_score, min(score, 1.0))

            if max_score > 0.0:
                scores[skill_id] = max_score

        return scores

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about registered patterns.

        Returns:
            Dictionary with pattern statistics
        """
        stats = {
            "total_skills": len(self._patterns),
            "total_patterns": sum(
                len(intent_patterns) for intent_patterns in self._patterns.values()
            ),
            "threshold": self._confidence_threshold,
            "ai_fallback_enabled": self._use_ai_fallback,
            "patterns_per_skill": {
                skill_id: len(intent_patterns)
                for skill_id, intent_patterns in self._patterns.items()
            },
        }
        return stats
