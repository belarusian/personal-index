"""Utility functions for text processing."""

import re


def slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug.

    - Lowercases the text
    - Replaces whitespace and special characters with hyphens
    - Removes consecutive hyphens
    - Strips leading/trailing hyphens

    Args:
        text: The input string to slugify.

    Returns:
        A URL-friendly slug string.

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("  Python 3.10 is great  ")
        'python-3-10-is-great'
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to a maximum length, appending a suffix if truncated.

    Args:
        text: The input string to truncate.
        max_length: The maximum allowed length of the result (including suffix).
        suffix: The string to append when truncation occurs. Defaults to "...".

    Returns:
        The truncated string with suffix if needed, or the original string
        if it fits within max_length.

    Raises:
        ValueError: If max_length is less than the length of the suffix.

    Examples:
        >>> truncate("Hello, World!", 8)
        'Hello...'
        >>> truncate("Hi", 10)
        'Hi'
    """
    if max_length < len(suffix):
        raise ValueError(
            f"max_length ({max_length}) must be at least the length of the suffix ({len(suffix)})"
        )
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def word_count(text: str) -> int:
    """Count the number of words in a string.

    Words are defined as sequences of non-whitespace characters.

    Args:
        text: The input string to count words in.

    Returns:
        The number of words in the text. Returns 0 for empty or whitespace-only strings.

    Examples:
        >>> word_count("Hello world")
        2
        >>> word_count("  One  two   three  ")
        3
        >>> word_count("")
        0
    """
    if not text or not text.strip():
        return 0
    return len(text.split())
