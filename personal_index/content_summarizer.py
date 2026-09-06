"""Content summarization for personal-index.

Provides extractive summarization of indexed content using
sentence scoring based on keyword frequency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


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
    """Split *text* into a list of sentence strings.

    Normalizes all runs of whitespace to a single space and strips the
    ends. Returns ``[]`` immediately when the normalized text is empty.
    Otherwise splits on sentence-ending punctuation (``.``/``!``/``?``)
    followed by whitespace and an uppercase letter
    (``re.split(r'(?<=[.!?])\\s+(?=[A-Z])', text)``), then strips each
    fragment and drops any that are empty. No abbreviation table or
    lookahead is applied. Returns the list of non-empty sentence strings.
    """
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
    """Tokenize text into lowercase alphanumeric tokens.

    Lowercases the input, then returns every maximal run of lowercase
    letters and digits found by ``re.findall(r'[a-z0-9]+', text.lower())``.
    Splits on any non-alphanumeric character (punctuation, spaces, and
    apostrophes all act as separators) and keeps digit runs as their own
    tokens. Returns ``list[str]``; an empty or all-punctuation input
    yields an empty list.
    """
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
    "as", "through", "below",
    "under", "further", "once", "many",
    "much", "nor", "s", "t", "don",
    "d", "ll", "m", "o", "re", "ve", "y", "ain", "aren",
    "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma",
    "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn",
})


def _word_frequency(text: str) -> dict[str, int]:
    """Calculate word frequency from text.

    Tokenizes *text* via :func:`_tokenize` (lowercase alphanumeric tokens),
    skips tokens present in the module-level :data:`STOPWORDS` frozenset,
    skips tokens with length <= 2, and accumulates counts in a plain dict
    (freq[word] = freq.get(word, 0) + 1).  Returns the resulting
    :obj:`dict[str, int]` mapping.
    """
    words = _tokenize(text)
    freq: dict[str, int] = {}
    for word in words:
        if word not in STOPWORDS and len(word) > 2:
            freq[word] = freq.get(word, 0) + 1
    return freq


def _score_sentence(sentence: str, word_freq: dict[str, int]) -> float:
    """Return the mean per-token frequency score of a sentence.

    Tokenizes ``sentence`` via ``_tokenize``. If no tokens are produced
    (empty or all-punctuation input) returns ``0.0``. Otherwise returns
    the sum of ``word_freq.get(w, 0)`` over the tokens divided by the
    token count (the mean per-token frequency, not the raw sum), so a
    short sentence of frequent words can outscore a long one. Returns
    ``float``.
    """
    words = _tokenize(sentence)
    if not words:
        return 0.0
    score = sum(word_freq.get(w, 0) for w in words)
    # Normalize by sentence length to avoid bias toward long sentences
    return score / len(words)


def _score_and_select(sentences: list[str], word_freq: dict[str, int], max_sentences: int) -> list[str]:
    scored: list[tuple[int, float, str]] = []
    for i, sentence in enumerate(sentences):
        score = _score_sentence(sentence, word_freq)
        if i == 0:
            score *= 2.5
        if i == len(sentences) - 1:
            score *= 1.1
        scored.append((i, score, sentence))

    scored.sort(key=lambda x: x[1], reverse=True)
    selected = scored[:max_sentences]
    selected.sort(key=lambda x: x[0])
    return [s[2] for s in selected]


def _build_summary_result(text: str, summary_sentences: list[str]) -> SummaryResult:
    summary = " ".join(summary_sentences)
    original_words = len(_tokenize(text))
    summary_words = len(_tokenize(summary))
    return SummaryResult(
        original_text=text,
        summary=summary,
        sentences=summary_sentences,
        ratio=summary_words / max(original_words, 1),
        word_count_original=original_words,
        word_count_summary=summary_words,
    )


def _no_op_result(text: str | None) -> SummaryResult:
    t = text or ""
    wc = len(_tokenize(t))
    return SummaryResult(
        original_text=t,
        summary=t,
        sentences=[t] if t else [],
        ratio=1.0,
        word_count_original=wc,
        word_count_summary=wc,
    )


def summarize(
    text: str,
    max_sentences: int = 3,
    min_length: int = 50,
) -> SummaryResult:
    """Generate an extractive summary of *text* and return a SummaryResult.

    Behavior, in order:
      1. Guard path: if *text* is falsy or ``len(text) < min_length``
         (default 50), return ``_no_op_result(text)`` -- a SummaryResult whose
         ``summary`` equals *text*, ``ratio`` is 1.0, ``sentences`` is
         ``[text]`` (or ``[]`` when *text* is empty), and both word counts are
         ``len(_tokenize(text))``. No sentence splitting or scoring occurs.
      2. Short-text path: split *text* via ``_split_sentences``; if the
         sentence count is ``<= max_sentences`` (default 3), return
         ``_build_summary_result(text, sentences)`` keeping ALL sentences
         (no scoring, no selection).
      3. Scoring path: otherwise compute ``_word_frequency(text)`` and select
         the top ``max_sentences`` via ``_score_and_select`` (the first
         sentence is boosted x2.5 and the last x1.1 before ranking), then
         return ``_build_summary_result(text, selected)``.

    Returns:
        SummaryResult(original_text, summary, sentences, ratio,
        word_count_original, word_count_summary) where ``summary`` is the
        space-joined selected sentences and ``ratio`` is
        ``word_count_summary / max(word_count_original, 1)``.
    """
    if not text or len(text) < min_length:
        return _no_op_result(text)

    sentences = _split_sentences(text)
    if len(sentences) <= max_sentences:
        return _build_summary_result(text, sentences)

    word_freq = _word_frequency(text)
    selected = _score_and_select(sentences, word_freq, max_sentences)
    return _build_summary_result(text, selected)


def summarize_page(
    title: str,
    content: str,
    max_sentences: int = 3,
) -> SummaryResult:
    """Summarize a page using title and content.

    The title is prepended to the content before summarizing.

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
