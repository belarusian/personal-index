"""Content summarization for personal-index.

Provides extractive summarization of indexed content using
sentence scoring based on keyword frequency and TF-IDF-like metrics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SummaryResult:
    """Result of a content summarization."""
    original_text: str
    summary: str
    sentences: list[str]
    ratio: float  # ratio of summary length to original
    word_count_original: int
    word_count_summary: int

    def __str__(self) -> str:
        return self.summary


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, handling common abbreviations."""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []

    # Split on sentence-ending punctuation followed by space and uppercase
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    # Filter empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words."""
    return re.findall(r'[a-z0-9]+', text.lower())


STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "what", "which", "who", "whom", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "about", "above", "after", "again", "also", "any",
    "because", "before", "between", "during", "if", "into", "like", "new",
    "now", "old", "over", "then", "there", "here", "up", "out", "off",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "once", "here", "there",
    "when", "where", "why", "how", "all", "both", "each", "few", "many",
    "much", "some", "any", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "s", "t", "can", "will", "just", "don",
    "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain", "aren",
    "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma",
    "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn",
})


def _word_frequency(text: str) -> dict[str, int]:
    """Calculate word frequency from text."""
    words = _tokenize(text)
    freq: dict[str, int] = {}
    for word in words:
        if word not in STOPWORDS and len(word) > 2:
            freq[word] = freq.get(word, 0) + 1
    return freq


def _score_sentence(sentence: str, word_freq: dict[str, int]) -> float:
    """Score a sentence based on word frequencies."""
    words = _tokenize(sentence)
    if not words:
        return 0.0
    score = sum(word_freq.get(w, 0) for w in words)
    # Normalize by sentence length to avoid bias toward long sentences
    return score / len(words)


def summarize(
    text: str,
    max_sentences: int = 3,
    min_length: int = 50,
) -> SummaryResult:
    """Generate an extractive summary of the given text.

    Uses sentence scoring based on keyword frequency to select
    the most informative sentences.

    Args:
        text: The text to summarize.
        max_sentences: Maximum number of sentences in the summary.
        min_length: Minimum character length to attempt summarization.

    Returns:
        SummaryResult containing the summary and metadata.
    """
    if not text or len(text) < min_length:
        return SummaryResult(
            original_text=text or "",
            summary=text or "",
            sentences=[text] if text else [],
            ratio=1.0,
            word_count_original=len(_tokenize(text)),
            word_count_summary=len(_tokenize(text)),
        )

    sentences = _split_sentences(text)
    if len(sentences) <= max_sentences:
        return SummaryResult(
            original_text=text,
            summary=text,
            sentences=sentences,
            ratio=1.0,
            word_count_original=len(_tokenize(text)),
            word_count_summary=len(_tokenize(text)),
        )

    # Calculate word frequencies
    word_freq = _word_frequency(text)

    # Score each sentence
    scored: list[tuple[int, float, str]] = []
    for i, sentence in enumerate(sentences):
        score = _score_sentence(sentence, word_freq)
        # Boost first and last sentences slightly
        if i == 0:
            score *= 2.5
        if i == len(sentences) - 1:
            score *= 1.1
        scored.append((i, score, sentence))

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = scored[:max_sentences]

    # Re-sort by original order
    selected.sort(key=lambda x: x[0])

    summary = " ".join(s[2] for s in selected)
    original_words = len(_tokenize(text))
    summary_words = len(_tokenize(summary))

    return SummaryResult(
        original_text=text,
        summary=summary,
        sentences=[s[2] for s in selected],
        ratio=summary_words / max(original_words, 1),
        word_count_original=original_words,
        word_count_summary=summary_words,
    )


def summarize_page(
    title: str,
    content: str,
    max_sentences: int = 3,
) -> SummaryResult:
    """Summarize a page using title and content.

    The title is used as a keyword boost for sentence scoring.

    Args:
        title: Page title.
        content: Page content text.
        max_sentences: Maximum sentences in summary.

    Returns:
        SummaryResult with the page summary.
    """
    # If content is empty, return empty summary
    if not content:
        return SummaryResult(
            original_text=title,
            summary="",
            sentences=[],
            ratio=0.0,
            word_count_original=len(_tokenize(title)),
            word_count_summary=0,
        )
    # Combine title with content for scoring
    combined = f"{title}. {content}"
    return summarize(combined, max_sentences=max_sentences)
