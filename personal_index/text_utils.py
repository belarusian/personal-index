"""Text processing utilities for personal-index.

Handles text extraction, cleaning, tokenization, and stopword removal.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Optional


# Common English stopwords
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "it", "its", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "what", "which", "who",
    "whom", "whose", "where", "when", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "as", "until", "while", "about", "between", "through",
    "during", "before", "after", "above", "below", "up", "down", "out",
    "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "any", "if", "into",
}


def clean_html(html: str) -> str:
    """Remove HTML tags and entities from text.

    Args:
        html: Raw HTML string.

    Returns:
        Clean text string.
    """
    # Remove script and style elements
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)

    # Remove all other tags
    clean = re.sub(r"<[^>]+>", "", clean)

    # Decode common HTML entities
    entity_map = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }
    for entity, char in entity_map.items():
        clean = clean.replace(entity, char)

    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean


def tokenize(text: str, lowercase: bool = True) -> list[str]:
    """Tokenize text into words.

    Args:
        text: Input text string.
        lowercase: Whether to convert to lowercase.

    Returns:
        List of token strings.
    """
    if lowercase:
        text = text.lower()

    # Split on whitespace and punctuation
    tokens = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", text)
    return tokens


def remove_stopwords(tokens: list[str], stopwords: Optional[set[str]] = None) -> list[str]:
    """Remove stopwords from a list of tokens.

    Args:
        tokens: List of token strings.
        stopwords: Custom set of stopwords, or use defaults.

    Returns:
        Filtered list of tokens.
    """
    stop = stopwords or STOPWORDS
    return [t for t in tokens if t.lower() not in stop]


def extract_keywords(text: str, top_n: int = 10) -> list[tuple[str, int]]:
    """Extract top keywords from text using term frequency.

    Args:
        text: Input text string.
        top_n: Number of top keywords to return.

    Returns:
        List of (keyword, count) tuples sorted by frequency.
    """
    tokens = tokenize(text)
    filtered = remove_stopwords(tokens)
    freq = Counter(filtered)
    return freq.most_common(top_n)


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Args:
        text: Input text.
        max_length: Maximum length.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rsplit(" ", 1)[0] + suffix


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute simple text similarity using Jaccard index.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    tokens1 = set(tokenize(text1))
    tokens2 = set(tokenize(text2))

    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


def extract_email_addresses(text: str) -> list[str]:
    """Extract email addresses from text.

    Args:
        text: Input text.

    Returns:
        List of email address strings.
    """
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(pattern, text)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text.

    Args:
        text: Input text.

    Returns:
        List of URL strings.
    """
    pattern = r"https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=-]+"
    return re.findall(pattern, text)
