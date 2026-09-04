"""Text processing utilities for content indexing."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace sequences into single spaces and strip.

    Args:
        text: Input text with potentially irregular whitespace.

    Returns:
        Normalized text with single spaces between words.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def remove_html_tags(html: str) -> str:
    """Strip HTML tags from text, preserving content.

    Args:
        html: HTML string to clean.

    Returns:
        Plain text with HTML tags removed.
    """
    if not html:
        return ""
    # Remove script and style content first
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return normalize_whitespace(text)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length, preferring a word boundary.

    The cut is made at a word boundary only when a space exists in the
    latter part of the truncated window (after 60% of ``max_length``);
    otherwise the text is cut at exactly ``max_length`` characters and
    may break a word. The ``suffix`` is appended when truncation occurs.

    Args:
        text: Text to truncate.
        max_length: Maximum character length.
        suffix: String to append when truncated.

    Returns:
        Truncated text.
    """
    if not text or len(text) <= max_length:
        return text or ""
    truncated = text[:max_length]
    # Don't break in the middle of a word
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.6:
        truncated = truncated[:last_space]
    return truncated.rstrip() + suffix


def extract_sentences(text: str, min_length: int = 10) -> list[str]:
    """Split text into sentences.

    Args:
        text: Input text.
        min_length: Minimum sentence length to include.

    Returns:
        List of sentence strings.
    """
    if not text:
        return []
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) >= min_length]


def extract_paragraphs(text: str, min_length: int = 20) -> list[str]:
    """Split text into paragraphs.

    Args:
        text: Input text.
        min_length: Minimum paragraph length to include.

    Returns:
        List of paragraph strings.
    """
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if len(p.strip()) >= min_length]


def word_frequency(text: str, min_freq: int = 1, stop_words: set[str] | None = None) -> dict[str, int]:
    """Calculate word frequency in text.

    Args:
        text: Input text.
        min_freq: Minimum frequency to include.
        stop_words: Optional set of words to exclude.

    Returns:
        Dict mapping words to their frequencies.
    """
    if not text:
        return {}
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if stop_words:
        words = [w for w in words if w not in stop_words]
    counter = Counter(words)
    return {word: freq for word, freq in counter.items() if freq >= min_freq}


def extract_keywords(text: str, top_n: int = 10, min_freq: int = 2) -> list[tuple[str, int]]:
    """Extract top keywords from text by frequency.

    Args:
        text: Input text.
        top_n: Number of top keywords to return.
        min_freq: Minimum frequency threshold.

    Returns:
        List of (word, frequency) tuples sorted by frequency descending.
    """
    # First get words meeting min_freq threshold
    freq_filtered = word_frequency(text, min_freq=min_freq)
    result = sorted(freq_filtered.items(), key=lambda x: x[1], reverse=True)

    # If we need more results to reach top_n, include remaining words
    if len(result) < top_n:
        freq_all = word_frequency(text, min_freq=1)
        existing_words = {w for w, _ in result}
        remaining = [(w, f) for w, f in freq_all.items() if w not in existing_words]
        remaining.sort(key=lambda x: x[1], reverse=True)
        result.extend(remaining[:top_n - len(result)])

    return result[:top_n]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Number of single-character edits to transform s1 into s2.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0).

    Uses Levenshtein distance normalized by the longer string length.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Similarity ratio where 1.0 means identical.
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Input text.

    Returns:
        Lowercase, hyphen-separated slug.
    """
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def highlight_text(text: str, terms: list[str], tag: str = "mark") -> str:
    """Highlight search terms in text.

    Args:
        text: Input text.
        terms: List of terms to highlight.
        tag: HTML tag to wrap matches with.

    Returns:
        Text with terms wrapped in HTML tags.
    """
    if not text or not terms:
        return text
    # Single-pass regex alternation, longest-first, so each source position
    # is matched at most once and shorter terms are not re-matched inside
    # markers inserted for longer terms.
    filtered = [t for t in terms if t]
    if not filtered:
        return text
    filtered.sort(key=len, reverse=True)
    term_map = {t.lower(): t for t in filtered}
    pattern = re.compile('|'.join(re.escape(t) for t in filtered), re.IGNORECASE)
    return pattern.sub(lambda m: f"<{tag}>{term_map.get(m.group(0).lower(), m.group(0))}</{tag}>", text)


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Input text.

    Returns:
        Number of words.
    """
    if not text:
        return 0
    return len(text.split())


def count_characters(text: str, include_spaces: bool = True) -> int:
    """Count characters in text.

    Args:
        text: Input text.
        include_spaces: Whether to count whitespace.

    Returns:
        Character count.
    """
    if not text:
        return 0
    if include_spaces:
        return len(text)
    return len(text.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", ""))


def read_time_minutes(text: str, wpm: int = 200) -> int:
    """Estimate reading time in minutes.

    Args:
        text: Input text.
        wpm: Words per minute reading speed.

    Returns:
        Integer number of minutes (minimum 1).
    """
    words = count_words(text)
    return max(1, round(words / wpm))


# Common English stopwords for text processing
STOPWORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "this", "that", "these",
    "those", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "need", "dare", "ought", "used", "not", "no", "nor",
    "so", "if", "then", "than", "too", "very", "just", "about", "above",
    "after", "again", "all", "also", "am", "any", "as", "because", "before",
    "between", "both", "each", "few", "further", "get", "got", "he", "her",
    "here", "him", "his", "how", "i", "into", "more", "most", "my", "now",
    "only", "other", "our", "out", "over", "own", "same", "she", "some",
    "such", "there", "they", "through", "up", "we", "what", "when", "where",
    "which", "while", "who", "whom", "why", "you", "your", "s", "t", "me",
    "himself", "herself", "itself", "themselves", "myself", "ourselves",
    "yourself", "yourselves", "down", "off", "once", "upon", "yet",
}


def tokenize(text: str, lowercase: bool = True, remove_stopwords: bool = False) -> list[str]:
    """Tokenize text into words.

    Args:
        text: Input text.
        lowercase: Whether to convert to lowercase.
        remove_stopwords: Whether to remove common English stopwords.

    Returns:
        List of token strings.
    """
    if not text:
        return []
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b|\b\d+\b", text)
    if lowercase:
        tokens = [t.lower() for t in tokens]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens
