"""
Intent Classifier - Hybrid intent detection system.

Combines pattern matching with optional AI fallback for detecting user intent
to execute skills from natural language input.
"""

import logging
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from ..interfaces.skill_manager import SkillIntent, IIntentClassifier

logger = logging.getLogger("ghostman.skills.intent")


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
        "file_search": [
            r"(find|locate|search\s+for)\s+(a\s+)?(file|document|folder)",
            r"where\s+is\s+(my|the)",
            r"show\s+me\s+files",
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
        ],
    }

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
            self.register_patterns(skill_id, patterns)

        logger.debug(f"Registered default patterns for {len(self.DEFAULT_PATTERNS)} skills")

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

        Args:
            user_input: User input text
            context: Optional context

        Returns:
            SkillIntent if AI detects intent, None otherwise
        """
        # TODO: Implement AI-based classification using existing AIService
        # This would involve:
        # 1. Construct prompt with available skills and their descriptions
        # 2. Ask AI which skill (if any) the user wants to use
        # 3. Extract parameters from response
        # 4. Return SkillIntent with confidence

        logger.debug("AI fallback not yet implemented")
        return None

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
