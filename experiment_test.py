"""Utility functions for text processing."""

import re


def slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug.

    - Lowercases the text
    - Replaces whitespace and special characters with hyphens
    - Removes consecutive hyphens
    - Strips leading/trailing hyphens
    - Strips non-ASCII characters

    Args:
        text: The input string to slugify.

    Returns:
        A URL-friendly slug string.

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("  Python 3.10  ")
        'python-3-10'
    """
    text = text.lower().strip()
    # Replace dots with hyphens before stripping special chars
    text = text.replace('.', '-')
    # Remove non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Remove remaining special characters
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace whitespace and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a specified maximum length.

    If the text exceeds max_length, it is cut off and a suffix is appended.
    The total length of the result (including suffix) will not exceed max_length.

    Args:
        text: The input string to truncate.
        max_length: Maximum allowed length of the result (including suffix).
        suffix: String to append when truncation occurs.

    Returns:
        The truncated string.

    Examples:
        >>> truncate("Hello, World!", 8)
        'Hello...'
        >>> truncate("Short", 100)
        'Short'
    """
    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return suffix[:max_length]

    return text[: max_length - len(suffix)] + suffix


def word_count(text: str) -> int:
    """Count the number of words in a string.

    Words are defined as sequences of non-whitespace characters.
    Empty strings and strings with only whitespace return 0.

    Args:
        text: The input string to count words in.

    Returns:
        The number of words in the string.

    Examples:
        >>> word_count("Hello world")
        2
        >>> word_count("  ")
        0
    """
    if not text or not text.strip():
        return 0
    return len(text.split())
