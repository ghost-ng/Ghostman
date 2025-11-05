"""
Collection Mention Parser for handling @collection:name syntax in user prompts.

Parses user messages to detect collection mentions and automatically attach
them to the conversation before processing the message.
"""

import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger("ghostman.application.collection_mention_parser")


class CollectionMentionParser:
    """
    Parser for @collection:name mention syntax in user messages.

    Syntax examples:
    - @collection:python-utils - Attach collection named "python-utils"
    - @collection:"My Python Project" - Attach collection with spaces in name
    - Multiple: @collection:utils @collection:docs - Attach multiple collections

    The mention is removed from the message before sending to AI.
    """

    # Regex patterns for collection mentions
    # Matches @collection:name or @collection:"name with spaces"
    MENTION_PATTERN = r'@collection:(?:"([^"]+)"|([^\s]+))'

    @staticmethod
    def parse_mentions(message: str) -> Tuple[List[str], str]:
        """
        Parse collection mentions from a message.

        Args:
            message: User message that may contain @collection mentions

        Returns:
            Tuple of (collection_names, cleaned_message)
            - collection_names: List of mentioned collection names
            - cleaned_message: Message with mentions removed
        """
        collection_names = []

        # Find all matches
        matches = re.finditer(CollectionMentionParser.MENTION_PATTERN, message)

        for match in matches:
            # Group 1 is quoted name, group 2 is unquoted name
            collection_name = match.group(1) if match.group(1) else match.group(2)
            collection_names.append(collection_name)
            logger.debug(f"Found collection mention: {collection_name}")

        # Remove mentions from message
        cleaned_message = re.sub(
            CollectionMentionParser.MENTION_PATTERN,
            '',
            message
        ).strip()

        # Clean up multiple spaces
        cleaned_message = ' '.join(cleaned_message.split())

        if collection_names:
            logger.info(
                f"✓ Parsed {len(collection_names)} collection mention(s): "
                f"{', '.join(collection_names)}"
            )

        return collection_names, cleaned_message

    @staticmethod
    def has_mentions(message: str) -> bool:
        """
        Check if a message contains any collection mentions.

        Args:
            message: User message to check

        Returns:
            True if message contains @collection mentions, False otherwise
        """
        return bool(re.search(CollectionMentionParser.MENTION_PATTERN, message))

    @staticmethod
    def extract_first_mention(message: str) -> Optional[str]:
        """
        Extract the first collection mention from a message.

        Args:
            message: User message

        Returns:
            First collection name mentioned, or None if no mentions
        """
        match = re.search(CollectionMentionParser.MENTION_PATTERN, message)
        if match:
            return match.group(1) if match.group(1) else match.group(2)
        return None

    @staticmethod
    def format_mention(collection_name: str) -> str:
        """
        Format a collection name as a mention.

        Args:
            collection_name: Name of the collection

        Returns:
            Formatted mention string (e.g., '@collection:name' or '@collection:"name with spaces"')
        """
        if ' ' in collection_name:
            return f'@collection:"{collection_name}"'
        else:
            return f'@collection:{collection_name}'

    @staticmethod
    def insert_mentions(message: str, collection_names: List[str]) -> str:
        """
        Insert collection mentions into a message.

        Args:
            message: Original message
            collection_names: List of collection names to mention

        Returns:
            Message with mentions prepended
        """
        if not collection_names:
            return message

        mentions = ' '.join(
            CollectionMentionParser.format_mention(name)
            for name in collection_names
        )

        return f"{mentions} {message}".strip()


# Example usage and tests
if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(level=logging.DEBUG)

    # Test cases
    test_messages = [
        "Can you review the code in @collection:python-utils?",
        '@collection:"My Python Project" show me the main function',
        "Compare @collection:utils with @collection:docs",
        'Use @collection:"Research Papers" and @collection:notes to answer',
        "No mentions in this message",
        "@collection:test123 @collection:another-test check these files",
    ]

    print("=" * 60)
    print("Collection Mention Parser - Test Cases")
    print("=" * 60)

    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        print("-" * 60)

        # Check if has mentions
        has_mentions = CollectionMentionParser.has_mentions(message)
        print(f"Has mentions: {has_mentions}")

        # Parse mentions
        mentions, cleaned = CollectionMentionParser.parse_mentions(message)
        print(f"Mentions found: {mentions}")
        print(f"Cleaned message: {cleaned}")

        # Extract first mention
        first = CollectionMentionParser.extract_first_mention(message)
        print(f"First mention: {first}")

    # Test insert mentions
    print("\n" + "=" * 60)
    print("Test: Insert Mentions")
    print("=" * 60)
    original = "Please help me with this code"
    collections = ["utils", "My Project"]
    with_mentions = CollectionMentionParser.insert_mentions(original, collections)
    print(f"Original: {original}")
    print(f"Collections: {collections}")
    print(f"With mentions: {with_mentions}")

    # Verify round-trip
    parsed_mentions, parsed_clean = CollectionMentionParser.parse_mentions(with_mentions)
    print(f"Round-trip mentions: {parsed_mentions}")
    print(f"Round-trip cleaned: {parsed_clean}")
