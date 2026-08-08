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
        A slugified version of the input string.
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to a maximum length, appending a suffix if truncated.

    Args:
        text: The input string to truncate.
        max_length: The maximum allowed length of the result (including suffix).
        suffix: The string to append when truncation occurs. Defaults to "...".

    Returns:
        The truncated string with suffix if it exceeded max_length, otherwise
        the original string.
    """
    if len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[: max_length - len(suffix)] + suffix


def word_count(text: str) -> int:
    """Count the number of words in a string.

    Words are defined as sequences of non-whitespace characters.

    Args:
        text: The input string to count words in.

    Returns:
        The number of words in the string. Returns 0 for empty or
        whitespace-only strings.
    """
    if not text or not text.strip():
        return 0
    return len(text.split())
